"""Plotly figure helpers: structure only -- rendering is client-side."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import datasets, plotting
from stats_textbook.processes import MarkovChain

TWO_STATE = np.array([[0.9, 0.1], [0.2, 0.8]])


def test_frame_slider_wires_one_step_per_frame():
    frames = [go.Frame(data=[go.Bar(x=["a"], y=[i])], name=str(i)) for i in range(4)]
    fig = plotting.frame_slider(frames, "n")
    assert len(fig.frames) == 4
    labels = [s["label"] for s in fig.layout.sliders[0].steps]
    assert labels == ["0", "1", "2", "3"]
    assert fig.layout.sliders[0].currentvalue.prefix == "n = "


def test_every_animated_figure_goes_through_frame_slider():
    """No figure may hand-roll its slider -- the wiring lives in one place."""
    import inspect

    from stats_textbook.plotting import probability

    src = inspect.getsource(probability)
    assert '"method": "animate"' not in src, "build frames and call frame_slider instead"


def test_curve_slider_builds_one_frame_per_step():
    x = np.linspace(0, 1, 20)
    frames = [("a", [("y", x**1, None)]), ("b", [("y", x**2, "dash"), ("z", x, None)])]
    fig = plotting.curve_slider(x, frames, slider_name="n")
    assert isinstance(fig, go.Figure)
    assert len(fig.frames) == 2
    assert len(fig.layout.sliders[0].steps) == 2
    assert len(fig.frames[1].data) == 2


def test_ppv_slider_shows_ppv_collapsing_at_low_prevalence():
    fig = plotting.ppv_slider([0.001, 0.01, 0.1, 0.5], sensitivity=0.99, specificity=0.95)
    assert len(fig.frames) == 4
    # The headline number must be legible from the figure's own data.
    assert fig.layout.yaxis.title.text is not None


def test_joint_marginal_heatmap_has_a_heatmap_and_two_margins():
    x, y = datasets.bivariate_normal(2000, rho=0.7, seed=0)
    fig = plotting.joint_marginal_heatmap(x, y, bins=20)
    kinds = [tr.type for tr in fig.data]
    assert "heatmap" in kinds
    assert kinds.count("bar") == 2, "one marginal per axis"


def test_poisson_limit_slider_frames_match_the_n_values():
    fig = plotting.poisson_limit_slider([5, 20, 100], lam=2.0, k_max=12)
    assert len(fig.frames) == 3
    # Binomial pmf and the Poisson limit are drawn together in every frame.
    assert len(fig.frames[0].data) == 2


def test_relation_graph_draws_every_edge_and_labels_every_node():
    fig = plotting.relation_graph()
    from stats_textbook import distributions as dist

    node_trace = [tr for tr in fig.data if tr.mode and "text" in tr.mode]
    assert node_trace, "nodes must carry text labels"
    assert len(node_trace[0].text) == len(dist.relation_layout())


def test_clt_convergence_has_one_frame_per_sample_size():
    fig = plotting.clt_convergence(["normal", "exponential", "cauchy"], ns=[1, 5, 30], n_reps=400)
    assert len(fig.frames) == 3
    # One histogram per sampler in each frame.
    assert len(fig.frames[0].data) == 3


def test_clt_convergence_bins_every_series_on_the_same_grid():
    """Per-series autobinning would render Cauchy as nothing, not as wide."""
    fig = plotting.clt_convergence(["normal", "cauchy"], ns=[50], n_reps=1500)
    bins = [tr.xbins for tr in fig.frames[0].data]
    assert bins[0] == bins[1], "series must share one binning to be comparable"
    assert all(tr.autobinx is False for tr in fig.frames[0].data)


def test_clt_convergence_names_the_off_screen_mass():
    """A series that mostly falls outside the window must say so."""
    fig = plotting.clt_convergence(["normal", "cauchy"], ns=[50], n_reps=1500)
    names = [tr.name for tr in fig.frames[0].data]
    assert names[0] == "normal", "a normal fits inside the window; no annotation"
    assert "枠外" in names[1], f"Cauchy must report its off-screen share, got {names[1]!r}"


def test_clt_convergence_is_deterministic():
    a = plotting.clt_convergence(["exponential"], ns=[2, 8], n_reps=300, seed=11)
    b = plotting.clt_convergence(["exponential"], ns=[2, 8], n_reps=300, seed=11)
    np.testing.assert_array_equal(a.frames[-1].data[0].x, b.frames[-1].data[0].x)


def test_random_walk_paths_caps_the_number_drawn():
    from stats_textbook.processes import random_walk

    paths = random_walk(100, n_paths=200, seed=0)
    fig = plotting.random_walk_paths(paths, n_show=12)
    assert len(fig.data) <= 13, "12 paths plus at most one envelope trace"


def test_markov_convergence_slider_ends_at_the_stationary_law():
    chain = MarkovChain(TWO_STATE)
    fig = plotting.markov_convergence_slider(chain, p0=np.array([1.0, 0.0]), n_steps=40)
    assert len(fig.frames) == 41
    final = np.asarray(fig.frames[-1].data[0].y, dtype=float)
    np.testing.assert_allclose(final, chain.stationary(), atol=1e-6)
