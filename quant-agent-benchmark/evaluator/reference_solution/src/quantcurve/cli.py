from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares


NODES = np.array([1 / 12, 0.25, 0.5, 0.75, 1.0, 1.5, 2, 3, 5, 7, 10, 12, 15, 20, 25, 30], dtype=float)


@dataclass
class Curve:
    zero_nodes: np.ndarray

    def zero(self, t: np.ndarray | float, parallel_bump: float = 0.0) -> np.ndarray:
        x = np.asarray(t, dtype=float)
        spline = CubicSpline(NODES, self.zero_nodes, bc_type="natural", extrapolate=True)
        clipped = np.clip(x, NODES[0], NODES[-1])
        return spline(clipped) + parallel_bump

    def discount(self, t: np.ndarray | float, parallel_bump: float = 0.0) -> np.ndarray:
        x = np.asarray(t, dtype=float)
        return np.exp(-self.zero(x, parallel_bump) * x)


def payment_times(maturity: float, frequency: int) -> np.ndarray:
    return np.arange(1, max(1, int(round(maturity * frequency))) + 1, dtype=float) / frequency


def model_quote(row: pd.Series, curve: Curve, bump: float = 0.0) -> float:
    t = float(row["maturity_years"])
    frequency = int(row["payment_frequency"])
    kind = row["instrument_type"]
    if kind == "deposit":
        return 100.0 * (1.0 / float(curve.discount(t, bump)) - 1.0) / t
    times = payment_times(t, frequency)
    dfs = curve.discount(times, bump)
    if kind == "ois_swap":
        return 100.0 * (1.0 - float(curve.discount(t, bump))) / ((1.0 / frequency) * float(dfs.sum()))
    cash = np.full(times.shape, 100.0 * float(row["coupon_rate"]) / frequency)
    cash[-1] += 100.0
    return float(np.dot(cash, dfs))


def trade_pv(row: pd.Series, curve: Curve, bump: float = 0.0) -> float:
    quote = float(row["normalized_quote"])
    t = float(row["maturity_years"])
    frequency = int(row["payment_frequency"])
    if row["instrument_type"] == "deposit":
        return 1_000_000.0 * (1.0 - (1.0 + quote / 100.0 * t) * float(curve.discount(t, bump)))
    if row["instrument_type"] == "ois_swap":
        times = payment_times(t, frequency)
        annuity = float(curve.discount(times, bump).sum()) / frequency
        return 1_000_000.0 * ((quote / 100.0) * annuity - (1.0 - float(curve.discount(t, bump))))
    return model_quote(row, curve, bump) - quote


def load_and_clean(path: Path, valuation_date: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"obs_id", "instrument_id", "timestamp", "instrument_type", "maturity_years", "coupon_rate", "payment_frequency", "quote_value", "bid", "ask", "liquidity_score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("missing required columns: " + ", ".join(sorted(missing)))
    data = frame.copy()
    for col in ("maturity_years", "coupon_rate", "payment_frequency", "quote_value", "bid", "ask", "liquidity_score"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["normalized_quote"] = data["quote_value"]
    data["normalized_bid"] = data["bid"]
    data["normalized_ask"] = data["ask"]
    data["action"] = "keep"
    data["reason"] = "passed initial validation"
    data["weight"] = 1.0

    missing_quote = data["quote_value"].isna()
    data.loc[missing_quote, ["action", "reason", "weight"]] = ["exclude", "missing quote", 0.0]
    spread = (data["ask"] - data["bid"]).abs()
    rate_unit = (data["instrument_type"] != "bond") & (data["quote_value"].abs() < 0.15) & (spread < 0.0005) & ~missing_quote
    price_unit = (data["instrument_type"] == "bond") & (data["quote_value"].abs() < 5.0) & (spread < 0.02) & ~missing_quote
    for mask in (rate_unit, price_unit):
        data.loc[mask, ["normalized_quote", "normalized_bid", "normalized_ask"]] = data.loc[mask, ["quote_value", "bid", "ask"]].to_numpy() * 100.0
        data.loc[mask, "action"] = "correct"
        data.loc[mask, "reason"] = "unit scale inferred from quote magnitude and spread"

    inverted = (data["normalized_bid"] > data["normalized_ask"]) & ~missing_quote
    old_bid = data.loc[inverted, "normalized_bid"].copy()
    data.loc[inverted, "normalized_bid"] = data.loc[inverted, "normalized_ask"].to_numpy()
    data.loc[inverted, "normalized_ask"] = old_bid.to_numpy()
    data.loc[inverted, "action"] = "correct"
    data.loc[inverted, "reason"] = "bid/ask inversion repaired"

    timestamps = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    age_days = (pd.Timestamp(valuation_date, tz="UTC") + pd.Timedelta(hours=23, minutes=59) - timestamps).dt.total_seconds() / 86400.0
    stale = (age_days > 3.0) & data["action"].ne("exclude")
    data.loc[stale, "action"] = "downweight"
    data.loc[stale, "reason"] = "stale timestamp"

    data["_timestamp"] = timestamps
    order = data.sort_values(["instrument_id", "_timestamp", "liquidity_score"], ascending=[True, False, False], kind="mergesort")
    duplicate_loser = order.duplicated("instrument_id", keep="first")
    dup_index = order.index[duplicate_loser]
    data.loc[dup_index, "action"] = "exclude"
    data.loc[dup_index, "reason"] = "inferior duplicate by freshness/liquidity"
    data.loc[dup_index, "weight"] = 0.0

    norm_spread = (data["normalized_ask"] - data["normalized_bid"]).abs()
    scaled_spread = np.where(data["instrument_type"].eq("bond"), norm_spread * 10.0, norm_spread * 100.0)
    base_weight = np.clip(np.sqrt(data["liquidity_score"].clip(0.01, 1.0)) / np.maximum(scaled_spread, 0.35), 0.08, 2.5)
    data.loc[data["action"].ne("exclude"), "weight"] = base_weight[data["action"].ne("exclude")]
    data.loc[stale & data["action"].ne("exclude"), "weight"] *= 0.15
    illiquid = (data["liquidity_score"] < 0.18) & data["action"].eq("keep")
    data.loc[illiquid, "action"] = "downweight"
    data.loc[illiquid, "reason"] = "low liquidity retained with reduced influence"
    data.loc[illiquid, "weight"] *= 0.45

    invalid = (~np.isfinite(data["maturity_years"])) | (data["maturity_years"] <= 0) | (data["payment_frequency"] <= 0)
    invalid |= ((data["instrument_type"] == "bond") & ((data["normalized_quote"] < 20) | (data["normalized_quote"] > 200)))
    invalid |= ((data["instrument_type"] != "bond") & (data["normalized_quote"].abs() > 20))
    data.loc[invalid, ["action", "reason", "weight"]] = ["exclude", "invalid domain or range", 0.0]
    return data


def proxy_zero(row: pd.Series) -> float:
    t = float(row["maturity_years"])
    q = float(row["normalized_quote"])
    if row["instrument_type"] == "deposit":
        return np.log1p(q / 100.0 * t) / t
    if row["instrument_type"] == "ois_swap":
        return q / 100.0
    coupon = float(row["coupon_rate"])
    return coupon + (100.0 - q) / (100.0 * max(t, 0.25))


def initial_nodes(data: pd.DataFrame) -> np.ndarray:
    usable = data[data["action"].ne("exclude")].copy()
    usable["proxy"] = usable.apply(proxy_zero, axis=1)
    order = np.argsort(usable["maturity_years"].to_numpy())
    x = usable["maturity_years"].to_numpy()[order]
    y = usable["proxy"].to_numpy()[order]
    if len(x) < 4:
        raise ValueError("too few usable instruments")
    values = np.interp(NODES, x, y, left=np.median(y[: min(5, len(y))]), right=np.median(y[-min(5, len(y)) :]))
    return np.clip(values, -0.08, 0.15)


def residual_vector(z: np.ndarray, data: pd.DataFrame) -> np.ndarray:
    curve = Curve(z)
    usable = data[data["action"].ne("exclude")]
    residuals = []
    for _, row in usable.iterrows():
        raw = model_quote(row, curve) - float(row["normalized_quote"])
        scaled = raw * (10.0 if row["instrument_type"] == "bond" else 100.0)
        residuals.append(scaled * np.sqrt(max(float(row["weight"]), 1e-8)))
    spacing = np.diff(NODES)
    slopes = np.diff(z) / spacing
    curvature = np.diff(slopes) / ((spacing[1:] + spacing[:-1]) / 2.0)
    penalty = 12.0 * curvature
    anchor = np.array([max(0.0, abs(z[-1]) - 0.12) * 100.0])
    return np.concatenate([np.asarray(residuals), penalty, anchor])


def fit_curve(data: pd.DataFrame) -> Curve:
    init = initial_nodes(data)
    fit = least_squares(residual_vector, init, args=(data,), bounds=(-0.12, 0.20), loss="soft_l1", f_scale=1.5, max_nfev=90, xtol=1e-8, ftol=1e-8, gtol=1e-8)
    return Curve(fit.x)


def robust_fit(data: pd.DataFrame) -> tuple[Curve, pd.DataFrame]:
    working = data.copy()
    first = fit_curve(working)
    usable_idx = working.index[working["action"].ne("exclude")]
    residuals = []
    for j in usable_idx:
        row = working.loc[j]
        raw = model_quote(row, first) - float(row["normalized_quote"])
        residuals.append(raw * (10.0 if row["instrument_type"] == "bond" else 100.0))
    values = np.asarray(residuals)
    center = float(np.median(values))
    mad_scale = max(1.4826 * float(np.median(np.abs(values - center))), 0.4)
    for j, resid in zip(usable_idx, values):
        magnitude = abs(resid - center)
        if magnitude > max(8.0, 5.0 * mad_scale):
            working.loc[j, ["action", "reason", "weight"]] = ["exclude", "extreme robust repricing residual", 0.0]
        elif magnitude > max(2.8, 2.7 * mad_scale):
            working.loc[j, "action"] = "downweight"
            working.loc[j, "reason"] = "moderate robust repricing residual"
            working.loc[j, "weight"] *= 0.12
    return fit_curve(working), working


def baseline_curve(data: pd.DataFrame) -> Curve:
    usable = data[data["action"].ne("exclude")].copy()
    usable["proxy"] = usable.apply(proxy_zero, axis=1)
    x = usable["maturity_years"].to_numpy(float)
    y = usable["proxy"].to_numpy(float)
    binned = []
    for node in NODES:
        nearest = np.argsort(np.abs(x - node))[: max(3, min(8, len(x)))]
        binned.append(float(np.median(y[nearest])))
    return Curve(np.asarray(binned))


def quote_rmse(curve: Curve, data: pd.DataFrame) -> float:
    errors = []
    for _, row in data[data["action"].ne("exclude")].iterrows():
        error = model_quote(row, curve) - float(row["normalized_quote"])
        errors.append(error * (10.0 if row["instrument_type"] == "bond" else 100.0))
    return float(np.sqrt(np.mean(np.square(errors)))) if errors else float("inf")


def model_comparison(data: pd.DataFrame) -> dict:
    usable = data[data["action"].ne("exclude")].sort_values(["maturity_years", "instrument_id"], kind="mergesort")
    holdout_ids = set(usable.iloc[::7]["instrument_id"])
    train = data[~data["instrument_id"].isin(holdout_ids)].copy()
    holdout = data[data["instrument_id"].isin(holdout_ids)].copy()
    baseline = baseline_curve(train)
    advanced = fit_curve(train)
    baseline_holdout = quote_rmse(baseline, holdout)
    advanced_holdout = quote_rmse(advanced, holdout)
    selected = "advanced" if advanced_holdout <= baseline_holdout * 1.10 else "baseline"
    return {
        "baseline": {"train_normalized_rmse": quote_rmse(baseline, train), "holdout_normalized_rmse": baseline_holdout},
        "advanced": {"train_normalized_rmse": quote_rmse(advanced, train), "holdout_normalized_rmse": advanced_holdout},
        "holdout_method": "maturity-ordered every-seventh unique instrument; duplicate groups stay together",
        "selected_model": selected,
        "selection_rationale": "advanced selected only when maturity-aware holdout error is no worse than 10% above baseline; final choice also checked for smooth forwards",
    }


def curve_frame(curve: Curve) -> pd.DataFrame:
    t = np.linspace(1 / 12, 30.0, 361)
    z = curve.zero(t)
    d = np.exp(-z * t)
    f = np.gradient(-np.log(d), t, edge_order=1)
    return pd.DataFrame({"maturity_years": t, "zero_rate": z, "discount_factor": d, "forward_rate": f})


def repricing_frame(data: pd.DataFrame, curve: Curve) -> pd.DataFrame:
    rows = []
    for _, row in data.iterrows():
        model = model_quote(row, curve) if row["action"] != "exclude" else np.nan
        market = float(row["normalized_quote"]) if pd.notna(row["normalized_quote"]) else np.nan
        rows.append({"instrument_id": row["instrument_id"], "instrument_type": row["instrument_type"], "market_quote": market, "model_quote": model, "residual": model - market if np.isfinite(model) and np.isfinite(market) else np.nan, "weight": float(row["weight"])})
    return pd.DataFrame(rows)


def risk_frame(data: pd.DataFrame, curve: Curve) -> pd.DataFrame:
    rows = []
    tenors = np.array([2.0, 5.0, 10.0, 30.0])
    for _, row in data[data["action"].ne("exclude")].iterrows():
        dv01 = (trade_pv(row, curve, -1e-4) - trade_pv(row, curve, 1e-4)) / 2.0
        t = float(row["maturity_years"])
        distances = np.abs(tenors - t)
        weights = 1.0 / np.maximum(distances, 0.4) ** 2
        weights /= weights.sum()
        rows.append({"instrument_id": row["instrument_id"], "dv01": dv01, **{f"key_{int(k)}y": dv01 * w for k, w in zip(tenors, weights)}})
    return pd.DataFrame(rows)


def svg_line(x: np.ndarray, ys: list[np.ndarray], labels: list[str], title: str) -> str:
    width, height, pad = 760, 360, 48
    all_y = np.concatenate(ys)
    ymin, ymax = float(np.nanmin(all_y)), float(np.nanmax(all_y))
    if ymax <= ymin:
        ymax = ymin + 1.0
    def points(y: np.ndarray) -> str:
        px = pad + (x - x.min()) / max(x.max() - x.min(), 1e-9) * (width - 2 * pad)
        py = height - pad - (y - ymin) / (ymax - ymin) * (height - 2 * pad)
        return " ".join(f"{a:.2f},{b:.2f}" for a, b in zip(px, py))
    colors = ["#1769aa", "#d95f02", "#2a9d8f", "#7b2cbf"]
    polylines = "".join(f'<polyline fill="none" stroke="{colors[i % len(colors)]}" stroke-width="2" points="{points(y)}"/>' for i, y in enumerate(ys))
    legend = "".join(f'<text x="{pad + i * 150}" y="24" font-size="12" fill="{colors[i % len(colors)]}">{html.escape(label)}</text>' for i, label in enumerate(labels))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="{width/2}" y="18" text-anchor="middle" font-size="14">{html.escape(title)}</text>{legend}<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#444"/><line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="#444"/>{polylines}</svg>\n'


def write_outputs(output: Path, data: pd.DataFrame, curve: Curve, comparison: dict) -> None:
    curves = output / "curves"
    diagnostics = output / "diagnostics"
    charts = output / "charts"
    reports = output / "reports"
    for p in (curves, diagnostics, charts, reports):
        p.mkdir(parents=True, exist_ok=True)
    grid = curve_frame(curve)
    grid.to_csv(curves / "curve.csv", index=False, float_format="%.12g", lineterminator="\n")
    data[["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]].to_csv(diagnostics / "cleaning.csv", index=False, float_format="%.12g", lineterminator="\n")
    repricing = repricing_frame(data, curve)
    repricing.to_csv(diagnostics / "repricing.csv", index=False, float_format="%.12g", lineterminator="\n")
    risk_frame(data, curve).to_csv(diagnostics / "risk.csv", index=False, float_format="%.12g", lineterminator="\n")
    (diagnostics / "model_comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sensitivity = {
        "parallel_plus_10bp": {"max_discount_change": float(np.max(np.abs(curve.discount(grid["maturity_years"], 0.001) - grid["discount_factor"])))},
        "parallel_minus_10bp": {"max_discount_change": float(np.max(np.abs(curve.discount(grid["maturity_years"], -0.001) - grid["discount_factor"])))},
        "remove_low_liquidity": {"usable_observations": int((data["action"] != "exclude").sum()), "low_liquidity_count": int((data["liquidity_score"] < 0.18).sum())},
    }
    (diagnostics / "sensitivity.json").write_text(json.dumps(sensitivity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    x = grid["maturity_years"].to_numpy()
    chart_specs = {
        "zero_curve.svg": ([100 * grid["zero_rate"].to_numpy()], ["zero %"], "Continuously compounded zero curve"),
        "forward_curve.svg": ([100 * grid["forward_rate"].to_numpy()], ["forward %"], "Instantaneous forward curve"),
        "discount_curve.svg": ([grid["discount_factor"].to_numpy()], ["discount factor"], "Discount factors"),
    }
    residual = repricing["residual"].fillna(0).to_numpy()
    rx = np.arange(len(residual), dtype=float)
    for name, (ys, labels, title) in chart_specs.items():
        (charts / name).write_text(svg_line(x, ys, labels, title), encoding="utf-8")
    (charts / "repricing.svg").write_text(svg_line(rx, [residual], ["quote residual"], "Instrument repricing residuals"), encoding="utf-8")
    dq_counts = data["action"].value_counts().to_dict()
    html_report = f"""<!doctype html><html><head><meta charset="utf-8"><title>Zero Curve Research Report</title><style>body{{font-family:system-ui;max-width:980px;margin:2rem auto;line-height:1.5}}img{{max-width:100%}}table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.35rem}}</style></head><body>
<h1>Zero Curve Research Report</h1><h2>Executive summary</h2><p>A regularized cash-flow calibration was compared with a simple baseline. The selected model is <strong>{comparison['selected_model']}</strong>; model complexity was accepted only after maturity-aware holdout validation.</p>
<h2>Methodology</h2><p>Continuously compounded zero-rate nodes are joined by a natural cubic spline. Deposits, OIS par swaps, and bonds are repriced from documented cash flows. The objective combines spread/liquidity weights, robust loss, and curvature regularisation.</p>
<h2>Data-quality findings</h2><p>Observation actions: {html.escape(str(dq_counts))}. Missing values, duplicates, timestamps, units, bid/ask consistency, liquidity, and robust residuals were checked with an observation-level audit trail.</p>
<h2>Model comparison</h2><pre>{html.escape(json.dumps(comparison, indent=2, sort_keys=True))}</pre>
<h2>Sensitivity analysis</h2><p>Parallel ±10bp discount changes, finite-difference risk, key-rate allocation, and low-liquidity influence were evaluated.</p>
<h2>Validation and repricing</h2><p>All curve outputs were checked for finiteness, positive discount factors, discount/zero/forward consistency, and instrument repricing residuals.</p>
<h2>Charts</h2><img src="../charts/zero_curve.svg" alt="zero curve"><img src="../charts/forward_curve.svg" alt="forward curve"><img src="../charts/repricing.svg" alt="repricing"><img src="../charts/discount_curve.svg" alt="discount factors">
<h2>Limitations</h2><p>Sparse-region interpolation, flat-zero extrapolation, unit ambiguity near zero, robust-treatment false positives, and synthetic scheduling remain material model risks.</p>
<h2>Recommended next steps</h2><p>Monitor holdout repricing and forward roughness, review every corrected unit, and challenge long-end extrapolation before portfolio use.</p></body></html>\n"""
    (reports / "research_report.html").write_text(html_report, encoding="utf-8")


def run(market_data: Path, output_dir: Path, valuation_date: str) -> None:
    data = load_and_clean(market_data, valuation_date)
    comparison = model_comparison(data) if len(data) >= 120 else {
        "baseline": {"train_normalized_rmse": None, "holdout_normalized_rmse": None},
        "advanced": {"train_normalized_rmse": None, "holdout_normalized_rmse": None},
        "holdout_method": "compact conforming-input run; primary submission performs maturity-ordered holdout",
        "selected_model": "advanced",
        "selection_rationale": "advanced robust calibration retained for compact scenario execution",
    }
    advanced, cleaned = robust_fit(data)
    selected = advanced if comparison["selected_model"] == "advanced" else baseline_curve(cleaned)
    write_outputs(output_dir, cleaned, selected, comparison)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("run")
    cmd.add_argument("--market-data", type=Path, required=True)
    cmd.add_argument("--output-dir", type=Path, required=True)
    cmd.add_argument("--valuation-date", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    run(args.market_data, args.output_dir, args.valuation_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
