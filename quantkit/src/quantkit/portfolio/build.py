"""Build a weight panel over time from a signal, ready for the backtest engine.

At each rebalance date we use only trailing data (covariance/vol from the last
``lookback`` bars, expected-return proxy = the signal score at that date), build
weights with the chosen method, project them onto the constraints, and hold them
until the next rebalance. Everything is causal: estimates use data up to the
rebalance date and the engine then lags the held weights by one more bar.
"""

from __future__ import annotations

import pandas as pd

from . import construct
from .constraints import Constraints, apply_constraints

_METHODS = {"equal", "inverse_vol", "risk_parity", "min_variance", "mean_variance"}


def _weights_at(method, window, score_row, assets):
    vol = window.std(ddof=1)
    cov = window.cov()
    if method == "equal":
        return construct.equal_weight(assets)
    if method == "inverse_vol":
        return construct.inverse_volatility(vol[assets])
    if method == "risk_parity":
        return construct.risk_parity(cov.loc[assets, assets])
    if method == "min_variance":
        return construct.min_variance(cov.loc[assets, assets])
    if method == "mean_variance":
        if score_row is None:
            raise ValueError("mean_variance needs a signal score (pass `scores`)")
        return construct.mean_variance(score_row[assets], cov.loc[assets, assets])
    raise ValueError(f"unknown method {method!r}; choose from {sorted(_METHODS)}")


def build_weights(
    returns: pd.DataFrame,
    *,
    method: str = "risk_parity",
    scores: pd.DataFrame | None = None,
    constraints: Constraints | None = None,
    lookback: int = 63,
    rebalance: str = "ME",
    min_assets: int = 2,
) -> pd.DataFrame:
    """Construct a held weight panel (dates × assets) from ``returns`` (+ ``scores``).

    Parameters
    ----------
    method : one of equal / inverse_vol / risk_parity / min_variance / mean_variance.
    scores : signal score panel (required for ``mean_variance``; it is the μ proxy).
    constraints : feasibility set (defaults to unconstrained-ish ``Constraints()``).
    lookback : trailing window (bars) for covariance/vol estimation.
    rebalance : pandas offset alias for rebalance dates (e.g. ``"ME"``, ``"W"``).
    min_assets : skip a rebalance date with fewer than this many usable assets.
    """
    if method not in _METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {sorted(_METHODS)}")
    constraints = constraints or Constraints()
    rebal_dates = returns.resample(rebalance).last().index
    rows = {}
    for d in rebal_dates:
        window = returns.loc[:d].tail(lookback).dropna(axis=1, how="any")
        if len(window) < max(2, lookback // 2) or window.shape[1] < min_assets:
            continue
        # resample labels are calendar period-ends (often weekends); key the
        # weights on the actual last business day in the window instead.
        d_eff = window.index[-1]
        assets = list(window.columns)
        score_row = scores.loc[d_eff] if (scores is not None and d_eff in scores.index) else None
        raw = _weights_at(method, window, score_row, assets)
        cov = window.cov()
        rows[d_eff] = apply_constraints(raw, constraints, cov=cov)
    if not rows:
        return pd.DataFrame(index=returns.index, columns=returns.columns, dtype="float64")
    target = pd.DataFrame(rows).T.reindex(columns=returns.columns)
    # hold each rebalance's weights until the next (a real portfolio behaviour)
    return target.reindex(returns.index, method="ffill")
