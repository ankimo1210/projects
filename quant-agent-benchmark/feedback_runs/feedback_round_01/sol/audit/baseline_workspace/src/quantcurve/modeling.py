"""Baseline and robust curvature-penalized zero-curve estimators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares, minimize_scalar

from .config import CurveConfig
from .curve import ZeroCurve
from .pricing import model_quote


@dataclass
class FitResult:
    curve: ZeroCurve
    residuals: np.ndarray
    standardized_residuals: np.ndarray
    robust_multipliers: np.ndarray
    robust_scores: np.ndarray
    objective_cost: float
    success: bool
    message: str
    iterations: int


def quote_scales(rows: pd.DataFrame, config: CurveConfig | None = None) -> np.ndarray:
    cfg = config or CurveConfig()
    spread = np.asarray(rows["spread"], dtype=float)
    floors = np.where(rows["instrument_type"].to_numpy() == "bond", cfg.min_price_scale, cfg.min_rate_scale)
    half_spread = 0.5 * np.abs(spread)
    half_spread[~np.isfinite(half_spread)] = floors[~np.isfinite(half_spread)] * 2.0
    return np.maximum(half_spread, floors)


def repricing_residuals(rows: pd.DataFrame, curve: ZeroCurve) -> np.ndarray:
    return np.array([model_quote(row, curve) - float(row["normalized_quote"]) for _, row in rows.iterrows()])


def _standalone_zero(row: pd.Series) -> float:
    maturity = float(row["maturity_years"])
    quote = float(row["normalized_quote"])
    if row["instrument_type"] == "deposit":
        denominator = 1.0 + quote * maturity
        if denominator <= 0:
            raise ValueError("deposit quote implies non-positive discount factor")
        return np.log(denominator) / maturity

    def objective(zero: float) -> float:
        constant = ZeroCurve(np.array([0.0, max(30.0, maturity)]), np.array([zero, zero]), method="pchip")
        return model_quote(row, constant) - quote

    lower, upper = -0.10, 0.20
    try:
        return float(brentq(objective, lower, upper, maxiter=200))
    except ValueError:
        fallback = minimize_scalar(lambda z: objective(float(z)) ** 2, bounds=(lower, upper), method="bounded")
        return float(fallback.x)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    ordered_values = values[order]
    ordered_weights = weights[order]
    cutoff = 0.5 * ordered_weights.sum()
    return float(ordered_values[np.searchsorted(np.cumsum(ordered_weights), cutoff, side="left")])


def fit_baseline(rows: pd.DataFrame, config: CurveConfig | None = None) -> FitResult:
    """Fit maturity-bucket weighted medians of standalone flat yields."""
    cfg = config or CurveConfig()
    if len(rows) < 3:
        raise ValueError("at least three observations are required")
    records = []
    for _, row in rows.iterrows():
        try:
            value = _standalone_zero(row)
        except (ValueError, FloatingPointError, OverflowError):
            continue
        if np.isfinite(value):
            bucket = int(np.floor(float(row["maturity_years"]) / cfg.holdout_bucket_years + 1e-10))
            records.append((bucket, float(row["maturity_years"]), value, float(row["fit_weight"])))
    if len(records) < 3:
        raise ValueError("too few observations imply standalone yields")
    table = pd.DataFrame(records, columns=["bucket", "maturity", "zero", "weight"])
    points = []
    for _, group in table.groupby("bucket", sort=True):
        weights = np.maximum(group["weight"].to_numpy(), 1e-12)
        maturity = float(np.average(group["maturity"], weights=weights))
        zero = _weighted_median(group["zero"].to_numpy(), weights)
        points.append((maturity, zero))
    points.sort()
    knots = np.array([p[0] for p in points])
    rates = np.array([p[1] for p in points])
    unique_knots, inverse = np.unique(knots, return_inverse=True)
    if len(unique_knots) != len(knots):
        rates = np.array([np.mean(rates[inverse == i]) for i in range(len(unique_knots))])
        knots = unique_knots
    if knots[0] > 0:
        knots = np.r_[0.0, knots]
        rates = np.r_[rates[0], rates]
    if knots[-1] < 30.0:
        knots = np.r_[knots, 30.0]
        rates = np.r_[rates, rates[-1]]
    # A three-point median removes isolated single-instrument bucket spikes
    # while retaining broad shape; this is intentionally simpler than the
    # cash-flow-level advanced estimator.
    if len(rates) >= 3:
        rates = pd.Series(rates).rolling(3, center=True, min_periods=1).median().to_numpy()
    rates = np.clip(rates, cfg.parameter_lower_bound, cfg.parameter_upper_bound)
    curve = ZeroCurve(knots, rates, method="pchip")
    residuals = repricing_residuals(rows, curve)
    standardized = residuals / quote_scales(rows, cfg)
    return FitResult(curve, residuals, standardized, np.ones(len(rows)), standardized.copy(), float(np.dot(standardized, standardized)), True, "weighted standalone-yield PCHIP", 1)


def huber_multipliers(standardized_residuals: np.ndarray, threshold: float) -> np.ndarray:
    absolute = np.abs(np.asarray(standardized_residuals, dtype=float))
    result = np.ones_like(absolute)
    mask = absolute > threshold
    result[mask] = threshold / absolute[mask]
    return result


def robust_outlier_scores(rows: pd.DataFrame, standardized_residuals: np.ndarray) -> np.ndarray:
    """Center repeated maturity/type groups before Huber weighting.

    A coherent but unusual quoted tenor should move the curve, not be mistaken
    for many independent outliers. Single-observation groups retain raw scores.
    """
    scores = np.asarray(standardized_residuals, dtype=float).copy()
    grouping = pd.DataFrame(
        {
            "instrument_type": rows["instrument_type"].to_numpy(),
            "maturity": np.round(rows["maturity_years"].to_numpy(dtype=float), 6),
            "position": np.arange(len(rows)),
        }
    )
    base = rows["base_weight"].to_numpy(dtype=float)
    for _, group in grouping.groupby(["instrument_type", "maturity"]):
        positions = group["position"].to_numpy(dtype=int)
        if len(positions) >= 3:
            center = _weighted_median(scores[positions], np.maximum(base[positions], 1e-12))
            scores[positions] -= center
    return scores


def fit_advanced(
    rows: pd.DataFrame,
    config: CurveConfig | None = None,
    initial_curve: ZeroCurve | None = None,
) -> FitResult:
    """Fit spline zero knots using curvature penalty and IRLS Huber weights."""
    cfg = config or CurveConfig()
    if len(rows) < 3:
        raise ValueError("at least three observations are required")
    knot_max = max(30.0, float(rows["maturity_years"].max()))
    knots = np.array(sorted(set(k for k in cfg.knot_years if k < knot_max) | {knot_max}), dtype=float)
    if initial_curve is None:
        initial_curve = fit_baseline(rows, cfg).curve
    parameters = np.clip(np.asarray(initial_curve.zero(knots)), cfg.parameter_lower_bound, cfg.parameter_upper_bound)
    scales = quote_scales(rows, cfg)
    base_weights = np.asarray(rows["fit_weight"], dtype=float)
    robust = np.ones(len(rows))
    penalty_grid = np.linspace(max(knots[1], 1.0 / 12.0), knots[-1], 61)
    result = None
    iterations = 0
    for iteration in range(cfg.robust_iterations):
        iterations = iteration + 1

        def objective(params: np.ndarray) -> np.ndarray:
            curve = ZeroCurve(knots, params, method="cubic")
            residuals = repricing_residuals(rows, curve) / scales
            data_part = np.sqrt(np.maximum(base_weights * robust, 0.0)) * residuals
            curvature = np.asarray(curve.second_derivative(penalty_grid))
            penalty = np.sqrt(cfg.smoothing_lambda) * curvature / cfg.curvature_scale
            return np.r_[data_part, penalty]

        result = least_squares(
            objective,
            parameters,
            bounds=(cfg.parameter_lower_bound, cfg.parameter_upper_bound),
            method="trf",
            x_scale="jac",
            max_nfev=600,
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
        )
        parameters = result.x
        curve = ZeroCurve(knots, parameters, method="cubic")
        standardized = repricing_residuals(rows, curve) / scales
        scores = robust_outlier_scores(rows, standardized)
        updated = huber_multipliers(scores, cfg.outlier_threshold)
        if np.max(np.abs(updated - robust)) < 1e-5:
            robust = updated
            break
        robust = updated
    assert result is not None
    curve = ZeroCurve(knots, parameters, method="cubic")
    residuals = repricing_residuals(rows, curve)
    standardized = residuals / scales
    scores = robust_outlier_scores(rows, standardized)
    return FitResult(
        curve=curve,
        residuals=residuals,
        standardized_residuals=standardized,
        robust_multipliers=huber_multipliers(scores, cfg.outlier_threshold),
        robust_scores=scores,
        objective_cost=float(2.0 * result.cost),
        success=bool(result.success and np.all(np.isfinite(parameters))),
        message=str(result.message),
        iterations=iterations,
    )


def fit_metrics(rows: pd.DataFrame, curve: ZeroCurve, config: CurveConfig | None = None) -> dict[str, object]:
    cfg = config or CurveConfig()
    residuals = repricing_residuals(rows, curve)
    standardized = residuals / quote_scales(rows, cfg)
    weights = np.asarray(rows["base_weight"], dtype=float)
    denominator = max(float(weights.sum()), 1e-12)
    result: dict[str, object] = {
        "n": int(len(rows)),
        "weighted_normalized_rmse": float(np.sqrt(np.dot(weights, standardized**2) / denominator)),
        "normalized_mae": float(np.mean(np.abs(standardized))),
    }
    by_type: dict[str, object] = {}
    for instrument_type, group in rows.groupby("instrument_type"):
        indexes = rows.index.get_indexer(group.index)
        type_residuals = residuals[indexes]
        multiplier = 10_000.0 if instrument_type != "bond" else 1.0
        by_type[str(instrument_type)] = {
            "n": int(len(group)),
            "rmse": float(np.sqrt(np.mean(type_residuals**2)) * multiplier),
            "mae": float(np.mean(np.abs(type_residuals)) * multiplier),
            "unit": "bp" if instrument_type != "bond" else "price_points",
        }
    result["by_instrument_type"] = by_type
    return result


def maturity_holdout_mask(rows: pd.DataFrame, config: CurveConfig | None = None) -> np.ndarray:
    """Deterministic half-year maturity blocks; identical nearby maturities stay together."""
    cfg = config or CurveConfig()
    buckets = np.floor(np.asarray(rows["maturity_years"], dtype=float) / cfg.holdout_bucket_years + 1e-10).astype(int)
    mask = buckets % cfg.holdout_modulus == cfg.holdout_remainder
    if mask.sum() < 3 or (~mask).sum() < 3:
        unique = np.unique(buckets)
        held = set(unique[2::5])
        mask = np.array([bucket in held for bucket in buckets])
    return mask
