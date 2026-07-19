"""Synthetic temperature dynamics, weather premia, and station basis risk.

Weather indices are not generally tradable underlyings, so the module exposes
the chosen premium principle rather than pretending that a unique
risk-neutral price exists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

DegreeDayKind = Literal["hdd", "cdd"]
PremiumPrinciple = Literal["expected_value", "standard_deviation", "exponential"]


def seasonal_temperature_mean(
    day,
    *,
    intercept: float = 15.0,
    trend_per_year: float = 0.0,
    amplitude: float = 10.0,
    peak_day: float = 200.0,
    period: float = 365.25,
) -> np.ndarray:
    """Linear trend plus annual cosine seasonality in degrees Celsius."""

    days = np.asarray(day, dtype=float)
    if np.any(~np.isfinite(days)):
        raise ValueError("day must be finite")
    if not np.isfinite(period) or period <= 0.0:
        raise ValueError("period must be finite and positive")
    values = (
        float(intercept)
        + float(trend_per_year) * days / period
        + float(amplitude) * np.cos(2.0 * np.pi * (days - float(peak_day)) / period)
    )
    return np.asarray(values, dtype=float)


def _mean_path(mean) -> np.ndarray:
    values = np.asarray(mean, dtype=float)
    if values.ndim != 1 or values.size < 1 or np.any(~np.isfinite(values)):
        raise ValueError("mean must be a non-empty finite 1-D path")
    return values


def simulate_ou_temperature(
    mean,
    initial_temperature: float,
    *,
    kappa: float = 0.20,
    sigma: float = 2.0,
    n_paths: int = 1_000,
    seed: int = 0,
) -> np.ndarray:
    """Exact-discretized daily OU deviations around a supplied seasonal mean."""

    mean_path = _mean_path(mean)
    if not np.isfinite(kappa) or kappa < 0.0:
        raise ValueError("kappa must be finite and non-negative")
    if not np.isfinite(sigma) or sigma < 0.0:
        raise ValueError("sigma must be finite and non-negative")
    if not isinstance(n_paths, int) or n_paths < 1:
        raise ValueError("n_paths must be a positive integer")
    if not np.isfinite(initial_temperature):
        raise ValueError("initial_temperature must be finite")
    rng = np.random.default_rng(seed)
    phi = math.exp(-kappa)
    innovation_std = sigma if kappa == 0.0 else sigma * math.sqrt((1.0 - phi**2) / (2.0 * kappa))
    output = np.empty((n_paths, mean_path.size))
    deviation = np.full(n_paths, float(initial_temperature) - mean_path[0])
    output[:, 0] = initial_temperature
    for i in range(1, mean_path.size):
        deviation = phi * deviation + innovation_std * rng.standard_normal(n_paths)
        output[:, i] = mean_path[i] + deviation
    return output


def fractional_noise_autocovariance(n_lags: int, hurst: float) -> np.ndarray:
    """Autocovariance of unit fractional-Gaussian-noise increments."""

    if not isinstance(n_lags, int) or n_lags < 1:
        raise ValueError("n_lags must be a positive integer")
    if not np.isfinite(hurst) or not 0.0 < hurst < 1.0:
        raise ValueError("hurst must lie in (0, 1)")
    k = np.arange(n_lags, dtype=float)
    covariance = 0.5 * (
        np.abs(k + 1.0) ** (2.0 * hurst)
        - 2.0 * np.abs(k) ** (2.0 * hurst)
        + np.abs(k - 1.0) ** (2.0 * hurst)
    )
    return covariance


def simulate_fractional_ou_temperature(
    mean,
    initial_temperature: float,
    *,
    kappa: float = 0.20,
    sigma: float = 1.0,
    hurst: float = 0.75,
    n_paths: int = 500,
    seed: int = 0,
) -> np.ndarray:
    """Small-sample fractional-OU proxy using correlated fGn innovations.

    Cholesky simulation is intentionally aimed at educational horizons, not
    production-scale weather books.
    """

    mean_path = _mean_path(mean)
    if not np.isfinite(kappa) or kappa < 0.0:
        raise ValueError("kappa must be finite and non-negative")
    if not np.isfinite(sigma) or sigma < 0.0:
        raise ValueError("sigma must be finite and non-negative")
    if not isinstance(n_paths, int) or n_paths < 1:
        raise ValueError("n_paths must be a positive integer")
    if mean_path.size == 1:
        return np.full((n_paths, 1), float(initial_temperature))
    covariance = fractional_noise_autocovariance(mean_path.size - 1, hurst)
    indices = np.arange(mean_path.size - 1)
    matrix = covariance[np.abs(indices[:, None] - indices[None, :])]
    cholesky = np.linalg.cholesky(matrix + 1e-12 * np.eye(matrix.shape[0]))
    rng = np.random.default_rng(seed)
    innovations = rng.standard_normal((n_paths, matrix.shape[0])) @ cholesky.T
    phi = math.exp(-kappa)
    output = np.empty((n_paths, mean_path.size))
    deviation = np.full(n_paths, float(initial_temperature) - mean_path[0])
    output[:, 0] = initial_temperature
    for i in range(1, mean_path.size):
        deviation = phi * deviation + sigma * innovations[:, i - 1]
        output[:, i] = mean_path[i] + deviation
    return output


def degree_day_index(
    temperatures, *, base: float = 18.0, kind: DegreeDayKind = "hdd"
) -> np.ndarray:
    """Heating or cooling degree days summed over the last array axis."""

    values = np.asarray(temperatures, dtype=float)
    if values.size == 0 or np.any(~np.isfinite(values)):
        raise ValueError("temperatures must be non-empty and finite")
    if kind == "hdd":
        daily = np.maximum(float(base) - values, 0.0)
    elif kind == "cdd":
        daily = np.maximum(values - float(base), 0.0)
    else:
        raise ValueError("kind must be 'hdd' or 'cdd'")
    return np.sum(daily, axis=-1)


def weather_contract_premium(
    payoffs,
    *,
    principle: PremiumPrinciple = "expected_value",
    loading: float = 0.0,
    risk_aversion: float = 0.0,
) -> float:
    """Seller premium under an explicitly selected incomplete-market principle."""

    values = np.asarray(payoffs, dtype=float)
    if values.size == 0 or np.any(~np.isfinite(values)):
        raise ValueError("payoffs must be non-empty and finite")
    values = values.ravel()
    expected = float(np.mean(values))
    if principle == "expected_value":
        if not np.isfinite(loading) or loading < 0.0:
            raise ValueError("loading must be finite and non-negative")
        return float((1.0 + loading) * expected)
    if principle == "standard_deviation":
        if not np.isfinite(loading) or loading < 0.0:
            raise ValueError("loading must be finite and non-negative")
        return float(expected + loading * np.std(values, ddof=0))
    if principle == "exponential":
        if not np.isfinite(risk_aversion) or risk_aversion <= 0.0:
            raise ValueError("risk_aversion must be finite and positive")
        scaled = risk_aversion * values
        maximum = float(np.max(scaled))
        return float((maximum + math.log(np.mean(np.exp(scaled - maximum)))) / risk_aversion)
    raise ValueError("unknown premium principle")


def station_index(temperatures, weights) -> np.ndarray:
    """Weighted station basket; the final axis enumerates stations."""

    values = np.asarray(temperatures, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.ndim < 1 or weights.ndim != 1 or values.shape[-1] != weights.size:
        raise ValueError("weights must match the final station axis")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)):
        raise ValueError("temperatures and weights must be finite")
    if np.any(weights < 0.0) or not np.isclose(np.sum(weights), 1.0):
        raise ValueError("weights must be non-negative and sum to one")
    return np.sum(values * weights, axis=-1)


@dataclass(frozen=True)
class BasisRiskReport:
    """Minimum-variance basis-hedge summary: ratio, correlation, variance reduction."""

    hedge_ratio: float
    correlation: float
    mismatch_rmse: float
    unhedged_std: float
    residual_std: float
    variance_reduction: float


def optimal_basis_hedge(target_payoff, station_payoff) -> BasisRiskReport:
    """Minimum-variance station-index hedge for a target-location payoff."""

    target = np.asarray(target_payoff, dtype=float).ravel()
    station = np.asarray(station_payoff, dtype=float).ravel()
    if target.size < 2 or target.shape != station.shape:
        raise ValueError("payoffs must have the same shape with at least two scenarios")
    if np.any(~np.isfinite(target)) or np.any(~np.isfinite(station)):
        raise ValueError("payoffs must be finite")
    station_variance = float(np.var(station, ddof=0))
    target_variance = float(np.var(target, ddof=0))
    covariance = float(np.mean((target - target.mean()) * (station - station.mean())))
    hedge_ratio = covariance / station_variance if station_variance > 0.0 else 0.0
    residual = (target - target.mean()) - hedge_ratio * (station - station.mean())
    residual_std = float(np.std(residual, ddof=0))
    unhedged_std = math.sqrt(target_variance)
    if target_variance > 0.0 and station_variance > 0.0:
        correlation = covariance / math.sqrt(target_variance * station_variance)
    else:
        correlation = 0.0
    reduction = 0.0 if target_variance == 0.0 else 1.0 - residual_std**2 / target_variance
    return BasisRiskReport(
        hedge_ratio=float(hedge_ratio),
        correlation=float(correlation),
        mismatch_rmse=float(np.sqrt(np.mean((target - station) ** 2))),
        unhedged_std=float(unhedged_std),
        residual_std=residual_std,
        variance_reduction=float(reduction),
    )
