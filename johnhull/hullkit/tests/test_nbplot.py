"""Tests for hullkit.nbplot."""

import matplotlib

matplotlib.use("Agg")  # headless; must run before any pyplot import

import numpy as np
import pytest
from hullkit import nbplot


def test_setup_disables_interactive():
    import matplotlib.pyplot as plt_direct

    plt_direct.ion()  # force interactive so the test fails without setup()'s ioff()
    plt = nbplot.setup()
    assert plt.isinteractive() is False
    assert hasattr(plt, "subplots")


def test_kde_xy_normal_samples():
    rng = np.random.default_rng(0)
    samples = rng.normal(5.0, 1.0, size=20_000)
    x, y = nbplot.kde_xy(samples, n_pts=300)
    assert x.shape == (300,) and y.shape == (300,)
    assert np.all(y >= 0.0)
    assert np.trapezoid(y, x) > 0.95  # density integrates to ~1
    assert abs(x[np.argmax(y)] - 5.0) < 0.3  # peak near the mean


# --- input-guard tests ---


def test_kde_xy_constant_raises():
    with pytest.raises(ValueError, match="kde_xy requires"):
        nbplot.kde_xy(np.full(100, 5.0))


def test_kde_xy_single_sample_raises():
    with pytest.raises(ValueError, match="kde_xy requires"):
        nbplot.kde_xy([1.0])
