"""Saved-data plots for Hull GE §26.4; shared by Book and offline portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-4/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE, _RED, _TEAL, _GREY = "#2563eb", "#dc2626", "#0f766e", "#64748b"


def _load_reference(path=None, record_path=None):
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "26.4":
        raise ValueError("gap reference requires a passing numerical record")
    if hashlib.sha256(source.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("gap reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            file = _PROJECT / relative
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                raise ValueError(f"gap source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "26.4" or len(data.get("cases", ())) != 30:
        raise ValueError("unsupported §26.4 reference")
    return data


def _trace(figure, role, name, x, y, color, **options):
    figure.add_scatter(
        x=x,
        y=y,
        name=name,
        mode="lines",
        line=dict(color=color, width=3),
        meta=dict(role=role),
        **options,
    )


def _marker(figure, role, x, y, color, symbol="circle"):
    figure.add_scatter(
        x=[x],
        y=[y],
        mode="markers",
        showlegend=False,
        marker=dict(color=color, symbol=symbol, size=11, line=dict(width=2)),
        meta=dict(role=role),
        name=role,
    )


def _finish(figure, key, title, x_title, y_title):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=80, r=35, t=80, b=100),
        legend=dict(orientation="h", y=-0.27),
        meta=dict(
            section="26.4",
            figure=key,
            source="Hull GE §26.4 p.617; independent signed-payoff quadrature",
        ),
    )
    figure.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    figure.update_yaxes(title_text=y_title, automargin=True, title_standoff=12, zeroline=True)
    return figure


def _payoff(data):
    row = data["figure"]["payoff"]
    x, trigger = row["stock"], row["trigger"]
    left, right = (
        [i for i, s in enumerate(x) if s < trigger],
        [i for i, s in enumerate(x) if s > trigger],
    )
    figure = go.Figure()
    _trace(
        figure,
        "call-inactive",
        "Call K₁=120",
        [x[i] for i in left] + [trigger],
        [0] * (len(left) + 1),
        _BLUE,
    )
    _trace(
        figure,
        "call-active",
        "Call K₁=120",
        [trigger] + [x[i] for i in right],
        [trigger - row["call_strike"]] + [row["call"][i] for i in right],
        _BLUE,
        showlegend=False,
    )
    _trace(
        figure,
        "put-active",
        "Put K₁=80",
        [x[i] for i in left] + [trigger],
        [row["put"][i] for i in left] + [row["put_strike"] - trigger],
        _RED,
    )
    _trace(
        figure,
        "put-inactive",
        "Put K₁=80",
        [trigger] + [x[i] for i in right],
        [0] * (len(right) + 1),
        _RED,
        showlegend=False,
    )
    _marker(figure, "call-limit", trigger, -20, _BLUE, "circle-open")
    _marker(figure, "put-limit", trigger, -20, _RED, "square-open")
    _marker(figure, "trigger-value", trigger, 0, _GREY)
    figure.add_vline(x=trigger, line_dash="dot", line_color=_GREY)
    return _finish(
        figure,
        "gap_payoff",
        "トリガーと決済額を分ける：負の給付も残る",
        "満期価格 Sₜ（通貨）",
        "給付（通貨）",
    )


def _decomposition(data):
    rows = data["figure"]["decomposition"]
    x = [row["K1"] for row in rows]
    figure = go.Figure()
    for role, name, field, color in (
        ("gap", "ギャップ・コール", "price", _BLUE),
        ("vanilla", "バニラ K₂=100", "vanilla", _GREY),
        ("cash", "現金バイナリ調整", "cash_adjustment", _RED),
    ):
        _trace(figure, role, name, x, [row[field] for row in rows], color)
    figure.add_vline(x=100, line_dash="dot", line_color=_GREY)
    return _finish(
        figure,
        "gap_decomposition",
        "価格＝バニラ＋現金バイナリの調整",
        "決済額に使う K₁（通貨）",
        "現在価格（通貨）",
    )


def _insurance(data):
    row = data["figure"]["insurance"]
    x, trigger = row["stock"], row["trigger"]
    left, right = (
        [i for i, s in enumerate(x) if s < trigger],
        [i for i, s in enumerate(x) if s >= trigger],
    )
    figure = go.Figure()
    _trace(
        figure,
        "ordinary",
        "費用なしの通常プット",
        [s / 1000 for s in x],
        [v / 1000 for v in row["ordinary"]],
        _GREY,
    )
    _trace(
        figure,
        "insurer-active",
        "保険会社の支出",
        [x[i] / 1000 for i in left] + [trigger / 1000],
        [row["insurer"][i] / 1000 for i in left] + [50],
        _BLUE,
    )
    _trace(
        figure,
        "insurer-inactive",
        "保険会社の支出",
        [x[i] / 1000 for i in right],
        [0] * len(right),
        _BLUE,
        showlegend=False,
    )
    _trace(
        figure,
        "holder",
        "契約者の費用控除後手取り",
        [s / 1000 for s in x],
        [v / 1000 for v in row["holder"]],
        _TEAL,
    )
    _marker(figure, "insurer-limit", 350, 50, _BLUE, "circle-open")
    _marker(figure, "insurer-trigger", 350, 0, _BLUE)
    figure.add_vline(x=350, line_dash="dot", line_color=_GREY)
    return _finish(
        figure,
        "gap_insurance",
        "Example 26.1：誰が50,000ドルを負担するか",
        "満期の資産価値（千ドル）",
        "支出・手取り（千ドル）",
    )


def _premium(data):
    rows = data["figure"]["premium"]
    figure = go.Figure()
    for role, name, color in (
        ("insurer", "保険会社の期待支出", _BLUE),
        ("holder", "契約者の期待手取り", _TEAL),
        ("transfer", "移転費用の期待額", _RED),
    ):
        _trace(
            figure,
            role,
            name,
            [row["cost"] / 1000 for row in rows],
            [row[role] / 1000 for row in rows],
            color,
        )
    figure.add_vline(x=50, line_dash="dot", line_color=_GREY)
    return _finish(
        figure,
        "gap_premium",
        "移転費用と保険料：50,000ドルで約45%減",
        "移転費用（千ドル）",
        "割引期待額（千ドル）",
    )


def _figures():
    data = _load_reference()
    return {
        "gap_payoff": _payoff(data),
        "gap_decomposition": _decomposition(data),
        "gap_insurance": _insurance(data),
        "gap_premium": _premium(data),
    }
