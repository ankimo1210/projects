"""Reusable Monte Carlo and stochastic-path primitives for B2.

The module separates path generation from payoff evaluation and requires an
explicit :class:`numpy.random.Generator` for every operation that consumes
randomness.  Confidence intervals quantify sampling uncertainty only; they
do not include time-discretization or model bias.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from numpy.random import Generator, SeedSequence
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
PathStep = Callable[[FloatArray, float, float, Generator], ArrayLike]


def _require_generator(rng: Generator) -> Generator:
    if not isinstance(rng, Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    return rng


def _positive_integer(value: int, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


def _finite_scalar(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _time_grid(times: ArrayLike) -> FloatArray:
    grid = np.asarray(times, dtype=float)
    if grid.ndim != 1 or grid.size < 2:
        raise ValueError("times must be a one-dimensional array with at least two entries")
    if not np.all(np.isfinite(grid)):
        raise ValueError("times must contain only finite values")
    if np.any(np.diff(grid) <= 0.0):
        raise ValueError("times must be strictly increasing")
    return grid


def _samples(values: ArrayLike, *, name: str = "samples", minimum: int = 2) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < minimum:
        raise ValueError(f"{name} must be a one-dimensional array with at least {minimum} entries")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _validate_ddof(ddof: int, n_samples: int) -> int:
    if isinstance(ddof, bool) or not isinstance(ddof, (int, np.integer)):
        raise TypeError("ddof must be an integer")
    if not 0 <= ddof < n_samples:
        raise ValueError("ddof must be between zero and n_samples - 1")
    return int(ddof)


def _confidence_level(confidence_level: float) -> float:
    level = float(confidence_level)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    return level


def spawn_generators(
    seed: int | np.integer | SeedSequence,
    n_streams: int,
) -> tuple[Generator, ...]:
    """Create reproducible child generators using ``SeedSequence.spawn``."""

    stream_count = _positive_integer(n_streams, name="n_streams")
    if isinstance(seed, SeedSequence):
        root = seed
    elif isinstance(seed, (int, np.integer)) and not isinstance(seed, bool):
        root = SeedSequence(int(seed))
    else:
        raise TypeError("seed must be an integer or numpy.random.SeedSequence")
    return tuple(np.random.default_rng(child) for child in root.spawn(stream_count))


@dataclass(frozen=True)
class ConfidenceInterval:
    """Two-sided normal-approximation confidence interval for a mean."""

    lower: float
    upper: float
    confidence_level: float
    standard_error: float
    critical_value: float
    method: str = "normal"


@dataclass(frozen=True)
class MonteCarloEstimate:
    """Sample mean, dispersion, and sampling-error diagnostics."""

    estimate: float
    sample_standard_deviation: float
    standard_error: float
    n_samples: int
    ddof: int
    confidence_interval: ConfidenceInterval


def monte_carlo_standard_error(samples: ArrayLike, *, ddof: int = 1) -> float:
    """Estimate standard error as sample standard deviation divided by ``sqrt(N)``."""

    values = _samples(samples)
    degrees = _validate_ddof(ddof, values.size)
    return float(values.std(ddof=degrees) / np.sqrt(values.size))


def estimate_confidence_interval(
    samples: ArrayLike,
    *,
    confidence_level: float = 0.95,
    ddof: int = 1,
) -> ConfidenceInterval:
    """Return a two-sided normal-approximation interval for an i.i.d. mean."""

    values = _samples(samples)
    degrees = _validate_ddof(ddof, values.size)
    level = _confidence_level(confidence_level)
    standard_error = float(values.std(ddof=degrees) / np.sqrt(values.size))
    critical_value = float(NormalDist().inv_cdf((1.0 + level) / 2.0))
    estimate = float(values.mean())
    half_width = critical_value * standard_error
    return ConfidenceInterval(
        lower=estimate - half_width,
        upper=estimate + half_width,
        confidence_level=level,
        standard_error=standard_error,
        critical_value=critical_value,
    )


def estimate_expectation(
    samples: ArrayLike,
    *,
    confidence_level: float = 0.95,
    ddof: int = 1,
) -> MonteCarloEstimate:
    """Estimate an expectation from already-evaluated payoff samples."""

    values = _samples(samples)
    degrees = _validate_ddof(ddof, values.size)
    interval = estimate_confidence_interval(
        values,
        confidence_level=confidence_level,
        ddof=degrees,
    )
    return MonteCarloEstimate(
        estimate=float(values.mean()),
        sample_standard_deviation=float(values.std(ddof=degrees)),
        standard_error=interval.standard_error,
        n_samples=values.size,
        ddof=degrees,
        confidence_interval=interval,
    )


def simulate_paths(
    initial_value: float | ArrayLike,
    times: ArrayLike,
    n_paths: int,
    step: PathStep,
    *,
    rng: Generator,
) -> FloatArray:
    """Apply a one-step transition and return shape ``(n_paths, n_times)``.

    ``step`` receives ``(state, time, time_step, rng)`` and must return one
    finite value per path.  The simulator deliberately knows nothing about
    payoffs, discounting, or confidence intervals.
    """

    grid = _time_grid(times)
    paths_count = _positive_integer(n_paths, name="n_paths")
    generator = _require_generator(rng)
    if not callable(step):
        raise TypeError("step must be callable")
    initial = np.asarray(initial_value, dtype=float)
    if initial.ndim == 0:
        state = np.full(paths_count, float(initial), dtype=float)
    elif initial.shape == (paths_count,):
        state = initial.astype(float, copy=True)
    else:
        raise ValueError("initial_value must be scalar or have one entry per path")
    if not np.all(np.isfinite(state)):
        raise ValueError("initial_value must contain only finite values")

    paths = np.empty((paths_count, grid.size), dtype=float)
    paths[:, 0] = state
    for index, time_step in enumerate(np.diff(grid), start=1):
        proposed = np.asarray(
            step(state.copy(), float(grid[index - 1]), float(time_step), generator),
            dtype=float,
        )
        if proposed.shape != (paths_count,):
            raise ValueError("step must return one value per path")
        if not np.all(np.isfinite(proposed)):
            raise FloatingPointError("step returned non-finite path values")
        state = proposed
        paths[:, index] = state
    return paths


def antithetic_variates(
    n_pairs: int,
    n_dimensions: int = 1,
    *,
    rng: Generator,
) -> FloatArray:
    """Return standard normals followed by their sign reversals.

    The output shape is ``(2 * n_pairs, n_dimensions)``.  Downstream code
    should average paired payoffs before estimating a standard error.
    """

    pair_count = _positive_integer(n_pairs, name="n_pairs")
    dimension_count = _positive_integer(n_dimensions, name="n_dimensions")
    draws = _require_generator(rng).standard_normal((pair_count, dimension_count))
    return np.vstack((draws, -draws))


def _normal_increments(
    n_paths: int,
    time_steps: FloatArray,
    *,
    rng: Generator,
    antithetic: bool,
) -> FloatArray:
    if not isinstance(antithetic, (bool, np.bool_)):
        raise TypeError("antithetic must be a boolean")
    if antithetic:
        if n_paths % 2:
            raise ValueError("antithetic path simulation requires an even n_paths")
        pairs = n_paths // 2
        standard = antithetic_variates(
            pairs,
            time_steps.size,
            rng=rng,
        )[:n_paths]
    else:
        standard = rng.standard_normal((n_paths, time_steps.size))
    return standard * np.sqrt(time_steps)[None, :]


def simulate_brownian_motion(
    times: ArrayLike,
    n_paths: int,
    *,
    rng: Generator,
    initial_value: float = 0.0,
    antithetic: bool = False,
) -> FloatArray:
    """Simulate Brownian paths on an arbitrary increasing time grid."""

    grid = _time_grid(times)
    paths_count = _positive_integer(n_paths, name="n_paths")
    start = _finite_scalar(initial_value, name="initial_value")
    generator = _require_generator(rng)
    increments = _normal_increments(
        paths_count,
        np.diff(grid),
        rng=generator,
        antithetic=antithetic,
    )
    paths = np.empty((paths_count, grid.size), dtype=float)
    paths[:, 0] = start
    paths[:, 1:] = start + np.cumsum(increments, axis=1)
    return paths


def quadratic_variation(paths: ArrayLike) -> FloatArray:
    """Return sum of squared adjacent increments for every path row."""

    values = np.asarray(paths, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] < 2:
        raise ValueError("paths must have shape (n_paths, n_times) with n_times at least two")
    if not np.all(np.isfinite(values)):
        raise ValueError("paths must contain only finite values")
    return np.sum(np.diff(values, axis=1) ** 2, axis=1)


def _gbm_parameters(
    initial_price: float,
    drift: float,
    volatility: float,
) -> tuple[float, float, float]:
    price = _finite_scalar(initial_price, name="initial_price")
    rate = _finite_scalar(drift, name="drift")
    sigma = _finite_scalar(volatility, name="volatility")
    if price <= 0.0:
        raise ValueError("initial_price must be strictly positive")
    if sigma < 0.0:
        raise ValueError("volatility must be non-negative")
    return price, rate, sigma


def simulate_gbm_exact(
    initial_price: float,
    drift: float,
    volatility: float,
    times: ArrayLike,
    n_paths: int,
    *,
    rng: Generator,
    antithetic: bool = False,
) -> FloatArray:
    """Simulate exact constant-coefficient geometric-Brownian transitions."""

    price, rate, sigma = _gbm_parameters(initial_price, drift, volatility)
    grid = _time_grid(times)
    paths_count = _positive_integer(n_paths, name="n_paths")
    generator = _require_generator(rng)
    time_steps = np.diff(grid)
    brownian_increments = _normal_increments(
        paths_count,
        time_steps,
        rng=generator,
        antithetic=antithetic,
    )
    log_increments = (rate - 0.5 * sigma**2) * time_steps[None, :] + sigma * brownian_increments
    paths = np.empty((paths_count, grid.size), dtype=float)
    paths[:, 0] = price
    paths[:, 1:] = price * np.exp(np.cumsum(log_increments, axis=1))
    if not np.all(np.isfinite(paths)):
        raise FloatingPointError("GBM simulation produced non-finite values")
    return paths


def simulate_gbm_euler(
    initial_price: float,
    drift: float,
    volatility: float,
    times: ArrayLike,
    n_paths: int,
    *,
    rng: Generator,
    antithetic: bool = False,
) -> FloatArray:
    """Simulate geometric Brownian motion using Euler--Maruyama."""

    price, rate, sigma = _gbm_parameters(initial_price, drift, volatility)
    grid = _time_grid(times)
    paths_count = _positive_integer(n_paths, name="n_paths")
    generator = _require_generator(rng)
    time_steps = np.diff(grid)
    brownian_increments = _normal_increments(
        paths_count,
        time_steps,
        rng=generator,
        antithetic=antithetic,
    )
    paths = np.empty((paths_count, grid.size), dtype=float)
    paths[:, 0] = price
    for index, time_step in enumerate(time_steps, start=1):
        previous = paths[:, index - 1]
        paths[:, index] = previous * (
            1.0 + rate * time_step + sigma * brownian_increments[:, index - 1]
        )
    if not np.all(np.isfinite(paths)):
        raise FloatingPointError("Euler--Maruyama simulation produced non-finite values")
    return paths


@dataclass(frozen=True)
class ControlVariateResult:
    """Optimal one-control linear adjustment and variance diagnostics."""

    adjusted_samples: FloatArray
    coefficient: float
    raw_estimate: float
    adjusted_estimate: float
    raw_variance: float
    adjusted_variance: float
    variance_reduction_ratio: float
    known_control_mean: float
    ddof: int


def control_variate(
    target_samples: ArrayLike,
    control_samples: ArrayLike,
    known_control_mean: float,
    *,
    ddof: int = 1,
) -> ControlVariateResult:
    """Adjust target samples using a control with known population mean."""

    targets = _samples(target_samples, name="target_samples")
    controls = _samples(control_samples, name="control_samples")
    if controls.shape != targets.shape:
        raise ValueError("control_samples must have the same shape as target_samples")
    degrees = _validate_ddof(ddof, targets.size)
    known_mean = _finite_scalar(known_control_mean, name="known_control_mean")
    control_variance = float(controls.var(ddof=degrees))
    if control_variance <= 0.0:
        raise ValueError("control_samples must have strictly positive sample variance")
    covariance = float(np.cov(targets, controls, ddof=degrees)[0, 1])
    coefficient = covariance / control_variance
    adjusted = targets - coefficient * (controls - known_mean)
    raw_variance = float(targets.var(ddof=degrees))
    adjusted_variance = float(adjusted.var(ddof=degrees))
    ratio = float("inf") if adjusted_variance == 0.0 else raw_variance / adjusted_variance
    return ControlVariateResult(
        adjusted_samples=np.asarray(adjusted, dtype=float),
        coefficient=float(coefficient),
        raw_estimate=float(targets.mean()),
        adjusted_estimate=float(adjusted.mean()),
        raw_variance=raw_variance,
        adjusted_variance=adjusted_variance,
        variance_reduction_ratio=ratio,
        known_control_mean=known_mean,
        ddof=degrees,
    )


@dataclass(frozen=True)
class ImportanceSamplingResult:
    """Normal upper-tail estimate with raw and scale-free weight diagnostics."""

    estimate: float
    standard_error: float
    confidence_interval: ConfidenceInterval
    effective_sample_size: float
    weight_mean: float
    weight_variance: float
    weight_coefficient_of_variation_squared: float
    log_weight_variance: float
    weight_variance_underflow: bool
    max_weight: float
    nonzero_contributions: int
    max_contribution_share: float
    log_weight_range: float
    n_samples: int
    threshold: float
    proposal_mean: float


def importance_sampling(
    threshold: float,
    n_samples: int,
    proposal_mean: float,
    *,
    rng: Generator,
    confidence_level: float = 0.95,
    ddof: int = 1,
) -> ImportanceSamplingResult:
    """Estimate ``P(Z > threshold)`` with a ``N(proposal_mean, 1)`` proposal."""

    cutoff = _finite_scalar(threshold, name="threshold")
    proposal = _finite_scalar(proposal_mean, name="proposal_mean")
    count = _positive_integer(n_samples, name="n_samples", minimum=2)
    degrees = _validate_ddof(ddof, count)
    generator = _require_generator(rng)
    draws = generator.normal(proposal, 1.0, size=count)
    log_weights = -proposal * draws + 0.5 * proposal**2
    maximum_log_weight = float(np.max(log_weights))
    scaled_weights = np.exp(log_weights - maximum_log_weight)
    effective_sample_size = float(scaled_weights.sum() ** 2 / np.sum(scaled_weights**2))
    with np.errstate(over="ignore", under="ignore"):
        weights = np.exp(log_weights)
    if not np.all(np.isfinite(weights)) or not np.any(weights > 0.0):
        raise FloatingPointError(
            "importance weights overflowed or underflowed; choose a less extreme proposal"
        )
    hits = draws > cutoff
    nonzero_contributions = int(np.count_nonzero(hits))
    if nonzero_contributions == 0:
        raise RuntimeError(
            "no event contributions were observed; choose a better importance-sampling proposal"
        )
    level = _confidence_level(confidence_level)
    critical_value = float(NormalDist().inv_cdf((1.0 + level) / 2.0))
    maximum_log_contribution = float(np.max(log_weights[hits]))
    scaled_contributions = np.zeros(count, dtype=float)
    scaled_contributions[hits] = np.exp(log_weights[hits] - maximum_log_contribution)
    contribution_scale = float(np.exp(maximum_log_contribution))
    if contribution_scale == 0.0:
        raise FloatingPointError("importance estimate is below floating-point range")
    scaled_estimate = float(scaled_contributions.mean())
    scaled_standard_error = float(scaled_contributions.std(ddof=degrees) / np.sqrt(count))
    estimate = contribution_scale * scaled_estimate
    standard_error = contribution_scale * scaled_standard_error
    if estimate == 0.0 or (scaled_standard_error > 0.0 and standard_error == 0.0):
        raise FloatingPointError(
            "importance estimate or standard error is below floating-point range"
        )
    max_contribution_share = float(scaled_contributions.max() / scaled_contributions.sum())
    raw_weight_variance = float(weights.var(ddof=degrees))
    scaled_weight_variance = float(scaled_weights.var(ddof=degrees))
    if scaled_weight_variance > 0.0:
        log_weight_variance = float(2.0 * maximum_log_weight + np.log(scaled_weight_variance))
    else:
        log_weight_variance = float("-inf")
    weight_variance_underflow = raw_weight_variance == 0.0 and scaled_weight_variance > 0.0
    weight_cv_squared = max(0.0, count / effective_sample_size - 1.0)
    half_width = critical_value * standard_error
    interval = ConfidenceInterval(
        lower=estimate - half_width,
        upper=estimate + half_width,
        confidence_level=level,
        standard_error=standard_error,
        critical_value=critical_value,
    )
    return ImportanceSamplingResult(
        estimate=estimate,
        standard_error=standard_error,
        confidence_interval=interval,
        effective_sample_size=effective_sample_size,
        weight_mean=float(weights.mean()),
        weight_variance=raw_weight_variance,
        weight_coefficient_of_variation_squared=weight_cv_squared,
        log_weight_variance=log_weight_variance,
        weight_variance_underflow=weight_variance_underflow,
        max_weight=float(weights.max()),
        nonzero_contributions=nonzero_contributions,
        max_contribution_share=max_contribution_share,
        log_weight_range=float(np.ptp(log_weights)),
        n_samples=count,
        threshold=cutoff,
        proposal_mean=proposal,
    )


def brownian_bridge(
    times: ArrayLike,
    start: float,
    end: float,
    n_paths: int,
    *,
    rng: Generator,
) -> FloatArray:
    """Simulate Brownian paths conditioned on scalar start and end values."""

    grid = _time_grid(times)
    start_value = _finite_scalar(start, name="start")
    end_value = _finite_scalar(end, name="end")
    paths_count = _positive_integer(n_paths, name="n_paths")
    generator = _require_generator(rng)
    horizon = float(grid[-1] - grid[0])
    relative_times = grid - grid[0]
    unconditioned = simulate_brownian_motion(
        grid,
        paths_count,
        rng=generator,
        initial_value=0.0,
    )
    fractions = relative_times / horizon
    centered_bridge = unconditioned - fractions[None, :] * unconditioned[:, -1, None]
    conditional_mean = start_value + fractions * (end_value - start_value)
    paths = centered_bridge + conditional_mean[None, :]
    paths[:, 0] = start_value
    paths[:, -1] = end_value
    return np.asarray(paths, dtype=float)
