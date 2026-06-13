"""ipywidgets-based interactive demos.

These only work in a live kernel (JupyterLab). The notebooks always pair them
with a static figure so the exported HTML still tells the story.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .plotting import plot_grid_transform, plot_vectors


def interactive_transform(lim: float = 2.0):
    """Sliders for the four entries of a 2x2 matrix; redraws the grid image."""
    import ipywidgets as widgets

    sliders = {
        name: widgets.FloatSlider(value=val, min=-2.0, max=2.0, step=0.1, description=name)
        for name, val in [("a", 1.0), ("b", 0.0), ("c", 0.0), ("d", 1.0)]
    }

    def draw(a, b, c, d):
        plot_grid_transform(np.array([[a, b], [c, d]]), lim=lim)
        plt.show()

    return widgets.interact(draw, **sliders)


def interactive_eigen(A=None):
    """Rotate a unit vector u and watch Au; alignment means an eigen-direction."""
    import ipywidgets as widgets

    if A is None:
        A = np.array([[2.0, 1.0], [1.0, 2.0]])
    A = np.asarray(A, dtype=float)

    def draw(theta_deg):
        th = np.deg2rad(theta_deg)
        u = np.array([np.cos(th), np.sin(th)])
        Au = A @ u
        cross = u[0] * Au[1] - u[1] * Au[0]
        _, ax = plt.subplots(figsize=(5.5, 5.5))
        lim = 1.3 * max(1.0, np.linalg.norm(Au))
        plot_vectors([u, Au], labels=["u", "Au"], colors=["#1f77b4", "#d62728"], ax=ax, lim=lim)
        ax.set_title(f"u x Au = {cross:+.3f}  (0 means eigen-direction)")
        plt.show()

    slider = widgets.FloatSlider(value=20.0, min=0.0, max=180.0, step=1.0, description="theta")
    return widgets.interact(draw, theta_deg=slider)


def interactive_rank(img):
    """Slider over k: original image vs its best rank-k approximation."""
    import ipywidgets as widgets

    from .decompositions import compression_ratio, svd_lowrank

    img = np.asarray(img, dtype=float)
    kmax = min(img.shape)

    def draw(k):
        _, axes = plt.subplots(1, 2, figsize=(8, 4))
        axes[0].imshow(img, cmap="gray")
        axes[0].set_title("original")
        axes[1].imshow(svd_lowrank(img, k), cmap="gray")
        axes[1].set_title(f"rank {k} ({compression_ratio(img.shape, k):.0%} storage)")
        for ax in axes:
            ax.axis("off")
        plt.show()

    slider = widgets.IntSlider(value=10, min=1, max=kmax, step=1, description="rank k")
    return widgets.interact(draw, k=slider)
