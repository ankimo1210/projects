"""quantkit.backtest — walk-forward backtest engine (honest evaluation).

The pieces:
  * :mod:`quantkit.backtest.split` — walk-forward folds with purge + embargo (no
    train/test leakage);
  * :mod:`quantkit.backtest.costs` — turnover-based transaction-cost model;
  * :mod:`quantkit.backtest.engine` — vectorized backtest (lagged weights, costs,
    equity curve) plus ``buy_and_hold`` and ``rebalanced`` helpers;
  * :mod:`quantkit.backtest.metrics` — annualized metrics and a ``compare`` table for
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
from .split import (
    Fold,
    combinatorial_purged,
    is_leakage_free,
    is_purged,
    n_combinatorial_folds,
    walk_forward,
)

__all__ = [
    "BacktestResult",
    "CostModel",
    "Fold",
    "annual_turnover",
    "annualized_return",
    "annualized_vol",
    "buy_and_hold",
    "combinatorial_purged",
    "compare",
    "hit_rate",
    "is_leakage_free",
    "is_purged",
    "max_drawdown",
    "n_combinatorial_folds",
    "rebalanced",
    "run_backtest",
    "sharpe",
    "sortino",
    "summary",
    "turnover",
    "walk_forward",
]
