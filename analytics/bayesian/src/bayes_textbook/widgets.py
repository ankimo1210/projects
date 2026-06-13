"""ipywidgets demos (live kernel only; notebooks pair them with static figures)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from . import visualization as viz
from .conjugacy import BetaBinomial


def interactive_medical_test():
    """Sliders for prevalence / sensitivity / specificity -> P(disease | positive)."""
    import ipywidgets as widgets

    def draw(prevalence, sensitivity, specificity):
        p_pos = sensitivity * prevalence + (1 - specificity) * (1 - prevalence)
        ppv = sensitivity * prevalence / p_pos
        # Natural frequencies out of 10,000 people.
        n = 10_000
        sick = prevalence * n
        tp, fp = sensitivity * sick, (1 - specificity) * (n - sick)
        _fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
        axes[0].bar(["true positive", "false positive"], [tp, fp], color=["#d62728", "#1f77b4"])
        axes[0].set_title(f"positives out of {n:,} people")
        axes[0].grid(alpha=0.3, axis="y")
        axes[1].bar(["P(disease | positive)"], [ppv], color="#d62728")
        axes[1].set_ylim(0, 1)
        axes[1].axhline(prevalence, color="gray", ls=":", label=f"prior {prevalence:.3f}")
        axes[1].set_title(f"PPV = {ppv:.1%}")
        axes[1].legend()
        plt.show()

    return widgets.interact(
        draw,
        prevalence=widgets.FloatSlider(
            value=0.01, min=0.001, max=0.5, step=0.001, readout_format=".3f"
        ),
        sensitivity=widgets.FloatSlider(value=0.95, min=0.5, max=1.0, step=0.01),
        specificity=widgets.FloatSlider(value=0.95, min=0.5, max=1.0, step=0.01),
    )


def interactive_distribution():
    """Dropdown over common distributions, sliders for their parameters."""
    import ipywidgets as widgets

    from .distributions import DISTRIBUTIONS

    name_dd = widgets.Dropdown(options=list(DISTRIBUTIONS), value="beta", description="dist")
    out = widgets.Output()
    sliders_box = widgets.VBox([])

    def rebuild(_=None):
        factory, specs, kind = DISTRIBUTIONS[name_dd.value]
        sliders = [
            widgets.FloatSlider(value=d, min=lo, max=hi, step=st, description=lab)
            for lab, lo, hi, st, d in specs
        ]

        def redraw(_=None):
            with out:
                out.clear_output(wait=True)
                frozen = factory(*[s.value for s in sliders])
                viz.plot_distribution(frozen, kind=kind)
                plt.title(f"{name_dd.value}({', '.join(f'{s.value:g}' for s in sliders)})")
                plt.show()

        for s in sliders:
            s.observe(redraw, names="value")
        sliders_box.children = sliders
        redraw()

    name_dd.observe(rebuild, names="value")
    rebuild()
    from IPython.display import display

    display(widgets.VBox([name_dd, sliders_box, out]))
    return name_dd, sliders_box, out


def interactive_beta_binomial():
    """Sliders for prior (alpha, beta) and data (successes, failures)."""
    import ipywidgets as widgets

    def draw(alpha, beta, successes, failures):
        viz.plot_prior_likelihood_posterior(
            BetaBinomial(alpha, beta), int(successes), int(failures)
        )
        plt.show()

    return widgets.interact(
        draw,
        alpha=widgets.FloatSlider(value=2, min=0.5, max=30, step=0.5),
        beta=widgets.FloatSlider(value=2, min=0.5, max=30, step=0.5),
        successes=widgets.IntSlider(value=7, min=0, max=100),
        failures=widgets.IntSlider(value=3, min=0, max=100),
    )


def interactive_prior_likelihood_posterior():
    """Alias kept for the spec's naming: same demo as interactive_beta_binomial."""
    return interactive_beta_binomial()


def interactive_bayesian_regression():
    """Sliders for data size and prior strength on a fixed synthetic dataset."""
    import ipywidgets as widgets

    from .models import BayesianLinearRegression

    r = np.random.default_rng(42)
    x_all = np.sort(r.uniform(-3, 3, 80))
    y_all = 0.8 + 1.4 * x_all + 1.0 * r.standard_normal(80)

    def draw(n_points, log10_sigma_w):
        x, y = x_all[:n_points], y_all[:n_points]
        X = np.column_stack([np.ones_like(x), x])
        model = BayesianLinearRegression(sigma=1.0, sigma_w=10.0**log10_sigma_w).fit(X, y)
        viz.plot_regression_uncertainty(x, y, model, x_grid=np.linspace(-3.2, 3.2, 100))
        plt.title(
            f"n={n_points}, sigma_w=10^{log10_sigma_w:.1f}, "
            f"w=({model.w_mean[0]:.2f}, {model.w_mean[1]:.2f})"
        )
        plt.show()

    return widgets.interact(
        draw,
        n_points=widgets.IntSlider(value=10, min=2, max=80),
        log10_sigma_w=widgets.FloatSlider(value=1.0, min=-2.0, max=1.5, step=0.1),
    )


def interactive_hierarchical_shrinkage():
    """Slider scales every group's sample size; watch shrinkage strengthen/relax."""
    import ipywidgets as widgets

    from .models import fit_partial_pooling_beta
    from .simulation import make_store_conversions

    base = make_store_conversions(n_stores=10, seed=42)

    def draw(size_factor):
        visits = np.maximum(1, (base["visits"] * size_factor).astype(int))
        r = np.random.default_rng(0)
        conv = r.binomial(visits, base["true_rate"])
        res = fit_partial_pooling_beta(conv, visits)
        viz.plot_shrinkage(res, group_labels=base["store"], sizes=visits)
        plt.title(f"sample sizes x{size_factor:.2f}")
        plt.show()

    return widgets.interact(
        draw, size_factor=widgets.FloatLogSlider(value=1.0, base=10, min=-1.5, max=1.0, step=0.25)
    )


def interactive_mcmc_sampler():
    """Proposal-width slider for random-walk Metropolis on a bimodal target."""
    import ipywidgets as widgets

    from .models import metropolis_hastings

    def log_target(x):
        return np.logaddexp(stats.norm.logpdf(x, -2, 0.6), stats.norm.logpdf(x, 2, 0.6))

    grid = np.linspace(-5, 5, 300)
    dens = np.exp([log_target(g) for g in grid])
    dens /= np.trapezoid(dens, grid)

    def draw(proposal_sd):
        samples, rate = metropolis_hastings(
            log_target, x0=-2.0, n_steps=2000, proposal_sd=proposal_sd, seed=0
        )
        _fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
        axes[0].plot(samples, lw=0.5)
        axes[0].set_title(f"trace (acceptance rate {rate:.0%})")
        axes[0].grid(alpha=0.3)
        axes[1].hist(samples[200:], bins=50, density=True, alpha=0.5, label="samples")
        axes[1].plot(grid, dens, "r", label="target")
        axes[1].legend()
        axes[1].grid(alpha=0.3)
        plt.show()

    return widgets.interact(
        draw, proposal_sd=widgets.FloatLogSlider(value=1.0, base=10, min=-1.5, max=1.3, step=0.1)
    )
