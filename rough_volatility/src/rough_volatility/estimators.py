"""Log-log regressions and classical roughness estimators."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from rough_volatility.diagnostics import log_spaced_lags, structure_function

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class LogLogFit:
    """Diagnostics for a (possibly weighted) log-log linear regression."""

    slope: float
    intercept: float
    slope_se: float
    intercept_se: float
    r_squared: float
    n_observations: int
    x_min: float
    x_max: float


@dataclass(frozen=True)
class HurstEstimate:
    """Hurst estimate and its regression-based standard error."""

    h_hat: float
    se: float
    estimator: str
    fit: LogLogFit


def loglog_ols(
    x: ArrayLike,
    y: ArrayLike,
    weights: ArrayLike | None = None,
) -> LogLogFit:
    """Fit ``log(y) = intercept + slope*log(x)`` by OLS or WLS."""
    x_values = np.asarray(x, dtype=np.float64)
    y_values = np.asarray(y, dtype=np.float64)
    if x_values.shape != y_values.shape or x_values.ndim != 1:
        raise ValueError("x and y must be one-dimensional arrays of equal shape")
    if weights is None:
        weight_values = np.ones_like(x_values)
    else:
        weight_values = np.asarray(weights, dtype=np.float64)
        if weight_values.shape != x_values.shape:
            raise ValueError("weights must have the same shape as x and y")

    valid = (
        np.isfinite(x_values)
        & np.isfinite(y_values)
        & np.isfinite(weight_values)
        & (x_values > 0)
        & (y_values > 0)
        & (weight_values > 0)
    )
    x_valid = x_values[valid]
    y_valid = y_values[valid]
    weight_valid = weight_values[valid]
    if x_valid.size < 3:
        raise ValueError("at least three positive finite observations are required")

    log_x = np.log(x_valid)
    log_y = np.log(y_valid)
    design = np.column_stack((np.ones_like(log_x), log_x))
    weighted_design = design * weight_valid[:, None]
    information = design.T @ weighted_design
    try:
        inverse_information = np.linalg.inv(information)
    except np.linalg.LinAlgError as exc:
        raise ValueError("log-log regression design is singular") from exc
    coefficients = inverse_information @ (weighted_design.T @ log_y)
    fitted = design @ coefficients
    residual = log_y - fitted
    degrees_freedom = log_x.size - 2
    residual_variance = float(np.sum(weight_valid * residual**2) / degrees_freedom)
    covariance = residual_variance * inverse_information

    weighted_mean = float(np.average(log_y, weights=weight_valid))
    total_sum = float(np.sum(weight_valid * (log_y - weighted_mean) ** 2))
    residual_sum = float(np.sum(weight_valid * residual**2))
    r_squared = 1.0 if total_sum <= np.finfo(float).eps else 1.0 - residual_sum / total_sum
    return LogLogFit(
        slope=float(coefficients[1]),
        intercept=float(coefficients[0]),
        slope_se=float(np.sqrt(max(covariance[1, 1], 0.0))),
        intercept_se=float(np.sqrt(max(covariance[0, 0], 0.0))),
        r_squared=r_squared,
        n_observations=int(log_x.size),
        x_min=float(x_valid.min()),
        x_max=float(x_valid.max()),
    )


def _path_and_lags(path: ArrayLike, lags: ArrayLike | None) -> tuple[FloatArray, FloatArray]:
    values = np.asarray(path, dtype=np.float64)
    if values.ndim != 1 or values.size < 32 or not np.all(np.isfinite(values)):
        raise ValueError("path must be a finite one-dimensional series of length >= 32")
    if lags is None:
        lag_values = log_spaced_lags(values.size, n_lags=15, max_frac=0.10)
    else:
        lag_values = np.asarray(lags, dtype=np.int64)
    if lag_values.size < 3:
        raise ValueError("at least three lags are required")
    return values, np.asarray(lag_values, dtype=np.float64)


def hurst_variogram(path: ArrayLike, lags: ArrayLike | None = None) -> HurstEstimate:
    """Estimate H from the second-order variogram slope ``2H``."""
    values, lag_values = _path_and_lags(path, lags)
    moments = structure_function(values, (2.0,), lag_values.astype(int))[0]
    fit = loglog_ols(lag_values, moments)
    return HurstEstimate(
        h_hat=0.5 * fit.slope,
        se=0.5 * fit.slope_se,
        estimator="variogram",
        fit=fit,
    )


def hurst_madogram(path: ArrayLike, lags: ArrayLike | None = None) -> HurstEstimate:
    """Estimate H from the first absolute-moment (madogram) slope ``H``."""
    values, lag_values = _path_and_lags(path, lags)
    moments = structure_function(values, (1.0,), lag_values.astype(int))[0]
    fit = loglog_ols(lag_values, moments)
    return HurstEstimate(
        h_hat=fit.slope,
        se=fit.slope_se,
        estimator="madogram",
        fit=fit,
    )


def hurst_aggregated_variance(
    increments: ArrayLike,
    block_sizes: ArrayLike | None = None,
) -> HurstEstimate:
    """Estimate H from ``Var(block mean) proportional to m**(2H-2)``."""
    values = np.asarray(increments, dtype=np.float64)
    if values.ndim != 1 or values.size < 64 or not np.all(np.isfinite(values)):
        raise ValueError("increments must be a finite series of length >= 64")
    values = values - values.mean()
    if block_sizes is None:
        maximum = max(4, values.size // 32)
        sizes = np.unique(np.rint(np.geomspace(2, maximum, 15)).astype(np.int64))
    else:
        sizes = np.asarray(block_sizes, dtype=np.int64)
    valid_sizes: list[int] = []
    variances: list[float] = []
    for size in sizes:
        n_blocks = values.size // int(size)
        if size < 1 or n_blocks < 8:
            continue
        means = values[: n_blocks * size].reshape(n_blocks, size).mean(axis=1)
        variance = float(means.var(ddof=1))
        if variance > 0 and np.isfinite(variance):
            valid_sizes.append(int(size))
            variances.append(variance)
    if len(valid_sizes) < 3:
        raise ValueError("at least three usable block sizes are required")
    fit = loglog_ols(np.asarray(valid_sizes), np.asarray(variances))
    return HurstEstimate(
        h_hat=0.5 * (fit.slope + 2.0),
        se=0.5 * fit.slope_se,
        estimator="aggregated_variance",
        fit=fit,
    )


ESTIMATORS: dict[str, Callable[..., HurstEstimate]] = {
    "variogram": hurst_variogram,
    "madogram": hurst_madogram,
    "aggregated_variance": hurst_aggregated_variance,
}
