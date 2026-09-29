"""Four shared Book and portal figures for Hull GE §26.3."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-3/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE = "#2563eb"
_RED = "#dc2626"
_TEAL = "#0f766e"
_GREY = "#94a3b8"


def _load_reference(path=None, record_path=None):
    """Load the saved reference only when its approved hash still matches."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("nonstandard American reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            file = _PROJECT / relative
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                raise ValueError(f"nonstandard American source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.3" or len(data.get("cases", ())) != 5:
        raise ValueError("unsupported §26.3 reference")
    return data


def _finish(figure, key, title, x_title, y_title):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=75, r=35, t=75, b=95),
        legend=dict(orientation="h", y=-0.30),
        meta={
            "section": "26.3",
            "figure": key,
            "source": "Hull GE §26.3 p.616; saved independent synthetic reference",
        },
    )
    figure.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    figure.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return figure


def _ordering(data):
    rows = data["cases"][:4]
    figure = go.Figure()
    figure.add_bar(
        x=[row["label"] for row in rows],
        y=[row["price"] for row in rows],
        marker_color=[_GREY, _BLUE, _TEAL, _RED],
        text=[f"{row['price']:.4f}" for row in rows],
        textposition="outside",
        name="プット価格",
    )
    figure.update_xaxes(
        tickmode="array",
        tickvals=[row["label"] for row in rows],
        ticktext=["欧州型", "指定日（5回）", "半期ロックアウト", "米国型"],
    )
    return _finish(
        figure, "scheduled_ordering", "行使できる日の違いと価格", "行使日程", "価格（通貨）"
    )


def _warrant(data):
    figure_data = data["figure"]
    figure = go.Figure()
    figure.add_scatter(
        x=figure_data["warrant_years"],
        y=figure_data["warrant_strikes"],
        mode="lines+markers+text",
        line=dict(color=_BLUE, width=3, shape="hv"),
        marker=dict(size=11),
        text=[f"${strike}" for strike in figure_data["warrant_strikes"]],
        textposition="top center",
        name="行使価格",
    )
    figure.update_xaxes(tickmode="array", tickvals=figure_data["warrant_years"])
    figure.update_yaxes(range=[27, 36])
    return _finish(
        figure,
        "scheduled_warrant",
        "7年ワラントの年別行使価格",
        "契約開始からの年",
        "行使価格（ドル）",
    )


def _exercise(data):
    lattice = data["figure"]["exercise_lattice"]
    figure = go.Figure()
    figure.add_scatter(
        x=[row["step"] for row in lattice["candidates"]],
        y=[row["stock"] for row in lattice["candidates"]],
        mode="markers",
        marker=dict(color=_GREY, size=7, opacity=0.5),
        name="行使可能節点",
    )
    figure.add_scatter(
        x=[row["step"] for row in lattice["points"]],
        y=[row["stock"] for row in lattice["points"]],
        mode="markers",
        marker=dict(color=_RED, size=10, symbol="diamond"),
        name="実際に行使する節点",
    )
    figure.update_xaxes(tickmode="array", tickvals=lattice["allowed_steps"])
    return _finish(
        figure,
        "scheduled_exercise",
        "指定日だけで早期行使を判定",
        "格子ステップ（20段／1年）",
        "株価（通貨）",
    )


def _frequency(data):
    ladder = data["figure"]["exercise_frequency"]
    figure = go.Figure()
    figure.add_scatter(
        x=ladder["date_counts"],
        y=ladder["prices"],
        mode="lines+markers",
        line=dict(color=_TEAL, width=3),
        marker=dict(size=10),
        name="プット価格",
    )
    figure.update_xaxes(type="log", tickmode="array", tickvals=ladder["date_counts"])
    return _finish(
        figure,
        "scheduled_frequency",
        "行使日を増やすと米国型に近づく",
        "行使可能日数（同じ64段格子）",
        "価格（通貨）",
    )


def _figures():
    data = _load_reference()
    return {
        "scheduled_ordering": _ordering(data),
        "scheduled_warrant": _warrant(data),
        "scheduled_exercise": _exercise(data),
        "scheduled_frequency": _frequency(data),
    }
