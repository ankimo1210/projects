"""Finite Markov chains and stopped random walks for the B2 chapters."""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd

import numpy as np
from numpy.random import Generator
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


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


def validate_transition_matrix(transition_matrix: ArrayLike) -> FloatArray:
    """Return a validated finite row-stochastic transition matrix."""

    matrix = np.asarray(transition_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("transition_matrix must be a non-empty square array")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("transition_matrix must contain only finite values")
    tolerance = 100.0 * np.finfo(float).eps * max(matrix.shape[0], 1)
    if np.any(matrix < -tolerance):
        raise ValueError("transition probabilities must be non-negative")
    matrix = np.clip(matrix, 0.0, None)
    row_sums = matrix.sum(axis=1)
    if not np.allclose(row_sums, 1.0, rtol=1e-12, atol=1e-14):
        raise ValueError("each transition-matrix row must sum to one")
    return matrix / row_sums[:, None]


@dataclass(frozen=True)
class StationaryDistributionResult:
    """One stationary distribution and uniqueness diagnostics."""

    probabilities: FloatArray
    residual_norm: float
    spectral_gap: float
    is_unique: bool


def _reachability(adjacency: BoolArray) -> BoolArray:
    reachability = adjacency | np.eye(adjacency.shape[0], dtype=bool)
    for intermediate in range(adjacency.shape[0]):
        reachability |= reachability[:, intermediate, None] & reachability[None, intermediate, :]
    return reachability


def _closed_communicating_class_count(matrix: FloatArray) -> int:
    adjacency = matrix > 0.0
    communication = _reachability(adjacency)
    communication &= communication.T
    remaining = set(range(matrix.shape[0]))
    closed_count = 0
    while remaining:
        representative = min(remaining)
        members = set(np.flatnonzero(communication[representative]).tolist())
        remaining -= members
        outside = np.ones(matrix.shape[0], dtype=bool)
        outside[list(members)] = False
        if not np.any(adjacency[np.ix_(list(members), np.flatnonzero(outside))]):
            closed_count += 1
    return closed_count


def _balance_operator(matrix: FloatArray) -> FloatArray:
    """Build the balance operator without diagonal cancellation."""

    balance = matrix.T.copy()
    np.fill_diagonal(balance, 0.0)
    for state in range(matrix.shape[0]):
        outgoing = np.delete(matrix[state], state)
        balance[state, state] = -float(outgoing.sum())
    return balance


def stationary_distribution(transition_matrix: ArrayLike) -> StationaryDistributionResult:
    """Solve ``pi @ P = pi`` with a probability-normalization constraint."""

    matrix = validate_transition_matrix(transition_matrix)
    n_states = matrix.shape[0]
    balance = _balance_operator(matrix)
    row_norms = np.linalg.norm(balance, axis=1)
    informative = row_norms > 0.0
    scaled_balance = balance[informative] / row_norms[informative, None]
    system = np.vstack((scaled_balance, np.ones(n_states)))
    target = np.concatenate((np.zeros(scaled_balance.shape[0]), np.ones(1)))
    probabilities, *_ = np.linalg.lstsq(system, target, rcond=None)
    tolerance = 1e-12 * max(n_states, 1)
    if np.any(probabilities < -tolerance):
        raise FloatingPointError("stationary solve produced materially negative probabilities")
    probabilities = np.clip(probabilities, 0.0, None)
    probabilities /= probabilities.sum()
    residual = float(np.linalg.norm(probabilities @ matrix - probabilities))

    eigenvalues = np.linalg.eigvals(matrix)
    magnitudes = np.sort(np.abs(eigenvalues))[::-1]
    spectral_gap = 1.0 if n_states == 1 else max(0.0, float(1.0 - magnitudes[1]))
    return StationaryDistributionResult(
        probabilities=np.asarray(probabilities, dtype=float),
        residual_norm=residual,
        spectral_gap=spectral_gap,
        is_unique=_closed_communicating_class_count(matrix) == 1,
    )


def _irreducibility_and_period(matrix: FloatArray) -> tuple[bool, int | None]:
    adjacency = matrix > 0.0
    reachability = _reachability(adjacency)
    irreducible = bool(np.all(reachability))
    if not irreducible:
        return False, None

    distances = np.full(matrix.shape[0], -1, dtype=int)
    distances[0] = 0
    queue = [0]
    for state in queue:
        for destination in np.flatnonzero(adjacency[state]):
            if distances[destination] < 0:
                distances[destination] = distances[state] + 1
                queue.append(int(destination))
    period = 0
    for source, destination in np.argwhere(adjacency):
        period = gcd(period, abs(int(distances[source] + 1 - distances[destination])))
    return True, max(period, 1)


@dataclass(frozen=True)
class MarkovChainDiagnostics:
    """Structural and stationary diagnostics for a finite chain."""

    n_states: int
    is_irreducible: bool
    is_aperiodic: bool
    period: int | None
    stationary: StationaryDistributionResult


def analyze_markov_chain(transition_matrix: ArrayLike) -> MarkovChainDiagnostics:
    """Diagnose irreducibility, period, and a stationary distribution."""

    matrix = validate_transition_matrix(transition_matrix)
    irreducible, period = _irreducibility_and_period(matrix)
    return MarkovChainDiagnostics(
        n_states=matrix.shape[0],
        is_irreducible=irreducible,
        is_aperiodic=period == 1,
        period=period,
        stationary=stationary_distribution(matrix),
    )


def simulate_markov_chain(
    transition_matrix: ArrayLike,
    initial_state: int,
    n_steps: int,
    n_paths: int,
    *,
    rng: Generator,
) -> IntArray:
    """Simulate state paths with shape ``(n_paths, n_steps + 1)``."""

    matrix = validate_transition_matrix(transition_matrix)
    if isinstance(initial_state, bool) or not isinstance(initial_state, (int, np.integer)):
        raise TypeError("initial_state must be an integer")
    if not 0 <= initial_state < matrix.shape[0]:
        raise ValueError("initial_state is out of bounds")
    steps = _positive_integer(n_steps, name="n_steps", minimum=0)
    paths_count = _positive_integer(n_paths, name="n_paths")
    generator = _require_generator(rng)
    paths = np.empty((paths_count, steps + 1), dtype=np.int64)
    paths[:, 0] = int(initial_state)
    states = np.arange(matrix.shape[0])
    for step in range(1, steps + 1):
        prior = paths[:, step - 1]
        for state in states:
            selected = prior == state
            count = int(np.count_nonzero(selected))
            if count:
                paths[selected, step] = generator.choice(states, size=count, p=matrix[state])
    return paths


def simulate_symmetric_random_walk(
    n_steps: int,
    n_paths: int,
    *,
    rng: Generator,
    start: float = 0.0,
) -> FloatArray:
    """Simulate a unit-step symmetric random walk, including time zero."""

    steps = _positive_integer(n_steps, name="n_steps", minimum=0)
    paths_count = _positive_integer(n_paths, name="n_paths")
    if not np.isfinite(start):
        raise ValueError("start must be finite")
    generator = _require_generator(rng)
    increments = 2.0 * generator.integers(0, 2, size=(paths_count, steps)) - 1.0
    paths = np.empty((paths_count, steps + 1), dtype=float)
    paths[:, 0] = start
    if steps:
        paths[:, 1:] = start + np.cumsum(increments, axis=1)
    return paths


@dataclass(frozen=True)
class StoppingTimeResult:
    """First boundary-exit results under a finite truncation horizon."""

    stopping_times: IntArray
    stopped_values: FloatArray
    hit_boundary: BoolArray
    lower_boundary: float
    upper_boundary: float
    max_steps: int


def first_exit_times(
    paths: ArrayLike,
    lower_boundary: float,
    upper_boundary: float,
) -> StoppingTimeResult:
    """Find first exits, using the last column for paths that never exit."""

    values = np.asarray(paths, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("paths must be a non-empty two-dimensional array")
    if not np.all(np.isfinite(values)):
        raise ValueError("paths must contain only finite values")
    if not np.isfinite(lower_boundary) or not np.isfinite(upper_boundary):
        raise ValueError("boundaries must be finite")
    if lower_boundary >= upper_boundary:
        raise ValueError("lower_boundary must be smaller than upper_boundary")

    exits = (values <= lower_boundary) | (values >= upper_boundary)
    hit = np.any(exits, axis=1)
    first = np.argmax(exits, axis=1).astype(np.int64)
    first[~hit] = values.shape[1] - 1
    stopped = values[np.arange(values.shape[0]), first]
    return StoppingTimeResult(
        stopping_times=first,
        stopped_values=np.asarray(stopped, dtype=float),
        hit_boundary=np.asarray(hit, dtype=bool),
        lower_boundary=float(lower_boundary),
        upper_boundary=float(upper_boundary),
        max_steps=values.shape[1] - 1,
    )


@dataclass(frozen=True)
class OptionalStoppingDiagnostics:
    """Finite-horizon diagnostics for a stopped random-walk martingale."""

    initial_value: float
    mean_stopped_value: float
    bias: float
    standard_error: float
    mean_stopping_time: float
    boundary_hit_rate: float
    truncation_rate: float
    n_paths: int
    stopping: StoppingTimeResult


def diagnose_optional_stopping(
    paths: ArrayLike,
    lower_boundary: float,
    upper_boundary: float,
) -> OptionalStoppingDiagnostics:
    """Compare the initial and stopped expectations at a bounded horizon."""

    values = np.asarray(paths, dtype=float)
    stopping = first_exit_times(values, lower_boundary, upper_boundary)
    n_paths = values.shape[0]
    initial = float(values[:, 0].mean())
    stopped_mean = float(stopping.stopped_values.mean())
    sample_standard_deviation = float(stopping.stopped_values.std(ddof=1)) if n_paths > 1 else 0.0
    return OptionalStoppingDiagnostics(
        initial_value=initial,
        mean_stopped_value=stopped_mean,
        bias=stopped_mean - initial,
        standard_error=sample_standard_deviation / np.sqrt(n_paths),
        mean_stopping_time=float(stopping.stopping_times.mean()),
        boundary_hit_rate=float(stopping.hit_boundary.mean()),
        truncation_rate=float(1.0 - stopping.hit_boundary.mean()),
        n_paths=n_paths,
        stopping=stopping,
    )


def random_walk_optional_stopping(
    n_paths: int,
    max_steps: int,
    lower_boundary: float,
    upper_boundary: float,
    *,
    rng: Generator,
    start: float = 0.0,
) -> OptionalStoppingDiagnostics:
    """Simulate and diagnose a boundary-stopped symmetric random walk."""

    paths = simulate_symmetric_random_walk(max_steps, n_paths, rng=rng, start=start)
    return diagnose_optional_stopping(paths, lower_boundary, upper_boundary)
