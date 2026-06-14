"""Performance metrics and side-by-side comparison.

A strategy is only meaningful next to a baseline and a benchmark, so
:func:`compare` lays several backtests in one table (the platform rule: always
compare to a simple baseline; report failures, not just the winner). All metrics
are annualized with ``periods`` bars/year.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import BacktestResult


def _as_returns(x) -> pd.Series:
    return x.returns if isinstance(x, BacktestResult) else pd.Series(x).dropna()


def annualized_return(returns, periods: int = 252) -> float:
    r = _as_returns(returns)
    if r.empty:
        return float("nan")
    return float((1.0 + r).prod() ** (periods / len(r)) - 1.0)


def annualized_vol(returns, periods: int = 252) -> float:
    r = _as_returns(returns)
    return float(r.std(ddof=1) * np.sqrt(periods)) if len(r) > 1 else float("nan")


def sharpe(returns, periods: int = 252, rf: float = 0.0) -> float:
    r = _as_returns(returns)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    excess = r - rf / periods
    return float(excess.mean() / r.std(ddof=1) * np.sqrt(periods))


def sortino(returns, periods: int = 252, rf: float = 0.0) -> float:
    r = _as_returns(returns)
    downside = r[r < 0]
    dd = downside.std(ddof=1)
    if len(r) < 2 or not dd or np.isnan(dd):
        return float("nan")
    excess = r - rf / periods
    return float(excess.mean() / dd * np.sqrt(periods))


def max_drawdown(returns) -> float:
    """Most negative peak-to-trough of the equity curve (<= 0)."""
    if isinstance(returns, BacktestResult):
        equity = returns.equity
    else:
        equity = (1.0 + pd.Series(returns).dropna()).cumprod()
    if equity.empty:
        return float("nan")
    return float((equity / equity.cummax() - 1.0).min())


def hit_rate(returns) -> float:
    r = _as_returns(returns)
    nonzero = r[r != 0]
    return float((nonzero > 0).mean()) if len(nonzero) else float("nan")


def annual_turnover(result: BacktestResult, periods: int = 252) -> float:
    if result.turnover.empty:
        return float("nan")
    return float(result.turnover.mean() * periods)


def summary(result, periods: int = 252) -> pd.Series:
    """One strategy's headline metrics as a Series."""
    r = _as_returns(result)
    out = {
        "ann_return": annualized_return(r, periods),
        "ann_vol": annualized_vol(r, periods),
        "sharpe": sharpe(r, periods),
        "sortino": sortino(r, periods),
        "max_drawdown": max_drawdown(result),
        "hit_rate": hit_rate(r),
        "n_periods": len(r),
    }
    if isinstance(result, BacktestResult):
        out["ann_turnover"] = annual_turnover(result, periods)
        out["total_cost"] = float(result.costs.sum())
    return pd.Series(out)


def compare(strategies: dict, periods: int = 252) -> pd.DataFrame:
    """Side-by-side metrics for several backtests/return series.

    ``strategies`` maps a label (e.g. ``"momentum"``, ``"equal_weight"``,
    ``"benchmark"``) to a :class:`BacktestResult` or a return Series. Columns are
    strategies, rows are metrics — so a strategy is read against its baselines.
    """
    cols = {name: summary(res, periods) for name, res in strategies.items()}
    return pd.DataFrame(cols)
