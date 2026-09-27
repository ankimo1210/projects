"""Lag-one close-to-close research approximation and prefix-only signals."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class BacktestResult:
    held_weights: pd.DataFrame
    gross_returns: pd.Series
    turnover: pd.Series
    costs: pd.Series
    net_returns: pd.Series
    equity: pd.Series


def _check_index(frame: pd.DataFrame, name: str) -> None:
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError(f"{name} index must be timezone-aware")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{name} index must be unique and ordered")
    if frame.columns.has_duplicates:
        raise ValueError(f"{name} asset columns must be unique")


def run_backtest(
    target_weights: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    commission_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> BacktestResult:
    """Apply one lag to close-decided targets; costs are charged at weight changes.

    The approximation assumes rebalancing to the desired held weights at each
    close. It does not claim actual next-open executions or drifted holdings.
    """
    _check_index(target_weights, "target_weights")
    _check_index(returns, "returns")
    if target_weights.empty or returns.empty:
        raise ValueError("empty backtest input")
    if target_weights.attrs.get("timing") not in (None, "decision_close"):
        raise ValueError("target_weights must be unlagged close decisions")
    if not target_weights.index.equals(returns.index):
        raise ValueError("target and return timestamps must match exactly")
    if set(target_weights.columns) != set(returns.columns) or not len(returns.columns):
        raise ValueError("asset columns must match exactly and be nonempty")
    if any(not np.isfinite(v) or v < 0 for v in (commission_bps, slippage_bps)):
        raise ValueError("cost basis points must be finite and nonnegative")
    targets = target_weights[returns.columns].astype(float)
    asset_returns = returns.astype(float)
    if not np.isfinite(targets.to_numpy()).all():
        raise ValueError("target weights must be finite")
    held = targets.shift(1).fillna(0.0)
    held.attrs["timing"] = "held"
    missing_held = ~np.isfinite(asset_returns) & held.ne(0.0)
    if missing_held.to_numpy().any():
        raise ValueError("held return is missing or nonfinite")
    gross = (held * asset_returns.where(held.ne(0.0), 0.0)).sum(axis=1)
    previous = held.shift(1).fillna(0.0)
    turnover = (held - previous).abs().sum(axis=1)
    costs = turnover * ((commission_bps + slippage_bps) / 10_000.0)
    net = gross - costs
    if (net <= -1.0).any():
        raise ValueError("net return exhausts equity")
    equity = (1.0 + net).cumprod()
    return BacktestResult(
        held_weights=held,
        gross_returns=gross,
        turnover=turnover,
        costs=costs,
        net_returns=net,
        equity=equity,
    )


def run_prefix_strategy(
    prices: pd.DataFrame, strategy: Callable[[pd.DataFrame], pd.Series]
) -> pd.DataFrame:
    """Call a strategy once per close with a detached historical prefix only."""
    _check_index(prices, "prices")
    if not len(prices) or not len(prices.columns):
        raise ValueError("prices must have observations and assets")
    rows: list[pd.Series] = []
    for index in range(len(prices)):
        prefix = prices.iloc[: index + 1].copy(deep=True)
        target = strategy(prefix)
        if not isinstance(target, pd.Series) or set(target.index) != set(prices.columns):
            raise ValueError("strategy must return one target weight per asset")
        ordered = target.reindex(prices.columns).astype(float)
        if not np.isfinite(ordered.to_numpy()).all():
            raise ValueError("strategy target weights must be finite")
        rows.append(ordered)
    result = pd.DataFrame(rows, index=prices.index, columns=prices.columns)
    result.attrs["timing"] = "decision_close"
    return result
