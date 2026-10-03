"""Evidence-checked signed risk premium figures shared by Book and portal."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-2/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_factor_risk_reference.py",
    "scripts/verify_factor_risk_numerics.py",
    "hullkit/src/hullkit/factor_risk.py",
    "hullkit/src/hullkit/risk_premium.py",
}
_COLORS = ("#2563eb", "#dc2626", "#0f766e", "#7c3aed")


def _load_reference(record_path=None):
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("section") != "28.2":
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
            section="28.2",
            figure=key,
            market=market,
            source="Hull GE pp.674–675; no-income multi-factor claims",
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _figures():
    data = _load_reference()
    row = data["figure"]["contributions"]
    contributions = go.Figure()
    contributions.add_bar(
        x=row["labels"],
        y=row["values"],
        name="λ×s（超過収益）",
        marker_color=_COLORS[0],
        meta=dict(role="contributions"),
    )
    contributions.update_xaxes(title_text="Example 28.3：因子別の寄与と合計")
    contributions.update_yaxes(title_text="超過収益 μ−r（年率）", tickformat=".0%")

    row = data["figure"]["loading"]
    loading = go.Figure()
    for i, (price, values) in enumerate(zip(row["risk_prices"], row["returns"], strict=True)):
        loading.add_scatter(
            x=row["loading"],
            y=values,
            mode="lines",
            name=f"λ₂={price:+.1f}",
            line=dict(color=_COLORS[i], width=3),
            meta=dict(role=f"lambda-{price}"),
        )
    loading.update_xaxes(title_text="因子2の符号付き係数 s₂（年⁻½）")
    loading.update_yaxes(title_text="総期待収益 μ（年率）", tickformat=".0%")

    row = data["hedge"]
    hedge = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("因子1の寄与", "因子2の寄与", "収益の寄与"),
        horizontal_spacing=0.14,
    )
    for col, role, values, name in (
        (1, "risk_1", row["risk"][0], "w×s₁"),
        (2, "risk_2", row["risk"][1], "w×s₂"),
        (3, "returns", row["returns"], "w×μ"),
    ):
        hedge.add_bar(
            x=["A", "B", "C", "合計"],
            y=[*values, sum(values)],
            name=name,
            marker_color=_COLORS[col - 1],
            meta=dict(role=role),
            row=1,
            col=col,
        )
    hedge.add_hline(y=row["r"], line_dash="dash", line_color=_COLORS[3], row=1, col=3)
    hedge.update_yaxes(title_text="年⁻½", row=1, col=1)
    hedge.update_yaxes(title_text="年⁻½", row=1, col=2)
    hedge.update_yaxes(title_text="年率", tickformat=".0%", row=1, col=3)

    validation = go.Figure()
    xs = [f"市場{i + 1}" for i in range(len(data["cases"]))]
    record = json.loads(_RECORD.read_text(encoding="utf-8"))
    for i, (role, values, name) in enumerate(
        (
            ("reference", [r["excess"] for r in data["cases"]], "独立math.fsum"),
            ("api", record["api_excess_returns"], "factor API"),
        )
    ):
        validation.add_bar(x=xs, y=values, name=name, marker_color=_COLORS[i], meta=dict(role=role))
    validation.update_layout(barmode="group")
    validation.update_xaxes(title_text="12合成市場：金利/λの倍率/係数の符号")
    validation.update_yaxes(title_text="超過収益（年率）", tickformat=".0%")
    return {
        "factor_risk_contributions": _finish(
            contributions,
            "factor_risk_contributions",
            "三因子の超過収益：+1% −1% +6%",
            "Example28.3: μ−r=6%; total μ=r+6%",
        ),
        "factor_risk_loading": _finish(
            loading,
            "factor_risk_loading",
            "符号付き係数と総期待収益",
            "r=4%, λ₁=.2,λ₃=.4,s₁=.05,s₃=.15; synthetic",
        ),
        "factor_risk_hedge": _finish(
            hedge,
            "factor_risk_hedge",
            "二因子の局所的な相殺",
            "w=(.25,.25,.5), r=4%, λ=(.3,-.2); money fractions, synthetic",
        ),
        "factor_risk_validation": _finish(
            validation,
            "factor_risk_validation",
            "独立算術とAPIの照合",
            "12 signed synthetic markets; tolerance 1e-12",
        ),
    }
