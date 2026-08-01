"""Figures for Part I (chapters 01-05).

Each function is a pure map from data to a ``go.Figure``: no globals, no
file writes, no randomness except through an explicit seed. That is what
makes them testable and what keeps the computation in the computation
modules where it belongs.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go
from scipy import stats

from .. import datasets, distributions, simulation
from ..processes import MarkovChain
from .core import apply_defaults, frame_slider

__all__ = [
    "clt_convergence",
    "joint_marginal_heatmap",
    "markov_convergence_slider",
    "poisson_limit_slider",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
]

# Display window for the standardised sample mean in ``clt_convergence``.
# Wide enough to hold a standard normal comfortably; everything past it is
# reported as an off-screen fraction rather than silently dropped.
VIEW = (-5.0, 5.0)


def ppv_slider(prevalences: Sequence[float], sensitivity: float, specificity: float) -> go.Figure:
    """Positive predictive value as prevalence varies (NB01's headline).

    An accurate test is still mostly wrong when the disease is rare -- the
    figure makes the collapse visible rather than arguing for it.
    """
    labels = ["真陽性", "偽陽性"]
    frames = []
    for prev in prevalences:
        tp = prev * sensitivity
        fp = (1.0 - prev) * (1.0 - specificity)
        ppv = tp / (tp + fp)
        frames.append(
            go.Frame(
                data=[go.Bar(x=labels, y=[tp, fp], text=[f"PPV = {ppv:.1%}", ""])],
                name=f"{prev:.3f}",
            )
        )
    return apply_defaults(
        frame_slider(frames, "有病率"),
        title="陽性者の内訳 — 有病率が下がると偽陽性が真陽性を飲み込む",
        yaxis_title="母集団に占める割合",
    )


def joint_marginal_heatmap(x: np.ndarray, y: np.ndarray, bins: int = 30) -> go.Figure:
    """A joint density with both marginals -- NB02's picture of marginalisation."""
    counts, xedges, yedges = np.histogram2d(x, y, bins=bins, density=True)
    xc = 0.5 * (xedges[:-1] + xedges[1:])
    yc = 0.5 * (yedges[:-1] + yedges[1:])
    fig = go.Figure(
        data=[
            go.Heatmap(z=counts.T, x=xc, y=yc, colorscale="Blues", showscale=False),
            go.Bar(x=xc, y=counts.sum(axis=1), name="x の周辺分布", yaxis="y2", opacity=0.5),
            go.Bar(x=yc, y=counts.sum(axis=0), name="y の周辺分布", xaxis="x2", opacity=0.5),
        ]
    )
    fig.update_layout(
        xaxis={"domain": [0.0, 0.78]},
        yaxis={"domain": [0.0, 0.78]},
        xaxis2={"domain": [0.82, 1.0]},
        yaxis2={"domain": [0.82, 1.0]},
    )
    return apply_defaults(fig, title="同時分布と 2 つの周辺分布", xaxis_title="x", yaxis_title="y")


def poisson_limit_slider(n_values: Sequence[int], lam: float, k_max: int = 15) -> go.Figure:
    """Binomial(n, lam/n) closing on Poisson(lam) as n grows (NB03)."""
    k = np.arange(0, k_max + 1)
    pois = stats.poisson.pmf(k, lam)
    frames = []
    for n in n_values:
        p = lam / n
        tv = distributions.binomial_poisson_tv_distance(int(n), float(p))
        frames.append(
            go.Frame(
                data=[
                    go.Bar(x=k, y=stats.binom.pmf(k, n, p), name=f"Binomial(n={n}, p={p:.4f})"),
                    go.Scatter(
                        x=k,
                        y=pois,
                        mode="lines+markers",
                        name=f"Poisson({lam}) — TV 距離 {tv:.4f}",
                    ),
                ],
                name=str(n),
            )
        )
    return apply_defaults(
        frame_slider(frames, "n"), title="ポアソン極限", xaxis_title="k", yaxis_title="確率"
    )


def relation_graph() -> go.Figure:
    """The map of Part I: which distribution turns into which, and when."""
    layout = distributions.relation_layout()
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    label_x, label_y, label_text = [], [], []
    for rel in distributions.RELATIONS:
        x0, y0 = layout[rel.source]
        x1, y1 = layout[rel.target]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        label_x.append(0.5 * (x0 + x1))
        label_y.append(0.5 * (y0 + y1))
        label_text.append(rel.condition)
    names = list(layout)
    fig = go.Figure(
        data=[
            go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"color": "#bbb"}, hoverinfo="skip"),
            go.Scatter(
                x=label_x,
                y=label_y,
                mode="markers",
                marker={"size": 6, "color": "#bbb"},
                text=label_text,
                hoverinfo="text",
                showlegend=False,
            ),
            go.Scatter(
                x=[layout[n][0] for n in names],
                y=[layout[n][1] for n in names],
                mode="markers+text",
                text=names,
                textposition="top center",
                marker={"size": 22, "color": "#4C78A8"},
                showlegend=False,
            ),
        ]
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_defaults(fig, title="分布の関係図 — 辺にカーソルを乗せると条件が出る")


def clt_convergence(
    sampler_names: Sequence[str], ns: Sequence[int], n_reps: int = 2000, seed: int = 0
) -> go.Figure:
    """The book's flagship figure: sample means going normal -- except Cauchy.

    Each frame is one sample size; each trace is one underlying law. The
    Cauchy histogram never narrows, which is the whole argument for why the
    CLT needs a finite variance.

    All series share one fixed binning over ``VIEW``. Letting Plotly choose
    bins per series would hide the point: Cauchy's standardised mean has a
    spread in the hundreds, so its automatic bins are ~15 units wide and it
    renders as nothing at all inside the window rather than as something
    wide. With a common grid it shows up as the low flat block it is, and
    the share of its mass that fell off-screen is named in the legend.
    """
    lo, hi = VIEW
    xbins = {"start": lo, "end": hi, "size": (hi - lo) / 60}
    frames = []
    for n in ns:
        traces = []
        for name in sampler_names:
            sampler = datasets.SAMPLERS[name]
            means = simulation.sampling_distribution(
                np.mean, sampler, n=int(n), n_reps=n_reps, seed=seed
            )
            # Standardise by the CLT's own prediction so a match is a match at
            # every n. Cauchy has no sd to standardise by -- it stays wide.
            scaled = means * np.sqrt(n)
            outside = float(np.mean((scaled < lo) | (scaled > hi)))
            label = name if outside < 0.005 else f"{name}（枠外 {outside:.0%}）"
            traces.append(
                go.Histogram(
                    x=scaled,
                    name=label,
                    opacity=0.55,
                    xbins=xbins,
                    autobinx=False,
                    histnorm="probability density",
                )
            )
        frames.append(go.Frame(data=traces, name=str(n)))
    fig = frame_slider(frames, "n")
    fig.update_layout(barmode="overlay", xaxis_range=list(VIEW))
    return apply_defaults(
        fig,
        title="標本平均の分布 — sqrt(n) で標準化したもの",
        xaxis_title="sqrt(n) * 標本平均",
        yaxis_title="密度",
    )


def random_walk_paths(paths: np.ndarray, n_show: int = 30) -> go.Figure:
    """Sample paths with a sqrt(t) envelope (NB05)."""
    paths = np.asarray(paths, dtype=float)
    t = np.arange(paths.shape[1])
    fig = go.Figure(
        data=[
            go.Scatter(x=t, y=path, mode="lines", line={"width": 1}, showlegend=False)
            for path in paths[:n_show]
        ]
    )
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([t, t[::-1]]),
            y=np.concatenate([np.sqrt(t), -np.sqrt(t)[::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.15)",
            line={"width": 0},
            name="±sqrt(t)",
        )
    )
    return apply_defaults(fig, title="ランダムウォーク", xaxis_title="ステップ", yaxis_title="位置")


def markov_convergence_slider(chain: MarkovChain, p0: np.ndarray, n_steps: int = 30) -> go.Figure:
    """The chain's law forgetting where it started (NB05)."""
    labels = list(chain.states) if chain.states else [str(i) for i in range(chain.n_states)]
    pi = chain.stationary()
    frames = []
    for n in range(n_steps + 1):
        p = chain.distribution_after(n, p0)
        frames.append(
            go.Frame(
                data=[
                    go.Bar(x=labels, y=p, name="n ステップ後"),
                    go.Scatter(
                        x=labels, y=pi, mode="markers", marker={"size": 12}, name="定常分布"
                    ),
                ],
                name=str(n),
            )
        )
    fig = frame_slider(frames, "ステップ数")
    fig.update_layout(yaxis_range=[0, 1])
    return apply_defaults(fig, title="マルコフ連鎖の分布が定常分布に落ち着く", yaxis_title="確率")
