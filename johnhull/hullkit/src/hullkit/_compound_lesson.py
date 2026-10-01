"""Verified four-contract compound figures shared by Book and offline portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-7/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_compound_reference.py",
    "scripts/verify_compound_numerics.py",
    "hullkit/src/hullkit/compound.py",
    "hullkit/src/hullkit/bsm.py",
}
_KINDS = ("call_on_call", "put_on_call", "call_on_put", "put_on_put")
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")
_MARKET = "S=100, K1=10, K2=100, r=5%, q=2%, σ=20%, T1=.5, T2=1"


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "26.7":
        raise ValueError("compound reference requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("compound reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("compound source hashes missing")
    for name, expected in hashes.items():
        path = _PROJECT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"compound source hash mismatch: {name}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(fig, key, title, x_title, y_title, market=_MARKET):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=80, r=35, t=80, b=145),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="26.7",
            figure=key,
            market=market,
            source="Hull GE pp.618–619; synthetic European GBM contracts",
        ),
    )
    fig.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    fig.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return fig


def _threshold(data):
    row = data["figure"]["threshold"]
    fig = go.Figure()
    for inner, color in zip(("call", "put"), _COLORS[:2], strict=True):
        fig.add_scatter(
            x=row["spot"],
            y=row[inner],
            name="内側" + inner,
            mode="lines",
            line=dict(color=color, dash="dot"),
            meta=dict(role=inner),
        )
    for kind, color in zip(_KINDS, _COLORS, strict=True):
        fig.add_scatter(
            x=row["spot"],
            y=row[kind],
            name=kind,
            mode="lines",
            line=dict(color=color, width=3),
            meta=dict(role=kind),
        )
    maximum = max(max(row[inner]) for inner in ("call", "put"))
    for inner in ("call", "put"):
        root = row["critical"][inner]
        fig.add_scatter(
            x=[root, root],
            y=[0, maximum],
            mode="lines",
            name="S* " + inner,
            line=dict(color="gray", dash="dash"),
            showlegend=False,
            meta=dict(role="critical-" + inner),
        )
    fig.add_scatter(
        x=row["spot"],
        y=[10] * len(row["spot"]),
        mode="lines",
        name="K1=10",
        line=dict(color="gray", dash="dot"),
        showlegend=False,
        meta=dict(role="strike"),
    )
    return _finish(
        fig,
        "compound_threshold",
        "T1の内側価値・外側給付と臨界株価",
        "T1株価 S₁（通貨）",
        "T1価値・給付（通貨）",
    )


def _curve(data, name, key, title, axis, x_title):
    row = data["figure"][name]
    fig = go.Figure()
    for kind, color in zip(_KINDS, _COLORS, strict=True):
        fig.add_scatter(
            x=row[axis],
            y=row[kind],
            mode="lines+markers",
            name=kind,
            line=dict(color=color, width=3),
            meta=dict(role=kind),
        )
    if name == "strikes":
        bound = row["put_bound"]
        fig.add_scatter(
            x=[bound, bound],
            y=[0, max(max(row[k]) for k in _KINDS)],
            mode="lines",
            line=dict(color="gray", dash="dash"),
            name="内側put上限",
            showlegend=False,
            meta=dict(role="put_bound"),
        )
    return _finish(fig, key, title, x_title, "現在価値（通貨）", _MARKET + "; varying " + axis)


def _validation(data):
    fig = go.Figure()
    rows = data["mc"]
    fig.add_bar(
        x=list(range(4)),
        y=[row["price"] for row in rows],
        name="条件付きMC（95%区間）",
        marker_color=_COLORS[0],
        error_y=dict(
            type="data",
            array=[1.959963984540054 * row["standard_error"] for row in rows],
            visible=True,
        ),
        meta=dict(role="mc"),
    )
    fig.add_scatter(
        x=list(range(4)),
        y=[row["reference_price"] for row in rows],
        mode="markers",
        name="独立T1密度求積",
        marker=dict(color=_COLORS[1], symbol="diamond", size=10),
        meta=dict(role="integral"),
    )
    fig.update_xaxes(tickvals=list(range(4)), ticktext=["C/C", "P/C", "C/P", "P/P"])
    return _finish(
        fig,
        "compound_validation",
        "独立求積と条件付きMC・平均の95%区間",
        "外側 / 内側 option",
        "現在価値（通貨）",
    )


def _figures():
    data = _load_reference()
    return dict(
        compound_threshold=_threshold(data),
        compound_strikes=_curve(
            data,
            "strikes",
            "compound_strikes",
            "外側K1と内側putの価値上限",
            "K1",
            "第1行使価格 K1（通貨）",
        ),
        compound_timing=_curve(
            data,
            "timing",
            "compound_timing",
            "T2=1年固定・第1行使日の比較",
            "T1",
            "第1行使時点 T1（年）",
        ),
        compound_validation=_validation(data),
    )
