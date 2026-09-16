"""Private artifact-only Plotly lessons for Hull 11e GE §26.13."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "docs/validation/section-26-13/lesson-data.json"
_FAMILIES = ("contract", "distribution", "observations", "errors", "seasoned")
_REQUIRED_SOURCES = frozenset(
    {
        "hullkit/src/hullkit/exotics.py",
        "scripts/build_asian_lesson_data.py",
        "scripts/build_asian_reference.py",
        "docs/validation/section-26-13/prices.json",
        "docs/validation/section-26-13/numerical-check.json",
    }
)
_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#2ca02c", "#86868b")
# One line per market, so the six must stay distinct after the portal theme remaps
# #1f77b4 to ink, #d62728 to the accent and #2ca02c to its gray (report_builder/theme.py).
_MARKET_COLORS = ("#1f77b4", "#d62728", "#bc8f00", "#2ca02c", "#7b52ab", "#0f766e")
_COMPACT = {
    "low-vol-short": "低ボラ短期 σ10%/0.25年",
    "positive-carry": "正キャリー σ20%/1年",
    "dividend-above-rate": "配当>金利 σ25%/1.5年",
    "negative-rate": "負金利 σ18%/0.75年",
    "zero-carry": "ゼロキャリー σ30%/2年",
    "high-vol-long": "高ボラ長期 σ70%/5年",
}
_LABELS = {
    "average_price": "平均価格型（call/put）",
    "average_strike": "平均行使型（call/put）",
    "call": "コール",
    "put": "プット",
    "low-vol-short": "低ボラ・短期（σ=10%, T=0.25年）",
    "positive-carry": "正のキャリー（σ=20%, T=1年）",
    "dividend-above-rate": "配当利回り > 金利（σ=25%, T=1.5年）",
    "negative-rate": "負の金利（σ=18%, T=0.75年）",
    "zero-carry": "ゼロキャリー r=q（σ=30%, T=2年）",
    "high-vol-long": "高ボラ・長期（σ=70%, T=5年）",
}


def _load_data(path=None):
    """Load saved numbers, refusing stale generator or pricing source hashes."""
    data = json.loads(Path(path or _DATA).read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        raise ValueError("unsupported asian lesson schema")
    digests = {}
    for family in _FAMILIES:
        sources = data[family].get("source_hashes", {})
        missing = _REQUIRED_SOURCES.difference(sources)
        if missing:
            raise ValueError(f"missing asian lesson source hashes: {family}: {sorted(missing)}")
        for relative, expected in sources.items():
            if relative not in digests:
                digests[relative] = hashlib.sha256((_ROOT / relative).read_bytes()).hexdigest()
            if digests[relative] != expected:
                raise ValueError(f"stale asian lesson source: {family}: {relative}")
    return data


def _meta(key, state):
    return {
        "section": "26.13",
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
        margin=dict(l=70, r=40, t=175, b=190 + extra),
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
    """One defined path: where the average sits and what each contract pays."""
    row = data["contract"]["rows"][0]
    prices = row["path"]
    strike = row["strike"]
    average = row["average"]
    terminal = row["terminal"]
    steps = list(range(len(prices)))
    fig = go.Figure()
    for state in ("average_price", "average_strike"):
        fig.add_trace(go.Scatter(
            x=steps, y=prices, mode="lines+markers", name="株価の経路",
            line=dict(color=_COLORS[0], width=2), meta=_trace_meta("path", state),
            hovertemplate="観測 %{x}: %{y:.1f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=steps, y=[average] * len(steps), mode="lines",
            name=f"平均 A = {average:.2f}", line=dict(color=_COLORS[2], width=2, dash="dash"),
            meta=_trace_meta("average", state), hovertemplate="平均 %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[steps[-1]], y=[terminal], mode="markers+text",
            name=f"満期値 S_T = {terminal:.1f}", text=["S_T"], textposition="top center",
            marker=dict(color=_COLORS[3], size=11), meta=_trace_meta("terminal", state),
            hovertemplate="満期値 %{y:.4f}<extra></extra>"))
    for state in ("average_price", "average_strike"):
        fig.add_trace(go.Scatter(
            x=steps, y=[strike] * len(steps), mode="lines", name=f"行使価格 K = {strike:.0f}",
            line=dict(color=_COLORS[1], width=1.5, dash="dot"),
            meta=_trace_meta("strike", state),
            hovertemplate="K %{y:.2f}<extra></extra>"))
    payoffs = row["payoffs"]
    fig.add_trace(go.Bar(
        x=["コール", "プット", "バニラ・コール"],
        y=[payoffs["average_price_call"], payoffs["average_price_put"], payoffs["vanilla_call"]],
        name="給付", marker_color=_COLORS[0], yaxis="y2", width=0.45,
        meta=_trace_meta("payoff", "average_price"),
        hovertemplate="%{x}: %{y:.4f}<extra></extra>"))
    fig.add_trace(go.Bar(
        x=["コール", "プット", "バニラ・コール"],
        y=[payoffs["average_strike_call"], payoffs["average_strike_put"], payoffs["vanilla_call"]],
        name="給付", marker_color=_COLORS[3], yaxis="y2", width=0.45,
        meta=_trace_meta("payoff", "average_strike"),
        hovertemplate="%{x}: %{y:.4f}<extra></extra>"))
    fig.update_layout(
        xaxis=dict(title="観測番号（0は今日＝観測日ではない）", domain=[0.0, 0.62]),
        yaxis=dict(title="株価"),
        xaxis2=dict(domain=[0.72, 1.0], anchor="y2"),
        yaxis2=dict(title="満期給付", anchor="x2", side="right"),
        barmode="group",
    )
    for trace in fig.data:
        if trace.meta["role"] == "payoff":
            trace.xaxis = "x2"
    titles = {
        "average_price": "平均価格型：平均 A が行使価格 K と比べられる",
        "average_strike": "平均行使型：満期値 S_T が平均 A と比べられる",
    }
    note = (
        "定義した折れ線の例であり、GBM標本ではない。観測日は1〜8で、今日（0）は平均に入らない。<br>"
        "平均価格型の給付は max(A−K,0) と max(K−A,0)、平均行使型は max(S_T−A,0) と max(A−S_T,0)。<br>"
        "同じ経路のバニラ・コール max(S_T−K,0) を並べている。価格ではなく満期給付である。"
    )
    return _finish(fig, "asian_payoff", ["average_price", "average_strike"], titles, note,
                   legend_rows=3)


def _distribution_figure(data):
    """The average is not lognormal: the fitted density misses the shape."""
    fig = go.Figure()
    titles = {}
    states = []
    for row in data["distribution"]["rows"]:
        state = row["market"]
        states.append(state)
        fig.add_trace(go.Bar(
            x=row["centres"], y=row["simulated_density"], name="平均 A の分布（シミュレーション）",
            marker_color=_COLORS[0], opacity=0.55, meta=_trace_meta("simulated", state),
            hovertemplate="A=%{x:.2f}: 密度 %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=row["centres"], y=row["fitted_density"], mode="lines",
            name="モーメント整合した対数正規", line=dict(color=_COLORS[1], width=2.5),
            meta=_trace_meta("fitted", state),
            hovertemplate="A=%{x:.2f}: 密度 %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[row["moment_1"], row["moment_1"]], y=[0.0, max(row["simulated_density"])],
            mode="lines", name=f"M1 = {row['moment_1']:.2f}",
            line=dict(color=_COLORS[2], width=1.5, dash="dash"),
            meta=_trace_meta("moment", state), hovertemplate="M1 %{x:.4f}<extra></extra>"))
        titles[state] = (
            f"{_LABELS[state]}<br>"
            f"整合ボラ {row['matched_volatility'] * 100:.2f}%、"
            f"歪度 実測 {row['simulated_skewness']:.3f} 対 当てはめ {row['fitted_skewness']:.3f}"
        )
    fig.update_layout(xaxis=dict(title="満期時点の平均 A"), yaxis=dict(title="確率密度"),
                      bargap=0.02)
    note = (
        "1次・2次モーメントだけを合わせるので、平均と分散は一致するが形は一致しない。<br>"
        "実測の歪度は当てはめた対数正規より大きい（3市場とも）。右裾の厚みは2次までの整合では残る。<br>"
        "観測52日、20万パス、固定シード。分位0.1%〜99.9%で切り出したヒストグラム。"
    )
    return _finish(fig, "asian_distribution", states, titles, note, legend_rows=2)


def _observation_figure(data):
    """Refining the averaging grid lowers the price toward the continuous limit."""
    fig = go.Figure()
    titles = {}
    states = []
    for row in data["observations"]["rows"]:
        state = row["market"]
        states.append(state)
        counts = [entry["observations"] for entry in row["entries"]]
        fig.add_trace(go.Scatter(
            x=counts, y=[entry["turnbull_wakeman"] for entry in row["entries"]],
            mode="lines+markers", name="モーメント整合（Turnbull-Wakeman）",
            line=dict(color=_COLORS[1], width=2), meta=_trace_meta("approximation", state),
            hovertemplate="観測数 %{x}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=counts, y=[entry["reference"] for entry in row["entries"]],
            error_y=dict(type="data", array=[4.0 * entry["standard_error"]
                                             for entry in row["entries"]], visible=True),
            mode="lines+markers", name="独立参照価格（±4標準誤差）",
            line=dict(color=_COLORS[0], width=2), meta=_trace_meta("reference", state),
            hovertemplate="観測数 %{x}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=counts, y=[entry["geometric"] for entry in row["entries"]],
            mode="lines+markers", name="幾何平均（厳密、算術平均の下界）",
            line=dict(color=_COLORS[4], width=1.5, dash="dot"),
            meta=_trace_meta("geometric", state),
            hovertemplate="観測数 %{x}: %{y:.4f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=[counts[0], counts[-1]],
            y=[row["continuous_turnbull_wakeman"]] * 2, mode="lines",
            name=f"連続平均の整合値 {row['continuous_turnbull_wakeman']:.4f}",
            line=dict(color=_COLORS[2], width=1.5, dash="dash"),
            meta=_trace_meta("continuous", state),
            hovertemplate="連続 %{y:.4f}<extra></extra>"))
        gap = row["entries"][-1]["turnbull_wakeman"] - row["entries"][-1]["reference"]
        titles[state] = (
            f"{_LABELS[state]}<br>"
            f"観測を増やすと価格は下がる（250観測での整合値の上乗せ {gap:+.4f}）"
        )
    fig.update_layout(xaxis=dict(title="観測数 m（対数軸）", type="log",
                                 tickvals=[12, 52, 250], ticktext=["12", "52", "250"]),
                      yaxis=dict(title="ATMコールの価格"))
    note = (
        "観測日は i·T/m で、今日を含まず満期を含む。この規約で原著の 6.00 / 5.70 / 5.63 が再現する。<br>"
        "整合値と参照価格の差は近似誤差であり、標準誤差のバーとは別物である。<br>"
        "幾何平均は算術平均以下なので、コールの価格も下界になる。"
    )
    return _finish(fig, "asian_observations", states, titles, note, legend_rows=3)


def _error_figure(data):
    """Where the moment match is safe and where it is not."""
    rows = data["errors"]["rows"]
    fig = go.Figure()
    titles = {}
    for state in ("call", "put"):
        selected = [row for row in rows if row["contract"] == state]
        by_market = {}
        for row in selected:
            by_market.setdefault(row["market"], []).append(row)
        for index, (market, entries) in enumerate(sorted(
                by_market.items(), key=lambda item: item[1][0]["scale"])):
            entries.sort(key=lambda row: row["spot_ratio"])
            fig.add_trace(go.Scatter(
                x=[row["spot_ratio"] for row in entries],
                y=[100.0 * row["relative_error"] for row in entries],
                mode="lines+markers", name=_COMPACT[market],
                line=dict(color=_MARKET_COLORS[index], width=2),
                meta=_trace_meta(f"market:{market}", state),
                hovertemplate="S/K=%{x:.2f}: %{y:+.2f}%<extra></extra>"))
        worst = max(selected, key=lambda row: abs(row["relative_error"]))
        titles[state] = (
            f"{_LABELS[state]}：モーメント整合の相対誤差<br>"
            f"最大 {100 * worst['relative_error']:+.2f}%（{_LABELS[worst['market']]}）"
        )
    fig.add_hline(y=0.0, line=dict(color="#86868b", width=1))
    fig.update_layout(xaxis=dict(title="スポット / 行使価格", tickvals=[0.8, 1.0, 1.25]),
                      yaxis=dict(title="相対誤差（%）"))
    note = (
        "誤差は片側ではない。プットは S/K が大きい（K が平均より下）ほど高く出て、<br>"
        "コールは σ√T が小さい市場で K が平均より上のとき安く出る（ゼロキャリー S/K=0.8 で −2.89%）。<br>"
        "σ√T が大きいほど悪化するが、キャリーがマネーネスを動かすため σ√T だけでは順序が決まらない。<br>"
        "観測52日。参照価格は制御変量モンテカルロで、標準誤差は各点の誤差よりはるかに小さい。"
    )
    return _finish(fig, "asian_error", ["call", "put"], titles, note, legend_rows=3)


def _figures(path=None):
    """Build every §26.13 lesson figure from the saved data."""
    data = _load_data(path)
    return {
        "asian_payoff": _payoff_figure(data),
        "asian_distribution": _distribution_figure(data),
        "asian_observations": _observation_figure(data),
        "asian_error": _error_figure(data),
    }
