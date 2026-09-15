"""Shared Plotly lesson figures for Hull 11e GE §26.10 binary options."""

from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ACCENT = "#d62728"
INK = "#1f77b4"
MUTED = "#86868b"


def _payoffs(terminal, strike=100.0, payout=100.0):
    """Return four binary payoffs under call >= K and put < K settlement."""
    terminal = np.asarray(terminal, dtype=float)
    call = terminal >= strike
    put = ~call
    return {
        "cash_call": np.where(call, payout, 0.0),
        "cash_put": np.where(put, payout, 0.0),
        "asset_call": np.where(call, terminal, 0.0),
        "asset_put": np.where(put, terminal, 0.0),
    }


def _cash_delta(S, K, r, sigma, T, q=0.0, payout=100.0):
    """Return vectorized positive-domain cash-call delta."""
    spot = np.asarray(S, dtype=float)
    root_t = math.sqrt(T)
    d2 = (np.log(spot / K) + (r - q - 0.5 * sigma**2) * T) / (sigma * root_t)
    density = np.exp(-0.5 * d2**2) / math.sqrt(2.0 * math.pi)
    return payout * math.exp(-r * T) * density / (spot * sigma * root_t)


def _market_meta(key, S0, K, r, sigma, T, q, payout):
    """Build stable layout metadata used by books and the browser portal."""
    return {
        "section": "26.10",
        "figure": key,
        "S0": S0,
        "K": K,
        "r": r,
        "sigma": sigma,
        "T": T,
        "q": q,
        "payout": payout,
    }


def _terminal_grid(K):
    """Return a payoff grid with browser probes and spread breakpoints."""
    points = np.linspace(0.5 * K, 1.5 * K, 201)
    required = [80.0, 100.0, 120.0, K]
    for width in (1.0, 5.0, 15.0):
        required.extend((K - width, K - width / 2.0, K + width / 2.0, K + width))
    return np.unique(np.append(points, required))


def _split_at_strike(x, y, strike):
    """Insert a Plotly gap before the actual settlement point at the strike."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    below = x < strike
    at_or_above = ~below
    split_x = [*x[below], None, *x[at_or_above]]
    split_y = [*y[below], None, *y[at_or_above]]
    return split_x, split_y


def _payoff_figure(K, payout):
    """Build the four-panel binary terminal-payoff figure."""
    titles = (
        "キャッシュ・オア・ナッシング call",
        "キャッシュ・オア・ナッシング put",
        "アセット・オア・ナッシング call",
        "アセット・オア・ナッシング put",
    )
    contracts = ("cash_call", "cash_put", "asset_call", "asset_put")
    colors = (ACCENT, INK, ACCENT, INK)
    figure = make_subplots(rows=2, cols=2, subplot_titles=titles)
    terminal = _terminal_grid(K)
    left = terminal[terminal < K]
    right = terminal[terminal > K]

    for index, (contract, title, color) in enumerate(zip(contracts, titles, colors, strict=True)):
        row, col = divmod(index, 2)
        row += 1
        col += 1
        left_values = _payoffs(left, K, payout)[contract]
        right_values = _payoffs(right, K, payout)[contract]
        actual_at_k = float(_payoffs([K], K, payout)[contract][0])
        one_sided = {
            "cash_call": 0.0,
            "cash_put": payout,
            "asset_call": 0.0,
            "asset_put": K,
        }[contract]
        for segment_index, (x, y) in enumerate(((left, left_values), (right, right_values))):
            figure.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=title,
                    legendgroup=contract,
                    showlegend=segment_index == 0,
                    line={"color": color, "width": 2.5},
                    meta={"role": "payoff", "contract": contract},
                    hovertemplate="S_T=%{x:.2f}<br>実際の給付=%{y:.2f}<extra>%{fullData.name}</extra>",
                ),
                row=row,
                col=col,
            )
        figure.add_trace(
            go.Scatter(
                x=[K],
                y=[actual_at_k],
                mode="markers",
                name=f"{title}: K の実際の決済",
                legendgroup=contract,
                showlegend=False,
                marker={"color": color, "size": 9, "symbol": "circle"},
                meta={"role": "payoff", "contract": contract},
                hovertemplate="S_T=K=%{x:g}<br>実際の給付=%{y:g}<extra></extra>",
            ),
            row=row,
            col=col,
        )
        figure.add_trace(
            go.Scatter(
                x=[K],
                y=[one_sided],
                mode="markers",
                name=f"{title}: 反対側の片側極限",
                legendgroup=contract,
                showlegend=False,
                marker={"color": color, "size": 9, "symbol": "circle-open", "line": {"width": 2}},
                meta={"role": "one_sided_limit", "contract": contract},
                hovertemplate="S_T→K の片側極限=%{y:g}<extra></extra>",
            ),
            row=row,
            col=col,
        )
        figure.add_vline(x=K, line_dash="dot", line_color=MUTED, row=row, col=col)
        figure.update_xaxes(title_text="満期原資産価格 S_T（通貨）", row=row, col=col)
        figure.update_yaxes(title_text="満期給付（通貨）", row=row, col=col)

    figure.add_annotation(
        text=(
            f"K={K:g}, Q={payout:g}（通貨）。選択した決済規約は call: S_T ≥ K、put: S_T < K。<br>"
            "正の T・σ の連続モデルでは等号の確率は 0。<br>"
            "●は K の実際の決済、○は反対側の片側極限。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.34,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": f"バイナリーの満期給付 — K={K:g}, Q={payout:g}", "x": 0.02},
        height=840,
        margin={"l": 65, "r": 25, "t": 90, "b": 240},
        legend={"orientation": "h", "x": 0.0, "y": -0.16, "yanchor": "top"},
        hovermode="x",
    )
    return figure


def _replication_figure(K):
    """Build the call/put dropdown for binary replication identities."""
    terminal = _terminal_grid(K)
    binaries = _payoffs(terminal, strike=K, payout=K)
    states = {
        "call": {
            "cash_leg": -binaries["cash_call"],
            "asset_leg": binaries["asset_call"],
            "vanilla": np.maximum(terminal - K, 0.0),
        },
        "put": {
            "cash_leg": binaries["cash_put"],
            "asset_leg": -binaries["asset_put"],
            "vanilla": np.maximum(K - terminal, 0.0),
        },
    }
    labels = {
        "cash_leg": "符号付きキャッシュ leg",
        "asset_leg": "符号付きアセット leg",
        "reconstructed": "再構成したペイオフ",
        "vanilla": "バニラ・ペイオフ",
    }
    styles = {
        "cash_leg": {"color": MUTED, "dash": "dash", "width": 2},
        "asset_leg": {"color": INK, "dash": "dot", "width": 2},
        "reconstructed": {"color": ACCENT, "width": 3},
        "vanilla": {"color": "#111111", "dash": "dash", "width": 1.5},
    }
    figure = go.Figure()
    for kind, values in states.items():
        values["reconstructed"] = values["cash_leg"] + values["asset_leg"]
        for role in ("cash_leg", "asset_leg", "reconstructed", "vanilla"):
            x_values = terminal
            y_values = values[role]
            if role in ("cash_leg", "asset_leg"):
                x_values, y_values = _split_at_strike(terminal, y_values, K)
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",
                    name=labels[role],
                    visible=kind == "call",
                    line=styles[role],
                    meta={"role": role, "kind": kind},
                    hovertemplate="S_T=%{x:.2f}<br>給付=%{y:.2f}<extra>%{fullData.name}</extra>",
                )
            )

    buttons = []
    for kind in ("call", "put"):
        buttons.append(
            {
                "label": kind,
                "method": "update",
                "args": [
                    {"visible": [trace.meta["kind"] == kind for trace in figure.data]},
                    {"title.text": f"バニラ・{kind} のバイナリー複製 — K={K:g}"},
                ],
            }
        )
    figure.add_hline(y=0.0, line_color="#c7c7c7", line_width=1)
    figure.add_vline(x=K, line_color=MUTED, line_dash="dot")
    figure.add_annotation(
        text=(
            f"K={K:g}（通貨）。cash leg の支払額は K。<br>"
            "call は asset-call − cash-call(K)、put は cash-put(K) − asset-put。<br>"
            "決済規約は call: S_T ≥ K、put: S_T < K。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.48,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": f"バニラ・call のバイナリー複製 — K={K:g}", "x": 0.02},
        xaxis_title="満期原資産価格 S_T（通貨）",
        yaxis_title="符号付き満期給付（通貨）",
        height=650,
        margin={"l": 65, "r": 25, "t": 115, "b": 240},
        legend={"orientation": "h", "x": 0.0, "y": -0.22, "yanchor": "top"},
        updatemenus=[
            {
                "type": "dropdown",
                "active": 0,
                "buttons": buttons,
                "x": 0.0,
                "xanchor": "left",
                "y": 1.03,
                "yanchor": "bottom",
            }
        ],
    )
    return figure


def _spread_figure(K):
    """Build normalized centered call-spread and butterfly payoff panels."""
    terminal = _terminal_grid(K)
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("正規化した中心 call spread", "正規化した butterfly"),
    )
    colors = (ACCENT, INK, MUTED)
    for width, color in zip((1.0, 5.0, 15.0), colors, strict=True):
        call_low = np.maximum(terminal - (K - width / 2.0), 0.0)
        call_high = np.maximum(terminal - (K + width / 2.0), 0.0)
        spread = (call_low - call_high) / width
        butterfly = (
            np.maximum(terminal - (K - width), 0.0)
            - 2.0 * np.maximum(terminal - K, 0.0)
            + np.maximum(terminal - (K + width), 0.0)
        ) / width**2
        figure.add_trace(
            go.Scatter(
                x=terminal,
                y=spread,
                mode="lines",
                name=f"中心 spread h={width:g}",
                legendgroup=f"h={width:g}",
                line={"color": color, "width": 2.5},
                meta={"role": "spread", "width": width},
                hovertemplate="S_T=%{x:.2f}<br>正規化給付=%{y:.4f}<extra>%{fullData.name}</extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=terminal,
                y=butterfly,
                mode="lines",
                name=f"butterfly h={width:g}",
                legendgroup=f"h={width:g}",
                showlegend=False,
                line={"color": color, "width": 2.5},
                meta={"role": "butterfly", "width": width},
                hovertemplate="S_T=%{x:.2f}<br>正規化給付=%{y:.4f}<extra>%{fullData.name}</extra>",
            ),
            row=1,
            col=2,
        )
    figure.add_vline(x=K, line_color=MUTED, line_dash="dot", row=1, col=1)
    figure.add_vline(x=K, line_color=MUTED, line_dash="dot", row=1, col=2)
    figure.update_xaxes(title_text="満期原資産価格 S_T（通貨）", row=1, col=1)
    figure.update_xaxes(title_text="満期原資産価格 S_T（通貨）", row=1, col=2)
    figure.update_yaxes(title_text="正規化ペイオフ（無次元）", row=1, col=1)
    figure.update_yaxes(title_text="正規化ペイオフ（1/通貨）", row=1, col=2)
    figure.add_annotation(
        text=(
            f"K={K:g}, h=1, 5, 15（通貨）。<br>"
            "中心 spread は K では 1/2。<br>"
            "デジタルへの収束は不連続点を除いて理解する。<br>"
            "butterfly は K に局在し、その価格極限は割引終端密度。<br>"
            "表示は価格密度ではなく満期のペイオフ曲線。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.32,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "バイナリーを作る狭いスプレッド — 満期ペイオフ", "x": 0.02},
        height=680,
        margin={"l": 65, "r": 25, "t": 90, "b": 220},
        legend={"orientation": "h", "x": 0.0, "y": -0.19, "yanchor": "top"},
    )
    return figure


def _delta_figure(S0, K, r, sigma, T, q, payout):
    """Build cash-call delta curves over spot for three positive expiries."""
    spots = np.unique(np.append(np.linspace(0.85 * K, 1.15 * K, 301), [S0, K, 100.0]))
    expiries = (T, 30.0 / 365.0, 1.0 / 365.0)
    figure = go.Figure()
    styles = ((ACCENT, "solid"), (INK, "dash"), (MUTED, "dot"))
    for expiry, (color, dash) in zip(expiries, styles, strict=True):
        figure.add_trace(
            go.Scatter(
                x=spots,
                y=_cash_delta(spots, K, r, sigma, expiry, q, payout),
                mode="lines",
                name=f"T={expiry:g} 年",
                line={"color": color, "dash": dash, "width": 2.5},
                meta={"role": "cash_delta", "T": expiry},
                hovertemplate="S_0=%{x:.2f}<br>cash-call Δ=%{y:.4f}<extra>%{fullData.name}</extra>",
            )
        )
    figure.add_vline(x=K, line_color=MUTED, line_dash="dot")
    figure.add_annotation(
        text=(
            f"K={K:g}, Q={payout:g}（通貨）, r={r:.2%}, q={q:.2%}, σ={sigma:.2%}（年率）, T は年。<br>"
            "すべて有限の正の T。<br>"
            "満期接近では K 近傍の delta が鋭く高くなり、K から離れると 0 に近づく。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.48,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "キャッシュ・オア・ナッシング call の delta — 満期接近", "x": 0.02},
        xaxis_title="現在の原資産価格 S_0（通貨）",
        yaxis_title="delta（給付通貨 / 原資産通貨）",
        height=650,
        margin={"l": 70, "r": 25, "t": 75, "b": 250},
        legend={"orientation": "h", "x": 0.0, "y": -0.22, "yanchor": "top"},
    )
    return figure


def _figures(S0=100.0, K=100.0, r=0.05, sigma=0.20, T=1.0, q=0.02, payout=100.0):
    """Return the four insertion-ordered figures for the §26.10 lesson."""
    figures = {
        "binary_payoffs": _payoff_figure(K, payout),
        "binary_replication": _replication_figure(K),
        "binary_spreads": _spread_figure(K),
        "binary_delta": _delta_figure(S0, K, r, sigma, T, q, payout),
    }
    for key, figure in figures.items():
        figure.layout.meta = _market_meta(key, S0, K, r, sigma, T, q, payout)
    return figures
