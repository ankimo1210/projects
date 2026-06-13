"""Small shared helpers: rng, credible intervals, posterior summaries."""

from __future__ import annotations

import numpy as np


def rng(seed: int = 42) -> np.random.Generator:
    """Project-wide convention: rng = default_rng(42) unless stated otherwise."""
    return np.random.default_rng(seed)


def credible_interval(samples, level: float = 0.95):
    """Equal-tailed credible interval from posterior samples. Returns (lo, hi)."""
    samples = np.asarray(samples)
    tail = (1.0 - level) / 2
    return float(np.quantile(samples, tail)), float(np.quantile(samples, 1 - tail))


def hdi(samples, level: float = 0.95):
    """Highest density interval (narrowest interval holding `level` mass).

    For unimodal posteriors this is the textbook HDI; computed by sliding a
    window over the sorted samples.
    """
    x = np.sort(np.asarray(samples))
    n = len(x)
    k = max(1, int(np.floor(level * n)))
    widths = x[k:] - x[: n - k]
    i = int(np.argmin(widths))
    return float(x[i]), float(x[i + k])


def summarize_posterior(samples, level: float = 0.95) -> dict:
    """Mean / sd / equal-tailed CI / HDI in one dict (for quick tables)."""
    samples = np.asarray(samples)
    lo, hi = credible_interval(samples, level)
    hlo, hhi = hdi(samples, level)
    return {
        "mean": float(samples.mean()),
        "sd": float(samples.std(ddof=1)),
        f"ci_{int(level * 100)}": (lo, hi),
        f"hdi_{int(level * 100)}": (hlo, hhi),
    }
