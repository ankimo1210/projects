"""Private artifact-only Plotly lessons for Hull 11e GE §26.12."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "docs/validation/section-26-12/lesson-data.json"
_FAMILIES = ("contract", "payoff", "decision_tree", "prices", "convergence", "boundaries")
_REQUIRED_SOURCES = frozenset(
    {
        "hullkit/src/hullkit/_shout.py",
        "scripts/build_shout_lesson_data.py",
        "scripts/build_shout_reference.py",
        "docs/validation/section-26-12/prices.json",
        "docs/validation/section-26-12/numerical-check.json",
        "hullkit/src/hullkit/exotics.py",
    }
)
_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#86868b")
_LABELS = {
    "shout60": "宣言時株価60（原著の例）",
    "shout50": "宣言時株価50（ATM恒等式）",
    "hull-example-market": "合成市場①（r=10%, σ=40%, T=0.25年）",
    "positive-carry": "正のキャリー",
    "dividend-above-rate": "配当利回り > 金利",
    "negative-rate": "負の金利",
    "zero-carry": "ゼロキャリー（r=q）",
    "long-high-vol": "長期・高ボラティリティ",
    "near-expiry": "満期直前",
}


def _load_data(path=None):
    """Load saved numbers, refusing stale generator or pricing source hashes."""
    data = json.loads(Path(path or _DATA).read_text())
    if data["schema_version"] != 1 or data["adopted_steps"] != 1024:
        raise ValueError("unsupported shout lesson schema")
    digests = {}
    for family in _FAMILIES:
        sources = data[family].get("source_hashes", {})
        missing = _REQUIRED_SOURCES.difference(sources)
        if missing:
            raise ValueError(f"missing shout lesson source hashes: {family}: {sorted(missing)}")
        for relative, expected in sources.items():
            if relative not in digests:
                digests[relative] = hashlib.sha256((_ROOT / relative).read_bytes()).hexdigest()
            if digests[relative] != expected:
                raise ValueError(f"stale shout lesson source: {family}: {relative}")
    return data


def _meta(key, state):
    return {
        "section": "26.12",
        "figure": key,
        "scenario": state,
        "contract": "call",
        "units": {"money": "currency", "time": "years", "rates": "continuous per year"},
    }


def _finish(fig, key, states, titles, note, height=550):
    buttons = []
    for state in states:
        buttons.append(
            dict(
                label=_LABELS.get(state, state),
                method="update",
                args=[
                    {"visible": [t.meta["scenario"] == state for t in fig.data]},
                    {"title.text": titles[state], "meta": _meta(key, state)},
                ],
            )
        )
    for t in fig.data:
        t.visible = t.meta["scenario"] == states[0]
    fig.update_layout(
        template="plotly_white",
        height=height + 130,
        title=dict(text=titles[states[0]], font_size=16, y=1 - 60 / (height + 130), yanchor="top"),
        meta=_meta(key, states[0]),
        margin=dict(l=65, r=40, t=185, b=220),
        font=dict(family="Arial, sans-serif", size=12),
        legend=dict(orientation="h", y=-60 / (height - 275), yanchor="top", x=0),
        updatemenus=[
            dict(
                type="dropdown",
                buttons=buttons,
                x=1,
                xanchor="right",
                y=1 + 80 / (height - 275),
                yanchor="top",
            )
        ]
        if len(states) > 1
        else [],
    )
    fig.add_annotation(
        x=0,
        y=0,
        yshift=-120,
        yanchor="top",
        xref="paper",
        yref="paper",
        text=note,
        showarrow=False,
        align="left",
        xanchor="left",
        font_size=11,
    )
    return fig


def _trace_meta(role, state):
    return dict(role=role, scenario=state, contract="call")


def _payoff_figure():
    fig = go.Figure()
    terminal = np.arange(30.0, 101.0)
    titles = {}
    for shouted in (60, 50):
        state = f"shout{shouted}"
        cash = np.full_like(terminal, shouted - 50)
        reset = np.maximum(terminal - shouted, 0)
        values = (np.maximum(terminal - 50, 0), cash + reset, cash, reset)
        names = (
            "欧州コール（K=50）",
            "ロック後の給付",
            f"+ 確定現金 {shouted - 50}",
            f"+ 欧州コール（K={shouted}）",
        )
        for i, (role, y, name) in enumerate(
            zip(("european", "locked", "cash", "reset_call"), values, names, strict=True)
        ):
            fig.add_trace(
                go.Scatter(
                    x=terminal,
                    y=y,
                    name=name,
                    mode="lines",
                    line=dict(
                        color=_COLORS[i],
                        width=3 if i == 1 else 2,
                        dash=("dash", "solid", "dot", "dashdot")[i],
                    ),
                    meta=_trace_meta(role, state),
                    hovertemplate="満期株価=%{x:.0f}<br>給付=%{y:.2f} 通貨<extra>%{fullData.name}</extra>",
                )
            )
        titles[state] = f"Shout の満期給付：K=50、宣言時株価={shouted}"
    fig.update_xaxes(title="満期株価 S_T（通貨）")
    fig.update_yaxes(title="満期給付（通貨、現在価格ではない）")
    return _finish(
        fig,
        "shout_payoff",
        list(titles),
        titles,
        "原著の例：max(S_T−50, 10) = 10 + max(S_T−60, 0)。<br>"
        "宣言時株価 ≥ K なら原著の字義的給付と intrinsic floor は一致。50で宣言すると欧州コールと同じ。",
    )


def _decision_figure(data):
    nodes = data["decision_tree"]["data"]["tree"]["small_tree_nodes"]
    state = "positive-carry"
    fig = go.Figure()
    positions = {
        (n["step"], n["upcount"]): (n["step"], 2 * n["upcount"] - n["step"]) for n in nodes
    }
    x, y = [], []
    for n in nodes:
        if n["step"] < 3:
            for up in (0, 1):
                a = positions[n["step"], n["upcount"]]
                b = positions[n["step"] + 1, n["upcount"] + up]
                x.extend([a[0], b[0], None])
                y.extend([a[1], b[1], None])
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color="#cccccc"),
            hoverinfo="skip",
            showlegend=False,
            meta=_trace_meta("edges", state),
        )
    )
    texts = []
    for n in nodes:
        if n["action"] == "maturity":
            text = f"S={n['spot']:.2f}<br>満期給付={n['value']:.3f}"
        else:
            action = "継続" if n["action"] == "continue" else "宣言"
            text = (
                f"S={n['spot']:.2f} ｜ {action}<br>継続={n['continuation']:.3f}<br>"
                f"宣言={n['immediate']:.3f}<br>V={n['value']:.3f}<br>"
                f"現金{n['discounted_cash']:+.3f} ＋ call {n['reset_atm']:.3f}"
            )
        texts.append(text)
    fig.add_trace(
        go.Scatter(
            x=[positions[n["step"], n["upcount"]][0] for n in nodes],
            y=[positions[n["step"], n["upcount"]][1] for n in nodes],
            mode="markers+text",
            text=texts,
            textposition="middle right",
            textfont_size=11,
            marker=dict(
                size=9, color=[_COLORS[1] if n["action"] == "shout" else _COLORS[0] for n in nodes]
            ),
            customdata=nodes,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
            meta=_trace_meta("nodes", state),
        )
    )
    fig.update_xaxes(
        range=[-0.15, 4.0],
        tickvals=[0, 1, 2, 3],
        ticktext=["0", "1/3", "2/3", "1"],
        title="経過時間（年）",
    )
    fig.update_yaxes(range=[-3.6, 3.6], visible=False)
    return _finish(
        fig,
        "shout_decision",
        [state],
        {state: "残り1回の宣言権：N=3 の実ノードで後退計算"},
        "合成例 S=K=100、r=5%、q=2%、σ=20%、T=1年。数値は通貨。N=3 は手順説明用。<br>"
        "継続 = 割引した子ノード価値の期待値。宣言 = (S−K)e^(−rτ) ＋ ATM欧州call。<br>"
        "宣言しない選択も可能。宣言時の現金レッグは負にもなり、ゼロに切り上げない。",
        height=760,
    )


def _boundary_figure(data):
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.64, 0.36],
        horizontal_spacing=0.13,
        subplot_titles=("有限木の実ノード区間と独立境界 B", "同じ市場の ATM call 残差"),
    )
    titles = {}
    for case in data["boundaries"]["data"]:
        state = case["market"]
        times = case["remaining_times"]
        segx, segy = [], []
        for tau, lo, hi in zip(times, case["lower"], case["upper"], strict=True):
            segx.extend([tau, tau, None])
            segy.extend([lo, hi, None])
        for role, x, y, mode, name, color in (
            ("bracket", segx, segy, "lines", "実ノード間の幅", "#cccccc"),
            ("lower", times, case["lower"], "markers", "継続側ノード", _COLORS[0]),
            ("upper", times, case["upper"], "markers", "宣言側ノード", _COLORS[1]),
            ("reference", times, case["reference"], "lines", "独立数値境界 B", _COLORS[2]),
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode=mode,
                    name=name,
                    marker_size=4,
                    line=dict(color=color),
                    marker_color=color,
                    meta=_trace_meta(role, state),
                    hovertemplate="残存年数=%{x:.5f}<br>株価=%{y:.5f} 通貨<extra>%{fullData.name}</extra>",
                ),
                row=1,
                col=1,
            )
        conv = data["convergence"]["data"]
        residuals = [
            next(
                r["residual"]
                for r in c["rows"]
                if r["market"] == state and r["contract"] == "call" and r["spot_ratio"] == 1
            )
            for c in conv
        ]
        fig.add_trace(
            go.Scatter(
                x=[c["steps"] for c in conv],
                y=residuals,
                mode="lines+markers",
                name="ATM call：木 − 独立価格",
                meta=_trace_meta("residual", state),
                line_color=_COLORS[0],
                hovertemplate="N=%{x}<br>残差=%{y:.7f} 通貨<extra></extra>",
            ),
            row=1,
            col=2,
        )
        p = case["parameters"]
        titles[state] = (
            f"宣言境界と価格収束：{_LABELS[state]}（合成市場）<br>"
            f"<sup>S=K=100、r={p['rate']:.1%}、q={p['dividend']:.1%}、"
            f"σ={p['volatility']:.1%}、T={p['expiry']:g}年</sup>"
        )
    fig.update_xaxes(title="残存時間 τ（年）", row=1, col=1)
    fig.update_yaxes(title="株価 S（通貨）", row=1, col=1)
    fig.update_xaxes(title="木の分割数 N", tickvals=[128, 256, 512, 1024], row=1, col=2)
    fig.update_yaxes(title="価格残差（通貨）", zeroline=True, row=1, col=2)
    return _finish(
        fig,
        "shout_boundary",
        list(titles),
        titles,
        "N=1024、59層を間引き表示。縦線はノード解像度であり、連続境界の包含保証ではない。<br>"
        "正のキャリー τ=0.5：B=112.03341 > 上端111.90723（差0.12618）。高ボラの幅は約13.8–40.4。<br>"
        "root・無区間の層は除外。全42例の最大絶対残差0.003793 < 0.005は実測値で、一般的な誤差上限ではない。",
        height=640,
    )


def _comparison_figure(data):
    fig = go.Figure()
    rows = [r for r in data["prices"]["data"] if r["contract"] == "call"]
    states = list(dict.fromkeys(r["market"] for r in rows))
    titles = {}
    for state in states:
        selected = [r for r in rows if r["market"] == state]
        for i, (role, field, name) in enumerate(
            (
                ("european", "european", "欧州 call"),
                ("shout", "tree", "Shout call（N=1024）"),
                ("lookback", "fixed_lookback", "固定行使価格 lookback call"),
            )
        ):
            if any(r[field] is None for r in selected):
                continue
            fig.add_trace(
                go.Bar(
                    x=[r["spot"] for r in selected],
                    y=[r[field] for r in selected],
                    name=name,
                    marker_color=_COLORS[i],
                    meta=_trace_meta(role, state),
                    customdata=[[r["tree_residual"], r["price"]] for r in selected],
                    hovertemplate="S=%{x}<br>価格=%{y:.6f} 通貨<br>Shout残差=%{customdata[0]:.7f}<br>独立Shout価格=%{customdata[1]:.6f}<extra>%{fullData.name}</extra>",
                )
            )
        p = selected[0]
        extra = " ／ r=q の lookback は現API未対応・非表示" if state == "zero-carry" else ""
        titles[state] = (
            f"合成市場の call 価格比較：{_LABELS[state]}<br>"
            f"<sup>K=100、r={p['rate']:.1%}、q={p['dividend']:.1%}、"
            f"σ={p['volatility']:.1%}、T={p['expiry']:.5g}年{extra}</sup>"
        )
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="現在株価 S（通貨）", tickvals=[80, 100, 125], type="category")
    fig.update_yaxes(title="オプション価格（通貨）")
    return _finish(
        fig,
        "shout_comparison",
        states,
        titles,
        "保存済みの合成計算例（原著の掲載価格ではない）。金利・配当利回りは年率連続複利。<br>"
        "残差 = N=1024のShout価格 − 独立数値参照。r=q のlookbackを0と表示しない。",
        height=600,
    )


def _figures():
    """Return the four ordered shared figures without invoking a pricing solver."""
    data = _load_data()
    return {
        "shout_payoff": _payoff_figure(),
        "shout_decision": _decision_figure(data),
        "shout_boundary": _boundary_figure(data),
        "shout_comparison": _comparison_figure(data),
    }
