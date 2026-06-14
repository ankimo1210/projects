"""Causal market-regime labels — volatility states and trend direction.

Regime detection is easy to do with look-ahead (fit a 2-state model on the whole
sample, then "discover" the crisis you already knew about). These detectors stay
**causal**: the volatility state at date ``t`` buckets the trailing realized vol
against quantile thresholds estimated from history **up to ``t`` only** (expanding),
and the trend state compares a fast vs a slow trailing moving average. So the label
at ``t`` never moves when future data arrives — verified by the tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def vol_regime(
    returns: pd.Series,
    *,
    lookback: int = 21,
    n_states: int = 3,
    min_history: int = 252,
) -> pd.Series:
    """Causal volatility-regime labels ``0..n_states-1`` (0 = calm).

    The trailing realized vol (``lookback``-bar std) at each date is bucketed by
    expanding quantile thresholds computed from all prior realized-vol values, so
    no future information sets the cut points. The first ``min_history`` bars are
    NaN (not enough history to place thresholds).
    """
    if n_states < 2:
        raise ValueError("n_states must be >= 2")
    rv = returns.rolling(lookback).std()
    qs = np.linspace(0.0, 1.0, n_states + 1)[1:-1]  # interior quantile cut points
    out = pd.Series(np.nan, index=returns.index, dtype="float64")
    rv_values = rv.to_numpy()
    for i in range(len(rv)):
        if i < min_history or np.isnan(rv_values[i]):
            continue
        past = rv_values[:i][~np.isnan(rv_values[:i])]  # strictly prior, causal
        if len(past) < n_states:
            continue
        thresholds = np.quantile(past, qs)
        out.iloc[i] = float(np.searchsorted(thresholds, rv_values[i], side="right"))
    return out.rename("vol_regime")


def trend_regime(price: pd.Series, *, fast: int = 50, slow: int = 200) -> pd.Series:
    """Causal trend label: ``+1`` when fast MA ≥ slow MA (bull), else ``-1`` (bear)."""
    ma_fast = price.rolling(fast).mean()
    ma_slow = price.rolling(slow).mean()
    sign = np.where(ma_fast >= ma_slow, 1.0, -1.0)
    out = pd.Series(sign, index=price.index, dtype="float64")
    out[ma_slow.isna()] = np.nan  # undefined until the slow window fills
    return out.rename("trend_regime")


def regime_summary(returns: pd.Series, regime: pd.Series, *, periods: int = 252) -> pd.DataFrame:
    """Per-regime return statistics: count, annualized mean, vol and Sharpe.

    Rows are sorted by regime label, so for a vol regime the table reads calm→turbulent.
    """
    df = pd.DataFrame({"r": returns, "regime": regime}).dropna()
    rows = {}
    for state, g in df.groupby("regime"):
        mean = g["r"].mean() * periods
        vol = g["r"].std() * np.sqrt(periods)
        rows[float(state)] = {
            "count": len(g),
            "mean": mean,
            "vol": vol,
            "sharpe": mean / vol if vol else np.nan,
        }
    out = pd.DataFrame(rows).T[["count", "mean", "vol", "sharpe"]]
    out.index.name = "regime"
    return out.sort_index()
