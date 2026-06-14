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


def monthly_returns_heatmap(result: BacktestResult, title: str = "Monthly returns") -> go.Figure:
    """Year × month grid of compounded monthly returns (calendar tearsheet view)."""
    r = result.returns
    monthly = (1.0 + r).resample("ME").prod() - 1.0
    grid = monthly.groupby([monthly.index.year, monthly.index.month]).sum().unstack()
    grid = grid.reindex(columns=range(1, 13))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(
        go.Heatmap(
            z=grid.to_numpy(),
            x=months,
            y=[str(y) for y in grid.index],
            colorscale="RdYlGn",
            zmid=0.0,
            text=[[f"{v:.1%}" if pd.notna(v) else "" for v in row] for row in grid.to_numpy()],
            texttemplate="%{text}",
            colorbar={"tickformat": ".0%"},
        )
    )
    fig = style(fig, title)
    fig.update_yaxes(autorange="reversed")
    return fig


def rolling_volatility(
    result: BacktestResult, window: int = 63, periods: int = 252, title: str | None = None
) -> go.Figure:
    """Rolling annualized volatility of one strategy's returns."""
    rv = result.returns.rolling(window).std(ddof=1) * np.sqrt(periods)
    fig = go.Figure(
        go.Scatter(
            x=rv.index, y=rv.to_numpy(), mode="lines", line={"color": COLORWAY[4 % len(COLORWAY)]}
        )
    )
    fig = style(fig, title or f"Rolling volatility ({window}-bar, annualized)")
    fig.update_yaxes(title="annualized vol", tickformat=".0%")
    return fig


def risk_return_scatter(compare_df: pd.DataFrame, title: str = "Risk vs return") -> go.Figure:
    """Scatter of annualized vol (x) vs annualized return (y), one labelled point per strategy.

    Expects a :func:`quantkit.backtest.compare` frame (rows include ``ann_vol`` and
    ``ann_return``, columns are strategies).
    """
    vol = compare_df.loc["ann_vol"]
    ret = compare_df.loc["ann_return"]
    fig = go.Figure(
        go.Scatter(
            x=vol.to_numpy(),
            y=ret.to_numpy(),
            text=list(compare_df.columns),
            mode="markers+text",
            textposition="top center",
            marker={"size": 12, "color": COLORWAY[: len(compare_df.columns)]},
        )
    )
    fig = style(fig, title)
    fig.update_xaxes(title="annualized vol", tickformat=".0%")
    fig.update_yaxes(title="annualized return", tickformat=".0%")
    return fig


def factor_heatmap(
    df: pd.DataFrame, title: str = "Factor exposures", zmid: float | None = 0.0
) -> go.Figure:
    """Heatmap of a rows × factors frame (PCA loadings, rolling betas, …)."""
    fig = go.Figure(
        go.Heatmap(
            z=df.to_numpy(),
            x=[str(c) for c in df.columns],
            y=[str(i) for i in df.index],
            colorscale="RdBu",
            zmid=zmid,
            colorbar={"title": "exposure"},
        )
    )
    fig = style(fig, title)
    fig.update_yaxes(autorange="reversed")
    return fig


def parameter_explorer(data, title: str = "Parameter explorer") -> go.Figure:
    """Interactive parameter-grid heatmap.

    ``data`` is either a single pivot frame (``param_x`` index × ``param_y`` columns
    of one metric) → a heatmap, or a ``{metric: pivot frame}`` mapping → a heatmap per
    metric with a dropdown (``updatemenus``) toggling which metric is shown. Fully
    offline/self-contained when embedded in the HTML report.
    """
    grids = data if isinstance(data, dict) else {"metric": data}
    names = list(grids)
    fig = go.Figure()
    for i, (name, grid) in enumerate(grids.items()):
        fig.add_trace(
            go.Heatmap(
                z=grid.to_numpy(),
                x=[str(c) for c in grid.columns],
                y=[str(r) for r in grid.index],
                colorscale="Viridis",
                visible=(i == 0),
                name=name,
                colorbar={"title": name},
            )
        )
    sample = next(iter(grids.values()))
    fig = style(fig, title)
    fig.update_xaxes(title=str(sample.columns.name or "param_y"))
    fig.update_yaxes(title=str(sample.index.name or "param_x"))
    if len(names) > 1:
        buttons = [
            {
                "label": name,
                "method": "update",
                "args": [
                    {"visible": [j == i for j in range(len(names))]},
                    {"coloraxis": {}},
                ],
            }
            for i, name in enumerate(names)
        ]
        fig.update_layout(
            updatemenus=[{"buttons": buttons, "x": 1.0, "xanchor": "right", "y": 1.15}]
        )
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
