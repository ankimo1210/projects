"""Synthetic data generators for the textbook.

Everything is generated locally from a seeded ``numpy`` Generator: the book
must run offline and reproduce byte-identical figures. No dataset is ever
downloaded.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

__all__ = [
    "SAMPLERS",
    "bivariate_normal",
    "coin_flips",
    "disease_test_counts",
    "exponential_sample",
    "heavy_tailed_sample",
    "make_capstone_dataset",
    "normal_sample",
]


def coin_flips(n: int, p: float = 0.5, seed: int = 0) -> np.ndarray:
    """``n`` Bernoulli(p) draws as 0/1 integers."""
    rng = np.random.default_rng(seed)
    return (rng.random(n) < p).astype(int)


def disease_test_counts(
    n: int, prevalence: float, sensitivity: float, specificity: float, seed: int = 0
) -> dict[str, int]:
    """Simulate a screening programme and return the 2x2 confusion counts.

    Feeds NB01's false-positive paradox: at low prevalence the false
    positives outnumber the true positives even for an accurate test.
    """
    rng = np.random.default_rng(seed)
    diseased = rng.random(n) < prevalence
    positive = np.where(diseased, rng.random(n) < sensitivity, rng.random(n) > specificity)
    return {
        "tp": int(np.sum(diseased & positive)),
        "fn": int(np.sum(diseased & ~positive)),
        "fp": int(np.sum(~diseased & positive)),
        "tn": int(np.sum(~diseased & ~positive)),
    }


def normal_sample(n: int, mu: float = 0.0, sigma: float = 1.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(mu, sigma, n)


def exponential_sample(n: int, rate: float = 1.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.exponential(1.0 / rate, n)


def bivariate_normal(n: int, rho: float, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Standard bivariate normal with correlation ``rho`` (Cholesky construction)."""
    if not -1.0 < rho < 1.0:
        raise ValueError(f"rho must lie strictly inside (-1, 1); got {rho}")
    rng = np.random.default_rng(seed)
    z1, z2 = rng.normal(size=(2, n))
    return z1, rho * z1 + np.sqrt(1.0 - rho**2) * z2


def heavy_tailed_sample(n: int, kind: str = "cauchy", seed: int = 0) -> np.ndarray:
    """A sample with no finite mean (``cauchy``) or no finite variance (``pareto``)."""
    rng = np.random.default_rng(seed)
    if kind == "cauchy":
        return rng.standard_cauchy(n)
    if kind == "pareto":
        # alpha = 1.5: mean exists, variance does not.
        return rng.pareto(1.5, n) + 1.0
    raise ValueError(f"unknown kind {kind!r}; expected 'cauchy' or 'pareto'")


# name -> (n, rng) -> sample. Used by the CLT figure (NB04) and by
# ``simulation``, both of which own their own Generator.
SAMPLERS: dict[str, Callable[[int, np.random.Generator], np.ndarray]] = {
    "normal": lambda n, rng: rng.normal(0.0, 1.0, n),
    "uniform": lambda n, rng: rng.uniform(-np.sqrt(3.0), np.sqrt(3.0), n),
    "exponential": lambda n, rng: rng.exponential(1.0, n) - 1.0,
    "cauchy": lambda n, rng: rng.standard_cauchy(n),
}


def make_capstone_dataset(n: int = 40, x_range=(-3.0, 3.0), noise: float = 0.35, seed: int = 0):
    """Shared 1-D regression data for the cross-book capstone (three lenses).

    The SAME generator is defined identically in all five analytics books so
    each can solve the same problem from its own lens without importing the
    others. True curve f(x) = sin(1.5 x) + 0.3 x, with Gaussian noise. Returns
    (x, y) as float64 arrays sorted by x.

    Do not "improve" this function. Any change to the draw order produces
    different numbers and breaks analytics/report's cross-book consistency
    test, which is the only thing making the capstone's claim checkable.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(x_range[0], x_range[1], n))
    f = np.sin(1.5 * x) + 0.3 * x
    y = f + noise * rng.standard_normal(n)
    return x, y
