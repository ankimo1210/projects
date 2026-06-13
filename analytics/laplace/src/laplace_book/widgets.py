"""ipywidgets explorers for the interactive sections.

Each explorer recomputes a small figure as sliders move. They are *optional*:
every notebook also shows a static version of the same figure, so the prose
still makes sense in environments where widgets do not run (e.g. the static
HTML build). Import ipywidgets lazily so importing the package never fails.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import plotting, systems


def explore_complex_frequency(t_max: float = 8.0, n: int = 400):
    """Sliders for sigma, omega -> pole pair on the s-plane and its response."""
    from ipywidgets import FloatSlider, interact

    t = np.linspace(0.0, t_max, n)

    def _draw(sigma=-0.4, omega=3.0):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        plotting.plot_pole_and_response(sigma, omega, t, axes=axes)
        plt.show()

    return interact(
        _draw,
        sigma=FloatSlider(value=-0.4, min=-1.5, max=1.0, step=0.1, description="sigma"),
        omega=FloatSlider(value=3.0, min=0.0, max=8.0, step=0.25, description="omega"),
    )


def explore_second_order(t_max: float = 12.0, n: int = 500):
    """Sliders for wn, zeta -> step response and pole locations of a 2nd-order system."""
    from ipywidgets import FloatSlider, interact

    t = np.linspace(0.0, t_max, n)

    def _draw(wn=1.0, zeta=0.3):
        sys = systems.second_order(wn, zeta)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        plotting.plot_s_plane(poles=systems.poles(sys), ax=axes[0], title="poles")
        y = systems.step_response(sys, t)
        plotting.plot_time_responses(t, [y], labels=[f"zeta={zeta:.2f}"], ax=axes[1],
                                     title="step response", ylabel="y(t)")
        axes[1].axhline(1.0, color="gray", ls=":", lw=1)
        plt.show()

    return interact(
        _draw,
        wn=FloatSlider(value=1.0, min=0.3, max=3.0, step=0.1, description="wn"),
        zeta=FloatSlider(value=0.3, min=0.0, max=2.0, step=0.05, description="zeta"),
    )


def explore_feedback(t_max: float = 12.0, n: int = 500):
    """Slider for loop gain K -> closed-loop step response of K/(s(s+1)) feedback."""
    from ipywidgets import FloatSlider, interact

    t = np.linspace(0.0, t_max, n)

    def _draw(K=1.0):
        plant = systems.tf([1.0], [1.0, 1.0, 0.0])  # 1 / (s^2 + s)
        loop = systems.series(plant, systems.tf([K], [1.0]))
        closed = systems.feedback(loop)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        plotting.plot_s_plane(poles=systems.poles(closed), ax=axes[0], title="closed-loop poles")
        y = systems.step_response(closed, t)
        plotting.plot_time_responses(t, [y], labels=[f"K={K:.1f}"], ax=axes[1],
                                     title="closed-loop step", ylabel="y(t)")
        axes[1].axhline(1.0, color="gray", ls=":", lw=1)
        plt.show()

    return interact(K=FloatSlider(value=1.0, min=0.1, max=8.0, step=0.1, description="K"))(_draw)
