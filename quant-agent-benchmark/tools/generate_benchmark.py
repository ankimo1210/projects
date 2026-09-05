#!/usr/bin/env python3
"""Deterministically generate the quant-agent benchmark data and manifests.

Run with Python 3.12 from any working directory.  The script only writes below
its own benchmark root. Static source files are versioned alongside this file;
this generator rebuilds all synthetic observations, hidden truth, scenarios,
and cryptographic manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd


VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
MASTER_SEED = 20260905
VALUATION_DATE = date(2026, 1, 15)
SOURCE_DATE_EPOCH = "2026-09-05T00:00:00Z"
ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input"
EVALUATOR = ROOT / "evaluator"
MARKET = INPUT / "market_data"
GROUND = EVALUATOR / "ground_truth"
SCENARIOS = EVALUATOR / "hidden_scenarios"

VISIBLE_COLUMNS = [
    "obs_id", "instrument_id", "source", "timestamp", "currency",
    "instrument_type", "maturity_date", "maturity_years", "start_years",
    "coupon_rate", "payment_frequency", "day_count", "quote_type",
    "quote_value", "quote_unit", "bid", "ask", "liquidity_score",
    "settlement_days",
]


@dataclass(frozen=True)
class CurveSpec:
    level: float = 0.0210
    slope: float = -0.0100
    curvature: float = 0.0080
    tau1: float = 0.85
    tau2: float = 3.2
    long_bend: float = -0.0030
    bump7: float = 0.0015
    bump18: float = -0.0010


def true_zero(t: np.ndarray | float, spec: CurveSpec) -> np.ndarray:
    """Continuously compounded annual zero rate."""
    x = np.asarray(t, dtype=float)
    x_safe = np.maximum(x, 1.0e-10)
    z = (
        spec.level
        + spec.slope * np.exp(-x_safe / spec.tau1)
        + spec.curvature * (x_safe / spec.tau2) * np.exp(-x_safe / spec.tau2)
        + spec.long_bend * (x_safe / 9.0) * np.exp(-x_safe / 9.0)
        + spec.bump7 * np.exp(-((x_safe - 7.0) / 1.25) ** 2)
        + spec.bump18 * np.exp(-((x_safe - 18.0) / 2.7) ** 2)
    )
    return z


def discount(t: np.ndarray | float, spec: CurveSpec) -> np.ndarray:
    x = np.asarray(t, dtype=float)
    return np.exp(-true_zero(x, spec) * x)


def instantaneous_forward(t: np.ndarray | float, spec: CurveSpec) -> np.ndarray:
    x = np.asarray(t, dtype=float)
    h = 1.0e-4
    lo = np.maximum(x - h, 1.0e-8)
    hi = x + h
    return (true_zero(hi, spec) * hi - true_zero(lo, spec) * lo) / (hi - lo)


def payment_times(maturity: float, frequency: int) -> np.ndarray:
    n = max(1, int(round(maturity * frequency)))
    return np.arange(1, n + 1, dtype=float) / frequency


def par_rate(maturity: float, frequency: int, spec: CurveSpec) -> float:
    times = payment_times(maturity, frequency)
    alpha = 1.0 / frequency
    return float((1.0 - discount(maturity, spec)) / (alpha * discount(times, spec).sum()))


def deposit_rate(maturity: float, spec: CurveSpec) -> float:
    return float((1.0 / discount(maturity, spec) - 1.0) / maturity)


def bond_price(maturity: float, frequency: int, coupon_rate: float, spec: CurveSpec) -> float:
    times = payment_times(maturity, frequency)
    coupons = np.full(times.shape, 100.0 * coupon_rate / frequency)
    coupons[-1] += 100.0
    return float(np.dot(coupons, discount(times, spec)))


def theoretical_quote(row: dict, spec: CurveSpec) -> float:
    maturity = float(row["maturity_years"])
    kind = row["instrument_type"]
    if kind == "deposit":
        return 100.0 * deposit_rate(maturity, spec)
    if kind == "ois_swap":
        return 100.0 * par_rate(maturity, int(row["payment_frequency"]), spec)
    if kind == "bond":
        return bond_price(maturity, int(row["payment_frequency"]), float(row["coupon_rate"]), spec)
    raise ValueError(f"unknown instrument type: {kind}")


def maturity_date(years: float) -> str:
    return (VALUATION_DATE + timedelta(days=round(365.0 * years))).isoformat()


def make_universe(rng: np.random.Generator, n: int = 160) -> list[dict]:
    """Create a deterministic mixed-instrument universe with clustered tenors."""
    n_deposits = 22 if n >= 150 else 14
    n_swaps = 82 if n >= 150 else 50
    deposit_tenors = np.resize(np.array([1 / 12, 1 / 12, 0.25, 0.25, 0.5, 0.5, 0.75, 1.0]), n_deposits)
    swap_base = np.array([
        1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30
    ], dtype=float)
    swap_tenors = np.resize(swap_base, n_swaps)
    bond_tenors = np.linspace(1.4, 29.7, n - len(deposit_tenors) - len(swap_tenors))
    bond_tenors += rng.normal(0.0, 0.08, size=len(bond_tenors))
    rows: list[dict] = []
    idx = 0
    for kind, tenors in (("deposit", deposit_tenors), ("ois_swap", swap_tenors), ("bond", bond_tenors)):
        for t in tenors:
            idx += 1
            t = float(max(t, 1 / 12))
            freq = 1 if kind == "deposit" else (1 if kind == "ois_swap" and t <= 2 else 2)
            coupon = float("nan")
            if kind == "bond":
                fair = par_rate(t, freq, CurveSpec())
                coupon = max(-0.0025, fair + rng.normal(0.0, 0.0055))
            quote_type = "simple_rate" if kind == "deposit" else ("par_rate" if kind == "ois_swap" else "clean_price")
            quote_unit = "PERCENT" if kind != "bond" else "PRICE_POINTS"
            rows.append({
                "instrument_id": f"INS{idx:04d}",
                "currency": "USD",
                "instrument_type": kind,
                "maturity_date": maturity_date(t),
                "maturity_years": round(t, 8),
                "start_years": 0.0,
                "coupon_rate": coupon,
                "payment_frequency": freq,
                "day_count": "ACT/365F",
                "quote_type": quote_type,
                "quote_unit": quote_unit,
                "settlement_days": 2,
            })
    return rows


def quote_noise(kind: str, liquidity: float, rng: np.random.Generator) -> float:
    if kind == "bond":
        return float(rng.normal(0.0, 0.018 + 0.055 * (1.0 - liquidity)))
    return float(rng.normal(0.0, 0.0018 + 0.0060 * (1.0 - liquidity)))


def build_observations(
    universe: list[dict],
    spec: CurveSpec,
    rng: np.random.Generator,
    *,
    holdout_ids: set[str] | None = None,
    corruption_profile: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return visible observations, clean truth, and hidden corruption labels."""
    holdout_ids = holdout_ids or set()
    corruption_profile = corruption_profile or {
        "missing": 4, "stale": 5, "inversion": 4, "extreme": 5,
        "moderate": 7, "rate_unit": 4, "price_unit": 3, "valid_unusual": 6,
        "duplicates": 7,
    }
    clean_rows: list[dict] = []
    visible_rows: list[dict] = []
    for i, base in enumerate(universe):
        truth = theoretical_quote(base, spec)
        maturity = float(base["maturity_years"])
        liquidity = float(np.clip(0.97 - 0.018 * maturity + rng.normal(0, 0.08), 0.08, 1.0))
        if maturity > 20:
            liquidity = min(liquidity, float(rng.uniform(0.08, 0.35)))
        spread = (0.025 + 0.12 * (1 - liquidity)) if base["instrument_type"] == "bond" else (0.0015 + 0.012 * (1 - liquidity))
        quote = truth + quote_noise(base["instrument_type"], liquidity, rng)
        obs = dict(base)
        obs.update({
            "obs_id": f"OBS{i + 1:04d}",
            "source": ["VENUE_A", "VENUE_B", "COMPOSITE"][i % 3],
            "timestamp": (datetime(2026, 1, 15, 16, 0, tzinfo=timezone.utc) - timedelta(minutes=int(rng.integers(0, 90)))).isoformat().replace("+00:00", "Z"),
            "quote_value": quote,
            "bid": quote - spread / 2,
            "ask": quote + spread / 2,
            "liquidity_score": liquidity,
        })
        clean = dict(obs)
        clean["true_quote"] = truth
        clean_rows.append(clean)
        if base["instrument_id"] not in holdout_ids:
            visible_rows.append(obs)

    visible = pd.DataFrame(visible_rows)
    labels: list[dict] = []
    available = list(visible.index)
    rng.shuffle(available)
    cursor = 0

    def take(k: int, predicate: Callable[[pd.Series], bool] | None = None) -> list[int]:
        nonlocal cursor
        selected: list[int] = []
        while cursor < len(available) and len(selected) < k:
            j = available[cursor]
            cursor += 1
            if predicate is None or predicate(visible.loc[j]):
                selected.append(j)
        return selected

    def label(j: int, issue: str, bad: bool, severity: str, action: str) -> None:
        labels.append({
            "obs_id": visible.at[j, "obs_id"], "instrument_id": visible.at[j, "instrument_id"],
            "issue": issue, "genuinely_bad": bad, "severity": severity,
            "acceptable_action": action,
        })

    for j in take(corruption_profile.get("missing", 0)):
        visible.at[j, "quote_value"] = np.nan
        label(j, "missing_quote", True, "high", "exclude")
    for j in take(corruption_profile.get("stale", 0)):
        visible.at[j, "timestamp"] = "2026-01-02T15:00:00Z"
        label(j, "stale_timestamp", True, "medium", "downweight_or_exclude")
    for j in take(corruption_profile.get("inversion", 0)):
        bid, ask = visible.at[j, "bid"], visible.at[j, "ask"]
        visible.at[j, "bid"], visible.at[j, "ask"] = ask, bid
        label(j, "bid_ask_inversion", True, "high", "repair_or_exclude")
    for j in take(corruption_profile.get("extreme", 0)):
        delta = 6.0 if visible.at[j, "instrument_type"] == "bond" else 1.7
        visible.at[j, "quote_value"] += delta * (-1 if j % 2 else 1)
        visible.at[j, "bid"] += delta * (-1 if j % 2 else 1)
        visible.at[j, "ask"] += delta * (-1 if j % 2 else 1)
        label(j, "extreme_outlier", True, "critical", "exclude")
    for j in take(corruption_profile.get("moderate", 0)):
        delta = 0.65 if visible.at[j, "instrument_type"] == "bond" else 0.16
        visible.at[j, "quote_value"] += delta * (-1 if j % 2 else 1)
        visible.at[j, "bid"] += delta * (-1 if j % 2 else 1)
        visible.at[j, "ask"] += delta * (-1 if j % 2 else 1)
        label(j, "moderate_outlier", True, "medium", "downweight_or_exclude")
    rate_pred = lambda r: r["instrument_type"] != "bond"
    for j in take(corruption_profile.get("rate_unit", 0), rate_pred):
        for col in ("quote_value", "bid", "ask"):
            visible.at[j, col] /= 100.0
        label(j, "rate_unit_error", True, "critical", "normalize")
    price_pred = lambda r: r["instrument_type"] == "bond"
    for j in take(corruption_profile.get("price_unit", 0), price_pred):
        for col in ("quote_value", "bid", "ask"):
            visible.at[j, col] /= 100.0
        label(j, "price_unit_error", True, "critical", "normalize")
    for j in take(corruption_profile.get("valid_unusual", 0)):
        visible.at[j, "liquidity_score"] = min(float(visible.at[j, "liquidity_score"]), 0.16)
        width = 0.55 if visible.at[j, "instrument_type"] == "bond" else 0.075
        visible.at[j, "bid"] = visible.at[j, "quote_value"] - width / 2
        visible.at[j, "ask"] = visible.at[j, "quote_value"] + width / 2
        label(j, "unusual_but_valid", False, "low", "keep_or_downweight")

    duplicates: list[pd.Series] = []
    dup_candidates = [j for j in visible.index if pd.notna(visible.at[j, "quote_value"])][:corruption_profile.get("duplicates", 0)]
    for k, j in enumerate(dup_candidates, 1):
        dup = visible.loc[j].copy()
        dup["obs_id"] = f"DUP{k:04d}"
        dup["source"] = "BACKUP_FEED"
        dup["timestamp"] = "2026-01-15T14:00:00Z"
        dup["quote_value"] = float(dup["quote_value"]) + (0.03 if dup["instrument_type"] == "bond" else 0.006)
        duplicates.append(dup)
        labels.append({
            "obs_id": dup["obs_id"], "instrument_id": dup["instrument_id"],
            "issue": "duplicate_observation", "genuinely_bad": True,
            "severity": "medium", "acceptable_action": "deduplicate",
        })
    if duplicates:
        visible = pd.concat([visible, pd.DataFrame(duplicates)], ignore_index=True)
    visible = visible[VISIBLE_COLUMNS].sort_values(["maturity_years", "obs_id"], kind="mergesort").reset_index(drop=True)
    clean_df = pd.DataFrame(clean_rows).sort_values("maturity_years", kind="mergesort").reset_index(drop=True)
    labels_df = pd.DataFrame(labels).sort_values("obs_id", kind="mergesort").reset_index(drop=True)
    return visible, clean_df, labels_df


def canonical_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n", float_format="%.10g", na_rep="")


def canonical_json(obj: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_hashes(base: Path, excludes: set[str] | None = None) -> dict[str, str]:
    excludes = excludes or set()
    result: dict[str, str] = {}
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(part in {"__pycache__", ".pytest_cache"} for part in p.parts):
            rel = p.relative_to(base).as_posix()
            if rel not in excludes and not rel.endswith(".pyc"):
                result[rel] = sha256(p)
    return result


def dense_truth(spec: CurveSpec) -> pd.DataFrame:
    t = np.concatenate(([1 / 365], np.linspace(1 / 12, 30.0, 720)))
    return pd.DataFrame({
        "maturity_years": t,
        "zero_rate": true_zero(t, spec),
        "discount_factor": discount(t, spec),
        "instantaneous_forward_rate": instantaneous_forward(t, spec),
    })


def pv_from_row(row: pd.Series | dict, spec: CurveSpec, quoted: float | None = None) -> float:
    kind = row["instrument_type"]
    t = float(row["maturity_years"])
    freq = int(row["payment_frequency"])
    q = float(quoted if quoted is not None else row.get("true_quote", row["quote_value"]))
    if kind == "deposit":
        rate = q / 100.0
        return 1_000_000.0 * (1.0 - (1.0 + rate * t) * float(discount(t, spec)))
    if kind == "ois_swap":
        rate = q / 100.0
        times = payment_times(t, freq)
        annuity = (1.0 / freq) * float(discount(times, spec).sum())
        return 1_000_000.0 * (rate * annuity - (1.0 - float(discount(t, spec))))
    return bond_price(t, freq, float(row["coupon_rate"]), spec) - q


def curve_with_parallel(spec: CurveSpec, bump: float) -> CurveSpec:
    return CurveSpec(**{**spec.__dict__, "level": spec.level + bump})


def risk_truth(clean: pd.DataFrame, spec: CurveSpec) -> pd.DataFrame:
    rows: list[dict] = []
    key_tenors = np.array([2.0, 5.0, 10.0, 30.0])
    for _, row in clean.iterrows():
        quote = float(row["true_quote"])
        up = pv_from_row(row, curve_with_parallel(spec, 1e-4), quote)
        down = pv_from_row(row, curve_with_parallel(spec, -1e-4), quote)
        maturity = float(row["maturity_years"])
        allocation = 1.0 / np.maximum(np.abs(key_tenors - maturity), 0.4) ** 2
        allocation /= allocation.sum()
        dv01 = (down - up) / 2.0
        rows.append({
            "instrument_id": row["instrument_id"],
            "dv01": dv01,
            "key_2y": dv01 * allocation[0],
            "key_5y": dv01 * allocation[1],
            "key_10y": dv01 * allocation[2],
            "key_30y": dv01 * allocation[3],
            "pv_base": pv_from_row(row, spec, quote),
        })
    return pd.DataFrame(rows)


def write_conventions() -> None:
    text = """# Instrument and Curve Conventions

- Valuation date: **2026-01-15**; currency: USD; settlement lag: two calendar days.
- `maturity_years` is the authoritative ACT/365F year fraction used for this synthetic benchmark. `maturity_date` is supplied for auditability.
- Rates in the input use percentage points (`PERCENT`): `2.35` means 2.35%, unless a data-quality defect must be detected and normalized.
- Bond coupons are decimals (`0.025` means 2.5%); prices use points per 100 face value.
- Deposit quotes use simple interest: `D(T) = 1 / (1 + r T)`.
- OIS swaps start at the valuation date. Fixed payments are annual through 2Y and semiannual thereafter. Par rates satisfy `r * sum(alpha_i D(t_i)) = 1 - D(T)`.
- Bonds pay level coupons at `1 / payment_frequency` year intervals, have face value 100, no accrued interest, and repay principal at maturity.
- Candidate zero rates must be continuously compounded annual decimals with `D(T) = exp(-z(T) T)`.
- Forward rates are instantaneous continuously compounded rates, consistent with `-d log(D(T))/dT`.
- Negative zero and forward rates are permitted; discount factors must remain strictly positive.
- DV01 is the central finite-difference change in receiver/fixed-instrument PV for a parallel one-basis-point yield move: `(PV[-1bp] - PV[+1bp]) / 2`. Deposits and swaps use notional 1,000,000; bonds use face 100.
- Key-rate sensitivities use local zero-rate bumps centered at 2Y, 5Y, 10Y, and 30Y; document the bump shape and ensure their aggregate is reasonably consistent with parallel DV01.
"""
    (MARKET / "CONVENTIONS.md").write_text(text, encoding="utf-8", newline="\n")


def generate_main() -> dict[str, int]:
    for generated_dir in (MARKET, GROUND):
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
        generated_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(MASTER_SEED)
    spec = CurveSpec()
    universe = make_universe(rng, 160)
    # Stratified, deterministic hidden holdout across instrument types and maturities.
    holdout_idx = set(np.linspace(3, len(universe) - 3, 24, dtype=int).tolist())
    holdout_ids = {universe[i]["instrument_id"] for i in holdout_idx}
    visible, clean, labels = build_observations(universe, spec, rng, holdout_ids=holdout_ids)
    canonical_csv(visible, MARKET / "market_observations.csv")
    write_conventions()
    canonical_csv(dense_truth(spec), GROUND / "main_curve.csv")
    canonical_csv(clean, GROUND / "all_instruments_truth.csv")
    canonical_csv(clean[clean["instrument_id"].isin(holdout_ids)].copy(), GROUND / "holdout_instruments.csv")
    canonical_csv(labels, GROUND / "corruption_labels.csv")
    canonical_csv(risk_truth(clean, spec), GROUND / "risk_truth.csv")
    canonical_json(spec.__dict__, GROUND / "true_curve_parameters.json")
    return {
        "universe_instruments": len(universe),
        "visible_observations": len(visible),
        "visible_unique_instruments": int(visible["instrument_id"].nunique()),
        "hidden_holdout_instruments": len(holdout_ids),
        "visible_corruption_labels": len(labels),
    }


SCENARIO_SPECS = [
    ("negative_front_end", CurveSpec(level=0.012, slope=-0.020, curvature=0.006, bump7=0.001)),
    ("steep_curve", CurveSpec(level=0.042, slope=-0.037, curvature=0.012, tau1=1.1, long_bend=-0.002)),
    ("strongly_inverted", CurveSpec(level=0.017, slope=0.038, curvature=-0.012, tau1=1.4, long_bend=0.001)),
    ("sparse_long_end", CurveSpec(level=0.025, slope=-0.012, curvature=0.009)),
    ("multiple_large_outliers", CurveSpec(level=0.020, slope=-0.008, curvature=0.007)),
    ("missing_liquid_benchmarks", CurveSpec(level=0.023, slope=-0.014, curvature=0.011)),
    ("duplicated_observations", CurveSpec(level=0.019, slope=-0.009, curvature=0.006)),
    ("unit_errors", CurveSpec(level=0.026, slope=-0.016, curvature=0.009)),
    ("illiquid_long_end", CurveSpec(level=0.022, slope=-0.011, curvature=0.010)),
    ("noisy_but_valid", CurveSpec(level=0.021, slope=-0.010, curvature=0.008, bump7=0.0022)),
]


def generate_scenarios() -> int:
    if SCENARIOS.exists():
        for p in SCENARIOS.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
    SCENARIOS.mkdir(parents=True, exist_ok=True)
    for i, (name, spec) in enumerate(SCENARIO_SPECS, 1):
        rng = np.random.default_rng(MASTER_SEED + 1000 + i)
        universe = make_universe(rng, 96)
        profile = {"missing": 1, "stale": 1, "inversion": 1, "extreme": 1, "moderate": 2, "rate_unit": 1, "price_unit": 1, "valid_unusual": 2, "duplicates": 2}
        if name == "multiple_large_outliers": profile["extreme"] = 10
        if name == "duplicated_observations": profile["duplicates"] = 18
        if name == "unit_errors": profile["rate_unit"], profile["price_unit"] = 10, 8
        if name == "noisy_but_valid":
            profile = {"missing": 0, "stale": 0, "inversion": 0, "extreme": 0, "moderate": 0, "rate_unit": 0, "price_unit": 0, "valid_unusual": 15, "duplicates": 0}
        visible, clean, labels = build_observations(universe, spec, rng, corruption_profile=profile)
        if name == "sparse_long_end":
            visible = visible[~((visible["maturity_years"] > 12) & (np.arange(len(visible)) % 4 != 0))].copy()
        elif name == "missing_liquid_benchmarks":
            anchors = np.array([2.0, 5.0, 10.0, 20.0])
            visible = visible[~visible["maturity_years"].apply(lambda x: np.min(np.abs(anchors - x)) < 0.12)].copy()
        elif name == "illiquid_long_end":
            mask = visible["maturity_years"] > 15
            visible.loc[mask, "liquidity_score"] = np.minimum(visible.loc[mask, "liquidity_score"], 0.08)
            visible.loc[mask, "bid"] -= np.where(visible.loc[mask, "instrument_type"] == "bond", 0.4, 0.05)
            visible.loc[mask, "ask"] += np.where(visible.loc[mask, "instrument_type"] == "bond", 0.4, 0.05)
        elif name == "noisy_but_valid":
            noise = rng.normal(0, 0.025, len(visible))
            rate_mask = visible["instrument_type"] != "bond"
            visible.loc[rate_mask, "quote_value"] += noise[rate_mask]
            visible.loc[~rate_mask, "quote_value"] += 8 * noise[~rate_mask]
        scenario_dir = SCENARIOS / f"s{i:02d}"
        canonical_csv(visible[VISIBLE_COLUMNS], scenario_dir / "market_data.csv")
        canonical_csv(dense_truth(spec), scenario_dir / "truth_curve.csv")
        canonical_csv(clean, scenario_dir / "instrument_truth.csv")
        canonical_csv(labels, scenario_dir / "corruption_labels.csv")
        canonical_json({"scenario_id": f"s{i:02d}", "scenario_name": name, "seed": MASTER_SEED + 1000 + i}, scenario_dir / "metadata.json")
    return len(SCENARIO_SPECS)


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("numpy", "pandas", "scipy", "matplotlib"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def write_manifests(stats: dict[str, int], scenario_count: int) -> None:
    public_hashes = file_hashes(INPUT, {"MANIFEST.json"})
    public_manifest = {
        "benchmark_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "valuation_date": VALUATION_DATE.isoformat(),
        "required_python": ">=3.12,<3.13",
        "dataset_files": ["market_data/market_observations.csv", "market_data/CONVENTIONS.md"],
        "dataset_summary": stats,
        "public_file_hashes": public_hashes,
    }
    canonical_json(public_manifest, INPUT / "MANIFEST.json")
    evaluator_hashes = file_hashes(EVALUATOR, {"MANIFEST.json", "validation_results.json"})
    evaluator_manifest = {
        "benchmark_version": VERSION,
        "evaluator_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "generation_timestamp_utc": SOURCE_DATE_EPOCH,
        "generation_timestamp_policy": "fixed SOURCE_DATE_EPOCH for byte-identical rebuilds",
        "master_random_seed": MASTER_SEED,
        "scenario_seeds": {f"s{i:02d}": MASTER_SEED + 1000 + i for i in range(1, scenario_count + 1)},
        "python_required": "3.12",
        "python_used": platform.python_version(),
        "package_versions": package_versions(),
        "dataset_summary": stats,
        "hidden_scenario_count": scenario_count,
        "evaluator_file_hashes": evaluator_hashes,
        "reference_solution_hash": hashlib.sha256("".join(v for k, v in evaluator_hashes.items() if k.startswith("reference_solution/")).encode()).hexdigest(),
    }
    canonical_json(evaluator_manifest, EVALUATOR / "MANIFEST.json")


def verify_within_root(path: Path) -> None:
    path.resolve().relative_to(ROOT.resolve())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-reproducibility", action="store_true", help="Generate twice and compare all generated data bytes")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(f"Python 3.12 required; found {platform.python_version()}")
    for path in (INPUT, MARKET, GROUND, SCENARIOS, *(ROOT / "results" / name for name in ("astra", "sol", "opus", "fable"))):
        verify_within_root(path)
        path.mkdir(parents=True, exist_ok=True)
    stats = generate_main()
    scenario_count = generate_scenarios()
    write_manifests(stats, scenario_count)
    if args.verify_reproducibility:
        tracked = sorted(
            [p for base in (MARKET, GROUND, SCENARIOS) for p in base.rglob("*") if p.is_file()]
            + [INPUT / "MANIFEST.json", EVALUATOR / "MANIFEST.json"]
        )
        before = {p: sha256(p) for p in tracked}
        stats2 = generate_main()
        scenario_count2 = generate_scenarios()
        write_manifests(stats2, scenario_count2)
        after = {p: sha256(p) if p.is_file() else "MISSING" for p in tracked}
        if before != after:
            changed = [str(p.relative_to(ROOT)) for p in tracked if before[p] != after[p]]
            raise SystemExit("non-reproducible generated files: " + ", ".join(changed))
        print(f"Reproducibility verified for {len(tracked)} generated datasets.")
    print(json.dumps({"benchmark_version": VERSION, **stats, "hidden_scenarios": scenario_count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
