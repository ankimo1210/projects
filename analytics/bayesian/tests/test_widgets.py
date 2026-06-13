"""Widget demos: build each one and flip its controls (kernel-side callbacks)."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from bayes_textbook import widgets as wdg


def _poke(interact_result, n_changes: int = 2):
    """Simulate user interaction on a widgets.interact result."""
    container = interact_result.widget
    for child in container.children:
        if not hasattr(child, "value"):
            continue
        if hasattr(child, "options") and child.options:
            for opt in list(child.options)[:n_changes]:
                child.value = opt if not isinstance(opt, tuple) else opt[1]
        elif hasattr(child, "min") and hasattr(child, "max"):
            lo, hi = child.min, child.max
            for frac in (0.3, 0.8)[:n_changes]:
                child.value = type(child.value)(lo + frac * (hi - lo))
    plt.close("all")


def test_interactive_medical_test():
    _poke(wdg.interactive_medical_test())


def test_interactive_beta_binomial():
    _poke(wdg.interactive_beta_binomial())


def test_interactive_bayesian_regression():
    _poke(wdg.interactive_bayesian_regression())


def test_interactive_hierarchical_shrinkage():
    _poke(wdg.interactive_hierarchical_shrinkage())


def test_interactive_mcmc_sampler():
    _poke(wdg.interactive_mcmc_sampler())


def test_interactive_distribution_dropdown():
    name_dd, sliders_box, _out = wdg.interactive_distribution()
    for name in ["normal", "poisson", "beta"]:
        name_dd.value = name  # rebuilds sliders + redraws
        for s in sliders_box.children:
            s.value = type(s.value)(s.min + 0.5 * (s.max - s.min))
    plt.close("all")


def test_plotly_curve_slider_structure():
    from bayes_textbook.visualization import plotly_curve_slider

    x = np.linspace(0, 1, 50)
    frames = [
        (n, [("posterior", x**n, None), ("prior", np.ones_like(x), "dash")]) for n in [1, 2, 3]
    ]
    fig = plotly_curve_slider(x, frames, slider_name="n")
    assert len(fig.frames) == 3
    assert len(fig.layout.sliders[0].steps) == 3
    assert len(fig.data) == 2
