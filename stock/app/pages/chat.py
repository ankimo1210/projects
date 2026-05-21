"""AI Chat page — natural-language investment analysis powered by Claude."""

from __future__ import annotations

import json

import dash
import dash_bootstrap_components as dbc
import requests as http_requests
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/chat", name="AI Chat")

_WELCOME = "こんにちは！投資分析のご質問はなんでも聞いてください。\n\nデータ取得・グラフ作成・統計分析など、その場で実行してお答えします。"


# ---------- helpers (defined before layout) ----------

def _make_user_bubble(text: str) -> html.Div:
    return html.Div(
        [
            html.Strong("You", className="text-primary"),
            html.Div(text, style={"whiteSpace": "pre-wrap", "marginTop": "4px"}),
        ],
        style={
            "background": "#d0e8ff",
            "borderRadius": "8px",
            "padding": "10px 14px",
            "alignSelf": "flex-end",
            "maxWidth": "85%",
        },
    )


def _make_ai_bubble(text: str, figures: list[str] | None = None, code_blocks: list[str] | None = None) -> html.Div:
    children: list = [
        html.Strong("AI", className="text-success"),
        html.Div(text, style={"whiteSpace": "pre-wrap", "marginTop": "4px"}),
    ]

    if code_blocks:
        for code in code_blocks:
            children.append(
                html.Details(
                    [
                        html.Summary("実行コード", style={"cursor": "pointer", "color": "#6c757d", "fontSize": "0.85em"}),
                        html.Pre(code, style={"fontSize": "0.8em", "backgroundColor": "#2d2d2d", "color": "#f8f8f2",
                                              "padding": "10px", "borderRadius": "4px", "overflowX": "auto"}),
                    ],
                    style={"marginTop": "8px"},
                )
            )

    if figures:
        import plotly.io as pio
        for fig_json in figures:
            try:
                fig = pio.from_json(fig_json)
                children.append(
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": True, "scrollZoom": True},
                        style={"marginTop": "12px"},
                    )
                )
            except Exception as e:
                children.append(html.P(f"グラフ描画エラー: {e}", className="text-danger"))

    return html.Div(
        children,
        style={
            "background": "#ffffff",
            "borderRadius": "8px",
            "padding": "10px 14px",
            "alignSelf": "flex-start",
            "maxWidth": "95%",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
        },
    )


def _make_thinking_bubble() -> html.Div:
    return html.Div(
        [
            html.Strong("AI", className="text-success"),
            html.Div(
                [dbc.Spinner(size="sm", color="success"), html.Span(" 分析中...", className="ms-2")],
                className="d-flex align-items-center mt-1",
            ),
        ],
        id="chat-thinking",
        style={
            "background": "#ffffff",
            "borderRadius": "8px",
            "padding": "10px 14px",
            "alignSelf": "flex-start",
            "maxWidth": "85%",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
        },
    )


# ---------- layout ----------

layout = dbc.Container(
    [
        dcc.Store(id="chat-history", data=[]),
        dcc.Store(id="chat-job-id", data=None),
        dcc.Interval(id="chat-poll", interval=1000, disabled=True),

        dbc.Row(
            dbc.Col(html.H4("AI Chat", className="mb-3"), width=12)
        ),

        # Message area
        dbc.Row(
            dbc.Col(
                html.Div(
                    id="chat-messages",
                    children=[_make_ai_bubble(_WELCOME)],
                    style={
                        "height": "60vh",
                        "overflowY": "auto",
                        "border": "1px solid #dee2e6",
                        "borderRadius": "8px",
                        "padding": "16px",
                        "backgroundColor": "#f8f9fa",
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "12px",
                    },
                ),
                width=12,
            ),
            className="mb-3",
        ),

        # Input row
        dbc.Row(
            [
                dbc.Col(
                    dbc.Textarea(
                        id="chat-input",
                        placeholder="メッセージを入力...",
                        style={"width": "100%", "height": "80px", "resize": "none"},
                    ),
                    width=10,
                ),
                dbc.Col(
                    dbc.Button(
                        "送信",
                        id="chat-send",
                        color="primary",
                        style={"width": "100%", "height": "80px"},
                        n_clicks=0,
                    ),
                    width=2,
                ),
            ],
            className="mb-2",
        ),

        dbc.Row(
            dbc.Col(
                html.Small(
                    "分析には数秒〜数十秒かかる場合があります。グラフはインラインで表示されます。",
                    className="text-muted",
                ),
                width=12,
            )
        ),
    ],
    fluid=True,
    className="py-3",
)


# ---------- callbacks ----------

@callback(
    Output("chat-history", "data"),
    Output("chat-job-id", "data"),
    Output("chat-poll", "disabled"),
    Output("chat-send", "disabled"),
    Output("chat-messages", "children", allow_duplicate=True),
    Output("chat-input", "value"),
    Input("chat-send", "n_clicks"),
    State("chat-input", "value"),
    State("chat-history", "data"),
    State("chat-messages", "children"),
    prevent_initial_call=True,
)
def send_message(n_clicks, message, history, current_messages):
    if not message or not message.strip():
        raise PreventUpdate

    user_msg = message.strip()

    # Build conversation for Claude (only role/content pairs)
    claude_conv = _to_claude_format(history)

    # Show user bubble + thinking spinner immediately
    new_messages = list(current_messages or []) + [
        _make_user_bubble(user_msg),
        _make_thinking_bubble(),
    ]

    # Submit job to background thread
    try:
        resp = http_requests.post(
            "http://127.0.0.1:8051/api/chat",
            json={"conversation": claude_conv, "message": user_msg},
            timeout=5,
        )
        job_id = resp.json().get("job_id")
    except Exception as e:
        new_messages[-1] = _make_ai_bubble(f"接続エラー: {e}")
        return history, None, True, False, new_messages, ""

    # Add user message to history
    updated_history = list(history or []) + [{"role": "user", "text": user_msg}]

    return updated_history, job_id, False, True, new_messages, ""


@callback(
    Output("chat-messages", "children", allow_duplicate=True),
    Output("chat-poll", "disabled", allow_duplicate=True),
    Output("chat-send", "disabled", allow_duplicate=True),
    Output("chat-history", "data", allow_duplicate=True),
    Output("chat-job-id", "data", allow_duplicate=True),
    Input("chat-poll", "n_intervals"),
    State("chat-job-id", "data"),
    State("chat-history", "data"),
    State("chat-messages", "children"),
    prevent_initial_call=True,
)
def poll_result(n_intervals, job_id, history, current_messages):
    if not job_id:
        raise PreventUpdate

    try:
        resp = http_requests.get(
            f"http://127.0.0.1:8051/api/status/{job_id}",
            timeout=3,
        )
        status = resp.json()
    except Exception:
        raise PreventUpdate

    if status["status"] == "running":
        raise PreventUpdate

    # Remove thinking bubble (last element)
    messages = list(current_messages or [])
    if messages and isinstance(messages[-1], dict) and messages[-1].get("props", {}).get("id") == "chat-thinking":
        messages = messages[:-1]

    if status["status"] == "error":
        messages.append(_make_ai_bubble(f"エラーが発生しました: {status.get('error', '不明')}"))
        return messages, True, False, history, None

    result = status.get("result") or {}
    ai_text = result.get("text", "(応答なし)")
    figures = result.get("figures", [])
    code_blocks = result.get("code_blocks", [])

    messages.append(_make_ai_bubble(ai_text, figures=figures, code_blocks=code_blocks))

    updated_history = list(history or []) + [{"role": "assistant", "text": ai_text}]

    # Clear job_id to prevent duplicate processing on extra Interval firings
    return messages, True, False, updated_history, None


# ---------- utils ----------

def _to_claude_format(history: list[dict]) -> list[dict]:
    """Convert simplified history [{role, text}] to Claude messages format."""
    result = []
    for h in (history or []):
        result.append({"role": h["role"], "content": h["text"]})
    return result
