"""Four saved-data Plotly figures for Hull 11e GE §27.1."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-1/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE, _RED, _GREEN, _GRAY = "#1f77b4", "#d62728", "#0f766e", "#86868b"


def _load_reference(path=None, record_path=None):
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != record.get("artifact_sha256"):
        raise ValueError("alternative-model reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"alternative-model source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.1" or len(data["poisson_table"]["counts"]) != 9:
        raise ValueError("unsupported alternative-model reference")
    return data


def _finish(fig, key, title, x_title, y_title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=65, r=30, t=85, b=75),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "27.1",
            "figure": key,
            "source": "Hull GE §27.1; saved independent reference",
        },
    )
    return fig


def _cev(data):
    row = data["cev"]
    fig = go.Figure()
    for beta, color in (("0.7", _BLUE), ("1.0", _GRAY), ("1.3", _RED)):
        fig.add_scatter(
            x=row["spots"],
            y=[100 * value for value in row["local_vol"][beta]],
            name=f"β={beta}",
            line=dict(color=color, width=2.8),
        )
    fig.add_vline(x=row["spot"], line_color=_GREEN, line_dash="dot")
    return _finish(
        fig,
        "alternative_cev",
        "CEV：株価と局所ボラティリティ",
        "株価 S（通貨）",
        "局所ボラティリティ（%/√年）",
    )


def _merton(data):
    row = data["merton"]
    fig = go.Figure()
    fig.add_scatter(
        x=[strike / row["spot"] for strike in row["strikes"]],
        y=[100 * value for value in row["implied_vol"]],
        name="Merton（下向きジャンプ）",
        line=dict(color=_BLUE, width=3),
    )
    fig.add_hline(
        y=100 * row["sigma"], line_color=_GRAY, line_dash="dot", annotation_text="拡散部分 20%"
    )
    return _finish(
        fig, "alternative_merton", "Merton：ジャンプが作る短期スキュー", "K / S₀", "BSM逆算IV（%）"
    )


def _poisson(data):
    row = data["poisson_table"]
    fig = go.Figure()
    fig.add_bar(
        x=row["counts"],
        y=row["probability"],
        name="P(N=m)",
        marker_color=_BLUE,
        text=[f"{value:.4f}" for value in row["probability"]],
        textposition="outside",
    )
    fig.add_scatter(
        x=row["counts"],
        y=row["cumulative"],
        mode="lines+markers",
        name="P(N≤m)",
        line=dict(color=_RED, width=2.5),
        yaxis="y2",
    )
    fig.update_layout(
        yaxis2=dict(title="累積確率", overlaying="y", side="right", range=[0, 1.08]),
        xaxis=dict(dtick=1),
        yaxis=dict(range=[0, 0.43]),
    )
    return _finish(
        fig,
        "alternative_poisson",
        "Table 27.1：2年間のジャンプ回数（λ=0.5/年）",
        "ジャンプ回数 m",
        "確率 P(N=m)",
    )


def _vg(data):
    row = data["variance_gamma"]
    fig = go.Figure()
    fig.add_scatter(
        x=row["terminal_price_centers"],
        y=row["sample_density"],
        name="VG（seed=2701, 40万標本）",
        line=dict(color=_BLUE, width=2.6),
    )
    fig.add_scatter(
        x=row["terminal_price_centers"],
        y=row["bsm_density"],
        name="GBM 対数正規密度",
        line=dict(color=_RED, width=2.3, dash="dash"),
    )
    fig.update_layout(xaxis_range=[40, 200])
    return _finish(
        fig,
        "alternative_vg",
        "Figure 27.1：VG と GBM の満期株価分布",
        "満期株価 S_T（通貨）",
        "確率密度（通貨⁻¹）",
    )


def _figures(path=None):
    """Build the four identical Book and portal figures from checked data."""
    data = _load_reference(path)
    return {
        "alternative_cev": _cev(data),
        "alternative_merton": _merton(data),
        "alternative_poisson": _poisson(data),
        "alternative_vg": _vg(data),
    }
