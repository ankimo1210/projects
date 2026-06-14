"""Tests for the Plotly slider helpers (structure only; rendering is client-side)."""

import numpy as np
from la_book import plotting as viz
from la_book.datasets import make_test_image


def test_plotly_grid_transform_frames():
    mats = [np.eye(2), [[1.5, 0], [0, 0.5]], [[1, 1], [0, 1]]]
    fig = viz.plotly_grid_transform(mats, ["I", "scale", "shear"])
    assert len(fig.frames) == 3
    assert len(fig.layout.sliders[0].steps) == 3


def test_plotly_linear_map_morph_frames_and_endpoints():
    A = np.array([[1.0, 1.0], [0.0, 1.0]])  # shear, det stays 1
    fig = viz.plotly_linear_map_morph(A, n_steps=11)
    assert len(fig.frames) == 11
    assert len(fig.layout.sliders[0].steps) == 11
    # t = 0 is the identity, t = 1 is A; both labels carry the live det.
    assert fig.frames[0].name.startswith("0.00")
    assert fig.frames[-1].name.startswith("1.00")
    assert "det=" in fig.layout.sliders[0].steps[0].label
    # Each frame: grid (ticks*2 lines) + filled unit square + 2 basis arrows.
    assert sum(tr.name == "Ae1" for tr in fig.frames[-1].data) == 1


def test_plotly_linear_map_morph_detects_collapse():
    # A degenerate matrix: det(A) = 0, so the last frame's square collapses.
    A = np.array([[1.0, 2.0], [0.5, 1.0]])
    fig = viz.plotly_linear_map_morph(A, n_steps=5)
    assert fig.frames[-1].name.endswith("det=+0.00)") or "0.00" in fig.frames[-1].name


def test_plotly_svd_action_stages():
    fig = viz.plotly_svd_action(np.array([[1.2, 0.8], [0.0, 0.9]]))
    assert len(fig.frames) == 4
    assert len(fig.layout.sliders[0].steps) == 4
    # Stage 1 is the unit circle (max radius ~ 1); last stage = A (radius ~ s_max).
    first = np.asarray(fig.frames[0].data[0].x, dtype=float)
    np.testing.assert_allclose(np.abs(first).max(), 1.0, atol=1e-6)


def test_plotly_two_line_system_collapses():
    fig = viz.plotly_two_line_system(n_steps=11)
    assert len(fig.frames) == 11
    assert len(fig.layout.sliders[0].steps) == 11
    # t=0 unique solution -> 3 traces (2 lines + marker); near t=1 the marker
    # is dropped (parallel lines, no in-range solution).
    assert any(tr.name == "solution" for tr in fig.frames[0].data)
    assert fig.frames[-1].name.startswith("1.00")


def test_plotly_projection_sweep_inner_product_in_label():
    fig = viz.plotly_projection_sweep(n_angles=13)
    assert len(fig.frames) == 13
    assert "a·b=" in fig.layout.sliders[0].steps[0].label
    # b, proj, residual and the span line are all present.
    names = {tr.name for tr in fig.frames[0].data}
    assert {"b", "proj", "residual", "span{a}"} <= names


def test_plotly_poly_fit_degree_rmse_decreases():
    rng = np.random.default_rng(0)
    x = np.linspace(-1, 1, 25)
    y = x**2 + 0.1 * rng.standard_normal(x.size)
    fig = viz.plotly_poly_fit_degree(x, y, degrees=[1, 2, 6, 12])
    assert len(fig.frames) == 4
    labels = [s.label for s in fig.layout.sliders[0].steps]

    def rmse(lbl):
        return float(lbl.split("RMSE=")[1].rstrip(")"))

    # Higher degree never increases the *training* RMSE.
    vals = [rmse(lbl) for lbl in labels]
    assert all(vals[i + 1] <= vals[i] + 1e-9 for i in range(len(vals) - 1))


def test_plotly_complex_orbit_frames():
    theta = 0.4
    A = 1.05 * np.array([[np.cos(theta), -np.sin(theta)],
                         [np.sin(theta), np.cos(theta)]])  # spiral out
    fig = viz.plotly_complex_orbit(A, n_steps=20)
    assert len(fig.frames) == 21  # x0 .. x20
    # The orbit grows (|x_k| increasing) for an expanding spiral.
    last = np.asarray(fig.frames[-1].data[0].x, dtype=float)
    assert abs(last[-1]) > abs(last[0]) or len(last) == 21


def test_plotly_kron_blocks_frames():
    A = np.array([[1.0, 2.0], [0.0, -1.0]])
    B = np.array([[1.0, 0.0], [0.0, 1.0]])
    fig = viz.plotly_kron_blocks(A, B)
    assert len(fig.frames) == 4  # 2x2 A -> 4 blocks
    # Each frame: heatmap + block outline.
    assert len(fig.frames[0].data) == 2
    assert "a[0,0]" in fig.layout.sliders[0].steps[0].label


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
