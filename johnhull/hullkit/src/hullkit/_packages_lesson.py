"""Four shared Book and portal figures for Hull GE §26.1."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-1/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = {
    "forward": "#64748b",
    "range_forward": "#2563eb",
    "break_forward": "#dc2626",
    "call": "#0f766e",
    "guide": "#94a3b8",
    "reference": "#111827",
}
_NAMES = {
    "forward": "先渡し",
    "range_forward": "レンジ先渡し",
    "break_forward": "ブレークフォワード",
}


def _load_reference(path=None, record_path=None):
    """Load the independent reference only while its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("packages reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"packages source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.1" or len(data["figure_payoffs"]["grid"]) != 141:
        raise ValueError("unsupported §26.1 reference")
    return data


def _finish(fig, key, title, x_title=None, y_title=None):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=65, r=35, t=72, b=70),
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "26.1",
            "figure": key,
            "source": "Hull GE §26.1 pp.614–615 and §17.2; saved independent reference",
        },
    )
    if x_title is not None:
        fig.update_layout(xaxis_title=x_title, yaxis_title=y_title)
    fig.update_xaxes(title_standoff=12, automargin=True)
    fig.update_yaxes(title_standoff=12, automargin=True)
    return fig


def _strikes(data):
    curve = data["strike_curve"]
    anchor = data["anchor_17_2"]
    forward = curve["forward"]
    fig = go.Figure()
    fig.add_scatter(
        x=[p["put_strike"] for p in curve["points"]],
        y=[p["call_strike"] for p in curve["points"]],
        mode="lines",
        name="c(K2) = p(K1) を満たす K2",
        line=dict(color=_COLORS["range_forward"], width=3),
    )
    low, high = curve["points"][0]["put_strike"], forward
    fig.add_scatter(
        x=[low, high],
        y=[low, high],
        mode="lines",
        name="K2 = K1",
        line=dict(color=_COLORS["guide"], dash="dash", width=2),
    )
    fig.add_scatter(
        x=[low, high],
        y=[forward, forward],
        mode="lines",
        name=f"先渡し価格 F = {forward:.4f}",
        line=dict(color=_COLORS["forward"], dash="dot", width=2),
    )
    fig.add_scatter(
        x=[anchor["put_strike"]],
        y=[anchor["call_strike"]],
        mode="markers",
        name=(
            f"原典 §17.2：K1 = {anchor['put_strike']:.4f} のとき K2 = {anchor['call_strike']:.4f}"
        ),
        marker=dict(color=_COLORS["break_forward"], size=12, symbol="diamond"),
    )
    fig.add_scatter(
        x=[forward],
        y=[forward],
        mode="markers",
        name="K1 = F：先渡しそのもの（K2 = F）",
        marker=dict(color=_COLORS["reference"], size=10, symbol="circle-open", line=dict(width=2)),
    )
    return _finish(
        fig,
        "packages_strikes",
        "ゼロコストのレンジ先渡し：K1 を決めると K2 が決まる",
        "売りプットの行使価格 K1",
        "買いコールの行使価格 K2",
    )


def _range_forward(data):
    payoff = data["figure_payoffs"]
    fig = go.Figure()
    fig.add_scatter(
        x=payoff["grid"],
        y=payoff["payoffs"]["forward"],
        mode="lines",
        name=f"先渡し（受渡価格 F = {payoff['forward_price']:.4f}）",
        line=dict(color=_COLORS["forward"], dash="dash", width=2),
    )
    fig.add_scatter(
        x=payoff["grid"],
        y=payoff["payoffs"]["range_forward"],
        mode="lines",
        name=(f"レンジ先渡し（K2 = {payoff['call_strike']:.4f}、K1 = {payoff['put_strike']:.4f}）"),
        line=dict(color=_COLORS["range_forward"], width=3),
    )
    fig.add_scatter(
        x=[payoff["put_strike"], payoff["call_strike"]],
        y=[0.0, 0.0],
        mode="markers",
        name="行使価格 K1・K2（損益ゼロの区間の端）",
        marker=dict(
            color=_COLORS["range_forward"], size=10, symbol="circle-open", line=dict(width=2)
        ),
    )
    return _finish(
        fig,
        "packages_range_forward",
        "レンジ先渡しの満期損益：K1 と K2 の間は損益ゼロ",
        "満期の資産価格 S_T",
        "満期の損益",
    )


def _deferred(data):
    payoff = data["figure_payoffs"]
    fig = go.Figure()
    fig.add_scatter(
        x=payoff["grid"],
        y=payoff["payoffs"]["forward"],
        mode="lines",
        name=f"先渡し（F = {payoff['forward_price']:.4f}）",
        line=dict(color=_COLORS["forward"], dash="dash", width=2),
    )
    fig.add_scatter(
        x=payoff["grid"],
        y=payoff["payoffs"]["call"],
        mode="lines",
        name="コールの満期価値 max(S_T − K, 0)（K = F）",
        line=dict(color=_COLORS["call"], dash="dot", width=2),
    )
    fig.add_scatter(
        x=payoff["grid"],
        y=payoff["payoffs"]["break_forward"],
        mode="lines",
        name=f"後払いのコール＝ブレークフォワード（A = {payoff['amount']:.5f}）",
        line=dict(color=_COLORS["break_forward"], width=3),
    )
    fig.add_scatter(
        x=[payoff["breakeven"]],
        y=[0.0],
        mode="markers",
        name=f"損益分岐 K + A = {payoff['breakeven']:.4f}",
        marker=dict(color=_COLORS["break_forward"], size=11, symbol="diamond"),
    )
    return _finish(
        fig,
        "packages_deferred",
        "後払いのコール：最大損失は A、損益分岐は K + A",
        "満期の資産価格 S_T",
        "満期の損益",
    )


def _risk(data):
    risk = data["risk_comparison"]
    panels = (
        ("loss_pv_quadrature", "期待損失の<br>現在価値"),
        ("probability_of_loss", "損失確率<br>（リスク中立）"),
        ("max_loss", "最大損失<br>（対数目盛）"),
    )
    fig = make_subplots(rows=1, cols=3, subplot_titles=[label for _, label in panels])
    for column, (key, _) in enumerate(panels, start=1):
        for name in _NAMES:
            fig.add_bar(
                x=[_NAMES[name]],
                y=[risk[name][key]],
                name=_NAMES[name],
                legendgroup=name,
                showlegend=column == 1,
                marker=dict(color=_COLORS[name]),
                text=[f"{risk[name][key]:.3g}"],
                textfont=dict(size=10),
                textposition="outside",
                cliponaxis=False,
                row=1,
                col=column,
            )
    fig.update_yaxes(
        type="log",
        range=[-1.8, 0.3],
        tickvals=[0.01, 0.1, 1],
        ticktext=["0.01", "0.1", "1"],
        row=1,
        col=3,
    )
    fig.update_yaxes(range=[0.0, 0.8], row=1, col=2)
    fig.update_yaxes(rangemode="tozero", row=1, col=1)
    fig.update_xaxes(showticklabels=False)
    fig.update_layout(barmode="group", showlegend=True)
    fig.update_annotations(font_size=13)
    _finish(fig, "packages_risk", "費用ゼロでもリスクは違う（σ = 14%、T = 0.25）")
    fig.update_layout(margin=dict(t=112))
    return fig


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "packages_strikes": _strikes(data),
        "packages_range_forward": _range_forward(data),
        "packages_deferred": _deferred(data),
        "packages_risk": _risk(data),
    }
