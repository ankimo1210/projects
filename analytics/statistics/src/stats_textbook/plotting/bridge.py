"""Figures for chapters 11-12.

``capstone_three_lenses`` is the book's closing figure: one dataset, three
procedures, drawn together so the places they agree and the places they
part are both visible at once.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import plotly.graph_objects as go

from .. import bridge, datasets, intervals, regression
from .core import apply_defaults, frame_slider

__all__ = [
    "capstone_features",
    "capstone_three_lenses",
    "interval_comparison",
    "posterior_slider",
    "prior_influence",
]


def capstone_features(x: np.ndarray, degree: int = 5) -> np.ndarray:
    """Polynomial design matrix with standardised non-constant columns.

    Identical to the one analytics/report's cross-book test uses. Kept
    here so NB12 and that test cannot drift apart.
    """
    x = np.asarray(x, dtype=float)
    X = np.vander(x, degree + 1, increasing=True)
    Xs = X.copy()
    Xs[:, 1:] = (X[:, 1:] - X[:, 1:].mean(0)) / X[:, 1:].std(0)
    return Xs


def interval_comparison(cases: Sequence[tuple[int, int]]) -> go.Figure:
    """Wald confidence interval against a Jeffreys credible interval (NB11)."""
    labels, wald_x, wald_y, cred_x, cred_y = [], [], [], [], []
    for row, (k, n) in enumerate(cases):
        labels.append(f"{k}/{n}")
        p_hat = k / n
        w = intervals.wald_interval(p_hat, float(np.sqrt(p_hat * (1 - p_hat) / n)))
        c = bridge.credible_interval(k, n)
        wald_x.extend([w.lo, w.hi, None])
        wald_y.extend([row + 0.12, row + 0.12, None])
        cred_x.extend([c.lo, c.hi, None])
        cred_y.extend([row - 0.12, row - 0.12, None])
    fig = go.Figure(
        data=[
            go.Scatter(x=wald_x, y=wald_y, mode="lines", line={"width": 6}, name="Wald 信頼区間"),
            go.Scatter(
                x=cred_x, y=cred_y, mode="lines", line={"width": 6}, name="Jeffreys 信用区間"
            ),
        ]
    )
    fig.add_vline(x=1.0, line={"color": "crimson", "dash": "dot"})
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(labels))), ticktext=labels)
    return apply_defaults(
        fig,
        title="同じデータ、2 種類の区間 — 赤い破線が母数の上限 1.0",
        xaxis_title="比率 p",
        yaxis_title="観測(成功/試行)",
    )


def prior_influence(ns: Sequence[int], p_true: float = 0.7) -> go.Figure:
    """Posterior means from three priors converging on the MLE (NB11)."""
    ns = list(ns)
    labels = {
        "jeffreys": "Jeffreys 事前 Beta(0.5, 0.5)",
        "uniform": "一様事前 Beta(1, 1)",
        "strong_high": "強い事前 Beta(20, 5)(平均 0.8)",
    }
    traces = [
        go.Scatter(
            x=ns,
            y=[bridge.posterior_mean(int(p_true * n), n, *bridge.PRIORS[key]) for n in ns],
            mode="lines+markers",
            name=labels[key],
        )
        for key in ["jeffreys", "uniform", "strong_high"]
    ]
    traces.append(
        go.Scatter(
            x=ns,
            y=[p_true] * len(ns),
            mode="lines",
            line={"color": "black", "dash": "dash"},
            name=f"MLE = {p_true}",
        )
    )
    fig = go.Figure(data=traces)
    fig.update_xaxes(type="log")
    return apply_defaults(
        fig,
        title="事前分布の影響はデータが増えると消える",
        xaxis_title="標本サイズ n(対数軸)",
        yaxis_title="事後平均",
    )


def posterior_slider(k_of_n: Sequence[tuple[int, int]], prior: str = "jeffreys") -> go.Figure:
    """The posterior tightening as data accumulates (NB11)."""
    a, b = bridge.PRIORS[prior]
    grid = np.linspace(0.0, 1.0, 400)
    frames = []
    for k, n in k_of_n:
        post = bridge.beta_binomial_posterior(k, n, a, b)
        ci = bridge.credible_interval(k, n, a, b)
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(
                        x=grid,
                        y=post.pdf(grid),
                        mode="lines",
                        fill="tozeroy",
                        name=f"事後分布 95% 区間 [{ci.lo:.3f}, {ci.hi:.3f}]",
                    )
                ],
                name=f"{k}/{n}",
            )
        )
    fig = frame_slider(frames, "観測")
    return apply_defaults(
        fig, title=f"事後分布が尖っていく({prior} 事前)", xaxis_title="p", yaxis_title="密度"
    )


def capstone_three_lenses(degree: int = 5, lam: float = 1.0, seed: int = 0) -> go.Figure:
    """One dataset, three procedures (NB12).

    Frequentist least squares, the Bayesian posterior mean (which equals
    ridge with lambda = sigma^2 / sigma_w^2), and a cross-validated ridge
    standing in for the machine-learning lens.
    """
    x, y = datasets.make_capstone_dataset(seed=seed)
    phi = capstone_features(x, degree)
    grid = np.linspace(x.min(), x.max(), 300)
    phi_grid = np.vander(grid, degree + 1, increasing=True)
    raw = np.vander(x, degree + 1, increasing=True)
    phi_grid[:, 1:] = (phi_grid[:, 1:] - raw[:, 1:].mean(0)) / raw[:, 1:].std(0)

    w_ols = regression.ols(phi, y).params
    ridge = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
    w_cv, lam_cv = _cv_ridge(phi, y)

    fig = go.Figure(
        data=[
            go.Scatter(x=x, y=y, mode="markers", marker={"size": 7}, name="観測データ"),
            go.Scatter(
                x=grid,
                y=np.sin(1.5 * grid) + 0.3 * grid,
                mode="lines",
                line={"color": "black", "dash": "dot"},
                name="真の関数",
            ),
            go.Scatter(
                x=grid,
                y=phi_grid @ w_ols,
                mode="lines",
                name=f"頻度論(最小二乗、||w|| = {np.linalg.norm(w_ols):.2f})",
            ),
            go.Scatter(
                x=grid,
                y=phi_grid @ ridge,
                mode="lines",
                name=f"ベイズ(事後平均、||w|| = {np.linalg.norm(ridge):.2f})",
            ),
            go.Scatter(
                x=grid,
                y=phi_grid @ w_cv,
                mode="lines",
                line={"dash": "dash"},
                name=(
                    f"機械学習(交差検証リッジ λ={lam_cv:.3g}、||w|| = {np.linalg.norm(w_cv):.2f})"
                ),
            ),
        ]
    )
    return apply_defaults(fig, title="1 つのデータ、3 つの視点", xaxis_title="x", yaxis_title="y")


def _cv_ridge(phi: np.ndarray, y: np.ndarray, n_folds: int = 5) -> tuple[np.ndarray, float]:
    """Ridge whose penalty is chosen by k-fold cross-validation.

    Returns the coefficients and the selected penalty. The penalty is
    reported because at the book's default degree of 5 it comes out at the
    bottom of the grid (1e-4), so the machine-learning curve lands on the
    least-squares one. That coincidence is a result, not a bug -- a
    degree-5 polynomial does not overfit 40 points at this noise level, and
    cross-validation says so -- but it looks like a plotting mistake unless
    the chosen value is on the figure.
    """
    lams = np.logspace(-4, 3, 40)
    n = y.size
    folds = np.arange(n) % n_folds
    errors = []
    for lam in lams:
        err = 0.0
        for f in range(n_folds):
            tr, te = folds != f, folds == f
            w = np.linalg.solve(phi[tr].T @ phi[tr] + lam * np.eye(phi.shape[1]), phi[tr].T @ y[tr])
            err += float(((y[te] - phi[te] @ w) ** 2).sum())
        errors.append(err)
    best = float(lams[int(np.argmin(errors))])
    return np.linalg.solve(phi.T @ phi + best * np.eye(phi.shape[1]), phi.T @ y), best
