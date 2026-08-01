"""Figures for chapters 09-10.

The residual catalogue is the workhorse: four designs that a coefficient
table cannot tell apart, and which the residual plot separates instantly.
That is the chapter's argument for looking at residuals at all.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go

from .. import glm, regression, simulation
from .core import apply_defaults, frame_slider

__all__ = [
    "coefficient_sampling",
    "irls_convergence",
    "link_function_fits",
    "residual_catalogue",
    "robust_se_comparison",
]

_BINS = 40


def _density_bars(values: np.ndarray, name: str) -> go.Bar:
    edges = np.linspace(values.min(), values.max(), _BINS + 1)
    counts, _ = np.histogram(values, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]
    return go.Bar(x=centres, y=counts / (values.size * width), name=name, opacity=0.65, width=width)


def _pathologies(n: int, seed: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Four designs that a coefficient table cannot diagnose.

    Measured at seed 1, n=200: the slopes come out 2.04, 1.88 and 2.05 and
    every p-value is below 1e-50, so the coefficient row reads the same
    across all of them. R^2 does move (0.94, 0.85, 0.71) -- but a lower R^2
    is equally consistent with plain extra noise, so it says something is
    different without saying what. The residual plot says what.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(-3, 3, n))
    X = np.column_stack([np.ones(n), x])
    out = [
        ("健全 — 仮定どおり", X, 1.0 + 2.0 * x + rng.normal(0, 1.0, n)),
        (
            "不均一分散 — ばらつきが x で変わる",
            X,
            1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.6 * np.abs(x), n),
        ),
        ("非線形 — 直線では足りない", X, 1.0 + 2.0 * x + 0.7 * x**2 + rng.normal(0, 1.0, n)),
        ("外れ値 — 少数の点が引っ張る", X, 1.0 + 2.0 * x + rng.normal(0, 1.0, n)),
    ]
    # Plant the outliers in the last design only.
    y = out[3][2].copy()
    y[[2, n // 2, n - 3]] += 12.0
    out[3] = (out[3][0], out[3][1], y)
    return out


def residual_catalogue(seed: int = 0, n: int = 200) -> go.Figure:
    """Fitted-vs-residual plots for four designs, on one slider (NB09)."""
    frames = []
    for label, X, y in _pathologies(n, seed):
        fit = regression.ols(X, y)
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(
                        x=fit.fitted,
                        y=fit.resid,
                        mode="markers",
                        marker={"size": 6},
                        name=f"R^2 = {fit.r_squared:.3f}",
                    )
                ],
                name=label,
            )
        )
    fig = frame_slider(frames, "データ")
    fig.add_hline(y=0.0, line={"color": "grey", "dash": "dash"})
    return apply_defaults(
        fig,
        title="残差プロットの病理カタログ — 係数表からは何が違うのか分からない",
        xaxis_title="当てはめ値",
        yaxis_title="残差",
    )


def coefficient_sampling(n: int = 60, n_reps: int = 3000, seed: int = 0) -> go.Figure:
    """The slope's own sampling distribution against its theoretical normal (NB09)."""
    true_slope = 2.0

    def sampler(m, rng):
        x = rng.normal(size=m)
        return np.column_stack([x, 1.0 + true_slope * x + rng.normal(0, 1.5, m)])

    def slope(pair):
        x, y = pair[:, 0], pair[:, 1]
        return float(regression.ols(np.column_stack([np.ones(x.size), x]), y).params[1])

    slopes = simulation.sampling_distribution(slope, sampler, n=n, n_reps=n_reps, seed=seed)
    grid = np.linspace(slopes.min(), slopes.max(), 200)
    sd = slopes.std(ddof=1)
    normal = np.exp(-0.5 * ((grid - true_slope) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
    fig = go.Figure(
        data=[
            _density_bars(slopes, f"傾きの標本分布 (sd = {sd:.4f})"),
            go.Scatter(x=grid, y=normal, mode="lines", name="正規近似"),
        ]
    )
    fig.add_vline(x=true_slope, line={"color": "crimson", "dash": "dash"})
    return apply_defaults(
        fig,
        title=f"回帰係数は推定量である — n = {n} での標本分布",
        xaxis_title="推定された傾き",
        yaxis_title="密度",
    )


def robust_se_comparison(seed: int = 0, ns: Sequence[int] = (50, 200, 1000)) -> go.Figure:
    """Ordinary vs HC3 standard errors under heteroskedasticity (NB09)."""
    rng = np.random.default_rng(seed)
    ns = list(ns)
    ordinary, robust = [], []
    for n in ns:
        x = rng.normal(size=n)
        X = np.column_stack([np.ones(n), x])
        y = 1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.8 * np.abs(x), n)
        fit = regression.ols(X, y)
        ordinary.append(float(fit.se[1]))
        robust.append(float(regression.robust_se(X, fit.resid, kind="HC3")[1]))
    fig = go.Figure(
        data=[
            go.Bar(x=[str(n) for n in ns], y=ordinary, name="通常の標準誤差"),
            go.Bar(x=[str(n) for n in ns], y=robust, name="HC3(頑健)"),
        ]
    )
    return apply_defaults(
        fig,
        title="不均一分散があると通常の標準誤差は当てにならない",
        xaxis_title="標本サイズ",
        yaxis_title="傾きの標準誤差",
    )


def link_function_fits(
    x: np.ndarray, y: np.ndarray, families: Sequence[str] = ("binomial", "gaussian")
) -> go.Figure:
    """The same binary data fitted with different links (NB10)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(x.size), x])
    grid = np.linspace(x.min(), x.max(), 200)
    Xg = np.column_stack([np.ones(grid.size), grid])
    labels = {
        "binomial": "ロジスティック(logit リンク)",
        "gaussian": "線形確率モデル(恒等リンク)",
    }
    traces: list[go.Scatter] = [
        go.Scatter(x=x, y=y, mode="markers", marker={"size": 5, "opacity": 0.4}, name="観測")
    ]
    for family in families:
        fit = glm.irls(X, y, family=family)
        eta = Xg @ fit.params
        mu = 1.0 / (1.0 + np.exp(-eta)) if family == "binomial" else eta
        traces.append(go.Scatter(x=grid, y=mu, mode="lines", name=labels.get(family, family)))
    fig = go.Figure(data=traces)
    fig.add_hline(y=0.0, line={"color": "grey", "dash": "dot"})
    fig.add_hline(y=1.0, line={"color": "grey", "dash": "dot"})
    return apply_defaults(
        fig,
        title="リンク関数が確率を [0, 1] に収める",
        xaxis_title="説明変数",
        yaxis_title="P(y = 1)",
    )


def irls_convergence(
    X: np.ndarray, y: np.ndarray, family: str = "binomial", max_iter: int = 8
) -> go.Figure:
    """Parameter estimates against IRLS iteration count (NB10)."""
    X = np.asarray(X, dtype=float)
    paths = [[] for _ in range(X.shape[1])]
    iters = list(range(1, max_iter + 1))
    for it in iters:
        fit = glm.irls(X, y, family=family, max_iter=it, tol=0.0)
        for j, value in enumerate(fit.params):
            paths[j].append(float(value))
    final = glm.irls(X, y, family=family)
    fig = go.Figure(
        data=[
            go.Scatter(x=iters, y=path, mode="lines+markers", name=f"beta[{j}]")
            for j, path in enumerate(paths)
        ]
    )
    for value in final.params:
        fig.add_hline(y=float(value), line={"color": "grey", "dash": "dot"})
    return apply_defaults(
        fig,
        title=f"IRLS の収束 — {final.n_iter} 反復で収束",
        xaxis_title="反復回数",
        yaxis_title="係数の推定値",
    )
