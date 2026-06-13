"""ipywidgets-based interactive demos.

These only work in a live kernel (JupyterLab). Every notebook pairs them with a
static figure so the exported HTML still tells the story. ipywidgets is
imported lazily so importing this module never fails in a headless build.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import solvers, systems
from .plotting import direction_field, phase_portrait, plot_solution_curves


def interactive_logistic():
    """Sliders for r, K, y0; redraws the logistic solution over its slope field."""
    import ipywidgets as widgets

    def draw(r, K, y0):
        t = np.linspace(0, 12, 300)
        f = systems.logistic(r, K)
        ax = direction_field(f, (0, 12), (0, max(2.0, 1.6 * K)), n=18)
        Y = solvers.rk4(f, [y0], t)
        ax.plot(t, Y[:, 0], color="#d62728", lw=2.2)
        ax.axhline(K, color="#2ca02c", ls="--", lw=1, label="K")
        ax.set_title(f"logistic: r={r:.2f}, K={K:.2f}, y0={y0:.2f}")
        plt.show()

    return widgets.interact(
        draw,
        r=widgets.FloatSlider(value=0.9, min=0.1, max=2.0, step=0.1, description="r"),
        K=widgets.FloatSlider(value=1.0, min=0.5, max=3.0, step=0.1, description="K"),
        y0=widgets.FloatSlider(value=0.1, min=0.01, max=3.0, step=0.05, description="y0"),
    )


def interactive_method_comparison():
    """Compare Euler vs RK4 against the exact decay solution as dt changes."""
    import ipywidgets as widgets

    rate, y0 = 1.5, 1.0

    def draw(n_steps):
        t = np.linspace(0, 5, int(n_steps))
        f = systems.exponential(-rate)
        exact = y0 * np.exp(-rate * t)
        ye = solvers.euler(f, [y0], t)[:, 0]
        yr = solvers.rk4(f, [y0], t)[:, 0]
        _, ax = plt.subplots(figsize=(6, 4))
        ax.plot(t, exact, "k-", lw=2, label="exact")
        ax.plot(t, ye, "o-", ms=3, color="#1f77b4", label="Euler")
        ax.plot(t, yr, "s-", ms=3, color="#2ca02c", label="RK4")
        ax.set_title(f"dt = {t[1] - t[0]:.3f}  ({int(n_steps)} steps)")
        ax.legend()
        ax.grid(alpha=0.25)
        plt.show()

    return widgets.interact(
        draw, n_steps=widgets.IntSlider(value=12, min=4, max=80, step=1, description="steps")
    )


def interactive_linear_phase():
    """Sliders for a 2x2 matrix A; redraws the phase portrait and its type."""
    import ipywidgets as widgets

    def draw(a, b, c, d):
        A = np.array([[a, b], [c, d]])
        f = systems.linear_system(A)
        kind = systems.classify_fixed_point(A)
        ax = phase_portrait(f, (-3, 3), (-3, 3), fixed_points=[(0, 0)])
        ax.set_title(f"dx/dt = A x  ->  {kind}")
        plt.show()

    s = dict(min=-2.0, max=2.0, step=0.1)
    return widgets.interact(
        draw,
        a=widgets.FloatSlider(value=0.0, description="a", **s),
        b=widgets.FloatSlider(value=1.0, description="b", **s),
        c=widgets.FloatSlider(value=-1.0, description="c", **s),
        d=widgets.FloatSlider(value=0.0, description="d", **s),
    )


def interactive_sir():
    """Sliders for beta, gamma; redraws the SIR curves and reports R0."""
    import ipywidgets as widgets

    def draw(beta, gamma):
        t = np.linspace(0, 60, 400)
        f = systems.sir(beta, gamma, N=1.0)
        Y = solvers.rk4(f, [0.99, 0.01, 0.0], t)
        ax = plot_solution_curves(t, [Y], labels=["S"], component=0)
        plot_solution_curves(t, [Y, Y], labels=["I", "R"], ax=ax, component=1)
        ax.plot(t, Y[:, 2], color="#2ca02c", label="R")
        ax.set_title(f"SIR: R0 = {beta / gamma:.2f}")
        ax.legend()
        plt.show()

    return widgets.interact(
        draw,
        beta=widgets.FloatSlider(value=0.5, min=0.1, max=1.0, step=0.05, description="beta"),
        gamma=widgets.FloatSlider(value=0.2, min=0.05, max=0.6, step=0.05, description="gamma"),
    )
