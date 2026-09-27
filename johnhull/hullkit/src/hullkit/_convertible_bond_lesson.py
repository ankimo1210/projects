"""Four shared Book and portal figures for Hull GE §27.4."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-4/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE, _GREEN, _RED = "#2563eb", "#0f766e", "#dc2626"


def _load_reference(path=None, record_path=None):
    """Load the saved independent reference only when its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("convertible reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"convertible source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.4" or len(data["textbook"]["nodes"]) != 10:
        raise ValueError("unsupported §27.4 reference")
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
            "section": "27.4",
            "figure": key,
            "source": "Hull GE Figure 27.2; saved independent recursive reference",
        },
    )
    return fig


def _tree(data):
    nodes = data["textbook"]["nodes"]
    levels = (("A",), ("C", "B"), ("F", "E", "D"), ("J", "I", "H", "G"))
    fig = go.Figure()
    # Place nodes by branch position so small-screen labels cannot collide.
    for t in range(3):
        for up in range(t + 1):
            y = 2 * up - t
            for child_y in (y - 1, y + 1):
                fig.add_shape(
                    type="line",
                    x0=t,
                    y0=y,
                    x1=t + 1,
                    y1=child_y,
                    line=dict(color="#cbd5e1", width=1),
                    layer="below",
                )
    for t, names in enumerate(levels):
        fig.add_scatter(
            x=[t] * len(names),
            y=[2 * up - t for up in range(len(names))],
            customdata=[
                [nodes[name]["value"], nodes[name]["stock"], nodes[name]["decision"]]
                for name in names
            ],
            text=[
                f"{name}<br>S {nodes[name]['stock']:.2f}<br>CB {nodes[name]['value']:.2f}"
                for name in names
            ],
            mode="markers+text",
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate="%{text}<br>%{customdata[2]}<extra></extra>",
            marker=dict(
                size=11,
                color=[
                    _RED if nodes[name]["decision"].startswith("call") else _BLUE for name in names
                ],
            ),
            showlegend=False,
        )
    fig = _finish(fig, "cb_tree", "図27.2：株価・転換社債の3段ツリー", "経過年数", "")
    fig.update_layout(height=560, showlegend=False, margin=dict(l=35, r=35, t=72, b=60))
    fig.update_xaxes(
        tickvals=[0, 1, 2, 3],
        ticktext=["0", "0.25", "0.50", "0.75"],
        range=[-0.35, 3.35],
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(range=[-4, 4], showticklabels=False, showgrid=False, zeroline=False)
    return fig


def _decisions(data):
    nodes = data["textbook"]["nodes"]
    names = ["B：コール→転換", "D：コール→転換", "E：継続"]
    selected = [nodes[key] for key in ("B", "D", "E")]
    fig = go.Figure()
    fig.add_bar(
        x=names,
        y=[n["continuation"] for n in selected],
        name="コール前の継続価値",
        marker_color=_BLUE,
    )
    fig.add_bar(
        x=names, y=[n["value"] for n in selected], name="権利行使後の価値", marker_color=_RED
    )
    fig.update_layout(barmode="group")
    return _finish(
        fig, "cb_decisions", "発行体のコールと保有者の再転換", "原著のノード", "価値 ($)"
    )


def _credit(data):
    scenarios = data["scenarios"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("ハザード率", "デフォルト回収額"))
    fig.add_scatter(
        x=[100 * r["hazard_rate"] for r in scenarios["credit"]],
        y=[r["price"] for r in scenarios["credit"]],
        name="信用リスク",
        line=dict(color=_BLUE),
        mode="lines+markers",
        row=1,
        col=1,
    )
    fig.add_scatter(
        x=[r["recovery_value"] for r in scenarios["recovery"]],
        y=[r["price"] for r in scenarios["recovery"]],
        name="回収額",
        line=dict(color=_GREEN),
        mode="lines+markers",
        row=1,
        col=2,
    )
    fig.update_xaxes(title_text="λ (%/年)", row=1, col=1)
    fig.update_xaxes(title_text="回収額 ($)", row=1, col=2)
    fig.update_yaxes(title_text="初期価格 ($)", row=1, col=1)
    return _finish(fig, "cb_credit", "信用リスクと回収仮定による価格差", "", "")


def _convergence(data):
    rows = data["scenarios"]["convergence"]
    fig = go.Figure()
    fig.add_scatter(
        x=[r["steps"] for r in rows],
        y=[r["price"] for r in rows],
        mode="lines+markers",
        name="コール可能な転換社債",
        line=dict(color=_BLUE),
    )
    fig.add_hline(
        y=rows[-1]["price"], line_dash="dash", line_color=_GREEN, annotation_text="96段の値"
    )
    return _finish(fig, "cb_convergence", "格子の刻みと評価額", "時間ステップ数", "初期価格 ($)")


def _figures(path=None):
    """Build four checked figures from one saved independent reference."""
    data = _load_reference(path)
    return {
        "cb_tree": _tree(data),
        "cb_decisions": _decisions(data),
        "cb_credit": _credit(data),
        "cb_convergence": _convergence(data),
    }
