"""Probability on a time axis: random walks, Markov chains, Poisson processes.

The one chapter of the book that leaves the i.i.d. world. Kept deliberately
small -- the aim is to make 'the future depends on the present only' concrete,
not to build a stochastic-process library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

__all__ = ["MarkovChain", "poisson_counts", "poisson_process", "random_walk"]

_STEPS = ("rademacher", "normal")


def random_walk(
    n_steps: int, n_paths: int = 1, step: str = "rademacher", seed: int = 0
) -> np.ndarray:
    """``n_paths`` walks of ``n_steps`` increments, each starting at 0.

    Returns shape ``(n_paths, n_steps + 1)`` so column 0 is the common origin.
    """
    if step not in _STEPS:
        raise ValueError(f"unknown step {step!r}; expected one of {_STEPS}")
    rng = np.random.default_rng(seed)
    if step == "rademacher":
        increments = rng.choice([-1.0, 1.0], size=(n_paths, n_steps))
    else:
        increments = rng.normal(0.0, 1.0, size=(n_paths, n_steps))
    return np.concatenate([np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)], axis=1)


@dataclass(frozen=True)
class MarkovChain:
    """A finite, time-homogeneous Markov chain given by its transition matrix."""

    P: np.ndarray
    states: tuple[str, ...] | None = field(default=None)

    def __post_init__(self) -> None:
        P = np.asarray(self.P, dtype=float)
        if P.ndim != 2 or P.shape[0] != P.shape[1]:
            raise ValueError(f"P must be square; got shape {P.shape}")
        if (P < 0).any() or not np.allclose(P.sum(axis=1), 1.0):
            raise ValueError("P rows must be probability distributions (>= 0, summing to 1)")
        object.__setattr__(self, "P", P)

    @property
    def n_states(self) -> int:
        return self.P.shape[0]

    def distribution_after(self, n: int, p0: np.ndarray) -> np.ndarray:
        """The law of the chain after ``n`` steps started from ``p0``."""
        p = np.asarray(p0, dtype=float)
        if not math.isclose(p.sum(), 1.0, abs_tol=1e-9):
            raise ValueError("p0 must sum to 1")
        return p @ np.linalg.matrix_power(self.P, n)

    def stationary(self) -> np.ndarray:
        """The left eigenvector of P with eigenvalue 1, normalised to sum to 1.

        Meaningful only for an irreducible chain: a reducible one has a whole
        family of stationary laws and this returns an arbitrary member.
        """
        values, vectors = np.linalg.eig(self.P.T)
        idx = int(np.argmin(np.abs(values - 1.0)))
        pi = np.real(vectors[:, idx])
        return pi / pi.sum()

    def simulate(self, n_steps: int, x0: int = 0, seed: int = 0) -> np.ndarray:
        """One trajectory of state indices, length ``n_steps + 1``."""
        rng = np.random.default_rng(seed)
        path = np.empty(n_steps + 1, dtype=int)
        path[0] = x0
        cdf = np.cumsum(self.P, axis=1)
        u = rng.random(n_steps)
        for t in range(n_steps):
            path[t + 1] = int(np.searchsorted(cdf[path[t]], u[t]))
        return path

    def _reachability(self) -> np.ndarray:
        """Boolean matrix: can state i reach state j in any number of steps."""
        n = self.n_states
        reach = (self.P > 0) | np.eye(n, dtype=bool)
        # Transitive closure: log2(n) squarings suffice for an n-state chain.
        for _ in range(math.ceil(math.log2(max(n, 2)))):
            reach = reach @ reach
        return reach

    def is_irreducible(self) -> bool:
        return bool(self._reachability().all())

    def period(self) -> int:
        """The gcd of the return times of state 0.

        Common to all states when the chain is irreducible; for a reducible
        chain it describes state 0's class only and says nothing about the rest.
        """
        n = self.n_states
        power = np.eye(n)
        period = 0
        for k in range(1, 2 * n + 1):
            power = power @ self.P
            if power[0, 0] > 1e-12:
                period = math.gcd(period, k)
                if period == 1:
                    return 1
        return period


def poisson_process(rate: float, t_max: float, seed: int = 0) -> np.ndarray:
    """Event times of a homogeneous Poisson process on ``[0, t_max]``.

    Built from exponential gaps, which is the construction the chapter uses
    to explain why the counts end up Poisson.
    """
    if rate <= 0:
        raise ValueError(f"rate must be positive; got {rate}")
    rng = np.random.default_rng(seed)
    times: list[float] = []
    t = 0.0
    while True:
        t += rng.exponential(1.0 / rate)
        if t > t_max:
            break
        times.append(t)
    return np.asarray(times)


def poisson_counts(rate: float, t_max: float, n_reps: int, seed: int = 0) -> np.ndarray:
    """Event counts over ``n_reps`` independent windows of length ``t_max``."""
    rng = np.random.default_rng(seed)
    return rng.poisson(rate * t_max, n_reps)
