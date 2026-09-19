"""Private saved-data Plotly lessons for Hull 11e GE §26.15."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "docs/validation/section-26-15/lesson-data.json"
_FAMILIES = ("payoff", "correlation", "comparison", "error")
_REQUIRED_SOURCES = frozenset(
    {
        "hullkit/src/hullkit/exotics.py",
        "scripts/build_basket_reference.py",
        "docs/validation/section-26-15/prices.json",
        "docs/validation/section-26-15/numerical-check.json",
        "scripts/build_basket_lesson_data.py",
    }
)
_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#7b52ab", "#0f766e", "#86868b")
_ERROR_MARKETS = (
    "baseline",
    "long-high-volatility",
    "three-diversified",
    "three-high-volatility",
)
_LABELS = {
    "call": "コール",
    "put": "プット",
    "all": "共分散寄与 + マッチ済みボラ",
    "covariance-only": "交差共分散寄与",
    "volatility-only": "マッチ済みボラ",
    "baseline-call": "標準市場・コール",
    "long-high-volatility-call": "長期高ボラ・コール",
    "baseline-put": "標準市場・プット",
    "baseline": "標準",
    "long-high-volatility": "長期・高ボラ",
    "three-diversified": "3資産・分散",
    "three-high-volatility": "3資産・高ボラ",
}


def _load_data(path=None, root=None):
    """Load saved lesson numbers and reject missing, deleted or stale sources."""
    root = Path(root) if root is not None else _ROOT
    data = json.loads(Path(path or _DATA).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("section") != "26.15":
        raise ValueError("unsupported basket lesson schema")
    digests = {}
    for family in _FAMILIES:
        sources = data[family].get("source_hashes", {})
        missing = _REQUIRED_SOURCES.difference(sources)
        if missing:
            raise ValueError(f"missing basket lesson source hashes: {family}: {sorted(missing)}")
        unexpected = set(sources).difference(_REQUIRED_SOURCES)
        if unexpected:
            raise ValueError(
                f"unexpected basket lesson source hashes: {family}: {sorted(unexpected)}"
            )
        for relative in sorted(_REQUIRED_SOURCES):
            source = root / relative
            if not source.is_file():
                raise ValueError(f"missing basket lesson source: {family}: {relative}")
            if relative not in digests:
                digests[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
            if digests[relative] != sources[relative]:
                raise ValueError(f"stale basket lesson source: {family}: {relative}")
    return data


def _meta(key, scenario):
    return {
        "section": "26.15",
        "figure": key,
        "scenario": scenario,
        "units": {
            "money": "currency",
            "time": "years",
            "rates": "continuous per year",
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
    weights = payload["weights"]
    strike = payload["strike"]
    rows = payload["rows"]
    labels = [
        f"S₁(T)={row['terminal_assets'][0]:.0f}, S₂(T)={row['terminal_assets'][1]:.0f}"
        for row in rows
    ]
    baskets = [row["basket_terminal"] for row in rows]
    fig = go.Figure()
    titles = {}
    for kind in ("call", "put"):
        fig.add_trace(
            go.Bar(
                x=labels,
                y=baskets,
                name="バスケット B_T",
                marker_color=_COLORS[0],
                opacity=0.55,
                meta=_trace_meta("basket-terminal", kind),
                customdata=[row["terminal_assets"] for row in rows],
                hovertemplate=(
                    "S₁(T)=%{customdata[0]:.0f}, S₂(T)=%{customdata[1]:.0f}"
                    "<br>B_T=%{y:.1f}<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=[row[kind] for row in rows],
                mode="lines+markers",
                name=f"{_LABELS[kind]}給付",
                line=dict(color=_COLORS[1], width=3),
                marker=dict(size=9),
                meta=_trace_meta("payoff", kind),
                hovertemplate="給付 %{y:.1f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=[strike] * len(rows),
                mode="lines",
                name=f"行使価格 K={strike:.0f}",
                line=dict(color=_COLORS[5], width=1.5, dash="dot"),
                meta=_trace_meta("strike", kind),
                hovertemplate="K=%{y:.0f}<extra></extra>",
            )
        )
        formula = "max(B_T−K, 0)" if kind == "call" else "max(K−B_T, 0)"
        titles[kind] = (
            f"2資産バスケット {_LABELS[kind]}：B_T = "
            f"{weights[0]:.1f}S₁(T) + {weights[1]:.1f}S₂(T)<br>給付 {formula}"
        )
    fig.update_layout(
        barmode="overlay",
        xaxis=dict(title="満期の2資産状態"),
        yaxis=dict(title="バスケット価値 / 給付"),
    )
    note = (
        "横軸は文字どおりの2資産満期値。両ウェイトは正で、左端では第2資産の寄与も正だが<br>"
        "B_T < K のためコール給付は0になる。ゼロ給付とゼロ保有量は別の概念である。"
    )
    return _finish(
        fig,
        "basket_payoff",
        ("call", "put"),
        titles,
        note,
        legend_rows=2,
    )


def _correlation_figure(data):
    entries = data["correlation"]["data"]["entries"]
    rho = [entry["rho"] for entry in entries]
    covariance = [entry["cross_covariance_contribution"] for entry in entries]
    volatility = [100.0 * entry["matched_volatility"] for entry in entries]
    fig = go.Figure()
    for state in ("all", "covariance-only"):
        fig.add_trace(
            go.Scatter(
                x=rho,
                y=covariance,
                mode="lines+markers",
                name="2 Cov(w₁S₁(T), w₂S₂(T))",
                line=dict(color=_COLORS[1], width=3),
                marker=dict(size=9),
                meta=_trace_meta("cross-covariance", state),
                hovertemplate="ρ=%{x:.2f}: 交差寄与 %{y:.2f}<extra></extra>",
            )
        )
    for state in ("all", "volatility-only"):
        fig.add_trace(
            go.Scatter(
                x=rho,
                y=volatility,
                mode="lines+markers",
                name="マッチ済み σ̂（右軸）",
                yaxis="y2",
                line=dict(color=_COLORS[0], width=2.5),
                marker=dict(size=9, symbol="diamond"),
                meta=_trace_meta("matched-volatility", state),
                hovertemplate="ρ=%{x:.2f}: σ̂=%{y:.2f}%<extra></extra>",
            )
        )
    fig.update_layout(
        xaxis=dict(title="相関 ρ", tickvals=rho),
        yaxis=dict(title="M₂ に入る交差共分散寄与"),
        yaxis2=dict(
            title="マッチ済みボラ σ̂（%/年）",
            overlaying="y",
            side="right",
        ),
    )
    titles = {
        "all": "相関だけを変えた同一市場：交差共分散寄与と σ̂",
        "covariance-only": "相関だけを変えた同一市場：2F₁F₂[exp(ρσ₁σ₂T)−1]",
        "volatility-only": "相関だけを変えた同一市場：M₁・M₂ にマッチした σ̂",
    }
    note = (
        "3点は spot・weight・配当・ボラ・金利・満期が同一で、ρ だけが −0.65 / 0.35 / 0.90。<br>"
        "ρ は M₂ の交差項を通じてバスケット分散を変え、その2モーメントに合わせた σ̂ を動かす。"
    )
    return _finish(
        fig,
        "basket_correlation",
        ("all", "covariance-only", "volatility-only"),
        titles,
        note,
        legend_rows=2,
    )


def _comparison_figure(data):
    fig = go.Figure()
    titles = {}
    states = []
    for family in data["comparison"]["data"]:
        state = family["scenario"]
        states.append(state)
        entries = family["entries"]
        strikes = [entry["strike"] for entry in entries]
        fig.add_trace(
            go.Scatter(
                x=strikes,
                y=[entry["approximation"] for entry in entries],
                mode="lines+markers",
                name="2モーメント対数正規近似",
                line=dict(color=_COLORS[1], width=3),
                meta=_trace_meta("approximation", state),
                hovertemplate="K=%{x:.0f}: 近似 %{y:.4f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=strikes,
                y=[entry["independent_reference"] for entry in entries],
                mode="lines+markers",
                name="独立な条件付き積分",
                line=dict(color=_COLORS[0], width=2.5, dash="dash"),
                meta=_trace_meta("independent-reference", state),
                hovertemplate="K=%{x:.0f}: 条件付き積分 %{y:.4f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=strikes,
                y=[entry["mc"] for entry in entries],
                mode="markers",
                name="独立 MC（±4SE）",
                marker=dict(color=_COLORS[3], size=10, symbol="diamond-open"),
                error_y=dict(
                    type="data",
                    array=[entry["four_standard_errors"] for entry in entries],
                    visible=True,
                    color=_COLORS[3],
                    thickness=1.5,
                ),
                meta=_trace_meta("mc-estimate", state),
                hovertemplate="K=%{x:.0f}: MC %{y:.4f}<extra></extra>",
            )
        )
        label = _LABELS[state]
        titles[state] = f"{label}：近似値と独立参照を区別する"
    fig.update_layout(
        xaxis=dict(title="行使価格 K", tickvals=[80, 100, 120]),
        yaxis=dict(title="オプション価格"),
    )
    note = (
        "赤は M₁・M₂ に合う対数正規代理分布による近似。青破線は2資産条件付き積分の独立参照。<br>"
        "菱形は別の相関 GBM シミュレーションで、エラーバーは ±4 標準誤差。"
    )
    return _finish(
        fig,
        "basket_comparison",
        tuple(states),
        titles,
        note,
        legend_rows=3,
    )


def _error_figure(data):
    fig = go.Figure()
    states = []
    titles = {}
    for family in data["error"]["data"]:
        state = family["scenario"]
        states.append(state)
        entries = family["entries"]
        established = [entry for entry in entries if entry["error_sign_established"]]
        unresolved = [entry for entry in entries if not entry["error_sign_established"]]
        fig.add_trace(
            go.Bar(
                x=[entry["market"] for entry in established],
                y=[entry["absolute_relative_error_percent"] for entry in established],
                name="|近似−参照| / |参照|（符号確認済み）",
                marker_color=_COLORS[1],
                meta=_trace_meta("absolute-relative-gap-established", state),
                customdata=[[entry["market"], entry["absolute_gap"]] for entry in established],
                hovertemplate=(
                    "%{customdata[0]}<br>|gap|=%{customdata[1]:.7f}"
                    "<br>相対値=%{y:.3f}%<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Bar(
                x=[entry["market"] for entry in unresolved],
                y=[entry["absolute_relative_error_percent"] for entry in unresolved],
                name="|近似−MC| / |MC|（符号未確定）",
                marker=dict(
                    color=_COLORS[5],
                    pattern=dict(shape="/"),
                ),
                meta=_trace_meta("absolute-relative-gap-unresolved", state),
                customdata=[
                    [entry["absolute_gap"], entry["four_standard_errors"]] for entry in unresolved
                ],
                hovertemplate=(
                    "%{x}<br>|gap|=%{customdata[0]:.7f}"
                    "<br>4SE=%{customdata[1]:.7f}"
                    "<br>符号未確定<extra></extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[entry["market"] for entry in entries],
                y=[entry["four_se_relative_percent"] for entry in entries],
                mode="markers",
                name="4SE / |参照|",
                marker=dict(
                    color=_COLORS[0],
                    size=11,
                    symbol="line-ew",
                    line_width=3,
                ),
                meta=_trace_meta("four-se-relative-uncertainty", state),
                hovertemplate="4SE 相対値 %{y:.3f}%<extra></extra>",
            )
        )
        target = next(entry for entry in entries if entry["market"] == "three-diversified")
        titles[state] = (
            f"K=100 {_LABELS[state]}：絶対相対誤差と MC 不確実性"
            f"<br>3資産・分散：|gap|={target['absolute_gap']:.7f} "
            f"< 4SE={target['four_standard_errors']:.7f}（符号未確定）"
        )
    fig.update_layout(
        barmode="group",
        xaxis=dict(
            title="固定市場（K=100）",
            tickvals=list(_ERROR_MARKETS),
            ticktext=[_LABELS[name] for name in _ERROR_MARKETS],
        ),
        yaxis=dict(title="絶対相対誤差 / 4SE 相対値（%）", rangemode="tozero"),
    )
    note = (
        "棒は常に絶対値で描き、上下方向に近似バイアスの符号を持たせない。斜線の点は<br>"
        "|gap| ≤ 4SE のため、保存済み MC だけでは過大・過小評価の向きを確定できない。"
    )
    return _finish(
        fig,
        "basket_error",
        tuple(states),
        titles,
        note,
        legend_rows=3,
    )


def _figures(path=None):
    """Build all §26.15 figures from checked-in lesson data only."""
    data = _load_data(path)
    return {
        "basket_payoff": _payoff_figure(data),
        "basket_correlation": _correlation_figure(data),
        "basket_comparison": _comparison_figure(data),
        "basket_error": _error_figure(data),
    }
