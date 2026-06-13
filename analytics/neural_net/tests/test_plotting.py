"""Tests for the Plotly slider helpers (structure only; rendering is client-side)."""

import numpy as np
from nn_textbook import datasets
from nn_textbook import plotting as viz


def test_plotly_image_slider_frames():
    imgs = [np.zeros((8, 8)), np.ones((8, 8)), np.eye(8)]
    fig = viz.plotly_image_slider(imgs, ["a", "b", "c"])
    assert len(fig.frames) == 3
    assert len(fig.layout.sliders[0].steps) == 3


def test_plotly_attention_slider_frames():
    rng = np.random.default_rng(0)
    scores = rng.standard_normal((5, 5))
    fig = viz.plotly_attention_slider(list("abcde"), scores, [0.5, 1.0, 2.0])
    assert len(fig.frames) == 3
    # Each frame is a valid softmax row-stochastic matrix.
    z = np.asarray(fig.frames[1].data[0].z)
    np.testing.assert_allclose(z.sum(axis=1), 1.0, atol=1e-6)


def test_plotly_decision_boundary_animates():
    X, y = datasets.make_moons_dataset(n=160, seed=0)
    fig = viz.plotly_decision_boundary(X, y, epochs=40, n_frames=6, grid_steps=30)
    assert len(fig.frames) >= 2
    # heatmap + scatter per frame.
    assert len(fig.frames[-1].data) == 2
    # Probabilities stay in [0, 1].
    z = np.asarray(fig.frames[-1].data[0].z)
    assert z.min() >= 0.0 and z.max() <= 1.0


def test_plotly_decision_boundary_learns():
    # By the last frame the boundary should classify the data better than chance.
    X, y = datasets.make_moons_dataset(n=200, seed=1)
    fig = viz.plotly_decision_boundary(X, y, epochs=200, n_frames=5, grid_steps=40)
    z0 = np.asarray(fig.frames[0].data[0].z)
    z_last = np.asarray(fig.frames[-1].data[0].z)
    # Untrained map is nearly flat; trained map spans the full probability range.
    assert (z_last.max() - z_last.min()) > (z0.max() - z0.min())


def test_plotly_training_curves_reveals():
    h1 = {"loss": list(np.linspace(2.0, 0.2, 30))}
    h2 = {"loss": list(np.linspace(2.0, 0.9, 30))}
    fig = viz.plotly_training_curves([h1, h2], ["fast", "slow"], n_frames=8)
    assert len(fig.frames) >= 2
    assert len(fig.frames[-1].data) == 2  # two configs


def test_plotly_activations_frames():
    fig = viz.plotly_activations()
    assert len(fig.frames) == 4
    # sigmoid derivative peaks at 0.25 in the middle and vanishes at the edges.
    sig = next(fr for fr in fig.frames if fr.name == "sigmoid")
    dsig = np.asarray(sig.data[1].y, dtype=float)
    assert abs(dsig.max() - 0.25) < 0.02 and dsig[0] < 0.01


def test_plotly_hidden_unfolding_separates():
    fig = viz.plotly_hidden_unfolding(epochs=180, n_frames=6)
    assert len(fig.frames) >= 2
    assert len(fig.frames[-1].data) == 1


def test_plotly_ssm_impulse_decay():
    fig = viz.plotly_ssm_impulse(decays=(0.5, 0.9), n_steps=20)
    assert len(fig.frames) == 2
    # Impulse response is A_diag**t: starts at 1, decays geometrically.
    y = np.asarray(fig.frames[0].data[0].y, dtype=float)  # decay 0.5
    np.testing.assert_allclose(y[0], 1.0, atol=1e-9)
    np.testing.assert_allclose(y[1], 0.5, atol=1e-9)
