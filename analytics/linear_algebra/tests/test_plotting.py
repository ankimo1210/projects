"""Tests for the Plotly slider helpers (structure only; rendering is client-side)."""

import numpy as np
from la_book import plotting as viz
from la_book.datasets import make_test_image


def test_plotly_grid_transform_frames():
    mats = [np.eye(2), [[1.5, 0], [0, 0.5]], [[1, 1], [0, 1]]]
    fig = viz.plotly_grid_transform(mats, ["I", "scale", "shear"])
    assert len(fig.frames) == 3
    assert len(fig.layout.sliders[0].steps) == 3


def test_plotly_curve_slider_frames_and_traces():
    x = np.linspace(0, 1, 20)
    frames = [("a", [("y", x**1, None)]), ("b", [("y", x**2, "dash"), ("z", x, None)])]
    fig = viz.plotly_curve_slider(x, frames, slider_name="n")
    assert len(fig.frames) == 2
    assert len(fig.data) == 1  # first frame has 1 curve
    assert len(fig.frames[1].data) == 2


def test_plotly_image_ranks_frames():
    fig = viz.plotly_image_ranks(make_test_image(48), [2, 5, 20])
    assert len(fig.frames) == 3
    assert len(fig.layout.sliders[0].steps) == 3


def test_plotly_eigen_sweep_frames():
    fig = viz.plotly_eigen_sweep(np.array([[2.0, 1.0], [1.0, 2.0]]), n_angles=13)
    assert len(fig.frames) == 13
    assert len(fig.layout.sliders[0].steps) == 13


def test_plotly_svd_spectrum_frames_and_energy():
    img = make_test_image(32)
    r = min(img.shape)
    fig = viz.plotly_svd_spectrum(img)
    # One frame per singular value (rank 1..r).
    assert len(fig.frames) == r
    assert len(fig.layout.sliders[0].steps) == r
    # Cumulative energy line is monotone and ends at 1.
    cum = np.asarray(fig.frames[-1].data[1].y, dtype=float)
    assert np.all(np.diff(cum) >= -1e-12)
    np.testing.assert_allclose(cum[-1], 1.0, atol=1e-9)


def test_plotly_iterative_convergence_cg_fastest():
    fig = viz.plotly_iterative_convergence(n_iter=40)
    assert len(fig.data) == 3  # Jacobi, Gauss-Seidel, CG
    by_name = {tr.name: np.asarray(tr.y, dtype=float) for tr in fig.data}
    # CG should drive the residual far lower than Jacobi within the budget.
    assert by_name["Conjugate Gradient"].min() < by_name["Jacobi"].min()


def test_plotly_pagerank_frames_sum_to_one():
    fig = viz.plotly_pagerank()
    assert len(fig.frames) >= 2
    last = np.asarray(fig.frames[-1].data[0].y, dtype=float)
    np.testing.assert_allclose(last.sum(), 1.0, atol=1e-6)


def test_plotly_gradient_descent_quadratic_converges():
    fig = viz.plotly_gradient_descent_quadratic(n_iter=30)
    # contour + path per frame; one frame per step (n_iter + 1).
    assert len(fig.frames) == 31
    assert len(fig.frames[-1].data) == 2
    # Path should approach the minimum at the origin (b = 0).
    last = fig.frames[-1].data[1]
    assert abs(last.x[-1]) < 0.5 and abs(last.y[-1]) < 0.5
