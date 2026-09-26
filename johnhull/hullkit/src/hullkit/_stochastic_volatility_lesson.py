"""Four saved-data Plotly figures for Hull 11e GE §27.2."""

import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-27-2/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_BLUE, _RED, _GREEN, _GRAY = "#1f77b4", "#d62728", "#0f766e", "#86868b"


def _load_reference(path=None, record_path=None):
    source = Path(path or _DATA)
    record = json.loads(Path(record_path or _RECORD).read_text(encoding="utf-8"))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != record.get("artifact_sha256"):
        raise ValueError("stochastic-volatility reference hash mismatch")
    if source == _DATA:
        for relative, expected in record.get("source_sha256", {}).items():
            current = _PROJECT / relative
            if (
                not current.is_file()
                or hashlib.sha256(current.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"stochastic-volatility source hash mismatch: {relative}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("section") != "27.2" or len(data["heston"]["strikes"]) != 26:
        raise ValueError("unsupported stochastic-volatility reference")
    return data


def _finish(fig, key, title, x_title, y_title, *, top=85):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=460,
        margin=dict(l=65, r=30, t=top, b=75),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", y=-0.27),
        meta={
            "section": "27.2",
            "figure": key,
            "source": "Hull GE §27.2; saved independent reference",
        },
    )
    return fig


def _term(data):
    row = data["term_structure"]
    fig = go.Figure()
    fig.add_scatter(
        x=row["times"],
        y=[100 * value for value in row["sigma"]],
        name="瞬時ボラ σ(t)",
        line=dict(color=_BLUE, width=2.8, shape="hv"),
    )
    fig.add_scatter(
        x=row["times"],
        y=[100 * value for value in row["remaining_rms_vol"]],
        name="残存期間の平均分散率の平方根",
        line=dict(color=_RED, width=2.6),
    )
    fig.add_scatter(
        x=[0.0, 1.0],
        y=[100 * row["arithmetic_volatility"]] * 2,
        name="ボラの単純平均 25%（誤り）",
        line=dict(color=_GRAY, width=2, dash="dot"),
    )
    fig.add_annotation(
        x=0.0,
        y=100 * row["average_volatility"],
        text="t=0：√0.065=25.5%",
        showarrow=True,
        ax=70,
        ay=-35,
    )
    fig.update_layout(yaxis_range=[15, 33])
    return _finish(
        fig,
        "stochvol_term",
        "式27.1：BSMに入れるのは平均分散率",
        "時刻 t（年）",
        "ボラティリティ（%/√年）",
    )


def _mixing(data):
    row = data["heston"]
    moneyness = [strike / row["spot"] for strike in row["strikes"]]
    fig = go.Figure()
    fig.add_scatter(
        x=moneyness,
        y=[100 * value for value in row["smiles"]["+0.0"]["implied_vol"]],
        name="確率ボラ（ρ=0）の逆算IV",
        line=dict(color=_BLUE, width=3),
    )
    fig.add_scatter(
        x=[moneyness[0], moneyness[-1]],
        y=[100 * row["flat_volatility"]] * 2,
        name="BSM：√E[V̄]=20%",
        line=dict(color=_GRAY, width=2.2, dash="dash"),
    )
    fig.add_annotation(x=1.08, y=17.6, text="BSMは過大評価", showarrow=False)
    fig.add_annotation(x=0.8, y=25.2, text="BSMは過小評価", showarrow=False)
    fig.add_annotation(x=1.45, y=25.2, text="BSMは過小評価", showarrow=False)
    return _finish(
        fig,
        "stochvol_mixing",
        "Hull–White：無相関の確率ボラはU字のスマイル",
        "K / S₀",
        "BSM逆算IV（%）",
    )


def _correlation(data):
    row = data["heston"]
    moneyness = [strike / row["spot"] for strike in row["strikes"]]
    fig = go.Figure()
    for label, name, color in (
        ("-0.7", "ρ=−0.7（株式型）", _RED),
        ("+0.0", "ρ=0", _GRAY),
        ("+0.7", "ρ=+0.7", _BLUE),
    ):
        fig.add_scatter(
            x=moneyness,
            y=[100 * value for value in row["smiles"][label]["implied_vol"]],
            name=name,
            line=dict(color=color, width=2.8),
        )
    return _finish(
        fig,
        "stochvol_correlation",
        "相関ρがスキューの向きを決める（α=0.5）",
        "K / S₀",
        "BSM逆算IV（%）",
    )


def _sabr(data):
    row = data["sabr"]
    strikes = [100 * strike for strike in row["strikes"]]
    fig = go.Figure()
    for label, color in (("-0.6", _RED), ("+0.0", _GRAY), ("+0.6", _BLUE)):
        fig.add_scatter(
            x=strikes,
            y=[100 * value for value in row["rho_group"][label]],
            name=f"ρ={float(label):+.1f}",
            line=dict(color=color, width=2.8),
            visible=True,
        )
    for label, color in (("0.2", _BLUE), ("0.4", _GRAY), ("0.8", _RED)):
        fig.add_scatter(
            x=strikes,
            y=[100 * value for value in row["nu_group"][label]],
            name=f"ν={label}",
            line=dict(color=color, width=2.8),
            visible=False,
        )
    mc = row["monte_carlo"]["rows"]
    fig.add_scatter(
        x=[100 * item["strike"] for item in mc],
        y=[100 * item["implied_vol"] for item in mc],
        error_y=dict(
            type="data",
            array=[200 * item["implied_vol_standard_error"] for item in mc],
            visible=True,
        ),
        mode="markers",
        name="MC（ρ=0, ν=0.4、±2SE）",
        marker=dict(color=_GREEN, size=8),
        visible=True,
    )
    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                x=1.0,
                xanchor="right",
                y=1.14,
                yanchor="top",
                showactive=True,
                buttons=[
                    dict(
                        label="ρを変える（ν=0.4）",
                        method="update",
                        args=[{"visible": [True] * 3 + [False] * 3 + [True]}],
                    ),
                    dict(
                        label="νを変える（ρ=0）",
                        method="update",
                        args=[{"visible": [False] * 3 + [True] * 3 + [True]}],
                    ),
                ],
            )
        ]
    )
    return _finish(
        fig,
        "stochvol_sabr",
        "SABR（β=0.5）：ρが傾き、νが曲がり",
        "行使価格 K（%）",
        "Black逆算IV（%）",
        top=105,
    )


def _figures(path=None):
    """Build the four identical Book and portal figures from checked data."""
    data = _load_reference(path)
    return {
        "stochvol_term": _term(data),
        "stochvol_mixing": _mixing(data),
        "stochvol_correlation": _correlation(data),
        "stochvol_sabr": _sabr(data),
    }
