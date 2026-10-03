"""Verified simple chooser figures shared by Book and offline portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-8/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_chooser_reference.py",
    "scripts/verify_chooser_numerics.py",
    "hullkit/src/hullkit/chooser.py",
    "hullkit/src/hullkit/bsm.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")
_MARKET = "S=100, K=100, r=5%, q=2%, σ=20%, T1=.5, T2=1"


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "26.8":
        raise ValueError("chooser reference requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("chooser reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("chooser source hashes missing")
    for name, expected in hashes.items():
        path = _PROJECT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"chooser source hash mismatch: {name}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(fig, key, title, x_title, y_title, market=_MARKET):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=80, r=35, t=80, b=145),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="26.8",
            figure=key,
            market=market,
            source="Hull GE pp.619–620; synthetic European GBM contracts",
        ),
    )
    fig.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    fig.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return fig


def _curve(data, name, key, title, axis, xlabel, roles, ylabel):
    row = data["figure"][name]
    fig = go.Figure()
    for role, color in zip(roles, _COLORS, strict=False):
        fig.add_scatter(
            x=row[axis],
            y=row[role],
            mode="lines+markers" if name == "timing" else "lines",
            name={
                "chosen": "選択価値 max(c₁,p₁)",
                "extra_put": "追加put脚（枚数w）",
                "immediate": "今すぐ選択 max(c₀,p₀)",
                "straddle": "満期選択 straddle",
            }.get(role, role),
            line=dict(color=color, width=3),
            meta=dict(role=role),
        )
    if name == "choice":
        maximum = max(row["chosen"])
        fig.add_scatter(
            x=[row["boundary"]] * 2,
            y=[0, maximum],
            mode="lines",
            name="選択境界 H",
            line=dict(color="gray", dash="dash"),
            meta=dict(role="boundary"),
        )
    market = _MARKET
    if name == "package":
        market += "; H=98.511194, w=0.990050; varying S₀"
    if name == "timing":
        market += "; varying T1"
    return _finish(fig, key, title, xlabel, ylabel, market)


def _validation(data):
    rows = data["mc"]
    fig = go.Figure()
    xs = [str(row["T1"]) for row in rows]
    fig.add_bar(
        x=xs,
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
        x=xs,
        y=[row["reference_price"] for row in rows],
        mode="markers",
        name="独立T1密度求積",
        marker=dict(color=_COLORS[1], symbol="diamond", size=10),
        meta=dict(role="integral"),
    )
    return _finish(
        fig,
        "chooser_validation",
        "選択時期別の独立求積・条件付きMC",
        "選択時点 T₁（年）",
        "現在価値（通貨）",
        _MARKET + "; varying T1",
    )


def _figures():
    data = _load_reference()
    return {
        "chooser_choice": _curve(
            data,
            "choice",
            "chooser_choice",
            "T1のcall・put価値と選択境界",
            "spot",
            "T1株価 S₁（通貨）",
            ("call", "put", "chosen"),
            "T1価値（通貨）",
        ),
        "chooser_package": _curve(
            data,
            "package",
            "chooser_package",
            "call一枚と配当調整putの複製",
            "spot",
            "現在株価 S₀（通貨）",
            ("call", "extra_put", "chooser"),
            "現在価値（通貨）",
        ),
        "chooser_timing": _curve(
            data,
            "timing",
            "chooser_timing",
            "選択を遅らせる権利と二つの限界",
            "T1",
            "選択時点 T₁（年）",
            ("chooser", "immediate", "straddle"),
            "現在価値（通貨）",
        ),
        "chooser_validation": _validation(data),
    }
