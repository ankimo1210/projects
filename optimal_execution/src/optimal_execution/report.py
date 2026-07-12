"""Offline bilingual standalone HTML reports from one quantitative source."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from jinja2 import BaseLoader, Environment, select_autoescape
from plotly.subplots import make_subplots

from .config import Config
from .i18n import Translator, validate_locales
from .provenance import artifact_dirs, generated_at, git_commit, json_safe, write_json
from .tca import bootstrap_mean_ci

_TEMPLATE = """<!doctype html>
<html lang="{{ locale }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="optimal_execution {{ version }}">
  <meta name="profile" content="{{ profile }}">
  <meta name="seed" content="{{ seed }}">
  <meta name="git-commit" content="{{ git_commit }}">
  <title>{{ title }}</title>
  <style>
    :root { --ink:#17202a; --muted:#5f6b78; --surface:#fff; --panel:#f5f7fa; --line:#d9e0e8; --accent:#0069a8; --accent2:#c94f00; }
    * { box-sizing: border-box; }
    body { margin:0; color:var(--ink); background:var(--surface); font-family:Inter, "Noto Sans JP", system-ui, -apple-system, sans-serif; line-height:1.68; }
    main { width:min(1180px, 94vw); margin:0 auto; padding:40px 0 80px; }
    header { padding:36px clamp(24px,5vw,64px); color:white; background:linear-gradient(125deg,#073b5c,#0069a8 58%,#1f7a72); border-radius:18px; box-shadow:0 12px 32px rgba(7,59,92,.18); }
    h1 { margin:0 0 10px; font-size:clamp(2rem,5vw,3.7rem); line-height:1.08; letter-spacing:-.03em; }
    header p { max-width:900px; margin:.5rem 0; color:#eef8ff; }
    .meta { font-size:.9rem; opacity:.92; }
    section { padding:34px 0 12px; border-bottom:1px solid var(--line); }
    h2 { margin:0 0 12px; font-size:clamp(1.45rem,3vw,2.1rem); line-height:1.25; }
    h3 { margin:26px 0 8px; }
    p { max-width:960px; }
    .callout { padding:18px 20px; border-left:4px solid var(--accent); background:var(--panel); border-radius:0 10px 10px 0; }
    .warning { border-left-color:var(--accent2); }
    .chart { min-height:380px; margin:18px 0 28px; border:1px solid var(--line); border-radius:12px; padding:6px; background:white; overflow:hidden; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px; margin:18px 0; }
    .tile { padding:17px; border:1px solid var(--line); border-radius:12px; background:var(--panel); }
    .tile .value { font-size:1.55rem; font-variant-numeric:tabular-nums; font-weight:700; color:var(--accent); }
    .tile .label { color:var(--muted); font-size:.9rem; }
    .table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:10px; margin:14px 0 24px; }
    table { width:100%; border-collapse:collapse; font-size:.91rem; font-variant-numeric:tabular-nums; }
    th,td { padding:10px 12px; border-bottom:1px solid var(--line); text-align:right; white-space:nowrap; }
    th { color:#334155; background:#eef2f7; position:sticky; top:0; }
    th:first-child,td:first-child { text-align:left; }
    tr:last-child td { border-bottom:0; }
    code { background:#edf1f5; padding:.12rem .35rem; border-radius:4px; font-size:.85em; }
    math { font-size:1.05rem; }
    .eq { margin:10px 0; overflow-x:auto; }
    .mvars { columns:2; column-gap:30px; }
    .mvars li { break-inside:avoid; }
    .swrap { display:grid; grid-template-columns:1fr 1fr; gap:12px 22px; margin:6px 0 4px; }
    .swrap ul { margin-top:4px; }
    @media (max-width:640px) { .mvars { columns:1; } .swrap { grid-template-columns:1fr; } }
    footer { padding-top:28px; color:var(--muted); font-size:.86rem; }
    .toc { margin:22px 0 4px; padding:14px 18px; border:1px solid var(--line); border-radius:12px; background:var(--panel); }
    .toc b { display:block; margin-bottom:6px; color:var(--ink); font-size:.9rem; }
    .toc a { display:inline-block; margin:3px 14px 3px 0; color:var(--accent); text-decoration:none; font-size:.9rem; }
    .toc a:hover { text-decoration:underline; }
    .prov { margin-top:8px; font-variant-numeric:tabular-nums; word-break:break-all; }
    @media print { body { font-size:10pt; } main { width:100%; padding:0; } header { color:#111; background:white; box-shadow:none; border:1px solid #aaa; } header p { color:#222; } .chart { break-inside:avoid; } section { break-before:auto; } }
  </style>
</head>
<body>
<main>
  <header>
    <h1>{{ title }}</h1>
    <p>{{ subtitle }}</p>
    <p class="meta">{{ profile_note }}</p>
  </header>

  <nav class="toc" aria-label="{{ tr.toc_label }}">
    <b>{{ tr.toc_label }}</b>
    <a href="#executive-summary">{{ tr.executive_summary }}</a>
    <a href="#market-setup">{{ tr.market_setup }}</a>
    <a href="#related-work">{{ tr.related_work }}</a>
    <a href="#model-theory">{{ tr.model_theory }}</a>
    <a href="#almgren-chriss">{{ tr.almgren_chriss }}</a>
    <a href="#impact-resilience">{{ tr.impact_resilience }}</a>
    <a href="#classical-tca">{{ tr.strategy_comparison }}</a>
    <a href="#reactive-lob">{{ tr.reactive_lob }}</a>
    <a href="#rl-evaluation">{{ tr.rl_evaluation }}</a>
    <a href="#ablation-shift">{{ tr.ablation_shift }}</a>
    <a href="#methodology">{{ tr.methodology }}</a>
    <a href="#conclusion">{{ tr.conclusion }}</a>
    <a href="#limitations">{{ tr.limitations }}</a>
    <a href="#reproduction">{{ tr.reproduction }}</a>
  </nav>

  <section id="executive-summary">
    <h2>{{ tr.executive_summary }}</h2>
    <p>{{ tr.executive_summary_body }}</p>
    <div class="grid">{{ hero_tiles | safe }}</div>
    <p class="callout">{{ tr.data_note }}</p>
  </section>

  <section id="market-setup">
    <h2>{{ tr.market_setup }}</h2>
    <p>{{ tr.market_setup_body }}</p>
  </section>

  <section id="related-work">
    <h2>{{ tr.related_work }}</h2>
    {{ related_work | safe }}
  </section>

  <section id="model-theory">
    <h2>{{ tr.model_theory }}</h2>
    {{ model_theory | safe }}
  </section>

  <section id="almgren-chriss">
    <h2>{{ tr.almgren_chriss }}</h2>
    <p>{{ tr.ac_body }}</p>
    <div class="chart">{{ charts.schedules | safe }}</div>
    <div class="chart">{{ charts.frontier | safe }}</div>
  </section>

  <section id="impact-resilience">
    <h2>{{ tr.impact_resilience }}</h2>
    <p>{{ tr.impact_body }}</p>
    <div class="chart">{{ charts.impact | safe }}</div>
  </section>

  <section id="classical-tca">
    <h2>{{ tr.strategy_comparison }}</h2>
    <p>{{ tr.strategy_comparison_body }}</p>
    <div class="chart">{{ charts.classical_cost | safe }}</div>
    <div class="chart">{{ charts.ecdf | safe }}</div>
    <h3>{{ tr.table_classical }}</h3>
    {{ tables.classical | safe }}
  </section>

  <section id="reactive-lob">
    <h2>{{ tr.reactive_lob }}</h2>
    <p>{{ tr.lob_body }}</p>
    <div class="chart">{{ charts.lob | safe }}</div>
    <div class="chart">{{ charts.reactive | safe }}</div>
    <p class="callout">{{ reactive_finding }}</p>
    <h3>{{ tr.table_lob }}</h3>
    {{ tables.lob | safe }}
  </section>

  <section id="rl-evaluation">
    <h2>{{ tr.rl_evaluation }}</h2>
    <p>{{ tr.rl_body }}</p>
    {% if seed_warning %}<p class="callout warning">{{ tr.rl_seed_warning }}</p>{% endif %}
    {% if val_selection %}<div class="callout">{{ val_selection | safe }}</div>{% endif %}
    <div class="chart">{{ charts.rl | safe }}</div>
    <div class="chart">{{ charts.stress | safe }}</div>
    <h3>{{ tr.table_rl }}</h3>
    {{ tables.rl | safe }}
  </section>

  <section id="ablation-shift">
    <h2>{{ tr.ablation_shift }}</h2>
    <p>{{ tr.ablation_body }}</p>
    <div class="chart">{{ charts.ablation | safe }}</div>
    <div class="chart">{{ charts.misspecification | safe }}</div>
    <p class="callout warning">{{ shift_finding }}</p>
    <h3>{{ tr.table_misspecification }}</h3>
    {{ tables.misspecification | safe }}
  </section>

  <section id="methodology">
    <h2>{{ tr.methodology }}</h2>
    <p>{{ tr.methodology_body }}</p>
    <p class="callout">{{ tr.experiment_note }}</p>
  </section>

  <section id="conclusion">
    <h2>{{ tr.conclusion }}</h2>
    <p>{{ conclusion }}</p>
  </section>

  <section id="limitations">
    <h2>{{ tr.limitations }}</h2>
    <p>{{ tr.limitations_body }}</p>
  </section>

  <section id="reproduction">
    <h2>{{ tr.reproduction }}</h2>
    <p>{{ tr.reproduction_body }}</p>
    <pre><code>make install
make test
make demo</code></pre>
  </section>

  <script type="application/json" id="quantitative-fingerprint">{{ fingerprint_json | safe }}</script>
  <script type="application/json" id="report-provenance">{{ provenance_json | safe }}</script>
  <footer>optimal_execution · {{ generated_at }}
    <div class="prov">{{ tr.provenance_label }}: profile={{ profile }} · seed={{ seed }} · git={{ git_commit }} · fingerprint={{ fingerprint_short }}</div>
  </footer>
</main>
</body>
</html>
"""


# Okabe–Ito chromatic slots (no achromatic gray as a series color); the two
# sub-3:1 slots are relieved by the adjacent data tables. Validated: worst
# adjacent CVD dE 17.9 on white.
COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def _artifact_frames(cfg: Config) -> dict[str, pd.DataFrame]:
    paths = artifact_dirs(cfg)
    required = {
        "schedules": paths["data"] / "classical_schedules.csv",
        "frontier": paths["data"] / "efficient_frontier.csv",
        "impact": paths["data"] / "impact_model_comparison.csv",
        "classical_path": paths["data"] / "classical_path_tca.parquet",
        "classical": paths["metrics"] / "classical_strategy_summary.csv",
        "lob_trace": paths["data"] / "lob_trace_sample.csv",
        "lob": paths["metrics"] / "lob_strategy_summary.csv",
        "reactive": paths["metrics"] / "reactive_comparison.csv",
        "stress": paths["metrics"] / "stress_summary.csv",
        "ablation": paths["metrics"] / "ablation_summary.csv",
        "misspecification": paths["metrics"] / "misspecification_summary.csv",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing report inputs; run `python -m optimal_execution.cli all --config ...`: "
            + ", ".join(missing)
        )
    out: dict[str, pd.DataFrame] = {}
    for name, path in required.items():
        out[name] = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    return out


def _strategy_name(t: Translator, strategy_id: str) -> str:
    if strategy_id.startswith("rl_residual_s"):
        seed = strategy_id.rsplit("s", 1)[-1]
        return f"Residual RL (seed {seed})" if t.locale == "en" else f"残差RL（seed {seed}）"
    if strategy_id.startswith("rl_free_s"):
        seed = strategy_id.rsplit("s", 1)[-1]
        return f"Free RL (seed {seed})" if t.locale == "en" else f"自由RL（seed {seed}）"
    if strategy_id.startswith("without_"):
        feature = strategy_id.removeprefix("without_").replace("_", " ")
        if t.locale == "ja":
            feature = {
                "imbalance": "注文不均衡",
                "recent flow": "直近フロー",
                "transient impact": "過渡的インパクト",
                "volume state": "出来高状態",
                "vol state": "ボラティリティ状態",
            }.get(feature, feature)
        return f"Without {feature}" if t.locale == "en" else f"{feature} なし"
    return t.strategy(strategy_id)


def _impact_name(locale: str, name: str) -> str:
    labels = {
        "en": {
            "temporary_only": "Temporary only",
            "permanent_only": "Permanent only",
            "transient_only": "Transient only",
            "all": "All channels",
        },
        "ja": {
            "temporary_only": "一時的のみ",
            "permanent_only": "恒久的のみ",
            "transient_only": "過渡的のみ",
            "all": "全経路",
        },
    }
    return labels[locale].get(name, name)


def _regime_name(locale: str, name: str) -> str:
    labels = {
        "en": {
            "in_distribution": "In-distribution",
            "high_vol": "High volatility",
            "low_liquidity": "Low liquidity",
            "volume_shift": "Volume shift",
            "adverse_alpha": "Adverse alpha",
            "stressed_spread": "Stressed spread",
            "strict_limits": "Strict limit fills",
            "misspecified_simulator": "Misspecified simulator",
        },
        "ja": {
            "in_distribution": "分布内",
            "high_vol": "高ボラ",
            "low_liquidity": "低流動性",
            "volume_shift": "出来高シフト",
            "adverse_alpha": "逆選択アルファ",
            "stressed_spread": "スプレッド逼迫",
            "strict_limits": "厳格な指値約定",
            "misspecified_simulator": "誤指定シミュレータ",
        },
    }
    return labels.get(locale, {}).get(name, name)


def _axis(locale: str, en: str, ja: str) -> str:
    return en if locale == "en" else ja


def _base_layout(fig: go.Figure, title: str, height: int = 430) -> None:
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        height=height,
        margin={"l": 65, "r": 30, "t": 65, "b": 60},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Inter, Noto Sans JP, system-ui", "color": "#17202a"},
        hoverlabel={"bgcolor": "white", "font_color": "#17202a"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    fig.update_xaxes(showgrid=False, linecolor="#cbd5e1")
    fig.update_yaxes(gridcolor="#e8edf2", linecolor="#cbd5e1")


def _charts(frames: dict[str, pd.DataFrame], t: Translator) -> dict[str, go.Figure]:
    locale = t.locale
    charts: dict[str, go.Figure] = {}

    fig = go.Figure()
    for i, (strategy_id, group) in enumerate(
        frames["schedules"].groupby("strategy_id", sort=False)
    ):
        fig.add_trace(
            go.Scatter(
                x=group["time_s"],
                y=group["inventory_fraction"],
                mode="lines",
                line={"color": COLORS[i % len(COLORS)], "shape": "hv", "width": 2},
                name=f"{_strategy_name(t, strategy_id)} · {strategy_id}",
                hovertemplate=(
                    _axis(locale, "Time", "時刻")
                    + ": %{x:.0f} s<br>"
                    + _axis(locale, "Inventory ratio", "在庫比率")
                    + ": %{y:.3f}<extra></extra>"
                ),
            )
        )
    _base_layout(fig, t("chart.schedules"))
    fig.update_xaxes(title=_axis(locale, "Time (seconds)", "時刻（秒）"))
    fig.update_yaxes(
        title=_axis(locale, "Inventory / initial inventory", "在庫／初期在庫"), range=[0, 1.02]
    )
    charts["schedules"] = fig

    frontier = frames["frontier"]
    fig = go.Figure(
        go.Scatter(
            x=frontier["cost_sd_bps"],
            y=frontier["expected_cost_bps"],
            mode="lines+markers",
            line={"color": COLORS[0]},
            marker={
                "size": 7,
                "color": np.log10(frontier["lambda"]),
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {"title": "log10 λ"},
            },
            customdata=np.column_stack([frontier["lambda"], frontier["kappa_T"]]),
            hovertemplate="σ(IS): %{x:.3f} bps<br>E[IS]: %{y:.3f} bps<br>λ: %{customdata[0]:.2e}<br>κT: %{customdata[1]:.3f}<extra></extra>",
        )
    )
    _base_layout(fig, t("chart.efficient_frontier"))
    fig.update_xaxes(
        title=_axis(
            locale, "Timing-risk standard deviation (bps)", "タイミング・リスク標準偏差（bps）"
        )
    )
    fig.update_yaxes(title=_axis(locale, "Expected cost (bps)", "期待コスト（bps）"))
    charts["frontier"] = fig

    fig = go.Figure()
    for i, (name, group) in enumerate(frames["impact"].groupby("impact_model", sort=False)):
        fig.add_trace(
            go.Scatter(
                x=group["time_s"],
                y=group["execution_price"],
                mode="lines",
                line={"color": COLORS[i], "width": 2},
                name=f"{_impact_name(locale, name)} · {name}",
                customdata=np.column_stack([group["impacted_mid"], group["transient_state"]]),
                hovertemplate=(
                    _axis(locale, "Execution price", "約定価格")
                    + ": %{y:.4f}<br>"
                    + _axis(locale, "Impacted mid", "インパクト後仲値")
                    + ": %{customdata[0]:.4f}<br>"
                    + "D: %{customdata[1]:.4f}<extra></extra>"
                ),
            )
        )
    _base_layout(fig, t("chart.impact"))
    fig.update_xaxes(title=_axis(locale, "Time (seconds)", "時刻（秒）"))
    fig.update_yaxes(title=_axis(locale, "Price", "価格"))
    charts["impact"] = fig

    classical = frames["classical"]
    fig = go.Figure()
    x_names = [
        f"{_strategy_name(t, x)}<br><span style='font-size:10px'>{x}</span>"
        for x in classical["strategy_id"]
    ]
    for metric, key, color in (
        ("is_mean_bps", "metric_mean_is", COLORS[0]),
        ("cvar95_bps", "metric_cvar95", COLORS[1]),
    ):
        fig.add_trace(
            go.Bar(
                x=x_names,
                y=classical[metric],
                name=t(key),
                marker_color=color,
                hovertemplate="%{x}<br>%{y:.3f} bps<extra></extra>",
            )
        )
    _base_layout(fig, t("chart.classical_cost"), height=470)
    fig.update_layout(barmode="group")
    fig.update_yaxes(
        title=_axis(locale, "Cost (bps; higher is worse)", "コスト（bps、高いほど不利）")
    )
    charts["classical_cost"] = fig

    fig = go.Figure()
    for i, (strategy_id, group) in enumerate(
        frames["classical_path"].groupby("strategy_id", sort=False)
    ):
        values = np.sort(group["is_bps"].to_numpy())
        ecdf = np.arange(1, len(values) + 1) / len(values)
        fig.add_trace(
            go.Scatter(
                x=values,
                y=ecdf,
                mode="lines",
                line={"color": COLORS[i % len(COLORS)]},
                name=f"{_strategy_name(t, strategy_id)} · {strategy_id}",
                hovertemplate="IS: %{x:.3f} bps<br>F(IS): %{y:.3f}<extra></extra>",
            )
        )
    _base_layout(fig, t("chart.is_ecdf"))
    fig.update_xaxes(
        title=_axis(locale, "Implementation shortfall (bps)", "実装ショートフォール（bps）")
    )
    fig.update_yaxes(
        title=_axis(locale, "Empirical cumulative probability", "経験累積確率"), range=[0, 1]
    )
    charts["ecdf"] = fig

    trace = frames["lob_trace"]
    preferred = (
        "heuristic" if "heuristic" in set(trace["strategy_id"]) else trace["strategy_id"].iloc[0]
    )
    one = trace[(trace["strategy_id"] == preferred) & (trace["episode"] == 0)]
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            _axis(locale, "Displayed depth", "表示深度"),
            _axis(locale, "Queue imbalance and transient displacement", "注文不均衡と過渡的変位"),
        ),
    )
    fig.add_trace(
        go.Scatter(
            x=one["time_s"],
            y=one["bid_depth"],
            name=_axis(locale, "Bid depth", "買い板深度"),
            line={"color": COLORS[0]},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=one["time_s"],
            y=one["ask_depth"],
            name=_axis(locale, "Ask depth", "売り板深度"),
            line={"color": COLORS[1]},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=one["time_s"],
            y=one["imbalance"],
            name=_axis(locale, "Queue imbalance", "注文不均衡"),
            line={"color": COLORS[2]},
        ),
        row=2,
        col=1,
    )
    # D is normalized for the shared second-panel scale; the hover retains raw D.
    scale = max(float(one["transient_impact"].abs().max()), 1e-12)
    fig.add_trace(
        go.Scatter(
            x=one["time_s"],
            y=one["transient_impact"] / scale,
            customdata=one[["transient_impact"]],
            name=_axis(locale, "Transient impact (normalized)", "過渡的インパクト（正規化）"),
            line={"color": COLORS[3]},
            hovertemplate="D: %{customdata[0]:.5f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    _base_layout(fig, t("chart.lob"), height=620)
    fig.update_xaxes(title=_axis(locale, "Time (seconds)", "時刻（秒）"), row=2, col=1)
    fig.update_yaxes(title=_axis(locale, "Shares", "株数"), row=1, col=1)
    fig.update_yaxes(title=_axis(locale, "Normalized state", "正規化状態"), row=2, col=1)
    charts["lob"] = fig

    reactive = frames["reactive"]
    mode_labels = [
        {"reactive": "反応型", "replay": "リプレイ"}.get(x, x) if locale == "ja" else x.title()
        for x in reactive["mode"]
    ]
    fig = go.Figure(
        go.Bar(
            x=mode_labels,
            y=reactive["is_mean_bps"],
            marker_color=[COLORS[0], COLORS[1]],
            customdata=reactive[["cvar95_bps"]],
            hovertemplate=(
                "%{x}<br>"
                + t("metric_mean_is")
                + ": %{y:.3f} bps<br>"
                + t("metric_cvar95")
                + ": %{customdata[0]:.3f} bps<extra></extra>"
            ),
        )
    )
    _base_layout(fig, t("chart.reactive"))
    fig.update_yaxes(title=t("metric_mean_is"))
    charts["reactive"] = fig

    stress = frames["stress"]
    in_dist = stress[stress["regime"] == "in_distribution"]
    fig = go.Figure()
    x_names = [
        f"{_strategy_name(t, x)}<br><span style='font-size:10px'>{x}</span>"
        for x in in_dist["strategy_id"]
    ]
    fig.add_trace(
        go.Bar(
            x=x_names, y=in_dist["is_mean_bps"], name=t("metric_mean_is"), marker_color=COLORS[0]
        )
    )
    fig.add_trace(
        go.Bar(x=x_names, y=in_dist["cvar95_bps"], name=t("metric_cvar95"), marker_color=COLORS[1])
    )
    _base_layout(fig, t("chart.rl"), height=480)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title=_axis(locale, "Cost (bps)", "コスト（bps）"))
    charts["rl"] = fig

    pivot = stress.pivot(index="strategy_id", columns="regime", values="is_mean_bps")
    fig = go.Figure(
        go.Heatmap(
            z=pivot.to_numpy(),
            x=[_regime_name(locale, c) for c in pivot.columns],
            y=[f"{_strategy_name(t, x)} · {x}" for x in pivot.index],
            colorscale="Magma",
            colorbar={"title": "IS bps"},
            hovertemplate="%{y}<br>%{x}<br>%{z:.3f} bps<extra></extra>",
        )
    )
    _base_layout(fig, t("chart.stress"), height=max(470, 65 * len(pivot)))
    fig.update_xaxes(title=_axis(locale, "Evaluation regime", "評価レジーム"))
    fig.update_yaxes(title=_axis(locale, "Strategy", "戦略"))
    charts["stress"] = fig

    ablation = frames["ablation"].sort_values("delta_vs_full_bps")
    fig = go.Figure(
        go.Bar(
            x=ablation["delta_vs_full_bps"],
            y=[_strategy_name(t, x) for x in ablation["strategy_id"]],
            orientation="h",
            marker_color=COLORS[0],
            customdata=ablation[["is_mean_bps"]],
            hovertemplate="ΔIS: %{x:.3f} bps<br>IS: %{customdata[0]:.3f} bps<extra></extra>",
        )
    )
    _base_layout(fig, t("chart.ablation"), height=470)
    fig.add_vline(x=0, line_width=1, line_color="#64748b")
    fig.update_xaxes(
        title=_axis(
            locale,
            "Change versus matched-budget full-feature reference (bps)",
            "学習量一致の全特徴量参照方策との差（bps）",
        )
    )
    charts["ablation"] = fig

    miss = frames["misspecification"].sort_values("is_mean_bps")
    fig = go.Figure(
        go.Bar(
            x=[
                f"{_strategy_name(t, x)}<br><span style='font-size:10px'>{x}</span>"
                for x in miss["strategy_id"]
            ],
            y=miss["is_mean_bps"],
            marker_color=COLORS[1],
            customdata=miss[["cvar95_bps"]],
            hovertemplate=(
                t("metric_mean_is")
                + ": %{y:.3f} bps<br>"
                + t("metric_cvar95")
                + ": %{customdata[0]:.3f} bps<extra></extra>"
            ),
        )
    )
    _base_layout(fig, t("table.misspecification"), height=470)
    fig.update_yaxes(title=t("metric_mean_is"))
    charts["misspecification"] = fig
    return charts


def _fig_html(figures: dict[str, go.Figure]) -> dict[str, str]:
    out: dict[str, str] = {}
    first = True
    for name, fig in figures.items():
        out[name] = pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs="inline" if first else False,
            config={"displayModeBar": False, "responsive": True, "scrollZoom": False},
            default_width="100%",
        )
        first = False
    return out


def _format(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "—"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return f"{float(value):,.{digits}f}"


def _table(frame: pd.DataFrame, t: Translator, caption: str | None = None) -> str:
    columns = [
        ("strategy_id", t("metric_strategy")),
        ("n_paths", t("metric_paths")),
        ("is_mean_bps", t("metric_mean_is")),
        ("is_std_bps", t("metric_std_is")),
        ("cvar95_bps", t("metric_cvar95")),
        ("cleanup_qty", t("metric_cleanup")),
        ("fill_rate", t("metric_fill_rate")),
    ]
    active = [(key, label) for key, label in columns if key in frame]
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in active)
    body_rows = []
    for _, row in frame.iterrows():
        cells = []
        for key, _ in active:
            if key == "strategy_id":
                strategy_id = str(row[key])
                text = f"{html.escape(_strategy_name(t, strategy_id))} <code>{html.escape(strategy_id)}</code>"
            elif key == "n_paths":
                text = _format(row[key], 0)
            elif key == "fill_rate":
                text = _format(row[key] * 100.0, 1) + "%" if pd.notna(row[key]) else "—"
            elif key == "cleanup_qty":
                text = _format(row[key], 0)
            else:
                text = _format(row[key])
            cells.append(f"<td>{text}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    caption_html = (
        f'<caption style="caption-side:top;text-align:left;color:var(--muted);'
        f'font-size:.84rem;font-variant-numeric:normal;white-space:normal;padding:8px 12px">'
        f"{html.escape(caption)}</caption>"
        if caption
        else ""
    )
    return (
        f'<div class="table-wrap"><table>{caption_html}<thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _quantitative_payload(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name in ("classical", "lob", "reactive", "stress", "ablation", "misspecification"):
        frame = frames[name]
        numeric = frame.select_dtypes(include=[np.number]).round(10)
        id_cols = [c for c in ("strategy_id", "mode", "regime", "feature_removed") if c in frame]
        payload[name] = pd.concat(
            [frame[id_cols].reset_index(drop=True), numeric.reset_index(drop=True)], axis=1
        ).to_dict(orient="records")
    payload = json_safe(payload)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "metrics": payload,
    }


def _paired_delta_ci(
    path_frame: pd.DataFrame,
    best: str,
    runner: str,
    seed: int,
    regime: str | None = None,
) -> tuple[float, float, float]:
    """Paired 95% bootstrap CI of mean(IS_best - IS_runner) in bps.

    Common-random-number pairs are aligned by within-strategy row order (the
    evaluators write each strategy's paths/episodes in identical scenario
    order). A negative delta means ``best`` is genuinely cheaper; the claim is
    significant only when the whole CI lies below zero.
    """
    df = path_frame
    if regime is not None and "regime" in df.columns:
        df = df[df["regime"] == regime]
    a = df.loc[df["strategy_id"] == best, "is_bps"].to_numpy()
    b = df.loc[df["strategy_id"] == runner, "is_bps"].to_numpy()
    n = min(len(a), len(b))
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    d = a[:n] - b[:n]
    lo, hi = bootstrap_mean_ci(d, seed=seed)
    return float(d.mean()), lo, hi


def _two_lowest(summary: pd.DataFrame) -> tuple[str, str | None]:
    s = summary.sort_values("is_mean_bps")
    best = str(s.iloc[0]["strategy_id"])
    runner = str(s.iloc[1]["strategy_id"]) if len(s) > 1 else None
    return best, runner


def _read_path_parquet(data: Path, name: str) -> pd.DataFrame | None:
    """Per-path/episode TCA frame if present (always written by the full
    pipeline); None lets the report degrade to a mean-only claim."""
    path = data / name
    return pd.read_parquet(path) if path.exists() else None


def _mean_of(summary: pd.DataFrame, strategy_id: str) -> float:
    return float(summary.loc[summary["strategy_id"] == strategy_id, "is_mean_bps"].iloc[0])


def _findings(cfg: Config, frames: dict[str, pd.DataFrame], t: Translator) -> dict[str, str]:
    data = artifact_dirs(cfg)["data"]
    classical_path = _read_path_parquet(data, "classical_path_tca.parquet")
    lob_path = _read_path_parquet(data, "lob_path_tca.parquet")
    rl_path = _read_path_parquet(data, "rl_evaluation_path_tca.parquet")

    def best_stmt(world: str, summary: pd.DataFrame, path_frame: pd.DataFrame | None) -> str:
        best, runner = _two_lowest(summary)
        if runner is None:
            return t("finding_single", world=world, best=_strategy_name(t, best))
        names = {"best": _strategy_name(t, best), "runner": _strategy_name(t, runner)}
        if path_frame is not None:
            delta, lo, hi = _paired_delta_ci(path_frame, best, runner, cfg.seed)
        else:
            delta, lo, hi = float("nan"), float("nan"), float("nan")
        if not np.isfinite(delta):  # per-path data absent: mean-only, no CI
            mean_delta = _mean_of(summary, best) - _mean_of(summary, runner)
            return t("finding_best_mean_only", world=world, delta=mean_delta, **names)
        significant = np.isfinite(hi) and hi < 0.0
        key = "finding_best_significant" if significant else "finding_best_not_significant"
        return t(key, world=world, delta=delta, lo=lo, hi=hi, **names)

    classical_stmt = best_stmt(t("world_classical"), frames["classical"], classical_path)
    lob_stmt = best_stmt(t("world_lob"), frames["lob"], lob_path)

    reactive = frames["reactive"].set_index("mode")
    reactive_cost = float(reactive.loc["reactive", "is_mean_bps"])
    replay_cost = float(reactive.loc["replay", "is_mean_bps"])
    reactive_finding = t(
        "finding_reactive_template",
        reactive=reactive_cost,
        replay=replay_cost,
        delta=reactive_cost - replay_cost,
    )

    in_dist = frames["stress"][frames["stress"]["regime"] == "in_distribution"]
    rl_rows = in_dist[in_dist["strategy_id"].str.startswith("rl_")]
    scripted = in_dist[~in_dist["strategy_id"].str.startswith("rl_")]
    if rl_rows.empty or scripted.empty:
        rl_statement = t("finding_rl_unavailable")
    else:
        rl_best = str(rl_rows.loc[rl_rows["is_mean_bps"].idxmin(), "strategy_id"])
        sc_best = str(scripted.loc[scripted["is_mean_bps"].idxmin(), "strategy_id"])
        names = {"best": _strategy_name(t, rl_best), "runner": _strategy_name(t, sc_best)}
        if rl_path is not None:
            delta, lo, hi = _paired_delta_ci(
                rl_path, rl_best, sc_best, cfg.seed, regime="in_distribution"
            )
        else:
            delta, lo, hi = float("nan"), float("nan"), float("nan")
        if not np.isfinite(delta):  # per-path data absent: mean-only, no CI
            mean_delta = float(rl_rows["is_mean_bps"].min()) - float(scripted["is_mean_bps"].min())
            rl_statement = t("finding_rl_mean_only", delta=mean_delta, **names)
        else:
            significant = np.isfinite(hi) and hi < 0.0
            key = "finding_rl_significant" if significant else "finding_rl_not_significant"
            rl_statement = t(key, delta=delta, lo=lo, hi=hi, **names)

    residual = rl_rows[rl_rows["strategy_id"].str.startswith("rl_residual_")]
    if residual.empty:
        id_cost = float("nan")
        shift_cost = float("nan")
    else:
        best_id = str(residual.loc[residual["is_mean_bps"].idxmin(), "strategy_id"])
        id_cost = float(residual.loc[residual["strategy_id"] == best_id, "is_mean_bps"].iloc[0])
        matched = frames["misspecification"][frames["misspecification"]["strategy_id"] == best_id]
        shift_cost = float(matched["is_mean_bps"].iloc[0]) if not matched.empty else float("nan")
    shift_finding = t(
        "finding_shift_template", id_cost=id_cost, shift_cost=shift_cost, delta=shift_cost - id_cost
    )
    conclusion = t(
        "conclusion_template",
        classical_stmt=classical_stmt,
        lob_stmt=lob_stmt,
        rl_statement=rl_statement,
    )
    return {"reactive": reactive_finding, "shift": shift_finding, "conclusion": conclusion}


def _related_work_html(t: Translator) -> str:
    """Localized related-work section.

    Field framing, the core models structured as problem -> proposal -> results
    -> open questions, and a summary table (reference / approach / short note).
    The same substance appears in the visual-lab notebook's survey cell.
    """
    e = html.escape
    if t.locale == "ja":
        framing = (
            "最適執行が扱う中心問題は「速度のトレードオフ」です。大口の注文を決められた"
            "時間内に売買するとき、速く執行すれば市場インパクト（自分の売買が価格を不利な"
            "方向へ動かす効果）を多く払い、ゆっくり執行すればその間の価格変動（タイミング・"
            "リスク）に晒されます。先行研究は、この費用を実装ショートフォール（到着価格に"
            "対する超過コスト）の期待値・分散・テールで定量化し、最適な執行スケジュールや"
            "戦術を求めてきました。派生する問いは大きく3つ——(1) 市場インパクトをどう"
            "モデル化するか、(2) 注文板の内生的な反応・約定確率・逆選択をどう扱うか、"
            "(3) モデル化しきれない動学の下で適応的な執行を学習できるか——であり、本ラボは"
            "この3軸を可視化します。"
        )
        core_heading = "コア文献：問題 → 提案 → 結果 → 今後の課題"
        labels = ("問題", "提案", "結果", "今後")
        sep = "："
        core = [
            (
                "Almgren–Chriss (2001)",
                "平均–分散の執行スケジュール（実装：almgren_chriss.py）",
                "線形インパクトの下で、期待執行コストと分散のトレードオフをどう最適化するか。",
                "離散時間の平均–分散目的 E[C] + λ·Var[C] を解き、閉形式の sinh 在庫軌道と効率的フロンティアを導出。",
                "リスク回避度 λ が大きいほど執行を前倒しし、λ→0 で TWAP に収束。効率的フロンティアが実務のベンチマークになった。",
                "非線形・過渡的インパクト、内生的な板、確率的ボラティリティへの一般化。",
            ),
            (
                "Obizhaeva–Wang (2013)",
                "回復力のある流動性（実装：resilience.py）",
                "板の流動性が有限で、消費後に時間をかけて回復（resilience）する動学の下での最適執行。",
                "指数回復核をもつ板で価値関数を最小化し、「端点ブロック＋一定率＋端点ブロック」の閉形式スケジュールを導出。",
                "回復が速いほど連続的な執行、遅いほど端点への集中となる。過渡的インパクトを明示的に扱う枠組み。",
                "一般核（伝播核）、確率的流動性、マルチアセットのクロスインパクト。",
            ),
            (
                "伝播核：Bouchaud et al. (2004) / Gatheral (2010)",
                "過渡的インパクトの一般理論",
                "一時的／恒久的の二分法では説明できないインパクトの時間減衰をどう表すか。",
                "過去の取引を減衰核 G で重み付けした和で現在のインパクトを表現する（I(t) = Σ_{s<t} G(t−s)·v_s、v_s は取引速度）。Gatheral は無裁定と両立する核の条件を与えた。",
                "過渡的インパクトを一般化。Obizhaeva–Wang の指数回復はその特殊例にあたる。",
                "非線形伝播、経験核の推定、執行最適化との統合。",
            ),
            (
                "インパクトのサイズ依存：Almgren et al. (2005) / Tóth et al. (2011)",
                "べき乗インパクトの直接推定と平方根則（診断：sqrt_impact）",
                "メタオーダー（分割された大口注文）のインパクトは注文サイズにどう依存するか。",
                "Almgren et al. (2005) は株式インパクトを直接推定し、一時的インパクトはべき指数 ≈0.6（3/5）、恒久的インパクトは線形とした。指数 1/2 の平方根則とその普遍性は Tóth et al. (2011) が流動性の希少性・臨界性から論じた。",
                "サイズに対して凹なインパクト。単純な線形外挿は大口で過大評価しやすい。",
                "時間依存性・日中変動の取り込み、線形モデルとの整合。本ラボの sqrt_impact は定型化した指数 1/2（σ·√(Q/V)）を用い、線形モデルには加算しない。",
            ),
            (
                "強化学習：Nevmyvaka et al. (2006) / Hendricks–Wilcox (2014) / PPO：Schulman et al. (2017, 2016)",
                "適応的執行（実装：rl_training.py, environment.py）",
                "解析的にモデル化しきれない板動学の下で、適応的な執行方策を直接学習できるか。",
                "状態（在庫・残時間・板特徴）から行動（子注文）への写像を学習。Hendricks–Wilcox は AC ベースラインまわりの調整（残差 RL の源流）。本ラボは PPO のクリップ代理目的＋GAE に安全層を重ねる。",
                "シミュレータ内ではルールベースを下回ることがあるが、報酬設計・学習量・シードに強く依存する。",
                "現実的な板較正、明示的なリスク制約、マルチシードでの頑健性、オフライン RL。",
            ),
        ]
        list_heading = "先行研究一覧（アプローチと短サマリー）"
        list_intro = "上記コア以外も含めた、本ラボが依拠・参照する主な先行研究です。"
        cols = ("文献", "アプローチ", "短サマリー")
        rows = [
            (
                "Bertsimas–Lo (1998)",
                "リスク中立の動的計画法",
                "期待コスト最小化。線形インパクトでは等分割（TWAP）が最適。AC の前身。",
            ),
            (
                "Almgren–Chriss (2001)",
                "平均–分散最適化",
                "閉形式 sinh 軌道と効率的フロンティア。本ラボの古典ベンチマーク。",
            ),
            (
                "Obizhaeva–Wang (2013)",
                "回復力ある板の最適制御",
                "端点ブロック＋一定率スケジュール。過渡的インパクトを明示。",
            ),
            (
                "Kyle (1985)",
                "情報均衡モデル",
                "線形の恒久インパクト（Kyle's λ）と逆選択の理論的基礎。",
            ),
            ("Perold (1988)", "コスト指標の定義", "実装ショートフォール。本ラボ全体の評価指標。"),
            (
                "Bouchaud et al. (2004)",
                "伝播核（応答関数）",
                "過渡的インパクトを減衰核で一般化する視点。",
            ),
            ("Gatheral (2010)", "無裁定条件", "インパクトと減衰核の無裁定整合条件を導出。"),
            (
                "Almgren et al. (2005)",
                "実証推定",
                "株式インパクトを直接推定：一時的はべき指数≈0.6、恒久的は線形。",
            ),
            (
                "Tóth et al. (2011)",
                "臨界性の議論",
                "平方根則（指数1/2）の普遍性を流動性の希少性から説明。",
            ),
            ("Nevmyvaka et al. (2006)", "強化学習", "執行に RL を本格適用した嚆矢。"),
            (
                "Hendricks–Wilcox (2014)",
                "RL × AC",
                "AC ベースラインまわりの RL 調整（残差 RL の発想）。",
            ),
            ("Schulman et al. (2017)", "PPO", "クリップ代理目的。本ラボの方策最適化アルゴリズム。"),
            ("Schulman et al. (2016)", "GAE", "一般化アドバンテージ推定。分散を抑えた優位性推定。"),
            (
                "Huang–Lehalle–Rosenbaum (2015)",
                "Queue-reactive モデル",
                "状態依存の点過程で板を反応的に生成。反応型シミュレータの正典。",
            ),
            (
                "Gatheral–Jaisson–Rosenbaum (2018)",
                "ラフボラティリティ",
                "ボラティリティの粗さ。将来拡張（ロードマップ項目）。",
            ),
            (
                "Bacry et al. (2015)",
                "Hawkes 過程",
                "自己励起する注文フロー。将来拡張（ロードマップ項目）。",
            ),
            (
                "Cartea–Jaimungal–Penalva (2015)",
                "教科書",
                "アルゴリズム・高頻度取引の体系的教科書。",
            ),
            ("Guéant (2016)", "教科書", "最適執行からマーケットメイクまでの数理。"),
        ]
    else:
        framing = (
            "The central problem of optimal execution is a trade-off in speed. When a "
            "large order must be traded within a fixed horizon, trading faster pays more "
            "market impact (the adverse price move caused by one's own trading), while "
            "trading slower exposes the order to price moves over time (timing risk). "
            "Prior work quantifies this cost through the expectation, variance, and tail "
            "of implementation shortfall (excess cost relative to the arrival price) and "
            "seeks optimal execution schedules and tactics. Three derived questions "
            "dominate: (1) how to model market impact, (2) how to treat the endogenous "
            "reaction of the order book, fill probability, and adverse selection, and "
            "(3) whether adaptive execution can be learned under dynamics that cannot be "
            "fully modeled. This lab visualizes these three axes."
        )
        core_heading = "Core works: problem -> proposal -> results -> open questions"
        labels = ("Problem", "Proposal", "Results", "Open questions")
        sep = ": "
        core = [
            (
                "Almgren–Chriss (2001)",
                "Mean–variance execution schedule (implementation: almgren_chriss.py)",
                "Under linear impact, how to optimize the trade-off between expected execution cost and its variance.",
                "Solve a discrete-time mean–variance objective E[C] + λ·Var[C], yielding a closed-form sinh inventory trajectory and an efficient frontier.",
                "Higher risk aversion λ front-loads trading; λ→0 recovers TWAP. The efficient frontier became a practitioner benchmark.",
                "Generalization to nonlinear/transient impact, endogenous order books, and stochastic volatility.",
            ),
            (
                "Obizhaeva–Wang (2013)",
                "Resilient liquidity (implementation: resilience.py)",
                "Optimal execution when book liquidity is finite and recovers (resilience) over time after consumption.",
                "Minimize a value function in a book with an exponential resilience kernel, giving a closed-form block + constant-rate + block schedule.",
                "Faster resilience yields more continuous trading; slower yields concentration at the endpoints. An explicit treatment of transient impact.",
                "General (propagator) kernels, stochastic liquidity, multi-asset cross-impact.",
            ),
            (
                "Propagator: Bouchaud et al. (2004) / Gatheral (2010)",
                "A general theory of transient impact",
                "How to represent the time decay of impact that the temporary/permanent dichotomy cannot capture.",
                "Express current impact as a decay-kernel-weighted sum of past trades, I(t) = Σ_{s<t} G(t−s)·v_s (v_s is the trade rate). Gatheral derived the no-arbitrage condition on admissible kernels.",
                "Generalizes transient impact; Obizhaeva–Wang's exponential resilience is a special case.",
                "Nonlinear propagation, empirical kernel estimation, integration with execution optimization.",
            ),
            (
                "Size dependence of impact: Almgren et al. (2005) / Tóth et al. (2011)",
                "Direct estimation of power-law impact and the square-root law (diagnostic: sqrt_impact)",
                "How does the impact of a metaorder depend on its size?",
                "Almgren et al. (2005) directly estimate equity impact: temporary impact follows a power law with exponent ≈0.6 (3/5) and permanent impact is linear. The exponent-1/2 square-root law and its universality are argued by Tóth et al. (2011) from the critical scarcity of liquidity.",
                "Impact is concave in size, so a naive linear extrapolation over-estimates large orders.",
                "Time dependence and intraday variation; consistency with linear models. The lab's sqrt_impact uses a stylized exponent-1/2 form (σ·√(Q/V)) and does not add it to the linear model.",
            ),
            (
                "RL: Nevmyvaka et al. (2006) / Hendricks–Wilcox (2014) / PPO: Schulman et al. (2017, 2016)",
                "Adaptive execution (implementation: rl_training.py, environment.py)",
                "Can an adaptive execution policy be learned directly under book dynamics that resist analytical modeling?",
                "Learn a map from state (inventory, time remaining, book features) to action (child orders). Hendricks–Wilcox adjust around an AC baseline (the residual-RL idea). This lab layers a safety wrapper on PPO's clipped surrogate objective with GAE.",
                "Inside the simulator RL can underperform rule-based policies; outcomes depend strongly on reward design, training budget, and seed.",
                "Realistic book calibration, explicit risk constraints, multi-seed robustness, offline RL.",
            ),
        ]
        list_heading = "Related work at a glance (approach and short note)"
        list_intro = (
            "The main prior work this lab relies on or references, beyond the core models above."
        )
        cols = ("Reference", "Approach", "Note")
        rows = [
            (
                "Bertsimas–Lo (1998)",
                "Risk-neutral dynamic programming",
                "Minimizes expected cost; with linear impact, equal splitting (TWAP) is optimal. Precursor to AC.",
            ),
            (
                "Almgren–Chriss (2001)",
                "Mean–variance optimization",
                "Closed-form sinh trajectory and efficient frontier. The lab's classical benchmark.",
            ),
            (
                "Obizhaeva–Wang (2013)",
                "Optimal control of a resilient book",
                "Block + constant-rate schedule; explicit transient impact.",
            ),
            (
                "Kyle (1985)",
                "Informational equilibrium",
                "Linear permanent impact (Kyle's λ) and the basis for adverse selection.",
            ),
            (
                "Perold (1988)",
                "Cost metric",
                "Implementation shortfall; the evaluation metric throughout the lab.",
            ),
            (
                "Bouchaud et al. (2004)",
                "Propagator (response function)",
                "Generalizes transient impact via a decay kernel.",
            ),
            (
                "Gatheral (2010)",
                "No-arbitrage condition",
                "Derives the no-arbitrage consistency between impact and decay kernel.",
            ),
            (
                "Almgren et al. (2005)",
                "Empirical estimation",
                "Directly estimates equity impact: temporary power ≈0.6, permanent linear.",
            ),
            (
                "Tóth et al. (2011)",
                "Criticality argument",
                "Explains the universality of the square-root (exponent-1/2) law via liquidity scarcity.",
            ),
            (
                "Nevmyvaka et al. (2006)",
                "Reinforcement learning",
                "The first substantial application of RL to execution.",
            ),
            (
                "Hendricks–Wilcox (2014)",
                "RL × AC",
                "RL adjustment around an AC baseline (the residual-RL idea).",
            ),
            (
                "Schulman et al. (2017)",
                "PPO",
                "Clipped surrogate objective; the lab's policy optimizer.",
            ),
            (
                "Schulman et al. (2016)",
                "GAE",
                "Generalized advantage estimation; low-variance advantages.",
            ),
            (
                "Huang–Lehalle–Rosenbaum (2015)",
                "Queue-reactive model",
                "Reactive book from state-dependent point processes; the canon for the reactive simulator.",
            ),
            (
                "Gatheral–Jaisson–Rosenbaum (2018)",
                "Rough volatility",
                "Roughness of volatility; a roadmap extension.",
            ),
            (
                "Bacry et al. (2015)",
                "Hawkes processes",
                "Self-exciting order flow; a roadmap extension.",
            ),
            (
                "Cartea–Jaimungal–Penalva (2015)",
                "Textbook",
                "Systematic textbook on algorithmic and high-frequency trading.",
            ),
            ("Guéant (2016)", "Textbook", "Mathematics from optimal execution to market making."),
        ]

    parts = [f"<p>{e(framing)}</p>", f"<h3>{e(core_heading)}</h3>"]
    for title, subtitle, problem, proposal, result, future in core:
        items = "".join(
            f"<li><strong>{e(lab)}</strong>{e(sep)}{e(txt)}</li>"
            for lab, txt in zip(labels, (problem, proposal, result, future), strict=True)
        )
        parts.append(f"<p><strong>{e(title)}</strong> — {e(subtitle)}</p><ul>{items}</ul>")
    parts.append(f"<h3>{e(list_heading)}</h3>")
    parts.append(f"<p>{e(list_intro)}</p>")
    head = "".join(f'<th style="text-align:left">{e(c)}</th>' for c in cols)
    body = "".join(
        "<tr>"
        + "".join(f'<td style="text-align:left;white-space:normal">{e(v)}</td>' for v in row)
        + "</tr>"
        for row in rows
    )
    parts.append(
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )
    return "".join(parts)


def _model_theory_html(t: Translator, charts: dict[str, str]) -> str:
    """Localized model-theory section.

    Per model: description, typeset equations (LaTeX -> MathML at build time,
    offline and font-free), a variable glossary, and qualitative
    strengths/weaknesses, closing with cross-model commonalities. The equations
    mirror the implementation modules (almgren_chriss/impact/resilience/
    order_book/rl_training); only the prose is localized.
    """
    from latex2mathml.converter import convert

    e = html.escape

    def eqs(*latex: str) -> str:
        return "".join(f'<div class="eq">{convert(x, display="block")}</div>' for x in latex)

    eq = {
        "ac": (
            r"J[x] = \int_0^T \left( \eta\, \dot{x}^2 + \lambda\, \sigma^2 x^2 \right) dt, \quad \kappa = \sqrt{\lambda\, \sigma^2 / \eta}",
            r"x^*(t) = X\, \frac{\sinh(\kappa (T-t))}{\sinh(\kappa T)}",
            r"\mathbb{E}[C] = \frac{\gamma}{2} X^2 + \eta \sum_k \frac{q_k^2}{\Delta t}, \quad \mathrm{Var}[C] = \sum_k \sigma_k^2\, \Delta t\, x_{k+1}^2",
        ),
        "impact": (
            r"f_{\mathrm{temp}} = \eta\, v, \quad v = q / \Delta t",
            r"D_{k+1} = e^{-\rho\, \Delta t} \left( D_k + \eta_t\, q_k \right)",
            r"D_k = \sum_{j<k} G\left( (k-j)\, \Delta t \right) \eta_t\, q_j",
            r"G(\tau) = e^{-\rho \tau}, \quad G(\tau) = \left( 1 + \tau/\tau_0 \right)^{-\beta}",
            r"I(Q) = Y\, \sigma_d\, \sqrt{Q / \mathrm{ADV}}",
        ),
        "ow": (
            r"C(q) = \frac{1}{2} \eta_t\, q' M q, \quad M_{kj} = G(|k-j|\, \Delta t), \quad M_{kk} = 1",
            r"q_0 = q_N = \frac{X}{\rho T + 2}, \quad \mathrm{rate} = \frac{\rho X}{\rho T + 2}",
            r"q = \frac{M^{-1} \mathbf{1}}{\mathbf{1}' M^{-1} \mathbf{1}}\, X",
        ),
        "lob": (
            r"I = \frac{Q^b - Q^a}{Q^b + Q^a} \in [-1, 1]",
            r"\lambda = \lambda_0\, \exp\left( \min(g, 10) \right)",
            r"g = \beta_0 + \beta_1 I + \beta_2 r + \beta_3 s",
            r"\alpha_k = \phi\, \alpha_{k-1} + \sigma_\alpha Z_k",
        ),
        "rl": (
            r"w_t = \exp\left( \log \pi_\theta(a_t | s_t) - \log \pi_{\mathrm{old}} \right)",
            r"L_{\mathrm{clip}} = \mathbb{E} \left[ \min\left( w_t \hat{A}_t,\ \mathrm{clip}(w_t, 1-\epsilon, 1+\epsilon)\, \hat{A}_t \right) \right]",
            r"\hat{A}_t = \sum_{l \ge 0} (\gamma \lambda)^l\, \delta_{t+l}, \quad \delta_t = r_t + \gamma V_{t+1} - V_t",
            r"a_t = a_t^{\mathrm{AC}} + \Delta a_t",
        ),
    }

    if t.locale == "ja":
        vars_h, str_h, weak_h, common_h = "変数", "強み", "弱み", "モデル間の共通点"

        def impl(f: str) -> str:
            return f"（実装：<code>{e(f)}</code>）"

        models = [
            {
                "key": "ac",
                "title": "Almgren–Chriss（平均–分散の最適執行）",
                "impl": "almgren_chriss.py",
                "desc": "線形の一時的インパクトと既知のボラティリティの下で、期待執行コストと分散のトレードオフを平均–分散目的で最小化する。連続解は sinh 軌道、離散解は決定グリッド上の子注文列で与えられる。",
                "vars": [
                    ("X", "初期在庫（株）"),
                    ("T", "執行時間（秒）"),
                    ("η", "一時的インパクト係数"),
                    ("γ", "恒久的インパクト係数"),
                    ("σ, σ_k", "ボラティリティ（σ_k はステップ別）"),
                    ("λ", "リスク回避度"),
                    ("κ", "緊急度 √(λσ²/η)、κ→0 で TWAP"),
                    ("q_k, x_k", "ステップ k の子注文／開始時在庫"),
                    ("Δt", "決定ステップ幅"),
                ],
                "strengths": [
                    "閉形式で解釈可能。効率的フロンティアが一目で描ける。",
                    "リスク回避度で前倒し／後ろ倒しを1パラメータ制御。",
                    "実務のベンチマーク（TWAP は κ→0 の特例）。",
                ],
                "weaknesses": [
                    "インパクトは線形固定で、板の内生反応を含まない。",
                    "ボラティリティを既知とし、過渡的（回復する）インパクトを扱わない。",
                    "静的スケジュールで、途中の状態観測に適応しない。",
                ],
            },
            {
                "key": "impact",
                "title": "市場インパクトの3経路＋平方根則",
                "impl": "impact.py",
                "desc": "インパクトを一時的（取引中のみ）・恒久的（中値を恒久シフト）・過渡的（回復核で減衰）に分解する。平方根則は総量に対する凹なインパクトで、線形モデルには加算しない独立診断（指数1/2は定型化した選択で、Almgren et al. (2005) の実証では一時的インパクトのべき指数は ≈0.6）。",
                "vars": [
                    ("v", "取引速度 q/Δt"),
                    ("η", "一時的係数"),
                    ("γ", "恒久的係数"),
                    ("η_t", "過渡的係数"),
                    ("ρ", "回復速度（resilience）"),
                    ("D_k", "ステップ k が見る過渡変位"),
                    ("G(τ)", "減衰核（指数／べき）"),
                    ("β, τ_0", "べき核パラメータ"),
                    ("Q, ADV, Y, σ_d", "総量・平均日次出来高・スケール・日次ボラ"),
                ],
                "strengths": [
                    "各経路が分離され、TCA 分解が厳密。",
                    "回復（過渡的インパクト）を核 G で明示。",
                    "平方根則を実証診断として併置できる。",
                ],
                "weaknesses": [
                    "パラメータは合成で、実データ較正なし。",
                    "線形（平方根則は非加算の別枠）。",
                    "クロスインパクト（多資産）は対象外。",
                ],
            },
            {
                "key": "ow",
                "title": "Obizhaeva–Wang（回復力ある流動性の最適執行）",
                "impl": "resilience.py",
                "desc": "純粋に過渡的な線形インパクトとブロック型の板の下で、二次形式の期待コストを最小化する。指数回復では『端点ブロック＋一定率』の閉形式、一般核では非負制約付き QP で解く。離散解は格子の細分で閉形式に収束することを検証済み（test_resilience）。",
                "vars": [
                    ("M", "核相関行列 M_{kj}=G(|k−j|Δt)"),
                    ("η_t", "過渡的インパクト係数"),
                    ("ρ", "回復速度"),
                    ("X", "初期在庫"),
                    ("q", "子注文ベクトル（Σq=X, q≥0）"),
                    ("1", "全 1 ベクトル"),
                ],
                "strengths": [
                    "指数核で閉形式、一般核でも QP が well-posed（M は正定値）。",
                    "過渡的インパクトを最適制御として明示的に扱う。",
                    "回復速度 ρ が執行の集中度を直接説明。",
                ],
                "weaknesses": [
                    "リスク中立（リスク回避は AC レイヤに委譲）。",
                    "ブロック型の板を仮定。",
                    "単一資産・単一銘柄。",
                ],
            },
            {
                "key": "lob",
                "title": "反応型リミットオーダーブック",
                "impl": "order_book.py",
                "desc": "注文不均衡・直近リターン・ストレスに応じて成行到着強度が変わる、状態依存の板。自分の成行は表示深度を消費して価格を動かし、指値は FIFO キューで約定し逆選択に晒される。",
                "vars": [
                    ("Q^b, Q^a", "買い／売り板深度"),
                    ("I", "注文不均衡 ∈[−1,1]"),
                    ("λ, λ_0", "成行到着強度／基準強度（cap で飽和）"),
                    ("g", "tilt（強度の対数線形傾き）"),
                    ("β_0..β_3", "切片・不均衡・リターン・ストレス係数"),
                    ("α_k", "潜在短期アルファ（AR(1)）"),
                    ("φ, σ_α, Z_k", "持続・撹乱スケール・標準正規"),
                ],
                "strengths": [
                    "板の内生反応・約定確率・逆選択・自己インパクトを捕捉。",
                    "成行の板歩きとスプレッド拡大を明示。",
                    "潜在アルファで逆選択経路を再現。",
                ],
                "weaknesses": [
                    "単一価格帯近似で、キュー順位・逆選択は代理。",
                    "実注文データに較正していない。",
                    "遅延・取引所分断・相場操縦規制は含まない。",
                ],
            },
            {
                "key": "rl",
                "title": "強化学習方策（PPO＋GAE、残差／自由）",
                "impl": "rl_training.py, environment.py",
                "desc": "状態（在庫・残時間・板特徴）から子注文への写像を PPO で最適化する。残差版は Almgren–Chriss をベースラインに調整を学習し、共通の安全層が過剰執行を防ぐ。学習は整形報酬、評価は経済的 IS。",
                "vars": [
                    ("w_t", "確率比 π_θ/π_old"),
                    ("Â_t", "GAE 優位性"),
                    ("δ_t", "TD 誤差"),
                    ("V", "価値関数"),
                    ("r_t", "（整形）報酬"),
                    ("γ, λ", "割引・GAE 係数"),
                    ("ε", "クリップ幅"),
                    ("a_t^AC", "AC ベースライン行動（残差版）"),
                ],
                "strengths": [
                    "板動学に適応、モデルフリー。",
                    "安全層で子注文・参加率・価格を制約。",
                    "残差版は AC を内包し学習が安定。",
                ],
                "weaknesses": [
                    "報酬設計・学習量・シードに強く依存。",
                    "シミュレータに依存し、実市場の因果ではない。",
                    "非解釈的で、quick は1シードのため優位性は記述的。",
                ],
            },
        ]
        commons = [
            "共通の状態変数（在庫 x、残時間、価格）と共通指標（実装ショートフォール IS、bps）で全モデルを評価する。",
            "インパクトは『取引の速さ・量で増加し、時間で（一部）回復する』という同じ構造：η（瞬間）・γ（恒久）・ρ（回復）・平方根則の凹性。",
            "最適スケジュールはどれも『速さ ↔ インパクト／リスク』トレードオフの解（AC＝平均分散、OW＝過渡コスト最小、RL＝報酬最大化）。",
            "線形2次モデル（AC・OW）は閉形式／QP、LOB・RL は確率的・数値的。RL の残差版は AC をベースラインに内包する。",
            "符号規約が統一：子注文 q_k≥0 が在庫を減らし、正のコストは到着価格より不利な執行を意味する。",
        ]
        behavior_label = "採用したときの行動："
        behaviors = {
            "ac": "リスク回避度 λ を上げるほど在庫を早く落とす（前倒し）。λ→0 では毎期同量＝TWAP（直線）。図は λ を動かした在庫軌道。",
            "impact": "回復速度 ρ が大きいほど取引後のインパクトが速く消える。ρ が小さいと変位が長く残り、後続の約定を押し下げ続ける。図は取引停止後の過渡変位の減衰。",
            "ow": "回復が遅い（ρ 小）ほど端点に大きなブロックを置き中間は薄く、速い（ρ 大）ほど均等に近づく。図は ρ 別のステップ発注量。",
            "lob": "指値は前方キューが長いほど約定しにくく、反対側フローが多いほど約定しやすい。P1-5 の厳格化はこの曲線を実質右へずらす。図は約定確率。",
            "rl": "学習が進むほど執行コストが下がる。残差RLは AC を土台に微調整、自由RLは行動グリッドを直接学習。図は学習曲線（学習時ISの移動平均＋検証点）。残差は検証が良くても独立テストで悪化しやすい（選択の楽観性）。",
        }
    else:
        vars_h, str_h, weak_h, common_h = (
            "Variables",
            "Strengths",
            "Weaknesses",
            "Commonalities across the models",
        )

        def impl(f: str) -> str:
            return f" (implementation: <code>{e(f)}</code>)"

        models = [
            {
                "key": "ac",
                "title": "Almgren–Chriss (mean–variance optimal execution)",
                "impl": "almgren_chriss.py",
                "desc": "Under linear temporary impact and known volatility, minimize a mean–variance trade-off between expected execution cost and its variance. The continuous solution is a sinh trajectory; the discrete solution is a sequence of child orders on the decision grid.",
                "vars": [
                    ("X", "initial inventory (shares)"),
                    ("T", "horizon (seconds)"),
                    ("η", "temporary-impact coefficient"),
                    ("γ", "permanent-impact coefficient"),
                    ("σ, σ_k", "volatility (σ_k per step)"),
                    ("λ", "risk aversion"),
                    ("κ", "urgency √(λσ²/η); κ→0 gives TWAP"),
                    ("q_k, x_k", "step-k child order / start-of-step inventory"),
                    ("Δt", "decision step length"),
                ],
                "strengths": [
                    "Closed-form and interpretable; the efficient frontier is immediate.",
                    "Risk aversion tunes front- vs back-loading with one parameter.",
                    "A practitioner benchmark (TWAP is the κ→0 special case).",
                ],
                "weaknesses": [
                    "Impact is fixed-linear with no endogenous book reaction.",
                    "Volatility is assumed known; transient (recovering) impact is not modeled.",
                    "A static schedule that does not adapt to observed state.",
                ],
            },
            {
                "key": "impact",
                "title": "Three impact channels + the square-root law",
                "impl": "impact.py",
                "desc": "Decompose impact into temporary (paid only while trading), permanent (a lasting mid shift), and transient (decaying via a resilience kernel). The square-root law is a concave law in total size, shown as an independent diagnostic and not added to the linear model (the exponent 1/2 is a stylized choice; Almgren et al. (2005) estimate a temporary-impact power of ≈0.6).",
                "vars": [
                    ("v", "trade rate q/Δt"),
                    ("η", "temporary coefficient"),
                    ("γ", "permanent coefficient"),
                    ("η_t", "transient coefficient"),
                    ("ρ", "resilience (recovery) rate"),
                    ("D_k", "transient displacement seen at step k"),
                    ("G(τ)", "decay kernel (exponential / power-law)"),
                    ("β, τ_0", "power-law kernel parameters"),
                    ("Q, ADV, Y, σ_d", "total size, average daily volume, scale, daily vol"),
                ],
                "strengths": [
                    "Channels are separated, so the TCA decomposition is exact.",
                    "Recovery (transient impact) is explicit via the kernel G.",
                    "The square-root law can be shown as an empirical diagnostic.",
                ],
                "weaknesses": [
                    "Parameters are synthetic, with no real-data calibration.",
                    "Linear (the square-root law is a separate, non-additive track).",
                    "Cross-impact (multi-asset) is out of scope.",
                ],
            },
            {
                "key": "ow",
                "title": "Obizhaeva–Wang (optimal execution with resilient liquidity)",
                "impl": "resilience.py",
                "desc": "Under purely transient linear impact against a block-shaped book, minimize a quadratic expected cost. Exponential resilience gives a closed-form block + constant-rate schedule; general kernels are solved as a non-negativity-constrained QP. The discrete solution is verified to converge to the closed form under grid refinement (test_resilience).",
                "vars": [
                    ("M", "kernel correlation matrix M_{kj}=G(|k−j|Δt)"),
                    ("η_t", "transient-impact coefficient"),
                    ("ρ", "resilience rate"),
                    ("X", "initial inventory"),
                    ("q", "child-order vector (Σq=X, q≥0)"),
                    ("1", "all-ones vector"),
                ],
                "strengths": [
                    "Closed form for the exponential kernel; the QP stays well-posed (M positive definite) for general kernels.",
                    "Treats transient impact explicitly as optimal control.",
                    "Resilience rate ρ directly explains execution concentration.",
                ],
                "weaknesses": [
                    "Risk-neutral (risk aversion is delegated to the AC layer).",
                    "Assumes a block-shaped book.",
                    "Single asset / single name.",
                ],
            },
            {
                "key": "lob",
                "title": "Reactive limit-order book",
                "impl": "order_book.py",
                "desc": "A state-dependent book whose market-order arrival intensity shifts with queue imbalance, recent return, and stress. Own market orders consume displayed depth and move the price; limit orders fill through a FIFO queue and face adverse selection.",
                "vars": [
                    ("Q^b, Q^a", "bid / ask depth"),
                    ("I", "queue imbalance ∈[−1,1]"),
                    (
                        "λ, λ_0",
                        "market-order arrival intensity / base intensity (saturated by a cap)",
                    ),
                    ("g", "tilt (log-linear slope of intensity)"),
                    ("β_0..β_3", "intercept, imbalance, return, stress coefficients"),
                    ("α_k", "latent short-horizon alpha (AR(1))"),
                    ("φ, σ_α, Z_k", "persistence, shock scale, standard normal"),
                ],
                "strengths": [
                    "Captures endogenous book reaction, fill probability, adverse selection, and self-impact.",
                    "Makes market-order walking and spread widening explicit.",
                    "Reproduces the adverse-selection channel via latent alpha.",
                ],
                "weaknesses": [
                    "A single-level approximation; queue position and adverse selection are proxies.",
                    "Not calibrated to real order-level data.",
                    "No latency, venue fragmentation, or manipulation rules.",
                ],
            },
            {
                "key": "rl",
                "title": "Reinforcement-learning policy (PPO + GAE, residual / free)",
                "impl": "rl_training.py, environment.py",
                "desc": "Optimize a map from state (inventory, time remaining, book features) to child orders with PPO. The residual variant learns adjustments around an Almgren–Chriss baseline, and a shared safety layer prevents over-execution. Training uses shaped rewards; evaluation uses economic IS.",
                "vars": [
                    ("w_t", "probability ratio π_θ/π_old"),
                    ("Â_t", "GAE advantage"),
                    ("δ_t", "TD error"),
                    ("V", "value function"),
                    ("r_t", "(shaped) reward"),
                    ("γ, λ", "discount / GAE coefficients"),
                    ("ε", "clip width"),
                    ("a_t^AC", "AC baseline action (residual variant)"),
                ],
                "strengths": [
                    "Adapts to book dynamics; model-free.",
                    "The safety layer constrains child orders, participation, and price.",
                    "The residual variant embeds AC, stabilizing training.",
                ],
                "weaknesses": [
                    "Depends strongly on reward design, training budget, and seed.",
                    "Simulator-bound; not real-market causality.",
                    "Not interpretable; the quick profile has one seed, so any edge is descriptive.",
                ],
            },
        ]
        commons = [
            "All models are evaluated on shared state variables (inventory x, time remaining, price) and a shared metric (implementation shortfall IS, bps).",
            "Impact shares one structure across models — it grows with trade speed and size and (partly) recovers over time: η (instantaneous), γ (permanent), ρ (recovery), and the concavity of the square-root law.",
            "Every optimal schedule solves the same speed ↔ impact/risk trade-off (AC = mean–variance, OW = minimum transient cost, RL = reward maximization).",
            "Linear-quadratic models (AC, OW) are closed-form/QP; LOB and RL are stochastic/numerical. The RL residual variant embeds AC as its baseline.",
            "One sign convention throughout: a child order q_k≥0 reduces inventory, and a positive cost means execution worse than the arrival price.",
        ]
        behavior_label = "Behavior when adopted:"
        behaviors = {
            "ac": "Raising risk aversion λ front-loads selling; λ→0 gives equal slices each period (TWAP, a straight line). The chart sweeps λ over the inventory path.",
            "impact": "Larger resilience ρ makes post-trade impact fade faster; small ρ leaves displacement lingering and keeps pushing later fills. The chart shows transient decay after trading stops.",
            "ow": "Slower resilience (small ρ) places large blocks at the endpoints with a thin interior; faster ρ approaches an even schedule. The chart shows per-step size by ρ.",
            "lob": "A limit order fills less readily as the queue ahead grows and more readily as opposite flow rises; the P1-5 stricter regime effectively shifts this curve right. The chart shows fill probability.",
            "rl": "Cost falls as training proceeds; residual RL fine-tunes around AC, free RL learns the action grid directly. The chart shows learning curves (training-IS moving average plus validation points). Residual can look good on validation yet degrade on the independent test (selection optimism).",
        }

    parts: list[str] = []
    for m in models:
        parts.append(f"<h3>{e(m['title'])}</h3>")
        parts.append(f"<p>{e(m['desc'])} {impl(m['impl'])}</p>")
        parts.append(eqs(*eq[m["key"]]))
        v_items = "".join(f"<li><code>{e(sym)}</code> — {e(mean)}</li>" for sym, mean in m["vars"])
        parts.append(f'<p><strong>{e(vars_h)}</strong></p><ul class="mvars">{v_items}</ul>')
        s_items = "".join(f"<li>{e(x)}</li>" for x in m["strengths"])
        w_items = "".join(f"<li>{e(x)}</li>" for x in m["weaknesses"])
        parts.append(
            f'<div class="swrap"><div><p><strong>{e(str_h)}</strong></p><ul>{s_items}</ul></div>'
            f"<div><p><strong>{e(weak_h)}</strong></p><ul>{w_items}</ul></div></div>"
        )
        behavior = behaviors.get(m["key"])
        if behavior:
            parts.append(f"<p><strong>{e(behavior_label)}</strong> {e(behavior)}</p>")
        chart = charts.get(f"mt_{m['key']}")
        if chart:
            parts.append(f'<div class="chart">{chart}</div>')
    c_items = "".join(f"<li>{e(x)}</li>" for x in commons)
    parts.append(f"<h3>{e(common_h)}</h3><ul>{c_items}</ul>")
    return "".join(parts)


def _n_scenarios(frame: pd.DataFrame) -> int:
    if "n_paths" in frame.columns and len(frame):
        return int(frame["n_paths"].iloc[0])
    return 0


def _val_selection_html(cfg: Config, t: Translator, in_dist: pd.DataFrame) -> str:
    """Validation (selection) vs independent test IS per RL policy (P1-7).

    Best checkpoints are chosen on the disjoint validation stream and reported
    on the test stream; the gap exposes selection optimism. Only the main
    policies are shown (ablation/reference runs are filtered out by run_id).
    """
    summary_path = artifact_dirs(cfg)["metrics"] / "rl_training_summary.json"
    if not summary_path.exists():
        return ""
    runs = json.loads(summary_path.read_text(encoding="utf-8")).get("runs", [])
    test_by_id = dict(zip(in_dist["strategy_id"], in_dist["is_mean_bps"], strict=False))
    rows = []
    for r in runs:
        variant, seed = r.get("variant"), r.get("seed")
        if variant not in ("residual", "free") or seed is None:
            continue
        if r.get("run_id") != f"{variant}_{cfg.profile}_s{int(seed)}":
            continue  # skip ablation and full-feature reference runs
        val = r.get("val_is_bps")
        sid = f"rl_{variant}_s{int(seed)}"
        test = test_by_id.get(sid)
        if val is None or test is None or not np.isfinite(float(val)):
            continue
        gap = float(test) - float(val)
        rows.append(
            f"<li>{html.escape(_strategy_name(t, sid))}: "
            f"{html.escape(t('val_label'))} {float(val):.3f} → "
            f"{html.escape(t('test_label'))} {float(test):.3f} bps "
            f"({html.escape(t('gap_label'))} {gap:+.3f})</li>"
        )
    if not rows:
        return ""
    return f"<p>{html.escape(t('val_selection_note'))}</p><ul>{''.join(rows)}</ul>"


def _model_theory_figures(cfg: Config, t: Translator) -> dict[str, go.Figure]:
    """One parameter-sweep chart per model, computed analytically from the
    model code so each figure shows how a single knob reshapes the strategy or
    response (deterministic, offline)."""
    from .almgren_chriss import ac_inventory, kappa_for_lambda
    from .fills import passive_fill_probability
    from .impact import transient_decay_curve
    from .resilience import ow_closed_form

    locale = t.locale
    figs: dict[str, go.Figure] = {}
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    dt = T / N
    t_grid = np.linspace(0.0, T, N + 1)

    # Almgren–Chriss: risk-aversion (lambda) sweep of the inventory path.
    fig = go.Figure()
    for i, lam in enumerate((1e-8, 1e-6, 1e-5, 1e-4)):
        kappa = kappa_for_lambda(cfg, lam)
        inv = ac_inventory(X, T, kappa, N)
        fig.add_trace(
            go.Scatter(
                x=t_grid,
                y=inv / X,
                mode="lines",
                line={"color": COLORS[i % len(COLORS)], "width": 2},
                name=f"λ={lam:.0e} (κT={kappa * T:.2f})",
            )
        )
    _base_layout(
        fig,
        _axis(
            locale, "Almgren–Chriss: risk-aversion sweep", "Almgren–Chriss：リスク回避度スイープ"
        ),
    )
    fig.update_xaxes(title=_axis(locale, "Time (seconds)", "時刻（秒）"))
    fig.update_yaxes(title=_axis(locale, "Inventory / initial", "在庫／初期在庫"), range=[0, 1.02])
    figs["mt_ac"] = fig

    # Impact channels: resilience (rho) sweep of transient recovery.
    fig = go.Figure()
    for i, rho in enumerate((0.002, 0.01, 0.05)):
        curve = transient_decay_curve(1.0, rho, dt, N)
        fig.add_trace(
            go.Scatter(
                x=np.arange(N + 1) * dt,
                y=curve,
                mode="lines",
                line={"color": COLORS[i], "width": 2},
                name=f"ρ={rho:g}",
            )
        )
    _base_layout(
        fig,
        _axis(locale, "Transient impact: resilience sweep", "過渡的インパクト：回復速度スイープ"),
    )
    fig.update_xaxes(title=_axis(locale, "Time after trading stops (s)", "取引停止後の時間（秒）"))
    fig.update_yaxes(title=_axis(locale, "Displacement (normalized)", "変位（正規化）"))
    figs["mt_impact"] = fig

    # Obizhaeva–Wang: resilience (rho) sweep of the closed-form schedule shape.
    fig = go.Figure()
    for i, rho in enumerate((0.002, 0.01, 0.05)):
        q = ow_closed_form(X, T, rho, N)
        fig.add_trace(
            go.Scatter(
                x=np.arange(N) * dt,
                y=q / X,
                mode="lines+markers",
                line={"color": COLORS[i], "width": 2},
                marker={"size": 4},
                name=f"ρ={rho:g}",
            )
        )
    _base_layout(
        fig,
        _axis(
            locale,
            "Obizhaeva–Wang: schedule vs resilience",
            "Obizhaeva–Wang：回復速度と発注スケジュール",
        ),
    )
    fig.update_xaxes(title=_axis(locale, "Time (seconds)", "時刻（秒）"))
    fig.update_yaxes(
        title=_axis(locale, "Shares traded / initial (per step)", "ステップ別発注量／初期在庫")
    )
    figs["mt_ow"] = fig

    # Reactive LOB: passive fill probability vs queue-ahead, opposite-flow sweep.
    fig = go.Figure()
    queue = np.linspace(0.0, 8000.0, 41)
    order_qty = X / N
    mean_size = cfg.lob.market_order_size_mean
    base = cfg.mo_rate_per_side
    for i, mult in enumerate((0.5, 1.0, 2.0)):
        rate = base * mult
        p = [passive_fill_probability(qa, order_qty, rate, mean_size, dt) for qa in queue]
        fig.add_trace(
            go.Scatter(
                x=queue,
                y=p,
                mode="lines",
                line={"color": COLORS[i], "width": 2},
                name=_axis(locale, f"flow ×{mult:g}", f"フロー ×{mult:g}"),
            )
        )
    _base_layout(
        fig, _axis(locale, "Reactive LOB: passive fill probability", "反応型板：指値の約定確率")
    )
    fig.update_xaxes(title=_axis(locale, "Queue ahead (shares)", "前方キュー（株）"))
    fig.update_yaxes(
        title=_axis(locale, "Fill probability over one step", "1ステップの約定確率"),
        range=[0, 1.02],
    )
    figs["mt_lob"] = fig

    # RL: learning curves (training-IS moving average + validation points).
    hist_path = artifact_dirs(cfg)["metrics"] / "rl_training_history.csv"
    if hist_path.exists():
        hist = pd.read_csv(hist_path)
        seed = int(cfg.rl.seeds[0])
        fig = go.Figure()
        drew = False
        for i, (variant, label_en, label_ja) in enumerate(
            (("residual", "Residual RL", "残差RL"), ("free", "Free RL", "自由RL"))
        ):
            sub = hist[hist["run_id"] == f"{variant}_{cfg.profile}_s{seed}"].sort_values("episodes")
            if sub.empty:
                continue
            drew = True
            fig.add_trace(
                go.Scatter(
                    x=sub["episodes"],
                    y=sub["train_is_ma_bps"],
                    mode="lines",
                    line={"color": COLORS[i], "width": 2},
                    name=_axis(locale, label_en, label_ja),
                )
            )
            val = sub.dropna(subset=["val_is_bps"])
            if not val.empty:
                fig.add_trace(
                    go.Scatter(
                        x=val["episodes"],
                        y=val["val_is_bps"],
                        mode="markers",
                        marker={"color": COLORS[i], "size": 7, "symbol": "diamond"},
                        name=_axis(locale, f"{label_en} val", f"{label_ja} 検証"),
                    )
                )
        if drew:
            _base_layout(fig, _axis(locale, "RL: learning curves", "RL：学習曲線"))
            fig.update_xaxes(title=_axis(locale, "Training episodes", "学習エピソード"))
            fig.update_yaxes(
                title=_axis(locale, "Implementation shortfall (bps)", "実装ショートフォール（bps）")
            )
            figs["mt_rl"] = fig
    return figs


def build_report(cfg: Config, locale: str) -> Path:
    validate_locales()
    t = Translator(locale)
    frames = _artifact_frames(cfg)
    # Model-theory sweeps come first so the inline Plotly bundle attaches to the
    # earliest chart in the DOM (the model-theory section precedes the results).
    figures = {**_model_theory_figures(cfg, t), **_charts(frames, t)}
    chart_html = _fig_html(figures)
    findings = _findings(cfg, frames, t)
    quantitative = _quantitative_payload(frames)

    classical_best = frames["classical"].loc[frames["classical"]["is_mean_bps"].idxmin()]
    lob_best = frames["lob"].loc[frames["lob"]["is_mean_bps"].idxmin()]
    in_dist = frames["stress"][frames["stress"]["regime"] == "in_distribution"]
    rl_only = in_dist[in_dist["strategy_id"].str.startswith("rl_")]
    rl_best = rl_only.loc[rl_only["is_mean_bps"].idxmin()] if not rl_only.empty else None
    hero = [
        (
            t("table.classical"),
            _strategy_name(t, str(classical_best["strategy_id"])),
            f"{classical_best['is_mean_bps']:.3f} bps",
        ),
        (
            t("table.lob"),
            _strategy_name(t, str(lob_best["strategy_id"])),
            f"{lob_best['is_mean_bps']:.3f} bps",
        ),
    ]
    if rl_best is not None:
        hero.append(
            (
                t("table.rl"),
                _strategy_name(t, str(rl_best["strategy_id"])),
                f"{rl_best['is_mean_bps']:.3f} bps",
            )
        )
    hero_html = "".join(
        f'<div class="tile"><div class="label">{html.escape(label)}</div><div class="value">{html.escape(value)}</div><div>{html.escape(detail)}</div></div>'
        for label, value, detail in hero
    )

    translations = {key.replace(".", "_"): value for key, value in t.messages.items()}
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"]))
    template = env.from_string(_TEMPLATE)
    stamp = generated_at()
    rendered = template.render(
        locale=locale,
        version="0.1.0",
        profile=cfg.profile,
        seed=cfg.seed,
        git_commit=git_commit() or "uncommitted",
        generated_at=stamp,
        title=t("report_title"),
        subtitle=t("report_subtitle"),
        profile_note=t(
            "profile_note_template",
            profile=cfg.profile,
            seed=cfg.seed,
            horizon=cfg.horizon_seconds,
            inventory=cfg.initial_inventory,
            price=cfg.arrival_price,
        ),
        tr=translations,
        charts=chart_html,
        tables={
            "classical": _table(
                frames["classical"], t, t("cap_classical", n=_n_scenarios(frames["classical"]))
            ),
            "lob": _table(frames["lob"], t, t("cap_lob", n=_n_scenarios(frames["lob"]))),
            "rl": _table(in_dist, t, t("cap_rl", n=_n_scenarios(in_dist))),
            "misspecification": _table(
                frames["misspecification"],
                t,
                t("cap_misspecification", n=_n_scenarios(frames["misspecification"])),
            ),
        },
        hero_tiles=hero_html,
        related_work=_related_work_html(t),
        model_theory=_model_theory_html(t, chart_html),
        val_selection=_val_selection_html(cfg, t, in_dist),
        fingerprint_short=quantitative["sha256"][:12],
        seed_warning=len(cfg.rl.seeds) == 1,
        reactive_finding=findings["reactive"],
        shift_finding=findings["shift"],
        conclusion=findings["conclusion"],
        fingerprint_json=json.dumps(quantitative, ensure_ascii=False, sort_keys=True),
        provenance_json=json.dumps(
            {
                "seed": cfg.seed,
                "profile": cfg.profile,
                "generated_at": stamp,
                "git_commit": git_commit(),
                "model_parameters": cfg.raw,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    # Plotly's inline bundle contains dormant map/tile defaults even though
    # this report has no geographic traces.  Neutralise those fallbacks so a
    # strict offline scan finds no callable CDN endpoint.
    rendered = rendered.replace("https://cdn.plot.ly/un/", "data:,")
    rendered = rendered.replace("https://basemaps.cartocdn.com", "data:")
    rendered = rendered.replace("https://tiles.basemaps.cartocdn.com", "data:")
    out = artifact_dirs(cfg)["reports"] / f"optimal_execution_report_{locale}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    _validate_report(out, t("report_title"), quantitative["sha256"])
    return out


def _validate_report(path: Path, expected_title: str, fingerprint: str) -> None:
    text = path.read_text(encoding="utf-8")
    if path.stat().st_size < 100_000:
        raise ValueError(f"standalone report unexpectedly small: {path}")
    if expected_title not in text:
        raise ValueError(f"missing localized title in {path}")
    if fingerprint not in text:
        raise ValueError(f"missing quantitative fingerprint in {path}")
    forbidden = ("cdn.plot.ly", "https://cdn", "http://cdn")
    if any(token in text for token in forbidden):
        raise ValueError(f"external CDN reference found in {path}")


def build_reports(cfg: Config) -> dict[str, Path]:
    outputs = {locale: build_report(cfg, locale) for locale in ("en", "ja")}
    en_text = outputs["en"].read_text(encoding="utf-8")
    ja_text = outputs["ja"].read_text(encoding="utf-8")
    marker = '"sha256": "'
    en_hash = en_text.split(marker, 1)[1].split('"', 1)[0]
    ja_hash = ja_text.split(marker, 1)[1].split('"', 1)[0]
    if en_hash != ja_hash:
        raise ValueError("English/Japanese reports have different quantitative fingerprints")
    write_json(
        artifact_dirs(cfg)["metrics"] / "bilingual_report_check.json",
        {
            "seed": cfg.seed,
            "profile": cfg.profile,
            "generated_at": generated_at(),
            "git_commit": git_commit(),
            "model_parameters": cfg.raw,
            "quantitative_fingerprint": en_hash,
            "reports": {locale: str(path) for locale, path in outputs.items()},
        },
    )
    return outputs
