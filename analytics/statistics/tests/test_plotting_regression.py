"""Figures for chapters 09-10."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_residual_catalogue_has_one_frame_per_pathology():
    fig = plotting.residual_catalogue(seed=0, n=150)
    assert len(fig.frames) == 4
    labels = [f.name for f in fig.frames]
    assert "健全" in labels[0]


def test_coefficient_sampling_centres_on_the_true_slope():
    fig = plotting.coefficient_sampling(n=60, n_reps=800, seed=0)
    bars = [tr for tr in fig.data if tr.type == "bar"]
    assert bars, "the sampling distribution is drawn as binned bars"
    x = np.asarray(bars[0].x, dtype=float)
    y = np.asarray(bars[0].y, dtype=float)
    centre = float((x * y).sum() / y.sum())
    assert abs(centre - 2.0) < 0.15, f"centred at {centre}"


def test_robust_se_comparison_shows_both_kinds():
    fig = plotting.robust_se_comparison(seed=0, ns=(50, 200))
    names = [tr.name for tr in fig.data if tr.name]
    assert any("通常" in n for n in names)
    assert any("HC3" in n for n in names)


def test_link_function_fits_draws_one_curve_per_family():
    rng = np.random.default_rng(1)
    x = rng.normal(size=200)
    y = (rng.random(200) < 1 / (1 + np.exp(-x))).astype(float)
    fig = plotting.link_function_fits(x, y, families=("binomial", "gaussian"))
    curves = [tr for tr in fig.data if tr.mode and "lines" in tr.mode]
    assert len(curves) == 2


def test_irls_convergence_shows_the_parameter_path():
    rng = np.random.default_rng(2)
    n = 300
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    y = rng.binomial(1, 1 / (1 + np.exp(-(X @ [-0.5, 1.2])))).astype(float)
    fig = plotting.irls_convergence(X, y, family="binomial", max_iter=8)
    assert len(fig.data) >= 1
    y0 = np.asarray(fig.data[0].y, dtype=float)
    assert len(y0) >= 3, "at least three iterations should be plotted"


def test_regression_figures_go_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import regression as rp

    assert '"method": "animate"' not in inspect.getsource(rp)


def test_regression_figures_ship_counts_not_raw_samples():
    import inspect

    from stats_textbook.plotting import regression as rp

    assert "go.Histogram(" not in inspect.getsource(rp)


def test_all_regression_figures_are_plotly_figures():
    rng = np.random.default_rng(3)
    x = rng.normal(size=120)
    y = (rng.random(120) < 0.5).astype(float)
    figs = [
        plotting.residual_catalogue(seed=0, n=100),
        plotting.coefficient_sampling(n=40, n_reps=400, seed=0),
        plotting.robust_se_comparison(seed=0, ns=(50,)),
        plotting.link_function_fits(x, y),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
