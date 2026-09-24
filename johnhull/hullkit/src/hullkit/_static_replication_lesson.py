"""Saved-data Plotly lesson for Hull 11e GE §26.17 static options replication."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-17/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE, _RED, _GREEN, _GRAY = "#1f77b4", "#d62728", "#0f766e", "#86868b"


def _load_reference(path=None, record_path=None):
    """Reject altered or stale reference values before displaying any figure."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != record.get("artifact_sha256"):
        raise ValueError("static replication reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"static replication source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.17" or set(data.get("ladders", {})) != {"3", "18", "100"}:
        raise ValueError("unsupported static replication reference")
    return data


def _finish(fig, key, title, x_title, y_title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=440,
        margin=dict(l=65, r=25, t=85, b=70),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.25),
        meta={
            "section": "26.17",
            "figure": key,
            "source": "Hull GE Table 26.1; saved independent reference",
        },
    )
    return fig


def _boundary(data):
    market = data["market"]
    expiry, barrier, strike = (market[name] for name in ("expiry", "barrier", "strike"))
    nodes = sorted(data["ladders"]["3"]["boundary_nodes"])
    fig = go.Figure()
    fig.add_scatter(
        x=[0, expiry],
        y=[barrier, barrier],
        name="ノックアウト境界 S=60",
        line=dict(color=_RED, width=3),
    )
    fig.add_scatter(
        x=[expiry, expiry], y=[0, barrier], name="満期 T=0.75", line=dict(color=_GRAY, dash="dash")
    )
    fig.add_scatter(
        x=nodes,
        y=[barrier] * len(nodes),
        mode="markers",
        name="3点の照合位置",
        marker=dict(color=_BLUE, size=11),
    )
    fig.add_scatter(
        x=[0],
        y=[market["spot"]],
        mode="markers",
        name="開始点 S₀=50",
        marker=dict(color=_GREEN, size=12),
    )
    fig.update_layout(yaxis_range=[strike - 5, barrier + 5], xaxis_range=[-0.03, expiry + 0.03])
    return _finish(
        fig, "static_boundary", "満期境界とバリア境界を合わせる", "時刻（年）", "株価（通貨）"
    )


def _ladder(data):
    row = data["ladders"]["3"]
    fig = go.Figure()
    fig.add_bar(
        x=["A: K50 / 9か月", "B: K60 / 9か月", "C: K60 / 6か月", "D: K60 / 3か月"],
        y=row["leg_values"],
        marker_color=[_BLUE if value >= 0 else _RED for value in row["leg_values"]],
        text=[f"{value:+.2f}" for value in row["leg_values"]],
        textposition="outside",
        name="各脚の現在価値",
    )
    fig.add_hline(y=0, line_color=_GRAY)
    fig.add_annotation(
        x=0.99,
        y=0.96,
        xref="paper",
        yref="paper",
        showarrow=False,
        text=f"合計 {row['initial_value']:.3f}（印刷値 0.73）",
        xanchor="right",
    )
    return _finish(
        fig, "static_ladder", "Table 26.1：4本の欧州コール", "オプションの脚", "現在価値（通貨）"
    )


def _boundary_error(data):
    fig = go.Figure()
    colors = (_BLUE, _RED, _GREEN)
    buttons = []
    for index, steps in enumerate((3, 18, 100)):
        curve = data["ladders"][str(steps)]["boundary_curve"]
        values = [point["value"] for point in curve]
        fig.add_scatter(
            x=[point["time"] for point in curve],
            y=values,
            mode="lines",
            name=f"{steps}点",
            visible=index == 0,
            line=dict(color=colors[index], width=2.5),
        )
        extent = max(abs(min(values)), abs(max(values))) * 1.12
        buttons.append(
            dict(
                label=f"{steps}点",
                method="update",
                args=[
                    {"visible": [i == index for i in range(3)]},
                    {"yaxis.range": [-extent, extent]},
                ],
            )
        )
    initial_curve = data["ladders"]["3"]["boundary_curve"]
    extent = max(abs(point["value"]) for point in initial_curve) * 1.12
    fig.update_layout(
        updatemenus=[dict(buttons=buttons, direction="down", x=0.98, y=1.16, xanchor="right")],
        yaxis_range=[-extent, extent],
    )
    fig.add_hline(y=0, line_color=_GRAY, line_dash="dot")
    return _finish(
        fig,
        "static_boundary_error",
        "バリア S=60 上：節点間の複製残差",
        "時刻（年）",
        "ヘッジの価値（通貨）",
    )


def _convergence(data):
    steps = (3, 18, 100)
    values = [data["ladders"][str(n)]["initial_value"] for n in steps]
    analytic = data["analytic_barrier_price"]
    fig = go.Figure()
    fig.add_scatter(
        x=steps,
        y=values,
        mode="lines+markers+text",
        text=[f"{value:.3f}" for value in values],
        textposition="top center",
        name="静的複製",
        line=dict(color=_BLUE, width=3),
    )
    fig.add_scatter(
        x=steps,
        y=[analytic] * 3,
        mode="lines",
        name=f"連続監視の解析値 {analytic:.4f}",
        line=dict(color=_RED, dash="dash", width=2.5),
    )
    fig.update_layout(xaxis_type="log", xaxis_tickvals=list(steps), yaxis_range=[0.25, 0.82])
    return _finish(
        fig,
        "static_convergence",
        "照合節点を増やすと解析値へ近づく",
        "バリア境界の照合点数",
        "初期価値（通貨）",
    )


def _figures(path=None):
    """Build four shared figures from checked-in numerical values only."""
    data = _load_reference(path)
    return {
        "static_boundary": _boundary(data),
        "static_ladder": _ladder(data),
        "static_boundary_error": _boundary_error(data),
        "static_convergence": _convergence(data),
    }
