"""Screener page."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, dash_table

from stockkit.analysis import screener as scr

dash.register_page(__name__, path="/screener", name="Screener")


DEFAULT_UNIVERSE = (
    "AAPL,MSFT,NVDA,GOOGL,META,AMZN,TSLA,AVGO,LLY,JPM,"
    "7203,9984,6758,8306,9432,6098,6861,7974,8035,4063"
)


layout = dbc.Container(
    [
        html.H4("Screener", className="my-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Universe (comma-separated)"),
                        dbc.Textarea(
                            id="sc-universe", value=DEFAULT_UNIVERSE, rows=3
                        ),
                    ],
                    md=12,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("PER <"),
                        dbc.Input(id="sc-pe", value=40, type="number"),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("ROE >"),
                        dbc.Input(id="sc-roe", value=0.10, type="number", step=0.01),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Div Yield >"),
                        dbc.Input(id="sc-div", value=0.0, type="number", step=0.005),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Above SMA"),
                        dcc.Dropdown(
                            id="sc-sma",
                            options=[
                                {"label": "—", "value": 0},
                                {"label": "SMA50", "value": 50},
                                {"label": "SMA200", "value": 200},
                            ],
                            value=200,
                            clearable=False,
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        dbc.Label(" "),
                        dbc.Button(
                            "Run", id="sc-run", color="primary", className="d-block"
                        ),
                    ],
                    md=2,
                ),
            ],
            className="g-2 mt-2",
        ),
        dcc.Loading(html.Div(id="sc-result", className="mt-3"), type="default"),
    ],
    fluid=True,
)


@dash.callback(
    Output("sc-result", "children"),
    Input("sc-run", "n_clicks"),
    State("sc-universe", "value"),
    State("sc-pe", "value"),
    State("sc-roe", "value"),
    State("sc-div", "value"),
    State("sc-sma", "value"),
    prevent_initial_call=True,
)
def run_screen(_n, universe, pe, roe, div, sma_w):
    syms = [s.strip() for s in (universe or "").split(",") if s.strip()]
    rules = []
    if pe:
        rules.append(scr.pe_below(float(pe)))
    if roe:
        rules.append(scr.roe_above(float(roe)))
    if div and float(div) > 0:
        rules.append(scr.dividend_yield_above(float(div)))
    if sma_w:
        rules.append(scr.above_sma(int(sma_w)))

    df = scr.screen(syms, rules, period="1y")
    if df.empty:
        return dbc.Alert("No matches.", color="info")

    show = df.reset_index()
    cols = [
        "symbol", "name", "sector", "pe", "pb", "roe",
        "dividend_yield", "market_cap", "price",
    ]
    show = show[[c for c in cols if c in show.columns]]
    return dash_table.DataTable(
        data=show.to_dict("records"),
        columns=[{"name": c, "id": c} for c in show.columns],
        page_size=20,
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "system-ui", "padding": "4px 8px"},
        style_header={"fontWeight": "bold"},
    )
