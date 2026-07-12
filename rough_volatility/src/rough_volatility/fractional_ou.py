"""Ordinary and fractional OU log-volatility simulators."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from rough_volatility.fbm import EmbeddingDiagnostics, davies_harte_fgn

FloatArray = NDArray[np.float64]


def _validate_common(
    kappa: float,
    noise_scale: float,
    n_steps: int,
    horizon: float,
    n_paths: int,
) -> None:
    if not np.isfinite(kappa) or kappa <= 0:
        raise ValueError("kappa must be positive")
    if not np.isfinite(noise_scale) or noise_scale < 0:
        raise ValueError("noise scale must be non-negative")
    if not isinstance(n_steps, (int, np.integer)) or n_steps < 1:
        raise ValueError("n_steps must be a positive integer")
    if not np.isfinite(horizon) or horizon <= 0:
        raise ValueError("horizon must be positive")
    if not isinstance(n_paths, (int, np.integer)) or n_paths < 1:
        raise ValueError("n_paths must be a positive integer")


def ou_exact(
    kappa: float,
    mean: float,
    sigma: float,
    x0: float,
    n_steps: int,
    horizon: float,
    n_paths: int,
    rng: np.random.Generator,
) -> FloatArray:
    """Simulate the exact Gaussian transition of a standard OU process."""
    _validate_common(kappa, sigma, n_steps, horizon, n_paths)
    if not np.isfinite(mean) or not np.isfinite(x0):
        raise ValueError("mean and x0 must be finite")
    dt = horizon / n_steps
    persistence = np.exp(-kappa * dt)
    innovation_std = sigma * np.sqrt(-np.expm1(-2.0 * kappa * dt) / (2.0 * kappa))
    innovations = rng.standard_normal((n_paths, n_steps))
    paths = np.empty((n_paths, n_steps + 1), dtype=np.float64)
    paths[:, 0] = x0
    for index in range(n_steps):
        paths[:, index + 1] = (
            mean + persistence * (paths[:, index] - mean) + innovation_std * innovations[:, index]
        )
    return paths


def fou_euler(
    kappa: float,
    mean: float,
    nu: float,
    h: float,
    x0: float,
    n_steps: int,
    horizon: float,
    n_paths: int,
    rng: np.random.Generator,
    *,
    burn_in_steps: int = 0,
) -> tuple[FloatArray, EmbeddingDiagnostics]:
    """Euler approximation to ``dX=-kappa(X-mean)dt+nu*dB^H``.

    ``burn_in_steps`` are simulated with the same step size and then removed;
    the returned array always contains ``n_steps + 1`` observations.
    """
    _validate_common(kappa, nu, n_steps, horizon, n_paths)
    if not np.isfinite(mean) or not np.isfinite(x0):
        raise ValueError("mean and x0 must be finite")
    if not np.isfinite(h) or not 0 < h < 1:
        raise ValueError("Hurst exponent must lie strictly between 0 and 1")
    if not isinstance(burn_in_steps, (int, np.integer)) or burn_in_steps < 0:
        raise ValueError("burn_in_steps must be a non-negative integer")

    total_steps = n_steps + burn_in_steps
    dt = horizon / n_steps
    fgn, diagnostics = davies_harte_fgn(h, total_steps, n_paths, rng)
    fgn *= dt**h
    paths = np.empty((n_paths, total_steps + 1), dtype=np.float64)
    paths[:, 0] = x0
    drift_scale = kappa * dt
    for index in range(total_steps):
        paths[:, index + 1] = (
            paths[:, index] - drift_scale * (paths[:, index] - mean) + nu * fgn[:, index]
        )
    return paths[:, burn_in_steps:].copy(), diagnostics
