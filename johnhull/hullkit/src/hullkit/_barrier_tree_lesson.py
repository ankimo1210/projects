"""Four shared Book and portal figures for Hull GE §27.6."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-6/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = {
    "binomial": "#9333ea",
    "simple": "#dc2626",
    "interpolated": "#0f766e",
    "on_barrier": "#2563eb",
    "analytic": "#111827",
    "position": "#f59e0b",
    "lattice": "#64748b",
}


def _load_reference(path=None, record_path=None):
    """Load the independent reference only while its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("barrier-tree reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"barrier-tree source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.6" or len(data["convergence"]["steps"]) != 281:
        raise ValueError("unsupported §27.6 reference")
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
            "section": "27.6",
            "figure": key,
            "source": "Hull GE §27.6 Figures 27.4–27.5; saved independent barrier reference",
        },
    )
    return fig


def _lattice(data):
    example = data["lattice_example"]
    barrier = data["parameters"]["barrier"]
    maturity = data["parameters"]["maturity"]
    fig = go.Figure()
    for key, name, shift, symbol in (
        ("standard", "標準の間隔 σ√(3Δt)", -0.012, "circle"),
        ("on_barrier", "バリア上に置く間隔", 0.012, "diamond"),
    ):
        nodes = example[key]["nodes"]
        fig.add_scatter(
            x=[t + shift for t, _ in nodes],
            y=[s for _, s in nodes],
            mode="markers",
            name=name,
            marker=dict(
                color=_COLORS["simple" if key == "standard" else "on_barrier"],
                size=7,
                symbol=symbol,
            ),
        )
    for level, name, color, dash in (
        (barrier, "真のバリア H=120", _COLORS["analytic"], "solid"),
        (example["standard"]["outer_barrier"], "外側バリア", _COLORS["simple"], "dash"),
        (example["standard"]["inner_barrier"], "内側バリア", _COLORS["position"], "dot"),
    ):
        fig.add_scatter(
            x=[0, maturity],
            y=[level, level],
            mode="lines",
            name=name,
            line=dict(color=color, dash=dash, width=2),
        )
    fig.update_yaxes(type="log", range=[1.78, 2.22])
    return _finish(
        fig,
        "barrier_lattice",
        "図27.4・27.5：ツリーが仮定するバリア（10段）",
        "時間 (年)",
        "株価 ($、対数目盛)",
    )


def _convergence(data):
    rows = data["convergence"]
    analytic = data["analytic"]["continuous"]
    fig = go.Figure()
    for key, name in (
        ("binomial_simple", "二項・素朴"),
        ("trinomial_simple", "三項・素朴"),
        ("interpolated", "内側・外側の補間"),
        ("on_barrier", "ノードをバリア上に"),
    ):
        color = _COLORS[{"binomial_simple": "binomial", "trinomial_simple": "simple"}.get(key, key)]
        fig.add_scatter(
            x=rows["steps"], y=rows[key], mode="lines", name=name, line=dict(color=color, width=2)
        )
    fig.add_scatter(
        x=[rows["steps"][0], rows["steps"][-1]],
        y=[analytic, analytic],
        mode="lines",
        name=f"連続監視の解析値 {analytic:.4f}",
        line=dict(color=_COLORS["analytic"], dash="dash", width=2),
    )
    return _finish(
        fig,
        "barrier_convergence",
        "up-and-out コール：時間ステップ数と価格",
        "時間ステップ数 N",
        "オプション価格 ($)",
    )


def _errors(data):
    rows = data["convergence"]
    analytic = data["analytic"]["continuous"]
    simple = [value - analytic for value in rows["trinomial_simple"]]
    position = [value - analytic for value in rows["outer_analytic"]]
    lattice = [a - b for a, b in zip(rows["trinomial_simple"], rows["outer_analytic"], strict=True)]
    on_barrier = [value - analytic for value in rows["on_barrier"]]
    fig = go.Figure()
    for values, name, color, width in (
        (simple, "三項・素朴の誤差", _COLORS["simple"], 3),
        (position, "うちバリア位置の差", _COLORS["position"], 1.5),
        (lattice, "うち格子の誤差", _COLORS["lattice"], 2),
        (on_barrier, "ノードをバリア上に：誤差", _COLORS["on_barrier"], 2),
    ):
        fig.add_scatter(
            x=rows["steps"], y=values, mode="lines", name=name, line=dict(color=color, width=width)
        )
    fig.update_xaxes(type="log", tickvals=[20, 30, 50, 100, 200, 300])
    return _finish(
        fig,
        "barrier_errors",
        "誤差の分解：外側バリアの位置と格子",
        "時間ステップ数 N（対数目盛）",
        "解析値との差 ($)",
    )


def _near(data):
    curves = data["near_barrier"]["curves"]
    fig = go.Figure()
    for steps, color in (("100", _COLORS["simple"]), ("400", _COLORS["on_barrier"])):
        curve = curves[steps]
        fig.add_scatter(
            x=curve["barrier"],
            y=curve["p_middle"],
            mode="lines",
            name=f"p_m（{steps}段）",
            line=dict(color=color, width=2.5),
        )
        for threshold, dash in (
            (curve["no_level_below"], "dot"),
            (curve["negative_middle_below"], "dash"),
        ):
            fig.add_vline(x=threshold, line=dict(color=color, dash=dash, width=1))
    fig.add_hline(y=0, line=dict(color=_COLORS["analytic"], width=1))
    return _finish(
        fig,
        "barrier_near",
        "初期価格にバリアが近いと中央の確率が負になる",
        "バリア H ($)",
        "中央の枝の確率 p_m",
    )


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "barrier_lattice": _lattice(data),
        "barrier_convergence": _convergence(data),
        "barrier_errors": _errors(data),
        "barrier_near": _near(data),
    }
