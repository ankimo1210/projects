"""Private saved-data Plotly lessons for Hull 11e GE §26.16 (volatility and variance swaps)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "docs/validation/section-26-16/lesson-data.json"
_FAMILIES = ("payoff", "strip", "replication", "convexity")
_REQUIRED_SOURCES = frozenset(
    {
        "hullkit/src/hullkit/variance_swaps.py",
        "scripts/build_variance_swap_reference.py",
        "docs/validation/section-26-16/reference.json",
        "docs/validation/section-26-16/numerical-check.json",
        "scripts/build_variance_swap_lesson_data.py",
    }
)
_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#7b52ab", "#0f766e", "#86868b")
_LABELS = {
    "payoffs": "2つの給付",
    "difference": "給付の差",
    "q": "Q(Kᵢ)",
    "contribution": "E(V) への寄与",
    "absolute": "誤差（分散）",
    "relative": "相対誤差（%）",
    "levels": "E(σ) の水準",
    "error": "近似の誤差",
    "narrow": "狭い 70–140",
    "medium": "中間 40–220",
    "wide": "広い 10–400",
    "put": "プット（K < S*）",
    "average": "平均（K = S*）",
    "call": "コール（K > S*）",
}
_KIND_COLORS = {"put": _COLORS[0], "average": _COLORS[2], "call": _COLORS[1]}
_RANGE_COLORS = {"narrow": _COLORS[1], "medium": _COLORS[2], "wide": _COLORS[0]}


def _load_data(path=None, root=None):
    """Load saved lesson numbers and reject missing, deleted or stale sources."""
    root = Path(root) if root is not None else _ROOT
    data = json.loads(Path(path or _DATA).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("section") != "26.16":
        raise ValueError("unsupported variance-swap lesson schema")
    digests = {}
    for family in _FAMILIES:
        sources = data[family].get("source_hashes", {})
        missing = _REQUIRED_SOURCES.difference(sources)
        if missing:
            raise ValueError(
                f"missing variance-swap lesson source hashes: {family}: {sorted(missing)}"
            )
        unexpected = set(sources).difference(_REQUIRED_SOURCES)
        if unexpected:
            raise ValueError(
                f"unexpected variance-swap lesson source hashes: {family}: {sorted(unexpected)}"
            )
        for relative in sorted(_REQUIRED_SOURCES):
            source = root / relative
            if not source.is_file():
                raise ValueError(f"missing variance-swap lesson source: {family}: {relative}")
            if relative not in digests:
                digests[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
            if digests[relative] != sources[relative]:
                raise ValueError(f"stale variance-swap lesson source: {family}: {relative}")
    return data


def _meta(key, scenario):
    return {
        "section": "26.16",
        "figure": key,
        "scenario": scenario,
        "units": {
            "money": "$ millions (Hull's examples)",
            "volatility": "annualized",
            "variance": "variance rate per year",
            "time": "years",
        },
    }


def _trace_meta(role, scenario):
    return {"role": role, "scenario": scenario}


def _finish(fig, key, states, titles, note, *, height=500, legend_rows=1):
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
    extra = 20 * (legend_rows - 1)
    fig.update_layout(
        template="plotly_white",
        height=height + 130 + extra,
        title=dict(text=titles[states[0]], font_size=16, y=0.92, yanchor="top"),
        meta=_meta(key, states[0]),
        margin=dict(l=75, r=75, t=175, b=180 + extra),
        font=dict(family="Arial, sans-serif", size=12),
        legend=dict(orientation="h", y=-0.20, yanchor="top", x=0),
        updatemenus=[
            dict(
                type="dropdown",
                buttons=buttons,
                x=1,
                xanchor="right",
                y=1.16,
                yanchor="top",
            )
        ],
    )
    fig.add_annotation(
        x=0,
        y=0,
        yshift=-105 - extra,
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


def _payoff_figure(data):
    payload = data["payoff"]["data"]
    rows = payload["rows"]
    sigma = [row["realized_volatility"] for row in rows]
    strike = payload["volatility_strike"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sigma,
            y=[row["volatility_payoff"] for row in rows],
            mode="lines",
            name="ボラティリティ・スワップ L_vol(σ − σ_K)",
            line=dict(color=_COLORS[0], width=3),
            meta=_trace_meta("volatility-payoff", "payoffs"),
            hovertemplate="σ=%{x:.2f}: %{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sigma,
            y=[row["variance_payoff"] for row in rows],
            mode="lines",
            name="バリアンス・スワップ L_var(σ² − σ_K²)",
            line=dict(color=_COLORS[1], width=3, dash="dash"),
            meta=_trace_meta("variance-payoff", "payoffs"),
            hovertemplate="σ=%{x:.2f}: %{y:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sigma,
            y=[row["difference"] for row in rows],
            mode="lines",
            name="差 = L_vol(σ − σ_K)² / (2σ_K)",
            line=dict(color=_COLORS[3], width=3),
            fill="tozeroy",
            meta=_trace_meta("difference", "difference"),
            hovertemplate="σ=%{x:.2f}: 差 %{y:.4f}<extra></extra>",
        )
    )
    for state in ("payoffs", "difference"):
        fig.add_trace(
            go.Scatter(
                x=[strike, strike],
                y=[
                    min(row["volatility_payoff"] for row in rows),
                    max(row["variance_payoff"] for row in rows),
                ]
                if state == "payoffs"
                else [0.0, max(row["difference"] for row in rows)],
                mode="lines",
                name=f"σ_K = {100 * strike:.0f}%",
                line=dict(color=_COLORS[5], width=1.5, dash="dot"),
                meta=_trace_meta("strike", state),
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        xaxis=dict(title="満期の実現ボラティリティ σ（年率、小数）", tickformat=".2f"),
        yaxis=dict(title="満期の給付（$ millions）"),
    )
    notional = payload["variance_notional"]
    titles = {
        "payoffs": (
            f"L_vol={payload['volatility_notional']:.0f}、σ_K={100 * strike:.0f}% と "
            f"L_var=L_vol/(2σ_K)={notional:.2f}：σ_K で接する"
        ),
        "difference": "バリアンス − ボラティリティ給付：常に 0 以上（凸性）",
    }
    note = (
        "Example 26.5 の契約（$100m、23%）を満期の給付で描く。L_var=L_vol/(2σ_K) は σ_K での傾きを<br>"
        "そろえる換算で、σ_K から離れるほどバリアンス側が大きい。割引前の値である。"
    )
    return _finish(fig, "varswap_payoff", ("payoffs", "difference"), titles, note, legend_rows=2)


def _strip_figure(data):
    payload = data["strip"]["data"]
    rows = payload["rows"]
    fig = go.Figure()
    for kind in ("put", "average", "call"):
        chosen = [row for row in rows if row["q_kind"] == kind]
        fig.add_trace(
            go.Bar(
                x=[row["strike"] for row in chosen],
                y=[row["q"] for row in chosen],
                name=f"Q(Kᵢ)：{_LABELS[kind]}",
                marker_color=_KIND_COLORS[kind],
                meta=_trace_meta(f"q-{kind}", "q"),
                hovertemplate="K=%{x:.0f}: Q=%{y:.4f}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[row["strike"] for row in rows],
            y=[row["printed_q"] for row in rows],
            mode="markers",
            name="Hull の印刷値（小数2桁）",
            marker=dict(color="#111111", size=9, symbol="diamond-open", line_width=2),
            meta=_trace_meta("printed-q", "q"),
            hovertemplate="K=%{x:.0f}: 印刷 %{y:.2f}<extra></extra>",
        )
    )
    for kind in ("put", "average", "call"):
        chosen = [row for row in rows if row["q_kind"] == kind]
        fig.add_trace(
            go.Bar(
                x=[row["strike"] for row in chosen],
                y=[row["variance_contribution"] for row in chosen],
                name=f"(2/T)ΔK/K² e^{{rT}} Q：{_LABELS[kind]}",
                marker_color=_KIND_COLORS[kind],
                meta=_trace_meta(f"contribution-{kind}", "contribution"),
                hovertemplate="K=%{x:.0f}: 寄与 %{y:.5f}<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="overlay",
        xaxis=dict(title="行使価格 K", tickvals=[row["strike"] for row in rows]),
        yaxis=dict(title="オプション価格 / 分散への寄与"),
    )
    titles = {
        "q": (
            f"Example 26.4：F₀={payload['forward']:.2f}、S*={payload['s_star']:.0f}。"
            "S* の下はプット、上はコール"
        ),
        "contribution": (
            f"寄与の合計 {sum(row['variance_contribution'] for row in rows):.6f} + 境界項 "
            f"{payload['boundary_terms']:.6f} = E(V) {payload['expected_variance']:.6f}"
        ),
    }
    note = (
        "Q はこのリポジトリの BSM で各行使価格のインプライド・ボラから再計算し、菱形の印刷値と<br>"
        "小数2桁で一致する。1/K² の重みで低い行使価格のプットが相対的に重く数えられる。"
    )
    return _finish(fig, "varswap_strip", ("q", "contribution"), titles, note, legend_rows=2)


def _replication_figure(data):
    payload = data["replication"]["data"]
    fig = go.Figure()
    for state, field in (("absolute", "error"), ("relative", "relative_error_percent")):
        for family in payload["families"]:
            name = family["range"]
            fig.add_trace(
                go.Scatter(
                    x=[entry["delta_k"] for entry in family["entries"]],
                    y=[entry[field] for entry in family["entries"]],
                    mode="lines+markers",
                    name=f"行使価格の範囲 {_LABELS[name]}",
                    line=dict(color=_RANGE_COLORS[name], width=2.5),
                    marker=dict(size=9),
                    meta=_trace_meta(f"strip-error-{name}", state),
                    customdata=[entry["strikes"] for entry in family["entries"]],
                    hovertemplate=("ΔK=%{x}: %{y:.3e}<br>行使価格 %{customdata} 本<extra></extra>"),
                )
            )
        fig.add_trace(
            go.Scatter(
                x=[1.25, 10.0],
                y=[0.0, 0.0],
                mode="lines",
                name="連続積分（誤差 0）",
                line=dict(color=_COLORS[5], width=1.5, dash="dot"),
                meta=_trace_meta("zero", state),
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        xaxis=dict(
            title="行使価格の間隔 ΔK（対数軸）",
            type="log",
            tickvals=[1.25, 2.5, 5, 10],
            ticktext=["1.25", "2.5", "5", "10"],
        ),
        yaxis=dict(title="離散ストリップ − 厳密 E(V)", exponentformat="e"),
    )
    exact = payload["exact"]
    titles = {
        "absolute": f"Heston の歪んだスマイル：厳密 E(V)={exact:.4f} に対する式26.8の誤差",
        "relative": "同じ誤差を厳密 E(V) に対する % で表示",
    }
    note = (
        "厳密値は閉形式の E(V)。連続積分としての式26.6は同じ価格から閉形式と "
        f"{payload['continuous_max_abs_difference']:.1e} 以内で一致した。<br>"
        "広い範囲では ΔK を半分にすると誤差がほぼ1/4（格子誤差）。狭い範囲では翼の欠落で負へ転じる。"
    )
    return _finish(
        fig, "varswap_replication", ("absolute", "relative"), titles, note, legend_rows=2
    )


def _convexity_figure(data):
    payload = data["convexity"]["data"]
    rows = payload["rows"]
    xi = [row["xi"] for row in rows]
    fig = go.Figure()
    for role, field, name, color, dash in (
        ("naive", "naive", "√E(V)（凸性を無視）", _COLORS[5], "dot"),
        ("exact", "exact", "厳密 E(√V)（CIR ラプラス変換）", _COLORS[0], "solid"),
        ("approximation", "approximation", "式26.9 の近似", _COLORS[1], "dash"),
    ):
        fig.add_trace(
            go.Scatter(
                x=xi,
                y=[100.0 * row[field] for row in rows],
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2.5, dash=dash),
                meta=_trace_meta(role, "levels"),
                hovertemplate="ξ=%{x:.1f}: %{y:.3f}%<extra></extra>",
            )
        )
    mc_rows = [row for row in rows if row["mc"] is not None]
    fig.add_trace(
        go.Scatter(
            x=[row["xi"] for row in mc_rows],
            y=[100.0 * row["mc"]["estimate"] for row in mc_rows],
            mode="markers",
            name="厳密 CIR 推移の MC（±4SE）",
            marker=dict(color=_COLORS[3], size=10, symbol="diamond-open", line_width=2),
            error_y=dict(
                type="data",
                array=[100.0 * row["mc"]["four_standard_errors"] for row in mc_rows],
                visible=True,
                color=_COLORS[3],
                thickness=1.5,
            ),
            meta=_trace_meta("mc-estimate", "levels"),
            hovertemplate="ξ=%{x:.1f}: MC %{y:.3f}%<extra></extra>",
        )
    )
    for role, field, name, color in (
        ("approximation-error", "approximation_error", "式26.9 − 厳密", _COLORS[1]),
        ("naive-error", "naive_error", "√E(V) − 厳密", _COLORS[5]),
    ):
        fig.add_trace(
            go.Scatter(
                x=xi,
                y=[100.0 * row[field] for row in rows],
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2.5),
                meta=_trace_meta(role, "error"),
                hovertemplate="ξ=%{x:.1f}: %{y:.4f} %pt<extra></extra>",
            )
        )
    fig.update_layout(
        xaxis=dict(title="分散過程のボラティリティ ξ（vol of vol）", tickvals=xi),
        yaxis=dict(title="年率ボラティリティ（%）/ 誤差（%ポイント）"),
    )
    base = payload["base"]
    titles = {
        "levels": (
            f"E(V)={base['theta']} で固定し ξ だけを動かす：E(√V) < √E(V)（T={base['expiry']}年）"
        ),
        "error": "近似の誤差（%ポイント）：式26.9 は ξ⁴ の速さで外れ、常に下側",
    }
    note = (
        "連続観測の Heston/CIR 分散（v₀=θ、κ=2）。var(V) は伊藤等長性、厳密値はラプラス変換の積分、<br>"
        "MC は非心カイ二乗による厳密推移。誤差の向きはこの市場の測定結果で、一般の保証ではない。"
    )
    return _finish(fig, "volswap_convexity", ("levels", "error"), titles, note, legend_rows=3)


def _figures(path=None):
    """Build all §26.16 figures from checked-in lesson data only."""
    data = _load_data(path)
    return {
        "varswap_payoff": _payoff_figure(data),
        "varswap_strip": _strip_figure(data),
        "varswap_replication": _replication_figure(data),
        "volswap_convexity": _convexity_figure(data),
    }
