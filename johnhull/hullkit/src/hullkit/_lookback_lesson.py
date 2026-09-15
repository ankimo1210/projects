"""Shared Plotly lesson figures for Hull 11e GE §26.11 lookback options."""

from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hullkit import exotics

ACCENT = "#d62728"
INK = "#1f77b4"
GOLD = "#bc8f00"
MUTED = "#86868b"

_PATH = np.array([100.0, 112.0, 94.0, 121.0, 90.0, 105.0, 84.0, 116.0, 108.0])
_TIMES = np.linspace(0.0, 1.0, 9)
_CONTRACTS = ("floating_call", "floating_put", "fixed_call", "fixed_put")
_MARKET = {"S0": 100.0, "r": 0.05, "q": 0.02, "sigma": 0.20, "T": 1.0}


def _path_payoffs(
    prices,
    strike=100.0,
    minimum_to_date=100.0,
    maximum_to_date=100.0,
    fixing_indices=None,
):
    """Return four lookback payoffs for an observed deterministic price path."""
    path = np.asarray(prices, dtype=float)
    if path.ndim != 1 or path.size == 0:
        raise ValueError("prices must be a non-empty one-dimensional sequence")
    if fixing_indices is None:
        indices = np.arange(path.size)
    else:
        indices = np.asarray([*fixing_indices, 0, path.size - 1], dtype=int)
        if np.any(indices < 0) or np.any(indices >= path.size):
            raise ValueError("fixing_indices must refer to positions in prices")
        indices = np.unique(indices)

    observed = path[indices]
    terminal = float(path[-1])
    minimum = min(float(minimum_to_date), float(np.min(observed)))
    maximum = max(float(maximum_to_date), float(np.max(observed)))
    strike = float(strike)
    return {
        "floating_call": terminal - minimum,
        "floating_put": maximum - terminal,
        "fixed_call": max(maximum - strike, 0.0),
        "fixed_put": max(strike - minimum, 0.0),
    }


def _layout_meta(key, **state):
    return {"section": "26.11", "figure": key, **state}


def _menu(buttons, active):
    return [
        {
            "type": "dropdown",
            "active": active,
            "buttons": buttons,
            "x": 1.0,
            "xanchor": "right",
            "y": 1.16,
            "yanchor": "top",
        }
    ]


def _state_button(label, figure, state_key, state, title, meta):
    return {
        "label": label,
        "method": "update",
        "args": [
            {"visible": [trace.meta[state_key] == state for trace in figure.data]},
            {"title.text": title, "meta": meta},
        ],
    }


def _payoff_figure():
    key = "lookback_payoffs"
    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.65, 0.35],
        horizontal_spacing=0.12,
        subplot_titles=("価格経路と観測済み極値", "満期給付（価格ではない）"),
        specs=[[{"type": "xy"}, {"type": "bar"}]],
    )
    scenarios = (
        ("new", "新規契約", 100.0, 100.0),
        ("seasoned", "過去の極値あり", 80.0, 130.0),
    )
    for scenario, _label, past_minimum, past_maximum in scenarios:
        visible = scenario == "new"
        running_minimum = np.minimum.accumulate(np.minimum(_PATH, past_minimum))
        running_maximum = np.maximum.accumulate(np.maximum(_PATH, past_maximum))
        common = {"scenario": scenario}
        figure.add_trace(
            go.Scatter(
                x=_TIMES,
                y=_PATH,
                mode="lines+markers",
                name="spot path",
                line={"color": INK, "width": 2.5},
                meta={"role": "spot", **common},
                visible=visible,
                hovertemplate="t=%{x:.3f}<br>S=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=_TIMES,
                y=running_minimum,
                mode="lines",
                name="running minimum",
                line={"color": ACCENT, "dash": "dash", "width": 2},
                meta={"role": "running_min", **common},
                visible=visible,
                hovertemplate="t=%{x:.3f}<br>min=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=_TIMES,
                y=running_maximum,
                mode="lines",
                name="running maximum",
                line={"color": GOLD, "dash": "dot", "width": 2},
                meta={"role": "running_max", **common},
                visible=visible,
                hovertemplate="t=%{x:.3f}<br>max=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        payoffs = _path_payoffs(
            _PATH,
            strike=100.0,
            minimum_to_date=past_minimum,
            maximum_to_date=past_maximum,
        )
        figure.add_trace(
            go.Bar(
                x=list(payoffs),
                y=list(payoffs.values()),
                name="payoffs",
                marker_color=[INK, GOLD, ACCENT, MUTED],
                meta={"role": "payoffs", **common},
                visible=visible,
                hovertemplate="%{x}<br>給付=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=2,
        )

    buttons = []
    for scenario, label, past_minimum, past_maximum in scenarios:
        meta = _layout_meta(
            key,
            scenario=scenario,
            K=100.0,
            minimum_to_date=past_minimum,
            maximum_to_date=past_maximum,
            path="piecewise_linear",
        )
        buttons.append(
            _state_button(
                label,
                figure,
                "scenario",
                scenario,
                f"ルックバック給付 — {label}",
                meta,
            )
        )
    figure.update_xaxes(title_text="時点 t（年）", row=1, col=1)
    figure.update_xaxes(
        tickmode="array",
        tickvals=list(_CONTRACTS),
        ticktext=["floating<br>call", "floating<br>put", "fixed<br>call", "fixed<br>put"],
        row=1,
        col=2,
    )
    figure.update_yaxes(title_text="原資産価格（通貨）", row=1, col=1)
    figure.update_yaxes(title_text="満期給付（通貨）", row=1, col=2)
    figure.add_annotation(
        text=(
            "経路は決定論的な区分線形補間。今日と満期を観測に含める。<br>"
            "棒はこの経路で確定する満期給付であり、オプションの現在価格ではない。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.25,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "ルックバック給付 — 新規契約", "x": 0.02},
        meta=buttons[0]["args"][1]["meta"],
        updatemenus=_menu(buttons, active=0),
        height=560,
        margin={"l": 65, "r": 25, "t": 90, "b": 135},
        legend={"orientation": "h", "x": 0.0, "y": -0.12, "yanchor": "top"},
        hovermode="closest",
    )
    return figure


def _history_figure():
    key = "lookback_history"
    S0, r, q, sigma, T = (_MARKET[name] for name in ("S0", "r", "q", "sigma", "T"))
    minimum_grid = np.unique(np.append(np.linspace(60.0, 100.0, 17), [80.0, 85.0, 100.0]))
    maximum_grid = np.unique(np.append(np.linspace(100.0, 150.0, 21), [100.0, 120.0, 130.0]))
    figure = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.13,
        subplot_titles=("過去の最小値 m₀", "過去の最大値 M₀"),
    )
    strikes = (80.0, 100.0, 125.0)
    specs = (
        ("floating_call", minimum_grid, ACCENT, "solid", 1),
        ("fixed_put", minimum_grid, INK, "dash", 1),
        ("floating_put", maximum_grid, GOLD, "solid", 2),
        ("fixed_call", maximum_grid, MUTED, "dash", 2),
    )
    for strike in strikes:
        for contract, grid, color, dash, column in specs:
            if contract == "floating_call":
                values = [exotics.lookback_floating_call(S0, m0, r, sigma, T, q) for m0 in grid]
            elif contract == "fixed_put":
                values = [exotics.lookback_fixed_put(S0, strike, m0, r, sigma, T, q) for m0 in grid]
            elif contract == "floating_put":
                values = [exotics.lookback_floating_put(S0, M0, r, sigma, T, q) for M0 in grid]
            else:
                values = [
                    exotics.lookback_fixed_call(S0, strike, M0, r, sigma, T, q) for M0 in grid
                ]
            figure.add_trace(
                go.Scatter(
                    x=grid,
                    y=values,
                    mode="lines",
                    name=contract,
                    line={"color": color, "dash": dash, "width": 2.5},
                    meta={"role": "price", "contract": contract, "strike": strike},
                    visible=strike == 100.0,
                    hovertemplate="history=%{x:.2f}<br>現在価値=%{y:.4f}<extra>%{fullData.name}</extra>",
                ),
                row=1,
                col=column,
            )

    buttons = []
    for strike in strikes:
        meta = _layout_meta(key, **_MARKET, K=strike)
        buttons.append(
            _state_button(
                f"K={strike:g}",
                figure,
                "strike",
                strike,
                f"履歴極値が現在価値へ与える効果 — K={strike:g}",
                meta,
            )
        )
    figure.update_xaxes(title_text="過去の最小値 m₀（通貨）", row=1, col=1)
    figure.update_xaxes(title_text="過去の最大値 M₀（通貨）", row=1, col=2)
    figure.update_yaxes(title_text="現在価値（通貨）", row=1, col=1)
    figure.update_yaxes(title_text="現在価値（通貨）", row=1, col=2)
    figure.add_annotation(
        text=(
            "S₀=100 を固定し、横軸は spot ではなく過去の極値。<br>"
            "fixed put は m₀≥K で星付き履歴が K に固定され平坦になる。<br>"
            "fixed call は M₀≤K で同様に平坦になる。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.28,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "履歴極値が現在価値へ与える効果 — K=100", "x": 0.02},
        meta=buttons[1]["args"][1]["meta"],
        updatemenus=_menu(buttons, active=1),
        height=590,
        margin={"l": 68, "r": 25, "t": 90, "b": 155},
        legend={"orientation": "h", "x": 0.0, "y": -0.14, "yanchor": "top"},
        hovermode="x unified",
    )
    return figure


def _replication_figure():
    key = "lookback_replication"
    S0, r, q, sigma, T = (_MARKET[name] for name in ("S0", "r", "q", "sigma", "T"))
    minimum_to_date, maximum_to_date = 85.0, 120.0
    strikes = np.unique(np.append(np.linspace(60.0, 140.0, 161), [80.0, 100.0, 125.0]))
    figure = go.Figure()
    styles = {
        "floating_leg": (ACCENT, "dash"),
        "stock_leg": (GOLD, "dot"),
        "cash_leg": (MUTED, "dot"),
        "reconstructed": (INK, "solid"),
        "fixed": ("#2ca02c", "dash"),
    }
    for kind in ("call", "put"):
        if kind == "call":
            floating = np.array(
                [
                    exotics.lookback_floating_put(S0, max(maximum_to_date, strike), r, sigma, T, q)
                    for strike in strikes
                ]
            )
            stock = np.full_like(strikes, S0 * math.exp(-q * T))
            cash = -strikes * math.exp(-r * T)
            fixed = np.array(
                [
                    exotics.lookback_fixed_call(S0, strike, maximum_to_date, r, sigma, T, q)
                    for strike in strikes
                ]
            )
        else:
            floating = np.array(
                [
                    exotics.lookback_floating_call(S0, min(minimum_to_date, strike), r, sigma, T, q)
                    for strike in strikes
                ]
            )
            stock = np.full_like(strikes, -S0 * math.exp(-q * T))
            cash = strikes * math.exp(-r * T)
            fixed = np.array(
                [
                    exotics.lookback_fixed_put(S0, strike, minimum_to_date, r, sigma, T, q)
                    for strike in strikes
                ]
            )
        values = {
            "floating_leg": floating,
            "stock_leg": stock,
            "cash_leg": cash,
            "reconstructed": floating + stock + cash,
            "fixed": fixed,
        }
        for role, series in values.items():
            color, dash = styles[role]
            figure.add_trace(
                go.Scatter(
                    x=strikes,
                    y=series,
                    mode="lines",
                    name=role,
                    line={"color": color, "dash": dash, "width": 3 if role == "fixed" else 2},
                    meta={"role": role, "kind": kind},
                    visible=kind == "call",
                    hovertemplate="K=%{x:.2f}<br>現在価値=%{y:.4f}<extra>%{fullData.name}</extra>",
                )
            )

    buttons = []
    for kind, label in (("call", "fixed call"), ("put", "fixed put")):
        meta = _layout_meta(
            key,
            **_MARKET,
            minimum_to_date=minimum_to_date,
            maximum_to_date=maximum_to_date,
            kind=kind,
        )
        buttons.append(
            _state_button(
                label,
                figure,
                "kind",
                kind,
                f"ルックバックの評価時点における複製 — {label}",
                meta,
            )
        )
    figure.add_hline(y=0.0, line_color="#c7c7c7", line_width=1)
    figure.add_annotation(
        text=(
            "call: M*=max(M₀,K), p_fl(M*) + S₀e⁻ᑫᵀ − Ke⁻ʳᵀ。<br>"
            "put: m*=min(m₀,K), c_fl(m*) − S₀e⁻ᑫᵀ + Ke⁻ʳᵀ。<br>"
            "満期のペイオフ恒等式を無裁定評価した関係で、全レッグは評価時点の現在価値（通貨）。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.29,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "ルックバックの評価時点における複製 — fixed call", "x": 0.02},
        meta=buttons[0]["args"][1]["meta"],
        updatemenus=_menu(buttons, active=0),
        xaxis_title="行使価格 K（通貨）",
        yaxis_title="現在価値（通貨）",
        height=590,
        margin={"l": 70, "r": 25, "t": 90, "b": 160},
        legend={"orientation": "h", "x": 0.0, "y": -0.14, "yanchor": "top"},
        hovermode="x unified",
    )
    return figure


def _monitoring_figure():
    key = "lookback_monitoring"
    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.65, 0.35],
        horizontal_spacing=0.12,
        subplot_titles=("区分線形の全経路と fixing", "離散観測の満期給付"),
        specs=[[{"type": "xy"}, {"type": "bar"}]],
    )
    interval_states = (1, 2, 4, 8)
    for intervals in interval_states:
        indices = np.arange(0, 9, 8 // intervals)
        visible = intervals == 8
        common = {"intervals": intervals}
        figure.add_trace(
            go.Scatter(
                x=_TIMES,
                y=_PATH,
                mode="lines",
                name="full path",
                line={"color": INK, "width": 2.5},
                meta={"role": "spot", **common},
                visible=visible,
                hovertemplate="t=%{x:.3f}<br>S=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=_TIMES[indices],
                y=_PATH[indices],
                mode="markers",
                name="fixings",
                marker={"color": ACCENT, "size": 9, "line": {"color": "white", "width": 1}},
                meta={"role": "fixings", **common},
                visible=visible,
                hovertemplate="fixing t=%{x:.3f}<br>S=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        payoffs = _path_payoffs(_PATH, fixing_indices=indices)
        figure.add_trace(
            go.Bar(
                x=list(payoffs),
                y=list(payoffs.values()),
                name="payoffs",
                marker_color=[INK, GOLD, ACCENT, MUTED],
                meta={"role": "payoffs", **common},
                visible=visible,
                hovertemplate="%{x}<br>給付=%{y:.2f}<extra></extra>",
            ),
            row=1,
            col=2,
        )

    buttons = []
    for intervals in interval_states:
        meta = _layout_meta(
            key,
            intervals=intervals,
            K=100.0,
            minimum_to_date=100.0,
            maximum_to_date=100.0,
            path="piecewise_linear",
        )
        buttons.append(
            _state_button(
                f"{intervals}区間",
                figure,
                "intervals",
                intervals,
                f"離散 fixing とルックバック給付 — {intervals}区間",
                meta,
            )
        )
    figure.update_xaxes(title_text="時点 t（年）", row=1, col=1)
    figure.update_xaxes(
        tickmode="array",
        tickvals=list(_CONTRACTS),
        ticktext=["floating<br>call", "floating<br>put", "fixed<br>call", "fixed<br>put"],
        row=1,
        col=2,
    )
    figure.update_yaxes(title_text="原資産価格（通貨）", row=1, col=1)
    figure.update_yaxes(title_text="満期給付（通貨）", row=1, col=2)
    figure.add_annotation(
        text=(
            "今日と満期を常に fixing に含める。8区間はこの区分線形の玩具経路の極値を正確に捕捉する。<br>"
            "これは連続 GBM への収束やオプション価格精度を示す図ではない。"
        ),
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.25,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={"size": 11},
    )
    figure.update_layout(
        title={"text": "離散 fixing とルックバック給付 — 8区間", "x": 0.02},
        meta=buttons[-1]["args"][1]["meta"],
        updatemenus=_menu(buttons, active=3),
        height=560,
        margin={"l": 65, "r": 25, "t": 90, "b": 135},
        legend={"orientation": "h", "x": 0.0, "y": -0.12, "yanchor": "top"},
        hovermode="closest",
    )
    return figure


def _figures():
    """Return the four insertion-ordered figures for the §26.11 lesson."""
    return {
        "lookback_payoffs": _payoff_figure(),
        "lookback_history": _history_figure(),
        "lookback_replication": _replication_figure(),
        "lookback_monitoring": _monitoring_figure(),
    }
