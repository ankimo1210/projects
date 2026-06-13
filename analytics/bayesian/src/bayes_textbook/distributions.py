"""Teaching helpers around scipy.stats distributions (grids for plotting)."""

from __future__ import annotations

import numpy as np
from scipy import stats


def grid_pdf(frozen, n: int = 400, tail: float = 1e-3):
    """Evaluation grid for a continuous frozen distribution. Returns (x, pdf)."""
    lo, hi = frozen.ppf(tail), frozen.ppf(1 - tail)
    x = np.linspace(lo, hi, n)
    return x, frozen.pdf(x)


def grid_pmf(frozen, k_max: int | None = None, tail: float = 1e-4):
    """Evaluation grid for a discrete frozen distribution. Returns (k, pmf)."""
    if k_max is None:
        k_max = int(frozen.ppf(1 - tail))
    k = np.arange(k_max + 1)
    return k, frozen.pmf(k)


# Registry used by the chapter-02 explorer: name -> (factory, param specs).
# Param spec: (label, min, max, step, default).
DISTRIBUTIONS = {
    "bernoulli": (
        lambda p: stats.bernoulli(p),
        [("p", 0.01, 0.99, 0.01, 0.3)],
        "discrete",
    ),
    "binomial": (
        lambda n, p: stats.binom(int(n), p),
        [("n", 1, 100, 1, 20), ("p", 0.01, 0.99, 0.01, 0.3)],
        "discrete",
    ),
    "poisson": (
        lambda lam: stats.poisson(lam),
        [("lam", 0.1, 30.0, 0.1, 4.0)],
        "discrete",
    ),
    "beta": (
        lambda a, b: stats.beta(a, b),
        [("a", 0.1, 20.0, 0.1, 2.0), ("b", 0.1, 20.0, 0.1, 2.0)],
        "continuous",
    ),
    "normal": (
        lambda mu, sigma: stats.norm(mu, sigma),
        [("mu", -5.0, 5.0, 0.1, 0.0), ("sigma", 0.1, 5.0, 0.1, 1.0)],
        "continuous",
    ),
    "gamma": (
        lambda shape, rate: stats.gamma(shape, scale=1.0 / rate),
        [("shape", 0.1, 20.0, 0.1, 2.0), ("rate", 0.1, 10.0, 0.1, 1.0)],
        "continuous",
    ),
}


def sample_dirichlet(alpha, n: int = 2000, seed: int = 42):
    """Samples from Dirichlet(alpha) — for the 3-component simplex plots."""
    return np.random.default_rng(seed).dirichlet(np.asarray(alpha, dtype=float), size=n)


def simplex_to_xy(p):
    """Project 3-component probability vectors onto the 2-D simplex triangle."""
    p = np.asarray(p, dtype=float)
    x = p[..., 1] + 0.5 * p[..., 2]
    y = (np.sqrt(3) / 2) * p[..., 2]
    return x, y
