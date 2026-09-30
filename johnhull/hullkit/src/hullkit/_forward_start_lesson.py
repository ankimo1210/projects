"""Saved-data plots for Hull GE §26.5, shared by Book and offline portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-5/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = ("#2563eb", "#dc2626", "#0f766e")
_GREY = "#64748b"
_SOURCES = {
    "scripts/build_forward_start_reference.py",
    "scripts/verify_forward_start_numerics.py",
    "hullkit/src/hullkit/forward_start.py",
    "hullkit/src/hullkit/bsm.py",
}


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "26.5":
        raise ValueError("forward-start reference requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("forward-start reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("forward-start source hashes missing")
    for relative, expected in hashes.items():
        file = _PROJECT / relative
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f"forward-start source hash mismatch: {relative}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(figure, key, title, x_title, y_title):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=80, r=35, t=80, b=120),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="26.5", figure=key, source="Hull GE p.618; synthetic two-time GBM references"
        ),
    )
    figure.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    figure.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return figure


def _contract(data):
    row = data["figure"]["contract"]
    figure = go.Figure()
    start, expiry = row["market"]["T1"], row["market"]["T2"]
    for path, color in zip(row["paths"], _COLORS, strict=True):
        name = path["label"]
        figure.add_scatter(
            x=row["time"],
            y=path["stock"],
            name=f"経路{name}",
            mode="lines",
            line=dict(color=color, width=3),
            meta=dict(role=f"stock-{name}"),
        )
        figure.add_scatter(
            x=[start, expiry],
            y=[path["strike"]] * 2,
            mode="lines",
            showlegend=False,
            line=dict(color=color, dash="dash", width=2),
            name=f"行使価格{name}",
            meta=dict(role=f"strike-{name}"),
        )
        figure.add_scatter(
            x=[start],
            y=[path["strike"]],
            mode="markers",
            showlegend=False,
            marker=dict(color=color, size=9),
            name=f"fixing {name}",
            meta=dict(role=f"fixing-{name}"),
        )
    figure.add_vline(x=start, line_dash="dot", line_color=_GREY)
    return _finish(
        figure,
        "forward_contract",
        "開始時点の株価が行使価格を決める",
        "時点（年）",
        "株価・行使価格（通貨）",
    )


def _homogeneity(data):
    row = data["figure"]["homogeneity"]
    figure = go.Figure()
    figure.add_scatter(
        x=row["spot"],
        y=row["price"],
        mode="lines",
        name="開始時点のATMコール価値",
        line=dict(color=_COLORS[0], width=3),
        meta=dict(role="conditional-value"),
    )
    at_spot = row["spot"].index(100)
    figure.add_scatter(
        x=[100],
        y=[row["price"][at_spot]],
        mode="markers",
        showlegend=False,
        marker=dict(color=_GREY, size=10),
        meta=dict(role="reference-spot"),
    )
    return _finish(
        figure,
        "forward_homogeneity",
        "開始時点の価値は株価に比例",
        "開始時点の株価 S₁（通貨）",
        "開始時点の価値（通貨）",
    )


def _sweep(data, field, key, title):
    figure = go.Figure()
    for row, color in zip(data["figure"][field], _COLORS, strict=True):
        figure.add_scatter(
            x=row["start"],
            y=row["price"],
            mode="lines",
            name=f"q={row['q']:.0%}",
            line=dict(color=color, width=3),
            meta=dict(role=f"q-{row['q']:g}"),
        )
    if field == "fixed_expiry":
        mc = data["mc"]
        figure.add_scatter(
            x=[row["T1"] for row in mc],
            y=[row["price"] for row in mc],
            mode="markers",
            name="MC q=3%（95%区間）",
            marker=dict(color=_GREY, size=8),
            error_y=dict(
                type="data",
                array=[1.959963984540054 * row["standard_error"] for row in mc],
                visible=True,
            ),
            meta=dict(role="mc"),
        )
    return _finish(figure, key, title, "開始時点 T₁（年）", "現在価値（通貨）")


def _figures():
    data = _load_reference()
    return dict(
        forward_contract=_contract(data),
        forward_homogeneity=_homogeneity(data),
        forward_start_delay=_sweep(data, "delay", "forward_start_delay", "τ=1年固定：開始日の影響"),
        forward_fixed_expiry=_sweep(
            data, "fixed_expiry", "forward_fixed_expiry", "T₂=2年固定：残り期間が縮む"
        ),
    )
