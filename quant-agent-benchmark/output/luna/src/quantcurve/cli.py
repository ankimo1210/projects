"""Command-line entry point for the complete zero-curve research workflow."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .curve import (
    calculate_risk,
    cleaning_audit,
    choose_holdout,
    fit_advanced,
    fit_baseline,
    reprice_frame,
    score_model,
    score_segments,
)
from .io import load_market_data, validate_schema
from .reporting import make_charts, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantcurve")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--valuation-date", required=True)
    return parser


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _fit_sensitivity(cleaned: pd.DataFrame, preferred_curve: Any, baseline: Any) -> dict[str, dict[str, Any]]:
    base_grid = preferred_curve.grid()

    def summarize(alternative: Any, interpretation: str) -> dict[str, Any]:
        alt_grid = alternative.grid()
        zero_shift = (alt_grid["zero_rate"].to_numpy() - base_grid["zero_rate"].to_numpy()) * 10000.0
        return {
            "max_abs_zero_shift_bp": float(np.max(np.abs(zero_shift))),
            "zero_30y_shift_bp": float(zero_shift[-1]),
            "max_abs_forward_shift_bp": float(np.max(np.abs((alt_grid["forward_rate"].to_numpy() - base_grid["forward_rate"].to_numpy()) * 10000.0))),
            "interpretation": interpretation,
        }

    results: dict[str, dict[str, Any]] = {}
    midpoint = cleaned.loc[cleaned["action"] != "exclude"].copy()
    midpoint["scenario_quote"] = midpoint["normalized_bid"]
    bid_curve, _ = fit_advanced(midpoint, smoothness=100.0, target_col="scenario_quote", initial=baseline)
    midpoint["scenario_quote"] = midpoint["normalized_ask"]
    ask_curve, _ = fit_advanced(midpoint, smoothness=100.0, target_col="scenario_quote", initial=baseline)
    bid_result = summarize(bid_curve, "Refit every quote at bid; measures the lower market-data edge.")
    ask_result = summarize(ask_curve, "Refit every quote at ask; measures the upper market-data edge.")
    results["bid_ask_midpoint_band"] = {
        "max_abs_zero_shift_bp": float(max(bid_result["max_abs_zero_shift_bp"], ask_result["max_abs_zero_shift_bp"])),
        "zero_30y_shift_bp": float(max(abs(bid_result["zero_30y_shift_bp"]), abs(ask_result["zero_30y_shift_bp"]))),
        "max_abs_forward_shift_bp": float(max(bid_result["max_abs_forward_shift_bp"], ask_result["max_abs_forward_shift_bp"])),
        "bid_zero_30y_shift_bp": bid_result["zero_30y_shift_bp"],
        "ask_zero_30y_shift_bp": ask_result["zero_30y_shift_bp"],
        "interpretation": "Bid/ask envelope refit; large values indicate quote uncertainty rather than model extrapolation alone.",
    }

    liquid = cleaned.loc[(cleaned["action"] != "exclude") & (cleaned["liquidity_score"] >= 0.25)].copy()
    if len(liquid) >= 3:
        liquid_curve, _ = fit_advanced(liquid, smoothness=100.0, initial=baseline)
        results["exclude_low_liquidity"] = summarize(liquid_curve, "Refit after removing observations with liquidity score below 0.25.")
    else:
        results["exclude_low_liquidity"] = {"max_abs_zero_shift_bp": None, "zero_30y_shift_bp": None, "max_abs_forward_shift_bp": None, "interpretation": "Not estimable: fewer than three liquid observations."}

    double_smooth, _ = fit_advanced(cleaned, smoothness=200.0, initial=baseline)
    results["double_smoothing_penalty"] = summarize(double_smooth, "Refit with twice the curvature penalty to test regularisation dependence.")

    no_bonds = cleaned.loc[(cleaned["action"] != "exclude") & (cleaned["instrument_type"] != "bond")].copy()
    if len(no_bonds) >= 3:
        no_bond_curve, _ = fit_advanced(no_bonds, smoothness=100.0, initial=baseline)
        results["remove_bonds"] = summarize(no_bond_curve, "Refit without coupon-bearing bonds to isolate OIS/deposit support.")
    else:
        results["remove_bonds"] = {"max_abs_zero_shift_bp": None, "zero_30y_shift_bp": None, "max_abs_forward_shift_bp": None, "interpretation": "Not estimable: insufficient non-bond observations."}
    return results


def _benchmark_start() -> datetime:
    raw = os.environ.get("QUANTCURVE_BENCHMARK_START_UTC")
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _write_summary(
    project_root: Path,
    start: datetime,
    finish: datetime,
    files_created: list[str],
    comparison: dict[str, Any],
    quality: dict[str, Any],
) -> None:
    unresolved = [
        "Synthetic single-date data do not support historical rolling backtests.",
        "Long-end extrapolation is constant in zero-rate terms beyond the last knot.",
        "Calendar, collateral, accrued-interest, and business-day conventions outside the supplied specification are out of scope.",
    ]
    summary = {
        "schema_version": "1.0",
        "model_name": os.environ.get("QUANTCURVE_MODEL_NAME", "gpt-5.6-luna"),
        "reasoning_effort": "xhigh",
        "start_time": start.isoformat().replace("+00:00", "Z"),
        "finish_time": finish.isoformat().replace("+00:00", "Z"),
        "start_time_utc": start.isoformat().replace("+00:00", "Z"),
        "finish_time_utc": finish.isoformat().replace("+00:00", "Z"),
        "start_epoch_seconds": start.timestamp(),
        "finish_epoch_seconds": finish.timestamp(),
        "wall_time_seconds": (finish - start).total_seconds(),
        "test_runs": int(os.environ.get("QUANTCURVE_TEST_RUNS", "0")),
        "failed_test_runs": int(os.environ.get("QUANTCURVE_FAILED_TEST_RUNS", "0")),
        "test_suite_runs": int(os.environ.get("QUANTCURVE_TEST_RUNS", "0")),
        "failed_test_suite_runs": int(os.environ.get("QUANTCURVE_FAILED_TEST_RUNS", "0")),
        "tests_passed": int(os.environ.get("QUANTCURVE_TESTS_PASSED", "0")),
        "tests_failed": int(os.environ.get("QUANTCURVE_TESTS_FAILED", "0")),
        "final_tests_passed": int(os.environ.get("QUANTCURVE_TESTS_PASSED", "0")),
        "final_tests_failed": int(os.environ.get("QUANTCURVE_TESTS_FAILED", "0")),
        "corrective_iterations": int(os.environ.get("QUANTCURVE_CORRECTIVE_ITERATIONS", "0")),
        "round_name": os.environ.get("QUANTCURVE_ROUND_NAME", "baseline_submission"),
        "time_limit_seconds": None,
        "round_experiments_count": int(os.environ.get("QUANTCURVE_ROUND_EXPERIMENTS", "0")),
        "original_input_hashes_unchanged": None,
        "files_created": files_created,
        "unresolved_limitations": unresolved,
        "quota_percentage_consumed": None,
        "credits_consumed": None,
        "estimated_usd_cost": None,
        "human_interventions": 0,
        "input_tokens": None,
        "cached_input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
        "reported_usd_cost": None,
        "five_hour_quota_before_percent": None,
        "five_hour_quota_after_percent": None,
        "weekly_quota_before_percent": None,
        "weekly_quota_after_percent": None,
        "major_modelling_decisions": [
            "Bootstrap deposits and OIS swaps as a transparent baseline.",
            "Fit a positive-discount-factor, piecewise-linear continuous zero curve using spread/liquidity weights, curvature regularisation, and four robust residual reweighting iterations.",
            "Construct instantaneous forwards analytically within each piecewise-linear zero-rate segment, using deterministic midpoint derivatives at interior knots.",
            "Use whole-maturity clusters near 2Y, 5Y, 10Y, 20Y, and 30Y for visible holdout validation.",
        ],
        "data_quality_summary": quality,
        "model_selection": comparison.get("selection_rationale"),
        "benchmark_integrity_incidents": [],
    }
    _write_json(project_root / "benchmark_summary.json", summary)


def run_workflow(market_data: Path, output_dir: Path, valuation_date: date) -> dict[str, Any]:
    started = _benchmark_start()
    raw = load_market_data(market_data)
    schema_issues = validate_schema(raw)
    fatal = [issue for issue in schema_issues if "no observations" in issue or "missing required" in issue]
    if fatal:
        raise ValueError("unrecoverable input errors: " + "; ".join(fatal))

    cleaned, audit, quality = cleaning_audit(raw, valuation_date)
    usable = cleaned.loc[(cleaned["action"] != "exclude") & cleaned["normalized_quote"].notna()].copy()
    if len(usable) < 3:
        raise ValueError("fewer than three usable observations remain after documented cleaning")
    holdout_ids, holdout_definition = choose_holdout(cleaned)
    train = cleaned.loc[~cleaned["instrument_id"].astype(str).isin(holdout_ids)].copy()
    if train.empty:
        raise ValueError("maturity-aware holdout consumed the full usable dataset")

    baseline_train = fit_baseline(train)
    advanced_train, advanced_meta = fit_advanced(train, smoothness=100.0, initial=baseline_train)
    baseline_train_score = score_model(train, baseline_train)
    baseline_holdout_score = score_model(cleaned, baseline_train, holdout_ids)
    advanced_train_score = score_model(train, advanced_train)
    advanced_holdout_score = score_model(cleaned, advanced_train, holdout_ids)
    comparison: dict[str, Any] = {
        "holdout_definition": holdout_definition,
        "baseline": {"train": baseline_train_score, "holdout": baseline_holdout_score},
        "advanced": {"train": advanced_train_score, "holdout": advanced_holdout_score, "fit_metadata": advanced_meta},
    }
    b_error = baseline_holdout_score.get("weighted_standardized_rmse")
    a_error = advanced_holdout_score.get("weighted_standardized_rmse")
    if a_error is None:
        selected = "baseline"
        rationale = "Advanced holdout score was unavailable; baseline retained as the only validated model."
    elif b_error is None or float(a_error) <= float(b_error) * 1.05:
        selected = "advanced"
        rationale = "Advanced model selected because its whole-maturity holdout standardized RMSE is no worse than 5% above the baseline and it uses the documented bond evidence and robust weighting."
    else:
        selected = "baseline"
        rationale = "Baseline selected because advanced holdout standardized RMSE was materially worse; complexity was not treated as evidence of superiority."
    comparison["model_selected"] = selected
    comparison["selected_model"] = selected
    comparison["selection_rationale"] = rationale
    comparison["adoption_gate"] = {
        "holdout_tolerance": 0.05,
        "definition": "advanced weighted standardized holdout RMSE <= baseline RMSE * 1.05",
        "post_hoc_changed": False,
    }
    comparison["visible_quality_issues"] = schema_issues

    baseline_all = fit_baseline(cleaned)
    advanced_all, advanced_all_meta = fit_advanced(cleaned, smoothness=100.0, initial=baseline_all)
    comparison["final_fit_metadata"] = {"advanced": advanced_all_meta}
    selected_curve = advanced_all if selected == "advanced" else baseline_all
    repricing = reprice_frame(cleaned, selected_curve)
    risk = calculate_risk(cleaned, selected_curve)
    sensitivity = _fit_sensitivity(cleaned, selected_curve, baseline_all)
    curve_grid = selected_curve.grid(start=1.0 / 12.0, end=30.0, count=601)
    comparison["segment_metrics"] = {
        "baseline": {
            "train": score_segments(train, baseline_train),
            "holdout": score_segments(cleaned, baseline_train, holdout_ids),
        },
        "advanced": {
            "train": score_segments(train, advanced_train),
            "holdout": score_segments(cleaned, advanced_train, holdout_ids),
        },
    }

    out = output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    root = out.parent if out.name == "outputs" else out
    curves_dir = out / "curves"
    diagnostics_dir = out / "diagnostics"
    charts_dir = out / "charts"
    curves_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    curve_grid.to_csv(curves_dir / "curve.csv", index=False, float_format="%.12g")
    audit.to_csv(diagnostics_dir / "cleaning.csv", index=False, float_format="%.12g")
    repricing.to_csv(diagnostics_dir / "repricing.csv", index=False, float_format="%.12g")
    risk.to_csv(diagnostics_dir / "risk.csv", index=False, float_format="%.12g")
    segment_rows = []
    for model_name, scopes in comparison["segment_metrics"].items():
        for scope, metrics in scopes.items():
            for segment, values in metrics.items():
                segment_rows.append({"model": model_name, "scope": scope, "segment": segment, **values})
    pd.DataFrame(segment_rows).to_csv(diagnostics_dir / "segment_metrics.csv", index=False, float_format="%.12g")
    _write_json(diagnostics_dir / "model_comparison.json", comparison)
    _write_json(diagnostics_dir / "sensitivity.json", sensitivity)
    _write_json(diagnostics_dir / "data_quality.json", quality)
    chart_files = make_charts(curve_grid, repricing, comparison, charts_dir)
    report_path = root / "reports" / "research_report.html"
    write_report(report_path, charts_dir, quality, comparison, holdout_definition, sensitivity, selected, repricing, risk, curve_grid)
    finish = datetime.now(timezone.utc)
    created = [
        str(path.relative_to(root))
        for path in [curves_dir / "curve.csv", diagnostics_dir / "cleaning.csv", diagnostics_dir / "repricing.csv", diagnostics_dir / "risk.csv", diagnostics_dir / "segment_metrics.csv", diagnostics_dir / "model_comparison.json", diagnostics_dir / "sensitivity.json", diagnostics_dir / "data_quality.json", *[charts_dir / name for name in chart_files], report_path]
    ]
    _write_summary(root, started, finish, created, comparison, quality)
    return {
        "selected_model": selected,
        "quality": quality,
        "comparison": comparison,
        "holdout_definition": holdout_definition,
        "curve": curve_grid,
        "repricing": repricing,
        "risk": risk,
        "sensitivity": sensitivity,
        "report_path": str(report_path),
        "wall_time_seconds": (finish - started).total_seconds(),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":
        return 2
    try:
        valuation_date = date.fromisoformat(args.valuation_date)
        result = run_workflow(args.market_data, args.output_dir, valuation_date)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"quantcurve: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "COMPLETED", "selected_model": result["selected_model"], "report": result["report_path"], "wall_time_seconds": result["wall_time_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
