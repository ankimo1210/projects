"""quantkit.visualization — Plotly figures + an offline, self-contained HTML report.

Figure builders (:mod:`~quantkit.visualization.figures`) turn the platform's own
objects (BacktestResult, the compare metrics frame, an IC Series, a cost sweep)
into styled Plotly figures; :func:`~quantkit.visualization.report.strategy_report`
assembles them into one HTML file that opens with no network (plotly.js embedded
inline). Everything is shown next to a baseline — including failures.
"""

from __future__ import annotations

from .figures import (
    cost_sensitivity,
    drawdown,
    equity_curves,
    factor_heatmap,
    ic_bar,
    metrics_table,
    monthly_returns_heatmap,
    parameter_explorer,
    returns_histogram,
    risk_return_scatter,
    rolling_sharpe,
    rolling_volatility,
)
from .report import build_report, comparison_dashboard, strategy_report, tearsheet
from .theme import style

__all__ = [
    "build_report",
    "comparison_dashboard",
    "cost_sensitivity",
    "drawdown",
    "equity_curves",
    "factor_heatmap",
    "ic_bar",
    "metrics_table",
    "monthly_returns_heatmap",
    "parameter_explorer",
    "returns_histogram",
    "risk_return_scatter",
    "rolling_sharpe",
    "rolling_volatility",
    "strategy_report",
    "style",
    "tearsheet",
]
