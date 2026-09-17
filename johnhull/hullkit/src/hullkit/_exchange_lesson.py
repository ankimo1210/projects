"""Private artifact-only Plotly lessons for Hull 11e GE §26.14."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "docs/validation/section-26-14/lesson-data.json"
_FAMILIES = ("contract", "correlation", "rate", "american")
_REQUIRED_SOURCES = frozenset(
    {
        "hullkit/src/hullkit/exotics.py",
        "scripts/build_exchange_lesson_data.py",
        "scripts/build_exchange_reference.py",
        "docs/validation/section-26-14/prices.json",
        "docs/validation/section-26-14/numerical-check.json",
    }
)
# Distinct after the portal theme remaps #1f77b4 to ink, #d62728 to the accent and
# #2ca02c to its gray (report_builder/theme.py), so no figure loses a line.
_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#7b52ab", "#0f766e", "#86868b")
_LABELS = {
    "exchange": "交換オプション max(V−U,0)",
    "better_of": "better-of max(U,V)",
    "worse_of": "worse-of min(U,V)",
    "equal-vol-uncorrelated": "等ボラ無相関（σ=20%/20%, q=0, T=1年）",
    "equal-vol-tight": "高相関（σ=20%/20%, ρ=0.9, q_U=1%, q_V=3%, T=1年）",
    "asymmetric-vol": "非対称ボラ（σ_U=15%, σ_V=45%, ρ=0.3, T=2年）",
    "yield-on-received": "受取側に配当（σ=25%/25%, ρ=0.5, q_V=6%, T=1.5年）",
    "long-high-vol": "長期・高ボラ（σ_U=55%, σ_V=70%, ρ=−0.2, T=5年）",
}


def _load_data(path=None):
    """Load saved numbers, refusing stale generator or pricing source hashes."""
    data = json.loads(Path(path or _DATA).read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        raise ValueError("unsupported exchange lesson schema")
    digests = {}
    for family in _FAMILIES:
        sources = data[family].get("source_hashes", {})
        missing = _REQUIRED_SOURCES.difference(sources)
        if missing:
            raise ValueError(f"missing exchange lesson source hashes: {family}: {sorted(missing)}")
        for relative, expected in sources.items():
            if relative not in digests:
                digests[relative] = hashlib.sha256((_ROOT / relative).read_bytes()).hexdigest()
            if digests[relative] != expected:
                raise ValueError(f"stale exchange lesson source: {family}: {relative}")
    return data


def _meta(key, state):
    return {
        "section": "26.14",
        "figure": key,
        "scenario": state,
        "units": {"money": "currency", "time": "years", "rates": "continuous per year"},
    }


def _trace_meta(role, state):
    return {"role": role, "scenario": state}


def _finish(fig, key, states, titles, note, height=520, legend_rows=1):
    buttons = [
        dict(
            label=_LABELS.get(state, state),
            method="update",
            args=[
                {"visible": [trace.meta["scenario"] == state for trace in fig.data]},
                {"title.text": titles[state], "meta": _meta(key, state)},
            ],
        )
        for state in states
    ]
    for trace in fig.data:
        trace.visible = trace.meta["scenario"] == states[0]
    # The horizontal legend wraps on the narrower Book column; reserve its rows so the
    # note below it is never overlapped or pushed outside the figure.
    extra = 19 * (legend_rows - 1)
    fig.update_layout(
        template="plotly_white",
        height=height + 130 + extra,
        title=dict(
            text=titles[states[0]], font_size=16,
            y=1 - 60 / (height + 130 + extra), yanchor="top",
        ),
        meta=_meta(key, states[0]),
        margin=dict(l=70, r=70, t=175, b=190 + extra),
        font=dict(family="Arial, sans-serif", size=12),
        legend=dict(orientation="h", y=-52 / (height - 250), yanchor="top", x=0),
        updatemenus=[
            dict(type="dropdown", buttons=buttons, x=1, xanchor="right",
                 y=1 + 80 / (height - 250), yanchor="top")
        ]
        if len(states) > 1
        else [],
    )
    fig.add_annotation(
        x=0, y=0, yshift=-105 - extra, yanchor="top", xref="paper", yref="paper", text=note,
        showarrow=False, align="left", xanchor="left", font_size=11,
    )
    return fig


def _payoff_figure(data):
    """What the three contracts pay, and that the decomposition is an identity."""
    rows = data["contract"]["data"]["rows"]
    given = data["contract"]["data"]["terminal_u"]
    terminal = [row["terminal_v"] for row in rows]
    fig = go.Figure()
    for state in ("exchange", "better_of", "worse_of"):
        fig.add_trace(go.Scatter(
            x=terminal, y=[row["given_up"] for row in rows], mode="lines",
            name=f"渡す資産 U_T = {given:.0f}", line=dict(color=_COLORS[5], width=1.5, dash="dot"),
            meta=_trace_meta("given", state), hovertemplate="U_T %{y:.1f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=terminal, y=terminal, mode="lines", name="受け取る資産 V_T",
            line=dict(color=_COLORS[2], width=1.5, dash="dot"),
            meta=_trace_meta("received", state), hovertemplate="V_T %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=terminal, y=[row["exchange"] for row in rows], mode="lines+markers",
        name="max(V_T−U_T, 0)", line=dict(color=_COLORS[1], width=3),
        meta=_trace_meta("payoff", "exchange"),
        hovertemplate="V_T=%{x:.0f}: 給付 %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=terminal, y=[row["better_of"] for row in rows], mode="lines+markers",
        name="max(U_T, V_T)", line=dict(color=_COLORS[1], width=3),
        meta=_trace_meta("payoff", "better_of"),
        hovertemplate="V_T=%{x:.0f}: 給付 %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=terminal, y=[row["worse_of"] for row in rows], mode="lines+markers",
        name="min(U_T, V_T)", line=dict(color=_COLORS[1], width=3),
        meta=_trace_meta("payoff", "worse_of"),
        hovertemplate="V_T=%{x:.0f}: 給付 %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=terminal, y=[row["given_up"] + row["exchange"] for row in rows], mode="markers",
        name="U_T + max(V_T−U_T, 0)（分解）", marker=dict(color=_COLORS[3], size=11,
                                                          symbol="circle-open", line_width=2),
        meta=_trace_meta("decomposition", "better_of"),
        hovertemplate="分解 %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=terminal, y=[row["terminal_v"] - row["exchange"] for row in rows], mode="markers",
        name="V_T − max(V_T−U_T, 0)（分解）", marker=dict(color=_COLORS[3], size=11,
                                                          symbol="circle-open", line_width=2),
        meta=_trace_meta("decomposition", "worse_of"),
        hovertemplate="分解 %{y:.1f}<extra></extra>"))
    fig.update_layout(
        xaxis=dict(title="満期の受取資産の価値 V_T", tickvals=terminal),
        yaxis=dict(title="満期の給付"),
    )
    titles = {
        "exchange": "交換オプション：U_T を渡して V_T を受け取る権利<br>給付 max(V_T−U_T, 0)",
        "better_of": "better-of：max(U_T, V_T) = U_T + max(V_T−U_T, 0)<br>資産 U と交換オプションの合計",
        "worse_of": "worse-of：min(U_T, V_T) = V_T − max(V_T−U_T, 0)<br>資産 V から交換オプションを引いた残り",
    }
    note = (
        f"満期給付であり価格ではない。渡す資産を U_T = {given:.0f} に固定し、受け取る資産 V_T を動かした。<br>"
        "両建ての分解は恒等式なので、○印は実線にちょうど重なる（状態ごとに満期の全点で一致）。<br>"
        "通貨の交換・株式公開買付など、行使価格が固定額でなく別の資産の価値になる契約である。"
    )
    return _finish(fig, "exchange_payoff", ["exchange", "better_of", "worse_of"], titles, note,
                   legend_rows=3)


def _correlation_figure(data):
    """The price falls with rho and collapses onto the discounted forward spread."""
    fig = go.Figure()
    titles = {}
    states = []
    for family in data["correlation"]["data"]:
        state = family["market"]
        states.append(state)
        entries = family["entries"]
        correlations = [entry["correlation"] for entry in entries]
        fig.add_trace(go.Scatter(
            x=correlations, y=[entry["price"] for entry in entries], mode="lines",
            name="交換オプションの価格（式26.5）", line=dict(color=_COLORS[1], width=2.5),
            meta=_trace_meta("price", state),
            hovertemplate="ρ=%{x:.2f}: 価格 %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=correlations, y=[100.0 * entry["spread_volatility"] for entry in entries],
            mode="lines", name="比 V/U のボラティリティ σ̂（右軸）", yaxis="y2",
            line=dict(color=_COLORS[0], width=2, dash="dash"),
            meta=_trace_meta("volatility", state),
            hovertemplate="ρ=%{x:.2f}: σ̂ %{y:.2f}%<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[correlations[0], correlations[-1]],
            y=[family["forward_spread"]] * 2, mode="lines",
            name=f"割引フォワードの差 {family['forward_spread']:.4f}（σ̂→0 の極限）",
            line=dict(color=_COLORS[5], width=1.5, dash="dot"),
            meta=_trace_meta("forward", state),
            hovertemplate="フォワード差 %{y:.4f}<extra></extra>"))
        first, last = entries[0], entries[-1]
        titles[state] = (
            f"{_LABELS[state]}<br>"
            f"ρ を {first['correlation']:.2f} から {last['correlation']:.2f} に上げると"
            f"価格は {first['price']:.4f} → {last['price']:.4f}"
            f"（σ̂ は {100 * first['spread_volatility']:.1f}% → "
            f"{100 * last['spread_volatility']:.1f}%）"
        )
    fig.update_layout(
        xaxis=dict(title="2資産の相関 ρ", tickvals=[-0.95, -0.5, 0.0, 0.5, 0.95]),
        yaxis=dict(title="価格（U_0 = V_0 = 100）"),
        yaxis2=dict(title="σ̂（%）", overlaying="y", side="right", rangemode="tozero"),
    )
    note = (
        "価格を動かすのは σ_U・σ_V・ρ が作る1つの量 σ̂ = √(σ_U²+σ_V²−2ρσ_Uσ_V) だけである。<br>"
        "ρ が高いほど2資産が同じ方向に動き、比 V/U のばらつきが減って交換の価値は下がる。<br>"
        "ρ→1 かつ σ_U=σ_V では σ̂→0 で、価格は割引フォワードの差（点線）に張り付く。"
    )
    return _finish(fig, "exchange_correlation", states, titles, note, legend_rows=2)


def _rate_figure(data):
    """The price does not move with r, and the ratio restatement gives the same number."""
    fig = go.Figure()
    titles = {}
    states = []
    for family in data["rate"]["data"]:
        state = family["market"]
        states.append(state)
        entries = family["entries"]
        rates = [entry["rate"] for entry in entries]
        price = family["library_price"]
        fig.add_trace(go.Scatter(
            x=[100.0 * rate for rate in rates], y=[entry["reference"] for entry in entries],
            mode="lines+markers", name="独立参照価格（求積・式26.5を使わない）",
            line=dict(color=_COLORS[1], width=2.5),
            meta=_trace_meta("reference", state),
            hovertemplate="r=%{x:.0f}%: %{y:.10f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[100.0 * rate for rate in rates], y=[family["restated_price"]] * len(rates),
            mode="lines", name=f"V/U の読み替え（行使1.0・金利 q_U・配当 q_V）{family['restated_price']:.6f}",
            line=dict(color=_COLORS[0], width=6, dash="dot"), opacity=0.45,
            meta=_trace_meta("restated", state),
            hovertemplate="読み替え %{y:.10f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[100.0 * rate for rate in rates],
            y=[entry["fixed_strike_misreading"] for entry in entries], mode="lines+markers",
            name="行使価格を今日の U_0 に固定した誤った読み方",
            line=dict(color=_COLORS[3], width=2, dash="dash"),
            meta=_trace_meta("naive", state),
            hovertemplate="r=%{x:.0f}%: %{y:.4f}<extra></extra>"))
        titles[state] = (
            f"{_LABELS[state]}<br>"
            f"r を −5% から 12% まで動かしても価格は {price:.6f} のまま"
            f"（最大差 {family['reference_spread']:.2e}）"
        )
    fig.update_layout(
        xaxis=dict(title="リスクフリー金利 r（%）", tickvals=[-5, -2, 0, 2, 5, 8, 12]),
        yaxis=dict(title="価格（V_0/U_0 = 1.1）"),
    )
    note = (
        "r が上がると2資産の期待成長率も割引率も同じだけ上がり、打ち消し合う。<br>"
        "太い点線は Hull の読み替え（V/U を原資産、行使1.0、金利 q_U、配当 q_V）で、<br>"
        "求積で出した実線とすべての r で重なる。破線は行使価格を今日の U_0 に<br>"
        "固定した普通のコールと読んだ場合で、こちらは r とともに動く。"
    )
    return _finish(fig, "exchange_rate", states, titles, note, legend_rows=4)


def _american_figure(data):
    """Early exercise is worth nothing without a yield on the asset received."""
    fig = go.Figure()
    titles = {}
    states = []
    for family in data["american"]["data"]:
        state = family["market"]
        states.append(state)
        entries = family["entries"]
        ratios = [entry["value_ratio"] for entry in entries]
        fig.add_trace(go.Scatter(
            x=ratios, y=[entry["european"] for entry in entries], mode="lines",
            name="欧州型（式26.5）", line=dict(color=_COLORS[1], width=2.5),
            meta=_trace_meta("european", state),
            hovertemplate="V/U=%{x:.2f}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=ratios, y=[entry["american"] for entry in entries], mode="lines",
            name="米国型（V/U 上の二項木・1024ステップ）",
            line=dict(color=_COLORS[0], width=2, dash="dash"),
            meta=_trace_meta("american", state),
            hovertemplate="V/U=%{x:.2f}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=ratios, y=[entry["intrinsic"] for entry in entries], mode="lines",
            name="即時行使の価値 max(V_0−U_0, 0)",
            line=dict(color=_COLORS[5], width=1.5, dash="dot"),
            meta=_trace_meta("intrinsic", state),
            hovertemplate="V/U=%{x:.2f}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=ratios, y=[entry["premium_on_grid"] for entry in entries], mode="lines+markers",
            name="早期行使プレミアム（同一格子で分離、右軸）", yaxis="y2",
            line=dict(color=_COLORS[3], width=2),
            customdata=[[entry["grid_residual"]] for entry in entries],
            meta=_trace_meta("premium", state),
            hovertemplate=("V/U=%{x:.2f}: プレミアム %{y:.3e}"
                           "（格子残差 %{customdata[0]:.1e}）<extra></extra>")))
        fig.add_trace(go.Scatter(
            x=ratios, y=[abs(entry["grid_residual"]) for entry in entries], mode="lines",
            name="有限格子の残差（早期行使ではない、右軸）", yaxis="y2",
            line=dict(color=_COLORS[4], width=1.5, dash="dot"),
            meta=_trace_meta("grid", state),
            hovertemplate="V/U=%{x:.2f}: 格子残差 %{y:.1e}<extra></extra>"))
        premium = max(entry["premium_on_grid"] for entry in entries)
        residual = max(abs(entry["grid_residual"]) for entry in entries)
        verdict = (
            f"最大プレミアム {premium:.3e}（格子残差 {residual:.1e} と同じ桁＝早期行使に価値なし）"
            if not family["early_exercise_possible"]
            else f"最大プレミアム {premium:.4f}（格子残差 {residual:.1e} の {premium / residual:,.0f} 倍）"
        )
        titles[state] = f"{_LABELS[state]}：q_V = {100 * family['yield_v']:.0f}%<br>{verdict}"
    fig.update_layout(
        xaxis=dict(title="V_0 / U_0", tickvals=[0.6, 0.8, 1.0, 1.2, 1.4]),
        yaxis=dict(title="価格（U_0 = 100）"),
        yaxis2=dict(title="早期行使プレミアム", overlaying="y", side="right", type="log",
                    exponentformat="e"),
    )
    note = (
        "Rubinstein の読み替えでは、この契約は V/U を原資産・行使1.0・<br>"
        "金利 q_U・配当 q_V とする米国型コール U_0 個である。<br>"
        "配当の無い資産へのコールは早期行使されないので、q_V = 0 なら米国型は欧州型に一致する。<br>"
        "木は有限格子なので、欧州型との差には早期行使と離散化が混ざる。<br>"
        "同じ格子で行使判定だけを外した価格と比べて両者を分離した（点線が離散化の分）。"
    )
    return _finish(fig, "exchange_american", states, titles, note, legend_rows=5)


def _figures(path=None):
    """Build every §26.14 lesson figure from the saved data."""
    data = _load_data(path)
    return {
        "exchange_payoff": _payoff_figure(data),
        "exchange_correlation": _correlation_figure(data),
        "exchange_rate": _rate_figure(data),
        "exchange_american": _american_figure(data),
    }
