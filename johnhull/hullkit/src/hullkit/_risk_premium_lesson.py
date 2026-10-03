"""Evidence-checked signed risk premium figures shared by Book and portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-1/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_risk_premium_reference.py",
    "scripts/verify_risk_premium_numerics.py",
    "hullkit/src/hullkit/risk_premium.py",
    "hullkit/src/hullkit/sde.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "28.1":
        raise ValueError("risk premium requires a passing numerical record")
    if hashlib.sha256(_DATA.read_bytes()).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("risk premium reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not _SOURCES <= hashes.keys():
        raise ValueError("risk premium source hashes missing")
    for name, expected in hashes.items():
        if hashlib.sha256((_PROJECT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"risk premium source hash mismatch: {name}")
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _finish(fig, key, title, market):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=80, r=35, t=100, b=140),
        legend=dict(orientation="h", y=-0.28),
        meta=dict(
            section="28.1",
            figure=key,
            market=market,
            source="Hull GE pp.671–674; no-income one-factor claims",
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _figures():
    data = _load_reference()
    row = data["figure"]["loading"]
    loading = go.Figure()
    for i, (lam, values) in enumerate(zip(row["risk_prices"], row["returns"], strict=True)):
        loading.add_scatter(
            x=row["loading"],
            y=values,
            mode="lines",
            name=f"λ={lam:+.2f}",
            line=dict(color=_COLORS[i], width=3),
            meta=dict(role=f"lambda-{lam}"),
        )
    loading.update_xaxes(title_text="符号付き係数 s（年^(-1/2)）")
    loading.update_yaxes(title_text="期待収益 μ（年率）", tickformat=".0%")

    row = data["figure"]["hedge"]
    hedge = make_subplots(rows=1, cols=2, subplot_titles=("符号付きリスク寄与", "年率収益の寄与"))
    for col, field, name, color in (
        (1, "risk", "w×s", _COLORS[0]),
        (2, "returns", "w×μ", _COLORS[1]),
    ):
        values = row[field]
        hedge.add_bar(
            x=["証券A", "証券B", "合計"],
            y=[*values, sum(values)],
            name=name,
            marker_color=color,
            meta=dict(role=field),
            row=1,
            col=col,
        )
    hedge.add_hline(y=row["r"], line_dash="dash", line_color=_COLORS[2], row=1, col=2)
    hedge.update_yaxes(title_text="年^(-1/2)", row=1, col=1)
    hedge.update_yaxes(title_text="年率", tickformat=".1%", row=1, col=2)

    row = data["figure"]["density"]
    distribution = go.Figure()
    for i, field in enumerate(("p", "q", "weighted_p")):
        distribution.add_scatter(
            x=row["log_return"],
            y=row[field],
            mode="lines",
            name={"p": "P 密度", "q": "Q 密度", "weighted_p": "P密度×dQ/dP"}[field],
            line=dict(color=_COLORS[i], width=3, dash="dot" if field == "weighted_p" else "solid"),
            meta=dict(role=field),
        )
    for field in ("mean_p", "mean_q"):
        distribution.add_vline(x=row[field], line_dash="dash", line_color="gray")
    distribution.update_xaxes(title_text="log(fT/f0)：対数収益")
    distribution.update_yaxes(title_text="対数収益の確率密度")

    validation = go.Figure()
    xs = [f"λ={r['risk_price']:+.2f}, s={r['loading']:+.1f}" for r in data["mc"]]
    for i, prefix in enumerate(("weighted", "direct")):
        validation.add_bar(
            x=xs,
            y=[r[prefix + "_price"] for r in data["mc"]],
            name="P再重み付け" if i == 0 else "Q直接標本",
            marker_color=_COLORS[i],
            error_y=dict(
                type="data",
                array=[1.959963984540054 * r[prefix + "_se"] for r in data["mc"]],
                visible=True,
            ),
            meta=dict(role=prefix),
        )
    validation.add_scatter(
        x=xs,
        y=[r["reference_price"] for r in data["mc"]],
        mode="markers",
        name="独立Gaussian求積",
        marker=dict(color=_COLORS[2], symbol="diamond", size=10),
        meta=dict(role="integral"),
    )
    validation.update_xaxes(title_text="市場リスクの価格λと符号付き係数s", tickangle=-12)
    validation.update_yaxes(title_text="割引終値の期待値（通貨）")
    validation.update_layout(barmode="group")
    return {
        "risk_premium_loading": _finish(
            loading, "risk_premium_loading", "符号付きリスクと期待収益", "r=6%; μ=r+λs"
        ),
        "risk_premium_hedge": _finish(
            hedge,
            "risk_premium_hedge",
            "共通リスクの局所的な相殺",
            "r=4%, λ=.25; 金額比率w=(.6,.4), s=(.2,-.3)",
        ),
        "risk_premium_density": _finish(
            distribution,
            "risk_premium_density",
            "P→Q：ドリフト変更と拡散の保存",
            "r=6%, λ=-.15, s=.3, T=2; 対数収益分散=.18",
        ),
        "risk_premium_validation": _finish(
            validation,
            "risk_premium_validation",
            "非正規化RNと直接Q標本（95%区間）",
            "f0=100,r=6%,T=2; 262144標本, seed281; 重みは非正規化",
        ),
    }
