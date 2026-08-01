"""The Monte-Carlo harness behind the book's second principle:
every claim is checked by simulation.

A confidence interval that claims 95% coverage, a test that claims a 5%
type-I error rate -- both are statements about long-run frequencies, and
both are measured here rather than asserted. The three entry points share
one shape: draw many samples from a known truth, apply the procedure, and
report the proportion with a Monte-Carlo standard error attached, so the
reader can tell a real discrepancy from simulation noise.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

__all__ = [
    "MonteCarloResult",
    "Sampler",
    "coverage_probability",
    "rejection_rate",
    "sampling_distribution",
]

# A sampler owns no randomness of its own: it receives the harness's Generator
# so a single seed reproduces the whole experiment.
Sampler = Callable[[int, np.random.Generator], np.ndarray]


@dataclass(frozen=True)
class MonteCarloResult:
    """A simulated proportion with its Monte-Carlo standard error."""

    estimate: float
    se: float
    n_reps: int

    def ci95(self) -> tuple[float, float]:
        """The 95% Monte-Carlo interval for the estimated proportion.

        This is the uncertainty in *our simulation*, not in the procedure
        being studied. Narrowing it means running more repetitions.
        """
        half = 1.96 * self.se
        return self.estimate - half, self.estimate + half


def _proportion_result(hits: np.ndarray, n_reps: int) -> MonteCarloResult:
    p = float(np.mean(hits))
    return MonteCarloResult(
        estimate=p, se=math.sqrt(max(p * (1.0 - p), 0.0) / n_reps), n_reps=n_reps
    )


def sampling_distribution(
    statistic: Callable[[np.ndarray], float],
    sampler: Sampler,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> np.ndarray:
    """``n_reps`` draws of ``statistic`` computed on fresh samples of size ``n``."""
    rng = np.random.default_rng(seed)
    return np.array([float(statistic(sampler(n, rng))) for _ in range(n_reps)])


def coverage_probability(
    sampler: Sampler,
    interval_fn: Callable[[np.ndarray], tuple[float, float]],
    truth: float,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> MonteCarloResult:
    """The proportion of intervals that actually contain ``truth``.

    A 95% interval whose measured coverage is 0.72 is not a 95% interval,
    however confidently it was derived.
    """
    rng = np.random.default_rng(seed)
    hits = np.empty(n_reps, dtype=bool)
    for i in range(n_reps):
        lo, hi = interval_fn(sampler(n, rng))
        hits[i] = lo <= truth <= hi
    return _proportion_result(hits, n_reps)


def rejection_rate(
    sampler: Sampler,
    pvalue_fn: Callable[[np.ndarray], float],
    alpha: float,
    n: int,
    n_reps: int,
    seed: int = 0,
) -> MonteCarloResult:
    """The proportion of samples on which the test rejects at level ``alpha``.

    Under a null-generating sampler this measures the type-I error rate;
    under an alternative it measures power. Same function, same code path --
    which is the point NB08 makes about what a test actually is.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly inside (0, 1); got {alpha}")
    rng = np.random.default_rng(seed)
    rejects = np.empty(n_reps, dtype=bool)
    for i in range(n_reps):
        rejects[i] = pvalue_fn(sampler(n, rng)) < alpha
    return _proportion_result(rejects, n_reps)
