"""Shared plotting helpers (matplotlib, plus a small animation helper).

Figure labels are English so no Japanese font setup is needed; the surrounding
notebook prose carries the Japanese explanation. Functions return the Axes (or
Figure/animation) so notebooks can compose or further annotate them.
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
# Calculus foundations visuals.
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
    """Show secant lines through x0 for shrinking offsets ``hs`` -> the tangent.

    The tangent (computed from the smallest h) is drawn in red; secants fade
    from light to dark as h -> 0, making the limit visible.
    """
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
    """Overlay Taylor approximations of increasing order on the true function.

    ``approx_by_order`` maps an integer order -> a callable g(x).
    """
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
# ODE-specific visuals.
# --------------------------------------------------------------------------- #
def direction_field(f, tlim, ylim, n=20, ax=None, color="#888888"):
    """Slope field for a scalar ODE dy/dt = f(t, y).

    Arrows are normalized so only the *direction* (the slope) is shown.
    """
    ax = _new_ax(ax)
    ts = np.linspace(*tlim, n)
    ys = np.linspace(*ylim, n)
    T, Y = np.meshgrid(ts, ys)
    S = np.vectorize(lambda t, y: float(np.asarray(f(t, y)).ravel()[0]))(T, Y)
    U = np.ones_like(S)
    V = S
    norm = np.hypot(U, V)
    ax.quiver(T, Y, U / norm, V / norm, color=color, angles="xy", pivot="mid", width=0.0025)
    ax.set_xlabel("t")
    ax.set_ylabel("y")
    ax.grid(alpha=0.2)
    return ax


def plot_solution_curves(t, trajectories, labels=None, ax=None, component=0):
    """Plot one component of several trajectories (each shape (len(t), dim))."""
    ax = _new_ax(ax)
    t = np.asarray(t, dtype=float)
    for i, Y in enumerate(trajectories):
        Y = np.atleast_2d(np.asarray(Y, dtype=float))
        if Y.shape[0] != t.size:
            Y = Y.T
        lab = None if labels is None else labels[i]
        ax.plot(t, Y[:, component], color=CURVE_COLORS[i % len(CURVE_COLORS)], label=lab)
    ax.set_xlabel("t")
    ax.grid(alpha=0.25)
    if labels:
        ax.legend(fontsize=9)
    return ax


def phase_portrait(f, xlim, ylim, n=22, trajectories=None, fixed_points=None, ax=None, stream=True):
    """Phase portrait of a 2-D system: stream/quiver field + trajectories.

    ``trajectories`` is a list of arrays of shape (steps, 2); ``fixed_points``
    a list of (x, y) marked with a red dot.
    """
    ax = _new_ax(ax, figsize=(5.8, 5.2))
    xs = np.linspace(*xlim, n)
    ys = np.linspace(*ylim, n)
    X, Y = np.meshgrid(xs, ys)
    U = np.zeros_like(X)
    V = np.zeros_like(Y)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            dx, dy = f(0.0, np.array([X[i, j], Y[i, j]]))
            U[i, j], V[i, j] = dx, dy
    if stream:
        ax.streamplot(X, Y, U, V, color="#aaaaaa", density=1.1, linewidth=0.7, arrowsize=0.8)
    else:
        norm = np.hypot(U, V) + 1e-12
        ax.quiver(X, Y, U / norm, V / norm, color="#aaaaaa", pivot="mid", width=0.003)
    if trajectories:
        for i, traj in enumerate(trajectories):
            traj = np.asarray(traj, dtype=float)
            ax.plot(traj[:, 0], traj[:, 1], color=CURVE_COLORS[i % len(CURVE_COLORS)], lw=1.8)
            ax.plot(traj[0, 0], traj[0, 1], "o", color=CURVE_COLORS[i % len(CURVE_COLORS)], ms=5)
    if fixed_points:
        fp = np.atleast_2d(np.asarray(fixed_points, dtype=float))
        ax.plot(fp[:, 0], fp[:, 1], "*", color="#d62728", ms=14, zorder=6)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return ax


def line_animation(x, frames, interval=60, ylim=None, xlabel="x", title=None):
    """FuncAnimation of a 1-D field evolving over time (also reused for PDE).

    ``frames`` is an array of shape (n_time, len(x)). Returns a FuncAnimation;
    in notebooks wrap with IPython.display.HTML(anim.to_jshtml()). A static
    snapshot is always shown alongside so the exported HTML stays meaningful.
    """
    from matplotlib import animation

    frames = np.asarray(frames, dtype=float)
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
