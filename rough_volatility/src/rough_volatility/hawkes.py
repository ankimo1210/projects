"""Bivariate sum-of-exponentials Hawkes process simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from rough_volatility.config import HawkesConfig

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def power_law_weights(betas: ArrayLike, alpha: float) -> FloatArray:
    """Return normalized mixture weights proportional to ``beta**alpha``."""
    rates = np.asarray(betas, dtype=np.float64)
    if rates.ndim != 1 or rates.size < 1 or np.any(~np.isfinite(rates)) or np.any(rates <= 0):
        raise ValueError("betas must be a non-empty vector of positive finite rates")
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    raw = rates**alpha
    return np.asarray(raw / raw.sum())


@dataclass(frozen=True)
class ExpSumKernel:
    """Separable matrix Hawkes kernel ``A * sum(w beta exp(-beta t))``."""

    amplitudes: FloatArray
    betas: FloatArray
    weights: FloatArray

    def __post_init__(self) -> None:
        amplitudes = np.asarray(self.amplitudes, dtype=np.float64)
        betas = np.asarray(self.betas, dtype=np.float64)
        weights = np.asarray(self.weights, dtype=np.float64)
        if amplitudes.shape != (2, 2) or np.any(~np.isfinite(amplitudes)) or np.any(amplitudes < 0):
            raise ValueError("amplitudes must be a finite non-negative 2x2 matrix")
        if (
            betas.ndim != 1
            or weights.shape != betas.shape
            or betas.size < 1
            or np.any(~np.isfinite(betas))
            or np.any(betas <= 0)
            or np.any(~np.isfinite(weights))
            or np.any(weights < 0)
            or not np.isclose(weights.sum(), 1.0)
        ):
            raise ValueError("betas/weights must be positive aligned vectors summing to one")
        object.__setattr__(self, "amplitudes", amplitudes)
        object.__setattr__(self, "betas", betas)
        object.__setattr__(self, "weights", weights)

    def branching_matrix(self) -> FloatArray:
        """Return the integrated kernel matrix."""
        return self.amplitudes.copy()

    def spectral_radius(self) -> float:
        """Return the Perron spectral radius of the branching matrix."""
        return float(np.max(np.abs(np.linalg.eigvals(self.amplitudes))))


@dataclass(frozen=True)
class HawkesModel:
    """Baseline intensity, kernel and scenario label."""

    mu: FloatArray
    kernel: ExpSumKernel
    name: str

    def __post_init__(self) -> None:
        baseline = np.asarray(self.mu, dtype=np.float64)
        if baseline.shape != (2,) or np.any(~np.isfinite(baseline)) or np.any(baseline <= 0):
            raise ValueError("mu must be a positive finite two-vector")
        if self.kernel.spectral_radius() >= 0.995:
            raise ValueError("Hawkes branching ratio must remain below 0.995")
        if not self.name:
            raise ValueError("scenario name cannot be empty")
        object.__setattr__(self, "mu", baseline)


@dataclass(frozen=True)
class HawkesResult:
    """Accepted event times/marks and thinning diagnostics."""

    times: FloatArray
    marks: IntArray
    truncated: bool
    n_candidates: int
    realized_rate: float


def make_scenario(name: str, config: HawkesConfig) -> HawkesModel:
    """Construct the rate-matched Poisson, stable or near-critical scenario."""
    config.validate()
    normalized = name.lower().replace("-", "_")
    if normalized == "poisson":
        branching = 0.0
        label = "poisson"
    elif normalized == "stable":
        branching = config.branching_stable
        label = "stable"
    elif normalized in {"critical", "near_critical", "nearcritical"}:
        branching = config.branching_critical
        label = "near_critical"
    else:
        raise ValueError("scenario must be poisson, stable, or critical")
    cross = branching * config.cross_fraction
    self_excitation = branching - cross
    amplitudes = np.array([[self_excitation, cross], [cross, self_excitation]], dtype=np.float64)
    if normalized in {"poisson", "stable"}:
        betas = np.asarray([config.exponential_beta], dtype=np.float64)
        weights = np.ones(1, dtype=np.float64)
    else:
        betas = np.asarray(config.betas, dtype=np.float64)
        weights = power_law_weights(betas, config.alpha_tail)
    kernel = ExpSumKernel(
        amplitudes=amplitudes,
        betas=betas,
        weights=weights,
    )
    baseline = np.full(2, config.target_rate * (1.0 - branching), dtype=np.float64)
    return HawkesModel(mu=baseline, kernel=kernel, name=label)


def _intensity(model: HawkesModel, state: FloatArray) -> FloatArray:
    kernel_scale = model.kernel.weights * model.kernel.betas
    source_excitation = state @ kernel_scale
    return model.mu + model.kernel.amplitudes @ source_excitation


def simulate_thinning(
    model: HawkesModel,
    horizon: float,
    rng: np.random.Generator,
    *,
    max_events: int,
) -> HawkesResult:
    """Simulate a stationary bivariate Hawkes process by Ogata thinning."""
    if not np.isfinite(horizon) or horizon <= 0:
        raise ValueError("horizon must be positive")
    if not isinstance(max_events, (int, np.integer)) or max_events < 1:
        raise ValueError("max_events must be a positive integer")
    if model.kernel.spectral_radius() >= 1.0:
        raise ValueError("cannot simulate a non-stationary Hawkes process")

    event_times = np.empty(max_events, dtype=np.float64)
    event_marks = np.empty(max_events, dtype=np.int64)
    state = np.zeros((2, model.kernel.betas.size), dtype=np.float64)
    time = 0.0
    count = 0
    candidates = 0
    while time < horizon and count < max_events:
        current_intensity = _intensity(model, state)
        upper = float(current_intensity.sum())
        if not np.isfinite(upper) or upper <= 0:
            raise RuntimeError("invalid Hawkes intensity during thinning")
        wait = float(rng.exponential(1.0 / upper))
        candidate_time = time + wait
        if candidate_time >= horizon:
            time = horizon
            break
        state *= np.exp(-model.kernel.betas * wait)[None, :]
        time = candidate_time
        candidates += 1
        candidate_intensity = _intensity(model, state)
        total = float(candidate_intensity.sum())
        if rng.random() * upper > total:
            continue
        mark = 0 if rng.random() * total < candidate_intensity[0] else 1
        event_times[count] = time
        event_marks[count] = mark
        count += 1
        state[mark] += 1.0

    truncated = count >= max_events and time < horizon
    return HawkesResult(
        times=event_times[:count].copy(),
        marks=event_marks[:count].copy(),
        truncated=truncated,
        n_candidates=candidates,
        realized_rate=count / (2.0 * horizon),
    )


def intensity_on_grid(
    model: HawkesModel,
    times: ArrayLike,
    marks: ArrayLike,
    grid: ArrayLike,
) -> FloatArray:
    """Reconstruct right-continuous conditional intensities on a regular grid."""
    event_times = np.asarray(times, dtype=np.float64)
    event_marks = np.asarray(marks, dtype=np.int64)
    grid_values = np.asarray(grid, dtype=np.float64)
    if (
        event_times.ndim != 1
        or event_marks.shape != event_times.shape
        or np.any(~np.isfinite(event_times))
        or np.any(event_times < 0)
        or np.any(np.diff(event_times) <= 0)
        or np.any((event_marks < 0) | (event_marks > 1))
    ):
        raise ValueError("event times/marks are invalid")
    if (
        grid_values.ndim != 1
        or grid_values.size < 1
        or np.any(~np.isfinite(grid_values))
        or np.any(grid_values < 0)
        or np.any(np.diff(grid_values) <= 0)
    ):
        raise ValueError("grid must be finite, non-negative and strictly increasing")

    output = np.empty((2, grid_values.size), dtype=np.float64)
    state = np.zeros((2, model.kernel.betas.size), dtype=np.float64)
    current_time = 0.0
    event_index = 0
    for grid_index, grid_time in enumerate(grid_values):
        while event_index < event_times.size and event_times[event_index] <= grid_time:
            event_time = event_times[event_index]
            state *= np.exp(-model.kernel.betas * (event_time - current_time))[None, :]
            current_time = float(event_time)
            state[event_marks[event_index]] += 1.0
            event_index += 1
        state *= np.exp(-model.kernel.betas * (grid_time - current_time))[None, :]
        current_time = float(grid_time)
        output[:, grid_index] = _intensity(model, state)
    return output


def integrated_intensity(
    model: HawkesModel,
    times: ArrayLike,
    marks: ArrayLike,
    horizon: float,
) -> FloatArray:
    """Evaluate the exact two-dimensional compensator at ``horizon``."""
    event_times = np.asarray(times, dtype=np.float64)
    event_marks = np.asarray(marks, dtype=np.int64)
    if (
        horizon <= 0
        or event_times.ndim != 1
        or event_marks.shape != event_times.shape
        or np.any(event_times < 0)
        or np.any(event_times >= horizon)
        or np.any((event_marks < 0) | (event_marks > 1))
    ):
        raise ValueError("events or horizon are invalid")
    compensator = model.mu * horizon
    for source in (0, 1):
        lags = horizon - event_times[event_marks == source]
        if lags.size == 0:
            continue
        integrated_kernel = np.sum(
            model.kernel.weights[:, None]
            * (1.0 - np.exp(-model.kernel.betas[:, None] * lags[None, :])),
            axis=0,
        )
        compensator += model.kernel.amplitudes[:, source] * integrated_kernel.sum()
    return np.asarray(compensator)
