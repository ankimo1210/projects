"""irp.visualization — Plotly figures + an offline, self-contained HTML report.

Figure builders (:mod:`~irp.visualization.figures`) turn the platform's own
objects (BacktestResult, the compare metrics frame, an IC Series, a cost sweep)
into styled Plotly figures; :func:`~irp.visualization.report.strategy_report`
assembles them into one HTML file that opens with no network (plotly.js embedded
inline). Everything is shown next to a baseline — including failures.
"""

from __future__ import annotations

from .figures import (
    cost_sensitivity,
    drawdown,
    equity_curves,
    ic_bar,
    metrics_table,
    returns_histogram,
    rolling_sharpe,
)
from .report import build_report, strategy_report
from .theme import style

__all__ = [
    "build_report",
    "cost_sensitivity",
    "drawdown",
    "equity_curves",
    "ic_bar",
    "metrics_table",
    "returns_histogram",
    "rolling_sharpe",
    "strategy_report",
    "style",
]
