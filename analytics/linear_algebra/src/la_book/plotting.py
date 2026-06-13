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
