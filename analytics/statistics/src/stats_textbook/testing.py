"""Hypothesis testing: size, power, and the price of asking many questions.

A test is a rule that maps data to reject/don't-reject. Everything the
theory says about it is a long-run frequency claim -- the type-I error
rate, the power -- and every one of them is measured here through
``simulation.rejection_rate`` rather than taken on faith.

Multiple testing gets its own section because the failure is quantitative,
not conceptual: run 200 tests on pure noise and about 10 come back
significant. Bonferroni and Benjamini-Hochberg are two different answers
to that, controlling two different things.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "TestResult",
    "benjamini_hochberg",
    "bonferroni",
    "false_discovery_proportion",
    "power_t_test",
    "required_n",
    "t_test",
    "two_sample_t_test",
]


@dataclass(frozen=True)
class TestResult:
    """A test statistic with its two-sided p-value."""

    statistic: float
    pvalue: float
    df: float | None = None


def t_test(sample: np.ndarray, mu0: float = 0.0) -> TestResult:
    """One-sample Student t test of ``mean == mu0``."""
    sample = np.asarray(sample, dtype=float)
    n = sample.size
    se = sample.std(ddof=1) / np.sqrt(n)
    t = (sample.mean() - mu0) / se
    return TestResult(float(t), float(2.0 * stats.t.sf(abs(t), n - 1)), float(n - 1))


def two_sample_t_test(x: np.ndarray, y: np.ndarray, equal_var: bool = False) -> TestResult:
    """Two-sample t test; Welch's version by default (unequal variances)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    nx, ny = x.size, y.size
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    if equal_var:
        pooled = ((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2)
        se = np.sqrt(pooled * (1.0 / nx + 1.0 / ny))
        df = float(nx + ny - 2)
    else:
        se = np.sqrt(vx / nx + vy / ny)
        df = float(
            (vx / nx + vy / ny) ** 2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
        )
    t = (x.mean() - y.mean()) / se
    return TestResult(float(t), float(2.0 * stats.t.sf(abs(t), df)), df)


def power_t_test(effect: float, n: int, alpha: float = 0.05) -> float:
    """Probability of rejecting when the true standardised effect is ``effect``.

    Exact, via the non-central t distribution -- not the normal
    approximation, which is optimistic at small n.
    """
    crit = stats.t.ppf(1.0 - alpha / 2.0, n - 1)
    ncp = effect * math.sqrt(n)
    value = stats.nct.sf(crit, n - 1, ncp) + stats.nct.cdf(-crit, n - 1, ncp)
    if not math.isfinite(value):
        # scipy's nct overflows to nan at large non-centrality (measured: nan
        # at n=500 and n=3000 for effect 0.5). That is exactly the regime
        # where the normal approximation is accurate, so fall back to it --
        # leaving the nan in place made required_n's binary search walk past
        # the answer and return 5880 instead of 34.
        return float(stats.norm.cdf(ncp - stats.norm.ppf(1.0 - alpha / 2.0)))
    return float(value)


def required_n(effect: float, alpha: float = 0.05, power: float = 0.8, n_max: int = 10_000) -> int:
    """Smallest n whose power reaches ``power``. Searched, not approximated."""
    lo, hi = 2, n_max
    if power_t_test(effect, hi, alpha) < power:
        raise ValueError(f"power {power} unreachable by n={n_max} at effect {effect}")
    while lo < hi:
        mid = (lo + hi) // 2
        if power_t_test(effect, mid, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly inside (0, 1); got {alpha}")


def bonferroni(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Control the probability of *any* false rejection (family-wise error).

    Conservative by construction: with 200 tests every p-value must beat
    0.00025 to survive.
    """
    _check_alpha(alpha)
    p = np.asarray(pvalues, dtype=float)
    return p <= alpha / p.size


def benjamini_hochberg(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Control the expected *proportion* of rejections that are false (FDR).

    A weaker guarantee than Bonferroni's and therefore a stronger test: it
    tolerates some false discoveries as long as they stay a small share of
    the discoveries made.
    """
    _check_alpha(alpha)
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    below = ranked <= alpha * np.arange(1, m + 1) / m
    rejected = np.zeros(m, dtype=bool)
    if below.any():
        # Reject everything up to the largest index that clears the line.
        cutoff = int(np.max(np.nonzero(below)[0]))
        rejected[order[: cutoff + 1]] = True
    return rejected


def false_discovery_proportion(rejected: np.ndarray, is_null: np.ndarray) -> float:
    """Share of the rejections that were true nulls. Zero if nothing rejected."""
    rejected = np.asarray(rejected, dtype=bool)
    if not rejected.any():
        return 0.0
    return float(np.sum(rejected & np.asarray(is_null, dtype=bool)) / rejected.sum())
