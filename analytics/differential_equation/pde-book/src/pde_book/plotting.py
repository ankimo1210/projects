"""Shared plotting helpers (matplotlib, plus a small animation helper).

Figure labels are English so no Japanese font setup is needed; the surrounding
notebook prose carries the Japanese explanation. The "calculus foundations"
visuals match the ODE book so 00 章 can be shared; the rest are PDE-specific
(field snapshots, space-time heatmaps, 2-D fields, animations).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

CURVE_COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]


def _new_ax(ax, figsize=(6, 4.5)):
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    return ax


# --------------------------------------------------------------------------- #
# Calculus foundations visuals (shared with the ODE book's 00 章).
# --------------------------------------------------------------------------- #
def plot_function(f, xs, ax=None, label=None, color=None, **kw):
    """Plot y = f(x) over the array ``xs``."""
    ax = _new_ax(ax)
    xs = np.asarray(xs, dtype=float)
    ax.plot(xs, f(xs), color=color or CURVE_COLORS[1], label=label, **kw)
    ax.axhline(0, color="gray", lw=0.6)
    ax.axvline(0, color="gray", lw=0.6)
    ax.grid(alpha=0.25)
    if label:
        ax.legend()
    return ax


def plot_secant_to_tangent(f, x0, hs, xs=None, ax=None):
    """Secant lines through x0 for shrinking offsets ``hs`` approaching the tangent."""
    ax = _new_ax(ax)
    if xs is None:
        span = max(abs(h) for h in hs) * 2.5
        xs = np.linspace(x0 - span, x0 + span, 200)
    ax.plot(xs, f(xs), color="black", lw=1.8, label="f(x)")
    ax.plot([x0], [f(x0)], "o", color="black", zorder=5)
    blues = plt.cm.Blues(np.linspace(0.4, 0.9, len(hs)))
    for h, c in zip(sorted(hs, reverse=True), blues, strict=False):
        slope = (f(x0 + h) - f(x0)) / h
        ax.plot(xs, f(x0) + slope * (xs - x0), color=c, lw=1.0, label=f"secant h={h:g}")
    tan_slope = (f(x0 + min(hs)) - f(x0 - min(hs))) / (2 * min(hs))
    ax.plot(xs, f(x0) + tan_slope * (xs - x0), color="#d62728", lw=2.0, label="tangent")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    return ax


def plot_riemann(f, a, b, n, rule="mid", xs=None, ax=None):
    """Draw the Riemann rectangles for f on [a, b] over a smooth curve."""
    ax = _new_ax(ax)
    if xs is None:
        xs = np.linspace(a, b, 300)
    ax.plot(xs, f(xs), color="#d62728", lw=2.0, zorder=5, label="f(x)")
    edges = np.linspace(a, b, n + 1)
    dx = (b - a) / n
    if rule == "left":
        sample = edges[:-1]
    elif rule == "right":
        sample = edges[1:]
    else:
        sample = 0.5 * (edges[:-1] + edges[1:])
    ax.bar(
        edges[:-1],
        f(sample),
        width=dx,
        align="edge",
        alpha=0.35,
        color="#1f77b4",
        edgecolor="#1f77b4",
        label=f"{rule} sum, n={n}",
    )
    ax.axhline(0, color="gray", lw=0.6)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9)
    return ax


def plot_area_fill(f, a, b, xs=None, ax=None):
    """Shade the signed area under f between a and b (the definite integral)."""
    ax = _new_ax(ax)
    if xs is None:
        xs = np.linspace(a, b, 300)
    ax.plot(xs, f(xs), color="#d62728", lw=2.0)
    ax.fill_between(xs, f(xs), alpha=0.3, color="#1f77b4")
    ax.axhline(0, color="gray", lw=0.6)
    ax.grid(alpha=0.25)
    return ax


def plot_taylor_approx(f_true, approx_by_order, xs, x0=0.0, ax=None):
    """Overlay Taylor approximations of increasing order on the true function."""
    ax = _new_ax(ax)
    xs = np.asarray(xs, dtype=float)
    ax.plot(xs, f_true(xs), color="black", lw=2.2, label="f(x)")
    for order in sorted(approx_by_order):
        ax.plot(xs, approx_by_order[order](xs), lw=1.3, label=f"order {order}")
    ax.plot([x0], [f_true(x0)], "o", color="#d62728", zorder=5)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    return ax


def contour_plot(f, xlim, ylim, n=80, ax=None, levels=14, with_gradient=False, ng=16):
    """Filled contour of a scalar field f(point); optionally overlay grad arrows."""
    ax = _new_ax(ax, figsize=(5.5, 5))
    xs = np.linspace(*xlim, n)
    ys = np.linspace(*ylim, n)
    X, Y = np.meshgrid(xs, ys)
    Z = np.array([[f(np.array([x, y])) for x in xs] for y in ys])
    cs = ax.contourf(X, Y, Z, levels=levels, cmap="viridis")
    ax.contour(X, Y, Z, levels=levels, colors="white", linewidths=0.4, alpha=0.5)
    plt.colorbar(cs, ax=ax, shrink=0.85)
    if with_gradient:
        gx = np.linspace(*xlim, ng)
        gy = np.linspace(*ylim, ng)
        GX, GY = np.meshgrid(gx, gy)
        from .calculus import gradient as _grad

        U = np.zeros_like(GX)
        V = np.zeros_like(GY)
        for i in range(GX.shape[0]):
            for j in range(GX.shape[1]):
                g = _grad(f, np.array([GX[i, j], GY[i, j]]))
                U[i, j], V[i, j] = g
        ax.quiver(GX, GY, U, V, color="white", alpha=0.9)
    ax.set_aspect("equal")
    return ax


def surface_plot(f, xlim, ylim, n=60, ax=None):
    """3-D surface of a scalar field f(point). Returns the 3-D Axes."""
    xs = np.linspace(*xlim, n)
    ys = np.linspace(*ylim, n)
    X, Y = np.meshgrid(xs, ys)
    Z = np.array([[f(np.array([x, y])) for x in xs] for y in ys])
    if ax is None:
        fig = plt.figure(figsize=(6, 5))
        ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
    return ax


# --------------------------------------------------------------------------- #
# PDE-specific visuals.
# --------------------------------------------------------------------------- #
def plot_field_snapshots(x, U, step_indices, dt=None, ax=None, title=None):
    """Overlay several time snapshots of a 1-D field history U (shape (steps+1, nx))."""
    ax = _new_ax(ax, figsize=(7, 4))
    x = np.asarray(x, dtype=float)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(step_indices)))
    for k, c in zip(step_indices, colors, strict=False):
        lab = f"step {k}" if dt is None else f"t={k * dt:.3f}"
        ax.plot(x, U[k], color=c, lw=2, label=lab)
    ax.set_xlabel("x")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    if title:
        ax.set_title(title)
    return ax


def space_time_heatmap(U, x, t, ax=None, title=None, cmap="inferno"):
    """Heatmap of a 1-D field history U over (x horizontal, t vertical)."""
    ax = _new_ax(ax, figsize=(6.5, 4.5))
    im = ax.imshow(
        U,
        aspect="auto",
        origin="lower",
        cmap=cmap,
        extent=[float(x[0]), float(x[-1]), float(t[0]), float(t[-1])],
    )
    plt.colorbar(im, ax=ax, shrink=0.9)
    ax.set_xlabel("x")
    ax.set_ylabel("t")
    if title:
        ax.set_title(title)
    return ax


def heatmap_2d(U, grid=None, ax=None, title=None, cmap="viridis"):
    """Heatmap of a 2-D field U (shape (ny, nx))."""
    ax = _new_ax(ax, figsize=(5.5, 4.8))
    extent = None
    if grid is not None:
        extent = [grid.x0, grid.x1, grid.y0, grid.y1]
    im = ax.imshow(U, origin="lower", cmap=cmap, extent=extent, aspect="equal")
    plt.colorbar(im, ax=ax, shrink=0.85)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    if title:
        ax.set_title(title)
    return ax


def surface_2d(X, Y, U, ax=None, title=None):
    """3-D surface of a 2-D field. X, Y, U all shape (ny, nx)."""
    if ax is None:
        fig = plt.figure(figsize=(6, 5))
        ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, U, cmap="viridis", linewidth=0, antialiased=True)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    if title:
        ax.set_title(title)
    return ax


def line_animation(x, frames, interval=60, ylim=None, xlabel="x", title=None, step=1):
    """FuncAnimation of a 1-D field evolving over time.

    ``frames`` has shape (n_time, len(x)); ``step`` subsamples time for speed.
    In notebooks wrap with IPython.display.HTML(anim.to_jshtml()); a static
    snapshot is always shown alongside so the exported HTML stays meaningful.
    """
    from matplotlib import animation

    frames = np.asarray(frames, dtype=float)[::step]
    fig, ax = plt.subplots(figsize=(6, 4))
    (line,) = ax.plot(x, frames[0], color="#d62728", lw=2)
    ax.set_xlim(float(np.min(x)), float(np.max(x)))
    if ylim is None:
        pad = 0.1 * (frames.max() - frames.min() + 1e-9)
        ylim = (frames.min() - pad, frames.max() + pad)
    ax.set_ylim(*ylim)
    ax.set_xlabel(xlabel)
    ax.grid(alpha=0.25)
    if title:
        ax.set_title(title)

    def update(k):
        line.set_ydata(frames[k])
        return (line,)

    anim = animation.FuncAnimation(fig, update, frames=len(frames), interval=interval, blit=True)
    plt.close(fig)
    return anim
