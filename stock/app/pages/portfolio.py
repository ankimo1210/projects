"""Portfolio analytics page."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dash_table, dcc, html
from stockkit.analysis import portfolio as port
from stockkit.viz import charts

dash.register_page(__name__, path="/portfolio", name="Portfolio")


layout = dbc.Container(
    [
        html.H4("Portfolio analytics", className="my-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Symbols (comma-separated)"),
                        dbc.Input(
                            id="pf-symbols",
                            value="AAPL,MSFT,NVDA,GOOGL,7203,9984,6758",
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    [
                        dbc.Label("Period"),
                        dcc.Dropdown(
                            id="pf-period",
                            options=[
                                {"label": "1Y", "value": "1y"},
                                {"label": "2Y", "value": "2y"},
                                {"label": "3Y", "value": "3y"},
                                {"label": "5Y", "value": "5y"},
                            ],
                            value="3y",
                            clearable=False,
                        ),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label(" "),
                        dbc.Button("Analyze", id="pf-run", color="primary", className="d-block"),
                    ],
                    md=2,
                ),
            ],
            className="g-2",
        ),
        dcc.Loading(
            [
                html.Div(id="pf-summary", className="mt-3"),
                dcc.Graph(id="pf-cumret"),
                dcc.Graph(id="pf-corr"),
            ],
            type="default",
        ),
    ],
    fluid=True,
)


@dash.callback(
    Output("pf-summary", "children"),
    Output("pf-cumret", "figure"),
    Output("pf-corr", "figure"),
    Input("pf-run", "n_clicks"),
    State("pf-symbols", "value"),
    State("pf-period", "value"),
    prevent_initial_call=True,
)
def analyze(_n, symbols, period):
    syms = [s.strip() for s in (symbols or "").split(",") if s.strip()]
    panel = port.price_panel(syms, period=period)
    if panel.empty:
        return dbc.Alert("No data", color="warning"), {}, {}

    summary = port.summary(panel).round(4).reset_index().rename(columns={"index": "symbol"})
    table = dash_table.DataTable(
        data=summary.to_dict("records"),
        columns=[{"name": c, "id": c} for c in summary.columns],
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "system-ui", "padding": "4px 8px"},
        style_header={"fontWeight": "bold"},
    )
    cum = charts.cumulative_returns_chart(port.cumulative_returns(panel))
    corr = charts.correlation_heatmap(port.correlation(panel))
    return table, cum, corr
