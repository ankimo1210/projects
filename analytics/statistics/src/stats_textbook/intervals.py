"""Interval estimation -- and what the number in front of the % sign means.

A 95% interval is not a statement about this interval. It is a statement
about the procedure: repeat the experiment and 95% of the intervals it
produces will contain the truth. That claim is measurable, and NB07
measures it with ``simulation.coverage_probability`` rather than trusting
the derivation.

The bootstrap earns its place where no closed form exists (a median, a
ratio, a trimmed mean). BCa is included because the plain percentile
interval is visibly wrong on skewed statistics, and seeing the correction
work is more convincing than being told it exists.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = [
    "Interval",
    "bootstrap_interval",
    "permutation_test",
    "t_interval",
    "wald_interval",
]

_METHODS = ("percentile", "bca")


@dataclass(frozen=True)
class Interval:
    """A closed interval. Iterable so it can be unpacked as ``(lo, hi)``."""

    lo: float
    hi: float

    def __iter__(self) -> Iterator[float]:
        yield self.lo
        yield self.hi

    def contains(self, value: float) -> bool:
        return self.lo <= value <= self.hi

    def width(self) -> float:
        return self.hi - self.lo


def t_interval(sample: np.ndarray, level: float = 0.95) -> Interval:
    """The Student t interval for a mean, using the sample standard deviation."""
    sample = np.asarray(sample, dtype=float)
    n = sample.size
    half = stats.t.ppf(0.5 + level / 2.0, n - 1) * sample.std(ddof=1) / np.sqrt(n)
    return Interval(float(sample.mean() - half), float(sample.mean() + half))


def wald_interval(estimate: float, se: float, level: float = 0.95) -> Interval:
    """estimate +- z * se. Valid only when the estimator is near-normal."""
    z = stats.norm.ppf(0.5 + level / 2.0)
    return Interval(estimate - z * se, estimate + z * se)


def _resample(sample: np.ndarray, statistic, n_boot: int, rng) -> np.ndarray:
    idx = rng.integers(0, sample.size, size=(n_boot, sample.size))
    return np.array([float(statistic(sample[i])) for i in idx])


def bootstrap_interval(
    sample: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    method: str = "percentile",
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> Interval:
    """Resample the data to get an interval for any statistic.

    ``percentile`` takes the empirical quantiles of the bootstrap
    distribution. ``bca`` shifts them to correct for bias (is the statistic
    systematically off-centre?) and acceleration (does its variance change
    with the parameter?), which matters for skewed statistics.
    """
    if method not in _METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {_METHODS}")
    sample = np.asarray(sample, dtype=float)
    rng = np.random.default_rng(seed)
    boot = _resample(sample, statistic, n_boot, rng)
    alpha = 1.0 - level

    if method == "percentile":
        lo, hi = np.quantile(boot, [alpha / 2.0, 1.0 - alpha / 2.0])
        return Interval(float(lo), float(hi))

    theta_hat = float(statistic(sample))
    # Bias correction: where the observed statistic sits in the bootstrap law.
    prop = float(np.mean(boot < theta_hat))
    prop = min(max(prop, 1.0 / (2 * n_boot)), 1.0 - 1.0 / (2 * n_boot))
    z0 = stats.norm.ppf(prop)
    # Acceleration from the jackknife's third moment.
    jack = np.array([float(statistic(np.delete(sample, i))) for i in range(sample.size)])
    d = jack.mean() - jack
    denom = 6.0 * (np.sum(d**2) ** 1.5)
    a = float(np.sum(d**3) / denom) if denom > 0 else 0.0

    def adjust(q: float) -> float:
        z = stats.norm.ppf(q)
        return float(stats.norm.cdf(z0 + (z0 + z) / (1.0 - a * (z0 + z))))

    lo, hi = np.quantile(boot, [adjust(alpha / 2.0), adjust(1.0 - alpha / 2.0)])
    return Interval(float(lo), float(hi))


def _mean_difference(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(x) - np.mean(y))


def permutation_test(
    x: np.ndarray,
    y: np.ndarray,
    statistic: Callable[[np.ndarray, np.ndarray], float] | None = None,
    n_perm: int = 5000,
    seed: int = 0,
) -> float:
    """Two-sided p-value from shuffling the group labels.

    Assumes only exchangeability under the null -- no distributional model
    at all, which is why it works where a t test's assumptions do not.
    """
    statistic = statistic or _mean_difference
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    observed = abs(statistic(x, y))
    pooled = np.concatenate([x, y])
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        if abs(statistic(pooled[: x.size], pooled[x.size :])) >= observed:
            count += 1
    # Add-one correction: a permutation p-value is never exactly zero.
    return (count + 1) / (n_perm + 1)
