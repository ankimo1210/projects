"""Figures for Part II chapters 06-08: structure only."""

import numpy as np
import plotly.graph_objects as go
from stats_textbook import plotting


def test_likelihood_curve_peaks_at_the_mle():
    from stats_textbook import estimation as est

    rng = np.random.default_rng(0)
    x = rng.poisson(3.0, 100)
    fig = plotting.likelihood_curve("poisson", x)
    curve = fig.data[0]
    peak = float(np.asarray(curve.x)[int(np.argmax(np.asarray(curve.y)))])
    assert abs(peak - est.mle("poisson", x).estimate) < 0.05


def test_mle_sampling_distribution_has_one_frame_per_n():
    fig = plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 50, 200], n_reps=500)
    assert len(fig.frames) == 3
    assert fig.layout.sliders[0].currentvalue.prefix == "n = "


def test_coverage_intervals_draws_the_requested_count_and_marks_misses():
    fig = plotting.coverage_intervals(n_intervals=100, n=12, truth=0.0, seed=0)
    # One trace for hits, one for misses, one for the truth line.
    names = [tr.name for tr in fig.data if tr.name]
    assert any("含む" in n for n in names)
    assert any("外す" in n for n in names)
    # The title must state the measured hit count, not a nominal 95.
    assert "/100" in (fig.layout.title.text or "")


def test_coverage_intervals_hit_count_is_near_the_nominal_rate():
    fig = plotting.coverage_intervals(n_intervals=200, n=12, truth=0.0, seed=1)
    title = fig.layout.title.text
    hits = int(title.split("/")[0].split()[-1])
    assert 175 <= hits <= 199, f"got {hits}/200"


def test_bootstrap_distribution_marks_the_observed_statistic():
    rng = np.random.default_rng(2)
    fig = plotting.bootstrap_distribution(rng.exponential(1.0, 60), np.median, n_boot=400)
    assert any(tr.type == "bar" for tr in fig.data)
    assert len(fig.layout.shapes) >= 1, "the observed value needs a marker line"


def test_power_curves_are_monotone_in_n():
    fig = plotting.power_curves(effects=[0.2, 0.5, 0.8], ns=[10, 20, 40, 80], alpha=0.05)
    for tr in fig.data:
        y = np.asarray(tr.y, dtype=float)
        assert np.all(np.diff(y) >= -1e-9), f"{tr.name} is not increasing in n"


def test_phacking_demo_separates_raw_from_corrected():
    fig = plotting.phacking_demo(n_tests=200, n=30, seed=0)
    names = [tr.name for tr in fig.data if tr.name]
    assert len(names) >= 2
    assert any("補正なし" in n for n in names)


def test_every_inference_figure_goes_through_the_shared_slider():
    import inspect

    from stats_textbook.plotting import inference

    src = inspect.getsource(inference)
    assert '"method": "animate"' not in src, "build frames and call frame_slider instead"


def test_inference_figures_ship_counts_not_raw_samples():
    """Same rule as Part I: histograms would serialise every replicate."""
    import inspect

    from stats_textbook.plotting import inference

    assert "go.Histogram(" not in inspect.getsource(inference)


def test_all_inference_figures_are_plotly_figures():
    rng = np.random.default_rng(3)
    figs = [
        plotting.likelihood_curve("poisson", rng.poisson(3.0, 50)),
        plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 40], n_reps=300),
        plotting.coverage_intervals(n_intervals=30, n=10, seed=0),
        plotting.bootstrap_distribution(rng.exponential(1.0, 40), np.mean, n_boot=200),
        plotting.power_curves([0.5], [10, 20]),
        plotting.phacking_demo(n_tests=50, n=20, seed=0),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
