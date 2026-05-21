"""Per-ticker analysis page."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html

from stockkit.analysis import fundamental
from stockkit.data import get_prices, normalize_symbol
from stockkit.viz import charts

dash.register_page(__name__, path="/ticker", name="Ticker")


PERIOD_OPTIONS = [
    {"label": "3M", "value": "3mo"},
    {"label": "6M", "value": "6mo"},
    {"label": "1Y", "value": "1y"},
    {"label": "2Y", "value": "2y"},
    {"label": "5Y", "value": "5y"},
    {"label": "MAX", "value": "max"},
]


layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Input(
                        id="tk-symbol",
                        value="AAPL",
                        placeholder="AAPL or 7203",
                        type="text",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="tk-period",
                        options=PERIOD_OPTIONS,
                        value="1y",
                        clearable=False,
                    ),
                    width=2,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="tk-source",
                        options=[
                            {"label": "Auto", "value": "auto"},
                            {"label": "yfinance", "value": "yfinance"},
                            {"label": "J-Quants", "value": "jquants"},
                        ],
                        value="auto",
                        clearable=False,
                    ),
                    width=2,
                ),
                dbc.Col(
                    dbc.Button("Load", id="tk-load", color="primary", n_clicks=0),
                    width="auto",
                ),
            ],
            className="g-2 my-2",
        ),
        dcc.Loading(
            [
                html.Div(id="tk-meta", className="my-3"),
                dcc.Graph(id="tk-chart"),
                html.H5("Fundamentals", className="mt-3"),
                html.Div(id="tk-fundamentals"),
            ],
            type="default",
        ),
    ],
    fluid=True,
)


def _kv_row(k: str, v) -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(html.Strong(k), width=4),
            dbc.Col(html.Span(str(v) if v is not None else "—"), width=8),
        ],
        className="mb-1",
    )


@dash.callback(
    Output("tk-meta", "children"),
    Output("tk-chart", "figure"),
    Output("tk-fundamentals", "children"),
    Input("tk-load", "n_clicks"),
    Input("tk-symbol", "n_submit"),
    Input("tk-period", "value"),
    Input("tk-symbol", "value"),
    Input("tk-source", "value"),
    prevent_initial_call=False,
)
def on_load(_n, _ns, period, symbol, source):
    if not symbol:
        return "", {}, ""
    sym = normalize_symbol(symbol)
    df = get_prices(sym, period=period, source=source or "auto")
    if df.empty:
        return dbc.Alert(f"No data for {sym}", color="warning"), {}, ""

    snap = fundamental.snapshot(sym)

    last_close = df["close"].iloc[-1]
    chg = df["close"].pct_change().iloc[-1] * 100
    meta = dbc.Row(
        [
            dbc.Col(html.H4(snap.get("name") or sym), width=6),
            dbc.Col(
                html.Div(
                    [
                        html.Span(f"{last_close:,.2f} {snap.get('currency') or ''}  "),
                        html.Span(
                            f"{chg:+.2f}%",
                            style={
                                "color": "green" if chg >= 0 else "red",
                                "fontWeight": "bold",
                            },
                        ),
                    ]
                ),
                width=6,
                className="text-end",
            ),
        ]
    )

    fig = charts.full_dashboard(df, sym)

    fundamentals_keys = [
        ("Sector", "sector"),
        ("Industry", "industry"),
        ("Market Cap", "market_cap"),
        ("PER (TTM)", "pe"),
        ("Forward PER", "forward_pe"),
        ("PBR", "pb"),
        ("PSR", "ps"),
        ("PEG", "peg"),
        ("ROE", "roe"),
        ("ROA", "roa"),
        ("Profit Margin", "profit_margin"),
        ("Operating Margin", "operating_margin"),
        ("Revenue Growth", "revenue_growth"),
        ("Earnings Growth", "earnings_growth"),
        ("Dividend Yield", "dividend_yield"),
        ("Debt/Equity", "debt_to_equity"),
        ("Beta", "beta"),
    ]
    fund_rows = [_kv_row(label, snap.get(k)) for label, k in fundamentals_keys]
    fund = dbc.Row(
        [
            dbc.Col(fund_rows[: len(fund_rows) // 2], md=6),
            dbc.Col(fund_rows[len(fund_rows) // 2 :], md=6),
        ]
    )
    return meta, fig, fund
