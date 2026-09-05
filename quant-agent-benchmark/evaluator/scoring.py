#!/usr/bin/env python3
"""Implementation-agnostic hidden evaluator for quantcurve candidates."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_ROOT = BENCHMARK_ROOT / "evaluator"
INPUT_ROOT = BENCHMARK_ROOT / "input"
VISIBLE_MARKET = INPUT_ROOT / "market_data" / "market_observations.csv"
GROUND_ROOT = EVALUATOR_ROOT / "ground_truth"
SCENARIO_ROOT = EVALUATOR_ROOT / "hidden_scenarios"
VALUATION_DATE = "2026-01-15"

CURVE_COLUMNS = ("maturity_years", "zero_rate", "discount_factor", "forward_rate")
CLEAN_COLUMNS = ("obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason")
RISK_COLUMNS = ("instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y")


@dataclass
class TestRecord:
    identifier: str
    passed: bool
    detail: str


@dataclass
class EvaluationState:
    tests: list[TestRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def check(self, identifier: str, passed: bool, detail: str) -> bool:
        self.tests.append(TestRecord(identifier, bool(passed), detail))
        return bool(passed)


def bounded_score(value: float, full: float, zero: float) -> float:
    """Return 1 at or below full, 0 at or above zero, linear between."""
    if not np.isfinite(value):
        return 0.0
    if value <= full:
        return 1.0
    if value >= zero:
        return 0.0
    return float((zero - value) / (zero - full))


def rmse(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0 or not np.isfinite(arr).all():
        return float("inf")
    return float(np.sqrt(np.mean(arr * arr)))


def locate_project(candidate: Path) -> Path | None:
    if (candidate / "pyproject.toml").is_file() and (candidate / "src").is_dir():
        return candidate
    children = [p for p in candidate.iterdir() if p.is_dir() and (p / "pyproject.toml").is_file() and (p / "src").is_dir()] if candidate.is_dir() else []
    return children[0] if len(children) == 1 else None


def sanitized_env(project: Path) -> dict[str, str]:
    keep = ("PATH", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update({
        "PYTHONPATH": str(project / "src"),
        "PYTHONHASHSEED": "0",
        "MPLBACKEND": "Agg",
        "NO_PROXY": "*",
    })
    return env


def run_command(command: list[str], cwd: Path, timeout: int = 180) -> dict[str, Any]:
    start = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=cwd, env=sanitized_env(cwd), capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-6000:],
            "wall_time_seconds": time.monotonic() - start,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": (exc.stdout or "")[-6000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-6000:] if isinstance(exc.stderr, str) else "",
            "wall_time_seconds": time.monotonic() - start,
            "timed_out": True,
        }


def run_cli(project: Path, market: Path, output: Path, timeout: int = 240) -> dict[str, Any]:
    command = [
        sys.executable, "-m", "quantcurve.cli", "run",
        "--market-data", str(market), "--output-dir", str(output),
        "--valuation-date", VALUATION_DATE,
    ]
    return run_command(command, project, timeout)


def safe_read_csv(path: Path, required: tuple[str, ...]) -> tuple[pd.DataFrame | None, str]:
    if not path.is_file():
        return None, f"missing {path.name}"
    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # evaluator must report candidate parse failures
        return None, f"cannot parse {path.name}: {type(exc).__name__}: {exc}"
    missing = [c for c in required if c not in frame.columns]
    if missing:
        return None, f"missing columns: {', '.join(missing)}"
    return frame, "ok"


def normalize_curve(frame: pd.DataFrame) -> pd.DataFrame:
    curve = frame.loc[:, CURVE_COLUMNS].copy()
    for col in CURVE_COLUMNS:
        curve[col] = pd.to_numeric(curve[col], errors="coerce")
    curve = curve.sort_values("maturity_years", kind="mergesort").drop_duplicates("maturity_years", keep="last")
    return curve.reset_index(drop=True)


def interp_zero(curve: pd.DataFrame, t: np.ndarray | float, bump: float = 0.0) -> np.ndarray:
    x = np.asarray(t, dtype=float)
    return np.interp(x, curve["maturity_years"], curve["zero_rate"], left=curve["zero_rate"].iloc[0], right=curve["zero_rate"].iloc[-1]) + bump


def curve_discount(curve: pd.DataFrame, t: np.ndarray | float, bump: float = 0.0) -> np.ndarray:
    x = np.asarray(t, dtype=float)
    return np.exp(-interp_zero(curve, x, bump) * x)


def payment_times(maturity: float, frequency: int) -> np.ndarray:
    return np.arange(1, max(1, int(round(maturity * frequency))) + 1, dtype=float) / frequency


def model_quote(row: pd.Series, curve: pd.DataFrame, bump: float = 0.0) -> float:
    t = float(row["maturity_years"])
    kind = row["instrument_type"]
    frequency = int(row["payment_frequency"])
    if kind == "deposit":
        return 100.0 * (1.0 / float(curve_discount(curve, t, bump)) - 1.0) / t
    times = payment_times(t, frequency)
    dfs = curve_discount(curve, times, bump)
    if kind == "ois_swap":
        return 100.0 * (1.0 - float(curve_discount(curve, t, bump))) / ((1.0 / frequency) * float(dfs.sum()))
    coupon = float(row["coupon_rate"])
    cash = np.full(times.shape, 100.0 * coupon / frequency)
    cash[-1] += 100.0
    return float(np.dot(cash, dfs))


def trade_pv(row: pd.Series, curve: pd.DataFrame, quote: float, bump: float = 0.0) -> float:
    t = float(row["maturity_years"])
    kind = row["instrument_type"]
    frequency = int(row["payment_frequency"])
    if kind == "deposit":
        r = quote / 100.0
        return 1_000_000.0 * (1.0 - (1.0 + r * t) * float(curve_discount(curve, t, bump)))
    if kind == "ois_swap":
        times = payment_times(t, frequency)
        annuity = float(curve_discount(curve, times, bump).sum()) / frequency
        return 1_000_000.0 * ((quote / 100.0) * annuity - (1.0 - float(curve_discount(curve, t, bump))))
    return model_quote(row, curve, bump) - quote


def curve_metrics(curve: pd.DataFrame, truth: pd.DataFrame, instruments: pd.DataFrame) -> dict[str, float]:
    t = truth["maturity_years"].to_numpy(float)
    z_true = truth["zero_rate"].to_numpy(float)
    f_true = truth["instantaneous_forward_rate"].to_numpy(float)
    z_est = interp_zero(curve, t)
    df_est = np.exp(-z_est * t)
    f_est = np.gradient(z_est * t, t, edge_order=1)
    weights = 1.0 / np.sqrt(0.15 + t)
    quote_errors: list[float] = []
    spread_normalized_errors: list[float] = []
    for _, row in instruments.iterrows():
        error = model_quote(row, curve) - float(row["true_quote"])
        # Rates become basis points; bond prices become 10-cent units.
        quote_errors.append(error * (100.0 if row["instrument_type"] != "bond" else 10.0))
        half_spread = max(abs(float(row["ask"]) - float(row["bid"])) / 2.0, 0.002 if row["instrument_type"] != "bond" else 0.02)
        spread_normalized_errors.append(error / half_spread)
    short = t <= 2.0
    long = t >= 15.0
    return {
        "zero_rate_rmse_bps": 1.0e4 * rmse(z_est - z_true),
        "weighted_zero_rate_rmse_bps": 1.0e4 * float(np.sqrt(np.average((z_est - z_true) ** 2, weights=weights))),
        "forward_rate_rmse_bps": 1.0e4 * rmse(f_est - f_true),
        "discount_factor_rmse_x1e4": 1.0e4 * rmse(df_est - truth["discount_factor"].to_numpy(float)),
        "hidden_instrument_normalized_rmse": rmse(np.asarray(quote_errors)),
        "bid_ask_normalized_pricing_rmse": rmse(np.asarray(spread_normalized_errors)),
        "short_end_zero_rmse_bps": 1.0e4 * rmse((z_est - z_true)[short]),
        "long_end_zero_rmse_bps": 1.0e4 * rmse((z_est - z_true)[long]),
        "forward_roughness": float(np.sqrt(np.mean(np.diff(f_est, n=2) ** 2))) if len(f_est) > 3 else float("inf"),
        "zero_curvature_rms": float(np.sqrt(np.mean(np.gradient(np.gradient(z_est, t), t) ** 2))) if len(t) > 3 else float("inf"),
    }


def risk_agreement(curve: pd.DataFrame, risk: pd.DataFrame, truth_instruments: pd.DataFrame) -> tuple[float, float, int]:
    merged = risk.merge(truth_instruments, on="instrument_id", how="inner")
    rel_errors: list[float] = []
    key_errors: list[float] = []
    valid = 0
    for _, row in merged.iterrows():
        try:
            reported = float(row["dv01"])
            q = float(row["true_quote"])
            expected = (trade_pv(row, curve, q, -1e-4) - trade_pv(row, curve, q, 1e-4)) / 2.0
            if np.isfinite(reported) and np.isfinite(expected):
                scale = max(abs(expected), 1e-8)
                rel_errors.append(abs(reported - expected) / scale)
                keys = sum(float(row[c]) for c in ("key_2y", "key_5y", "key_10y", "key_30y"))
                key_errors.append(abs(keys - reported) / max(abs(reported), 1e-8))
                valid += 1
        except (TypeError, ValueError, OverflowError):
            continue
    if not rel_errors:
        return float("inf"), float("inf"), 0
    return float(np.median(rel_errors)), float(np.median(key_errors)), valid


def data_quality_metrics(cleaning: pd.DataFrame | None) -> dict[str, float]:
    labels = pd.read_csv(GROUND_ROOT / "corruption_labels.csv")
    visible = pd.read_csv(VISIBLE_MARKET)
    if cleaning is None:
        return {"bad_observation_handling_rate": 0.0, "valid_retention_rate": 0.0, "unit_normalization_rate": 0.0, "duplicate_handling_rate": 0.0, "missing_handling_rate": 0.0}
    c = cleaning.copy()
    c["action"] = c["action"].astype(str).str.lower()
    joined = labels.merge(c[["obs_id", "action", "normalized_quote"]], on="obs_id", how="left")
    bad = joined[joined["genuinely_bad"].astype(bool)]
    handled = bad["action"].isin(["correct", "downweight", "exclude"])
    unit = joined[joined["issue"].isin(["rate_unit_error", "price_unit_error"])]
    unit_ok = unit["action"].eq("correct") & pd.to_numeric(unit["normalized_quote"], errors="coerce").notna()
    dup = joined[joined["issue"].eq("duplicate_observation")]
    dup_ok = dup["action"].isin(["downweight", "exclude"])
    miss = joined[joined["issue"].eq("missing_quote")]
    miss_ok = miss["action"].eq("exclude")
    labeled_ids = set(labels[labels["genuinely_bad"].astype(bool)]["obs_id"])
    good_ids = set(visible["obs_id"]) - labeled_ids
    good = c[c["obs_id"].isin(good_ids)]
    valid_kept = good["action"].isin(["keep", "correct", "downweight"])
    unusual = joined[joined["issue"].eq("unusual_but_valid")]
    unusual_kept = unusual["action"].isin(["keep", "correct", "downweight"])
    return {
        "bad_observation_handling_rate": float(handled.mean()) if len(handled) else 0.0,
        "valid_retention_rate": float(valid_kept.mean()) if len(valid_kept) else 0.0,
        "unusual_valid_retention_rate": float(unusual_kept.mean()) if len(unusual_kept) else 0.0,
        "unit_normalization_rate": float(unit_ok.mean()) if len(unit_ok) else 0.0,
        "duplicate_handling_rate": float(dup_ok.mean()) if len(dup_ok) else 0.0,
        "missing_handling_rate": float(miss_ok.mean()) if len(miss_ok) else 0.0,
    }


def static_scan(project: Path) -> list[str]:
    findings: list[str] = []
    forbidden = {
        "evaluator/ground_truth": "explicit ground-truth path",
        "evaluator/hidden_tests": "explicit hidden-test path",
        "evaluator/hidden_scenarios": "explicit hidden-scenario path",
        "true_curve_parameters.json": "hidden parameter filename",
        "negative_front_end": "hidden scenario identifier",
        "multiple_large_outliers": "hidden scenario identifier",
    }
    truth = pd.read_csv(GROUND_ROOT / "main_curve.csv")["zero_rate"].head(20)
    truth_snippets = [f"{v:.10f}" for v in truth]
    for p in project.rglob("*"):
        if not p.is_file() or p.stat().st_size > 2_000_000 or any(part in {".git", "__pycache__", ".venv"} for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        rel = p.relative_to(project).as_posix()
        for token, meaning in forbidden.items():
            if token in text:
                findings.append(f"{rel}: {meaning}")
        if sum(s in text for s in truth_snippets) >= 8:
            findings.append(f"{rel}: unexplained array closely matches hidden truth")
        for model in ("astra", "sol", "opus", "fable"):
            if f"results/{model}" in text or f"results\\{model}" in text:
                findings.append(f"{rel}: reference to another result directory")
    return sorted(set(findings))


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def output_digest(output: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in ("curves/curve.csv", "diagnostics/cleaning.csv", "diagnostics/repricing.csv", "diagnostics/risk.csv", "diagnostics/model_comparison.json", "diagnostics/sensitivity.json"):
        p = output / rel
        if p.is_file():
            result[rel] = file_digest(p)
    return result


def report_score(project: Path, output: Path, state: EvaluationState) -> float:
    candidates = [output / "reports" / "research_report.html"]
    report = next((p for p in candidates if p.is_file() and p.stat().st_size > 500), None)
    if report is None:
        state.check("report.exists", False, "research_report.html missing or empty")
        return 0.0
    text = re.sub(r"<[^>]+>", " ", report.read_text(encoding="utf-8", errors="ignore")).lower()
    sections = {
        "executive summary": ("executive summary",),
        "methodology": ("methodology",),
        "data quality": ("data quality", "data-quality"),
        "model comparison": ("model comparison", "baseline"),
        "sensitivity analysis": ("sensitivity",),
        "validation": ("validation", "repricing"),
        "charts": ("curve", "forward"),
        "limitations": ("limitations", "model risk"),
        "recommended next steps": ("next steps", "recommendation"),
    }
    found = sum(any(term in text for term in terms) for terms in sections.values())
    charts = list((output / "charts").glob("*.png")) + list((output / "charts").glob("*.svg"))
    charts_ok = len(charts) >= 4 and all(p.stat().st_size > 100 for p in charts)
    state.check("report.exists", True, str(report))
    state.check("report.sections", found == len(sections), f"{found}/{len(sections)} required section concepts found")
    state.check("report.charts", charts_ok, f"{len(charts)} non-empty chart files")
    return 4.0 * found / len(sections) + (1.0 if charts_ok else min(0.5, len(charts) / 8.0))


def evaluate_candidate(candidate_path: str | Path, external_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    state = EvaluationState()
    candidate = Path(candidate_path).expanduser().resolve()
    started = time.monotonic()
    if not candidate.is_dir():
        return zero_result(candidate, "candidate path is not a directory")
    project_src = locate_project(candidate)
    if project_src is None:
        return zero_result(candidate, "could not locate one project with pyproject.toml and src/")
    with tempfile.TemporaryDirectory(prefix="quant-benchmark-eval-") as temp_name:
        temp = Path(temp_name)
        project = temp / "candidate"
        shutil.copytree(project_src, project, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "outputs"))
        main_out = temp / "main_output"
        repeat_out = temp / "repeat_output"

        import_run = run_command([sys.executable, "-c", "import quantcurve; print(quantcurve.__name__)"], project, 30)
        import_ok = state.check("software.import", import_run["returncode"] == 0, import_run["stderr"] or import_run["stdout"])
        test_run = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], project, 180)
        tests_ok = state.check("software.candidate_tests", test_run["returncode"] == 0, test_run["stderr"] or test_run["stdout"])
        cli_run = run_cli(project, VISIBLE_MARKET, main_out)
        cli_ok = state.check("software.cli", cli_run["returncode"] == 0, cli_run["stderr"] or cli_run["stdout"])

        curve_frame, curve_msg = safe_read_csv(main_out / "curves" / "curve.csv", CURVE_COLUMNS)
        curve: pd.DataFrame | None = normalize_curve(curve_frame) if curve_frame is not None else None
        cleaning, clean_msg = safe_read_csv(main_out / "diagnostics" / "cleaning.csv", CLEAN_COLUMNS)
        risk, risk_msg = safe_read_csv(main_out / "diagnostics" / "risk.csv", RISK_COLUMNS)
        repricing, repricing_msg = safe_read_csv(main_out / "diagnostics" / "repricing.csv", ("instrument_id", "instrument_type", "market_quote", "model_quote", "residual", "weight"))
        model_cmp_path = main_out / "diagnostics" / "model_comparison.json"
        sensitivity_path = main_out / "diagnostics" / "sensitivity.json"
        state.check("outputs.curve", curve is not None, curve_msg)
        state.check("outputs.cleaning", cleaning is not None, clean_msg)
        state.check("outputs.repricing", repricing is not None, repricing_msg)
        state.check("outputs.risk", risk is not None, risk_msg)
        numeric_tables_ok = False
        if cleaning is not None and repricing is not None and risk is not None:
            usable_clean = cleaning[cleaning["action"].astype(str).str.lower().ne("exclude")]
            usable_reprice = repricing[pd.to_numeric(repricing["weight"], errors="coerce") > 0]
            numeric_tables_ok = bool(
                len(usable_clean) >= 20
                and pd.to_numeric(usable_clean["normalized_quote"], errors="coerce").notna().all()
                and len(usable_reprice) >= 20
                and pd.to_numeric(usable_reprice["model_quote"], errors="coerce").notna().all()
                and len(risk) >= 10
                and np.isfinite(risk[list(RISK_COLUMNS[1:])].apply(pd.to_numeric, errors="coerce").to_numpy()).all()
            )
        state.check("outputs.numeric_tables", numeric_tables_ok, "cleaning, repricing, and risk tables contain finite usable values")

        numeric_score = 0.0
        quantitative_score = 0.0
        main_metrics: dict[str, float] = {}
        if curve is not None and len(curve):
            vals = curve[list(CURVE_COLUMNS)].to_numpy(float)
            finite_ok = np.isfinite(vals).all()
            positive_ok = finite_ok and bool((curve["discount_factor"] > 0).all())
            coverage_ok = len(curve) >= 361 and curve["maturity_years"].iloc[0] <= 1 / 12 + 1e-5 and curve["maturity_years"].iloc[-1] >= 30.0 - 1e-5
            ordered_ok = bool(np.all(np.diff(curve["maturity_years"]) > 0))
            expected_df = np.exp(-curve["zero_rate"] * curve["maturity_years"])
            df_consistency = float(np.max(np.abs(expected_df - curve["discount_factor"]))) if finite_ok else float("inf")
            calc_fwd = np.gradient(-np.log(curve["discount_factor"]), curve["maturity_years"], edge_order=1) if positive_ok and ordered_ok else np.full(len(curve), np.nan)
            fwd_consistency = rmse(calc_fwd - curve["forward_rate"].to_numpy(float))
            jumps = float(np.max(np.abs(np.diff(curve["zero_rate"])))) if len(curve) > 1 else float("inf")
            state.check("math.finite_outputs", finite_ok, "all curve values finite")
            state.check("math.positive_discount_factors", positive_ok, "all discount factors strictly positive")
            state.check("math.grid_coverage", coverage_ok, f"rows={len(curve)}, range={curve['maturity_years'].iloc[0]:.6g}-{curve['maturity_years'].iloc[-1]:.6g}")
            state.check("math.interpolation_behavior", ordered_ok and jumps < 0.02, f"ordered={ordered_ok}, max zero-rate jump={jumps:.6g}")
            state.check("math.extrapolation_behavior", coverage_ok and abs(curve["zero_rate"].iloc[-1]) < 0.25, "30Y finite and economically bounded")
            state.check("math.zero_discount_consistency", df_consistency < 2e-8, f"max abs error={df_consistency:.3g}")
            state.check("math.forward_discount_consistency", fwd_consistency < 8e-4, f"RMSE={fwd_consistency:.3g}")
            numeric_score += 3.0 if finite_ok else 0.0
            numeric_score += 3.0 if positive_ok else 0.0
            numeric_score += 4.0 * bounded_score(df_consistency, 2e-8, 2e-4)
            numeric_score += 4.0 * bounded_score(fwd_consistency, 1e-4, 4e-3)
            numeric_score += 3.0 * (sum((coverage_ok, ordered_ok, jumps < 0.02)) / 3.0)
            truth = pd.read_csv(GROUND_ROOT / "main_curve.csv")
            holdout = pd.read_csv(GROUND_ROOT / "holdout_instruments.csv")
            main_metrics = curve_metrics(curve, truth, holdout)
            state.diagnostics.update(main_metrics)
            repricing_quality = bounded_score(main_metrics["hidden_instrument_normalized_rmse"], 0.35, 8.0)
            numeric_score += 5.0 * repricing_quality
            state.check("math.hidden_instrument_repricing", main_metrics["hidden_instrument_normalized_rmse"] < 3.0, f"normalized RMSE={main_metrics['hidden_instrument_normalized_rmse']:.4g}")
            quantitative_score += 7.0 * bounded_score(main_metrics["zero_rate_rmse_bps"], 1.2, 16.0)
            quantitative_score += 3.0 * bounded_score(main_metrics["weighted_zero_rate_rmse_bps"], 1.0, 12.0)
            quantitative_score += 4.0 * bounded_score(main_metrics["forward_rate_rmse_bps"], 6.0, 80.0)
            quantitative_score += 4.0 * bounded_score(main_metrics["hidden_instrument_normalized_rmse"], 0.35, 8.0)
            try:
                model_cmp = json.loads(model_cmp_path.read_text(encoding="utf-8"))
                model_cmp_ok = all(k in model_cmp for k in ("baseline", "advanced", "selected_model", "selection_rationale"))
            except Exception:
                model_cmp_ok = False
            try:
                sensitivity = json.loads(sensitivity_path.read_text(encoding="utf-8"))
                sensitivity_ok = isinstance(sensitivity, dict) and len(sensitivity) >= 3
            except Exception:
                sensitivity_ok = False
            quantitative_score += 1.0 if model_cmp_ok else 0.0
            quantitative_score += 1.0 if sensitivity_ok and main_metrics["forward_roughness"] < 0.002 else 0.0
            state.check("quant.model_comparison", model_cmp_ok, str(model_cmp_path))
            state.check("quant.sensitivity_analysis", sensitivity_ok, str(sensitivity_path))
            if risk is not None:
                all_truth = pd.read_csv(GROUND_ROOT / "all_instruments_truth.csv")
                risk_rel, key_rel, risk_n = risk_agreement(curve, risk, all_truth)
                state.diagnostics.update({"dv01_median_relative_error": risk_rel, "key_rate_sum_median_relative_error": key_rel, "risk_instruments_checked": risk_n})
                dv_ok = risk_n >= 10 and risk_rel < 0.08
                key_ok = risk_n >= 10 and key_rel < 0.35
                state.check("math.dv01_finite_difference", dv_ok, f"n={risk_n}, median relative error={risk_rel:.4g}")
                state.check("math.key_rate_consistency", key_ok, f"median relative error={key_rel:.4g}")
                numeric_score += 4.0 * bounded_score(risk_rel, 0.02, 0.5) if risk_n >= 10 else 0.0
                numeric_score += 2.0 * bounded_score(key_rel, 0.12, 1.0) if risk_n >= 10 else 0.0
            else:
                state.check("math.dv01_finite_difference", False, risk_msg)
                state.check("math.key_rate_consistency", False, risk_msg)

        repeat_run = run_cli(project, VISIBLE_MARKET, repeat_out) if cli_ok else {"returncode": 1}
        deterministic = cli_ok and repeat_run["returncode"] == 0 and output_digest(main_out) == output_digest(repeat_out) and bool(output_digest(main_out))
        state.check("software.deterministic", deterministic, f"first={len(output_digest(main_out))} artifacts, repeat={len(output_digest(repeat_out))}")

        scenario_metrics: dict[str, Any] = {}
        scenario_valid = 0
        scenario_quality: list[float] = []
        negative_ok = False
        sparse_ok = False
        for scenario in sorted(SCENARIO_ROOT.glob("s*")):
            sid = scenario.name
            out = temp / f"scenario_{sid}"
            run = run_cli(project, scenario / "market_data.csv", out, 180) if import_ok else {"returncode": 1, "stderr": "import failed"}
            cf, msg = safe_read_csv(out / "curves" / "curve.csv", CURVE_COLUMNS) if run["returncode"] == 0 else (None, run.get("stderr", "CLI failed"))
            if cf is None:
                scenario_metrics[sid] = {"valid": False, "error": msg}
                scenario_quality.append(0.0)
                continue
            scurve = normalize_curve(cf)
            valid = bool(len(scurve) >= 361 and np.isfinite(scurve[list(CURVE_COLUMNS)].to_numpy(float)).all() and (scurve["discount_factor"] > 0).all())
            truth = pd.read_csv(scenario / "truth_curve.csv")
            inst = pd.read_csv(scenario / "instrument_truth.csv")
            metrics = curve_metrics(scurve, truth, inst)
            quality = 0.65 * bounded_score(metrics["zero_rate_rmse_bps"], 2.0, 35.0) + 0.35 * bounded_score(metrics["forward_rate_rmse_bps"], 10.0, 150.0)
            quality = quality if valid else 0.0
            scenario_quality.append(quality)
            scenario_valid += int(valid)
            scenario_metrics[sid] = {"valid": valid, **metrics}
            if sid == "s01":
                front = scurve[scurve["maturity_years"] <= 1.0]
                negative_ok = bool(valid and len(front) > 0 and float(front["zero_rate"].min()) < -1e-4)
            if sid == "s04":
                sparse_ok = bool(valid and metrics["long_end_zero_rmse_bps"] < 35.0)
        robustness_score = 15.0 * float(np.mean(scenario_quality)) if scenario_quality else 0.0
        state.diagnostics["hidden_scenarios"] = scenario_metrics
        state.check("math.negative_rate_handling", negative_ok, "front-end negative curve recovered with positive discount factors")
        state.check("math.numerical_stability", scenario_valid == len(scenario_quality), f"{scenario_valid}/{len(scenario_quality)} scenarios produced valid curves")
        state.check("math.sparse_curve_behavior", sparse_ok, "sparse long-end scenario remained bounded")
        numeric_score += 2.0 if negative_ok else 0.0

        dq = data_quality_metrics(cleaning)
        state.diagnostics["data_quality"] = dq
        data_quality_score = (
            3.0 * dq["bad_observation_handling_rate"]
            + 1.5 * dq["valid_retention_rate"]
            + 1.0 * dq.get("unusual_valid_retention_rate", 0.0)
            + 2.0 * dq["unit_normalization_rate"]
            + 1.5 * dq["duplicate_handling_rate"]
            + 1.0 * dq["missing_handling_rate"]
        )
        state.check("data.unit_handling", dq["unit_normalization_rate"] >= 0.75, f"rate={dq['unit_normalization_rate']:.3f}")
        state.check("data.duplicate_handling", dq["duplicate_handling_rate"] >= 0.75, f"rate={dq['duplicate_handling_rate']:.3f}")
        state.check("data.missing_handling", dq["missing_handling_rate"] >= 0.9, f"rate={dq['missing_handling_rate']:.3f}")
        # Issue-specific outcomes are intentionally tolerant of downweight versus exclusion.
        labels = pd.read_csv(GROUND_ROOT / "corruption_labels.csv")
        if cleaning is not None:
            action = labels.merge(cleaning[["obs_id", "action"]], on="obs_id", how="left")
            normalized_action = action["action"].astype(str).str.lower()
            extreme_ok = normalized_action[action["issue"].eq("extreme_outlier")].isin(["exclude", "downweight"]).mean()
            moderate_ok = normalized_action[action["issue"].eq("moderate_outlier")].isin(["exclude", "downweight"]).mean()
            stale_ok = normalized_action[action["issue"].eq("stale_timestamp")].isin(["exclude", "downweight"]).mean()
            inversion_ok = normalized_action[action["issue"].eq("bid_ask_inversion")].isin(["exclude", "correct"]).mean()
        else:
            extreme_ok = moderate_ok = stale_ok = inversion_ok = 0.0
        state.check("data.extreme_outliers", extreme_ok >= 0.8, f"handled={extreme_ok:.3f}")
        state.check("data.moderate_outliers", moderate_ok >= 0.5, f"handled={moderate_ok:.3f}")
        state.check("data.stale_observations", stale_ok >= 0.6, f"handled={stale_ok:.3f}")
        state.check("data.bid_ask_inversions", inversion_ok >= 0.75, f"handled={inversion_ok:.3f}")
        state.check("data.valid_observation_retention", dq["valid_retention_rate"] >= 0.85, f"retained={dq['valid_retention_rate']:.3f}")
        state.check("data.unusual_valid_retention", dq.get("unusual_valid_retention_rate", 0.0) >= 0.65, f"retained={dq.get('unusual_valid_retention_rate', 0.0):.3f}")

        findings = static_scan(project)
        state.warnings.extend(f"anti-cheating review: {item}" for item in findings)
        no_external_paths = not any("/Users/" in p.read_text(encoding="utf-8", errors="ignore") for p in project.rglob("*.py") if p.is_file())
        software_score = (
            (2.0 if import_ok else 0.0)
            + (2.0 if tests_ok else 0.0)
            + (3.0 if cli_ok else 0.0)
            + (3.0 if deterministic else 0.0)
            + (2.0 if no_external_paths and not findings else (1.0 if no_external_paths else 0.0))
            + (1.0 if (project / "src" / "quantcurve").is_dir() else 0.0)
            + (2.0 if scenario_valid >= 8 else scenario_valid / 4.0)
        )
        state.check("software.no_personal_paths", no_external_paths, "Python sources contain no /Users/ dependency")
        state.check("integrity.anti_cheating_scan", not findings, f"{len(findings)} suspicious findings; warnings require manual review")

        rep_score = report_score(project_src, main_out, state)
        summary_path = project_src / "benchmark_summary.json"
        summary: dict[str, Any] = {}
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception as exc:
                state.warnings.append(f"benchmark_summary.json parse error: {exc}")
        required_summary = {"model_name", "reasoning_effort", "start_time", "finish_time", "wall_time_seconds", "test_runs", "failed_test_runs", "corrective_iterations", "tests_passed", "tests_failed", "files_created", "unresolved_limitations"}
        summary_ok = required_summary.issubset(summary)
        readme_ok = (project_src / "README.md").is_file() and (project_src / "README.md").stat().st_size > 500
        risks_ok = (project_src / "MODEL_RISKS.md").is_file() and (project_src / "MODEL_RISKS.md").stat().st_size > 300
        required_outputs = all((main_out / rel).is_file() for rel in ("curves/curve.csv", "diagnostics/cleaning.csv", "diagnostics/repricing.csv", "diagnostics/risk.csv", "diagnostics/model_comparison.json", "diagnostics/sensitivity.json"))
        integrity_score = (2.0 if required_outputs else 0.0) + (1.0 if summary_ok else 0.0) + (1.0 if readme_ok else 0.0) + (1.0 if risks_ok else 0.0)
        state.check("integrity.summary_schema", summary_ok, f"missing={sorted(required_summary - set(summary))}")
        state.check("integrity.documentation", readme_ok and risks_ok, f"README={readme_ok}, MODEL_RISKS={risks_ok}")
        state.check("integrity.required_outputs", required_outputs, "fresh workflow output completeness")

        categories = {
            "numerical_correctness": round(min(30.0, numeric_score), 3),
            "quantitative_model_quality": round(min(20.0, quantitative_score), 3),
            "hidden_scenario_robustness": round(min(15.0, robustness_score), 3),
            "software_engineering_reproducibility": round(min(15.0, software_score), 3),
            "data_quality_handling": round(min(10.0, data_quality_score), 3),
            "report_completeness": round(min(5.0, rep_score), 3),
            "completion_integrity": round(min(5.0, integrity_score), 3),
        }
        total = round(sum(categories.values()), 3)
        efficiency = build_efficiency(total, summary, external_metadata or {}, time.monotonic() - started)
        return {
            "benchmark_version": "1.0.0",
            "candidate_path": str(candidate),
            "total_score": total,
            "category_scores": categories,
            "hidden_tests": {
                "passed": [t.identifier for t in state.tests if t.passed],
                "failed": [t.identifier for t in state.tests if not t.passed],
                "details": [{"id": t.identifier, "passed": t.passed, "detail": t.detail} for t in state.tests],
            },
            "quantitative_diagnostics": state.diagnostics,
            "warnings": state.warnings,
            "failed_test_identifiers": [t.identifier for t in state.tests if not t.passed],
            "efficiency_metrics": efficiency,
            "evaluator_wall_time_seconds": round(time.monotonic() - started, 3),
        }


def build_efficiency(score: float, summary: dict[str, Any], external: dict[str, Any], evaluator_time: float) -> dict[str, Any]:
    merged = {**summary, **external}
    wall = merged.get("wall_time_seconds")
    cost = merged.get("estimated_usd_cost")
    try:
        per_minute = score / (float(wall) / 60.0) if float(wall) > 0 else None
    except (TypeError, ValueError):
        per_minute = None
    try:
        per_dollar = score / float(cost) if float(cost) > 0 else None
    except (TypeError, ValueError):
        per_dollar = None
    return {
        "model": merged.get("model_name") or merged.get("model"),
        "reasoning_effort": merged.get("reasoning_effort"),
        "wall_clock_duration_seconds": wall,
        "test_run_count": merged.get("test_runs"),
        "failed_test_run_count": merged.get("failed_test_runs"),
        "corrective_iterations": merged.get("corrective_iterations"),
        "human_interventions": merged.get("human_interventions"),
        "quota_percentage_consumed": merged.get("quota_percentage_consumed"),
        "credits_consumed": merged.get("credits_consumed"),
        "estimated_usd_cost": cost,
        "capability_score_per_minute": per_minute,
        "capability_score_per_dollar": per_dollar,
        "evaluator_duration_seconds": round(evaluator_time, 3),
    }


def zero_result(candidate: Path, reason: str) -> dict[str, Any]:
    categories = {
        "numerical_correctness": 0.0, "quantitative_model_quality": 0.0,
        "hidden_scenario_robustness": 0.0, "software_engineering_reproducibility": 0.0,
        "data_quality_handling": 0.0, "report_completeness": 0.0,
        "completion_integrity": 0.0,
    }
    return {
        "benchmark_version": "1.0.0", "candidate_path": str(candidate),
        "total_score": 0.0, "category_scores": categories,
        "hidden_tests": {"passed": [], "failed": ["setup.candidate_project"], "details": [{"id": "setup.candidate_project", "passed": False, "detail": reason}]},
        "quantitative_diagnostics": {}, "warnings": [reason],
        "failed_test_identifiers": ["setup.candidate_project"],
        "efficiency_metrics": {}, "evaluator_wall_time_seconds": 0.0,
    }
