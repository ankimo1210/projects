"""Exact-grid joint-Gaussian rough Bergomi-style simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import cholesky
from scipy.special import hyp2f1

from rough_volatility.config import BergomiConfig
from rough_volatility.random import stream

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class VolterraOperators:
    """Schur factors coupling Brownian increments to the Volterra driver."""

    times: FloatArray
    cross_op: FloatArray
    residual_chol: FloatArray
    diag_error: float
    jitter_used: float


@dataclass(frozen=True)
class RoughBergomiPaths:
    """Full path samples including time zero and the standardized spot driver."""

    times: FloatArray
    v: FloatArray
    s: FloatArray
    driver: FloatArray


@dataclass(frozen=True)
class TerminalResult:
    """Memory-bounded terminal samples plus a small path reservoir."""

    s_by_maturity: dict[int, FloatArray]
    v_sample: FloatArray
    s_sample: FloatArray
    realized_variance: FloatArray
    ev_check: dict[str, Any]


def _validate_h_and_times(h: float, times: ArrayLike) -> FloatArray:
    if not np.isfinite(h) or not 0 < h < 1:
        raise ValueError("Hurst exponent must lie strictly between 0 and 1")
    values = np.asarray(times, dtype=np.float64)
    if (
        values.ndim != 1
        or values.size < 1
        or np.any(~np.isfinite(values))
        or np.any(values <= 0)
        or np.any(np.diff(values) <= 0)
    ):
        raise ValueError("times must be a finite, positive, strictly increasing vector")
    return values


def volterra_covariance(h: float, times: ArrayLike) -> FloatArray:
    r"""Covariance of the normalized Riemann--Liouville Volterra process.

    For :math:`s\le t`,

    .. math::

       \operatorname{Cov}(\widetilde W_s,\widetilde W_t)
       =\frac{2H}{H+1/2}s^{H+1/2}t^{H-1/2}
        {}_2F_1(1/2-H,1;H+3/2;s/t).
    """
    values = _validate_h_and_times(h, times)
    smaller = np.minimum.outer(values, values)
    larger = np.maximum.outer(values, values)
    ratio = smaller / larger
    covariance = (
        (2.0 * h / (h + 0.5))
        * smaller ** (h + 0.5)
        * larger ** (h - 0.5)
        * hyp2f1(0.5 - h, 1.0, h + 1.5, ratio)
    )
    np.fill_diagonal(covariance, values ** (2.0 * h))
    return np.asarray(0.5 * (covariance + covariance.T), dtype=np.float64)


def volterra_increment_cross_covariance(h: float, times: ArrayLike) -> FloatArray:
    r"""Return ``Cov(W_tilde(t_j), Delta W_k)`` for grid intervals."""
    values = _validate_h_and_times(h, times)
    left = np.r_[0.0, values[:-1]]
    row_times = values[:, None]
    power = h + 0.5
    first = np.maximum(row_times - left[None, :], 0.0) ** power
    second = np.maximum(row_times - values[None, :], 0.0) ** power
    factor = np.sqrt(2.0 * h) / power
    return np.asarray(factor * (first - second), dtype=np.float64)


def build_operators(h: float, times: ArrayLike) -> VolterraOperators:
    """Build the exact Schur factorization for ``(Delta W, W_tilde)``."""
    values = _validate_h_and_times(h, times)
    intervals = np.diff(np.r_[0.0, values])
    covariance = volterra_covariance(h, values)
    cross_covariance = volterra_increment_cross_covariance(h, values)
    cross_op = cross_covariance / np.sqrt(intervals)[None, :]
    residual = covariance - cross_op @ cross_op.T
    residual = 0.5 * (residual + residual.T)
    jitter_used = 0.0
    try:
        residual_chol = cholesky(residual, lower=True, check_finite=False)
    except np.linalg.LinAlgError:
        jitter_used = 1e-12 * float(np.trace(covariance)) / values.size
        try:
            residual_chol = cholesky(
                residual + jitter_used * np.eye(values.size),
                lower=True,
                check_finite=False,
            )
        except np.linalg.LinAlgError as exc:
            raise np.linalg.LinAlgError(
                "Volterra Schur complement is not positive definite"
            ) from exc

    reconstructed_diagonal = np.sum(cross_op**2, axis=1) + np.sum(residual_chol**2, axis=1)
    diag_error = float(np.max(np.abs(reconstructed_diagonal - values ** (2.0 * h))))
    return VolterraOperators(
        times=values.copy(),
        cross_op=np.asarray(cross_op),
        residual_chol=np.asarray(residual_chol),
        diag_error=diag_error,
        jitter_used=jitter_used,
    )


def _forward_variance(config: BergomiConfig, times: FloatArray) -> FloatArray:
    if not config.forward_variance:
        return np.full(times.shape, config.xi0, dtype=np.float64)
    points = np.asarray(config.forward_variance, dtype=np.float64)
    return np.interp(times, points[:, 0], points[:, 1])


def simulate_given_normals(
    config: BergomiConfig,
    operators: VolterraOperators,
    z: ArrayLike,
    z_perp: ArrayLike,
    z_residual: ArrayLike,
) -> RoughBergomiPaths:
    """Simulate paths from explicit normals, enabling exact CRN comparisons."""
    config.validate()
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (z, z_perp, z_residual))
    if any(array.ndim != 2 for array in arrays):
        raise ValueError("normal arrays must all be two-dimensional")
    if arrays[0].shape != arrays[1].shape or arrays[0].shape != arrays[2].shape:
        raise ValueError("normal arrays must have identical shapes")
    n_paths, n_steps = arrays[0].shape
    if n_steps != config.n_steps or operators.times.size != n_steps:
        raise ValueError("normal/operator grid does not match config.n_steps")
    if (
        np.any(~np.isfinite(arrays[0]))
        or np.any(~np.isfinite(arrays[1]))
        or np.any(~np.isfinite(arrays[2]))
    ):
        raise ValueError("normal arrays must be finite")

    z_array, z_perp_array, residual_array = arrays
    volterra = z_array @ operators.cross_op.T + residual_array @ operators.residual_chol.T
    positive_times = operators.times
    all_times = np.r_[0.0, positive_times]
    forward_variance = _forward_variance(config, all_times)
    variance = np.empty((n_paths, n_steps + 1), dtype=np.float64)
    variance[:, 0] = forward_variance[0]
    variance[:, 1:] = forward_variance[None, 1:] * np.exp(
        config.eta * volterra - 0.5 * config.eta**2 * positive_times[None, :] ** (2.0 * config.h)
    )

    intervals = np.diff(all_times)
    driver = config.rho * z_array + np.sqrt(max(0.0, 1.0 - config.rho**2)) * z_perp_array
    log_increments = (
        config.r * intervals[None, :]
        - 0.5 * variance[:, :-1] * intervals[None, :]
        + np.sqrt(variance[:, :-1] * intervals[None, :]) * driver
    )
    spot = np.empty((n_paths, n_steps + 1), dtype=np.float64)
    spot[:, 0] = config.s0
    spot[:, 1:] = config.s0 * np.exp(np.cumsum(log_increments, axis=1))
    return RoughBergomiPaths(
        times=all_times,
        v=variance,
        s=spot,
        driver=np.asarray(driver),
    )


def simulate_chunked(
    config: BergomiConfig,
    operators: VolterraOperators,
    seed: int,
    *,
    maturity_indices: tuple[int, ...] | list[int] | NDArray[np.integer],
    keep_paths: int | None = None,
) -> TerminalResult:
    """Run seeded Monte Carlo in chunks without changing the random sequence."""
    config.validate()
    indices = tuple(int(index) for index in maturity_indices)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("maturity_indices must be non-empty and unique")
    if any(index < 1 or index > config.n_steps for index in indices):
        raise ValueError("maturity index lies outside the simulation grid")
    requested_keep = config.keep_paths if keep_paths is None else keep_paths
    if requested_keep < 0:
        raise ValueError("keep_paths cannot be negative")
    n_keep = min(int(requested_keep), config.n_paths)

    s_by_maturity = {index: np.empty(config.n_paths, dtype=np.float64) for index in indices}
    v_by_maturity = {index: np.empty(config.n_paths, dtype=np.float64) for index in indices}
    s_sample = np.empty((n_keep, config.n_steps + 1), dtype=np.float64)
    v_sample = np.empty((n_keep, config.n_steps + 1), dtype=np.float64)
    realized_variance = np.empty(config.n_paths, dtype=np.float64)
    z_generator = stream(seed, "asset_z")
    z_perp_generator = stream(seed, "asset_zperp")
    residual_generator = stream(seed, "volterra_residual")

    for start in range(0, config.n_paths, config.chunk_size):
        stop = min(start + config.chunk_size, config.n_paths)
        count = stop - start
        paths = simulate_given_normals(
            config,
            operators,
            z_generator.standard_normal((count, config.n_steps)),
            z_perp_generator.standard_normal((count, config.n_steps)),
            residual_generator.standard_normal((count, config.n_steps)),
        )
        for index in indices:
            s_by_maturity[index][start:stop] = paths.s[:, index]
            v_by_maturity[index][start:stop] = paths.v[:, index]
        realized_variance[start:stop] = np.sum(np.diff(np.log(paths.s), axis=1) ** 2, axis=1)
        sample_stop = min(stop, n_keep)
        if start < sample_stop:
            local_count = sample_stop - start
            s_sample[start:sample_stop] = paths.s[:local_count]
            v_sample[start:sample_stop] = paths.v[:local_count]

    all_times = np.r_[0.0, operators.times]
    expected_variance = _forward_variance(config, all_times)
    variance_checks: list[dict[str, float | int]] = []
    spot_checks: list[dict[str, float | int]] = []
    for index in indices:
        variance_values = v_by_maturity[index]
        variance_se = float(variance_values.std(ddof=1) / np.sqrt(config.n_paths))
        variance_error = float(variance_values.mean() - expected_variance[index])
        variance_checks.append(
            {
                "index": index,
                "time": float(all_times[index]),
                "mean": float(variance_values.mean()),
                "expected": float(expected_variance[index]),
                "standard_error": variance_se,
                "z_score": variance_error / variance_se if variance_se > 0 else 0.0,
            }
        )
        spot_values = s_by_maturity[index]
        spot_se = float(spot_values.std(ddof=1) / np.sqrt(config.n_paths))
        expected_spot = config.s0 * np.exp(config.r * all_times[index])
        spot_checks.append(
            {
                "index": index,
                "time": float(all_times[index]),
                "mean": float(spot_values.mean()),
                "expected": float(expected_spot),
                "standard_error": spot_se,
                "z_score": (float(spot_values.mean()) - expected_spot) / spot_se
                if spot_se > 0
                else 0.0,
            }
        )
    return TerminalResult(
        s_by_maturity=s_by_maturity,
        v_sample=v_sample,
        s_sample=s_sample,
        realized_variance=realized_variance,
        ev_check={
            "variance": variance_checks,
            "spot": spot_checks,
            "operator_diag_error": operators.diag_error,
            "operator_jitter": operators.jitter_used,
            "sample_size": config.n_paths,
        },
    )
