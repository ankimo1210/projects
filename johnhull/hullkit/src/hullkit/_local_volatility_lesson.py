"""Four shared Book and portal figures for Hull 11e GE §27.3."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-3/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = ("#1f77b4", "#0f766e", "#d62728")


def _load_reference(path=None, record_path=None):
    """Load a reference only when its digest and source records still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("local-volatility reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"local-volatility source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.3" or len(data["pde_repricing"]) != 9:
        raise ValueError("unsupported §27.3 reference")
    return data


def _finish(fig, key, title, x_title, y_title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=70, r=35, t=72, b=75),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "27.3",
            "figure": key,
            "source": "Hull GE §27.3; saved independent synthetic reference",
        },
    )
    return fig


def _smile(data):
    fig = go.Figure()
    for maturity, color in zip(data["maturities"], _COLORS, strict=True):
        fig.add_scatter(
            x=data["strikes"],
            y=[100 * v for v in data["slices"][str(maturity)]["implied_vols"]],
            name=f"T={maturity:g}年",
            line=dict(color=color, width=2.8),
        )
    return _finish(
        fig, "ivf_smile", "合成市場の欧州コールから逆算した IV", "行使価格 K", "BSM 逆算 IV（%）"
    )


def _local(data):
    fig = go.Figure()
    for maturity, color in zip(data["maturities"], _COLORS, strict=True):
        fig.add_scatter(
            x=data["strikes"],
            y=[100 * v for v in data["slices"][str(maturity)]["local_vols"]],
            name=f"T={maturity:g}年",
            line=dict(color=color, width=2.8),
        )
    return _finish(
        fig, "ivf_local", "Dupire 局所ボラ：IV と同じ値ではない", "状態 S=K", "局所ボラ σloc（%）"
    )


def _repricing(data):
    rows = data["pde_repricing"]
    fig = go.Figure()
    fig.add_scatter(
        x=[r["market_call"] for r in rows],
        y=[r["local_vol_pde_call"] for r in rows],
        text=[f"K={r['strike']:g}, T={r['maturity']:g}" for r in rows],
        mode="markers",
        name="後退 PDE",
        marker=dict(size=10, color=_COLORS[0]),
        hovertemplate="%{text}<br>合成市場 %{x:.4f}<br>PDE %{y:.4f}<extra></extra>",
    )
    extent = [min(r["market_call"] for r in rows), max(r["market_call"] for r in rows)]
    fig.add_scatter(
        x=extent, y=extent, mode="lines", name="一致線", line=dict(color="#86868b", dash="dash")
    )
    return _finish(
        fig,
        "ivf_repricing",
        "局所ボラ PDE による欧州価格の再現",
        "合成市場のコール価格",
        "局所ボラ PDE 価格",
    )


def _joint(data):
    result = data["two_date_models"]["both_dates_up"]
    values = [result["latent_probability"], result["local_probability"]]
    fig = go.Figure(
        go.Bar(
            x=["潜在ボラ混合", "局所ボラ"],
            y=values,
            name="両時点で S>100",
            marker_color=list(_COLORS[:2]),
            text=[f"{v:.2%}" for v in values],
            textposition="outside",
            error_y=dict(
                type="data", array=[2 * result["paired_standard_error"]] * 2, visible=True
            ),
        )
    )
    fig.update_yaxes(range=[0, 0.45])
    return _finish(
        fig, "ivf_joint", "同じバニラ面、異なる二時点確率", "価格過程", "両時点で S>100 の確率"
    )


def _figures(path=None):
    """Build four figures from the single checked reference for both surfaces."""
    data = _load_reference(path)
    return {
        "ivf_smile": _smile(data),
        "ivf_local": _local(data),
        "ivf_repricing": _repricing(data),
        "ivf_joint": _joint(data),
    }
