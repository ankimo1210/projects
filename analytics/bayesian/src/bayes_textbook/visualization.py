"""Shared plots (matplotlib) and static-HTML-capable Plotly sliders.

Figure labels are in English (no Japanese font setup needed); the notebook
prose carries the Japanese explanation.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .distributions import grid_pdf, grid_pmf

COLORS = {"prior": "#1f77b4", "likelihood": "#2ca02c", "posterior": "#d62728"}


def plot_distribution(frozen, kind: str = "continuous", ax=None, label=None, **kw):
    """Plot a frozen scipy distribution (pdf line or pmf stems)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 4))
    if kind == "continuous":
        x, y = grid_pdf(frozen)
        ax.plot(x, y, label=label, **kw)
        ax.set_ylabel("density")
    else:
        k, p = grid_pmf(frozen)
        ax.vlines(k, 0, p, lw=3, alpha=0.8, label=label, **kw)
        ax.set_ylabel("probability")
    ax.grid(alpha=0.3)
    if label:
        ax.legend()
    return ax


def plot_beta(alpha: float, beta: float, ax=None, **kw):
    """Convenience: plot Beta(alpha, beta)."""
    return plot_distribution(
        stats.beta(alpha, beta), ax=ax, label=f"Beta({alpha:g}, {beta:g})", **kw
    )


def plot_prior_likelihood_posterior(prior, successes: int, failures: int, ax=None):
    """The signature Bayes picture: prior, (normalized) likelihood, posterior.

    ``prior`` is a conjugacy.BetaBinomial. The binomial likelihood is rescaled
    to integrate to 1 so the three curves share one axis.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 4.5))
    post = prior.update(successes, failures)
    theta = np.linspace(1e-4, 1 - 1e-4, 400)
    like = theta**successes * (1 - theta) ** failures
    like = like / np.trapezoid(like, theta)

    ax.plot(
        theta,
        prior.dist.pdf(theta),
        color=COLORS["prior"],
        label=f"prior Beta({prior.alpha:g}, {prior.beta:g})",
    )
    ax.plot(
        theta,
        like,
        color=COLORS["likelihood"],
        ls="--",
        label=f"likelihood (s={successes}, f={failures})",
    )
    ax.plot(
        theta,
        post.dist.pdf(theta),
        color=COLORS["posterior"],
        lw=2,
        label=f"posterior Beta({post.alpha:g}, {post.beta:g})",
    )
    ax.set_xlabel("theta")
    ax.set_ylabel("density")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_beta_binomial_update(prior, flips, ax=None, checkpoints=(0, 2, 10, None)):
    """Sequential updating: posterior after increasing numbers of coin flips.

    ``flips`` is a 0/1 array; ``checkpoints`` are flip counts to draw
    (None = all flips).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 4.5))
    flips = np.asarray(flips)
    theta = np.linspace(1e-4, 1 - 1e-4, 400)
    n_total = len(flips)
    for i, n in enumerate(checkpoints):
        n = n_total if n is None else min(n, n_total)
        s = int(flips[:n].sum())
        post = prior.update(s, n - s)
        ax.plot(
            theta,
            post.dist.pdf(theta),
            alpha=0.4 + 0.6 * i / max(1, len(checkpoints) - 1),
            color=COLORS["posterior"],
            label=f"after n={n} (s={s})",
        )
    ax.set_xlabel("theta")
    ax.set_ylabel("density")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_credible_interval(post, level: float = 0.95, ax=None, color=COLORS["posterior"]):
    """Posterior density with the equal-tailed credible interval shaded."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    x, y = grid_pdf(post.dist)
    lo, hi = post.credible_interval(level)
    ax.plot(x, y, color=color)
    mask = (x >= lo) & (x <= hi)
    ax.fill_between(
        x[mask],
        y[mask],
        alpha=0.3,
        color=color,
        label=f"{int(level * 100)}% CI [{lo:.3f}, {hi:.3f}]",
    )
    ax.axvline(post.mean, color="k", ls=":", lw=1, label=f"mean {post.mean:.3f}")
    ax.set_xlabel("theta")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_regression_uncertainty(
    x, y, model, x_grid=None, n_lines: int = 30, ax=None, seed: int = 42
):
    """Data + sampled regression lines + credible and predictive bands."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 5))
    if x_grid is None:
        x_grid = np.linspace(x.min() - 0.5, x.max() + 0.5, 120)
    Xg = np.column_stack([np.ones_like(x_grid), x_grid])
    for w in model.sample_weights(n_lines, seed=seed):
        ax.plot(x_grid, Xg @ w, color="gray", alpha=0.15, lw=1)
    pred = model.predict(Xg)
    ax.fill_between(
        x_grid,
        pred["pred_lo"],
        pred["pred_hi"],
        alpha=0.15,
        color="#1f77b4",
        label="95% predictive band",
    )
    ax.fill_between(
        x_grid,
        pred["cred_lo"],
        pred["cred_hi"],
        alpha=0.35,
        color="#1f77b4",
        label="95% credible band (function)",
    )
    ax.plot(x_grid, pred["mean"], color="#d62728", lw=2, label="posterior mean")
    ax.scatter(x, y, s=25, color="k", zorder=3, label="data")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_shrinkage(result, ax=None, group_labels=None, sizes=None):
    """The classic partial-pooling picture: raw rates shrink toward the pool.

    ``result`` is a models.PoolingResult. Arrow length = amount of shrinkage;
    optional ``sizes`` annotates each group's sample size.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8.5, 5))
    k = len(result.unpooled)
    xs = np.arange(k)
    ax.axhline(result.pooled, color="gray", ls="--", label="complete pooling (one rate)")
    ax.scatter(xs, result.unpooled, s=40, color="#1f77b4", label="no pooling (raw rate)")
    ax.scatter(xs, result.partial, s=40, color="#d62728", label="partial pooling (hierarchical)")
    for i in range(k):
        ax.annotate(
            "",
            xy=(xs[i], result.partial[i]),
            xytext=(xs[i], result.unpooled[i]),
            arrowprops={"arrowstyle": "->", "color": "gray", "alpha": 0.6},
        )
    if sizes is not None:
        for i, n in enumerate(sizes):
            ax.text(
                xs[i],
                min(result.unpooled[i], result.partial[i]) - 0.004,
                f"n={n}",
                ha="center",
                fontsize=7,
                color="gray",
            )
    if group_labels is not None:
        ax.set_xticks(xs, group_labels, rotation=45, fontsize=8)
    ax.set_ylabel("rate")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_trace(samples, ax=None, burn_in: int | None = None, title=None):
    """Trace plot of a 1-D chain, optionally marking the burn-in cutoff."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))
    ax.plot(samples, lw=0.6)
    if burn_in:
        ax.axvspan(0, burn_in, color="red", alpha=0.12, label=f"burn-in ({burn_in})")
        ax.legend(fontsize=8)
    ax.set_xlabel("step")
    ax.set_ylabel("value")
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title)
    return ax


def plot_autocorr(samples, max_lag: int = 50, ax=None, label=None):
    """Autocorrelation function of a chain (mixing diagnostic)."""
    from .models import autocorrelation

    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 3.2))
    acf = autocorrelation(samples, max_lag)
    ax.vlines(np.arange(len(acf)), 0, acf, lw=2, alpha=0.8, label=label)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("lag")
    ax.set_ylabel("autocorrelation")
    ax.grid(alpha=0.3)
    if label:
        ax.legend()
    return ax


def plot_posterior_predictive(observed, pp_samples, ax=None, bins=20, stat_label="value"):
    """Observed data histogram vs draws from the posterior predictive."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    ax.hist(
        np.asarray(pp_samples).ravel(),
        bins=bins,
        density=True,
        alpha=0.4,
        color="#1f77b4",
        label="posterior predictive",
    )
    ax.hist(
        np.asarray(observed),
        bins=bins,
        density=True,
        alpha=0.5,
        color="#d62728",
        histtype="step",
        lw=2,
        label="observed",
    )
    ax.set_xlabel(stat_label)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    return ax


def plot_ranking_intervals(names, samples_list, level: float = 0.95, ax=None, truth=None):
    """Credible-interval ranking: items sorted by posterior mean, with CIs."""
    from .utils import credible_interval

    means = [np.mean(s) for s in samples_list]
    order = np.argsort(means)[::-1]
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 0.45 * len(names) + 1.5))
    for rank, i in enumerate(order):
        lo, hi = credible_interval(samples_list[i], level)
        ax.plot([lo, hi], [rank, rank], color="#1f77b4", lw=2)
        ax.plot(means[i], rank, "o", color="#d62728")
        if truth is not None:
            ax.plot(truth[i], rank, "x", color="k", ms=7)
    ax.set_yticks(range(len(names)), [names[i] for i in order])
    ax.invert_yaxis()
    ax.set_xlabel("estimate")
    ax.grid(alpha=0.3, axis="x")
    return ax


# ---------------------------------------------------------------------------
# Plotly sliders (work in the static Jupyter Book HTML)
# ---------------------------------------------------------------------------


def plotly_curve_slider(
    x, frames, slider_name: str = "step", title=None, ylim=None, frame_traces: int | None = None
):
    """A line plot with a slider stepping through frames.

    frames: list of (label, list_of_(name, y, dash_or_None)) — each frame can
    hold several named curves over the shared x grid.
    """
    import plotly.graph_objects as go

    def traces(curves):
        out = []
        for name, y, dash in curves:
            out.append(
                go.Scatter(
                    x=list(x),
                    y=list(y),
                    mode="lines",
                    name=name,
                    line={"dash": dash} if dash else None,
                )
            )
        return out

    _first_label, first_curves = frames[0]
    fig = go.Figure(
        data=traces(first_curves),
        frames=[go.Frame(data=traces(c), name=str(lab)) for lab, c in frames],
    )
    steps = [
        {
            "args": [[str(lab)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(lab),
            "method": "animate",
        }
        for lab, _ in frames
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=720,
        height=450,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 30},
    )
    if ylim is not None:
        fig.update_yaxes(range=list(ylim))
    return fig
