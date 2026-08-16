"""Figures for chapters 11-12."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_interval_comparison_shows_both_kinds():
    fig = plotting.interval_comparison([(8, 10), (80, 100)])
    names = [tr.name for tr in fig.data if tr.name]
    assert any("信頼区間" in n for n in names)
    assert any("信用区間" in n for n in names)


def test_interval_comparison_marks_the_excursion_past_one():
    """At k=8, n=10 the Wald interval runs past 1.0 and the figure must
    not quietly clip it -- that excursion is the chapter's point."""
    fig = plotting.interval_comparison([(8, 10)])
    xs = [v for tr in fig.data for v in (tr.x or []) if v is not None]
    assert max(float(v) for v in xs) > 1.0


def test_prior_influence_curves_converge():
    fig = plotting.prior_influence(ns=[5, 50, 500, 5000], p_true=0.7)
    for tr in fig.data:
        if tr.name and "MLE" not in tr.name:
            y = np.asarray(tr.y, dtype=float)
            assert abs(y[-1] - 0.7) < abs(y[0] - 0.7), f"{tr.name} does not converge"


def test_posterior_slider_has_one_frame_per_dataset():
    fig = plotting.posterior_slider([(4, 5), (40, 50), (400, 500)])
    assert len(fig.frames) == 3


def test_capstone_three_lenses_draws_data_and_three_fits():
    fig = plotting.capstone_three_lenses()
    names = [tr.name for tr in fig.data if tr.name]
    assert any("観測" in n for n in names)
    assert any("頻度論" in n for n in names)
    assert any("ベイズ" in n for n in names)
    assert any("機械学習" in n for n in names)


def test_capstone_reports_the_penalty_cross_validation_picked():
    """At the book's default degree of 5, cross-validation selects the
    bottom of the grid and the ML curve coincides with least squares
    (measured: lambda = 1e-4, both norms 7.40). Putting the selected
    penalty in the legend is what keeps that from reading as a bug."""
    names = [tr.name for tr in plotting.capstone_three_lenses().data if tr.name]
    ml = next(n for n in names if "機械学習" in n)
    assert "λ=" in ml, ml
    assert "0.0001" in ml, ml


def test_cross_validation_does_shrink_once_the_model_can_overfit():
    """The counterpart fact NB12 uses: at degree 9 least squares blows up
    to a norm of 53.7 and cross-validation pulls it back to 4.2."""
    degree = 9
    names = [tr.name for tr in plotting.capstone_three_lenses(degree=degree).data if tr.name]
    norms = {}
    for key in ["頻度論", "機械学習"]:
        label = next(n for n in names if key in n)
        norms[key] = float(label.split("||w|| = ")[1].rstrip(")"))
    assert norms["頻度論"] > 40.0, norms
    assert norms["機械学習"] < 10.0, norms


def test_bridge_figures_go_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import bridge as bp

    assert '"method": "animate"' not in inspect.getsource(bp)


def test_bridge_figures_ship_counts_not_raw_samples():
    import inspect

    from stats_textbook.plotting import bridge as bp

    assert "go.Histogram(" not in inspect.getsource(bp)


def test_all_bridge_figures_are_plotly_figures():
    figs = [
        plotting.interval_comparison([(8, 10), (80, 100)]),
        plotting.prior_influence(ns=[5, 50]),
        plotting.posterior_slider([(4, 5), (40, 50)]),
        plotting.capstone_three_lenses(),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
