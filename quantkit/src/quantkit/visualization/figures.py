"""Plotly figure builders for backtest results.

Each returns a styled ``plotly.graph_objects.Figure`` — usable inline in a
notebook (``fig.show()``) or embedded into the offline HTML report
(:mod:`quantkit.visualization.report`). Inputs are the objects the rest of the
platform already produces: :class:`~quantkit.backtest.engine.BacktestResult`, the
``compare`` metrics frame, an IC Series, and a cost-sweep frame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..backtest.engine import BacktestResult
from .theme import COLORWAY, style


def _equity(res) -> pd.Series:
    return res.equity if isinstance(res, BacktestResult) else pd.Series(res)


def equity_curves(results: dict, *, log_y: bool = False, title: str = "Equity curves") -> go.Figure:
    """Cumulative growth of 1 unit (net of costs) for several strategies."""
    fig = go.Figure()
    for name, res in results.items():
        eq = _equity(res)
        fig.add_trace(go.Scatter(x=eq.index, y=eq.to_numpy(), mode="lines", name=name))
    if log_y:
        fig.update_yaxes(type="log")
    fig = style(fig, title)
    fig.update_yaxes(title="growth of 1")
    return fig


def drawdown(result: BacktestResult, title: str = "Drawdown") -> go.Figure:
    """Underwater plot (peak-to-trough) of one strategy's equity curve."""
    eq = _equity(result)
    dd = eq / eq.cummax() - 1.0
    fig = go.Figure(
        go.Scatter(
            x=dd.index,
            y=dd.to_numpy(),
            fill="tozeroy",
            mode="lines",
            line={"color": COLORWAY[2]},
            name="drawdown",
        )
    )
    fig = style(fig, title)
    fig.update_yaxes(title="drawdown", tickformat=".0%")
    return fig


def metrics_table(df: pd.DataFrame, title: str = "Metrics") -> go.Figure:
    """Render a ``compare()`` frame (metrics × strategies) as a table."""

    def fmt(col):
        return [f"{v:.4g}" if isinstance(v, (int, float, np.floating)) else str(v) for v in col]

    header = ["metric", *map(str, df.columns)]
    cells = [list(df.index), *[fmt(df[c]) for c in df.columns]]
    fig = go.Figure(
        go.Table(
            header={
                "values": header,
                "fill_color": "#111",
                "font": {"color": "white"},
                "align": "left",
            },
            cells={"values": cells, "fill_color": "#fafafa", "align": "left"},
        )
    )
    return style(fig, title, height=80 + 28 * (len(df) + 1))


def returns_histogram(
    result: BacktestResult, title: str = "Daily return distribution"
) -> go.Figure:
    r = result.returns
    fig = go.Figure(go.Histogram(x=r.to_numpy(), nbinsx=60, marker={"color": COLORWAY[1]}))
    fig = style(fig, title)
    fig.update_xaxes(title="return", tickformat=".1%")
    return fig


def rolling_sharpe(
    result: BacktestResult, window: int = 126, periods: int = 252, title: str | None = None
) -> go.Figure:
    r = result.returns
    rs = (r.rolling(window).mean() / r.rolling(window).std(ddof=1)) * np.sqrt(periods)
    fig = go.Figure(go.Scatter(x=rs.index, y=rs.to_numpy(), mode="lines", name="rolling Sharpe"))
    fig.add_hline(y=0, line={"color": "rgba(0,0,0,0.25)", "dash": "dot"})
    return style(fig, title or f"Rolling Sharpe ({window}-bar)")


def ic_bar(ic: pd.Series, title: str = "Mean IC by model") -> go.Figure:
    s = ic.dropna().sort_values()
    colors = [COLORWAY[3] if v >= 0 else COLORWAY[2] for v in s]
    fig = go.Figure(
        go.Bar(x=s.to_numpy(), y=list(s.index), orientation="h", marker={"color": colors})
    )
    fig = style(fig, title)
    fig.update_xaxes(title="mean rank IC")
    return fig


def cost_sensitivity(
    df: pd.DataFrame, y: str = "sharpe", title: str = "Cost sensitivity"
) -> go.Figure:
    """Line of a metric vs cost (df indexed by cost_bps, with a ``y`` column)."""
    fig = go.Figure(
        go.Scatter(
            x=df.index,
            y=df[y].to_numpy(),
            mode="lines+markers",
            name=y,
            line={"color": COLORWAY[0]},
        )
    )
    fig = style(fig, title)
    fig.update_xaxes(title=str(df.index.name or "cost_bps"))
    fig.update_yaxes(title=y)
    return fig
