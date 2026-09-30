"""Four shared Book and portal figures for Hull GE §26.4 gap options."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-4/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE = "#2563eb"
_RED = "#dc2626"
_TEAL = "#0f766e"
_GREY = "#64748b"
_INK = "#111827"


def _load_reference(path=None, record_path=None):
    """Load the saved reference only while its approved hashes still match."""
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("gap option reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            file = _PROJECT / relative
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                raise ValueError(f"gap option source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.4" or len(data.get("cases", ())) != 38:
        raise ValueError("unsupported §26.4 reference")
    return data


def _broken(grid, values, trigger, kind):
    """Break the line where the trigger switches, so the payoff jump is not drawn as a steep line.

    A call pays when ``S_T > K2`` and a put when ``S_T < K2``, so a grid point at
    ``K2`` itself belongs to the no-payment side of a call and of a put alike.
    """
    cut = next(i for i, x in enumerate(grid) if (x > trigger if kind == "call" else x >= trigger))
    return [*grid[:cut], None, *grid[cut:]], [*values[:cut], None, *values[cut:]]


def _finish(figure, key, title, x_title, y_title):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=75, r=35, t=75, b=95),
        legend=dict(orientation="h", y=-0.30),
        meta={
            "section": "26.4",
            "figure": key,
            "source": "Hull GE §26.4 p.617 and Example 26.1; saved independent reference",
        },
    )
    figure.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    figure.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return figure


def _payoff(data):
    payoff = data["figure"]["payoff"]
    grid, trigger = payoff["grid"], payoff["K2"]
    figure = go.Figure()
    figure.add_scatter(
        x=grid,
        y=payoff["regular_call"],
        mode="lines",
        name="通常のコール（K = 100）",
        line=dict(color=_GREY, dash="dash", width=2),
    )
    for key, color, label in (
        ("gap_call_K1_90", _BLUE, "ギャップ・コール K1 = 90（跳び +10）"),
        ("gap_call_K1_110", _RED, "ギャップ・コール K1 = 110（跳び −10）"),
    ):
        x, y = _broken(grid, payoff[key], trigger, "call")
        figure.add_scatter(
            x=x, y=y, mode="lines", name=label, line=dict(color=color, width=3), connectgaps=False
        )
    figure.add_scatter(
        x=[trigger, trigger],
        y=[trigger - 90.0, trigger - 110.0],
        mode="markers",
        name="S_T が K2 に上から近づくときの極限（K2 自体の支払は0）",
        marker=dict(
            color="white", size=10, symbol="circle", line=dict(color=[_BLUE, _RED], width=2)
        ),
    )
    figure.add_hline(y=0.0, line=dict(color=_INK, width=1))
    return _finish(
        figure,
        "gap_payoff",
        "満期の支払：S_T > K2 = 100 なら S_T − K1",
        "満期の資産価格 S_T",
        "満期の支払",
    )


def _settlement_line(data):
    line = data["figure"]["settlement_line"]
    means = data["conditional_mean"]
    trigger = line["K2"]
    at_trigger = line["K1"].index(trigger)
    figure = go.Figure()
    for kind, color, label in (
        ("call", _BLUE, "ギャップ・コール"),
        ("put", _RED, "ギャップ・プット"),
    ):
        figure.add_scatter(
            x=line["K1"],
            y=line[kind],
            mode="lines",
            name=f"{label}（傾き {line[kind + '_slope']:+.4f}）",
            line=dict(color=color, width=3),
        )
    figure.add_scatter(
        x=[trigger, trigger],
        y=[line["call"][at_trigger], line["put"][at_trigger]],
        mode="markers",
        name="K1 = K2：通常のオプション",
        marker=dict(color=_INK, size=11, symbol="circle-open", line=dict(width=2)),
    )
    figure.add_scatter(
        x=[means["call"]["closed_form"], means["put"]["closed_form"]],
        y=[0.0, 0.0],
        mode="markers",
        name="価値ゼロの K1＝条件付き平均",
        marker=dict(color=_TEAL, size=12, symbol="diamond"),
    )
    figure.add_hline(y=0.0, line=dict(color=_INK, width=1))
    return _finish(
        figure,
        "gap_settlement_line",
        "K1 だけ動かすと価格は直線（K2 = 100）",
        "決済に使う行使価格 K1",
        "価格",
    )


def _insurance(data):
    insurance = data["figure"]["insurance"]
    example = data["example_26_1"]
    grid = insurance["grid"]
    figure = go.Figure()
    figure.add_scatter(
        x=grid,
        y=insurance["regular_put"],
        mode="lines",
        name="通常のプット：支払 400,000 − S_T",
        line=dict(color=_GREY, dash="dash", width=2),
    )
    x, y = _broken(grid, insurance["insurer_gap_put"], example["K2"], "put")
    figure.add_scatter(
        x=x,
        y=y,
        mode="lines",
        name="保険会社の費用（ギャップ・プット）",
        line=dict(color=_RED, width=3),
        connectgaps=False,
    )
    figure.add_scatter(
        x=[example["K2"]],
        y=[example["K1"] - example["K2"]],
        mode="markers",
        name="S_T が 350,000 に下から近づくときの極限（350,000 では請求なし）",
        marker=dict(color="white", size=10, symbol="circle", line=dict(color=_RED, width=2)),
    )
    figure.add_scatter(
        x=grid,
        y=insurance["policyholder_net"],
        mode="lines",
        name="契約者の手取り（移転費用 50,000 控除後）",
        line=dict(color=_BLUE, dash="dot", width=3),
    )
    figure.update_xaxes(tickformat=",")
    figure.update_yaxes(tickformat=",")
    return _finish(
        figure,
        "gap_insurance",
        "例題26.1：請求は S_T < 350,000 のときだけ",
        "1年後の資産価値 S_T（ドル）",
        "満期の金額（ドル）",
    )


def _transfer_cost(data):
    block = data["figure"]["transfer_cost"]
    rows = block["rows"]
    example = data["example_26_1"]
    costs = [row["transfer_cost"] for row in rows]
    figure = go.Figure()
    for key, color, dash, label in (
        ("insurer_cost", _RED, "solid", "保険会社の費用（ギャップ・プット）"),
        ("policyholder_value", _BLUE, "dot", "契約者にとっての価値"),
        ("transfer_cost_present_value", _TEAL, "dash", "移転費用の現在価値（差額）"),
    ):
        figure.add_scatter(
            x=costs,
            y=[row[key] for row in rows],
            mode="lines",
            name=label,
            line=dict(color=color, dash=dash, width=3),
        )
    figure.add_scatter(
        x=[0.0, example["transfer_cost"]],
        y=[block["regular_put"], example["insurer_gap_put"]],
        mode="markers",
        name=(
            f"原典：{example['printed']['regular_put']:,} → {example['printed']['gap_put']:,}"
            f"（約{example['printed']['reduction_percent']}%減）"
        ),
        marker=dict(color=_INK, size=11, symbol="diamond"),
    )
    figure.update_xaxes(tickformat=",")
    figure.update_yaxes(tickformat=",")
    return _finish(
        figure,
        "gap_transfer_cost",
        "移転費用が大きいほど保険会社の費用は下がる",
        "契約者が負担する移転費用（ドル）",
        "現在価値（ドル）",
    )


def _figures(path=None):
    """Build four checked figures for both rendered surfaces."""
    data = _load_reference(path)
    return {
        "gap_payoff": _payoff(data),
        "gap_settlement_line": _settlement_line(data),
        "gap_insurance": _insurance(data),
        "gap_transfer_cost": _transfer_cost(data),
    }
