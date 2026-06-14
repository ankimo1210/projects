"""irp.backtest — walk-forward backtest engine (honest evaluation).

The pieces:
  * :mod:`irp.backtest.split` — walk-forward folds with purge + embargo (no
    train/test leakage);
  * :mod:`irp.backtest.costs` — turnover-based transaction-cost model;
  * :mod:`irp.backtest.engine` — vectorized backtest (lagged weights, costs,
    equity curve) plus ``buy_and_hold`` and ``rebalanced`` helpers;
  * :mod:`irp.backtest.metrics` — annualized metrics and a ``compare`` table for
    strategy vs baseline vs benchmark.

Rigor: weights are lagged (no same-bar look-ahead), returns are never
forward-filled, and every strategy is meant to be reported next to a simple
baseline — including the ones that fail.
"""

from __future__ import annotations

from .costs import CostModel, turnover
from .engine import BacktestResult, buy_and_hold, rebalanced, run_backtest
from .metrics import (
    annual_turnover,
    annualized_return,
    annualized_vol,
    compare,
    hit_rate,
    max_drawdown,
    sharpe,
    sortino,
    summary,
)
from .split import Fold, is_leakage_free, walk_forward

__all__ = [
    "BacktestResult",
    "CostModel",
    "Fold",
    "annual_turnover",
    "annualized_return",
    "annualized_vol",
    "buy_and_hold",
    "compare",
    "hit_rate",
    "is_leakage_free",
    "max_drawdown",
    "rebalanced",
    "run_backtest",
    "sharpe",
    "sortino",
    "summary",
    "turnover",
    "walk_forward",
]
