"""Verified market-price-of-risk figures shared by Book and offline portal (§28.1)."""

import hashlib
import json
import math
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-1/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_market_price_of_risk_reference.py",
    "scripts/verify_market_price_of_risk_numerics.py",
    "hullkit/src/hullkit/market_price_of_risk.py",
    "hullkit/src/hullkit/bsm.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")
_MARKET = "S=100, r=5%, σ=20%, 実世界μ=12%（λ=0.35）"
_Z95 = 1.959963984540054


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "28.1":
        raise ValueError("market price of risk reference requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("market price of risk reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("market price of risk source hashes missing")
    for name, expected in hashes.items():
        path = _PROJECT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"market price of risk source hash mismatch: {name}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(fig, key, title, x_title, y_title, market=_MARKET):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=80, r=35, t=80, b=145),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="28.1",
            figure=key,
            market=market,
            source="Hull GE pp.671–674; Example 28.2 printed, other inputs synthetic",
        ),
    )
    fig.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    fig.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return fig


def _line(data):
    fig = go.Figure()
    span = [-4.2, 4.2]
    for rows, lam, color, label in (
        (data["contracts"], data["figure"]["line"]["market_lambda"], _COLORS[0], "λ=0.35"),
        (
            data["negative_contracts"],
            data["figure"]["line"]["negative_lambda"],
            _COLORS[1],
            "λ=−0.1",
        ),
    ):
        fig.add_scatter(
            x=[r["loading"] for r in rows],
            y=[r["growth"] - r["r"] for r in rows],
            mode="markers",
            name=f"{label}の{len(rows)}請求権（独立求積）",
            text=[f"{r['kind']} K={r['K']:g} T={r['T']:g}" for r in rows],
            marker=dict(color=color, size=9),
            meta=dict(role="claims", market_lambda=lam),
        )
        fig.add_scatter(
            x=span,
            y=[lam * x for x in span],
            mode="lines",
            name=f"m−r = λs（{label}）",
            line=dict(color=color, dash="dash"),
            meta=dict(role="line", market_lambda=lam),
        )
    ex = data["examples"]["example_28_2"]
    fig.add_scatter(
        x=[ex["s1"], ex["s2"]],
        y=[ex["m1"] - ex["r"], ex["m2"] - ex["r"]],
        mode="markers",
        name="Example 28.2（λ=−0.15）",
        marker=dict(color=_COLORS[3], symbol="diamond", size=12),
        meta=dict(role="example"),
    )
    return _finish(
        fig,
        "mpr_line",
        "超過成長率は符号付きloadingに比例する（式28.9）",
        "符号付きloading s（年^−1/2）",
        "超過成長率 m − r（年率）",
        _MARKET + "; second market μ=2%, σ=30%",
    )


def _riskless(data):
    fig = go.Figure()
    for row, color, label in zip(
        data["riskless"], _COLORS, ("call＋put（K=100, T=1）", "cash call＋asset put"), strict=False
    ):
        fig.add_scatter(
            x=row["steps"],
            y=row["residual_std_ratio"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=3),
            meta=dict(role="pair"),
        )
    first = data["riskless"][0]
    scale = first["residual_std_ratio"][-1] / math.sqrt(first["steps"][-1])
    fig.add_scatter(
        x=first["steps"],
        y=[scale * math.sqrt(h) for h in first["steps"]],
        mode="lines",
        name="√h の傾き",
        line=dict(color="gray", dash="dot"),
        meta=dict(role="sqrt"),
    )
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return _finish(
        fig,
        "mpr_riskless",
        "無リスクportfolioのΔΠの標準偏差（片脚との比）",
        "保有期間 h（年、対数）",
        "std(ΔΠ) / std(片脚)（対数）",
    )


def _worlds(data):
    d, market = data["figure"]["densities"], data["market"]
    fig = go.Figure()
    xs = [math.exp(x) for x in d["log_spot"]]
    for lam, density, color in zip(d["lambdas"], d["density"], _COLORS, strict=True):
        fig.add_scatter(
            x=xs,
            y=density,
            mode="lines",
            name=f"λ={lam:g}：drift r+λσ={market['r'] + lam * market['sigma']:.0%}",
            line=dict(color=color, width=3),
            meta=dict(role="density", world_lambda=lam),
        )
    fig.update_xaxes(type="log")
    return _finish(
        fig,
        "mpr_worlds",
        "λを選ぶと平均だけが動き、ln S_T の幅は同じ（式28.10）",
        "1年後の株価 S_T（対数軸）",
        "ln S_T の確率密度",
        _MARKET + "; varying λ, T=1",
    )


def _validation(data):
    rows = data["mc"]["worlds"]
    fig = go.Figure()
    xs = [f"λ={r['world_lambda']:g}" for r in rows]
    for key, se, color, label in (
        ("direct_mean", "direct_se", _COLORS[0], "各世界で直接標本（95%区間）"),
        ("reweighted_mean", "reweighted_se", _COLORS[2], "Pの標本を尤度比で再重み付け（95%区間）"),
    ):
        fig.add_bar(
            x=xs,
            y=[r[key] for r in rows],
            name=label,
            marker_color=color,
            error_y=dict(type="data", array=[_Z95 * r[se] for r in rows], visible=True),
            meta=dict(role=key),
        )
    fig.add_scatter(
        x=xs,
        y=[r["analytic_mean"] for r in rows],
        mode="markers",
        name="解析値 S₀e^{(r+λσ)T}",
        marker=dict(color=_COLORS[1], symbol="diamond", size=11),
        meta=dict(role="analytic"),
    )
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[95, 120])
    return _finish(
        fig,
        "mpr_validation",
        "世界ごとの E[S_T]：直接標本・尤度比・解析値",
        "市場リスクの価格 λ",
        "E[S_T]（通貨）",
        _MARKET + "; seed281, 524288 paths, T=1",
    )


def _figures():
    data = _load_reference()
    return {
        "mpr_line": _line(data),
        "mpr_riskless": _riskless(data),
        "mpr_worlds": _worlds(data),
        "mpr_validation": _validation(data),
    }
