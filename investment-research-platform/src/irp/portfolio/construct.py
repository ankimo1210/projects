"""Portfolio constructors (single cross-section).

Each takes the inputs it needs (a vol/cov estimate, optionally expected returns)
and returns a raw weight Series; :func:`~irp.portfolio.constraints.apply_constraints`
then projects it onto the feasible set. These replace the crude
``long_short_quantile`` with proper, comparable weighting schemes.

  * ``equal_weight`` / ``inverse_volatility`` — naive baselines.
  * ``risk_parity`` — equal risk contribution (SLSQP).
  * ``min_variance`` — Σ⁻¹·1 (global minimum variance).
  * ``mean_variance`` — Σ⁻¹·μ (tangency direction; μ is the expected-return proxy).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def equal_weight(assets, *, gross: float = 1.0) -> pd.Series:
    assets = list(assets)
    return pd.Series(gross / len(assets), index=assets)


def inverse_volatility(vol: pd.Series) -> pd.Series:
    """Weights ∝ 1/volatility (risk parity if assets were uncorrelated)."""
    inv = 1.0 / vol.replace(0.0, np.nan)
    inv = inv.dropna()
    return inv / inv.sum()


def _pinv(cov: pd.DataFrame) -> np.ndarray:
    return np.linalg.pinv(cov.to_numpy())


def min_variance(cov: pd.DataFrame) -> pd.Series:
    """Global minimum-variance weights ∝ Σ⁻¹·1 (may go short)."""
    inv = _pinv(cov)
    ones = np.ones(cov.shape[0])
    raw = inv @ ones
    w = raw / raw.sum() if raw.sum() != 0 else raw
    return pd.Series(w, index=cov.index)


def mean_variance(mu: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Tangency-direction weights ∝ Σ⁻¹·μ (max-Sharpe direction; gross-normalized)."""
    assets = cov.index
    m = mu.reindex(assets).fillna(0.0).to_numpy()
    raw = _pinv(cov) @ m
    g = np.abs(raw).sum()
    w = raw / g if g != 0 else raw
    return pd.Series(w, index=assets)


def risk_parity(cov: pd.DataFrame) -> pd.Series:
    """Equal-risk-contribution (long-only, sums to 1) via SLSQP.

    Minimizes the dispersion of the *fractional* risk contributions
    ``w_i·(Σw)_i / Σ_j w_j·(Σw)_j``. Normalizing to fractions keeps the objective
    O(1) and scale-invariant — otherwise a tiny covariance (e.g. daily returns,
    entries ~1e-4) makes the objective numerically ~0 and the optimizer stalls at
    the equal-weight start.
    """
    sigma = cov.to_numpy()
    n = sigma.shape[0]

    def obj(w):
        rc = w * (sigma @ w)
        total = rc.sum()
        if total <= 0:
            return 1.0
        frac = rc / total
        return float(((frac - frac.mean()) ** 2).sum())

    res = minimize(
        obj,
        np.full(n, 1.0 / n),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    return pd.Series(res.x, index=cov.index)


def risk_contributions(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Each asset's share of portfolio variance (sums to 1) — to inspect balance."""
    w = weights.reindex(cov.index).fillna(0.0).to_numpy()
    sigma = cov.to_numpy()
    rc = w * (sigma @ w)
    total = rc.sum()
    return pd.Series(rc / total if total else rc, index=cov.index)
