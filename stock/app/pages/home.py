"""Home page."""

from __future__ import annotations

import dash
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/", name="Home")


layout = dbc.Container(
    [
        html.H2("stockkit dashboard"),
        html.P("日本株・米株の分析ツール（yfinance ベース）"),
        html.Ul(
            [
                html.Li("Ticker — 個別銘柄のテクニカル + ファンダメンタルズ"),
                html.Li("Screener — ルールで銘柄抽出"),
                html.Li("Portfolio — 複数銘柄のリターン/相関/シャープ"),
            ]
        ),
        html.P(
            "ティッカーは AAPL のような海外コード、または 7203 のような4桁日本コード。"
        ),
    ],
    className="py-3",
)
