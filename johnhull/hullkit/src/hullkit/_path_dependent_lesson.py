"""Four shared Book and portal figures for Hull GE §27.5."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-5/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = {"X": "#2563eb", "Y": "#0f766e", "Z": "#dc2626"}


def _load_reference(path=None, record_path=None):
    """Load the independent reference only while its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("path-dependent reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"path-dependent source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.5" or len(data["exact_small_trees"]) != 5:
        raise ValueError("unsupported §27.5 reference")
    return data


def _finish(fig, key, title, x_title, y_title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=65, r=35, t=72, b=70),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "27.5",
            "figure": key,
            "source": "Hull GE Figure 27.3; saved printed and independent path reference",
        },
    )
    return fig


def _grids(data):
    fig = go.Figure()
    for name in ("X", "Y", "Z"):
        node = data["figure_27_3"][name]
        fig.add_scatter(
            x=node["averages"],
            y=node["values"],
            mode="lines+markers",
            name=f"{name} (S={node['stock']:.2f})",
            line=dict(color=_COLORS[name], width=2.5),
        )
    return _finish(
        fig,
        "path_grids",
        "図27.3：各節点の代表平均と価値",
        "算術平均株価 ($)",
        "オプション価値 ($)",
    )


def _interpolation(data):
    row = data["interpolation"]
    values = [row["up_value"], row["down_value"], row["x_value"]]
    fig = go.Figure(
        go.Bar(
            x=["Y：上昇後", "Z：下落後", "X：割引期待値"],
            y=values,
            marker_color=[_COLORS["Y"], _COLORS["Z"], _COLORS["X"]],
            text=[f"{value:.3f}" for value in values],
            textposition="outside",
        )
    )
    fig.update_yaxes(range=[0, 10])
    return _finish(
        fig, "path_interpolation", "X の平均51.44から子節点へ補間", "後退帰納の段階", "価値 ($)"
    )


def _prices(data):
    rows = [data["printed"][key] for key in ("coarse", "fine")]
    labels = [f"{row['steps']}段 × {row['average_points']}平均" for row in rows]
    fig = go.Figure()
    fig.add_bar(
        x=labels, y=[row["european"] for row in rows], name="欧州型", marker_color=_COLORS["X"]
    )
    fig.add_bar(
        x=labels, y=[row["american"] for row in rows], name="米国型", marker_color=_COLORS["Y"]
    )
    fig.update_layout(barmode="group")
    return _finish(
        fig,
        "path_prices",
        "原著の粗い格子と細かい格子",
        "時間段数 × 各節点の平均値数",
        "初期価格 ($)",
    )


def _exact(data):
    rows = data["exact_small_trees"]
    fig = go.Figure()
    fig.add_scatter(
        x=[row["steps"] for row in rows],
        y=[row["european"] for row in rows],
        mode="lines+markers",
        name="欧州型・全経路",
        line=dict(color=_COLORS["X"]),
    )
    fig.add_scatter(
        x=[row["steps"] for row in rows],
        y=[row["american"] for row in rows],
        mode="lines+markers",
        name="米国型・全経路",
        line=dict(color=_COLORS["Y"]),
    )
    return _finish(
        fig, "path_exact", "補間を使わない小規模ツリーの基準値", "時間ステップ数", "初期価格 ($)"
    )


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "path_grids": _grids(data),
        "path_interpolation": _interpolation(data),
        "path_prices": _prices(data),
        "path_exact": _exact(data),
    }
