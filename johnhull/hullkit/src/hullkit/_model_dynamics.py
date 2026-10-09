"""Fixed-driver monthly Heston and local-volatility paths for RB-F04.

Times are in years and variances are instantaneous annual variances. The
caller owns random-number generation: these routines consume the supplied
two-factor standardized normal increments without generating or modifying
them. Twelve equally spaced observations plus the initial spot are retained,
regardless of the number of internal Euler steps.
"""

from typing import Protocol

import numpy as np


class _Parameters(Protocol):
    spot: float
    rate: float
    dividend_yield: float
    v0: float
    kappa: float
    theta: float
    xi: float
    rho: float


class _VarianceSurface(Protocol):
    def evaluate(self, t: float, spots: np.ndarray) -> dict: ...


def aggregate_normals(z: np.ndarray, factor: int) -> np.ndarray:
    """Sum consecutive fine normal increments and divide by sqrt(factor).

    ``z`` has shape ``(paths, steps, 2)`` and ``factor`` must be a positive
    integer dividing ``steps``. Scaling by the coarse time step therefore
    recovers the sum of the corresponding fine Brownian increments. The
    source array is left unchanged, including any nonfinite path inputs.
    """
    normals = _normals(z)
    if not np.isfinite(factor) or factor < 1 or int(factor) != factor:
        raise ValueError("factor must be a positive integer")
    factor = int(factor)
    paths, steps, factors = normals.shape
    if steps % factor:
        raise ValueError("factor must divide the number of steps")
    return normals.reshape(paths, steps // factor, factor, factors).sum(axis=2) / np.sqrt(factor)


def _normals(z: np.ndarray) -> np.ndarray:
    normals = np.asarray(z, dtype=float)
    if normals.ndim != 3 or normals.shape[2] != 2 or normals.shape[1] == 0:
        raise ValueError("normal increments must have shape (paths, positive steps, 2)")
    return normals


def _prepare(parameters: _Parameters, z: np.ndarray, expiry: float) -> tuple:
    normals = _normals(z)
    if normals.shape[1] % 12:
        raise ValueError("the number of steps must be a multiple of twelve")
    if not np.isfinite(expiry) or expiry <= 0:
        raise ValueError("expiry must be finite and positive")
    parameter_values = [
        parameters.spot,
        parameters.rate,
        parameters.dividend_yield,
        parameters.v0,
        parameters.kappa,
        parameters.theta,
        parameters.xi,
        parameters.rho,
    ]
    if not np.isfinite(parameter_values).all():
        raise ValueError("model parameters must be finite")
    if (
        parameters.spot <= 0
        or min(parameters.v0, parameters.kappa, parameters.theta, parameters.xi) < 0
        or abs(parameters.rho) > 1
    ):
        raise ValueError(
            "spot must be positive, variances/rates of variance nonnegative, |rho| <= 1"
        )
    paths, steps, _ = normals.shape
    observations = np.full((paths, 13), np.nan)
    observations[:, 0] = parameters.spot
    failures = np.zeros(paths, dtype=bool)
    reasons = [""] * paths
    return normals, expiry / steps, observations, failures, reasons


def _mark(failures: np.ndarray, reasons: list[str], indices: np.ndarray, reason: str) -> None:
    """Retain each cause reported on the failing step, including concurrent causes."""
    failures[indices] = True
    for index in indices:
        reasons[index] = f"{reasons[index]};{reason}" if reasons[index] else reason


def _result(
    observations: np.ndarray, failures: np.ndarray, reasons: list[str], expiry: float
) -> dict:
    return {
        "observations": observations,
        "observation_times": np.arange(13, dtype=float) * expiry / 12.0,
        "failures": failures,
        "failure_reasons": np.asarray(reasons, dtype=str),
    }


def heston_monthly(parameters: _Parameters, z: np.ndarray, expiry: float = 1.0) -> dict:
    """Simulate full-truncation log-Euler Heston with explicit normal drivers.

    Stock uses the first shock; variance uses ``rho*z1 + sqrt(1-rho**2)*z2``.
    Full truncation applies only when computing the drift and diffusion;
    negative variance states persist. ``negative_variance_counts`` counts
    finite negative states after every step, including the terminal step,
    and ``variance_observations`` retains the actual monthly states.

    ``observations`` has shape ``(paths, 13)`` with the initial spot in column
    zero. A failed path retains earlier observations, has NaN observations
    from its failing step onward, and keeps all causes on that step in the
    semicolon-separated ``failure_reasons``. ``failures`` is a per-path
    boolean array; failed paths are never removed or filled with zero.
    """
    normals, dt, observations, failures, reasons = _prepare(parameters, z, expiry)
    paths, steps, _ = normals.shape
    stock = np.full(paths, parameters.spot, dtype=float)
    variance = np.full(paths, parameters.v0, dtype=float)
    variance_observations = np.full_like(observations, np.nan)
    variance_observations[:, 0] = parameters.v0
    negative_counts = np.zeros(paths, dtype=np.int64)
    sqrt_dt = np.sqrt(dt)
    independent_weight = np.sqrt(1.0 - parameters.rho**2)
    observation_stride = steps // 12

    for step in range(steps):
        indices = np.flatnonzero(~failures)
        if not indices.size:
            break
        shocks = normals[indices, step]
        finite_driver = np.isfinite(shocks).all(axis=1)
        _mark(failures, reasons, indices[~finite_driver], "nonfinite_driver")
        indices = indices[finite_driver]
        shocks = shocks[finite_driver]
        positive_variance = np.maximum(variance[indices], 0.0)
        sqrt_variance_dt = np.sqrt(positive_variance) * sqrt_dt
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            stock[indices] *= np.exp(
                (parameters.rate - parameters.dividend_yield - 0.5 * positive_variance) * dt
                + sqrt_variance_dt * shocks[:, 0]
            )
            variance[indices] += parameters.kappa * (
                parameters.theta - positive_variance
            ) * dt + parameters.xi * sqrt_variance_dt * (
                parameters.rho * shocks[:, 0] + independent_weight * shocks[:, 1]
            )
        negative_counts[indices] += np.isfinite(variance[indices]) & (variance[indices] < 0)
        _mark(failures, reasons, indices[~np.isfinite(stock[indices])], "nonfinite_stock")
        _mark(failures, reasons, indices[stock[indices] <= 0], "nonpositive_stock")
        _mark(failures, reasons, indices[~np.isfinite(variance[indices])], "nonfinite_variance")
        if (step + 1) % observation_stride == 0:
            column = (step + 1) // observation_stride
            active = ~failures
            observations[active, column] = stock[active]
            variance_observations[active, column] = variance[active]

    result = _result(observations, failures, reasons, expiry)
    result.update(
        variance_observations=variance_observations,
        negative_variance_counts=negative_counts,
    )
    return result


def local_monthly(
    parameters: _Parameters, surface: _VarianceSurface, z: np.ndarray, expiry: float = 1.0
) -> dict:
    """Simulate local-variance log Euler at twelve fixed observation dates.

    At each left endpoint, ``surface.evaluate(t, spots)`` supplies arrays
    ``variance`` and ``status`` with the same shape as the active spots. At
    zero, every queried spot equals the supplied initial spot; the surface
    defines only that initial state. The first normal factor drives stock.

    Every surface label, including explicit wing/early-time extensions and
    unsupported labels, is counted per path in ``status_counts``. A label
    starting with ``unsupported`` or a negative/nonfinite local variance
    fails the path without clipping or substitution. Returned observation
    dates, failure masks, NaN suffixes and failure reasons follow
    :func:`heston_monthly`; earlier valid observations remain inspectable.
    """
    normals, dt, observations, failures, reasons = _prepare(parameters, z, expiry)
    paths, steps, _ = normals.shape
    stock = np.full(paths, parameters.spot, dtype=float)
    status_counts = {}
    observation_stride = steps // 12
    sqrt_dt = np.sqrt(dt)

    for step in range(steps):
        indices = np.flatnonzero(~failures)
        if not indices.size:
            break
        evaluated = surface.evaluate(step * dt, stock[indices])
        variance = np.asarray(evaluated["variance"], dtype=float)
        status = np.asarray(evaluated["status"], dtype=str)
        if variance.shape != indices.shape or status.shape != indices.shape:
            raise ValueError("surface variance and status must have the active spots' shape")
        for label in np.unique(status):
            selected = indices[status == label]
            if label not in status_counts:
                status_counts[label] = np.zeros(paths, dtype=np.int64)
            status_counts[label][selected] += 1
            if label.startswith("unsupported"):
                _mark(failures, reasons, selected, str(label))
        shocks = normals[indices, step, 0]
        _mark(failures, reasons, indices[~np.isfinite(shocks)], "nonfinite_driver")
        _mark(failures, reasons, indices[~np.isfinite(variance)], "nonfinite_variance")
        _mark(failures, reasons, indices[variance < 0], "negative_local_variance")
        valid = ~failures[indices]
        indices = indices[valid]
        variance = variance[valid]
        shocks = shocks[valid]
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            stock[indices] *= np.exp(
                (parameters.rate - parameters.dividend_yield - 0.5 * variance) * dt
                + np.sqrt(variance) * sqrt_dt * shocks
            )
        _mark(failures, reasons, indices[~np.isfinite(stock[indices])], "nonfinite_stock")
        _mark(failures, reasons, indices[stock[indices] <= 0], "nonpositive_stock")
        if (step + 1) % observation_stride == 0:
            column = (step + 1) // observation_stride
            active = ~failures
            observations[active, column] = stock[active]

    result = _result(observations, failures, reasons, expiry)
    result["status_counts"] = status_counts
    return result
