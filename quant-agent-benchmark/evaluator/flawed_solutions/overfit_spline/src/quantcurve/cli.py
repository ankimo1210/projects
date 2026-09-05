from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

from .variant import VARIANT


def times(t: float, f: int) -> np.ndarray:
    return np.arange(1, max(1, int(round(t * f))) + 1) / f


def clean_data(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    for col in ("quote_value", "bid", "ask", "maturity_years", "coupon_rate", "payment_frequency", "liquidity_score"):
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d["normalized_quote"] = d["quote_value"]
    d["action"] = "keep"
    d["reason"] = "accepted by simple rules"
    d["weight"] = d["liquidity_score"].fillna(0.1).clip(0.05, 1.0)
    missing = d["quote_value"].isna()
    d.loc[missing, ["action", "reason", "weight"]] = ["exclude", "missing", 0.0]
    if VARIANT != "unit_bug":
        spread = (d["ask"] - d["bid"]).abs()
        rate_units = (d["instrument_type"] != "bond") & (d["quote_value"].abs() < 0.15) & (spread < 0.0005)
        price_units = (d["instrument_type"] == "bond") & (d["quote_value"].abs() < 5) & (spread < 0.02)
        unit = rate_units | price_units
        d.loc[unit, "normalized_quote"] *= 100
        d.loc[unit, "action"] = "correct"
        d.loc[unit, "reason"] = "simple unit rescale"
    dup = d.duplicated("instrument_id", keep="first")
    d.loc[dup, ["action", "reason", "weight"]] = ["exclude", "duplicate", 0.0]
    if VARIANT == "overdelete":
        usable = d[~missing]
        for kind, group in usable.groupby("instrument_type"):
            med = group["normalized_quote"].median()
            mad = max(float((group["normalized_quote"] - med).abs().median()), 1e-6)
            bad = (d["instrument_type"] == kind) & ((d["normalized_quote"] - med).abs() > 0.7 * mad)
            d.loc[bad, ["action", "reason", "weight"]] = ["exclude", "aggressive global outlier deletion", 0.0]
    return d


def proxy(row: pd.Series) -> float:
    q, t = float(row["normalized_quote"]), float(row["maturity_years"])
    if row["instrument_type"] == "deposit":
        return np.log1p(q / 100 * t) / t if 1 + q / 100 * t > 0 else 0.0
    if row["instrument_type"] == "ois_swap":
        return q / 100
    return float(row["coupon_rate"]) + (100 - q) / (100 * max(t, 0.25))


def fitted_zero(data: pd.DataFrame, grid: np.ndarray) -> np.ndarray:
    u = data[data["action"] != "exclude"].copy()
    u["proxy"] = u.apply(proxy, axis=1)
    grouped = u.groupby("maturity_years", as_index=False)["proxy"].median().sort_values("maturity_years")
    x, y = grouped["maturity_years"].to_numpy(), grouped["proxy"].to_numpy()
    if len(x) < 2:
        return np.full_like(grid, 0.02)
    if VARIANT == "overfit_spline" and len(x) >= 4:
        z = CubicSpline(x, y, bc_type="not-a-knot", extrapolate=True)(np.clip(grid, x[0], x[-1]))
        return np.clip(z, -0.2, 0.25)
    return np.interp(grid, x, y, left=y[0], right=y[-1])


def curve_discount(grid: np.ndarray, zero: np.ndarray, t: np.ndarray | float, bump: float = 0.0) -> np.ndarray:
    x = np.asarray(t, dtype=float)
    z = np.interp(x, grid, zero, left=zero[0], right=zero[-1]) + bump
    return np.exp(-z * x)


def model_quote(row: pd.Series, grid: np.ndarray, zero: np.ndarray, bump: float = 0.0) -> float:
    t, f = float(row["maturity_years"]), int(row["payment_frequency"])
    if row["instrument_type"] == "deposit":
        return 100 * (1 / float(curve_discount(grid, zero, t, bump)) - 1) / t
    ts = times(t, f)
    dfs = curve_discount(grid, zero, ts, bump)
    if row["instrument_type"] == "ois_swap":
        return 100 * (1 - float(curve_discount(grid, zero, t, bump))) / (dfs.sum() / f)
    cash = np.full(ts.shape, 100 * float(row["coupon_rate"]) / f)
    cash[-1] += 100
    return float(np.dot(cash, dfs))


def pv(row: pd.Series, grid: np.ndarray, zero: np.ndarray, bump: float) -> float:
    q, t, f = float(row["normalized_quote"]), float(row["maturity_years"]), int(row["payment_frequency"])
    if row["instrument_type"] == "deposit":
        return 1e6 * (1 - (1 + q / 100 * t) * float(curve_discount(grid, zero, t, bump)))
    if row["instrument_type"] == "ois_swap":
        ts = times(t, f)
        return 1e6 * ((q / 100) * curve_discount(grid, zero, ts, bump).sum() / f - (1 - float(curve_discount(grid, zero, t, bump))))
    return model_quote(row, grid, zero, bump) - q


def write_svg(path: Path, title: str) -> None:
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240"><rect width="100%" height="100%" fill="white"/><text x="20" y="30">{title}</text><polyline points="20,200 160,120 320,150 480,80 620,100" fill="none" stroke="#1769aa" stroke-width="3"/></svg>\n', encoding="utf-8")


def run(market: Path, output: Path) -> None:
    data = clean_data(market)
    grid = np.linspace(1 / 12, 30, 361)
    zero = fitted_zero(data, grid)
    discount = np.exp(-zero * grid)
    forward = np.gradient(-np.log(discount), grid)
    for sub in ("curves", "diagnostics", "charts", "reports"):
        (output / sub).mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"maturity_years": grid, "zero_rate": zero, "discount_factor": discount, "forward_rate": forward}).to_csv(output / "curves" / "curve.csv", index=False, float_format="%.12g", lineterminator="\n")
    data[["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]].to_csv(output / "diagnostics" / "cleaning.csv", index=False, float_format="%.12g", lineterminator="\n")
    repricing, risks = [], []
    for _, row in data.iterrows():
        usable = row["action"] != "exclude"
        m = model_quote(row, grid, zero) if usable else np.nan
        q = float(row["normalized_quote"]) if pd.notna(row["normalized_quote"]) else np.nan
        repricing.append({"instrument_id": row["instrument_id"], "instrument_type": row["instrument_type"], "market_quote": q, "model_quote": m, "residual": m - q if usable else np.nan, "weight": row["weight"]})
        if usable:
            dv01 = (pv(row, grid, zero, -1e-4) - pv(row, grid, zero, 1e-4)) / 2
            if VARIANT == "bad_dv01":
                dv01 *= -100
            risks.append({"instrument_id": row["instrument_id"], "dv01": dv01, "key_2y": 0.2 * dv01, "key_5y": 0.25 * dv01, "key_10y": 0.3 * dv01, "key_30y": 0.25 * dv01})
    pd.DataFrame(repricing).to_csv(output / "diagnostics" / "repricing.csv", index=False, float_format="%.12g", lineterminator="\n")
    pd.DataFrame(risks).to_csv(output / "diagnostics" / "risk.csv", index=False, float_format="%.12g", lineterminator="\n")
    comparison = {"baseline": {"holdout_normalized_rmse": 5.0}, "advanced": {"holdout_normalized_rmse": 5.0}, "selected_model": "baseline", "selection_rationale": "fixture"}
    (output / "diagnostics" / "model_comparison.json").write_text(json.dumps(comparison, sort_keys=True) + "\n", encoding="utf-8")
    sensitivity = {"plus_10bp": 0.001, "minus_10bp": -0.001, "remove_quotes": 0.0}
    (output / "diagnostics" / "sensitivity.json").write_text(json.dumps(sensitivity, sort_keys=True) + "\n", encoding="utf-8")
    for name in ("curve", "forward", "repricing", "comparison"):
        write_svg(output / "charts" / f"{name}.svg", f"{VARIANT}: {name}")
    report = """<!doctype html><html><body><h1>Research report</h1><h2>Executive summary</h2><p>This deterministic fixture completes the workflow but contains a known quantitative defect and must not be used for decisions.</p><h2>Methodology</h2><p>A simple quote-to-zero proxy and interpolation produce the displayed curve.</p><h2>Data quality findings</h2><p>Basic missing-value, duplicate, and unit checks were attempted.</p><h2>Model comparison</h2><p>A placeholder baseline comparison is present but does not establish superiority.</p><h2>Sensitivity analysis</h2><p>Three compact perturbation checks are recorded.</p><h2>Validation and repricing</h2><p>Residuals are emitted for inspection.</p><h2>Charts</h2><p>Curve, forward, repricing, and comparison charts are included.</p><h2>Limitations</h2><p>The selected fixture defect materially limits the numerical results.</p><h2>Recommended next steps</h2><p>Use the benchmark score to confirm that this implementation is rejected before deployment.</p></body></html>"""
    (output / "reports" / "research_report.html").write_text(report, encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("run")
    cmd.add_argument("--market-data", type=Path, required=True)
    cmd.add_argument("--output-dir", type=Path, required=True)
    cmd.add_argument("--valuation-date", required=True)
    args = p.parse_args(argv)
    run(args.market_data, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
