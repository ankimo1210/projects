"""Full-truncation Euler Heston benchmark with explicit random drivers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from rough_volatility.config import HestonConfig

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class HestonPaths:
    """Heston variance/spot paths and standardized correlated spot driver."""

    times: FloatArray
    v: FloatArray
    s: FloatArray
    driver: FloatArray


def expected_variance(config: HestonConfig, t: ArrayLike) -> float | FloatArray:
    """Return the continuous-time Heston conditional variance mean."""
    config.validate()
    times = np.asarray(t, dtype=np.float64)
    if np.any(~np.isfinite(times)) or np.any(times < 0):
        raise ValueError("times must be finite and non-negative")
    result = config.theta + (config.v0 - config.theta) * np.exp(-config.kappa * times)
    return float(result) if result.ndim == 0 else np.asarray(result)


def simulate_given_normals(
    config: HestonConfig,
    s0: float,
    r: float,
    times: ArrayLike,
    z: ArrayLike,
    z_perp: ArrayLike,
) -> HestonPaths:
    """Simulate Heston paths using full truncation and supplied CRN arrays."""
    config.validate()
    if not np.isfinite(s0) or s0 <= 0 or not np.isfinite(r):
        raise ValueError("s0 must be positive and r finite")
    positive_times = np.asarray(times, dtype=np.float64)
    if (
        positive_times.ndim != 1
        or positive_times.size < 1
        or np.any(~np.isfinite(positive_times))
        or np.any(positive_times <= 0)
        or np.any(np.diff(positive_times) <= 0)
    ):
        raise ValueError("times must be finite, positive and strictly increasing")
    z_array = np.asarray(z, dtype=np.float64)
    z_perp_array = np.asarray(z_perp, dtype=np.float64)
    if (
        z_array.ndim != 2
        or z_array.shape != z_perp_array.shape
        or z_array.shape[1] != positive_times.size
    ):
        raise ValueError("normal arrays must share shape (n_paths, len(times))")
    if np.any(~np.isfinite(z_array)) or np.any(~np.isfinite(z_perp_array)):
        raise ValueError("normal arrays must be finite")

    n_paths, n_steps = z_array.shape
    all_times = np.r_[0.0, positive_times]
    intervals = np.diff(all_times)
    driver = config.rho * z_array + np.sqrt(max(0.0, 1.0 - config.rho**2)) * z_perp_array
    variance = np.empty((n_paths, n_steps + 1), dtype=np.float64)
    log_spot = np.empty((n_paths, n_steps + 1), dtype=np.float64)
    variance[:, 0] = config.v0
    log_spot[:, 0] = np.log(s0)
    for index, dt in enumerate(intervals):
        current = np.maximum(variance[:, index], 0.0)
        log_spot[:, index + 1] = (
            log_spot[:, index]
            + r * dt
            - 0.5 * current * dt
            + np.sqrt(current * dt) * driver[:, index]
        )
        candidate = (
            variance[:, index]
            + config.kappa * (config.theta - current) * dt
            + config.nu * np.sqrt(current * dt) * z_array[:, index]
        )
        variance[:, index + 1] = np.maximum(candidate, 0.0)
    return HestonPaths(
        times=all_times,
        v=variance,
        s=np.exp(log_spot),
        driver=np.asarray(driver),
    )
