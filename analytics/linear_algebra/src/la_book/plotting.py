"""Shared plotting helpers (matplotlib + a few Plotly figures).

Figure labels are kept in English so no Japanese font setup is required;
the surrounding notebook text carries the Japanese explanation.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

VEC_COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]


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
    lim = 1.3 * max(1.0, float(np.abs(np.linalg.eigvals(A)).max()))
    thetas = np.linspace(0, np.pi, n_angles)

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
        sliders=[{"steps": steps, "currentvalue": {"prefix": "angle (deg) = "}}],
        width=560,
        height=560,
        title=title,
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

    def grid_traces(A):
        A = np.asarray(A, dtype=float)
        traces = []
        for c in ticks:
            for seg in (np.vstack([np.full_like(t, c), t]), np.vstack([t, np.full_like(t, c)])):
                out = A @ seg
                traces.append(
                    go.Scatter(
                        x=out[0],
                        y=out[1],
                        mode="lines",
                        line={"color": "#1f77b4", "width": 1},
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
        return traces

    frames = [
        go.Frame(data=grid_traces(M), name=str(lab))
        for M, lab in zip(matrices, labels, strict=True)
    ]
    fig = go.Figure(data=grid_traces(matrices[0]), frames=frames)
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
        xaxis={"range": [-2 * lim, 2 * lim], "scaleanchor": "y", "zeroline": True},
        yaxis={"range": [-2 * lim, 2 * lim], "zeroline": True},
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
    approx = {k: svd_lowrank(img, k) for k in ks}
    frames = [
        go.Frame(
            data=[go.Heatmap(z=approx[k][::-1], colorscale="gray", showscale=False)], name=str(k)
        )
        for k in ks
    ]
    fig = go.Figure(
        data=[go.Heatmap(z=approx[ks[0]][::-1], colorscale="gray", showscale=False)], frames=frames
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
        sliders=[{"steps": steps, "currentvalue": {"prefix": "rank = "}}],
        width=460,
        height=500,
        title="low-rank image approximation",
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

    def traces(k):
        colors = ["#d62728" if i < k else "#c7c7c7" for i in range(r)]
        return [
            go.Bar(
                x=list(idx),
                y=list(share),
                marker={"color": colors},
                name="energy share",
                showlegend=False,
            ),
            go.Scatter(
                x=list(idx),
                y=list(cum),
                mode="lines",
                name="cumulative energy",
                line={"color": "#1f77b4"},
                yaxis="y2",
            ),
            go.Scatter(
                x=[k],
                y=[float(cum[k - 1])],
                mode="markers+text",
                marker={"color": "#1f77b4", "size": 12, "symbol": "circle-open"},
                text=[f"{cum[k - 1]:.0%}"],
                textposition="top center",
                showlegend=False,
                yaxis="y2",
            ),
        ]

    fig = go.Figure(
        data=traces(1),
        frames=[go.Frame(data=traces(int(k)), name=str(int(k))) for k in idx],
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
        for k in idx
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "rank k = "}}],
        width=720,
        height=450,
        title=title,
        xaxis={"title": "singular value index"},
        yaxis={"title": "energy share", "rangemode": "tozero"},
        yaxis2={
            "title": "cumulative energy",
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
        xaxis_title="maturity (years)",
        yaxis_title="yield (%)",
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
        xaxis_title="maturity (years)",
        yaxis_title="loading",
        width=720,
        height=420,
        margin={"l": 60, "r": 20, "t": 30, "b": 50},
    )
    return fig


def plotly_iterative_convergence(
    A=None, b=None, n_iter: int = 40, title="Iterative solvers: residual vs iteration"
):
    """Residual norm per iteration for Jacobi / Gauss-Seidel / Conjugate Gradient.

    Reuses :func:`algebra.jacobi`, :func:`algebra.gauss_seidel`,
    :func:`algebra.conjugate_gradient`. Default system is the 1-D Laplacian
    (SPD), where CG converges in far fewer steps than the splitting methods.
    """
    import plotly.graph_objects as go

    from .algebra import conjugate_gradient, gauss_seidel, jacobi

    if A is None:
        n = 20
        A = 2 * np.eye(n) - np.eye(n, k=1) - np.eye(n, k=-1)
    A = np.asarray(A, dtype=float)
    b = np.ones(A.shape[0]) if b is None else np.asarray(b, dtype=float)
    _, rj = jacobi(A, b, n_iter=n_iter, return_history=True)
    _, rg = gauss_seidel(A, b, n_iter=n_iter, return_history=True)
    _, rc = conjugate_gradient(A, b, max_iter=n_iter)
    fig = go.Figure()
    for name, res in [("Jacobi", rj), ("Gauss-Seidel", rg), ("Conjugate Gradient", rc)]:
        res = np.clip(np.asarray(res, dtype=float), 1e-16, None)
        fig.add_trace(
            go.Scatter(x=list(range(len(res))), y=list(res), mode="lines+markers", name=name)
        )
    fig.update_layout(
        xaxis_title="iteration",
        yaxis_title="residual norm",
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
        sliders=[{"steps": steps, "currentvalue": {"prefix": "iteration = "}}],
        xaxis_title="page",
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
    lr: float = 0.12,
    n_iter: int = 30,
    x0=(-2.6, 2.6),
    title="Gradient descent on a quadratic bowl",
):
    """Contour of f(x) = 0.5 xᵀA x − bᵀx with the GD path revealed by a slider.

    Reuses :func:`algebra.gradient_descent_quadratic`. The anisotropic bowl
    (unequal eigenvalues) makes the descent zig-zag toward the minimum.
    """
    import plotly.graph_objects as go

    from .algebra import gradient_descent_quadratic

    if A is None:
        A = np.array([[3.0, 0.0], [0.0, 1.0]])
    A = np.asarray(A, dtype=float)
    b = np.zeros(A.shape[0]) if b is None else np.asarray(b, dtype=float)
    path = gradient_descent_quadratic(A, b, lr=lr, n_iter=n_iter, x0=np.array(x0, dtype=float))
    span = 3.0
    g = np.linspace(-span, span, 60)
    XX, YY = np.meshgrid(g, g)
    Z = 0.5 * (A[0, 0] * XX**2 + (A[0, 1] + A[1, 0]) * XX * YY + A[1, 1] * YY**2) - (
        b[0] * XX + b[1] * YY
    )

    def traces(k):
        return [
            go.Contour(
                x=g,
                y=g,
                z=Z,
                showscale=False,
                contours_coloring="lines",
                line_width=1,
                colorscale="Greys",
            ),
            go.Scatter(
                x=list(path[: k + 1, 0]),
                y=list(path[: k + 1, 1]),
                mode="lines+markers",
                name="GD path",
            ),
        ]

    frames = [go.Frame(data=traces(k), name=str(k)) for k in range(len(path))]
    fig = go.Figure(data=traces(0), frames=frames)
    steps = [
        {
            "args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(k),
            "method": "animate",
        }
        for k in range(len(path))
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "step = "}}],
        xaxis_title="x1",
        yaxis_title="x2",
        width=560,
        height=540,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(scaleanchor="x")
    return fig
