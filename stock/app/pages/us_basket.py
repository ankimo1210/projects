"""US index basket comparison page (DJIA / SP500 / NDX100)."""

from __future__ import annotations

from datetime import date, timedelta

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/us-basket", name="US Basket")

_COLORS = {"basket": "#1f77b4", "index": "#d62728", "etf": "#2ca02c", "futures": "#ff7f0e"}

layout = dbc.Container(
    [
        html.H4("米株インデックス: バスケット vs ETF/先物", className="mb-3"),
        html.P(
            "DJIA（価格加重・30銘柄）/ S&P500（時価総額加重・500銘柄）/ NASDAQ-100（時価総額加重・100銘柄）"
            "を選択して、構成銘柄バスケットを指数・ETF・先物と比較。",
            className="text-muted small",
        ),

        dbc.Row(
            [
                dbc.Col([html.Label("指数", className="small"),
                         dcc.Dropdown(id="us-index",
                                      options=[
                                          {"label": "Dow Jones 30 (DJIA)", "value": "DJIA"},
                                          {"label": "S&P 500", "value": "SP500"},
                                          {"label": "NASDAQ-100", "value": "NDX100"},
                                      ],
                                      value="DJIA", clearable=False)], width=3),
                dbc.Col([html.Label("開始日", className="small"),
                         dcc.DatePickerSingle(id="us-start",
                                              date=(date.today() - timedelta(days=365 * 5)).isoformat(),
                                              display_format="YYYY-MM-DD")], width=3),
                dbc.Col([html.Label("終了日", className="small"),
                         dcc.DatePickerSingle(id="us-end",
                                              date=date.today().isoformat(),
                                              display_format="YYYY-MM-DD")], width=2),
                dbc.Col([html.Label(" ", className="small d-block"),
                         dbc.Button("分析実行", id="us-run", color="primary", n_clicks=0),
                         html.Small(" SP500は2-3分かかります", className="text-muted ms-2")], width=4),
            ],
            className="mb-3",
        ),

        dcc.Loading(children=[
            html.Div(id="us-summary", className="mb-3"),
            dcc.Tabs(id="us-tabs", value="returns", children=[
                dcc.Tab(label="リターン比較", value="returns", children=[
                    html.Div([dcc.Graph(id="us-chart"),
                              html.Div(id="us-te", className="mt-3")], className="pt-3"),
                ]),
                dcc.Tab(label="ウェイト構成", value="weights", children=[
                    html.Div([
                        html.H6("現在のウェイト Top 30", className="mt-3"),
                        dcc.Graph(id="us-weight-bar"),
                        html.H6("ウェイト推移 Top 10", className="mt-4"),
                        dcc.Graph(id="us-weight-evolution"),
                        html.H6("構成銘柄テーブル", className="mt-4"),
                        html.Div(id="us-weight-table"),
                    ], className="pt-3"),
                ]),
            ]),
        ]),
    ],
    fluid=True,
    className="py-3",
)


@callback(
    Output("us-summary", "children"),
    Output("us-chart", "figure"),
    Output("us-te", "children"),
    Output("us-weight-bar", "figure"),
    Output("us-weight-evolution", "figure"),
    Output("us-weight-table", "children"),
    Input("us-run", "n_clicks"),
    State("us-index", "value"),
    State("us-start", "date"),
    State("us-end", "date"),
    prevent_initial_call=True,
)
def run(n_clicks, index_code, start, end):
    if not n_clicks:
        raise PreventUpdate

    from stockkit.analysis.basket import (
        compare_basket, compute_historical_weights,
        tracking_error, weight_summary,
    )
    from stockkit.data.us_indices import load_constituents, get_index_meta

    universe = load_constituents(index_code)
    meta = get_index_meta(index_code)
    weighting = meta["weighting"]

    benchmarks = {
        "index": meta["yf_index"],
        "etf": meta["yf_etf"],
        "futures": meta["yf_futures"],
    }

    result, px, shares = compare_basket(
        universe, start=start, end=end, weighting=weighting,
        benchmarks=benchmarks,
        shares_cache_key=index_code,
    )

    if result.empty:
        empty = go.Figure()
        return dbc.Alert("データ取得失敗", color="danger"), empty, "", empty, empty, ""

    labels = {
        "basket": f"{index_code} バスケット ({weighting})",
        "index": f"{meta['yf_index']} (指数)",
        "etf": f"{meta['yf_etf']} (ETF)",
        "futures": f"{meta['yf_futures']} (先物)",
    }

    # Summary
    last = (result.iloc[-1] * 100).round(2)
    cards = [
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.Small(labels.get(c, c), className="text-muted"),
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
                                      name=labels.get(c, c),
                                      line=dict(color=_COLORS.get(c, "#888"), width=2)))
    fig_ret.update_layout(title=f"{meta['name']} 累積リターン比較 ({start} 〜 {end})",
                          xaxis_title="日付", yaxis_title="累積リターン (%)",
                          hovermode="x unified", height=500, template="plotly_white")

    # TE
    te = tracking_error(result, vs="index")
    te_rows = [html.Tr([html.Th("対象"), html.Th(f"年率TE (vs {meta['yf_index']})")])]
    for k, v in te.items():
        te_rows.append(html.Tr([html.Td(labels.get(k, k)), html.Td(f"{v*100:.2f}%")]))
    te_table = dbc.Card(dbc.CardBody([
        html.H6("トラッキングエラー", className="text-muted"),
        html.Table(te_rows, className="table table-sm mb-0"),
    ]))

    # Weights (shares already fetched by compare_basket above)
    weights = compute_historical_weights(px, weighting=weighting, shares=shares)
    name_map = universe.set_index("ticker")["name"]
    summary_df = weight_summary(weights, names=name_map, top_n=30)

    bar_df = summary_df.copy()
    bar_df["label"] = bar_df.index + " " + bar_df["name"].astype(str).str[:30]
    fig_bar = go.Figure(go.Bar(x=(bar_df["current_weight"] * 100).round(3),
                               y=bar_df["label"], orientation="h",
                               marker_color="#1f77b4",
                               text=(bar_df["current_weight"] * 100).round(2).astype(str) + "%",
                               textposition="outside"))
    fig_bar.update_layout(height=700, yaxis=dict(autorange="reversed"),
                          xaxis_title="ウェイト (%)", template="plotly_white",
                          margin=dict(l=240))

    fig_evo = go.Figure()
    for tk in summary_df.index[:10]:
        nm = name_map.get(tk, "")
        fig_evo.add_trace(go.Scatter(x=weights.index, y=weights[tk] * 100,
                                      mode="lines", name=f"{tk} {str(nm)[:20]}",
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
