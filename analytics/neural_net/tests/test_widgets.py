"""Tests for the ipywidgets demos and plotly interactives.

A browser cannot be driven from pytest, but ipywidgets callbacks run entirely
kernel-side: creating each widget and programmatically changing its control
values exercises the same code path a user's slider drag would. Each test
asserts the demo builds and its redraw callback survives value changes.
"""

import matplotlib

matplotlib.use("Agg")  # headless backend; plt.show() becomes a no-op

import matplotlib.pyplot as plt
import numpy as np
import pytest
from nn_textbook import widgets as wdg


def _poke(interact_result, n_changes: int = 2):
    """Simulate user interaction: flip every control to a few new values."""
    container = interact_result.widget  # the `interactive` container
    for child in container.children:
        if not hasattr(child, "value"):
            continue
        if hasattr(child, "options") and child.options:  # Dropdown
            for opt in list(child.options)[:n_changes]:
                child.value = opt if not isinstance(opt, tuple) else opt[1]
        elif hasattr(child, "min") and hasattr(child, "max"):  # sliders
            lo, hi = child.min, child.max
            for frac in (0.25, 0.9)[:n_changes]:
                child.value = type(child.value)(lo + frac * (hi - lo))
    plt.close("all")


def test_activation_explorer():
    _poke(wdg.activation_explorer())


def test_learning_rate_explorer():
    from nn_textbook.datasets import make_moons_dataset
    from nn_textbook.models import MLP
    from nn_textbook.training import train_numpy_mlp

    X, y = make_moons_dataset(n=60, seed=0)

    def fresh():
        return MLP([2, 8, 2], seed=0)

    def quick_train(model, X, y, lr):
        train_numpy_mlp(model, X, y, lr=lr, epochs=3, batch_size=32, seed=0)

    _poke(wdg.learning_rate_explorer(fresh, X, y, quick_train))


def test_decision_boundary_trainer():
    from nn_textbook.datasets import make_moons_dataset
    from nn_textbook.models import MLP
    from nn_textbook.training import train_numpy_mlp

    X, y = make_moons_dataset(n=60, seed=0)
    model = MLP([2, 8, 2], seed=0)

    def step_fn(m, n_steps):
        if n_steps > 0:
            train_numpy_mlp(m, X, y, lr=0.3, epochs=max(1, n_steps // 20), batch_size=32, seed=0)

    _poke(wdg.decision_boundary_trainer(model, X, y, step_fn, max_steps=40, stride=20))


def test_convolution_kernel_explorer():
    rng = np.random.default_rng(0)
    _poke(wdg.convolution_kernel_explorer(rng.random((16, 16))))


def test_attention_matrix_explorer():
    tokens = ["a", "b", "c"]
    E = np.eye(3)
    _poke(wdg.attention_matrix_explorer(tokens, E))


def test_positional_encoding_explorer():
    _poke(wdg.positional_encoding_explorer(seq_len=20, d_model=8))


def test_latent_interpolation_explorer():
    def decode(z):
        return np.tile(z.sum(), 16)  # any flat "image" of fixed size

    _poke(wdg.latent_interpolation_explorer(decode, np.zeros(2), np.ones(2), image_shape=(4, 4)))


def test_diffusion_noising_explorer():
    rng = np.random.default_rng(1)
    _poke(wdg.diffusion_noising_explorer(rng.random((8, 8))))


# ---------------------------------------------------------------------------
# Plotly interactives (slider figures that survive in static HTML)
# ---------------------------------------------------------------------------


def test_plotly_image_slider_structure():
    from nn_textbook.plotting import plotly_image_slider

    imgs = [np.random.default_rng(i).random((8, 8)) for i in range(4)]
    fig = plotly_image_slider(imgs, labels=[0.0, 0.3, 0.6, 1.0], slider_name="t")
    assert len(fig.frames) == 4
    assert len(fig.layout.sliders[0].steps) == 4


def test_plotly_attention_slider_rows_softmaxed():
    from nn_textbook.plotting import plotly_attention_slider

    rng = np.random.default_rng(0)
    scores = rng.standard_normal((4, 4))
    fig = plotly_attention_slider(list("abcd"), scores, temperatures=[0.5, 1.0, 2.0])
    assert len(fig.frames) == 3
    z = np.array(fig.data[0].z)
    np.testing.assert_allclose(z.sum(axis=1), np.ones(4), atol=1e-10)


def test_widgets_require_ipywidgets():
    pytest.importorskip("ipywidgets")
