"""Shared notebook-plotting helpers for the johnhull volumes.

Captures the ipympl know-how from interest_rate_models/PROGRESS.md:
plt.ioff() right after import prevents duplicate-display comm_id errors,
and update callbacks should use fig.canvas.draw_idle().

The committed copies of the classic notebooks carry static PNG outputs so the
Jupyter Book (``execute_notebooks: off``) shows their figures. They are
written by ``verify_core_notebooks.py --write-outputs``, which sets
``HULLKIT_STATIC_FIGURES=1``; opened directly, the notebooks stay interactive.
"""

import base64
import os

import numpy as np

STATIC_FIGURES_ENV = "HULLKIT_STATIC_FIGURES"


def setup():
    """Prepare matplotlib for ipympl notebooks (Japanese fonts, no implicit display).

    Returns the pyplot module so notebooks can write ``plt = nbplot.setup()``.
    Under ``HULLKIT_STATIC_FIGURES=1`` it also calls
    :func:`enable_static_figures`.
    """
    import japanize_matplotlib  # noqa: F401
    import matplotlib.pyplot as plt

    enable_static_figures()
    plt.ioff()
    return plt


def figure_canvases(widget):
    """Matplotlib canvases in a widget tree (the widget itself, then its children)."""
    figure = getattr(widget, "figure", None)
    if figure is not None and hasattr(figure, "savefig"):
        yield widget
    for child in getattr(widget, "children", ()) or ():
        yield from figure_canvases(child)


def enable_static_figures():
    """Display ipywidgets as the PNGs of the figures they contain, if requested.

    Active only when ``HULLKIT_STATIC_FIGURES=1`` and an IPython shell is
    running; returns whether it was enabled. ``display(controls, fig.canvas)``
    and ``display(widgets.VBox([..., fig.canvas]))`` then publish one static
    PNG per ipympl canvas and nothing for sliders, so an executed notebook
    keeps its figures in a static renderer. The ipympl backend itself is left
    in place, so callbacks and ``fig.canvas.draw_idle()`` still work.
    """
    if os.environ.get(STATIC_FIGURES_ENV, "") != "1":
        return False
    try:
        from IPython import get_ipython
    except ImportError:  # pragma: no cover - notebooks always have IPython
        return False
    shell = get_ipython()
    if shell is None:
        return False
    import ipywidgets
    from IPython.core.pylabtools import print_figure
    from IPython.display import publish_display_data

    def display_static(widget):
        for canvas in figure_canvases(widget):
            figure = canvas.figure
            width, height = figure.get_size_inches() * figure.dpi
            png = print_figure(figure, "png", bbox_inches="tight")
            publish_display_data(
                {
                    "image/png": base64.b64encode(png).decode("ascii"),
                    "text/plain": (
                        f"<Figure size {width:g}x{height:g} with {len(figure.axes)} Axes>"
                    ),
                }
            )

    shell.display_formatter.ipython_display_formatter.for_type(ipywidgets.Widget, display_static)
    return True


def kde_xy(samples, n_pts=200):
    """Gaussian KDE of 1-D samples on an even grid. Returns (x, density)."""
    from scipy.stats import gaussian_kde

    samples = np.asarray(samples, dtype=float)
    if samples.size < 2 or np.ptp(samples) == 0.0:
        raise ValueError("kde_xy requires >= 2 samples with nonzero spread")
    kde = gaussian_kde(samples)
    x = np.linspace(samples.min(), samples.max(), n_pts)
    return x, kde(x)
