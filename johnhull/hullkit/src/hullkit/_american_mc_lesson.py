"""Four shared Book and portal figures for Hull GE §27.8."""

import hashlib
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-8/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_COLORS = {
    "late": "#2563eb",
    "early": "#dc2626",
    "cubic": "#0f766e",
    "reference": "#111827",
    "guide": "#94a3b8",
}
_TIMES = {"2": "t=2", "1": "t=1"}


def _load_reference(path=None, record_path=None):
    """Load the independent reference only while its hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("american Monte Carlo reference hash mismatch")
    if source == _DATA:
        for relative, expected in record["source_sha256"].items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"american Monte Carlo source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.8" or len(data["hand_example"]["paths"]) != 8:
        raise ValueError("unsupported §27.8 reference")
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
            "section": "27.8",
            "figure": key,
            "source": "Hull GE §27.8 Tables 27.4-27.7; saved independent reference",
        },
    )
    fig.update_xaxes(title_standoff=12, automargin=True)
    fig.update_yaxes(title_standoff=12, automargin=True)
    return fig


def _regression(data):
    hand = data["hand_example"]
    strike = hand["strike"]
    steps = hand["least_squares"]["steps"]
    grid = np.linspace(0.74, 1.10, 73)
    fig = go.Figure()
    for time, color, symbol in (
        ("2", _COLORS["late"], "circle"),
        ("1", _COLORS["early"], "diamond"),
    ):
        step = steps[time]
        a, b, c = step["coefficients"]
        fig.add_scatter(
            x=step["spots"],
            y=step["discounted_continuation"],
            mode="markers",
            name=f"{_TIMES[time]} 継続の実現値（割引後）",
            marker=dict(color=color, symbol=symbol, size=10),
        )
        fig.add_scatter(
            x=grid.tolist(),
            y=(a + b * grid + c * grid**2).tolist(),
            mode="lines",
            name=f"{_TIMES[time]} 回帰 a+bS+cS²",
            line=dict(color=color, width=2),
        )
    fig.add_scatter(
        x=[0.74, strike],
        y=[strike - 0.74, 0.0],
        mode="lines",
        name="即時行使の価値 K−S",
        line=dict(color=_COLORS["guide"], dash="dash", width=2),
    )
    for time, color in (("2", _COLORS["late"]), ("1", _COLORS["early"])):
        spots = [
            s
            for s, i in zip(steps[time]["spots"], steps[time]["paths"], strict=True)
            if i in steps[time]["exercised"]
        ]
        fig.add_scatter(
            x=spots,
            y=[strike - s for s in spots],
            mode="markers",
            name=f"{_TIMES[time]} で行使する経路",
            marker=dict(color=color, symbol="x", size=10),
        )
    return _finish(
        fig,
        "american_mc_regression",
        "最小二乗法：継続価値の回帰（原典の8経路）",
        "株価 S",
        "価値",
    )


def _boundary(data):
    steps = data["hand_example"]["boundary"]["steps"]
    fig = go.Figure()
    left, right = 0.70, 1.12
    for time, color in (("2", _COLORS["late"]), ("1", _COLORS["early"])):
        step = steps[time]
        prices = step["candidates"][1:]
        averages = step["averages"]
        fig.add_scatter(
            x=[left, *prices, right],
            y=[*averages, averages[-1]],
            mode="lines",
            line_shape="hv",
            name=f"{_TIMES[time]} 平均価値",
            line=dict(color=color, width=2),
        )
        best = averages.index(max(averages))
        fig.add_scatter(
            x=step["interval"],
            y=[averages[best]] * 2,
            mode="lines+markers",
            name=f"{_TIMES[time]} 最適な S*（{step['interval'][0]:.2f}以上{step['interval'][1]:.2f}未満）",
            line=dict(color=color, width=6),
            marker=dict(color=color, size=9, symbol=["circle", "circle-open"]),
        )
    return _finish(
        fig,
        "american_mc_boundary",
        "境界のパラメータ化：S* と平均価値（原典の8経路）",
        "臨界価格 S*",
        "その時点での平均価値",
    )


def _bias(data):
    bias = data["bias"]
    fig = go.Figure()
    series = (
        ("lsm_in", "最小二乗法：推定に使った経路", _COLORS["late"], "dash"),
        ("lsm_out", "最小二乗法：新しい経路", _COLORS["late"], "solid"),
        ("boundary_in", "境界：推定に使った経路", _COLORS["early"], "dash"),
        ("boundary_out", "境界：新しい経路", _COLORS["early"], "solid"),
    )
    for key, name, color, dash in series:
        fig.add_scatter(
            x=bias["sizes"],
            y=[m - bias["exact"] for m in bias[key]["mean"]],
            error_y=dict(
                type="data", array=[2 * e for e in bias[key]["standard_error"]], thickness=1
            ),
            mode="lines+markers",
            name=name,
            line=dict(color=color, dash=dash, width=2),
        )
    fig.add_hline(y=0, line=dict(color=_COLORS["reference"], width=1))
    fig.update_xaxes(type="log", tickvals=bias["sizes"], ticktext=[str(n) for n in bias["sizes"]])
    return _finish(
        fig,
        "american_mc_bias",
        f"推定に使う経路数と偏り（{bias['replications']}回の平均±2標準誤差）",
        "推定に使う経路数（対数目盛）",
        "厳密値との差",
    )


def _dates(data):
    dates = data["dates"]
    counts = dates["counts"]
    fig = go.Figure()
    fig.add_scatter(
        x=counts,
        y=dates["exact"],
        mode="lines+markers",
        name="厳密値（数値積分とCN）",
        line=dict(color=_COLORS["reference"], width=2),
        marker=dict(size=7),
    )
    # The three policies share the dates; small offsets on the log axis keep the
    # markers and error bars apart, and the hover shows the true count.
    for key, name, color, symbol, shift in (
        ("lsm2", "最小二乗法（2次）", _COLORS["late"], "circle-open", 0.93),
        ("lsm3", "最小二乗法（3次）", _COLORS["cubic"], "square-open", 1.0),
        ("boundary", "境界のパラメータ化", _COLORS["early"], "diamond-open", 1.075),
    ):
        fig.add_scatter(
            x=[n * shift for n in counts],
            customdata=counts,
            hovertemplate="行使日 %{customdata} 回<br>%{y:.5f}<extra>" + name + "</extra>",
            y=dates[key]["value"],
            error_y=dict(
                type="data", array=[2 * e for e in dates[key]["standard_error"]], thickness=1
            ),
            mode="markers",
            name=name,
            marker=dict(color=color, symbol=symbol, size=10, line=dict(width=2)),
        )
    fig.add_scatter(
        x=[counts[0], counts[-1]],
        y=[dates["american"]] * 2,
        mode="lines",
        name=f"連続行使（米国型）{dates['american']:.4f}",
        line=dict(color=_COLORS["guide"], dash="dash", width=2),
    )
    fig.update_xaxes(type="log", tickvals=counts)
    return _finish(
        fig,
        "american_mc_dates",
        "行使日の数と価格（新しい経路で評価、±2標準誤差）",
        "3年間の行使日の数（対数目盛）",
        "プットの価格",
    )


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "american_mc_regression": _regression(data),
        "american_mc_boundary": _boundary(data),
        "american_mc_bias": _bias(data),
        "american_mc_dates": _dates(data),
    }
