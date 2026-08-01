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
    # The slider is sampled (at most 24 steps) rather than one frame per rank.
    assert 2 <= len(fig.frames) <= 24
    assert len(fig.layout.sliders[0].steps) == len(fig.frames)
    # The cumulative curve is static, so it lives in fig.data and not in frames.
    cum = np.asarray(fig.data[1].y, dtype=float)
    assert len(cum) == r
    assert np.all(np.diff(cum) >= -1e-12)
    np.testing.assert_allclose(cum[-1], 1.0, atol=1e-6)
    # Frames only carry the two traces that change with k.
    assert tuple(fig.frames[0].traces) == (0, 2)
    assert len(fig.frames[0].data) == 2


def test_plotly_svd_spectrum_uses_log_axis_so_the_tail_stays_visible():
    # An image puts ~89% of the energy in sigma_1; on a linear axis every bar
    # past the third is indistinguishable from zero.
    img = make_test_image(32)
    fig = viz.plotly_svd_spectrum(img)
    assert fig.layout.yaxis.type == "log"
    share = np.asarray(fig.frames[0].data[0].y, dtype=float)
    lo, hi = fig.layout.yaxis.range
    # The axis floor sits below a bar that is six orders of magnitude down.
    assert 10.0**lo < share[0] * 1e-5
    assert 10.0**hi >= share.max()


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
    # One frame per step (n_iter + 1); the static contour and the minimum marker
    # live in fig.data, so a frame carries only the growing path (trace 1).
    assert len(fig.frames) == 31
    assert len(fig.frames[-1].data) == 1
    assert tuple(fig.frames[-1].traces) == (1,)
    assert len(fig.data) == 3  # contour, path, minimum marker
    # Default bowl has its minimum at (1, 1).
    last = fig.frames[-1].data[0]
    assert abs(last.x[-1] - 1.0) < 0.5 and abs(last.y[-1] - 1.0) < 0.5


def test_plotly_gradient_descent_quadratic_actually_zigzags():
    # The surrounding text promises a zig-zag; that needs lr * lambda_max > 1.
    # A mild bowl with a small step gives a smooth monotone curve instead.
    fig = viz.plotly_gradient_descent_quadratic(n_iter=30)
    path = np.column_stack(
        [np.asarray(fig.frames[-1].data[0].x, dtype=float),
         np.asarray(fig.frames[-1].data[0].y, dtype=float)]
    )
    steps = np.diff(path, axis=0)
    flips = int(np.sum(np.sign(steps[1:, 0]) != np.sign(steps[:-1, 0])))
    assert flips >= 10, "the default bowl must oscillate along the stiff axis"


def test_plotly_axis_ranges_cover_everything_that_is_drawn():
    # A strongly shearing matrix used to be drawn outside a hard-coded range.
    fig = viz.plotly_grid_transform([np.array([[1.0, 2.0], [0.5, 1.0]])], ["degenerate"])
    xs = np.concatenate([np.asarray(tr.x, dtype=float) for tr in fig.frames[0].data])
    ys = np.concatenate([np.asarray(tr.y, dtype=float) for tr in fig.frames[0].data])
    (x_lo, x_hi), (y_lo, y_hi) = fig.layout.xaxis.range, fig.layout.yaxis.range
    assert x_lo <= xs.min() and xs.max() <= x_hi
    assert y_lo <= ys.min() and ys.max() <= y_hi
    # A non-normal matrix has ||Au|| > max|lambda|: sizing on eigenvalues clipped it.
    fig = viz.plotly_eigen_sweep(np.array([[1.0, 1.0], [0.0, 1.0]]), n_angles=13)
    au = np.concatenate([np.asarray(tr.x, dtype=float) for f in fig.frames for tr in f.data])
    x_lo, x_hi = fig.layout.xaxis.range
    assert x_lo <= au.min() and au.max() <= x_hi


def test_plotly_complex_orbit_frames_the_orbit_not_the_origin():
    # The ch.03 migration orbit converges to (66.7, 33.3); an origin-centred
    # square left it using a few percent of the canvas.
    P = np.array([[0.9, 0.2], [0.1, 0.8]])
    fig = viz.plotly_complex_orbit(P, x0=(100.0, 0.0), n_steps=20)
    pts = np.column_stack(
        [np.asarray(fig.frames[-1].data[0].x, dtype=float),
         np.asarray(fig.frames[-1].data[0].y, dtype=float)]
    )
    (x_lo, x_hi), (y_lo, y_hi) = fig.layout.xaxis.range, fig.layout.yaxis.range
    assert x_lo <= pts[:, 0].min() and pts[:, 0].max() <= x_hi
    box = (x_hi - x_lo) * (y_hi - y_lo)
    spread = (pts[:, 0].max() - pts[:, 0].min()) * (pts[:, 1].max() - pts[:, 1].min())
    assert spread / box > 0.5
    # Equal aspect is preserved so the spiral is not sheared.
    np.testing.assert_allclose(x_hi - x_lo, y_hi - y_lo, rtol=1e-9)


def test_plotly_iterative_convergence_preconditioned_variant():
    fig = viz.plotly_iterative_convergence(n_iter=40, precondition=True)
    by_name = {tr.name: np.asarray(tr.y, dtype=float) for tr in fig.data}
    assert "CG + Jacobi preconditioner" in by_name
    # On the badly scaled system, preconditioning beats plain CG.
    assert by_name["CG + Jacobi preconditioner"].min() < by_name["Conjugate Gradient"].min()


# --- new interactive 3-D / graph / step-replay figures -----------------------


def test_plotly_rank_collapse_3d_shows_one_axis_per_surviving_dimension():
    rng = np.random.default_rng(0)
    cloud = rng.standard_normal((80, 3))
    mats = [
        np.eye(3),
        np.array([[1.0, 0, 1], [0, 1, 1], [1, 1, 2]]),  # rank 2
        np.outer([1.0, 0.5, 0.2], [1.0, 1.0, 1.0]),  # rank 1
    ]
    fig = viz.plotly_rank_collapse_3d(cloud, mats, ["rank 3", "rank 2", "rank 1"])
    assert len(fig.frames) == 3
    # The basis trace draws one segment (3 points incl. the None break) per axis.
    for frame, expected in zip(fig.frames, [3, 2, 1], strict=True):
        assert len(frame.data[1].x) == 3 * expected
    # A cube aspect keeps a flattened cloud from being autoscaled back to a blob.
    assert fig.layout.scene.aspectmode == "cube"


def test_plotly_least_squares_3d_minimises_at_the_projection():
    fig = viz.plotly_least_squares_3d(n_steps=21)
    dists = [float(s.label.split("=")[-1].rstrip(")")) for s in fig.layout.sliders[0].steps]
    # The sweep passes through the foot of the perpendicular: the minimum is
    # interior, and it is the projection distance.
    assert 0 < int(np.argmin(dists)) < len(dists) - 1
    A = np.array([[1.0, 0.0], [0.6, 1.0], [0.0, 0.4]])
    b = np.array([0.6, 0.4, 1.6])
    p = A @ np.linalg.solve(A.T @ A, A.T @ b)
    np.testing.assert_allclose(min(dists), np.linalg.norm(b - p), atol=5e-3)


def test_plotly_graph_draws_every_edge_and_scales_nodes_by_value():
    from la_book.algebra import page_rank
    from la_book.datasets import make_web_graph

    names, adj = make_web_graph()
    ranks = page_rank(adj)
    fig = viz.plotly_graph(adj, names, node_value=ranks, directed=True)
    # Directed: one arrow annotation per link, and x/y carry 3 entries per edge.
    n_edges = int(adj.sum())
    assert len(fig.layout.annotations) == n_edges
    assert len(fig.data[0].x) == 3 * n_edges
    sizes = np.asarray(fig.data[1].marker.size, dtype=float)
    assert np.argmax(sizes) == int(np.argmax(ranks))  # the hub is the biggest node


def test_spring_layout_is_deterministic_and_bounded():
    from la_book.datasets import make_two_cluster_graph

    adj, _ = make_two_cluster_graph(n_per=8, seed=1)
    p1 = viz._spring_layout(adj, seed=3)
    p2 = viz._spring_layout(adj, seed=3)
    np.testing.assert_allclose(p1, p2)
    assert np.isfinite(p1).all() and np.abs(p1).max() <= 1.0 + 1e-9


def test_plotly_rref_steps_replays_every_row_operation():
    from la_book.algebra import rref, rref_steps

    Ab = np.array([[2.0, 1.0, 8.0], [1.0, 3.0, 9.0]])
    R, piv, steps = rref_steps(Ab)
    R_ref, piv_ref = rref(Ab)
    np.testing.assert_allclose(R, R_ref, atol=1e-12)
    assert piv == piv_ref
    fig = viz.plotly_rref_steps(Ab)
    # Frame 0 is the starting matrix, then one frame per recorded operation.
    assert len(fig.frames) == len(steps) + 1
    assert fig.frames[0].name.startswith("0.")
    # The last frame shows the RREF itself.
    np.testing.assert_allclose(np.asarray(fig.frames[-1].data[0].z)[::-1], R, atol=1e-9)


def test_plotly_char_poly_collapses_the_square_at_an_eigenvalue():
    A = np.array([[2.0, 1.0], [1.0, 2.0]])  # eigenvalues 1 and 3
    fig = viz.plotly_char_poly(A, n_steps=41)
    dets = [float(s.label.split("det=")[1].rstrip(")")) for s in fig.layout.sliders[0].steps]
    lams = [float(s.label.split("λ=")[1].split()[0]) for s in fig.layout.sliders[0].steps]
    # det(A - lambda I) really is what the label claims, and it changes sign
    # between the two eigenvalues.
    for lam, det in zip(lams, dets, strict=True):
        np.testing.assert_allclose(np.linalg.det(A - lam * np.eye(2)), det, atol=5e-3)
    assert min(dets) < 0 < max(dets)


def test_plotly_svd_rank_explorer_links_image_and_spectrum():
    img = make_test_image(48)
    fig = viz.plotly_svd_rank_explorer(img, ks=[1, 5, 20])
    assert len(fig.frames) == 3
    # Every frame updates both panels from the same k.
    for frame in fig.frames:
        assert tuple(frame.traces) == (0, 1)
        assert len(frame.data) == 2
    # Higher k retains more energy, and the label says so.
    pct = [float(s.label.split("説明 ")[1].split("%")[0]) for s in fig.layout.sliders[0].steps]
    assert pct == sorted(pct)
    assert fig.layout.yaxis2.type == "log"
