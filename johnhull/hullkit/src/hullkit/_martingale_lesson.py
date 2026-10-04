"""Checked conditional and numeraire figures for Book and portal."""

import hashlib
import json
import math
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-3/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_martingale_reference.py",
    "scripts/verify_martingale_numerics.py",
    "hullkit/src/hullkit/_martingales.py",
    "hullkit/src/hullkit/risk_premium.py",
    "hullkit/src/hullkit/bsm.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e")


def _load_reference():
    record = json.loads(_RECORD.read_text())
    raw = _DATA.read_bytes()
    if record.get("status") != "PASS" or record.get("section") != "28.3":
        raise ValueError("passing martingale record required")
    if hashlib.sha256(raw).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("martingale reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not isinstance(hashes, dict) or not _SOURCES <= hashes.keys():
        raise ValueError("martingale source hash missing")
    for name, expected in hashes.items():
        path = (_PROJECT / name).resolve()
        if (
            not path.is_relative_to(_PROJECT)
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError("martingale source hash mismatch")
    data = json.loads(raw)
    try:
        payload = {k: record[k] for k in ("api_conditional_means", "conditional_mc", "pricing")}
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        if digest != record.get("result_sha256"):
            raise ValueError("martingale result hash mismatch")
        expected = [r["mean"] for r in data["conditional"]]
        means = record["api_conditional_means"]
        if not isinstance(means, list) or len(means) != 9:
            raise ValueError("API results shape mismatch")
        for actual, want in zip(means, expected, strict=True):
            if (
                isinstance(actual, bool)
                or not isinstance(actual, (int, float))
                or not math.isfinite(actual)
                or abs(actual - want) > 1e-12
            ):
                raise ValueError("API results differ from independent conditional means")
        if len(record["conditional_mc"]) != 9 or len(record["pricing"]) != 4:
            raise ValueError("Monte Carlo results shape mismatch")
        for row, want in zip(
            [*record["conditional_mc"], *record["pricing"]],
            [*expected, *data["figure"]["pricing"]["reference"]],
            strict=True,
        ):
            values = [row[n] for n in ("mean", "se", "z", "reference")]
            if any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in values
            ):
                raise ValueError("Monte Carlo results nonfinite")
            if (
                row["se"] <= 0
                or abs(row["reference"] - want) > 1e-12
                or abs(row["z"] - abs(row["mean"] - want) / row["se"]) > 1e-12
                or row["z"] > 5
            ):
                raise ValueError("Monte Carlo results invalid")
        for row in record["pricing"]:
            if (
                not math.isfinite(row["quadrature"])
                or abs(row["quadrature"] - row["reference"]) > 1e-9
            ):
                raise ValueError("price quadrature mismatch")
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("martingale results missing or malformed") from exc
    return data, record


def _finish(fig, key, title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=80, r=35, t=100, b=155),
        legend=dict(orientation="h", y=-0.30),
        meta=dict(
            section="28.3",
            figure=key,
            source="Hull GE pp.675–676; constant GBM, synthetic/no income",
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _figures():
    data, record = _load_reference()
    row = data["figure"]["ito"]
    ito = go.Figure()
    ito.add_bar(
        x=row["labels"],
        y=row["values"],
        name="比の相対drift",
        marker_color=_COLORS[0],
        meta=dict(role="ito"),
    )
    ito.update_xaxes(title_text="sf=.3, sg=−.2：Itôの補正を含めた相殺")
    ito.update_yaxes(title_text="比の相対drift（年率）", tickformat=".0%")
    conditional = go.Figure()
    row = data["figure"]["conditional"]
    for i, curve in enumerate(row["curves"]):
        conditional.add_scatter(
            x=row["horizons"],
            y=curve["mean"],
            mode="lines+markers",
            name=f"λ={curve['risk_price']:+.1f}" + ("（g測度）" if i == 0 else "（別測度）"),
            line=dict(color=_COLORS[i]),
            meta=dict(role=f"lambda-{curve['risk_price']}"),
        )
    conditional.update_xaxes(title_text="観測時点からの経過時間 h（年）")
    conditional.update_yaxes(title_text="E[X_(t+h)|F_t]、観測比X_t=1.25")
    plots = {"martingale_ito": ito, "martingale_conditional": conditional}
    for key, rows, labels, title in (
        (
            "martingale_conditional_mc",
            record["conditional_mc"],
            data["figure"]["conditional_mc"]["labels"],
            "複数時刻・状態の条件付きMC：解析値との差",
        ),
        (
            "martingale_pricing",
            record["pricing"],
            data["figure"]["pricing"]["labels"],
            "同じcall給付：Q/G測度のMC価格差",
        ),
    ):
        fig = go.Figure()
        fig.add_scatter(
            x=labels,
            y=[r["mean"] - r["reference"] for r in rows],
            mode="markers",
            name="MC差 ±95%区間",
            error_y=dict(type="data", array=[1.96 * r["se"] for r in rows], visible=True),
            marker=dict(color=_COLORS[0], size=9),
            meta=dict(role="mc"),
        )
        fig.add_scatter(
            x=labels,
            y=[0] * len(rows),
            mode="lines",
            name="独立解析値との差0",
            line=dict(color=_COLORS[2], dash="dash"),
            meta=dict(role="reference"),
        )
        fig.update_xaxes(
            title_text="独立な合成条件付き状態（t=0は別初期市場）"
            if key.endswith("mc")
            else "同一H=(S_T−100)+、s_gの正負"
        )
        fig.update_yaxes(
            title_text="MC−解析平均（比）" if key.endswith("mc") else "MC−独立価格（通貨）"
        )
        plots[key] = _finish(fig, key, title)
    plots["martingale_ito"] = _finish(ito, "martingale_ito", "比 f/g のItô driftは0になる")
    plots["martingale_conditional"] = _finish(
        conditional, "martingale_conditional", "条件付き期待値と測度の選択"
    )
    return plots
