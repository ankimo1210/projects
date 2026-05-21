"""Nikkei 225 basket page (with JPY/USD toggle)."""

from __future__ import annotations

from datetime import date, timedelta

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/basket", name="N225 Basket")

_LABELS = {
    "basket": "現物バスケット (PAF=1近似)",
    "n225": "^N225 (現物指数)",
    "etf_1321": "1321.T (ETF)",
    "futures_nkd": "NKD=F (CME円建て先物)",
}
_COLORS = {
    "basket": "#1f77b4",
    "n225": "#d62728",
    "etf_1321": "#2ca02c",
    "futures_nkd": "#ff7f0e",
}

layout = dbc.Container(
    [
        html.H4("Nikkei 225: バスケット比較 + 構成銘柄ウェイト", className="mb-3"),
        html.P(
            "225銘柄を価格加重で買い持ちした場合のパフォーマンスを、現物指数・ETF・先物と比較。"
            "PAF=1.0仮定のため公式指数と数%の誤差があります。",
            className="text-muted small",
        ),

        dbc.Row(
            [
                dbc.Col([html.Label("開始日", className="small"),
                         dcc.DatePickerSingle(id="bk-start",
                                              date=(date.today() - timedelta(days=365 * 5)).isoformat(),
                                              display_format="YYYY-MM-DD")], width=3),
                dbc.Col([html.Label("終了日", className="small"),
                         dcc.DatePickerSingle(id="bk-end",
                                              date=date.today().isoformat(),
                                              display_format="YYYY-MM-DD")], width=3),
                dbc.Col([html.Label("通貨", className="small"),
                         dbc.RadioItems(id="bk-ccy",
                                        options=[{"label": "JPY", "value": "JPY"},
                                                 {"label": "USD", "value": "USD"}],
                                        value="JPY", inline=True)], width=2),
                dbc.Col([html.Label(" ", className="small d-block"),
                         dbc.Button("分析実行", id="bk-run", color="primary", n_clicks=0),
                         html.Small(" 5年分は30秒〜1分", className="text-muted ms-2")], width=4),
            ],
            className="mb-3",
        ),

        dcc.Loading(children=[
            html.Div(id="bk-summary", className="mb-3"),
            dcc.Tabs(id="bk-tabs", value="returns", children=[
                dcc.Tab(label="リターン比較", value="returns", children=[
                    html.Div([dcc.Graph(id="bk-chart"),
                              html.Div(id="bk-te", className="mt-3")], className="pt-3"),
                ]),
                dcc.Tab(label="ウェイト構成", value="weights", children=[
                    html.Div([
                        html.H6("現在のウェイト Top 30", className="mt-3"),
                        dcc.Graph(id="bk-weight-bar"),
                        html.H6("ウェイト推移 Top 10", className="mt-4"),
                        dcc.Graph(id="bk-weight-evolution"),
                        html.H6("構成銘柄テーブル", className="mt-4"),
                        html.Div(id="bk-weight-table"),
                    ], className="pt-3"),
                ]),
            ]),
        ]),
    ],
    fluid=True,
    className="py-3",
)


@callback(
    Output("bk-summary", "children"),
    Output("bk-chart", "figure"),
    Output("bk-te", "children"),
    Output("bk-weight-bar", "figure"),
    Output("bk-weight-evolution", "figure"),
    Output("bk-weight-table", "children"),
    Input("bk-run", "n_clicks"),
    State("bk-start", "date"),
    State("bk-end", "date"),
    State("bk-ccy", "value"),
    prevent_initial_call=True,
)
def run_compare(n_clicks, start, end, ccy):
    if not n_clicks:
        raise PreventUpdate

    from stockkit.analysis.basket import (
        compare_basket, compute_historical_weights, tracking_error, weight_summary,
    )
    from stockkit.data.nikkei225 import load_constituents

    universe = load_constituents()
    benchmarks = {"n225": "^N225", "etf_1321": "1321.T", "futures_nkd": "NKD=F"}

    result, constituent_px, _ = compare_basket(
        universe, start=start, end=end, weighting="price",
        benchmarks=benchmarks,
        to_currency=ccy if ccy == "USD" else None,
        base_ccy="JPY",
    )

    if result.empty:
        empty = go.Figure()
        return dbc.Alert("データ取得失敗", color="danger"), empty, "", empty, empty, ""

    ccy_suffix = "(USD換算)" if ccy == "USD" else "(JPY)"

    # Summary cards
    last = (result.iloc[-1] * 100).round(2)
    cards = [
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.Small(_LABELS.get(c, c), className="text-muted"),
                html.H4(f"{last[c]:+.2f}%", className=f"text-{'success' if last[c] >= 0 else 'danger'} mb-0"),
            ]), className="text-center"),
            width=3,
        ) for c in result.columns
    ]
    summary = dbc.Row(cards, className="g-2")

    # Return chart
    fig_ret = go.Figure()
    for c in result.columns:
        fig_ret.add_trace(go.Scatter(x=result.index, y=result[c] * 100, mode="lines",
                                      name=_LABELS.get(c, c),
                                      line=dict(color=_COLORS.get(c, "#888"), width=2)))
    fig_ret.update_layout(title=f"累積リターン比較 {ccy_suffix} ({start} 〜 {end})",
                          xaxis_title="日付", yaxis_title="累積リターン (%)",
                          hovermode="x unified", height=500, template="plotly_white")

    # TE
    te = tracking_error(result, vs="n225")
    te_rows = [html.Tr([html.Th("対象"), html.Th("年率TE (vs ^N225)")])]
    for k, v in te.items():
        te_rows.append(html.Tr([html.Td(_LABELS.get(k, k)), html.Td(f"{v*100:.2f}%")]))
    te_table = dbc.Card(dbc.CardBody([
        html.H6("トラッキングエラー", className="text-muted"),
        html.Table(te_rows, className="table table-sm mb-0"),
    ]))

    # Weights (use raw JPY prices for weight calculation - currency doesn't affect ratios)
    name_map = universe.set_index("ticker")["name"]
    weights = compute_historical_weights(constituent_px, weighting="price")
    summary_df = weight_summary(weights, names=name_map, top_n=30)

    bar_df = summary_df.copy()
    bar_df["label"] = bar_df.index + " " + bar_df["name"]
    fig_bar = go.Figure(go.Bar(x=(bar_df["current_weight"] * 100).round(3),
                               y=bar_df["label"], orientation="h",
                               marker_color="#1f77b4",
                               text=(bar_df["current_weight"] * 100).round(2).astype(str) + "%",
                               textposition="outside"))
    fig_bar.update_layout(height=700, yaxis=dict(autorange="reversed"),
                          xaxis_title="ウェイト (%)", template="plotly_white",
                          margin=dict(l=200))

    fig_evo = go.Figure()
    for tk in summary_df.index[:10]:
        nm = name_map.get(tk, "")
        fig_evo.add_trace(go.Scatter(x=weights.index, y=weights[tk] * 100,
                                      mode="lines", name=f"{tk} {nm}",
                                      line=dict(width=1.5)))
    fig_evo.update_layout(title="Top 10銘柄のウェイト推移",
                          xaxis_title="日付", yaxis_title="ウェイト (%)",
                          hovermode="x unified", height=500, template="plotly_white")

    table_df = summary_df.reset_index().rename(columns={"index": "ticker"})
    table_df["current_weight"] = (table_df["current_weight"] * 100).round(3)
    table_df["start_weight"] = (table_df["start_weight"] * 100).round(3)
    table_df["weight_change_bp"] = table_df["weight_change_bp"].round(1)
    table_df.columns = ["ticker", "銘柄", "現ウェイト(%)", "期初ウェイト(%)", "変化(bp)"]

    weight_table = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        sort_action="native", page_size=30,
        style_cell={"textAlign": "left", "fontSize": "0.9em"},
        style_header={"backgroundColor": "#f1f3f5", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": "{変化(bp)} > 0", "column_id": "変化(bp)"}, "color": "green"},
            {"if": {"filter_query": "{変化(bp)} < 0", "column_id": "変化(bp)"}, "color": "red"},
        ],
    )

    return summary, fig_ret, te_table, fig_bar, fig_evo, weight_table
