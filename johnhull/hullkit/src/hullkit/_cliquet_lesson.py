"""Checked cliquet reset/cashflow figures shared by Book and offline portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-26-6/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_cliquet_reference.py",
    "scripts/verify_cliquet_numerics.py",
    "hullkit/src/hullkit/cliquet.py",
    "hullkit/src/hullkit/forward_start.py",
    "hullkit/src/hullkit/bsm.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")
_MARKET = "S=100, r=5%, q=3%, σ=20%; payment dates .5, 1, 1.5, 2"


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "26.6":
        raise ValueError("cliquet reference requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("cliquet reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("cliquet source hashes missing")
    for relative, expected in hashes.items():
        file = _PROJECT / relative
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f"cliquet source hash mismatch: {relative}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(figure, key, title, x_title, y_title, market=_MARKET):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=80, r=35, t=80, b=120),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="26.6",
            figure=key,
            market=market,
            source="Hull GE p.618; synthetic GBM stock-price cashflows",
        ),
    )
    figure.update_xaxes(title_text=x_title, automargin=True, title_standoff=12)
    figure.update_yaxes(title_text=y_title, automargin=True, title_standoff=12)
    return figure


def _reset(data):
    row = data["figure"]["reset"]
    figure = go.Figure()
    figure.add_scatter(
        x=row["time"],
        y=row["stock"],
        mode="lines",
        name="株価（例示経路）",
        line=dict(color=_COLORS[0], width=3),
        meta=dict(role="stock"),
    )
    for i, strike in enumerate(row["strikes"]):
        figure.add_scatter(
            x=row["time"][i : i + 2],
            y=[strike] * 2,
            mode="lines",
            name=f"第{i + 1}期 strike",
            line=dict(color=_COLORS[2], dash="dash"),
            showlegend=i == 0,
            meta=dict(role=f"strike-{i}"),
        )
    figure.add_scatter(
        x=row["time"][:-1],
        y=row["strikes"],
        mode="markers",
        name="ATM fixing",
        marker=dict(color=_COLORS[2], size=9),
        meta=dict(role="fixing"),
    )
    figure.add_scatter(
        x=row["time"][1:],
        y=row["stock"][1:],
        mode="markers",
        name="期末給付",
        marker=dict(color=_COLORS[1], symbol="diamond", size=10),
        customdata=list(zip(row["call_payoffs"], row["put_payoffs"], strict=True)),
        hovertemplate="t=%{x}<br>S=%{y:.2f}<br>call=%{customdata[0]:.2f}<br>put=%{customdata[1]:.2f}<extra></extra>",
        meta=dict(role="payment"),
    )
    return _finish(
        figure,
        "cliquet_reset",
        "各期の開始株価へstrikeをreset",
        "時点（年）",
        "株価・strike（通貨）",
    )


def _components(data):
    figure = go.Figure()
    for kind, color in zip(("call", "put"), _COLORS[:2], strict=True):
        row = data["example"][kind]
        figure.add_bar(
            x=row["payment_times"],
            y=row["components"],
            name=kind,
            marker_color=color,
            meta=dict(role=kind),
        )
    figure.update_layout(barmode="group")
    return _finish(
        figure,
        "cliquet_components",
        "各支払日から割り引いた価格の和",
        "支払時点 tᵢ（年）",
        "各期の現在価値（通貨）",
    )


def _frequency(data):
    row = data["figure"]["frequency"]
    figure = go.Figure()
    for kind, color in zip(("call", "put"), _COLORS[:2], strict=True):
        figure.add_scatter(
            x=row["periods"],
            y=row[kind],
            name=kind,
            mode="lines+markers",
            line=dict(color=color, width=3),
            meta=dict(role=kind),
        )
    figure.add_scatter(
        x=row["periods"],
        y=[row["call"][0]] * len(row["periods"]),
        name="通常ATM call（2年）",
        mode="lines",
        line=dict(color=_COLORS[2], dash="dash"),
        meta=dict(role="vanilla"),
    )
    return _finish(
        figure,
        "cliquet_frequency",
        "満期2年固定・等間隔resetの回数",
        "期間数 n（最初のvanillaを含む）",
        "現在価値（通貨）",
        market="S=100, r=5%, q=3%, σ=20%; expiry 2; equal intervals",
    )


def _limits(data):
    row = data["complex"]
    figure = go.Figure()
    figure.add_bar(
        x=[0, 1, 2, 3],
        y=[c["price"] for c in row["contracts"]],
        name="MC（95%区間）",
        marker_color=list(_COLORS),
        error_y=dict(
            type="data",
            visible=True,
            array=[1.959963984540054 * c["standard_error"] for c in row["contracts"]],
        ),
        meta=dict(role="mc"),
    )
    figure.add_scatter(
        x=[0],
        y=[row["reference_price"]],
        mode="markers",
        name="単純和の独立求積",
        marker=dict(color="black", symbol="x", size=12),
        meta=dict(role="reference"),
    )
    figure.update_xaxes(
        tickmode="array",
        tickvals=[0, 1, 2, 3],
        ticktext=["単純和", "総額 floor 5<br>cap 20", "各期 cap 5", "95–105で<br>期末終了"],
    )
    return _finish(
        figure,
        "cliquet_limits",
        "総額制約・各期制約・範囲終了を区別",
        "契約（MC共通経路）",
        "価値（通貨、r=q=0）",
        market="S=100, r=q=0, σ=20%; payment dates .5, 1, 1.5, 2",
    )


def _figures():
    data = _load_reference()
    return dict(
        cliquet_reset=_reset(data),
        cliquet_components=_components(data),
        cliquet_frequency=_frequency(data),
        cliquet_limits=_limits(data),
    )
