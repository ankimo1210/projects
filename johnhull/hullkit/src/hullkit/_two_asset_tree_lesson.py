"""Four shared Book and portal figures for Hull GE §27.7."""

import hashlib
import json
import math
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-7/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_METHODS = ("transform", "rubinstein", "adjusted")
_NAMES = {
    "transform": "変数変換",
    "rubinstein": "Rubinstein（非矩形）",
    "adjusted": "確率の調整",
}
_COLORS = {
    "transform": "#2563eb",
    "rubinstein": "#dc2626",
    "adjusted": "#0f766e",
    "reference": "#111827",
    "guide": "#94a3b8",
}
_SYMBOLS = {"transform": "circle", "rubinstein": "diamond", "adjusted": "square"}


def _load_reference(path=None, record_path=None):
    """Load the independent reference only while its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("two-asset reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"two-asset source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.7" or len(data["convergence"]["steps"]) != 181:
        raise ValueError("unsupported §27.7 reference")
    return data


def _finish(fig, key, title, x_title, y_title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=65, r=35, t=72, b=70),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "27.7",
            "figure": key,
            "source": "Hull GE §27.7 Tables 27.2–27.3; saved independent two-asset reference",
        },
    )
    fig.update_xaxes(title_standoff=12, automargin=True)
    fig.update_yaxes(title_standoff=12, automargin=True)
    return fig


def _with_probability(name, span):
    if name.endswith("）"):
        return f"{name[:-1]}、確率 {span}）"
    return f"{name}（確率 {span}）"


def _nodes(data):
    hand = data["hand_example"]
    v1, v2 = data["parameters"]["volatilities"]
    rho = data["parameters"]["correlation"]
    root = math.sqrt(hand["dt"])
    fig = go.Figure()
    for method in _METHODS:
        moves = hand[method]["moves"]
        probabilities = hand[method]["probabilities"]
        labelled = method == "adjusted"
        low, high = min(probabilities), max(probabilities)
        span = f"{low:.2f}" if high - low < 1e-12 else f"{low:.3f}–{high:.3f}"
        fig.add_scatter(
            x=[m[0] / (v1 * root) for m in moves],
            y=[m[1] / (v2 * root) for m in moves],
            mode="markers+text" if labelled else "markers",
            name=_NAMES[method] if labelled else _with_probability(_NAMES[method], span),
            text=[f"{p:.3f}" for p in probabilities] if labelled else None,
            textposition="middle left",
            marker=dict(
                color=_COLORS[method],
                symbol=_SYMBOLS[method],
                size=[10 + 48 * p for p in probabilities],
                line=dict(color="white", width=1),
            ),
        )
    angles = [2 * math.pi * i / 120 for i in range(121)]
    fig.add_scatter(
        x=[math.cos(a) for a in angles],
        y=[rho * math.cos(a) + math.sqrt(1 - rho**2) * math.sin(a) for a in angles],
        mode="lines",
        name=f"相関 ρ={rho} の1標準偏差の楕円",
        line=dict(color=_COLORS["reference"], dash="dot", width=1.5),
    )
    fig.update_xaxes(range=[-2.1, 2.1])
    fig.update_yaxes(range=[-1.8, 1.8], scaleanchor="x", scaleratio=1)
    return _finish(
        fig,
        "two_asset_nodes",
        "1ステップの4つの枝（点の大きさ＝確率）",
        "Δln S1 / (σ1√Δt)",
        "Δln S2 / (σ2√Δt)",
    )


def _convergence(data):
    rows = data["convergence"]
    reference = data["analytic"]["american_exchange"]["value"]
    fig = go.Figure()
    for method in _METHODS:
        fig.add_scatter(
            x=rows["steps"],
            y=rows["american"][method],
            mode="lines",
            name=_NAMES[method],
            line=dict(color=_COLORS[method], width=2),
        )
    fig.add_scatter(
        x=[rows["steps"][0], rows["steps"][-1]],
        y=[reference, reference],
        mode="lines",
        name=f"1次元に帰着した基準 {reference:.4f}",
        line=dict(color=_COLORS["reference"], dash="dash", width=2),
    )
    return _finish(
        fig,
        "two_asset_convergence",
        "米国型の交換オプション：時間ステップ数と価格",
        "時間ステップ数 N",
        "オプション価格 ($)",
    )


def _errors(data):
    rows = data["errors"]
    steps = rows["steps"]
    fig = go.Figure()
    for method in _METHODS:
        fig.add_scatter(
            x=steps,
            y=[abs(e) for e in rows[f"{method}_max_call"]],
            mode="lines+markers",
            name=_NAMES[method],
            line=dict(color=_COLORS[method], width=2),
            marker=dict(symbol=_SYMBOLS[method], size=8),
        )
    start = abs(rows["transform_max_call"][0])
    fig.add_scatter(
        x=[steps[0], steps[-1]],
        y=[start, start * steps[0] / steps[-1]],
        mode="lines",
        name="1/N の傾き",
        line=dict(color=_COLORS["guide"], dash="dot", width=1.5),
    )
    fig.update_xaxes(type="log", tickvals=steps)
    fig.update_yaxes(type="log", exponentformat="power")
    return _finish(
        fig,
        "two_asset_errors",
        "欧州型 max コール：Stulz の式との差",
        "時間ステップ数 N（対数目盛）",
        "|誤差| ($、対数目盛)",
    )


def _correlation(data):
    rows = data["correlation"]
    fig = go.Figure()
    for method in _METHODS:
        fig.add_scatter(
            x=rows["rho"],
            y=rows[method],
            mode="lines+markers",
            name=f"{_NAMES[method]}（{rows['steps']}段）",
            line=dict(color=_COLORS[method], width=2),
            marker=dict(symbol=_SYMBOLS[method], size=6),
        )
    for method in _METHODS:
        fig.add_scatter(
            x=rows["rho"],
            y=rows[f"{method}_odd"],
            mode="lines",
            name=f"{_NAMES[method]}（{rows['odd_steps']}段）",
            line=dict(color=_COLORS[method], width=1.2, dash="dot"),
        )
    fig.add_hline(y=0, line=dict(color=_COLORS["reference"], width=1))
    return _finish(
        fig,
        "two_asset_correlation",
        f"欧州型 max コール：相関と誤差（{rows['steps']}段・{rows['odd_steps']}段）",
        "相関 ρ",
        "Stulz の式との差 ($)",
    )


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "two_asset_nodes": _nodes(data),
        "two_asset_convergence": _convergence(data),
        "two_asset_errors": _errors(data),
        "two_asset_correlation": _correlation(data),
    }
