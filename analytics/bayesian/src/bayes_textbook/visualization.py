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


def plotly_posterior_update(
    prior,
    flips,
    n_grid: int = 400,
    title="Belief updating: prior -> likelihood -> posterior",
    slider_name="n flips",
):
    """Beta-Binomial belief updating as coin flips accumulate (slider over n).

    Each frame shows the fixed ``prior``, the normalized binomial likelihood of
    the first n flips, and the resulting posterior. As n grows the posterior
    concentrates -- you watch the peak rise and narrow. ``prior`` is a
    conjugacy.BetaBinomial; ``flips`` is a 0/1 array.
    """
    flips = np.asarray(flips)
    theta = np.linspace(1e-4, 1 - 1e-4, n_grid)
    prior_pdf = prior.dist.pdf(theta)
    n_total = len(flips)
    frames = []
    ymax = float(prior_pdf.max())
    for n in range(n_total + 1):
        s = int(flips[:n].sum())
        f = n - s
        if n == 0:
            like = np.ones_like(theta)
        else:
            like = theta**s * (1 - theta) ** f
        like = like / np.trapezoid(like, theta)
        post = prior.update(s, f)
        post_pdf = post.dist.pdf(theta)
        ymax = max(ymax, float(post_pdf.max()), float(like.max()))
        frames.append(
            (
                n,
                [
                    ("prior", prior_pdf, None),
                    ("likelihood", like, "dash"),
                    ("posterior", post_pdf, None),
                ],
            )
        )
    return plotly_curve_slider(
        theta, frames, slider_name=slider_name, title=title, ylim=(0, ymax * 1.05)
    )


def plotly_mcmc_trace(
    samples,
    target=None,
    n_frames: int = 12,
    title="MCMC convergence: trace + running mean",
    slider_name="steps",
):
    """Reveal an MCMC chain step by step with its running mean (slider).

    ``samples`` is a 1-D chain; the optional ``target`` draws the value the
    running mean should converge to. The slider grows the visible window, so
    you see the running mean settle while the raw trace keeps wandering.
    """
    s = np.asarray(samples, dtype=float)
    n = len(s)
    steps = np.arange(1, n + 1)
    run_mean = np.cumsum(s) / steps
    cutoffs = np.unique(np.linspace(max(2, n // n_frames), n, n_frames).astype(int))
    frames = []
    for c in cutoffs:
        shown = steps <= c
        trace = np.where(shown, s, np.nan)
        rmean = np.where(shown, run_mean, np.nan)
        curves = [("trace", trace, None), ("running mean", rmean, None)]
        if target is not None:
            curves.append(("target", np.full(n, float(target)), "dot"))
        frames.append((int(c), curves))
    lo, hi = float(np.nanmin(s)), float(np.nanmax(s))
    pad = 0.05 * (hi - lo + 1e-9)
    return plotly_curve_slider(
        steps, frames, slider_name=slider_name, title=title, ylim=(lo - pad, hi + pad)
    )


def plotly_posterior_predictive(
    x,
    y,
    x_grid=None,
    sigma: float = 1.0,
    sigma_w: float = 10.0,
    degree: int = 3,
    n_frames: int = 10,
    title="Posterior predictive: bands shrink with data",
    slider_name="n points",
):
    """Bayesian polynomial regression with predictive bands tightening on a slider.

    Fits a degree-``degree`` Bayesian linear regression (models.BayesianLinear
    Regression) on the first k points and draws the posterior mean with 95%
    credible (function uncertainty) and predictive (adds observation noise)
    bands. The slider sweeps k, so the bands visibly contract as data arrives.
    """
    import plotly.graph_objects as go

    from .models import BayesianLinearRegression

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    if x_grid is None:
        x_grid = np.linspace(x.min(), x.max(), 120)

    def design(t):
        return np.vander(np.asarray(t, dtype=float), degree + 1, increasing=True)

    Xg = design(x_grid)
    ks = np.unique(np.linspace(degree + 2, len(x), n_frames).astype(int))

    def frame_traces(k):
        model = BayesianLinearRegression(sigma=sigma, sigma_w=sigma_w).fit(design(x[:k]), y[:k])
        p = model.predict(Xg)
        return [
            go.Scatter(
                x=list(x_grid),
                y=list(p["pred_hi"]),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(p["pred_lo"]),
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(31,119,180,0.15)",
                line={"width": 0},
                name="95% predictive",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(p["cred_hi"]),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(p["cred_lo"]),
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(31,119,180,0.35)",
                line={"width": 0},
                name="95% credible",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(p["mean"]),
                mode="lines",
                line={"color": COLORS["posterior"], "width": 2},
                name="posterior mean",
            ),
            go.Scatter(
                x=list(x[:k]),
                y=list(y[:k]),
                mode="markers",
                marker={"color": "black", "size": 6},
                name="data",
            ),
        ]

    fig = go.Figure(
        data=frame_traces(int(ks[0])),
        frames=[go.Frame(data=frame_traces(int(k)), name=str(int(k))) for k in ks],
    )
    steps = [
        {
            "args": [
                [str(int(k))],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": str(int(k)),
            "method": "animate",
        }
        for k in ks
    ]
    pad = 0.15 * float(y.max() - y.min() + 1e-9)
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=720,
        height=450,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 30},
    )
    fig.update_yaxes(range=[float(y.min()) - pad, float(y.max()) + pad])
    return fig


def plotly_gp_regression(
    x_train=None,
    y_train=None,
    length_scale: float = 1.0,
    noise: float = 0.05,
    n_frames: int = 8,
    title="Gaussian process: posterior shrinks near data",
):
    """GP posterior mean and ±2σ band, slider over the number of observations.

    Reuses :class:`models.GaussianProcess`. The same Normal-prior x Normal-
    likelihood machinery as the conjugate chapters, lifted to functions: the
    band collapses where data lands and stays wide where it is absent.
    """
    import plotly.graph_objects as go

    from .models import GaussianProcess

    rng = np.random.default_rng(0)
    if x_train is None:
        x_all = np.sort(rng.uniform(-3, 3, 12))
        y_all = np.sin(1.5 * x_all) + 0.1 * rng.standard_normal(len(x_all))
    else:
        x_all = np.asarray(x_train, dtype=float)
        y_all = np.asarray(y_train, dtype=float)
    x_grid = np.linspace(-3.4, 3.4, 140)
    ks = np.unique(np.linspace(1, len(x_all), n_frames).astype(int))

    def traces(k):
        gp = GaussianProcess(length_scale=length_scale, signal_var=1.0, noise=noise)
        gp.fit(x_all[:k, None], y_all[:k])
        mean, sd = gp.predict(x_grid[:, None])
        return [
            go.Scatter(
                x=list(x_grid),
                y=list(mean + 2 * sd),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(mean - 2 * sd),
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(31,119,180,0.2)",
                line={"width": 0},
                name="±2σ",
            ),
            go.Scatter(
                x=list(x_grid),
                y=list(mean),
                mode="lines",
                line={"color": COLORS["posterior"], "width": 2},
                name="posterior mean",
            ),
            go.Scatter(
                x=list(x_all[:k]),
                y=list(y_all[:k]),
                mode="markers",
                marker={"color": "black", "size": 7},
                name="observations",
            ),
        ]

    fig = go.Figure(
        data=traces(int(ks[0])),
        frames=[go.Frame(data=traces(int(k)), name=str(int(k))) for k in ks],
    )
    steps = [
        {
            "args": [
                [str(int(k))],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": str(int(k)),
            "method": "animate",
        }
        for k in ks
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "observations = "}}],
        xaxis_title="x",
        yaxis_title="y",
        width=720,
        height=450,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(range=[-2.6, 2.6])
    return fig


def plotly_bandit_regret(
    true_rates=(0.2, 0.4, 0.6, 0.8),
    n_rounds: int = 2000,
    seed: int = 0,
    title="Cumulative regret: Thompson vs epsilon-greedy",
):
    """Cumulative regret of Thompson sampling vs epsilon-greedy on a bandit.

    Reuses :func:`models.thompson_bandit` and :func:`models.epsilon_greedy_bandit`.
    Thompson's posterior sampling explores smarter, so its regret curve stays
    well below the epsilon-greedy baseline.
    """
    import plotly.graph_objects as go

    from .models import epsilon_greedy_bandit, thompson_bandit

    _pt, regret_t = thompson_bandit(true_rates, n_rounds=n_rounds, seed=seed)
    _pe, regret_e = epsilon_greedy_bandit(true_rates, n_rounds=n_rounds, epsilon=0.1, seed=seed)
    t = list(range(1, n_rounds + 1))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=t,
            y=list(regret_t),
            mode="lines",
            name="Thompson sampling",
            line={"color": COLORS["posterior"]},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=list(regret_e),
            mode="lines",
            name="epsilon-greedy",
            line={"color": COLORS["prior"]},
        )
    )
    fig.update_layout(
        xaxis_title="round",
        yaxis_title="cumulative regret",
        width=720,
        height=440,
        title=title,
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_gibbs_path(
    rho: float = 0.85,
    n_steps: int = 80,
    n_frames: int = 20,
    title="Gibbs sampler exploring a correlated Gaussian",
):
    """Gibbs-sampler path over a correlated bivariate normal (slider reveals steps).

    Reuses :func:`models.gibbs_bivariate_normal`. Each move updates one
    coordinate at a time, so the chain visibly zig-zags along the correlation
    ridge while filling the target density (drawn as contour lines).
    """
    import plotly.graph_objects as go

    from .models import gibbs_bivariate_normal

    s = gibbs_bivariate_normal(rho, n_steps=n_steps, seed=0)
    g = np.linspace(-3, 3, 60)
    XX, YY = np.meshgrid(g, g)
    det = 1 - rho**2
    Z = np.exp(-0.5 * (XX**2 - 2 * rho * XX * YY + YY**2) / det)
    cutoffs = np.unique(np.linspace(2, n_steps, n_frames).astype(int))

    def traces(c):
        return [
            go.Contour(
                x=g,
                y=g,
                z=Z,
                showscale=False,
                contours_coloring="lines",
                line_width=1,
                colorscale="Greys",
            ),
            go.Scatter(
                x=list(s[:c, 0]),
                y=list(s[:c, 1]),
                mode="lines+markers",
                marker={"size": 4},
                name="chain",
            ),
        ]

    fig = go.Figure(
        data=traces(int(cutoffs[0])),
        frames=[go.Frame(data=traces(int(c)), name=str(int(c))) for c in cutoffs],
    )
    steps = [
        {
            "args": [
                [str(int(c))],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": str(int(c)),
            "method": "animate",
        }
        for c in cutoffs
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "steps = "}}],
        xaxis_title="x",
        yaxis_title="y",
        width=560,
        height=520,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    fig.update_yaxes(scaleanchor="x")
    return fig
