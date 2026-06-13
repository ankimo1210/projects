"""Tests for the Plotly slider helpers (structure only; rendering is client-side)."""

import numpy as np
from bayes_textbook import visualization as viz
from bayes_textbook.conjugacy import BetaBinomial
from bayes_textbook.models import metropolis_hastings


def test_plotly_curve_slider_frames_and_traces():
    x = np.linspace(0, 1, 20)
    frames = [("a", [("y", x**1, None)]), ("b", [("y", x**2, "dash"), ("z", x, None)])]
    fig = viz.plotly_curve_slider(x, frames, slider_name="n")
    assert len(fig.frames) == 2
    assert len(fig.data) == 1
    assert len(fig.frames[1].data) == 2


def test_plotly_posterior_update_frames():
    rng = np.random.default_rng(0)
    flips = (rng.random(12) < 0.7).astype(int)
    fig = viz.plotly_posterior_update(BetaBinomial(2, 2), flips)
    # One frame per accumulated flip count, 0..n inclusive.
    assert len(fig.frames) == len(flips) + 1
    assert len(fig.layout.sliders[0].steps) == len(flips) + 1
    # Each frame draws prior, likelihood, posterior.
    assert len(fig.frames[0].data) == 3


def test_plotly_posterior_update_is_deterministic():
    flips = np.array([1, 0, 1, 1, 0, 1])
    f1 = viz.plotly_posterior_update(BetaBinomial(1, 1), flips)
    f2 = viz.plotly_posterior_update(BetaBinomial(1, 1), flips)
    np.testing.assert_array_equal(f1.frames[-1].data[2].y, f2.frames[-1].data[2].y)


def test_plotly_mcmc_trace_reveals_chain():
    samples, _rate = metropolis_hastings(
        lambda t: -0.5 * t**2, x0=0.0, n_steps=300, proposal_sd=1.0, seed=1
    )
    fig = viz.plotly_mcmc_trace(samples, target=0.0, n_frames=10)
    assert len(fig.frames) <= 10 and len(fig.frames) >= 1
    # trace, running mean, target = 3 curves per frame.
    assert len(fig.frames[-1].data) == 3
    # Last frame's running mean ends near the target (standard normal -> 0).
    rmean = np.asarray(fig.frames[-1].data[1].y, dtype=float)
    assert abs(np.nanmean(rmean[-10:])) < 0.5


def test_plotly_posterior_predictive_bands():
    rng = np.random.default_rng(3)
    x = np.linspace(-2, 2, 40)
    y = 0.5 * x**2 - x + 0.3 * rng.standard_normal(40)
    fig = viz.plotly_posterior_predictive(x, y, degree=2, n_frames=6)
    assert len(fig.frames) >= 1
    # 4 band traces + mean + data = 6 traces per frame.
    assert len(fig.frames[-1].data) == 6


def test_plotly_gp_regression_band_shrinks():
    fig = viz.plotly_gp_regression(n_frames=6)
    assert len(fig.frames) >= 2
    assert len(fig.frames[-1].data) == 4  # upper, lower, mean, observations
    # More observations in the last frame than the first.
    assert len(fig.frames[-1].data[3].x) > len(fig.frames[0].data[3].x)


def test_plotly_bandit_regret_thompson_wins():
    fig = viz.plotly_bandit_regret(n_rounds=1500, seed=0)
    assert len(fig.data) == 2
    by = {tr.name: np.asarray(tr.y, dtype=float) for tr in fig.data}
    # Thompson sampling ends with lower cumulative regret than epsilon-greedy.
    assert by["Thompson sampling"][-1] < by["epsilon-greedy"][-1]


def test_plotly_gibbs_path_reveals():
    fig = viz.plotly_gibbs_path(rho=0.8, n_steps=60, n_frames=10)
    assert len(fig.frames) >= 2
    # contour + chain per frame; chain grows over frames.
    assert len(fig.frames[-1].data) == 2
    assert len(fig.frames[-1].data[1].x) > len(fig.frames[0].data[1].x)
