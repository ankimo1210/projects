"""Figures for Part II (chapters 06-08).

Same rules as ``probability``: pure functions from data to a ``go.Figure``,
frames assembled here and animated through ``core.frame_slider``, and bin
counts rather than raw samples in anything histogram-shaped.

``coverage_intervals`` is the chapter-07 flagship. It draws the intervals
themselves and states the *measured* hit count in the title, so the figure
reports what happened rather than what was promised.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import plotly.graph_objects as go

from .. import estimation, intervals, simulation, testing
from .core import apply_defaults, frame_slider

__all__ = [
    "bootstrap_distribution",
    "coverage_intervals",
    "likelihood_curve",
    "mle_sampling_distribution",
    "phacking_demo",
    "power_curves",
]

_BINS = 50


def _density_bars(values: np.ndarray, name: str, lo: float, hi: float) -> go.Bar:
    """Bin here so the figure carries counts, not every replicate."""
    edges = np.linspace(lo, hi, _BINS + 1)
    counts, _ = np.histogram(values, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]
    return go.Bar(x=centres, y=counts / (values.size * width), name=name, opacity=0.6, width=width)


def likelihood_curve(
    family_name: str, x: np.ndarray, grid: Sequence[float] | None = None
) -> go.Figure:
    """The log-likelihood as a function of theta, with the MLE marked (NB06)."""
    x = np.asarray(x, dtype=float)
    hat = estimation.mle(family_name, x)
    if grid is None:
        span = max(4.0 * hat.se, 0.1 * abs(hat.estimate))
        grid = np.linspace(hat.estimate - span, hat.estimate + span, 200)
    grid = np.asarray(grid, dtype=float)
    ll = np.array([estimation.log_likelihood(family_name, t, x) for t in grid])
    fig = go.Figure(
        data=[
            go.Scatter(x=grid, y=ll, mode="lines", name="対数尤度"),
            go.Scatter(
                x=[hat.estimate],
                y=[hat.loglik],
                mode="markers",
                marker={"size": 12, "color": "crimson"},
                name=f"MLE = {hat.estimate:.4f}",
            ),
        ]
    )
    return apply_defaults(
        fig,
        title=f"{family_name} の対数尤度 — 頂点が最尤推定量",
        xaxis_title="theta",
        yaxis_title="対数尤度",
    )


def mle_sampling_distribution(
    family_name: str, theta: float, ns: Sequence[int], n_reps: int = 3000, seed: int = 0
) -> go.Figure:
    """The MLE's own distribution tightening as n grows, against the CRLB (NB06)."""
    frames = []
    for n in ns:

        def sampler(m, rng, _f=family_name, _t=theta):
            if _f == "poisson":
                return rng.poisson(_t, m).astype(float)
            if _f == "bernoulli":
                return (rng.random(m) < _t).astype(float)
            if _f == "exponential":
                return rng.exponential(1.0 / _t, m)
            return rng.normal(_t, 1.0, m)

        hats = simulation.sampling_distribution(
            lambda s, _f=family_name: estimation.mle(_f, s).estimate,
            sampler,
            n=int(n),
            n_reps=n_reps,
            seed=seed,
        )
        sd = np.sqrt(estimation.cramer_rao_bound(family_name, theta, int(n)))
        lo, hi = theta - 4.0 * sd, theta + 4.0 * sd
        grid = np.linspace(lo, hi, 200)
        normal = np.exp(-0.5 * ((grid - theta) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        frames.append(
            go.Frame(
                data=[
                    _density_bars(hats, f"MLE の分布 (sd = {hats.std(ddof=1):.4f})", lo, hi),
                    go.Scatter(
                        x=grid,
                        y=normal,
                        mode="lines",
                        name=f"Cramer-Rao 下限 (sd = {sd:.4f})",
                    ),
                ],
                name=str(n),
            )
        )
    fig = frame_slider(frames, "n")
    return apply_defaults(
        fig,
        title="最尤推定量の標本分布は Cramer-Rao 下限に張り付く",
        xaxis_title="推定値",
        yaxis_title="密度",
    )


def coverage_intervals(
    n_intervals: int = 100, n: int = 12, truth: float = 0.0, seed: int = 0
) -> go.Figure:
    """Draw many 95% intervals and count how many contain the truth (NB07).

    The title carries the measured count. A reader who remembers one figure
    from this book should remember this one: 95% is a property of the
    procedure, visible only across repetitions.
    """
    rng = np.random.default_rng(seed)
    hit_x, hit_y, miss_x, miss_y = [], [], [], []
    for i in range(n_intervals):
        sample = rng.normal(truth, 1.0, n)
        interval = intervals.t_interval(sample)
        target = (hit_x, hit_y) if interval.contains(truth) else (miss_x, miss_y)
        target[0].extend([interval.lo, interval.hi, None])
        target[1].extend([i, i, None])
    hits = sum(1 for v in hit_y if v is not None) // 2
    fig = go.Figure(
        data=[
            go.Scatter(
                x=hit_x, y=hit_y, mode="lines", line={"color": "#4C78A8"}, name="真値を含む"
            ),
            go.Scatter(
                x=miss_x, y=miss_y, mode="lines", line={"color": "crimson"}, name="真値を外す"
            ),
        ]
    )
    fig.add_vline(x=truth, line={"color": "black", "dash": "dash"})
    return apply_defaults(
        fig,
        title=f"95% 信頼区間を {n_intervals} 本 — 真値を含んだのは {hits}/{n_intervals}",
        xaxis_title="値",
        yaxis_title="実験の番号",
    )


def bootstrap_distribution(
    sample: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    seed: int = 0,
) -> go.Figure:
    """The resampling distribution of any statistic, with the observed value (NB07)."""
    sample = np.asarray(sample, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, sample.size, size=(n_boot, sample.size))
    boot = np.array([float(statistic(sample[i])) for i in idx])
    observed = float(statistic(sample))
    ci = intervals.bootstrap_interval(sample, statistic, n_boot=n_boot, seed=seed)
    lo, hi = boot.min(), boot.max()
    fig = go.Figure(data=[_density_bars(boot, "ブートストラップ分布", lo, hi)])
    fig.add_vline(x=observed, line={"color": "crimson"})
    fig.add_vrect(x0=ci.lo, x1=ci.hi, fillcolor="#4C78A8", opacity=0.12, line_width=0)
    return apply_defaults(
        fig,
        title=f"観測値 {observed:.4f}、95% 区間 [{ci.lo:.4f}, {ci.hi:.4f}]",
        xaxis_title="統計量",
        yaxis_title="密度",
    )


def power_curves(effects: Sequence[float], ns: Sequence[int], alpha: float = 0.05) -> go.Figure:
    """Power against sample size, one curve per effect size (NB08)."""
    ns = list(ns)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=ns,
                y=[testing.power_t_test(e, n, alpha) for n in ns],
                mode="lines+markers",
                name=f"効果量 {e}",
            )
            for e in effects
        ]
    )
    fig.add_hline(y=0.8, line={"color": "grey", "dash": "dot"})
    fig.update_yaxes(range=[0, 1])
    return apply_defaults(
        fig,
        title=f"検出力曲線 (alpha = {alpha}、破線は慣習的な 0.8)",
        xaxis_title="標本サイズ n",
        yaxis_title="検出力",
    )


def phacking_demo(n_tests: int = 200, n: int = 30, seed: int = 0) -> go.Figure:
    """Run many tests on pure noise and count the "discoveries" (NB08)."""
    rng = np.random.default_rng(seed)
    pvals = np.array([testing.t_test(rng.normal(0.0, 1.0, n)).pvalue for _ in range(n_tests)])
    raw = int((pvals < 0.05).sum())
    bonf = int(testing.bonferroni(pvals).sum())
    bh = int(testing.benjamini_hochberg(pvals).sum())
    edges = np.linspace(0.0, 1.0, 21)
    counts, _ = np.histogram(pvals, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    fig = go.Figure(
        data=[
            go.Bar(x=centres, y=counts, width=0.05, name="p 値の分布(全て帰無仮説が真)"),
            go.Bar(
                x=[0.025],
                y=[raw],
                width=0.05,
                marker={"color": "crimson"},
                name=f"補正なしで有意 {raw} 件",
            ),
        ]
    )
    fig.update_layout(barmode="overlay")
    return apply_defaults(
        fig,
        title=(
            f"純粋なノイズに {n_tests} 回検定 — 補正なし {raw} 件、Bonferroni {bonf} 件、BH {bh} 件"
        ),
        xaxis_title="p 値",
        yaxis_title="件数",
    )
