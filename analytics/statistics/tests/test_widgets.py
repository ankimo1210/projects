"""ipywidgets wrappers: they construct, and they delegate to plotting."""

import numpy as np
from stats_textbook import widgets


def test_ppv_widget_constructs_with_a_slider_and_a_figure():
    box = widgets.ppv_widget()
    kinds = [type(child).__name__ for child in box.children]
    assert any("Slider" in k for k in kinds)
    assert any("FigureWidget" in k or "Output" in k for k in kinds)


def test_clt_widget_constructs():
    box = widgets.clt_widget(sampler_names=("normal", "cauchy"))
    assert len(box.children) >= 2


def test_markov_widget_constructs():
    box = widgets.markov_widget(np.array([[0.9, 0.1], [0.2, 0.8]]))
    assert len(box.children) >= 2


def test_widgets_do_not_reimplement_figures():
    """Every widget must go through ``plotting`` -- no private figure code."""
    import inspect

    src = inspect.getsource(widgets)
    assert "go.Figure(" not in src, "widgets must delegate to plotting, not build figures"


def test_widgets_never_call_figure_show():
    """``show`` blocks on the browser renderer outside a notebook.

    Calling it made the tests above hang instead of fail, which is the worse
    failure mode -- pin the fix so it cannot come back.
    """
    import inspect

    src = inspect.getsource(widgets)
    assert ".show()" not in src, "use IPython.display.display; show() blocks headless"
