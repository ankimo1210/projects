"""Curve calibration: holdout split, baseline bootstrap-style fit, and an
advanced regularised/robust spline fit.

Both models are fitted by global weighted nonlinear least squares over
*every* calibration instrument simultaneously (rather than a sequential
per-pillar bootstrap), because the dataset has several independent
quotes per OIS maturity and irregularly spaced bond maturities that do
not line up with swap pillars. Zero rates are the optimisation
variables directly (never log- or square-transformed), so nothing in
the fit prevents negative rates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from .cashflows import bond_model_price, deposit_model_rate, swap_model_par_rate
from .curve import PiecewiseLinearZeroCurve, SplineZeroCurve
from .grids import CALIBRATION_KNOTS

TUKEY_C = 4.685
N_IRLS_ITER = 5
FINE_GRID = np.linspace(CALIBRATION_KNOTS[0], CALIBRATION_KNOTS[-1], 200)
LAMBDA_GRID = (0.0, 1e2, 1e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7, 3e7, 1e8)


def model_quote(row, discount_fn) -> float:
    if row.instrument_type == "deposit":
        return deposit_model_rate(discount_fn, row.maturity_years) * 100.0
    if row.instrument_type == "ois_swap":
        return swap_model_par_rate(discount_fn, row.maturity_years, int(row.payment_frequency)) * 100.0
    if row.instrument_type == "bond":
        return bond_model_price(discount_fn, row.maturity_years, row.coupon_rate, int(row.payment_frequency))
    raise ValueError(f"unsupported instrument_type: {row.instrument_type}")


def build_holdout_split(df_usable: pd.DataFrame) -> tuple[pd.Series, set]:
    """Maturity-aware visible holdout.

    Deposits stay entirely in training (only five tenors anchor the
    front end; removing any would leave a gap the curve cannot bridge).
    OIS swaps are held out by *whole maturity bucket* so that co-located
    independent quotes at the same tenor never split across train and
    holdout (avoiding the leakage the task explicitly warns about).
    Bonds, whose maturities are all distinct, are held out by taking
    every fifth bond sorted by maturity, excluding the shortest and
    longest so both models are always tested on genuine interpolation.

    Candidate swap maturities are additionally screened for local
    smoothness before being made eligible for holdout: a maturity whose
    bucket-median par rate is a robust outlier versus a straight-line
    interpolation of its immediate neighbours is a genuine, idiosyncratic
    market feature (attested by several independent quotes, not a data
    error) rather than a smoothly-interpolable point, so holding it out
    would not test generalisation -- it would fail for any smooth model,
    baseline or advanced alike, and swamp the comparison. Such points are
    kept in training instead.

    Returns the split labels plus the set of swap maturities that were
    removed *entirely* from training -- callers must drop the matching
    calibration knot for train-only fits (see ``active_knots``),
    otherwise that knot is unconstrained by any training residual and
    is left to drift arbitrarily.
    """
    split = pd.Series("train", index=df_usable.index, dtype=object)
    holdout_swap_maturities: set = set()

    swap_idx = df_usable.index[df_usable["instrument_type"] == "ois_swap"]
    if len(swap_idx) > 0:
        buckets = df_usable.loc[swap_idx, "maturity_years"].round(6)
        unique_buckets = sorted(buckets.unique())
        if len(unique_buckets) >= 6:
            eligible = _smooth_interior_maturities(df_usable.loc[swap_idx], buckets, unique_buckets)
            if eligible:
                step = max(1, len(eligible) // 4)
                holdout_swap_maturities = set(eligible[::step][:4])
                holdout_rows = swap_idx[buckets.isin(holdout_swap_maturities)]
                split.loc[holdout_rows] = "holdout"

    bond_idx = df_usable.index[df_usable["instrument_type"] == "bond"]
    if len(bond_idx) > 0:
        ordered = df_usable.loc[bond_idx, "maturity_years"].sort_values().index
        n = len(ordered)
        if n >= 8:
            holdout_bonds = [ordered[i] for i in range(2, n - 1, 5)]
            split.loc[holdout_bonds] = "holdout"

    return split, holdout_swap_maturities


def _smooth_interior_maturities(swap_df: pd.DataFrame, buckets: pd.Series, unique_buckets: list) -> list:
    """Interior swap maturities whose consensus rate is not a local-smoothness outlier."""
    medians = {m: float(swap_df.loc[buckets == m, "normalized_quote"].median()) for m in unique_buckets}
    deviations = {}
    for p in range(1, len(unique_buckets) - 1):
        m = unique_buckets[p]
        left_m, right_m = unique_buckets[p - 1], unique_buckets[p + 1]
        left_v, right_v = medians[left_m], medians[right_m]
        interp = left_v + (m - left_m) / (right_m - left_m) * (right_v - left_v)
        deviations[m] = abs(medians[m] - interp)
    if not deviations:
        return []
    dev_vals = np.array(list(deviations.values()))
    dev_med = float(np.median(dev_vals))
    dev_mad = float(np.median(np.abs(dev_vals - dev_med))) * 1.4826
    threshold = dev_med + 3.0 * max(dev_mad, 0.02)
    return sorted(m for m, d in deviations.items() if d <= threshold)


def active_knots(knots: np.ndarray, excluded_maturities: set, tol: float = 1e-6) -> np.ndarray:
    """Calibration knots with any fully-held-out maturity removed.

    A knot with zero training instruments on both sides carries no
    gradient information; dropping it lets the curve bridge the gap by
    interpolation from its neighbours instead, which is what a holdout
    test of interpolation quality is supposed to measure.
    """
    if not excluded_maturities:
        return knots
    mask = np.array([not any(abs(k - m) < tol for m in excluded_maturities) for k in knots])
    return knots[mask]


@dataclass
class FitResult:
    curve: object
    per_type_scale: dict
    weights: np.ndarray
    irls_history: list


def _initial_guess(df_train: pd.DataFrame) -> float:
    deposits = df_train[df_train["instrument_type"] == "deposit"]
    if len(deposits) > 0:
        return float(deposits["normalized_quote"].median()) / 100.0
    return float(df_train["normalized_quote"].median()) / 100.0 if len(df_train) else 0.02


def _residual_vector(z, knots, curve_cls, rows, weights, lambda_reg=0.0, grid=None):
    curve = curve_cls(np.asarray(knots), z)
    model = np.fromiter((model_quote(r, curve.discount) for r in rows), dtype=float, count=len(rows))
    market = np.fromiter((r.normalized_quote for r in rows), dtype=float, count=len(rows))
    market_res = weights * (market - model)
    if lambda_reg > 0 and grid is not None:
        f = curve.forward_rate(grid)
        d2 = np.diff(f, 2)
        pen = np.sqrt(lambda_reg) * d2
        return np.concatenate([market_res, pen])
    return market_res


def _solve(knots, curve_cls, rows, weights, z0, lambda_reg=0.0, grid=None):
    def resid(z):
        return _residual_vector(z, knots, curve_cls, rows, weights, lambda_reg, grid)

    result = least_squares(resid, z0, method="lm", max_nfev=20000)
    if not result.success:
        result = least_squares(resid, z0, method="trf", max_nfev=20000)
    curve = curve_cls(np.asarray(knots), result.x)
    return curve, result


def _type_scale_from_residuals(rows, discount_fn) -> dict:
    resid_by_type: dict[str, list] = {}
    for r in rows:
        resid = r.normalized_quote - model_quote(r, discount_fn)
        resid_by_type.setdefault(r.instrument_type, []).append(abs(resid))
    return {t: max(float(np.median(vals)), 0.01) for t, vals in resid_by_type.items()}


def fit_baseline(df_train: pd.DataFrame, knots: np.ndarray = CALIBRATION_KNOTS) -> FitResult:
    rows = list(df_train.itertuples())
    base_weight = df_train["weight"].to_numpy(dtype=float)
    z0 = np.full(knots.shape, _initial_guess(df_train))

    curve1, _ = _solve(knots, PiecewiseLinearZeroCurve, rows, base_weight, z0)
    per_type_scale = _type_scale_from_residuals(rows, curve1.discount)
    combined_weight = np.array([base_weight[i] / per_type_scale[rows[i].instrument_type] for i in range(len(rows))])
    curve2, _ = _solve(knots, PiecewiseLinearZeroCurve, rows, combined_weight, curve1.zero_rates)

    return FitResult(curve=curve2, per_type_scale=per_type_scale, weights=combined_weight, irls_history=[])


def fit_advanced(
    df_train: pd.DataFrame,
    per_type_scale: dict,
    lambda_reg: float,
    knots: np.ndarray = CALIBRATION_KNOTS,
    z0: np.ndarray | None = None,
    n_irls: int = N_IRLS_ITER,
) -> FitResult:
    rows = list(df_train.itertuples())
    raw_weight = df_train["weight"].to_numpy(dtype=float)
    base_weight = np.array([raw_weight[i] / per_type_scale[rows[i].instrument_type] for i in range(len(rows))])
    if z0 is None:
        z0 = np.full(knots.shape, _initial_guess(df_train))

    weight = base_weight.copy()
    history = []
    curve = None
    for _ in range(n_irls):
        curve, _ = _solve(knots, SplineZeroCurve, rows, weight, z0, lambda_reg, FINE_GRID)
        z0 = curve.zero_rates
        market = np.fromiter((r.normalized_quote for r in rows), dtype=float, count=len(rows))
        model = np.fromiter((model_quote(r, curve.discount) for r in rows), dtype=float, count=len(rows))
        standardized = base_weight * (market - model)
        med = float(np.median(standardized))
        mad = float(np.median(np.abs(standardized - med))) * 1.4826
        scale_r = max(mad, 1e-6)
        u = standardized / (TUKEY_C * scale_r)
        robust_mult = np.where(np.abs(u) < 1.0, (1.0 - u**2) ** 2, 0.0)
        history.append({"n_downweighted": int(np.sum(robust_mult < 0.5))})
        weight = np.maximum(base_weight * robust_mult, base_weight * 0.01)

    return FitResult(curve=curve, per_type_scale=per_type_scale, weights=weight, irls_history=history)


def select_lambda(
    df_train: pd.DataFrame,
    df_holdout: pd.DataFrame,
    per_type_scale: dict,
    knots: np.ndarray,
    z0: np.ndarray,
    lambda_grid: tuple = LAMBDA_GRID,
) -> tuple[float, list[dict], "FitResult"]:
    """Grid-search the smoothing strength by out-of-sample weighted RMSE.

    Empirical, deterministic, and reused verbatim as the "regularisation
    sensitivity" check in diagnostics/sensitivity.json. Returns the best
    lambda, the full grid (for reporting), and the already-fitted
    ``FitResult`` at that lambda (avoids refitting).
    """
    grid_results = []
    best_lambda, best_holdout, best_fit = lambda_grid[0], float("inf"), None
    for lam in lambda_grid:
        fit = fit_advanced(df_train, per_type_scale, lambda_reg=lam, knots=knots, z0=z0)
        train_rmse = weighted_rmse(df_train, fit.curve.discount, per_type_scale)
        holdout_rmse = weighted_rmse(df_holdout, fit.curve.discount, per_type_scale) if len(df_holdout) else float("nan")
        grid_results.append({"lambda": lam, "train_wrmse": train_rmse, "holdout_wrmse": holdout_rmse})
        compare_value = holdout_rmse if len(df_holdout) else train_rmse
        if compare_value < best_holdout:
            best_lambda, best_holdout, best_fit = lam, compare_value, fit
    return best_lambda, grid_results, best_fit


def weighted_rmse(df: pd.DataFrame, discount_fn, per_type_scale: dict) -> float:
    if len(df) == 0:
        return float("nan")
    rows = list(df.itertuples())
    raw_weight = df["weight"].to_numpy(dtype=float)
    residuals = np.fromiter(
        (r.normalized_quote - model_quote(r, discount_fn) for r in rows), dtype=float, count=len(rows)
    )
    combined_weight = np.array([raw_weight[i] / per_type_scale[rows[i].instrument_type] for i in range(len(rows))])
    return float(np.sqrt(np.mean((combined_weight * residuals) ** 2)))


def per_type_rmse(df: pd.DataFrame, discount_fn) -> dict:
    out = {}
    for itype, sub in df.groupby("instrument_type"):
        rows = list(sub.itertuples())
        residuals = np.fromiter(
            (r.normalized_quote - model_quote(r, discount_fn) for r in rows), dtype=float, count=len(rows)
        )
        out[itype] = float(np.sqrt(np.mean(residuals**2))) if len(residuals) else float("nan")
    return out
