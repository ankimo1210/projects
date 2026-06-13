"""ipywidgets-based interactive demos (JupyterLab only).

Each notebook pairs these with a static figure so the exported HTML still tells
the story. ipywidgets is imported lazily so importing this module never fails
in a headless build.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import datasets, grids, solvers
from .plotting import plot_field_snapshots


def interactive_heat_stability():
    """Slider over the diffusion number r; show stable smoothing vs blow-up."""
    import ipywidgets as widgets

    g = grids.Grid1D(0.0, 1.0, 101)
    x, dx = g.x, g.dx
    u0 = datasets.bump(x, 0.5, 0.15)

    def draw(r):
        alpha = 1.0
        dt = r * dx**2 / alpha
        U = solvers.solve_heat_explicit(u0, alpha, dx, dt, steps=60)
        ax = plot_field_snapshots(x, U, [0, 5, 20, 60], dt=dt)
        verdict = "stable" if r <= 0.5 else "UNSTABLE (r > 1/2)"
        ax.set_title(f"explicit heat, r = {r:.2f}  ->  {verdict}")
        ax.set_ylim(-0.5, 1.5)
        plt.show()

    return widgets.interact(
        draw, r=widgets.FloatSlider(value=0.4, min=0.1, max=0.8, step=0.05, description="r")
    )


def interactive_transport_scheme():
    """Compare upwind vs FTCS for advection at a given CFL number."""
    import ipywidgets as widgets

    g = grids.Grid1D(0.0, 1.0, 201)
    x, dx = g.x, g.dx
    u0 = datasets.gaussian(x, 0.3, 0.06)

    def draw(C, scheme):
        c = 1.0
        dt = C * dx / c
        steps = int(0.4 / dt)
        U = solvers.solve_transport(u0, c, dx, dt, steps, scheme=scheme)
        _, ax = plt.subplots(figsize=(7, 4))
        ax.plot(x, U[0], "k--", lw=1, label="initial")
        ax.plot(x, U[-1], color="#d62728", lw=2, label=f"{scheme}, t={steps * dt:.2f}")
        ax.legend()
        ax.grid(alpha=0.25)
        ax.set_title(f"advection, CFL C = {C:.2f}")
        plt.show()

    return widgets.interact(
        draw,
        C=widgets.FloatSlider(value=0.8, min=0.2, max=1.4, step=0.1, description="CFL"),
        scheme=widgets.Dropdown(options=["upwind", "ftcs"], value="upwind", description="scheme"),
    )


def interactive_fourier_square():
    """Slider over number of Fourier terms approximating a square wave."""
    import ipywidgets as widgets

    x = np.linspace(0, 2 * np.pi, 800)
    target = np.where((x % (2 * np.pi)) < np.pi, 1.0, -1.0)

    def draw(n_terms):
        approx = solvers.square_wave_partial_sum(x, n_terms, L=np.pi)
        _, ax = plt.subplots(figsize=(7, 4))
        ax.plot(x, target, "k--", lw=1, label="square wave")
        ax.plot(x, approx, color="#d62728", lw=2, label=f"{n_terms} terms")
        ax.legend()
        ax.grid(alpha=0.25)
        ax.set_title(f"Fourier partial sum, {n_terms} terms (Gibbs near jumps)")
        plt.show()

    return widgets.interact(
        draw, n_terms=widgets.IntSlider(value=3, min=1, max=40, step=1, description="terms")
    )
