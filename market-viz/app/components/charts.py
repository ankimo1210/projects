"""Reusable Plotly chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DARK_TEMPLATE = "plotly_dark"


def candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    show_volume: bool = True,
    ma_windows: list[int] | None = None,
) -> go.Figure:
    """OHLCV candlestick with optional MA overlays."""
    rows = 2 if show_volume else 1
    row_heights = [0.75, 0.25] if show_volume else [1.0]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=ticker,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    if ma_windows:
        colors = ["#ffeb3b", "#2196f3", "#ff9800"]
        for i, w in enumerate(ma_windows):
            ma = df["close"].rolling(w).mean()
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=ma,
                    name=f"MA{w}",
                    line=dict(color=colors[i % len(colors)], width=1),
                ),
                row=1,
                col=1,
            )

    if show_volume and "volume" in df.columns:
        colors_vol = [
            "#26a69a" if c >= o else "#ef5350"
            for c, o in zip(df["close"], df["open"], strict=False)
        ]
        fig.add_trace(
            go.Bar(
                x=df["timestamp"],
                y=df["volume"],
                name="Volume",
                marker_color=colors_vol,
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        template=DARK_TEMPLATE,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        height=500,
        title_text=ticker,
    )
    return fig


def line_chart(
    series_dict: dict[str, pd.Series],
    title: str = "",
    yformat: str = ".2%",
    height: int = 350,
) -> go.Figure:
    fig = go.Figure()
    for name, s in series_dict.items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, mode="lines"))
    fig.update_layout(
        template=DARK_TEMPLATE,
        title_text=title,
        height=height,
        yaxis_tickformat=yformat,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
    )
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Correlation Heatmap") -> go.Figure:
    fig = go.Figure(
        go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns.tolist(),
            y=corr_matrix.index.tolist(),
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr_matrix.round(2).values,
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False,
        )
    )
    fig.update_layout(
        template=DARK_TEMPLATE,
        title_text=title,
        height=450,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def equity_chart(equity: pd.Series, title: str = "Equity Curve") -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=equity.index,
            y=equity.values,
            name="Strategy",
            fill="tozeroy",
            line_color="#26a69a",
        )
    )
    fig.update_layout(
        template=DARK_TEMPLATE,
        title_text=title,
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def drawdown_chart(equity: pd.Series) -> go.Figure:
    peak = equity.cummax()
    dd = (equity - peak) / peak * 100
    fig = go.Figure(
        go.Scatter(
            x=dd.index,
            y=dd.values,
            name="Drawdown (%)",
            fill="tozeroy",
            line_color="#ef5350",
        )
    )
    fig.update_layout(
        template=DARK_TEMPLATE,
        title_text="Drawdown (%)",
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig
