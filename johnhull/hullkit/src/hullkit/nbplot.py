"""Shared notebook-plotting helpers for the johnhull volumes.

Captures the ipympl know-how from interest_rate_models/PROGRESS.md:
plt.ioff() right after import prevents duplicate-display comm_id errors,
and update callbacks should use fig.canvas.draw_idle().
"""

import numpy as np


def setup():
    """Prepare matplotlib for ipympl notebooks (Japanese fonts, no implicit display).

    Returns the pyplot module so notebooks can write ``plt = nbplot.setup()``.
    """
    import japanize_matplotlib  # noqa: F401
    import matplotlib.pyplot as plt

    plt.ioff()
    return plt


def kde_xy(samples, n_pts=200):
    """Gaussian KDE of 1-D samples on an even grid. Returns (x, density)."""
    from scipy.stats import gaussian_kde

    samples = np.asarray(samples, dtype=float)
    if samples.size < 2 or np.ptp(samples) == 0.0:
        raise ValueError("kde_xy requires >= 2 samples with nonzero spread")
    kde = gaussian_kde(samples)
    x = np.linspace(samples.min(), samples.max(), n_pts)
    return x, kde(x)
