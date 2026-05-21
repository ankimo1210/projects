"""Plotly chart helpers."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from stockkit.analysis import technical


def candlestick(df: pd.DataFrame, title: str = "") -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="OHLC",
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def price_with_indicators(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Candlestick + SMA20/50/200 + Bollinger bands."""
    sma20 = technical.sma(df, 20)
    sma50 = technical.sma(df, 50)
    sma200 = technical.sma(df, 200)
    bb = technical.bollinger(df)

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        )
    )
    for s, name in [(sma20, "SMA20"), (sma50, "SMA50"), (sma200, "SMA200")]:
        fig.add_trace(go.Scatter(x=df.index, y=s, name=name, mode="lines"))
    fig.add_trace(go.Scatter(x=df.index, y=bb["upper"], name="BB upper", line=dict(dash="dot")))
    fig.add_trace(go.Scatter(x=df.index, y=bb["lower"], name="BB lower", line=dict(dash="dot")))
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=500,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def rsi_panel(df: pd.DataFrame) -> go.Figure:
    r = technical.rsi(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=r, name="RSI(14)"))
    fig.add_hline(y=70, line_dash="dot", line_color="red")
    fig.add_hline(y=30, line_dash="dot", line_color="green")
    fig.update_layout(
        template="plotly_white",
        height=200,
        yaxis_range=[0, 100],
        margin=dict(l=40, r=20, t=10, b=20),
    )
    return fig


def macd_panel(df: pd.DataFrame) -> go.Figure:
    m = technical.macd(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="MACD"))
    fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="Signal"))
    fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="Hist", opacity=0.5))
    fig.update_layout(
        template="plotly_white",
        height=220,
        margin=dict(l=40, r=20, t=10, b=20),
    )
    return fig


def full_dashboard(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Price + RSI + MACD in a 3-row stacked figure."""
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=(title, "RSI(14)", "MACD"),
    )
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    for w, name in [(20, "SMA20"), (50, "SMA50"), (200, "SMA200")]:
        fig.add_trace(
            go.Scatter(x=df.index, y=technical.sma(df, w), name=name, mode="lines"),
            row=1,
            col=1,
        )
    fig.add_trace(go.Scatter(x=df.index, y=technical.rsi(df), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    m = technical.macd(df)
    fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="Signal"), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="Hist", opacity=0.5), row=3, col=1)

    fig.update_layout(
        template="plotly_white",
        height=750,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def correlation_heatmap(corr: pd.DataFrame, title: str = "Correlation") -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
        )
    )
    fig.update_layout(title=title, template="plotly_white", height=500)
    return fig


def cumulative_returns_chart(cum: pd.DataFrame, title: str = "Cumulative returns") -> go.Figure:
    fig = go.Figure()
    for col in cum.columns:
        fig.add_trace(go.Scatter(x=cum.index, y=cum[col], name=col, mode="lines"))
    fig.update_layout(
        title=title,
        template="plotly_white",
        yaxis_tickformat=".0%",
        height=450,
    )
    return fig
