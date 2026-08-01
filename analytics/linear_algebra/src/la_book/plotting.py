"""Shared plotting helpers (matplotlib + a few Plotly figures).

Figure labels are kept in English so no Japanese font setup is required;
the surrounding notebook text carries the Japanese explanation.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

VEC_COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]


def _square_box(points, pad: float = 0.12, include_origin: bool = False):
    """Equal-aspect axis ranges that frame ``points`` (shape (n, 2)) snugly.

    Plotly figures here pin ``scaleanchor`` so x and y share a scale; a range
    picked from unrelated quantities (eigenvalues, a fixed constant) either
    clips the drawing or leaves it in a corner of a mostly empty canvas. This
    returns (x_range, y_range) of equal width centred on the data, so every
    frame's content is both fully visible and reasonably large.
    """
    p = np.asarray(points, dtype=float).reshape(-1, 2)
    lo, hi = p.min(axis=0), p.max(axis=0)
    if include_origin:
        lo, hi = np.minimum(lo, 0.0), np.maximum(hi, 0.0)
    center = 0.5 * (lo + hi)
    half = max(0.5 * float(np.max(hi - lo)), 1e-9) * (1.0 + pad)
    return (
        [float(center[0] - half), float(center[0] + half)],
        [float(center[1] - half), float(center[1] + half)],
    )


def _f(a, decimals: int = 4):
    """Round coordinates before they are embedded in the notebook JSON.

    Slider figures repeat their traces once per frame, so full float64 repr
    dominates the committed ``.ipynb`` size while adding no visible precision.
    """
    return np.round(np.asarray(a, dtype=float), decimals).tolist()


def _setup_ax(ax, lim: float, title: str | None = None):
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    if title:
        ax.set_title(title)


def plot_vectors(vectors, labels=None, colors=None, ax=None, lim=None, origin=(0.0, 0.0)):
    """Draw 2-D vectors as arrows from a common origin."""
    vectors = [np.asarray(v, dtype=float) for v in vectors]
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    if lim is None:
        lim = 1.3 * max(1.0, max(np.abs(v).max() for v in vectors))
    if colors is None:
        colors = [VEC_COLORS[i % len(VEC_COLORS)] for i in range(len(vectors))]
    ox, oy = origin
    for i, v in enumerate(vectors):
        ax.annotate(
            "",
            xy=(ox + v[0], oy + v[1]),
            xytext=(ox, oy),
            arrowprops={"arrowstyle": "-|>", "color": colors[i], "lw": 2},
        )
        if labels is not None:
            ax.text(ox + v[0] * 1.07, oy + v[1] * 1.07, labels[i], color=colors[i], fontsize=12)
    _setup_ax(ax, lim)
    return ax


def plot_vector_sum(a, b, ax=None):
    """Parallelogram picture of a + b."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    s = a + b
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5.5))
    lim = 1.3 * max(1.0, np.abs(np.vstack([a, b, s])).max())
    plot_vectors([a, b, s], labels=["a", "b", "a+b"], ax=ax, lim=lim)
    # Dashed translated copies complete the parallelogram.
    ax.plot([a[0], s[0]], [a[1], s[1]], "--", color=VEC_COLORS[1], alpha=0.6)
    ax.plot([b[0], s[0]], [b[1], s[1]], "--", color=VEC_COLORS[0], alpha=0.6)
    return ax


def _grid_segments(lim: float = 2.0, step: float = 0.5, n_pts: int = 41):
    """Line segments of a square grid as a list of (2, n_pts) arrays."""
    ticks = np.arange(-lim, lim + step / 2, step)
    t = np.linspace(-lim, lim, n_pts)
    segs = []
    for c in ticks:
        segs.append(np.vstack([np.full_like(t, c), t]))  # vertical line x = c
        segs.append(np.vstack([t, np.full_like(t, c)]))  # horizontal line y = c
    return segs


def plot_grid_transform(A, lim: float = 2.0, axes=None, show_basis: bool = True):
    """Two panels: the standard grid, and its image under the matrix A."""
    A = np.asarray(A, dtype=float)
    if axes is None:
        _, axes = plt.subplots(1, 2, figsize=(10, 5))
    segs = _grid_segments(lim=lim)
    out_lim = max(lim, 1.25 * np.abs(A @ np.array([[lim, lim], [lim, -lim]]).T).max())
    for seg in segs:
        axes[0].plot(*seg, color="#1f77b4", lw=0.6, alpha=0.5)
        axes[1].plot(*(A @ seg), color="#1f77b4", lw=0.6, alpha=0.5)
    if show_basis:
        e1, e2 = np.array([1.0, 0.0]), np.array([0.0, 1.0])
        plot_vectors([e1, e2], labels=["e1", "e2"], ax=axes[0], lim=lim)
        plot_vectors([A @ e1, A @ e2], labels=["Ae1", "Ae2"], ax=axes[1], lim=out_lim)
    _setup_ax(axes[0], lim, "before")
    _setup_ax(axes[1], out_lim, f"after: det A = {np.linalg.det(A):.2f}")
    return axes


def plot_unit_square(A, ax=None):
    """Unit square vs its image under A; the area ratio is |det A|."""
    A = np.asarray(A, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5.5))
    sq = np.array([[0, 1, 1, 0, 0], [0, 0, 1, 1, 0]], dtype=float)
    im = A @ sq
    ax.fill(sq[0], sq[1], color="#1f77b4", alpha=0.3, label="unit square (area 1)")
    ax.fill(
        im[0], im[1], color="#d62728", alpha=0.3, label=f"image (area {abs(np.linalg.det(A)):.2f})"
    )
    ax.plot(sq[0], sq[1], color="#1f77b4")
    ax.plot(im[0], im[1], color="#d62728")
    lim = 1.2 * max(1.5, np.abs(im).max())
    _setup_ax(ax, lim)
    ax.legend(loc="upper left", fontsize=9)
    return ax


def plot_direction_field(A, n_dirs: int = 36, ax=None, tol_deg: float = 3.0):
    """For unit directions u, draw u (gray) and Au; directions where Au stays
    parallel to u (eigen-directions) are highlighted in red."""
    A = np.asarray(A, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    thetas = np.linspace(0, 2 * np.pi, n_dirs, endpoint=False)
    max_len = 1.0
    for th in thetas:
        u = np.array([np.cos(th), np.sin(th)])
        Au = A @ u
        max_len = max(max_len, np.linalg.norm(Au))
        cross = abs(u[0] * Au[1] - u[1] * Au[0])
        aligned = cross < np.sin(np.deg2rad(tol_deg)) * np.linalg.norm(Au)
        ax.plot([0, u[0]], [0, u[1]], color="gray", lw=0.8, alpha=0.5)
        ax.annotate(
            "",
            xy=Au,
            xytext=(0, 0),
            arrowprops={
                "arrowstyle": "-|>",
                "color": "#d62728" if aligned else "#1f77b4",
                "lw": 2.0 if aligned else 0.9,
                "alpha": 1.0 if aligned else 0.6,
            },
        )
    _setup_ax(ax, 1.15 * max_len, "u (gray) vs Au (red = direction preserved)")
    return ax


def plot_projection(b, a, ax=None):
    """Project b onto the line spanned by a; dashed segment is the residual."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    p = (a @ b) / (a @ a) * a
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5.5))
    lim = 1.4 * max(1.0, np.abs(np.vstack([a, b])).max())
    t = np.linspace(-lim, lim, 2)
    na = a / np.linalg.norm(a)
    ax.plot(t * na[0], t * na[1], color="gray", lw=1, label="span{a}")
    plot_vectors([b, p], labels=["b", "proj"], colors=["#1f77b4", "#d62728"], ax=ax, lim=lim)
    ax.plot([b[0], p[0]], [b[1], p[1]], "k--", lw=1.2, label="residual (orthogonal)")
    ax.legend(loc="upper left", fontsize=9)
    return ax


def plot_least_squares(x, y, coeffs, ax=None, label: str | None = None):
    """Scatter + fitted polynomial (highest degree first) + vertical residuals."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 4.5))
    yhat = np.polyval(coeffs, x)
    xs = np.linspace(x.min(), x.max(), 200)
    ax.scatter(x, y, s=22, color="#1f77b4", zorder=3)
    ax.plot(xs, np.polyval(coeffs, xs), color="#d62728", lw=2, label=label or "fit")
    ax.vlines(x, yhat, y, color="gray", lw=0.8, alpha=0.7)
    ax.grid(alpha=0.25)
    ax.legend()
    return ax


def plot_svd_action(A, n_pts: int = 200):
    """Unit circle through the three SVD stages: x -> V^T x -> S V^T x -> U S V^T x."""
    A = np.asarray(A, dtype=float)
    U, s, Vt = np.linalg.svd(A)
    th = np.linspace(0, 2 * np.pi, n_pts)
    circ = np.vstack([np.cos(th), np.sin(th)])
    stages = [
        (circ, "unit circle"),
        (Vt @ circ, "rotate: V^T x"),
        (np.diag(s) @ Vt @ circ, "stretch: S V^T x"),
        (U @ np.diag(s) @ Vt @ circ, "rotate: U S V^T x = Ax"),
    ]
    lim = 1.3 * max(1.0, s.max())
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2))
    v_cols = ["#d62728", "#1f77b4"]
    for ax, (pts, title) in zip(axes, stages, strict=True):
        ax.plot(pts[0], pts[1], color="#2ca02c", lw=1.5)
        _setup_ax(ax, lim, title)
    # Right singular vectors on the first panel, scaled left ones on the last.
    for i in range(2):
        v = Vt[i]
        axes[0].annotate(
            "", xy=v, xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "color": v_cols[i], "lw": 2}
        )
        axes[0].text(*(v * 1.15), f"v{i + 1}", color=v_cols[i])
        u = s[i] * U[:, i]
        axes[3].annotate(
            "", xy=u, xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "color": v_cols[i], "lw": 2}
        )
        axes[3].text(*(u * 1.1), f"s{i + 1} u{i + 1}", color=v_cols[i])
    fig.tight_layout()
    return axes


def plot_singular_spectrum(s, ax=None, log: bool = True):
    """Singular values in decreasing order (log scale by default)."""
    s = np.asarray(s, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.plot(np.arange(1, len(s) + 1), s, "o-", ms=4)
    if log:
        ax.set_yscale("log")
    ax.set_xlabel("index k")
    ax.set_ylabel("singular value")
    ax.grid(alpha=0.3)
    return ax


def show_image_ranks(img, ks, cmap: str = "gray"):
    """Original image next to its best rank-k approximations."""
    from .decompositions import compression_ratio, svd_lowrank

    img = np.asarray(img, dtype=float)
    n = len(ks) + 1
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n, 3.4))
    axes[0].imshow(img, cmap=cmap)
    axes[0].set_title(f"original (rank {min(img.shape)})")
    for ax, k in zip(axes[1:], ks, strict=True):
        ax.imshow(svd_lowrank(img, k), cmap=cmap)
        ratio = compression_ratio(img.shape, k)
        ax.set_title(f"rank {k} ({ratio:.0%} storage)")
    for ax in axes:
        ax.axis("off")
    fig.tight_layout()
    return axes


def plot_pca_axes(X, result, ax=None, scale: float = 2.0):
    """Scatter of 2-D data with principal axes drawn from the mean.

    Arrow lengths are scale * sqrt(explained variance)."""
    X = np.asarray(X, dtype=float)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(X[:, 0], X[:, 1], s=12, alpha=0.45, color="#1f77b4")
    for i, (comp, var) in enumerate(zip(result.components, result.explained_variance, strict=True)):
        v = scale * np.sqrt(var) * comp
        ax.annotate(
            "",
            xy=result.mean + v,
            xytext=result.mean,
            arrowprops={"arrowstyle": "-|>", "color": VEC_COLORS[i], "lw": 2.5},
        )
        ax.text(*(result.mean + v * 1.12), f"PC{i + 1}", color=VEC_COLORS[i], fontsize=12)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    return ax


def plot_convergence(histories: dict, ax=None, ylabel: str = "error"):
    """Semilog convergence curves, one per labeled history."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 4.2))
    for label, h in histories.items():
        ax.semilogy(np.asarray(h, dtype=float), label=label)
    ax.set_xlabel("iteration")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    return ax


# ---------------------------------------------------------------------------
# Plotly figures (used mainly in the finance application notebook)
# ---------------------------------------------------------------------------


def plotly_eigen_sweep(A, n_angles: int = 49, title=None):
    """Slider over a unit vector u(theta); shows u and Au, with eigen-lines drawn.

    When Au lines up with u (and with an eigenvector line), theta is an
    eigen-direction. Works in the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    w, V = np.linalg.eig(A)
    thetas = np.linspace(0, np.pi, n_angles)
    # Frame from what is actually drawn: for a non-normal A (a shear, say)
    # ||Au|| can exceed max|lambda|, so sizing the axes from the eigenvalues
    # alone would push the red arrow off-screen.
    us = np.stack([np.cos(thetas), np.sin(thetas)], axis=1)
    swept = np.vstack([us, us @ A.T, -us, -(us @ A.T)])
    x_range, y_range = _square_box(swept, include_origin=True)
    lim = float(x_range[1])

    def eig_lines():
        lines = []
        for i in range(V.shape[1]):
            if np.isreal(w[i]):
                v = np.real(V[:, i])
                v = v / np.linalg.norm(v) * lim
                lines.append(
                    go.Scatter(
                        x=[-v[0], v[0]],
                        y=[-v[1], v[1]],
                        mode="lines",
                        line={"color": "gray", "dash": "dot", "width": 1},
                        name="eigen-line",
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
        return lines

    def frame_data(th):
        u = np.array([np.cos(th), np.sin(th)])
        au = A @ u
        return [
            *eig_lines(),
            go.Scatter(
                x=[0, u[0]],
                y=[0, u[1]],
                mode="lines+markers",
                line={"color": "#1f77b4", "width": 3},
                name="u",
            ),
            go.Scatter(
                x=[0, au[0]],
                y=[0, au[1]],
                mode="lines+markers",
                line={"color": "#d62728", "width": 3},
                name="Au",
            ),
        ]

    frames = [go.Frame(data=frame_data(th), name=f"{np.degrees(th):.0f}") for th in thetas]
    fig = go.Figure(data=frame_data(thetas[0]), frames=frames)
    steps = [
        {
            "args": [
                [f"{np.degrees(th):.0f}"],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": f"{np.degrees(th):.0f}",
            "method": "animate",
        }
        for th in thetas
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "角度（度） = "}}],
        width=560,
        height=560,
        title=title,
        xaxis={"range": x_range, "scaleanchor": "y", "zeroline": True},
        yaxis={"range": y_range, "zeroline": True},
        margin={"l": 30, "r": 30, "t": 50, "b": 30},
    )
    return fig


def plotly_linear_map_morph(
    A, n_steps: int = 21, lim: float = 2.0, title="恒等写像 I から A へ: t を動かして平面を変形"
):
    """Slider over ``t`` in [0, 1] morphing the identity into ``A`` via
    ``M(t) = (1 - t) I + t A``.

    Each frame draws the deformed grid, the image of the unit square (its signed
    area is ``det M(t)`` — the value is shown live in the slider label), and the
    images of the basis vectors ``e1, e2``. This ties the grid-transform picture
    to the determinant inside a single interactive figure: drag ``t`` and watch
    the plane deform while ``det`` changes, flips sign (orientation reversal), or
    hits 0 (the plane collapses). Works in the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    eye = np.eye(2)
    ts = np.linspace(0.0, 1.0, n_steps)
    ticks = np.arange(-lim, lim + 0.25, 0.5)
    t_line = np.linspace(-lim, lim, 21)
    square = np.array([[0, 1, 1, 0, 0], [0, 0, 1, 1, 0]], dtype=float)

    def frame_traces(M):
        traces = []
        for c in ticks:
            for seg in (
                np.vstack([np.full_like(t_line, c), t_line]),
                np.vstack([t_line, np.full_like(t_line, c)]),
            ):
                out = M @ seg
                traces.append(
                    go.Scatter(
                        x=out[0],
                        y=out[1],
                        mode="lines",
                        line={"color": "#c7d6ee", "width": 1},
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
        sq = M @ square
        traces.append(
            go.Scatter(
                x=sq[0],
                y=sq[1],
                fill="toself",
                fillcolor="rgba(214,39,40,0.22)",
                line={"color": "#d62728", "width": 2},
                name="unit square (area = |det|)",
                hoverinfo="skip",
            )
        )
        for col, name, color in ((M[:, 0], "Ae1", "#d62728"), (M[:, 1], "Ae2", "#1f77b4")):
            traces.append(
                go.Scatter(
                    x=[0, col[0]],
                    y=[0, col[1]],
                    mode="lines+markers",
                    line={"color": color, "width": 3},
                    name=name,
                )
            )
        return traces

    mats = [(1 - t) * eye + t * A for t in ts]
    dets = [float(np.linalg.det(M)) for M in mats]
    labels = [f"{t:.2f}  (det={d:+.2f})" for t, d in zip(ts, dets, strict=True)]
    frames = [
        go.Frame(data=frame_traces(M), name=lab) for M, lab in zip(mats, labels, strict=True)
    ]
    fig = go.Figure(data=frame_traces(mats[0]), frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    corners = np.array([[lim, lim, -lim, -lim], [lim, -lim, lim, -lim]])
    span = max(lim, 1.2 * float(np.abs(A @ corners).max()))
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "t = "}}],
        width=560,
        height=560,
        title=title,
        xaxis={"range": [-span, span], "scaleanchor": "y", "zeroline": True},
        yaxis={"range": [-span, span], "zeroline": True},
        margin={"l": 30, "r": 30, "t": 50, "b": 30},
    )
    return fig


def plotly_svd_action(A, n_pts: int = 160, title=None):
    """Slider over the four SVD stages applied to the unit circle:
    circle -> ``V^T`` (rotate) -> ``Sigma`` (stretch) -> ``U`` (rotate) = ``A``.

    Makes "any matrix = rotate, stretch, rotate" steppable: the circle always
    becomes an ellipse whose semi-axis lengths are the singular values. Works in
    the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    U, s, Vt = np.linalg.svd(A)
    th = np.linspace(0, 2 * np.pi, n_pts)
    circ = np.vstack([np.cos(th), np.sin(th)])
    stages = [
        ("① 単位円", circ),
        ("② 回転 Vᵀ", Vt @ circ),
        ("③ 伸縮 Σ", np.diag(s) @ Vt @ circ),
        ("④ 回転 U = A", U @ np.diag(s) @ Vt @ circ),
    ]
    lim = 1.3 * max(1.0, float(s.max()))

    def traces(pts):
        return [
            go.Scatter(
                x=list(pts[0]),
                y=list(pts[1]),
                mode="lines",
                line={"color": "#2ca02c", "width": 2.5},
                name="image",
                hoverinfo="skip",
            )
        ]

    frames = [go.Frame(data=traces(p), name=lab) for lab, p in stages]
    fig = go.Figure(data=traces(stages[0][1]), frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab, _ in stages
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": ""}}],
        width=520,
        height=520,
        title=title or "SVD: 円 → 回転 → 伸縮 → 回転 で楕円になる",
        xaxis={"range": [-lim, lim], "scaleanchor": "y", "zeroline": True},
        yaxis={"range": [-lim, lim], "zeroline": True},
        margin={"l": 30, "r": 30, "t": 50, "b": 30},
    )
    return fig


def plotly_grid_transform(matrices, labels, lim: float = 2.0, title=None):
    """Slider over a list of 2x2 matrices showing the deformed unit grid.

    Each frame draws the image of a square grid under one matrix. Works in the
    static Jupyter Book HTML (the slider is client-side Plotly JS).
    """
    import plotly.graph_objects as go

    ticks = np.arange(-lim, lim + 0.25, 0.5)
    t = np.linspace(-lim, lim, 21)
    mats = [np.asarray(M, dtype=float) for M in matrices]
    # The grid fills the square [-lim, lim]^2, so its image under M is the
    # parallelogram spanned by the mapped corners. Framing on those keeps every
    # matrix in view — a fixed range clipped the strongly shearing ones.
    box_corners = np.array([[lim, lim, -lim, -lim], [lim, -lim, lim, -lim]])
    x_range, y_range = _square_box(
        np.hstack([M @ box_corners for M in mats]).T, include_origin=True
    )

    def grid_traces(A):
        A = np.asarray(A, dtype=float)
        traces = []
        for c in ticks:
            for seg in (np.vstack([np.full_like(t, c), t]), np.vstack([t, np.full_like(t, c)])):
                out = A @ seg
                traces.append(
                    go.Scatter(
                        x=_f(out[0]),
                        y=_f(out[1]),
                        mode="lines",
                        line={"color": "#1f77b4", "width": 1},
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
        return traces

    frames = [
        go.Frame(data=grid_traces(M), name=str(lab)) for M, lab in zip(mats, labels, strict=True)
    ]
    fig = go.Figure(data=grid_traces(mats[0]), frames=frames)
    steps = [
        {
            "args": [[str(lab)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(lab),
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": ""}}],
        width=560,
        height=560,
        title=title,
        xaxis={"range": x_range, "scaleanchor": "y", "zeroline": True},
        yaxis={"range": y_range, "zeroline": True},
        margin={"l": 30, "r": 30, "t": 50, "b": 30},
    )
    return fig


def plotly_curve_slider(x, frames, slider_name: str = "step", title=None, ylim=None):
    """Generic line-plot slider. ``frames`` = list of (label, [(name, y, dash), ...]).

    Mirrors the helper used in the neural_net / bayesian books so the three
    textbooks share one interactive idiom; works in static HTML.
    """
    import plotly.graph_objects as go

    def traces(curves):
        return [
            go.Scatter(
                x=list(x), y=list(y), mode="lines", name=name, line={"dash": dash} if dash else None
            )
            for name, y, dash in curves
        ]

    fig = go.Figure(
        data=traces(frames[0][1]),
        frames=[go.Frame(data=traces(c), name=str(lab)) for lab, c in frames],
    )
    steps = [
        {
            "args": [[str(lab)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(lab),
            "method": "animate",
        }
        for lab, _ in frames
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=720,
        height=450,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 30},
    )
    if ylim is not None:
        fig.update_yaxes(range=list(ylim))
    return fig


def plotly_image_ranks(img, ks):
    """Slider over rank-k SVD approximations of an image (static-HTML safe)."""
    import plotly.graph_objects as go

    from .decompositions import compression_ratio, svd_lowrank

    img = np.asarray(img, dtype=float)
    # 3 decimals is finer than the 256 grey levels a screen can show, and keeps
    # each 128x128 frame from writing ~19 characters per pixel into the .ipynb.
    approx = {k: _f(svd_lowrank(img, k)[::-1], 3) for k in ks}
    frames = [
        go.Frame(data=[go.Heatmap(z=approx[k], colorscale="gray", showscale=False)], name=str(k))
        for k in ks
    ]
    fig = go.Figure(
        data=[go.Heatmap(z=approx[ks[0]], colorscale="gray", showscale=False)], frames=frames
    )
    steps = [
        {
            "args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": f"{k} ({compression_ratio(img.shape, k):.0%})",
            "method": "animate",
        }
        for k in ks
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "ランク = "}}],
        width=460,
        height=500,
        title="低ランク近似（ランク k を動かす）",
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def plotly_svd_spectrum(A, max_k=None, title="Singular value spectrum & cumulative energy"):
    """Energy share per singular value + cumulative energy, with a rank slider.

    Complements :func:`plotly_image_ranks`: that one shows *what* a rank-k
    approximation looks like, this one shows *why* a small k often suffices by
    highlighting how quickly the cumulative energy reaches 1. Slider sweeps k.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    s = np.linalg.svd(A, compute_uv=False)
    r = len(s) if max_k is None else min(max_k, len(s))
    s = s[:r]
    energy = s**2
    share = energy / energy.sum()
    cum = np.cumsum(share)
    idx = np.arange(1, r + 1)
    # Real spectra decay fast (an image puts ~89% in sigma_1), so on a linear
    # axis every bar past the third is a flat line at zero — exactly the part
    # the figure is meant to show. Log scale keeps the whole tail readable.
    positive = share[share > 0]
    floor = max(float(positive.min()) if positive.size else 1e-12, float(share.max()) * 1e-6)
    # One frame per rank is wasteful for a 128-column matrix; sample the slider.
    ks = idx if r <= 24 else np.unique(np.linspace(1, r, 24).astype(int))

    def moving_traces(k):
        """Only these change with k, so only these travel in each frame."""
        return [
            go.Bar(
                x=[int(i) for i in idx],
                # Not rounded: shares reach 1e-9 and the log axis needs them.
                y=list(share),
                marker={"color": ["#d62728" if i < k else "#c7c7c7" for i in range(r)]},
                name="エネルギー比",
                showlegend=False,
            ),
            go.Scatter(
                x=[int(k)],
                y=[float(cum[k - 1])],
                mode="markers+text",
                marker={"color": "#1f77b4", "size": 12, "symbol": "circle-open"},
                text=[f"{cum[k - 1]:.0%}"],
                textposition="top center",
                showlegend=False,
                yaxis="y2",
            ),
        ]

    cumulative = go.Scatter(
        x=[int(i) for i in idx],
        y=_f(cum, 6),
        mode="lines",
        name="累積エネルギー",
        line={"color": "#1f77b4"},
        yaxis="y2",
    )
    first = moving_traces(int(ks[0]))
    fig = go.Figure(
        data=[first[0], cumulative, first[1]],
        frames=[
            # traces=[0, 2] pins the static cumulative curve in place instead of
            # re-sending it with every frame.
            go.Frame(data=moving_traces(int(k)), traces=[0, 2], name=str(int(k)))
            for k in ks
        ],
    )
    steps = [
        {
            "args": [
                [str(int(k))],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": str(int(k)),
            "method": "animate",
        }
        for k in ks
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "ランク k = "}}],
        width=720,
        height=450,
        title=title,
        xaxis={"title": "特異値の番号"},
        yaxis={
            "title": "エネルギー比（対数）",
            "type": "log",
            "range": [float(np.log10(floor * 0.5)), float(np.log10(1.5))],
        },
        yaxis2={
            "title": "累積エネルギー",
            "overlaying": "y",
            "side": "right",
            "range": [0, 1.02],
        },
        margin={"l": 60, "r": 60, "t": 50, "b": 40},
        bargap=0.15,
    )
    return fig


def plotly_yield_curves(maturities, curves, every: int = 25):
    """Sampled yield curves colored from oldest (light) to newest (dark)."""
    import plotly.graph_objects as go

    curves = np.asarray(curves, dtype=float)
    idx = np.arange(0, len(curves), every)
    fig = go.Figure()
    for j, i in enumerate(idx):
        shade = 0.15 + 0.85 * j / max(1, len(idx) - 1)
        fig.add_trace(
            go.Scatter(
                x=list(maturities),
                y=curves[i],
                mode="lines",
                line={"color": f"rgba(31, 119, 180, {shade:.2f})", "width": 1.5},
                name=f"day {i}",
                showlegend=False,
            )
        )
    fig.update_layout(
        xaxis_title="満期（年）",
        yaxis_title="利回り（%）",
        width=720,
        height=420,
        margin={"l": 60, "r": 20, "t": 30, "b": 50},
    )
    return fig


def plotly_pca_loadings(
    maturities, components, names=("PC1 (Level)", "PC2 (Slope)", "PC3 (Curvature)")
):
    """Loadings of the first principal components across maturities."""
    import plotly.graph_objects as go

    fig = go.Figure()
    for comp, name in zip(np.asarray(components, dtype=float), names, strict=False):
        fig.add_trace(go.Scatter(x=list(maturities), y=comp, mode="lines+markers", name=name))
    fig.add_hline(y=0, line={"color": "gray", "width": 1})
    fig.update_layout(
        xaxis_title="満期（年）",
        yaxis_title="ローディング",
        width=720,
        height=420,
        margin={"l": 60, "r": 20, "t": 30, "b": 50},
    )
    return fig


def plotly_iterative_convergence(
    A=None,
    b=None,
    n_iter: int = 40,
    title="Iterative solvers: residual vs iteration",
    precondition: bool = False,
):
    """Residual norm per iteration for Jacobi / Gauss-Seidel / Conjugate Gradient.

    Reuses :func:`algebra.jacobi`, :func:`algebra.gauss_seidel`,
    :func:`algebra.conjugate_gradient`. Default system is the 1-D Laplacian
    (SPD), where CG converges in far fewer steps than the splitting methods.

    With ``precondition=True`` the default system is instead a *badly scaled*
    SPD matrix (row scales spanning four orders of magnitude) and a fourth curve
    shows Jacobi-preconditioned CG. That is the ch.09 story — preconditioning,
    not the solver, is what buys the iterations — so the appendix gets its own
    figure rather than repeating the ch.06 one.
    """
    import plotly.graph_objects as go

    from .algebra import conjugate_gradient, gauss_seidel, jacobi

    if A is None:
        n = 20
        lap = 2 * np.eye(n) - np.eye(n, k=1) - np.eye(n, k=-1)
        if precondition:
            # D^(1/2) L D^(1/2): same sparsity, wildly uneven diagonal, so the
            # trivial diagonal preconditioner has something real to fix.
            scale = np.logspace(0.0, 2.0, n)
            A = (scale[:, None] * lap) * scale[None, :]
        else:
            A = lap
    A = np.asarray(A, dtype=float)
    b = np.ones(A.shape[0]) if b is None else np.asarray(b, dtype=float)
    _, rj = jacobi(A, b, n_iter=n_iter, return_history=True)
    _, rg = gauss_seidel(A, b, n_iter=n_iter, return_history=True)
    _, rc = conjugate_gradient(A, b, max_iter=n_iter)
    curves = [("Jacobi", rj), ("Gauss-Seidel", rg), ("Conjugate Gradient", rc)]
    if precondition:
        d = np.diag(A)
        _, rp = conjugate_gradient(A, b, max_iter=n_iter, M_inv=lambda v, d=d: v / d)
        curves.append(("CG + Jacobi preconditioner", rp))
    fig = go.Figure()
    for name, res in curves:
        res = np.clip(np.asarray(res, dtype=float), 1e-16, None)
        fig.add_trace(
            # Not rounded: residuals span many decades and need relative, not
            # absolute, precision to stay meaningful on a log axis.
            go.Scatter(x=list(range(len(res))), y=list(res), mode="lines+markers", name=name)
        )
    fig.update_layout(
        xaxis_title="反復回数",
        yaxis_title="残差ノルム",
        width=720,
        height=440,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(type="log")
    return fig


def plotly_pagerank(names=None, adj=None, damping: float = 0.85, title="PageRank power iteration"):
    """Bar chart of PageRank scores converging over power iterations (slider).

    Reuses :func:`algebra.page_rank` (with history) and the default web graph
    from :func:`datasets.make_web_graph`.
    """
    import plotly.graph_objects as go

    from .algebra import page_rank
    from .datasets import make_web_graph

    if adj is None:
        names, adj = make_web_graph()
    _r, hist = page_rank(np.asarray(adj, dtype=float), damping=damping, return_history=True)
    if len(hist) > 26:  # keep the slider light
        idx = np.unique(np.linspace(0, len(hist) - 1, 26).astype(int))
        hist = hist[idx]
        labels = [str(int(i)) for i in idx]
    else:
        labels = [str(i) for i in range(len(hist))]
    frames = [
        go.Frame(data=[go.Bar(x=list(names), y=list(hist[t]))], name=labels[t])
        for t in range(len(hist))
    ]
    fig = go.Figure(data=[go.Bar(x=list(names), y=list(hist[0]))], frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "反復 = "}}],
        xaxis_title="ページ",
        yaxis_title="PageRank",
        width=680,
        height=440,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(range=[0, float(hist.max()) * 1.1])
    return fig


def plotly_gradient_descent_quadratic(
    A=None,
    b=None,
    lr: float | None = None,
    n_iter: int = 30,
    x0=(-1.5, 2.5),
    title="Gradient descent on a quadratic bowl",
):
    """Contour of f(x) = 0.5 xᵀA x − bᵀx with the GD path revealed by a slider.

    Reuses :func:`algebra.gradient_descent_quadratic`. The default is the same
    ill-conditioned bowl as the static figure in ch.06 (kappa = 30, step
    1.9 / lambda_max) so that the promised zig-zag actually happens: a mild bowl
    with a small step gives a smooth monotone curve and quietly contradicts the
    surrounding text. ``lr=None`` picks 1.9 / lambda_max for whatever ``A`` is
    passed, keeping any custom bowl just inside the stability limit 2 / lambda_max.
    """
    import plotly.graph_objects as go

    from .algebra import gradient_descent_quadratic

    if A is None:
        A = np.array([[30.0, 0.0], [0.0, 1.0]])
        if b is None:
            b = np.array([30.0, 1.0])  # minimum at (1, 1)
    A = np.asarray(A, dtype=float)
    b = np.zeros(A.shape[0]) if b is None else np.asarray(b, dtype=float)
    if lr is None:
        lr = 1.9 / float(np.linalg.eigvalsh(0.5 * (A + A.T)).max())
    path = gradient_descent_quadratic(A, b, lr=lr, n_iter=n_iter, x0=np.array(x0, dtype=float))
    x_range, y_range = _square_box(
        np.vstack([path, np.linalg.solve(A, b)[None, :]]), pad=0.18
    )
    gx = np.linspace(x_range[0], x_range[1], 70)
    gy = np.linspace(y_range[0], y_range[1], 70)
    XX, YY = np.meshgrid(gx, gy)
    Z = 0.5 * (A[0, 0] * XX**2 + (A[0, 1] + A[1, 0]) * XX * YY + A[1, 1] * YY**2) - (
        b[0] * XX + b[1] * YY
    )

    def path_trace(k):
        return go.Scatter(
            x=_f(path[: k + 1, 0]),
            y=_f(path[: k + 1, 1]),
            mode="lines+markers",
            line={"color": "#d62728"},
            name="GD path",
        )

    contour = go.Contour(
        x=_f(gx),
        y=_f(gy),
        z=_f(Z, 3),
        showscale=False,
        contours_coloring="lines",
        line_width=1,
        colorscale="Greys",
        hoverinfo="skip",
    )
    # The contour never changes; re-sending it in all 31 frames used to make this
    # single figure ~2.8 MB inside the notebook. traces=[1] updates only the path.
    frames = [
        go.Frame(data=[path_trace(k)], traces=[1], name=str(k)) for k in range(len(path))
    ]
    fig = go.Figure(data=[contour, path_trace(0)], frames=frames)
    steps = [
        {
            "args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(k),
            "method": "animate",
        }
        for k in range(len(path))
    ]
    fig.add_trace(
        go.Scatter(
            x=_f([np.linalg.solve(A, b)[0]]),
            y=_f([np.linalg.solve(A, b)[1]]),
            mode="markers",
            marker={"color": "#2ca02c", "size": 14, "symbol": "star"},
            name="minimum",
        )
    )
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "ステップ = "}}],
        xaxis_title="x1",
        yaxis_title="x2",
        width=560,
        height=540,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
        xaxis={"range": x_range},
        yaxis={"range": y_range},
    )
    fig.update_yaxes(scaleanchor="x")
    return fig


def _line_xy(coef, rhs, span):
    """Sample a line ``coef . (x, y) = rhs`` across a square box of half-width
    ``span`` (handles vertical/horizontal lines uniformly)."""
    coef = np.asarray(coef, dtype=float)
    n2 = coef @ coef
    foot = coef * rhs / n2  # closest point to the origin on the line
    direction = np.array([-coef[1], coef[0]]) / np.sqrt(n2)  # along the line
    s = np.linspace(-3 * span, 3 * span, 2)
    pts = foot[:, None] + direction[:, None] * s
    return pts[0], pts[1]


def plotly_two_line_system(A=None, b=None, n_steps: int = 21, span: float = 4.0, title=None):
    """Row picture of a 2x2 system, with a slider that morphs equation 2 toward
    being parallel to equation 1.

    As ``t`` goes 0 -> 1, row 2 turns into a multiple of row 1: the determinant
    shrinks to 0, the two lines become parallel, and the unique intersection
    (the solution) shoots off to infinity and disappears. This makes "rank
    deficiency = lost/blown-up solution" something you watch happen. Works in
    the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.array([[1.0, 1.0], [1.0, -1.0]] if A is None else A, dtype=float)
    b = np.array([3.0, 1.0] if b is None else b, dtype=float)
    row1, row2_0 = A[0], A[1]
    row2_par = 1.5 * row1  # the parallel target for row 2
    ts = np.linspace(0.0, 1.0, n_steps)

    def traces(t):
        row2 = (1 - t) * row2_0 + t * row2_par
        out = [
            go.Scatter(
                x=list(_line_xy(row1, b[0], span)[0]),
                y=list(_line_xy(row1, b[0], span)[1]),
                mode="lines",
                line={"color": "#1f77b4", "width": 3},
                name="equation 1",
            ),
            go.Scatter(
                x=list(_line_xy(row2, b[1], span)[0]),
                y=list(_line_xy(row2, b[1], span)[1]),
                mode="lines",
                line={"color": "#ff7f0e", "width": 3},
                name="equation 2",
            ),
        ]
        det = row1[0] * row2[1] - row1[1] * row2[0]
        if abs(det) > 1e-3:
            sol = np.linalg.solve(np.vstack([row1, row2]), b)
            if np.abs(sol).max() <= span:
                out.append(
                    go.Scatter(
                        x=[sol[0]],
                        y=[sol[1]],
                        mode="markers",
                        marker={"color": "#d62728", "size": 13},
                        name="solution",
                    )
                )
        return out

    dets = [row1[0] * ((1 - t) * row2_0 + t * row2_par)[1]
            - row1[1] * ((1 - t) * row2_0 + t * row2_par)[0] for t in ts]
    labels = [f"{t:.2f}  (det={d:+.2f})" for t, d in zip(ts, dets, strict=True)]
    frames = [go.Frame(data=traces(t), name=lab) for t, lab in zip(ts, labels, strict=True)]
    fig = go.Figure(data=traces(0.0), frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "t = "}}],
        width=560,
        height=560,
        title=title or "二直線の交点 = 連立解（t→1 で平行になり解が消える）",
        xaxis={"range": [-span, span], "scaleanchor": "y", "zeroline": True},
        yaxis={"range": [-span, span], "zeroline": True},
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )
    return fig


def plotly_projection_sweep(a=(2.0, 1.0), r: float = 2.2, n_angles: int = 37, title=None):
    """Slider sweeping a vector ``b`` around a circle; shows its orthogonal
    projection onto the fixed line ``span{a}`` and the residual.

    The slider label reports the inner product ``a . b`` (max when b aligns with
    a, zero when orthogonal, negative when opposed) so the algebra and the
    picture move together. Works in the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    a = np.asarray(a, dtype=float)
    na = a / np.linalg.norm(a)
    lim = 1.4 * max(r, np.linalg.norm(a))
    thetas = np.linspace(0, 2 * np.pi, n_angles)

    def traces(th):
        b = r * np.array([np.cos(th), np.sin(th)])
        p = (a @ b) / (a @ a) * a
        return [
            go.Scatter(
                x=[-lim * na[0], lim * na[0]],
                y=[-lim * na[1], lim * na[1]],
                mode="lines",
                line={"color": "gray", "width": 1},
                name="span{a}",
                hoverinfo="skip",
            ),
            go.Scatter(x=[0, b[0]], y=[0, b[1]], mode="lines+markers",
                       line={"color": "#1f77b4", "width": 3}, name="b"),
            go.Scatter(x=[0, p[0]], y=[0, p[1]], mode="lines+markers",
                       line={"color": "#d62728", "width": 3}, name="proj"),
            go.Scatter(x=[b[0], p[0]], y=[b[1], p[1]], mode="lines",
                       line={"color": "black", "width": 1.5, "dash": "dash"},
                       name="residual", hoverinfo="skip"),
        ]

    dots = [float(a @ (r * np.array([np.cos(th), np.sin(th)]))) for th in thetas]
    labels = [f"{np.degrees(th):.0f}°  (a·b={d:+.2f})" for th, d in zip(thetas, dots, strict=True)]
    frames = [go.Frame(data=traces(th), name=lab) for th, lab in zip(thetas, labels, strict=True)]
    fig = go.Figure(data=traces(thetas[0]), frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "角度 = "}}],
        width=560,
        height=560,
        title=title or "b を回すと影（射影）と残差が動く",
        xaxis={"range": [-lim, lim], "scaleanchor": "y", "zeroline": True},
        yaxis={"range": [-lim, lim], "zeroline": True},
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )
    return fig


def plotly_poly_fit_degree(x, y, degrees=range(1, 13), title=None):
    """Slider over polynomial degree fitting fixed (x, y) data.

    Low degree underfits; very high degree overfits (the curve wiggles to chase
    noise) even as the training RMSE keeps dropping — the slider label shows
    that RMSE so the trade-off is explicit. Works in the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xs = np.linspace(x.min(), x.max(), 200)
    degrees = list(degrees)
    pad = 0.5 * (y.max() - y.min())
    ylim = [y.min() - pad, y.max() + pad]

    def traces(d):
        coeffs = np.polyfit(x, y, d)
        rmse = float(np.sqrt(np.mean((np.polyval(coeffs, x) - y) ** 2)))
        return rmse, [
            go.Scatter(x=list(x), y=list(y), mode="markers",
                       marker={"color": "#1f77b4", "size": 8}, name="data"),
            go.Scatter(x=list(xs), y=list(np.polyval(coeffs, xs)), mode="lines",
                       line={"color": "#d62728", "width": 2}, name=f"degree {d} fit"),
        ]

    info = [traces(d) for d in degrees]
    labels = [f"degree {d}  (RMSE={rmse:.3f})" for d, (rmse, _) in zip(degrees, info, strict=True)]
    frames = [go.Frame(data=tr, name=lab) for (_, tr), lab in zip(info, labels, strict=True)]
    fig = go.Figure(data=info[0][1], frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": ""}}],
        width=720,
        height=460,
        title=title or "多項式の次数を上げる：当てはまり vs 過学習",
        xaxis={"title": "x"},
        yaxis={"title": "y", "range": ylim},
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_complex_orbit(A, x0=(1.0, 0.0), n_steps: int = 24, title=None):
    """Slider revealing the orbit ``x, Ax, A^2 x, ...`` of a 2x2 matrix.

    When ``A`` has complex eigenvalues ``r e^{i theta}``, the orbit spirals:
    ``theta`` sets the rotation per step and ``r`` sets growth (r>1), decay
    (r<1), or a closed circle (r=1). This turns "complex eigenvalue = rotation +
    scaling" into a picture you can step through. Works in static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    pts = [np.asarray(x0, dtype=float)]
    for _ in range(n_steps):
        pts.append(A @ pts[-1])
    pts = np.array(pts)
    # Frame the orbit itself. Orbits that converge to a fixed point far from the
    # origin (the 03 migration example lives around (67, 33)) would otherwise sit
    # in one corner of a huge origin-centred square.
    x_range, y_range = _square_box(pts, pad=0.15)

    def traces(k):
        return [
            go.Scatter(x=_f(pts[: k + 1, 0]), y=_f(pts[: k + 1, 1]),
                       mode="lines+markers", line={"color": "#1f77b4", "width": 1.5},
                       marker={"size": 5}, name="orbit"),
            go.Scatter(x=_f([pts[k, 0]]), y=_f([pts[k, 1]]), mode="markers",
                       marker={"color": "#d62728", "size": 12}, name=f"x_{k}"),
        ]

    frames = [go.Frame(data=traces(k), name=str(k)) for k in range(len(pts))]
    fig = go.Figure(data=traces(0), frames=frames)
    steps = [
        {
            "args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(k),
            "method": "animate",
        }
        for k in range(len(pts))
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "ステップ k = "}}],
        width=560,
        height=560,
        title=title or "軌道 x, Ax, A²x, … （複素固有値なら螺旋）",
        xaxis={"range": x_range, "scaleanchor": "y", "zeroline": True},
        yaxis={"range": y_range, "zeroline": True},
        margin={"l": 40, "r": 20, "t": 50, "b": 30},
    )
    return fig


def plotly_kron_blocks(A, B, title=None):
    """Heatmap of the Kronecker product ``A (x) B`` with a slider that highlights
    one block at a time.

    ``A (x) B`` replaces each entry ``a_ij`` with the block ``a_ij * B``; the
    slider walks the entries of ``A`` and outlines the matching block, so the
    "matrix of matrices" structure is visible. Works in static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    K = np.kron(A, B)
    p, q = A.shape
    r, s = B.shape

    def rect(i, j):
        x0, x1 = j * s - 0.5, (j + 1) * s - 0.5
        y0, y1 = i * r - 0.5, (i + 1) * r - 0.5
        return (
            go.Heatmap(z=K, colorscale="RdBu", zmid=0, showscale=True),
            go.Scatter(
                x=[x0, x1, x1, x0, x0],
                y=[y0, y0, y1, y1, y0],
                mode="lines",
                line={"color": "#000000", "width": 3},
                name="block",
                hoverinfo="skip",
            ),
        )

    cells = [(i, j) for i in range(p) for j in range(q)]
    labels = [f"a[{i},{j}] = {A[i, j]:+.1f}" for i, j in cells]
    frames = [go.Frame(data=rect(i, j), name=lab) for (i, j), lab in zip(cells, labels, strict=True)]
    fig = go.Figure(data=rect(*cells[0]), frames=frames)
    steps = [
        {
            "args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": lab,
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "ブロック "}}],
        width=560,
        height=520,
        title=title or "クロネッカー積 A⊗B：各ブロックは a_ij·B",
        xaxis={"visible": False},
        yaxis={"visible": False, "autorange": "reversed", "scaleanchor": "x"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


# ---------------------------------------------------------------------------
# Interactive 3-D and graph figures
#
# The pictures in this section are the ones that a static image cannot carry:
# a cloud collapsing onto a plane reads as "a cloud" until you rotate it, and a
# network's community structure is invisible in an adjacency heatmap.
# ---------------------------------------------------------------------------


def _slider_steps(labels, prefix=""):
    """Plotly slider steps for a list of frame names."""
    return [
        {
            "args": [[str(lab)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(lab),
            "method": "animate",
        }
        for lab in labels
    ]


def plotly_rank_collapse_3d(cloud, matrices, labels, title=None):
    """Slider over matrices of decreasing rank, applied to a 3-D point cloud.

    Rank loss is the moment information dies, and in 3-D that is literally
    visible: the cloud goes from a blob to a pancake to a needle. A static
    projection hides it (a flat cloud seen edge-on still looks like a cloud), so
    this one is worth rotating with the mouse. Alongside the points, the axes of
    ``Im(A)`` are drawn — count them and you have read the rank off the picture.
    """
    import plotly.graph_objects as go

    cloud = np.asarray(cloud, dtype=float)
    mats = [np.asarray(M, dtype=float) for M in matrices]
    images = [cloud @ M.T for M in mats]
    lim = 1.15 * float(max(np.abs(im).max() for im in images))

    def basis_trace(M, scale):
        """Line segments through the origin along an orthonormal basis of Im(M)."""
        U, s, _ = np.linalg.svd(M)
        r = int((s > 1e-9 * max(s[0], 1e-30)).sum())
        xs, ys, zs = [], [], []
        for i in range(r):
            u = U[:, i] * scale
            xs += [-u[0], u[0], None]
            ys += [-u[1], u[1], None]
            zs += [-u[2], u[2], None]
        return go.Scatter3d(
            x=xs, y=ys, z=zs, mode="lines",
            line={"color": "#d62728", "width": 6},
            name=f"Im(A) の軸 ({r} 本)",
        )

    def traces(M, im):
        return [
            go.Scatter3d(
                x=_f(im[:, 0], 3), y=_f(im[:, 1], 3), z=_f(im[:, 2], 3),
                mode="markers",
                marker={"size": 2.5, "color": "#1f77b4", "opacity": 0.55},
                name="変換後の点群",
            ),
            basis_trace(M, 0.9 * lim),
        ]

    frames = [
        go.Frame(data=traces(M, im), name=str(lab))
        for M, im, lab in zip(mats, images, labels, strict=True)
    ]
    fig = go.Figure(data=traces(mats[0], images[0]), frames=frames)
    axis = {"range": [-lim, lim], "zeroline": True, "showbackground": True}
    fig.update_layout(
        sliders=[{"steps": _slider_steps(labels), "currentvalue": {"prefix": ""}}],
        width=640,
        height=600,
        title=title or "ランクが落ちると点群がつぶれる（ドラッグで回せます）",
        scene={
            "xaxis": {**axis, "title": "x"},
            "yaxis": {**axis, "title": "y"},
            "zaxis": {**axis, "title": "z"},
            # A cube keeps a flattened cloud from being stretched back out by
            # autoscaling, which would hide the very thing being shown.
            "aspectmode": "cube",
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
    )
    return fig


def plotly_least_squares_3d(A=None, b=None, n_steps: int = 25, title=None):
    """The least-squares picture in 3-D: a plane, a point off it, and the foot.

    Slide ``t`` to walk a candidate point along ``col(A)``. The dashed segment to
    ``b`` is what least squares minimises, and its length (shown in the slider
    label) bottoms out exactly where the segment meets the plane at a right
    angle. That is the whole content of the normal equations, as a picture.
    """
    import plotly.graph_objects as go

    A = np.array([[1.0, 0.0], [0.6, 1.0], [0.0, 0.4]] if A is None else A, dtype=float)
    b = np.array([0.6, 0.4, 1.6] if b is None else b, dtype=float)
    a1, a2 = A[:, 0], A[:, 1]
    x_hat = np.linalg.solve(A.T @ A, A.T @ b)
    p = A @ x_hat
    # Walk along the plane through p, in the direction of col(A) that is most
    # spread out, so the sweep visibly passes through the foot.
    q_dir = a1 / np.linalg.norm(a1)
    ts = np.linspace(-1.4, 1.4, n_steps)
    pts = np.array([p + t * q_dir for t in ts])
    span = 1.25 * float(np.abs(np.vstack([pts, b[None, :], p[None, :], A.T])).max())

    grid = np.linspace(-1.6, 1.6, 12)
    S, T = np.meshgrid(grid, grid)
    plane = S[..., None] * a1 + T[..., None] * a2

    static = [
        go.Surface(
            x=_f(plane[..., 0], 3), y=_f(plane[..., 1], 3), z=_f(plane[..., 2], 3),
            showscale=False, opacity=0.32, colorscale=[[0, "#9ecae1"], [1, "#9ecae1"]],
            name="col(A)", hoverinfo="skip",
        ),
        go.Scatter3d(
            x=[0, b[0]], y=[0, b[1]], z=[0, b[2]], mode="lines+markers",
            line={"color": "#1f77b4", "width": 6}, marker={"size": 4}, name="b",
        ),
        go.Scatter3d(
            x=[0, p[0]], y=[0, p[1]], z=[0, p[2]], mode="lines+markers",
            line={"color": "#d62728", "width": 6}, marker={"size": 4},
            name="p = 正射影（最小点）",
        ),
        go.Scatter3d(
            x=[b[0], p[0]], y=[b[1], p[1]], z=[b[2], p[2]], mode="lines",
            line={"color": "#d62728", "width": 3, "dash": "dash"},
            name="残差 r = b - p", hoverinfo="skip",
        ),
    ]

    def moving(q):
        return [
            go.Scatter3d(
                x=[q[0]], y=[q[1]], z=[q[2]], mode="markers",
                marker={"size": 7, "color": "#2ca02c"}, name="平面上の候補点 q",
            ),
            go.Scatter3d(
                x=[b[0], q[0]], y=[b[1], q[1]], z=[b[2], q[2]], mode="lines",
                line={"color": "#2ca02c", "width": 4}, name="‖b - q‖", hoverinfo="skip",
            ),
        ]

    labels = [f"t={t:+.2f}  (‖b-q‖={np.linalg.norm(b - q):.3f})" for t, q in zip(ts, pts, strict=True)]
    n_static = len(static)
    frames = [
        go.Frame(data=moving(q), traces=[n_static, n_static + 1], name=lab)
        for q, lab in zip(pts, labels, strict=True)
    ]
    fig = go.Figure(data=[*static, *moving(pts[0])], frames=frames)
    axis = {"range": [-span, span], "zeroline": True}
    fig.update_layout(
        sliders=[{"steps": _slider_steps(labels), "currentvalue": {"prefix": ""}}],
        width=680,
        height=620,
        title=title or "最小二乗＝col(A) の中で b に一番近い点（ドラッグで回せます）",
        scene={
            "xaxis": {**axis, "title": "x"},
            "yaxis": {**axis, "title": "y"},
            "zaxis": {**axis, "title": "z"},
            "aspectmode": "cube",
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
    )
    return fig


def _spring_layout(adj, seed: int = 0, iterations: int = 300):
    """Deterministic Fruchterman-Reingold layout (no networkx dependency)."""
    A = np.asarray(adj, dtype=float)
    A = ((A + A.T) > 0).astype(float)
    np.fill_diagonal(A, 0.0)  # self-loops would pull a node against itself
    n = A.shape[0]
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-1.0, 1.0, (n, 2))
    k = 1.0 / np.sqrt(n)
    temp = 0.15
    for _ in range(iterations):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(delta, axis=-1)
        # A large finite diagonal keeps self-pairs inert without inf * 0 = nan.
        np.fill_diagonal(dist, 1e9)
        repel = (k**2 / dist**2)[..., None] * delta
        attract = (dist / k)[..., None] * delta * A[..., None]
        disp = (repel - attract).sum(axis=1)
        norm = np.linalg.norm(disp, axis=1, keepdims=True)
        pos = pos + disp / np.maximum(norm, 1e-12) * np.minimum(norm, temp)
        temp *= 0.99
    pos = pos - pos.mean(axis=0)
    return pos / max(float(np.abs(pos).max()), 1e-12)


def plotly_graph(
    adj,
    names=None,
    pos=None,
    node_value=None,
    node_color=None,
    directed: bool = False,
    title=None,
    value_name: str = "value",
    colorbar_title=None,
    seed: int = 0,
):
    """Draw the graph itself — nodes and edges, not an adjacency heatmap.

    Chapter 07 computes PageRank and a Fiedler split but only ever shows bar
    charts and matrix images, where the structure being discussed is invisible.
    ``node_value`` scales the markers (PageRank) and ``node_color`` colours them
    (Fiedler sign), so the eigenvector is read off the network directly.
    """
    import plotly.graph_objects as go

    A = np.asarray(adj, dtype=float)
    n = A.shape[0]
    names = [str(i) for i in range(n)] if names is None else list(names)
    pos = _spring_layout(A, seed=seed) if pos is None else np.asarray(pos, dtype=float)

    edges = [(i, j) for i in range(n) for j in range(n) if A[i, j] and (directed or i < j)]
    ex, ey = [], []
    for i, j in edges:
        ex += [pos[i, 0], pos[j, 0], None]
        ey += [pos[i, 1], pos[j, 1], None]

    if node_value is None:
        sizes = np.full(n, 18.0)
    else:
        v = np.asarray(node_value, dtype=float)
        sizes = 14.0 + 46.0 * (v - v.min()) / max(float(v.max() - v.min()), 1e-12)

    marker = {"size": sizes, "line": {"color": "#333333", "width": 1}}
    if node_color is None:
        marker["color"] = "#1f77b4"
    else:
        marker.update(
            color=list(np.asarray(node_color, dtype=float)),
            colorscale="RdBu",
            cmid=0.0,
            showscale=True,
            colorbar={"title": colorbar_title or "", "thickness": 14},
        )

    hover = (
        [f"{nm}" for nm in names]
        if node_value is None
        else [f"{nm}<br>{value_name} = {v:.3f}" for nm, v in zip(names, node_value, strict=True)]
    )
    fig = go.Figure(
        [
            go.Scatter(
                x=[None if v is None else round(float(v), 4) for v in ex],
                y=[None if v is None else round(float(v), 4) for v in ey],
                mode="lines",
                line={"color": "rgba(120,120,120,0.55)", "width": 1.4},
                hoverinfo="skip",
                showlegend=False,
                name="edges",
            ),
            go.Scatter(
                x=_f(pos[:, 0]),
                y=_f(pos[:, 1]),
                mode="markers+text",
                marker=marker,
                text=names,
                textposition="middle center",
                textfont={"size": 10, "color": "#ffffff"},
                hovertext=hover,
                hoverinfo="text",
                showlegend=False,
                name="nodes",
            ),
        ]
    )
    if directed:
        # Arrowheads carry the link direction, which PageRank depends on.
        fig.update_layout(
            annotations=[
                {
                    "x": pos[j, 0], "y": pos[j, 1], "ax": pos[i, 0], "ay": pos[i, 1],
                    "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
                    "showarrow": True, "arrowhead": 3, "arrowsize": 1.1,
                    "arrowwidth": 1.2, "arrowcolor": "rgba(120,120,120,0.85)",
                    "standoff": 14, "startstandoff": 12, "text": "",
                }
                for i, j in edges
            ]
        )
    fig.update_layout(
        width=620,
        height=560,
        title=title,
        xaxis={"visible": False, "range": [-1.25, 1.25], "scaleanchor": "y"},
        yaxis={"visible": False, "range": [-1.25, 1.25]},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        plot_bgcolor="white",
    )
    return fig


def _rref_step_label(step, n_cols_aug: int | None = None) -> str:
    """Japanese description of one recorded row operation."""
    kind = step["kind"]
    if kind == "swap":
        i, j = step["rows"]
        return f"行 {i + 1} ↔ 行 {j + 1} を入れ替え"
    if kind == "scale":
        return f"行 {step['row'] + 1} を {step['factor']:.3g} 倍"
    return f"行 {step['target'] + 1} に 行 {step['source'] + 1} の {step['factor']:.3g} 倍を加える"


def plotly_rref_steps(Ab, augmented: bool = True, title=None):
    """Replay Gauss-Jordan elimination one row operation at a time.

    The chapter defines elimination as a *procedure* — three row operations,
    applied until the matrix is in reduced row echelon form — and then only ever
    prints the final answer. This steps through the actual operations, showing
    the matrix after each one and naming the operation in the slider label. The
    pivot being worked on is outlined; the augmented column is separated by a
    dashed rule.
    """
    import plotly.graph_objects as go

    from .algebra import rref_steps

    M0 = np.asarray(Ab, dtype=float)
    _R, _piv, steps = rref_steps(M0)
    n_rows, n_cols = M0.shape
    states = [{"matrix": M0.copy(), "label": "開始（拡大係数行列）", "pivot": None}]
    for s in steps:
        states.append({"matrix": s["matrix"], "label": _rref_step_label(s), "pivot": s["pivot"]})

    scale = float(np.abs(M0).max()) or 1.0

    def heat(M):
        # Rows are drawn top-down, so flip for the heatmap's bottom-up y axis.
        z = M[::-1]
        return go.Heatmap(
            z=_f(z, 4),
            text=[[f"{v:g}" for v in row] for row in np.round(z, 4)],
            texttemplate="%{text}",
            textfont={"size": 14},
            colorscale="RdBu",
            zmid=0.0,
            zmin=-scale,
            zmax=scale,
            showscale=False,
            hoverinfo="skip",
        )

    def pivot_box(pivot):
        if pivot is None:
            return go.Scatter(x=[], y=[], mode="lines", showlegend=False, hoverinfo="skip")
        r, c = pivot
        y = n_rows - 1 - r
        return go.Scatter(
            x=[c - 0.5, c + 0.5, c + 0.5, c - 0.5, c - 0.5],
            y=[y - 0.5, y - 0.5, y + 0.5, y + 0.5, y - 0.5],
            mode="lines",
            line={"color": "#2ca02c", "width": 4},
            name="pivot",
            showlegend=False,
            hoverinfo="skip",
        )

    labels = [f"{i}. {st['label']}" for i, st in enumerate(states)]
    frames = [
        go.Frame(data=[heat(st["matrix"]), pivot_box(st["pivot"])], name=lab)
        for st, lab in zip(states, labels, strict=True)
    ]
    fig = go.Figure(data=[heat(states[0]["matrix"]), pivot_box(None)], frames=frames)
    if augmented and n_cols >= 2:
        fig.add_vline(x=n_cols - 1.5, line={"color": "#333333", "width": 2, "dash": "dash"})
    fig.update_layout(
        sliders=[{"steps": _slider_steps(labels), "currentvalue": {"prefix": "手順 "}}],
        width=680,
        height=420,
        title=title or "掃き出し法：行基本変形を 1 手ずつ",
        xaxis={"visible": False, "range": [-0.5, n_cols - 0.5]},
        yaxis={"visible": False, "range": [-0.5, n_rows - 0.5], "scaleanchor": "x"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def plotly_char_poly(A, lam_range=None, n_steps: int = 41, title=None):
    """Sweep lambda: the graph of det(A - lambda I) beside the square it squashes.

    The characteristic equation is introduced as "det(A - lambda I) = 0" with no
    picture of why a determinant should vanish. Here the left panel plots that
    determinant and the right panel shows what (A - lambda I) does to the unit
    square. Drag lambda onto a root and watch the square flatten to a segment at
    the exact moment the curve crosses zero — the eigenvalue *is* the collapse.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    A = np.asarray(A, dtype=float)
    eig = np.linalg.eigvals(A)
    real_eig = np.real(eig[np.isreal(eig)])
    if lam_range is None:
        if real_eig.size:
            lo, hi = float(real_eig.min()), float(real_eig.max())
            pad = max(1.0, 0.6 * (hi - lo))
            lam_range = (lo - pad, hi + pad)
        else:
            lam_range = (-2.0, 2.0)
    lams = np.linspace(lam_range[0], lam_range[1], n_steps)
    curve_x = np.linspace(lam_range[0], lam_range[1], 241)
    curve_y = np.array([np.linalg.det(A - t * np.eye(2)) for t in curve_x])
    square = np.array([[0, 1, 1, 0, 0], [0, 0, 1, 1, 0]], dtype=float)
    images = [(A - t * np.eye(2)) @ square for t in lams]
    lim = 1.2 * float(max(np.abs(im).max() for im in images) or 1.0)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("det(A - λI)", "単位正方形の像（面積 = |det|）"),
        horizontal_spacing=0.12,
    )
    fig.add_trace(
        go.Scatter(x=_f(curve_x), y=_f(curve_y), mode="lines",
                   line={"color": "#1f77b4", "width": 2}, name="det(A - λI)"),
        row=1, col=1,
    )
    fig.add_hline(y=0, line={"color": "#999999", "width": 1}, row=1, col=1)
    for lam in real_eig:
        fig.add_vline(x=float(lam), line={"color": "#2ca02c", "width": 1, "dash": "dot"},
                      row=1, col=1)

    def moving(lam, im):
        return [
            go.Scatter(x=[float(lam)], y=[float(np.linalg.det(A - lam * np.eye(2)))],
                       mode="markers", marker={"color": "#d62728", "size": 12},
                       name="いまの λ"),
            go.Scatter(x=_f(im[0]), y=_f(im[1]), fill="toself",
                       fillcolor="rgba(214,39,40,0.25)",
                       line={"color": "#d62728", "width": 2}, name="像"),
        ]

    first = moving(lams[0], images[0])
    fig.add_trace(first[0], row=1, col=1)
    fig.add_trace(first[1], row=1, col=2)
    labels = [
        f"λ={lam:+.2f}  (det={np.linalg.det(A - lam * np.eye(2)):+.3f})" for lam in lams
    ]
    frames = [
        # Traces 1 and 2 move; the curve (0) and the eigen-lines stay put.
        go.Frame(data=moving(lam, im), traces=[1, 2], name=lab)
        for lam, im, lab in zip(lams, images, labels, strict=True)
    ]
    fig.frames = frames
    fig.update_layout(
        sliders=[{"steps": _slider_steps(labels), "currentvalue": {"prefix": ""}}],
        width=880,
        height=440,
        title=title or "固有値とは「det(A - λI) が 0 になる λ」＝正方形がつぶれる瞬間",
        showlegend=False,
        margin={"l": 50, "r": 20, "t": 70, "b": 40},
    )
    fig.update_xaxes(title_text="λ", row=1, col=1)
    fig.update_xaxes(range=[-lim, lim], row=1, col=2)
    fig.update_yaxes(range=[-lim, lim], scaleanchor="x2", row=1, col=2)
    return fig


def plotly_svd_rank_explorer(img, ks=None, title=None):
    """One slider driving both the rank-k image and the spectrum behind it.

    Previously these were two figures, so the reader had to move two sliders and
    pair up the numbers mentally. Here rank k picks the picture on the left and
    lights up the singular values paying for it on the right, with the retained
    energy and the storage cost in the label.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    from .decompositions import compression_ratio, svd_lowrank

    img = np.asarray(img, dtype=float)
    s = np.linalg.svd(img, compute_uv=False)
    share = s**2 / (s**2).sum()
    cum = np.cumsum(share)
    r = len(s)
    if ks is None:
        # Few enough frames that the embedded images stay a sane size.
        ks = [1, 2, 3, 5, 10, 20, 40]
    ks = [k for k in ks if 1 <= k <= r]
    idx = np.arange(1, r + 1)
    floor = max(float(share[share > 0].min()), float(share.max()) * 1e-6)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("ランク k 近似の見た目", "特異値のエネルギー比（対数）"),
        horizontal_spacing=0.1,
        column_widths=[0.45, 0.55],
    )

    def moving(k):
        return [
            go.Heatmap(z=_f(svd_lowrank(img, k)[::-1], 3), colorscale="gray",
                       showscale=False, hoverinfo="skip"),
            go.Bar(x=[int(i) for i in idx], y=list(share),
                   marker={"color": ["#d62728" if i < k else "#c7c7c7" for i in range(r)]},
                   name="エネルギー比"),
        ]

    first = moving(ks[0])
    fig.add_trace(first[0], row=1, col=1)
    fig.add_trace(first[1], row=1, col=2)
    labels = [
        f"k={k}  (説明 {cum[k - 1]:.1%} / 記憶 {compression_ratio(img.shape, k):.0%})" for k in ks
    ]
    fig.frames = [
        go.Frame(data=moving(k), traces=[0, 1], name=lab)
        for k, lab in zip(ks, labels, strict=True)
    ]
    fig.update_layout(
        sliders=[{"steps": _slider_steps(labels), "currentvalue": {"prefix": "ランク "}}],
        width=940,
        height=470,
        title=title or "ランク k を動かす：画像とスペクトルが連動する",
        showlegend=False,
        margin={"l": 40, "r": 30, "t": 70, "b": 40},
    )
    fig.update_xaxes(visible=False, row=1, col=1)
    fig.update_yaxes(visible=False, scaleanchor="x", row=1, col=1)
    fig.update_xaxes(title_text="特異値の番号", row=1, col=2)
    fig.update_yaxes(type="log", range=[float(np.log10(floor * 0.5)), float(np.log10(1.5))],
                     title_text="エネルギー比", row=1, col=2)
    return fig
