from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.project) / "src"))

    from quantcurve.cleaning import clean_market_data
    from quantcurve.config import CurveConfig
    from quantcurve.curve import ZeroCurve
    from quantcurve.io import load_market_data
    from quantcurve.modeling import (
        FitResult,
        _standalone_zero,
        _weighted_median,
        fit_advanced,
        fit_baseline,
        fit_metrics,
        maturity_holdout_mask,
        quote_scales,
        repricing_residuals,
    )
    from quantcurve.pricing import model_quote

    started = time.perf_counter()
    cfg = CurveConfig()
    public = clean_market_data(load_market_data(args.input), "2026-01-15", cfg).usable.reset_index(drop=True)
    mask = maturity_holdout_mask(public, cfg)
    public_train = public.loc[~mask].reset_index(drop=True)
    public_holdout = public.loc[mask].reset_index(drop=True)

    def variant(rows: pd.DataFrame, bucketed: bool, rolling_median: bool) -> FitResult:
        records: list[tuple[float, float, float, float]] = []
        for _, row in rows.iterrows():
            z = _standalone_zero(row)
            key = (
                float(math.floor(float(row.maturity_years) / cfg.holdout_bucket_years + 1e-10))
                if bucketed
                else round(float(row.maturity_years), 10)
            )
            records.append((key, float(row.maturity_years), float(z), float(row.fit_weight)))
        table = pd.DataFrame(records, columns=["key", "maturity", "zero", "weight"])
        points: list[tuple[float, float]] = []
        for _, group in table.groupby("key", sort=True):
            weights = np.maximum(group.weight.to_numpy(float), 1e-12)
            points.append((float(np.average(group.maturity, weights=weights)), _weighted_median(group.zero.to_numpy(float), weights)))
        points.sort()
        knots = np.array([p[0] for p in points])
        rates = np.array([p[1] for p in points])
        if knots[0] > 0:
            knots, rates = np.r_[0.0, knots], np.r_[rates[0], rates]
        if knots[-1] < 30:
            knots, rates = np.r_[knots, 30.0], np.r_[rates, rates[-1]]
        if rolling_median and len(rates) >= 3:
            rates = pd.Series(rates).rolling(3, center=True, min_periods=1).median().to_numpy()
        curve = ZeroCurve(knots, np.clip(rates, cfg.parameter_lower_bound, cfg.parameter_upper_bound), method="pchip")
        residuals = repricing_residuals(rows, curve)
        standardized = residuals / quote_scales(rows, cfg)
        return FitResult(curve, residuals, standardized, np.ones(len(rows)), standardized.copy(), float(standardized @ standardized), True, "diagnostic", 1)

    def segmented(rows: pd.DataFrame, curve: ZeroCurve) -> dict[str, object]:
        residuals = repricing_residuals(rows, curve)
        scales = quote_scales(rows, cfg)
        standardized = residuals / scales
        weights = rows.base_weight.to_numpy(float)

        def one(pos: np.ndarray, kind: str) -> dict[str, object] | None:
            if int(pos.sum()) == 0:
                return None
            r, s, w = residuals[pos], standardized[pos], weights[pos]
            native = 10_000.0 * r if kind != "bond" else r
            return {
                "n": int(pos.sum()),
                "weighted_normalized_rmse": float(np.sqrt(np.dot(w, s * s) / max(w.sum(), 1e-12))),
                "native_rmse": float(np.sqrt(np.mean(native * native))),
                "native_unit": "bp" if kind != "bond" else "price_points",
            }

        out: dict[str, object] = {
            "overall": fit_metrics(rows, curve, cfg),
            "by_product": {},
            "by_tenor": {},
            "by_tenor_product": {},
            "by_maturity_convention": {},
        }
        for kind in ("deposit", "ois_swap", "bond"):
            pos = rows.instrument_type.to_numpy() == kind
            out["by_product"][kind] = one(pos, kind)
        t = rows.maturity_years.to_numpy(float)
        bands = {"short_T_le_2": t <= 2, "medium_2_to_15": (t > 2) & (t < 15), "long_T_ge_15": t >= 15}
        for name, band in bands.items():
            if not int(band.sum()):
                out["by_tenor"][name] = None
            else:
                s, w = standardized[band], weights[band]
                out["by_tenor"][name] = {"n": int(band.sum()), "weighted_normalized_rmse": float(np.sqrt(np.dot(w, s * s) / max(w.sum(), 1e-12)))}
            for kind in ("deposit", "ois_swap", "bond"):
                pos = band & (rows.instrument_type.to_numpy() == kind)
                out["by_tenor_product"][f"{name}|{kind}"] = one(pos, kind)
        fractional = np.abs(2.0 * t - np.round(2.0 * t)) > 1e-8
        for name, pos in {"regular_half_year_grid": ~fractional, "fractional_maturity": fractional}.items():
            if not int(pos.sum()):
                out["by_maturity_convention"][name] = None
            else:
                s, w = standardized[pos], weights[pos]
                out["by_maturity_convention"][name] = {
                    "n": int(pos.sum()),
                    "weighted_normalized_rmse": float(np.sqrt(np.dot(w, s * s) / max(w.sum(), 1e-12))),
                }
        return out

    public_models = {
        "baseline": fit_baseline(public_train, cfg).curve,
        "no_rolling_median": variant(public_train, True, False).curve,
        "exact_tenor_no_median": variant(public_train, False, False).curve,
    }
    public_models["advanced"] = fit_advanced(public_train, cfg, public_models["baseline"]).curve
    public_results = {name: segmented(public_holdout, curve) for name, curve in public_models.items()}

    shapes = {
        "flat": (lambda t: np.full_like(np.asarray(t, float), 0.015), lambda t: np.zeros_like(np.asarray(t, float))),
        "rising": (lambda t: 0.008 + 0.0008 * np.asarray(t, float), lambda t: np.full_like(np.asarray(t, float), 0.0008)),
        "falling": (lambda t: 0.030 - 0.0006 * np.asarray(t, float), lambda t: np.full_like(np.asarray(t, float), -0.0006)),
        "humped": (
            lambda t: 0.012 + 0.012 * np.exp(-((np.asarray(t, float) - 1.0) / 0.55) ** 2) + 0.0002 * np.asarray(t, float),
            lambda t: 0.0002 - 0.024 * (np.asarray(t, float) - 1.0) / (0.55**2) * np.exp(-((np.asarray(t, float) - 1.0) / 0.55) ** 2),
        ),
    }

    def independent_quote(row: pd.Series, discount, bond_stub_coupon: bool = False) -> float:
        t = float(row.maturity_years)
        if row.instrument_type == "deposit":
            return (1.0 / float(discount(t)) - 1.0) / t
        if row.instrument_type == "ois_swap":
            f = 1 if t <= 2.0 + 1e-12 else 2
            step = 1.0 / f
            times = step * np.arange(1, int(np.floor(t * f + 1e-10)) + 1)
            if len(times) == 0 or t - times[-1] > 1e-10:
                times = np.r_[times, t]
            accruals = np.diff(np.r_[0.0, times])
            return (1.0 - float(discount(t))) / float(np.dot(accruals, discount(times)))
        f = int(row.payment_frequency)
        step = 1.0 / f
        times = step * np.arange(1, int(np.floor(t * f + 1e-10)) + 1)
        coupon = 100.0 * float(row.coupon_rate) / f
        amounts = np.full(len(times), coupon)
        if len(times) and abs(times[-1] - t) <= 1e-10:
            amounts[-1] += 100.0
        else:
            if bond_stub_coupon:
                previous = float(times[-1]) if len(times) else 0.0
                stub_coupon = 100.0 * float(row.coupon_rate) * (t - previous)
            else:
                stub_coupon = 0.0
            times = np.r_[times, t]
            amounts = np.r_[amounts, 100.0 + stub_coupon]
        return float(np.dot(amounts, discount(times)))

    synthetic: dict[str, object] = {}
    proxy: dict[str, object] = {}
    truth_grid = np.linspace(1 / 12, 30.0, 1201)
    for shape, (z_fn, dz_fn) in shapes.items():
        discount = lambda x, z_fn=z_fn: np.exp(-z_fn(np.asarray(x, float)) * np.asarray(x, float))
        rows = public.copy()
        rows["normalized_quote"] = [independent_quote(row, discount) for _, row in rows.iterrows()]
        train = rows.loc[~mask].reset_index(drop=True)
        fits = {
            "baseline": fit_baseline(train, cfg).curve,
            "no_rolling_median": variant(train, True, False).curve,
            "exact_tenor_no_median": variant(train, False, False).curve,
        }
        fits["advanced"] = fit_advanced(train, cfg, fits["baseline"]).curve
        z_true = z_fn(truth_grid)
        f_true = z_true + truth_grid * dz_fn(truth_grid)
        shape_result: dict[str, object] = {}
        for name, curve in fits.items():
            z_err = 10_000.0 * (np.asarray(curve.zero(truth_grid)) - z_true)
            f_err = 10_000.0 * (np.asarray(curve.forward(truth_grid)) - f_true)
            model_result: dict[str, object] = {
                "zero_rmse_bp": float(np.sqrt(np.mean(z_err**2))),
                "forward_rmse_bp": float(np.sqrt(np.mean(f_err**2))),
            }
            for band_name, pos in {
                "short_T_le_2": truth_grid <= 2,
                "medium_2_to_15": (truth_grid > 2) & (truth_grid < 15),
                "long_T_ge_15": truth_grid >= 15,
            }.items():
                model_result[band_name] = {
                    "zero_rmse_bp": float(np.sqrt(np.mean(z_err[pos] ** 2))),
                    "forward_rmse_bp": float(np.sqrt(np.mean(f_err[pos] ** 2))),
                }
            shape_result[name] = model_result
        synthetic[shape] = shape_result
        proxy_rows = []
        for _, row in rows.iterrows():
            estimate = _standalone_zero(row)
            proxy_rows.append((str(row.instrument_type), float(row.maturity_years), 10_000.0 * (estimate - float(z_fn(float(row.maturity_years))))))
        proxy_table = pd.DataFrame(proxy_rows, columns=["product", "maturity", "error_bp"])
        by_product = {k: {"n": int(len(g)), "rmse_bp": float(np.sqrt(np.mean(g.error_bp**2))), "bias_bp": float(g.error_bp.mean())} for k, g in proxy_table.groupby("product")}
        proxy[shape] = {"overall_rmse_bp": float(np.sqrt(np.mean(proxy_table.error_bp**2))), "by_product": by_product}

    check_rows = []
    for kind in ("deposit", "ois_swap", "bond"):
        group = public[public.instrument_type == kind]
        chosen = pd.concat([group.head(1), group.loc[(group.maturity_years % 0.5).abs() > 1e-8].head(1)]).drop_duplicates("instrument_id")
        for _, row in chosen.iterrows():
            for level, slope, label in ((0.015, 0.0, "flat"), (-0.01, 0.0005, "negative_rising")):
                curve = ZeroCurve(np.array([0.0, 30.0]), np.array([level, level + 30.0 * slope]), method="pchip")
                discount = lambda x, level=level, slope=slope: np.exp(-(level + slope * np.asarray(x, float)) * np.asarray(x, float))
                expected = independent_quote(row, discount)
                actual = model_quote(row, curve)
                alternate = independent_quote(row, discount, bond_stub_coupon=True) if kind == "bond" else expected
                check_rows.append({
                    "instrument_id": str(row.instrument_id), "product": kind, "maturity": float(row.maturity_years), "shape": label,
                    "implementation": float(actual), "independent_documented": float(expected), "abs_difference": float(abs(actual - expected)),
                    "alternate_stub_coupon": float(alternate), "alternate_minus_documented": float(alternate - expected),
                })

    result = {
        "runtime_seconds": time.perf_counter() - started,
        "public_split": {"train_n": int((~mask).sum()), "holdout_n": int(mask.sum())},
        "public_holdout": public_results,
        "synthetic_truth": synthetic,
        "standalone_proxy": proxy,
        "pricing_checks": check_rows,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"runtime_seconds": result["runtime_seconds"], "public_split": result["public_split"]}, indent=2))


if __name__ == "__main__":
    main()
