"""ipywidgets wrappers for readers running a live kernel.

Strictly a convenience layer: every widget re-calls the corresponding
``plotting`` function and swaps the figure in. The book must read the same
without a kernel, so nothing here may own figure construction -- duplicated
figures drift apart, and the static HTML would be the one that goes stale.
"""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as ipw
import numpy as np
from IPython.display import display

from . import plotting
from .processes import MarkovChain

__all__ = ["clt_widget", "markov_widget", "ppv_widget"]


def _panel(control: ipw.Widget, render) -> ipw.VBox:
    """Wire ``control`` to an output area redrawn by ``render(value)``.

    Uses ``display`` rather than ``Figure.show``: outside a notebook the
    default renderer is the browser one, and ``show`` blocks on it forever
    (constructing a widget under pytest hung until killed). ``display``
    degrades to a repr in a plain process and renders normally in a kernel.
    """
    out = ipw.Output()

    def _redraw(change) -> None:
        out.clear_output(wait=True)
        with out:
            display(render(change["new"]))

    control.observe(_redraw, names="value")
    with out:
        display(render(control.value))
    return ipw.VBox([control, out])


def ppv_widget(sensitivity: float = 0.99, specificity: float = 0.95) -> ipw.VBox:
    """Drag prevalence and watch the positive predictive value collapse."""
    slider = ipw.FloatLogSlider(
        value=0.01, base=10, min=-4, max=-0.3, step=0.1, description="有病率"
    )
    return _panel(slider, lambda prev: plotting.ppv_slider([prev], sensitivity, specificity))


def clt_widget(
    sampler_names: Sequence[str] = ("normal", "exponential", "cauchy"),
) -> ipw.VBox:
    """Drag the sample size through the central limit theorem."""
    slider = ipw.IntSlider(value=5, min=1, max=200, step=1, description="n")
    return _panel(
        slider, lambda n: plotting.clt_convergence(list(sampler_names), ns=[n], n_reps=1500)
    )


def markov_widget(P: np.ndarray) -> ipw.VBox:
    """Drag the step count and watch the chain forget its start."""
    chain = MarkovChain(np.asarray(P, dtype=float))
    p0 = np.zeros(chain.n_states)
    p0[0] = 1.0
    slider = ipw.IntSlider(value=0, min=0, max=60, step=1, description="ステップ")
    return _panel(
        slider, lambda n: plotting.markov_convergence_slider(chain, p0, n_steps=max(n, 1))
    )
