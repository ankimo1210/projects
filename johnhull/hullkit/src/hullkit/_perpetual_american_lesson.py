"""Four source-backed Book and portal figures for Hull GE §26.2."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-2/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = {
    "call": "#2563eb",
    "put": "#dc2626",
    "intrinsic": "#64748b",
    "spot": "#0f766e",
    "guide": "#94a3b8",
}
_CASE_NAMES = {
    "symmetric": "対称",
    "dividend_stock": "配当株",
    "standard_dividend": "標準",
    "high_yield_call_exercise": "高配当",
    "high_vol_put_exercise": "高ボラ",
    "zero_yield": "無配当",
}


def _load_reference(path=None, record_path=None):
    """Read only the independent reference approved by its hash record."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("perpetual American reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"perpetual American source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.2":
        raise ValueError("unsupported perpetual American reference section")
    if {case["label"] for case in data["cases"]} != set(_CASE_NAMES):
        raise ValueError("unsupported perpetual American reference cases")
    curve = data["figure"]
    if not all(
        len(curve[key]) == len(curve["spot_grid"])
        for key in ("call", "put", "call_intrinsic", "put_intrinsic")
    ):
        raise ValueError("perpetual American reference curve lengths differ")
    return data


def _case(data, label):
    return next(case for case in data["cases"] if case["label"] == label)


def _finish(fig, key, title, x_title=None, y_title=None):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=65, r=35, t=75, b=95),
        legend=dict(orientation="h", y=-0.29),
        meta={
            "section": "26.2",
            "figure": key,
            "source": "Hull GE §26.2 pp.615–616; saved independent reference",
        },
    )
    if x_title:
        fig.update_layout(xaxis_title=x_title)
    if y_title:
        fig.update_layout(yaxis_title=y_title)
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _value(data):
    curve = data["figure"]
    x = curve["spot_grid"]
    symmetric = _case(data, curve["label"])
    fig = go.Figure()
    for field, name, color, dash in (
        ("call", "永久コール価値", _COLORS["call"], "solid"),
        ("put", "永久プット価値", _COLORS["put"], "solid"),
        ("call_intrinsic", "コール即時行使価値", _COLORS["intrinsic"], "dash"),
        ("put_intrinsic", "プット即時行使価値", _COLORS["guide"], "dash"),
    ):
        fig.add_scatter(
            x=x,
            y=curve[field],
            mode="lines",
            name=name,
            line=dict(color=color, width=3 if "永久" in name else 2, dash=dash),
        )
    fig.add_scatter(
        x=[curve["call_boundary"]],
        y=[symmetric["call"]["boundary_intrinsic"]],
        mode="markers",
        name="コールの最適行使境界 H₁",
        marker=dict(color=_COLORS["call"], size=13, symbol="diamond"),
    )
    fig.add_scatter(
        x=[curve["put_boundary"]],
        y=[symmetric["put"]["boundary_intrinsic"]],
        mode="markers",
        name="プットの最適行使境界 H₂",
        marker=dict(color=_COLORS["put"], size=13, symbol="diamond"),
    )
    fig.update_layout(xaxis_range=[min(x), max(x)])
    return _finish(
        fig,
        "perpetual_value",
        "永久アメリカンの価値と行使境界",
        "現在の資産価格 S（通貨）",
        "オプション価値（通貨）",
    )


def _boundaries(data):
    cases = data["cases"]
    labels = [_CASE_NAMES[case["label"]] for case in cases]
    details = [
        f"{name}<br>S₀={case['parameters']['spot']:.0f}, K={case['parameters']['strike']:.0f}"
        f"<br>r={case['parameters']['rate']:.0%}, q={case['parameters']['yield']:.0%}, "
        f"σ={case['parameters']['sigma']:.0%}"
        for name, case in zip(labels, cases, strict=True)
    ]
    fig = go.Figure()
    for kind, name, color in (
        ("call", "コール H₁/K", _COLORS["call"]),
        ("put", "プット H₂/K", _COLORS["put"]),
    ):
        fig.add_bar(
            x=labels,
            y=[
                case[kind]["boundary"] / case["parameters"]["strike"]
                if case[kind]["boundary"] is not None
                else None
                for case in cases
            ],
            name=name,
            marker_color=color,
            customdata=details,
            hovertemplate="%{customdata}<br>%{fullData.name}=%{y:.3f}<extra></extra>",
            text=[
                f"{case[kind]['boundary'] / case['parameters']['strike']:.2f}"
                if case[kind]["boundary"] is not None
                else ""
                for case in cases
            ],
            textposition="outside",
            cliponaxis=False,
        )
    fig.add_scatter(
        x=labels,
        y=[case["parameters"]["spot"] / case["parameters"]["strike"] for case in cases],
        mode="markers",
        name="現在値 S₀/K",
        marker=dict(color=_COLORS["spot"], size=11, symbol="diamond"),
        customdata=details,
        hovertemplate="%{customdata}<br>%{fullData.name}=%{y:.3f}<extra></extra>",
    )
    fig.add_hline(y=1, line=dict(color=_COLORS["guide"], dash="dot"))
    fig.update_layout(barmode="group", yaxis_range=[0, 5.3])
    fig.add_annotation(
        x=labels[-1],
        y=2.0,
        text="H₁=∞",
        showarrow=False,
        font=dict(color=_COLORS["call"], size=12),
    )
    fig.update_xaxes(tickangle=0, tickfont=dict(size=10))
    return _finish(
        fig,
        "perpetual_boundaries",
        "永久オプションの最適行使境界",
        "保存参照の合成市場",
        "行使境界 / 行使価格",
    )


def _zero_dividend(data):
    curve = data["figure"]
    zero = _case(data, "zero_yield")
    strike = zero["parameters"]["strike"]
    grid = curve["spot_grid"]
    fig = go.Figure()
    fig.add_scatter(
        x=grid,
        y=grid,
        mode="lines",
        name="q=0 の永久コール V(S)=S",
        line=dict(color=_COLORS["call"], width=3),
    )
    fig.add_scatter(
        x=grid,
        y=[max(spot - strike, 0.0) for spot in grid],
        mode="lines",
        name="即時行使価値 (S−K)⁺",
        line=dict(color=_COLORS["intrinsic"], width=2, dash="dash"),
    )
    fig.add_scatter(
        x=[zero["parameters"]["spot"]],
        y=[zero["call"]["value"]],
        mode="markers",
        name="保存参照：S₀=100 で V=100",
        marker=dict(color=_COLORS["put"], size=12, symbol="diamond"),
    )
    fig.update_layout(xaxis_range=[min(grid), max(grid)])
    return _finish(
        fig,
        "perpetual_zero_dividend",
        "無配当コール：有限の最適行使境界はなく、永久価値は S",
        "現在の資産価格 S（通貨）",
        "コール価値（通貨）",
    )


def _convergence(data):
    symmetric = _case(data, "symmetric")
    rows = symmetric["lattice"]["rows"]
    maturities = [row["maturity"] for row in rows]
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["有限満期の American 価格", "永久価値との差"],
        horizontal_spacing=0.17,
    )
    for kind, name, color in (
        ("call", "コール", _COLORS["call"]),
        ("put", "プット", _COLORS["put"]),
    ):
        fig.add_scatter(
            x=maturities,
            y=[row[kind] for row in rows],
            mode="lines+markers",
            name=f"{name}：CRR",
            line=dict(color=color, width=2.5),
            marker=dict(size=9, symbol="circle" if kind == "call" else "circle-open"),
            row=1,
            col=1,
        )
    for kind, name, color in (
        ("call", "コール", _COLORS["call"]),
        ("put", "プット", _COLORS["put"]),
    ):
        fig.add_scatter(
            x=maturities,
            y=[symmetric[kind]["value"]] * len(rows),
            mode="lines",
            name=f"{name}：永久極限",
            line=dict(color=color, width=2, dash="dash"),
            row=1,
            col=1,
        )
    for kind, name, color in (
        ("call", "コール", _COLORS["call"]),
        ("put", "プット", _COLORS["put"]),
    ):
        fig.add_scatter(
            x=maturities,
            y=[row[f"{kind}_gap"] for row in rows],
            mode="lines+markers",
            name=f"{name}：差",
            line=dict(color=color, width=2.5),
            marker=dict(size=9, symbol="circle" if kind == "call" else "circle-open"),
            showlegend=False,
            row=1,
            col=2,
        )
    fig.update_xaxes(title_text="満期（年）", tickvals=maturities, row=1, col=1)
    fig.update_xaxes(title_text="満期（年）", tickvals=maturities, row=1, col=2)
    fig.update_yaxes(title_text="現在価値（通貨）", rangemode="tozero", row=1, col=1)
    fig.update_yaxes(
        title_text="永久価値 − 有限満期価格（通貨）",
        type="log",
        tickmode="array",
        tickvals=[0.02, 0.1, 0.5, 2.0],
        ticktext=["0.02", "0.1", "0.5", "2"],
        row=1,
        col=2,
    )
    fig.update_annotations(font_size=13)
    return _finish(
        fig,
        "perpetual_convergence",
        "有限満期ツリーと永久価値",
    )


def _figures(path=None):
    """Build the four shared figures solely from checked independent data."""
    data = _load_reference(path)
    return {
        "perpetual_value": _value(data),
        "perpetual_boundaries": _boundaries(data),
        "perpetual_zero_dividend": _zero_dividend(data),
        "perpetual_convergence": _convergence(data),
    }
