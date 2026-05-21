"""Backtest page."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, dash_table

from stockkit.analysis import backtest as bt
from stockkit.data import get_prices, normalize_symbol

dash.register_page(__name__, path="/backtest", name="Backtest")


STRATEGIES = [
    {"label": "SMA cross (fast/slow)", "value": "sma_cross"},
    {"label": "MACD cross", "value": "macd_cross"},
    {"label": "RSI mean-reversion", "value": "rsi_reversion"},
    {"label": "Donchian breakout", "value": "donchian"},
]


layout = dbc.Container(
    [
        html.H4("Backtest", className="my-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Symbol"),
                        dbc.Input(id="bt-symbol", value="SPY"),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Period"),
                        dcc.Dropdown(
                            id="bt-period",
                            options=[
                                {"label": x, "value": v}
                                for x, v in [
                                    ("1Y", "1y"),
                                    ("2Y", "2y"),
                                    ("3Y", "3y"),
                                    ("5Y", "5y"),
                                    ("10Y", "10y"),
                                ]
                            ],
                            value="5y",
                            clearable=False,
                        ),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Strategy"),
                        dcc.Dropdown(
                            id="bt-strategy",
                            options=STRATEGIES,
                            value="sma_cross",
                            clearable=False,
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Param 1 (fast / buy / window)"),
                        dbc.Input(id="bt-p1", type="number", value=50),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Param 2 (slow / sell)"),
                        dbc.Input(id="bt-p2", type="number", value=200),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label(" "),
                        dbc.Button(
                            "Run", id="bt-run", color="primary", className="d-block"
                        ),
                    ],
                    md=1,
                ),
            ],
            className="g-2",
        ),
        dcc.Loading(
            [
                html.Div(id="bt-metrics", className="mt-3"),
                dcc.Graph(id="bt-equity"),
                html.H5("Trades"),
                html.Div(id="bt-trades"),
            ],
            type="default",
        ),
    ],
    fluid=True,
)


def _build_signal(name: str, p1, p2):
    if name == "sma_cross":
        return bt.signal_sma_cross(int(p1 or 50), int(p2 or 200))
    if name == "macd_cross":
        return bt.signal_macd_cross()
    if name == "rsi_reversion":
        return bt.signal_rsi_reversion(buy=float(p1 or 30), sell=float(p2 or 55))
    if name == "donchian":
        return bt.signal_donchian(window=int(p1 or 20))
    raise ValueError(f"unknown strategy {name}")


@dash.callback(
    Output("bt-metrics", "children"),
    Output("bt-equity", "figure"),
    Output("bt-trades", "children"),
    Input("bt-run", "n_clicks"),
    State("bt-symbol", "value"),
    State("bt-period", "value"),
    State("bt-strategy", "value"),
    State("bt-p1", "value"),
    State("bt-p2", "value"),
    prevent_initial_call=True,
)
def run(_n, symbol, period, strategy, p1, p2):
    sym = normalize_symbol(symbol or "")
    if not sym:
        return dbc.Alert("Enter a symbol", color="warning"), {}, ""
    df = get_prices(sym, period=period)
    if df.empty:
        return dbc.Alert("No data", color="warning"), {}, ""

    sig = _build_signal(strategy, p1, p2)
    res = bt.run(df, sig)

    m = res.metrics
    cards = dbc.Row(
        [
            dbc.Col(_metric_card("Total return", f"{m.get('total_return', 0):.2%}"), md=2),
            dbc.Col(_metric_card("CAGR", f"{m.get('cagr', 0):.2%}"), md=2),
            dbc.Col(_metric_card("Vol", f"{m.get('annual_vol', 0):.2%}"), md=2),
            dbc.Col(_metric_card("Sharpe", f"{m.get('sharpe', 0):.2f}"), md=2),
            dbc.Col(_metric_card("Max DD", f"{m.get('max_drawdown', 0):.2%}"), md=2),
            dbc.Col(_metric_card("Bars", f"{int(m.get('bars', 0))}"), md=2),
        ],
        className="mb-3",
    )

    # Equity vs buy-and-hold
    bh = (df["close"] / df["close"].iloc[0]) * res.equity.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res.equity.index, y=res.equity, name="Strategy"))
    fig.add_trace(go.Scatter(x=bh.index, y=bh, name="Buy & Hold", line=dict(dash="dot")))
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=40, r=20, t=30, b=20),
        title=f"{sym} — {strategy}",
    )

    trades = res.trades
    if trades.empty:
        trades_view = html.P("No closed trades.")
    else:
        t = trades.copy()
        for c in ("entry_date", "exit_date"):
            if c in t.columns:
                t[c] = t[c].astype(str)
        if "return" in t.columns:
            t["return"] = (t["return"] * 100).round(2)
        trades_view = dash_table.DataTable(
            data=t.to_dict("records"),
            columns=[{"name": c, "id": c} for c in t.columns],
            page_size=15,
            sort_action="native",
            style_cell={"fontFamily": "system-ui", "padding": "4px 8px"},
            style_header={"fontWeight": "bold"},
        )
    return cards, fig, trades_view


def _metric_card(label: str, value: str):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="text-muted small"),
                html.Div(value, className="h5 mb-0"),
            ]
        ),
        className="shadow-sm",
    )
