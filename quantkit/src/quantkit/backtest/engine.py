"""Vectorized backtest engine.

Given target ``weights`` (from a signal/model, decided at the close of bar ``t``)
and per-bar asset ``returns``, the engine:

  1. **lags** the weights by ``lag`` bars so a decision at ``t`` is held from
     ``t+lag`` — never earning the same-bar return it was computed from;
  2. earns ``gross[t] = Σ_i w_held[t,i] · return[t,i]``;
  3. charges costs on turnover between held weights;
  4. reports net returns, turnover, costs, and the equity curve.

No forward-fill of returns, no same-bar look-ahead. The result feeds
``quantkit.backtest.metrics`` for evaluation and baseline/benchmark comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .costs import CostModel, turnover


@dataclass
class BacktestResult:
    returns: pd.Series  # net portfolio return per bar
    gross_returns: pd.Series
    costs: pd.Series
    turnover: pd.Series
    weights: pd.DataFrame  # weights actually held (after lag)
    equity: pd.Series  # cumulative (1 + net).cumprod()
    meta: dict = field(default_factory=dict)

    @property
    def total_return(self) -> float:
        return float(self.equity.iloc[-1] - 1.0) if len(self.equity) else float("nan")


def run_backtest(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    cost_model: CostModel | None = None,
    lag: int = 1,
) -> BacktestResult:
    """Backtest ``weights`` against asset ``returns`` (both dates × assets).

    ``weights`` are target weights decided at each bar; they are shifted by
    ``lag`` (default 1) before being applied, so the portfolio holds yesterday's
    decision today. Columns are aligned to the intersection of assets.
    """
    cost_model = cost_model or CostModel()
    assets = weights.columns.intersection(returns.columns)
    w = weights[assets].reindex(returns.index)
    rets = returns[assets]

    held = w.shift(lag)  # decision at t held from t+lag (no same-bar lookahead)
    gross = (held * rets).sum(axis=1, min_count=1)
    tov = turnover(held.fillna(0.0))
    cost = cost_model.on_turnover(tov)
    net = (gross.fillna(0.0) - cost).where(gross.notna() | (tov > 0))
    net = net.dropna()
    equity = (1.0 + net).cumprod()
    return BacktestResult(
        returns=net,
        gross_returns=gross.reindex(net.index),
        costs=cost.reindex(net.index),
        turnover=tov.reindex(net.index),
        weights=held.reindex(net.index),
        equity=equity,
        meta={"lag": lag, "cost_per_unit": cost_model.per_unit, "assets": list(assets)},
    )


def rebalanced(weights: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Hold target weights between rebalance dates (sample at ``rule``, then hold).

    ``rule`` is a pandas offset alias (e.g. ``"ME"`` month-end, ``"W"`` weekly).
    Forward-holding a chosen target between rebalances is a real portfolio
    behaviour, not data fabrication — but note the held book then drifts from the
    daily target. Returns weights on the original index.
    """
    sampled = weights.resample(rule).last()
    return sampled.reindex(weights.index, method="ffill")


def buy_and_hold(returns: pd.DataFrame, weights: pd.Series | None = None) -> BacktestResult:
    """Baseline: fixed weights (equal-weight by default), no rebalancing cost after entry."""
    if weights is None:
        weights = pd.Series(1.0 / returns.shape[1], index=returns.columns)
    w = pd.DataFrame([weights.values] * len(returns), index=returns.index, columns=returns.columns)
    return run_backtest(w, returns, cost_model=CostModel(0.0, 0.0), lag=0)
