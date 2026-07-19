"""Polished offline Plotly report with JavaScript embedded exactly once."""

from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import ProjectConfig
from .plotting import COLORS, LABELS
from .training import checkpoint_directory

LABELS_JA = {
    "neural_mse": "ニューラルヘッジ（MSE）",
    "black_scholes_delta": "Black–Scholesデルタ",
    "black_scholes_band": "Black–Scholesバンド",
    "no_hedge": "ヘッジなし",
}


def _style_figure(figure: go.Figure, title: str, subtitle: str = "") -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        title={"text": f"{title}<br><sup>{subtitle}</sup>" if subtitle else title, "x": 0.01},
        font={"family": "system-ui, -apple-system, Segoe UI, sans-serif", "color": "#111827"},
        margin={"l": 65, "r": 35, "t": 80, "b": 55},
        legend={"orientation": "h", "y": 1.02, "x": 0},
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=470,
    )
    figure.update_xaxes(gridcolor="#E5E7EB")
    figure.update_yaxes(gridcolor="#E5E7EB")
    return figure


def _distribution(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    strategies = list(frame["strategy"].drop_duplicates())
    for strategy in strategies:
        values = frame.loc[frame["strategy"] == strategy, "discounted_pnl"]
        figure.add_trace(
            go.Histogram(
                x=values,
                histnorm="probability density",
                name=LABELS.get(strategy, strategy),
                marker_color=COLORS.get(strategy, "#6B7280"),
                opacity=0.55,
                nbinsx=100,
            )
        )
    buttons = [
        {
            "label": "All strategies",
            "method": "update",
            "args": [{"visible": [True] * len(strategies)}],
        }
    ]
    buttons.extend(
        {
            "label": LABELS.get(strategy, strategy),
            "method": "update",
            "args": [{"visible": [candidate == strategy for candidate in strategies]}],
        }
        for strategy in strategies
    )
    figure.update_layout(
        barmode="overlay",
        updatemenus=[
            {"buttons": buttons, "direction": "down", "x": 1.0, "xanchor": "right", "y": 1.2}
        ],
    )
    figure.update_xaxes(title="Discounted P&L after costs, including premium")
    figure.update_yaxes(title="Density")
    return _style_figure(
        figure,
        "Economic P&L distribution",
        "Common out-of-sample paths; selector changes visible strategies",
    )


def _ecdf(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for strategy, group in frame.groupby("strategy", sort=False):
        values = np.sort(group["discounted_pnl"].to_numpy())
        probabilities = np.arange(1, len(values) + 1) / len(values)
        figure.add_trace(
            go.Scatter(
                x=values,
                y=probabilities,
                mode="lines",
                name=LABELS.get(strategy, strategy),
                line={"color": COLORS.get(strategy)},
            )
        )
    tail_lower = float(frame["discounted_pnl"].quantile(0.001))
    tail_upper = float(frame["discounted_pnl"].quantile(0.25))
    full_lower, full_upper = frame["discounted_pnl"].quantile([0.001, 0.999])
    figure.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Tail zoom",
                        "method": "relayout",
                        "args": [
                            {"xaxis.range": [tail_lower, tail_upper], "yaxis.range": [0, 0.25]}
                        ],
                    },
                    {
                        "label": "Full range",
                        "method": "relayout",
                        "args": [
                            {
                                "xaxis.range": [float(full_lower), float(full_upper)],
                                "yaxis.range": [0, 1],
                            }
                        ],
                    },
                ],
                "x": 1.0,
                "xanchor": "right",
                "y": 1.2,
            }
        ]
    )
    figure.update_xaxes(
        title="Discounted P&L after costs, including premium", range=[tail_lower, tail_upper]
    )
    figure.update_yaxes(title="Cumulative probability", range=[0, 0.25])
    return _style_figure(
        figure,
        "Empirical CDF with tail zoom",
        "Lower values are worse for the short-option position",
    )


def _tail_bar(summary: pd.DataFrame) -> go.Figure:
    names = list(summary.index)
    figure = go.Figure(
        [
            go.Bar(
                x=[LABELS.get(name, name) for name in names],
                y=summary["var_loss_99"],
                name="99% VaR",
                marker_color="#93C5FD",
            ),
            go.Bar(
                x=[LABELS.get(name, name) for name in names],
                y=summary["cvar_loss_99"],
                name="99% CVaR",
                marker_color="#2563EB",
            ),
        ]
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(title="Discounted economic loss")
    return _style_figure(
        figure, "99% tail loss", "VaR is the loss quantile; CVaR is mean loss beyond the quantile"
    )


def _sensitivity(sensitivity: pd.DataFrame) -> go.Figure:
    figure = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("P&L standard deviation", "99% CVaR loss", "Turnover", "Transaction cost"),
    )
    specs = [
        ("std_discounted_pnl_after_costs_including_premium", 1, 1),
        ("cvar_loss_99", 1, 2),
        ("average_turnover_shares", 2, 1),
        ("average_discounted_transaction_cost", 2, 2),
    ]
    for column, row, col in specs:
        figure.add_trace(
            go.Scatter(
                x=sensitivity["transaction_cost_bps"],
                y=sensitivity[column],
                mode="lines+markers",
                marker={"color": "#2563EB"},
                line={"color": "#2563EB"},
                showlegend=False,
            ),
            row=row,
            col=col,
        )
    figure.update_xaxes(title="Cost (bp)", row=2, col=1)
    figure.update_xaxes(title="Cost (bp)", row=2, col=2)
    figure.update_layout(height=650)
    return _style_figure(
        figure,
        "Transaction-cost sensitivity",
        "Each point is a separately trained neural policy evaluated on common paths",
    )


def _policy_heatmap(surface: pd.DataFrame, difference: bool = False) -> go.Figure:
    value = "difference" if difference else "neural_delta"
    pivot = surface.pivot(index="tau_normalized", columns="spot", values=value).sort_index()
    figure = go.Figure(
        go.Heatmap(
            x=pivot.columns,
            y=pivot.index,
            z=pivot.to_numpy(),
            colorscale="RdBu" if difference else "Viridis",
            zmid=0 if difference else None,
            colorbar={"title": "Δ difference" if difference else "Stock position"},
        )
    )
    figure.update_xaxes(title="Spot")
    figure.update_yaxes(title="Normalized time to maturity")
    title = "Neural minus Black–Scholes delta" if difference else "Neural hedge policy surface"
    return _style_figure(
        figure,
        title,
        "Previous position fixed at 0.5 shares; volatility 20%; transaction cost 5 bp",
    )


def _training_history(history: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    train = history.dropna(subset=["train_objective"])
    figure.add_trace(
        go.Scatter(
            x=train["epoch"], y=train["train_objective"], name="Training", line={"color": "#2563EB"}
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history["epoch"],
            y=history["validation_objective"],
            name="Validation",
            line={"color": "#D97706"},
        )
    )
    figure.update_xaxes(title="Epoch")
    figure.update_yaxes(title="MSE objective")
    return _style_figure(
        figure, "Training history", "Fresh training paths per update and one fixed validation set"
    )


def _risk_objectives(risk: pd.DataFrame) -> go.Figure:
    metrics = [
        ("std_discounted_pnl_after_costs_including_premium", "P&L std"),
        ("cvar_loss_99", "99% CVaR loss"),
        ("average_turnover_shares", "Turnover"),
    ]
    indexed = risk.set_index("objective")
    figure = go.Figure()
    for objective in indexed.index:
        ratios = [
            float(indexed.loc[objective, column] / indexed.loc["mse", column])
            for column, _ in metrics
        ]
        figure.add_trace(
            go.Bar(
                x=[label for _, label in metrics],
                y=ratios,
                name=objective,
                marker_color="#2563EB" if objective == "mse" else "#BE185D",
            )
        )
    figure.add_hline(y=1, line_dash="dash", line_color="#111827")
    figure.update_layout(barmode="group")
    figure.update_yaxes(title="Ratio to MSE")
    return _style_figure(
        figure,
        "Risk-objective comparison",
        "Same market, transaction cost and test paths; values normalized to the MSE policy",
    )


def _figure_html(figure: go.Figure, *, include_js: bool) -> str:
    return figure.to_html(
        full_html=False,
        include_plotlyjs="inline" if include_js else False,
        config={"responsive": True, "displaylogo": False},
    )


def _metrics_table(summary: pd.DataFrame, language: str = "en") -> str:
    columns = [
        "mean_discounted_pnl_after_costs_including_premium",
        "std_discounted_pnl_after_costs_including_premium",
        "rmse_discounted_hedging_error",
        "cvar_loss_99",
        "average_turnover_shares",
        "average_discounted_transaction_cost",
    ]
    if language == "ja":
        names = ["平均P&L", "P&L標準偏差", "RMSE", "99% CVaR損失", "売買回転量", "取引コスト"]
        labels = LABELS_JA
    else:
        names = ["Mean P&L", "P&L std", "RMSE", "99% CVaR loss", "Turnover", "Transaction cost"]
        labels = LABELS
    table = summary[columns].copy()
    table.columns = names
    table.index = [labels.get(str(index), str(index)) for index in table.index]
    return table.to_html(
        float_format=lambda value: f"{value:.4f}", classes="metrics-table", border=0
    )


MODEL_ROWS = [
    (
        "neural_mse",
        "Neural hedge (MSE)",
        "ニューラルヘッジ（MSE）",
        "Shared MLP policy trained end to end to minimize expected squared discounted hedging error.",
        "共有MLP方策を、割引ヘッジ誤差の二乗平均を最小化するようエンドツーエンドで学習。",
    ),
    (
        "neural_entropic",
        "Neural hedge (entropic)",
        "ニューラルヘッジ（エントロピック）",
        "Same architecture retrained with an entropic risk objective that penalizes tail losses more than MSE.",
        "同一アーキテクチャを、MSEよりテール損失を強く罰するエントロピック・リスク目的で再学習。",
    ),
    (
        "black_scholes_delta",
        "Black–Scholes delta",
        "Black–Scholesデルタ",
        "Analytic Black–Scholes delta, rebalanced at every hedge date without regard to transaction cost.",
        "Black–Scholes公式の解析的デルタを、取引コストを考慮せず毎ヘッジ時点で再調整。",
    ),
    (
        "black_scholes_band",
        "Black–Scholes band",
        "Black–Scholesバンド",
        "Black–Scholes delta with a fixed no-trade band, a classical heuristic for reducing turnover under cost.",
        "Black–Scholesデルタに固定の不感帯を設けた、コスト下で回転量を抑える古典的ヒューリスティック。",
    ),
    (
        "no_hedge",
        "No hedge",
        "ヘッジなし",
        "Zero stock position throughout; the naive baseline.",
        "全期間ゼロポジションの素朴なベースライン。",
    ),
]


def _models_table(config: ProjectConfig, language: str) -> str:
    rows = [
        row for row in MODEL_ROWS if row[0] != "neural_entropic" or config.experiment.run_entropic
    ]
    name_idx, desc_idx = (1, 3) if language == "en" else (2, 4)
    header = ("Model", "What it optimizes") if language == "en" else ("モデル", "最適化対象")
    body = "".join(
        f"<tr><td>{html.escape(row[name_idx])}</td><td>{html.escape(row[desc_idx])}</td></tr>"
        for row in rows
    )
    return f"<table class='metrics-table'><thead><tr><th>{header[0]}</th><th>{header[1]}</th></tr></thead><tbody>{body}</tbody></table>"


def _parameter_rows(config: ProjectConfig) -> list[tuple[str, str, str, str]]:
    market, policy, risk, training, experiment = (
        config.market,
        config.policy,
        config.risk,
        config.training,
        config.experiment,
    )
    architecture_en = (
        f"{policy.hidden_layers} hidden layers × {policy.hidden_units} units, {policy.activation}"
        + (" + LayerNorm" if policy.layer_norm else "")
    )
    architecture_ja = (
        f"隠れ層{policy.hidden_layers}層 × {policy.hidden_units}ユニット、{policy.activation}"
        + ("＋LayerNorm" if policy.layer_norm else "")
    )
    objective_en = f"{risk.objective}" + (
        f" / entropic (γ={risk.entropic_gamma:g})" if experiment.run_entropic else ""
    )
    objective_ja = f"{risk.objective}" + (
        f" / entropic（γ={risk.entropic_gamma:g}）" if experiment.run_entropic else ""
    )
    return [
        (
            "Spot / strike",
            "スポット / 権利行使価格",
            f"{market.s0:.2f} / {market.strike:.2f}",
            f"{market.s0:.2f} / {market.strike:.2f}",
        ),
        (
            "Maturity / hedge dates",
            "満期 / ヘッジ時点数",
            f"{market.maturity_years:.3f}y, {market.n_steps} steps",
            f"{market.maturity_years:.3f}年、{market.n_steps}時点",
        ),
        (
            "Volatility (σ) / drift (μ)",
            "ボラティリティ（σ）/ ドリフト（μ）",
            f"{market.volatility:.0%} / {market.mu:.1%}",
            f"{market.volatility:.0%} / {market.mu:.1%}",
        ),
        (
            "Risk-free rate (r)",
            "無リスク金利（r）",
            f"{market.risk_free_rate:.1%}",
            f"{market.risk_free_rate:.1%}",
        ),
        (
            "Transaction cost (this run)",
            "取引コスト（本実行）",
            f"{market.transaction_cost_bps:.1f} bp",
            f"{market.transaction_cost_bps:.1f} bp",
        ),
        (
            "No-trade band (BS-band baseline)",
            "不感帯幅（BSバンド方策）",
            f"±{experiment.no_trade_band:.0%} of target delta",
            f"目標デルタの±{experiment.no_trade_band:.0%}",
        ),
        ("Policy network", "方策ネットワーク", architecture_en, architecture_ja),
        (
            "Position bounds",
            "ポジション上下限",
            f"[{policy.action_min:.2f}, {policy.action_max:.2f}] × short qty ({market.short_quantity:g} sh)",
            f"[{policy.action_min:.2f}, {policy.action_max:.2f}] × 売建数量（{market.short_quantity:g}株）",
        ),
        ("Risk objective (main / alt.)", "リスク目的（主 / 代替）", objective_en, objective_ja),
        (
            "Training",
            "学習",
            f"{training.epochs} epochs, batch {training.batch_size}, lr {training.learning_rate:g}",
            f"{training.epochs}エポック、バッチ{training.batch_size}、学習率{training.learning_rate:g}",
        ),
        (
            "Evaluation paths (val / test)",
            "評価経路数（検証 / テスト）",
            f"{training.validation_paths:,} / {training.test_paths:,}",
            f"{training.validation_paths:,} / {training.test_paths:,}",
        ),
    ]


def _parameters_table(config: ProjectConfig, language: str) -> str:
    label_idx, value_idx = (0, 2) if language == "en" else (1, 3)
    header = ("Parameter", "Value") if language == "en" else ("パラメータ", "値")
    rows = "".join(
        f"<tr><td>{html.escape(row[label_idx])}</td><td>{html.escape(row[value_idx])}</td></tr>"
        for row in _parameter_rows(config)
    )
    return f"<table class='metrics-table'><thead><tr><th>{header[0]}</th><th>{header[1]}</th></tr></thead><tbody>{rows}</tbody></table>"


def _tradeoff_rows(neural: pd.Series, bs: pd.Series) -> list[tuple[str, str, str, str, str, str]]:
    return [
        (
            "Cost awareness",
            "コスト適応",
            "Learned directly from transaction cost in the training loss",
            "学習損失に取引コストを組み込み学習で獲得",
            "None by construction (the band variant adds a fixed heuristic)",
            "構造上は考慮なし（バンド版は固定の不感帯で代替）",
        ),
        (
            "Risk target",
            "リスク目的",
            "Configurable: MSE, entropic, or CVaR",
            "設定可能：MSE、エントロピック、CVaR",
            "Delta-neutral only",
            "デルタニュートラルのみ",
        ),
        (
            "Interpretability",
            "解釈可能性",
            "Black-box MLP; needs empirical checks (policy surface, sanity checks)",
            "ブラックボックスなMLP。方策面や健全性チェック等の実証的検証が必要",
            "Closed-form formula, fully auditable",
            "解析的公式で完全に監査可能",
        ),
        (
            "Data & compute",
            "データ・計算コスト",
            "Needs a simulator/data and a training run per configuration",
            "設定ごとにシミュレータ・データと学習実行が必要",
            "None; evaluate the formula",
            "不要。公式を評価するのみ",
        ),
        (
            "Governance",
            "ガバナンス",
            "Requires model risk management: validation, monitoring, retraining policy",
            "モデルリスク管理（検証・監視・再学習方針）が必要",
            "Standard, well-understood governance",
            "標準的で確立されたガバナンス",
        ),
        (
            "This run's result",
            "本実行の実測値",
            f"99% CVaR loss {neural['cvar_loss_99']:.3f}, turnover {neural['average_turnover_shares']:.3f} sh/path",
            f"99% CVaR損失 {neural['cvar_loss_99']:.3f}、回転量 {neural['average_turnover_shares']:.3f} 株/経路",
            f"99% CVaR loss {bs['cvar_loss_99']:.3f}, turnover {bs['average_turnover_shares']:.3f} sh/path",
            f"99% CVaR損失 {bs['cvar_loss_99']:.3f}、回転量 {bs['average_turnover_shares']:.3f} 株/経路",
        ),
    ]


def _tradeoffs_table(neural: pd.Series, bs: pd.Series, language: str) -> str:
    aspect_idx, neural_idx, bs_idx = (0, 2, 4) if language == "en" else (1, 3, 5)
    header = (
        ("Aspect", "Neural hedge", "Black–Scholes delta")
        if language == "en"
        else ("側面", "ニューラルヘッジ", "Black–Scholesデルタ")
    )
    body = "".join(
        f"<tr><td>{html.escape(row[aspect_idx])}</td><td>{html.escape(row[neural_idx])}</td><td>{html.escape(row[bs_idx])}</td></tr>"
        for row in _tradeoff_rows(neural, bs)
    )
    return (
        f"<table class='metrics-table'><thead><tr><th>{header[0]}</th><th>{header[1]}</th><th>{header[2]}</th></tr>"
        f"</thead><tbody>{body}</tbody></table>"
    )


def build_standalone_report(
    config: ProjectConfig,
    project_root: str | Path,
    manifest: dict[str, Path],
    *,
    output_path: str | Path | None = None,
) -> Path:
    """Build the requested self-contained interactive technical report."""
    root = Path(project_root)
    output = (
        Path(output_path)
        if output_path
        else root / config.output.reports_dir / "deep_hedging_report.html"
    )
    frame = pd.read_csv(manifest["main_path_results"])
    summary = pd.read_csv(manifest["strategy_summary"], index_col=0)
    sensitivity = pd.read_csv(manifest["sensitivity_summary"])
    risk = pd.read_csv(manifest["risk_objective_summary"])
    surface = pd.read_csv(manifest["policy_surface"])
    sanity = json.loads(manifest["sanity_checks"].read_text(encoding="utf-8"))
    history = pd.read_csv(
        checkpoint_directory(config.with_risk(objective="mse"), root) / "history.csv"
    )
    neural = summary.loc["neural_mse"]
    bs = summary.loc["black_scholes_delta"]
    no_hedge = summary.loc["no_hedge"]
    dispersion_reduction = (
        1
        - neural["std_discounted_pnl_after_costs_including_premium"]
        / no_hedge["std_discounted_pnl_after_costs_including_premium"]
    )
    summary_sentences_en = [
        f"The quick run used {config.training.test_paths:,} common out-of-sample paths. The neural hedge reduced P&L dispersion by {dispersion_reduction:.1%} versus no hedge.",
        f"At 5 bp, neural 99% CVaR loss was {neural['cvar_loss_99']:.3f}, versus {bs['cvar_loss_99']:.3f} for discrete Black–Scholes delta.",
        "Sanity checks are reported as observed outcomes; failed checks remain visible and do not trigger unsupported superiority claims.",
    ]
    summary_sentences_ja = [
        f"quick実行では、共通のアウト・オブ・サンプル経路を{config.training.test_paths:,}本使用しました。ニューラルヘッジは、ヘッジなしに比べてP&Lのばらつきを{dispersion_reduction:.1%}削減しました。",
        f"取引コスト5 bpで、ニューラルヘッジの99% CVaR損失は{neural['cvar_loss_99']:.3f}、離散Black–Scholesデルタは{bs['cvar_loss_99']:.3f}でした。",
        "健全性チェックは観測結果をそのまま表示します。不合格を隠したり、根拠のない優位性へ言い換えたりしません。",
    ]
    models_table_en = _models_table(config, "en")
    models_table_ja = _models_table(config, "ja")
    parameters_table_en = _parameters_table(config, "en")
    parameters_table_ja = _parameters_table(config, "ja")
    tradeoffs_table_en = _tradeoffs_table(neural, bs, "en")
    tradeoffs_table_ja = _tradeoffs_table(neural, bs, "ja")
    business_use_en = [
        "Trading desks hedging short-dated options where transaction costs are a material fraction of P&L can use this as a cost-aware alternative or overlay to delta hedging.",
        "Risk managers can select the training risk objective to match a house mandate: MSE for symmetric dispersion reduction, entropic or CVaR for tail-loss-focused mandates.",
        "Before adopting a learned policy in production, a report like this one supports the decision: compare economic P&L, tail loss, and turnover against the existing delta-hedging baseline on common paths.",
        "This is Phase 1 research on GBM only. Production use needs Phase 2 extensions (realistic/jump dynamics, multi-asset support, integration with existing risk and execution systems, model risk governance) before it can replace, rather than inform, an existing hedging process.",
    ]
    business_use_ja = [
        "取引コストがP&Lの無視できない割合を占める短期オプションをヘッジするトレーディングデスクにとって、デルタヘッジの代替またはオーバーレイとしてコスト適応的な選択肢になり得ます。",
        "リスク管理者は学習時のリスク目的関数をハウスのマンデートに合わせて選択できます。対称的な分散低減にはMSE、テール損失重視のマンデートにはエントロピックやCVaRです。",
        "本番投入前には、本レポートのような比較を意思決定支援として用い、共通経路上で学習方策の経済的P&L・テール損失・回転量を既存のデルタヘッジ基準と比較します。",
        "本プロジェクトはPhase 1のGBM限定の研究段階です。本番投入には、より現実的な（ジャンプを含む）市場ダイナミクス、複数資産対応、既存のリスク・執行システムとの統合、モデルリスクガバナンスといったPhase 2の拡張が必要であり、現状は既存のヘッジ業務を置き換えるのではなく意思決定を補助する位置づけが適切です。",
    ]
    figures = [
        _distribution(frame),
        _ecdf(frame),
        _tail_bar(summary),
        _sensitivity(sensitivity),
        _policy_heatmap(surface),
        _policy_heatmap(surface, difference=True),
        _training_history(history),
        _risk_objectives(risk),
    ]
    figure_blocks = [
        _figure_html(figure, include_js=index == 0) for index, figure in enumerate(figures)
    ]
    cards = [
        (
            "Neural P&L std",
            "ニューラルP&L標準偏差",
            neural["std_discounted_pnl_after_costs_including_premium"],
            "discounted currency",
            "割引通貨単位",
        ),
        (
            "Neural 99% CVaR",
            "ニューラル99% CVaR",
            neural["cvar_loss_99"],
            "economic loss",
            "経済損失",
        ),
        (
            "Neural turnover",
            "ニューラル売買回転量",
            neural["average_turnover_shares"],
            "shares per path",
            "1経路当たり株数",
        ),
        (
            "Average neural cost",
            "平均ニューラル取引コスト",
            neural["average_discounted_transaction_cost"],
            "discounted currency",
            "割引通貨単位",
        ),
    ]
    cards_html = "".join(
        f"<article class='metric-card'><span data-lang='en'>{html.escape(label_en)}</span><span data-lang='ja'>{html.escape(label_ja)}</span><strong>{value:.4f}</strong><small data-lang='en'>{html.escape(unit_en)}</small><small data-lang='ja'>{html.escape(unit_ja)}</small></article>"
        for label_en, label_ja, value, unit_en, unit_ja in cards
    )
    sanity_names_ja = {
        "near_frictionless_closer_to_bs_than_25bp": "低コスト方策は25 bp方策よりBSデルタに近い",
        "turnover_generally_decreases_with_cost": "取引コスト上昇に伴い売買回転量が概ね低下",
        "competent_hedge_reduces_dispersion": "有効なヘッジがP&L分散を低減",
        "common_random_numbers": "戦略比較で共通乱数を使用",
        "separate_train_validation_test": "学習・検証・テスト経路を分離",
        "tail_sample_size": "テール評価に必要な標本数",
    }
    sanity_rows = "".join(
        f"<tr><td><span data-lang='en'>{html.escape(name.replace('_', ' '))}</span><span data-lang='ja'>{html.escape(sanity_names_ja.get(name, name))}</span></td><td class='{'pass' if detail.get('passed') else 'warn'}'><span data-lang='en'>{'PASS' if detail.get('passed') else 'WARN'}</span><span data-lang='ja'>{'合格' if detail.get('passed') else '注意'}</span></td></tr>"
        for name, detail in sanity.items()
        if isinstance(detail, dict) and "passed" in detail
    )
    chart_translations = {
        "0": {
            "en": {
                "title": "Economic P&L distribution<br><sup>Common out-of-sample paths; selector changes visible strategies</sup>",
                "layout": {
                    "xaxis.title.text": "Discounted P&L after costs, including premium",
                    "yaxis.title.text": "Density",
                    "updatemenus[0].buttons[0].label": "All strategies",
                },
                "names": [LABELS[name] for name in frame["strategy"].drop_duplicates()],
            },
            "ja": {
                "title": "経済P&L分布<br><sup>共通のアウト・オブ・サンプル経路。セレクターで表示戦略を変更</sup>",
                "layout": {
                    "xaxis.title.text": "取引コスト控除後・プレミアム込みの割引P&L",
                    "yaxis.title.text": "密度",
                    "updatemenus[0].buttons[0].label": "全戦略",
                },
                "names": [LABELS_JA[name] for name in frame["strategy"].drop_duplicates()],
            },
        },
        "1": {
            "en": {
                "title": "Empirical CDF with tail zoom<br><sup>Lower values are worse for the short-option position</sup>",
                "layout": {
                    "xaxis.title.text": "Discounted P&L after costs, including premium",
                    "yaxis.title.text": "Cumulative probability",
                    "updatemenus[0].buttons[0].label": "Tail zoom",
                    "updatemenus[0].buttons[1].label": "Full range",
                },
                "names": [LABELS[name] for name in frame["strategy"].drop_duplicates()],
            },
            "ja": {
                "title": "テール拡大付き経験CDF<br><sup>ショート・オプションでは左側ほど悪い結果</sup>",
                "layout": {
                    "xaxis.title.text": "取引コスト控除後・プレミアム込みの割引P&L",
                    "yaxis.title.text": "累積確率",
                    "updatemenus[0].buttons[0].label": "テール拡大",
                    "updatemenus[0].buttons[1].label": "全範囲",
                },
                "names": [LABELS_JA[name] for name in frame["strategy"].drop_duplicates()],
            },
        },
        "2": {
            "en": {
                "title": "99% tail loss<br><sup>VaR is the loss quantile; CVaR is mean loss beyond the quantile</sup>",
                "layout": {"yaxis.title.text": "Discounted economic loss"},
                "names": ["99% VaR", "99% CVaR"],
            },
            "ja": {
                "title": "99%テール損失<br><sup>VaRは損失分位点、CVaRは分位点を超える損失の平均</sup>",
                "layout": {"yaxis.title.text": "割引経済損失"},
                "names": ["99% VaR損失", "99% CVaR損失"],
            },
        },
        "3": {
            "en": {
                "title": "Transaction-cost sensitivity<br><sup>Each point is a separately trained neural policy evaluated on common paths</sup>",
                "layout": {
                    "annotations[0].text": "P&L standard deviation",
                    "annotations[1].text": "99% CVaR loss",
                    "annotations[2].text": "Turnover",
                    "annotations[3].text": "Transaction cost",
                    "xaxis3.title.text": "Cost (bp)",
                    "xaxis4.title.text": "Cost (bp)",
                },
            },
            "ja": {
                "title": "取引コスト感応度<br><sup>各点は個別学習した方策を共通経路で評価</sup>",
                "layout": {
                    "annotations[0].text": "P&L標準偏差",
                    "annotations[1].text": "99% CVaR損失",
                    "annotations[2].text": "売買回転量",
                    "annotations[3].text": "取引コスト",
                    "xaxis3.title.text": "取引コスト (bp)",
                    "xaxis4.title.text": "取引コスト (bp)",
                },
            },
        },
        "4": {
            "en": {
                "title": "Neural hedge policy surface<br><sup>Previous position fixed at 0.5 shares; volatility 20%; transaction cost 5 bp</sup>",
                "layout": {
                    "xaxis.title.text": "Spot",
                    "yaxis.title.text": "Normalized time to maturity",
                },
                "colorbar": "Stock position",
            },
            "ja": {
                "title": "ニューラルヘッジ方策面<br><sup>前回ポジション0.5株、ボラティリティ20%、取引コスト5 bpに固定</sup>",
                "layout": {
                    "xaxis.title.text": "スポット価格",
                    "yaxis.title.text": "正規化残存期間",
                },
                "colorbar": "株式ポジション",
            },
        },
        "5": {
            "en": {
                "title": "Neural minus Black–Scholes delta<br><sup>Previous position fixed at 0.5 shares; volatility 20%; transaction cost 5 bp</sup>",
                "layout": {
                    "xaxis.title.text": "Spot",
                    "yaxis.title.text": "Normalized time to maturity",
                },
                "colorbar": "Delta difference",
            },
            "ja": {
                "title": "ニューラル − Black–Scholesデルタ<br><sup>前回ポジション0.5株、ボラティリティ20%、取引コスト5 bpに固定</sup>",
                "layout": {
                    "xaxis.title.text": "スポット価格",
                    "yaxis.title.text": "正規化残存期間",
                },
                "colorbar": "デルタ差",
            },
        },
        "6": {
            "en": {
                "title": "Training history<br><sup>Fresh training paths per update and one fixed validation set</sup>",
                "layout": {"xaxis.title.text": "Epoch", "yaxis.title.text": "MSE objective"},
                "names": ["Training", "Validation"],
            },
            "ja": {
                "title": "学習履歴<br><sup>更新ごとに新規学習経路を生成し、検証経路は固定</sup>",
                "layout": {"xaxis.title.text": "エポック", "yaxis.title.text": "MSE目的値"},
                "names": ["学習", "検証"],
            },
        },
        "7": {
            "en": {
                "title": "Risk-objective comparison<br><sup>Same market, transaction cost and test paths; values normalized to the MSE policy</sup>",
                "layout": {"yaxis.title.text": "Ratio to MSE"},
                "names": ["MSE", "Entropic"],
            },
            "ja": {
                "title": "リスク目的関数の比較<br><sup>市場・取引コスト・テスト経路を統一し、MSE方策を1として正規化</sup>",
                "layout": {"yaxis.title.text": "MSEに対する比率"},
                "names": ["MSE", "エントロピック"],
            },
        },
    }
    chart_translations_json = json.dumps(chart_translations, ensure_ascii=False)
    document = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Deep Hedging — 欧州コール</title>
<style>
:root{{--ink:#111827;--muted:#4b5563;--line:#e5e7eb;--blue:#2563eb;--paper:#fff;--soft:#f8fafc}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--soft);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}}
header{{background:linear-gradient(130deg,#0f172a,#1e3a8a);color:white;padding:56px 24px}} header>div,main{{max-width:1120px;margin:auto}}
h1{{font-size:2.55rem;line-height:1.1;margin:0 0 12px}} h2{{font-size:1.65rem;margin-top:0}} h3{{font-size:1.15rem}}
.eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:.78rem;color:#bfdbfe}} .subtitle{{max-width:800px;color:#dbeafe}}
main{{padding:32px 20px 70px}} section{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:28px;margin:22px 0;box-shadow:0 4px 18px rgba(15,23,42,.04)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:20px 0}} .metric-card{{border:1px solid var(--line);border-radius:10px;padding:16px;background:#fff}}
.metric-card span,.metric-card small{{display:block;color:var(--muted)}} .metric-card strong{{display:block;font-size:1.75rem;color:#1d4ed8;margin:4px 0}}
.chart{{margin:18px 0 28px}} .note{{border-left:4px solid #d97706;background:#fffbeb;padding:12px 16px;color:#78350f}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}} th,td{{border-bottom:1px solid var(--line);padding:10px;text-align:right}} th:first-child,td:first-child{{text-align:left}} th{{background:#f8fafc}}
.pass{{color:#166534;font-weight:700}} .warn{{color:#b45309;font-weight:700}} code{{background:#f1f5f9;padding:.15em .35em;border-radius:4px}}
pre{{overflow:auto;background:#0f172a;color:#e2e8f0;padding:16px;border-radius:8px}} footer{{color:var(--muted);text-align:center;margin-top:30px}}
.language-switch{{position:fixed;z-index:50;right:18px;top:16px;display:flex;gap:6px;padding:5px;background:rgba(15,23,42,.88);border:1px solid rgba(255,255,255,.25);border-radius:999px;backdrop-filter:blur(8px)}}
.language-switch button{{border:0;border-radius:999px;padding:7px 12px;background:transparent;color:#dbeafe;font-weight:700;cursor:pointer}} .language-switch button.active{{background:#fff;color:#1e3a8a}}
[data-lang='en']{{display:none}}
@media(max-width:700px){{header{{padding:38px 18px}}h1{{font-size:2rem}}section{{padding:18px}}.plotly-graph-div{{min-height:420px}}}}
</style></head><body>
<nav class="language-switch" aria-label="Language"><button type="button" data-language-button="ja" class="active" onclick="setLanguage('ja')">日本語</button><button type="button" data-language-button="en" onclick="setLanguage('en')">English</button></nav>
<header><div><div class="eyebrow">Phase 1 · Deep Hedging</div><h1><span data-lang="en">Dynamic hedging of a short European call</span><span data-lang="ja">欧州コールの動的ディープヘッジング</span></h1><p class="subtitle" data-lang="en">A reproducible PyTorch experiment under physical-measure GBM, discrete rebalancing, proportional transaction costs, and discounted pathwise accounting.</p><p class="subtitle" data-lang="ja">物理測度GBM、離散リバランス、比例取引コスト、割引パス会計を用いた再現可能なPyTorch実験。</p></div></header>
<main>
<section id="summary"><h2><span data-lang="en">Technical summary</span><span data-lang="ja">技術サマリー</span></h2><ul data-lang="en">{"".join(f"<li>{html.escape(sentence)}</li>" for sentence in summary_sentences_en)}</ul><ul data-lang="ja">{"".join(f"<li>{html.escape(sentence)}</li>" for sentence in summary_sentences_ja)}</ul><div class="cards">{cards_html}</div></section>
<section id="comparison"><h2><span data-lang="en">Main strategy comparison at 5 bp</span><span data-lang="ja">取引コスト5 bpでの主要戦略比較</span></h2><p data-lang="en">All strategies use identical simulated paths and the same accounting engine. P&L is discounted, after transaction costs, and includes the initial Black–Scholes premium.</p><p data-lang="ja">全戦略で同一のシミュレーション経路と会計エンジンを使用します。P&Lは割引済み・取引コスト控除後・初期Black–Scholesプレミアム込みです。</p><div data-lang="en">{_metrics_table(summary, "en")}</div><div data-lang="ja">{_metrics_table(summary, "ja")}</div><div class="chart" data-chart-index="0">{figure_blocks[0]}</div><p data-lang="en">The selector reveals each strategy without changing bins or the underlying sample.</p><p data-lang="ja">セレクターはビンや標本を変えず、表示する戦略だけを切り替えます。</p><div class="chart" data-chart-index="1">{figure_blocks[1]}</div></section>
<section id="tails"><h2><span data-lang="en">Tail outcomes are evaluated as economic loss</span><span data-lang="ja">テール結果は経済損失として評価</span></h2><p data-lang="en">VaR and CVaR are applied to minus P&L, so larger positive values represent worse losses.</p><p data-lang="ja">VaRとCVaRはマイナスP&Lに適用するため、大きな正値ほど悪い損失を表します。</p><div class="chart" data-chart-index="2">{figure_blocks[2]}</div></section>
<section id="method"><h2><span data-lang="en">Scope, definitions, and method</span><span data-lang="ja">対象範囲・定義・手法</span></h2><p data-lang="en">The model observes log-moneyness, normalized time to maturity, previous hedge, volatility, and proportional cost. It outputs a bounded stock position and is trained end to end from <code>L = discounted payoff − net trading gain</code>. The reporting premium is excluded from training but included in economic P&L.</p><p data-lang="ja">モデルは対数マネーネス、正規化残存期間、前回ヘッジ、ボラティリティ、比例取引コストを観測します。有界な株式ポジションを出力し、<code>L = 割引ペイオフ − 純売買損益</code>からエンドツーエンドで学習します。報告用プレミアムは学習損失から除外し、経済P&Lには含めます。</p><p data-lang="en">Transaction costs are paid when establishing or changing positions at hedge dates. The supplied accounting convention does not charge a terminal liquidation trade.</p><p data-lang="ja">取引コストは各ヘッジ時点でポジションを新設・変更するときに支払います。指定された会計規約では満期清算取引を課していません。</p><div class="chart" data-chart-index="6">{figure_blocks[6]}</div></section>
<section id="sensitivity"><h2><span data-lang="en">Transaction costs change trading behavior and risk</span><span data-lang="ja">取引コストによる売買行動とリスクの変化</span></h2><p data-lang="en">Each cost level receives a separately trained policy, while evaluation paths stay fixed. This distinguishes learned response from Monte Carlo sample noise.</p><p data-lang="ja">各コスト水準で方策を個別学習し、評価経路は固定します。これにより、学習した反応とMonte Carlo標本ノイズを区別します。</p><div class="chart" data-chart-index="3">{figure_blocks[3]}</div></section>
<section id="policy"><h2><span data-lang="en">The policy depends on both market state and prior holdings</span><span data-lang="ja">方策は市場状態と前回保有量の両方に依存</span></h2><p data-lang="en">The two heatmaps condition on a 0.5-share prior position. They are slices of a five-dimensional policy, not unconditional target deltas.</p><p data-lang="ja">2つのヒートマップは前回ポジションを0.5株に固定した条件付き表示です。無条件の目標デルタではなく、5次元方策の断面です。</p><div class="chart" data-chart-index="4">{figure_blocks[4]}</div><div class="chart" data-chart-index="5">{figure_blocks[5]}</div></section>
<section id="risk"><h2><span data-lang="en">Risk objective comparison</span><span data-lang="ja">リスク目的関数の比較</span></h2><p data-lang="en">MSE and entropic policies are evaluated with the same economic metrics. Ratios below one indicate a smaller value than the MSE policy, but no single ratio establishes overall superiority.</p><p data-lang="ja">MSE方策とエントロピック方策を同一の経済指標で評価します。1未満はMSE方策より小さい値ですが、単一の比率だけで総合的な優位性は判断できません。</p><div class="chart" data-chart-index="7">{figure_blocks[7]}</div></section>
<section id="model-params"><h2><span data-lang="en">Models and parameters</span><span data-lang="ja">モデルとパラメータ</span></h2><p data-lang="en">All strategies above are evaluated under this run's configuration; each neural policy is a separately trained set of weights.</p><p data-lang="ja">上記の全戦略は本実行の設定の下で評価しており、ニューラル方策は学習ごとに個別の重みを持ちます。</p><h3><span data-lang="en">Models compared</span><span data-lang="ja">比較対象モデル</span></h3><div data-lang='en'>{models_table_en}</div><div data-lang='ja'>{models_table_ja}</div><h3><span data-lang="en">Key parameters (this run)</span><span data-lang="ja">主要パラメータ（本実行）</span></h3><div data-lang='en'>{parameters_table_en}</div><div data-lang='ja'>{parameters_table_ja}</div></section>
<section id="tradeoffs"><h2><span data-lang="en">Advantages, disadvantages, and business use</span><span data-lang="ja">利点・欠点とビジネスユース</span></h2><h3><span data-lang="en">Neural hedge versus Black–Scholes delta</span><span data-lang="ja">ニューラルヘッジ vs Black–Scholesデルタ</span></h3><div data-lang='en'>{tradeoffs_table_en}</div><div data-lang='ja'>{tradeoffs_table_ja}</div><h3><span data-lang="en">Where this could be used</span><span data-lang="ja">想定される活用場面</span></h3><ul data-lang="en">{"".join(f"<li>{html.escape(sentence)}</li>" for sentence in business_use_en)}</ul><ul data-lang="ja">{"".join(f"<li>{html.escape(sentence)}</li>" for sentence in business_use_ja)}</ul></section>
<section id="robustness"><h2><span data-lang="en">Robustness and sanity checks</span><span data-lang="ja">頑健性・健全性チェック</span></h2><table><thead><tr><th><span data-lang="en">Check</span><span data-lang="ja">チェック項目</span></th><th><span data-lang="en">Status</span><span data-lang="ja">状態</span></th></tr></thead><tbody>{sanity_rows}</tbody></table><p class="note" data-lang="en">A WARN is retained as an empirical limitation. It is not silently rewritten as a success.</p><p class="note" data-lang="ja">注意結果は実証上の制約として残し、成功へ書き換えません。</p></section>
<section id="limitations"><h2><span data-lang="en">Limitations and uncertainty</span><span data-lang="ja">制約と不確実性</span></h2><ul data-lang="en"><li>GBM has constant volatility and no jumps, stochastic volatility, liquidity state, or model uncertainty.</li><li>Quick-profile 99% CVaR uses roughly {int(config.training.test_paths * 0.01)} tail observations and is noisier than the full profile.</li><li>The option premium is a reporting convention, not a price learned jointly with the hedge.</li><li>Results are educational research, not trading or investment advice.</li></ul><ul data-lang="ja"><li>GBMはボラティリティ一定で、ジャンプ、確率的ボラティリティ、流動性状態、モデル不確実性を含みません。</li><li>quickプロファイルの99% CVaRは約{int(config.training.test_paths * 0.01)}件のテール観測に基づき、fullプロファイルよりノイズが大きくなります。</li><li>オプションプレミアムは報告上の規約であり、ヘッジと同時学習した価格ではありません。</li><li>本結果は教育・研究目的で、取引・投資助言ではありません。</li></ul></section>
<section id="reproduce"><h2><span data-lang="en">Reproduce and extend</span><span data-lang="ja">再現と拡張</span></h2><pre>python -m deep_hedge_price.cli train --config configs/quick.yaml
python -m deep_hedge_price.cli evaluate --config configs/quick.yaml
python -m deep_hedge_price.cli sensitivity --config configs/quick.yaml
python -m deep_hedge_price.cli report --config configs/quick.yaml
make demo</pre><p data-lang="en">Phase 2 should begin with a Black–Scholes supervised pricing surrogate and an independently validated Monte Carlo label generator before joint price-and-Greeks learning.</p><p data-lang="ja">Phase 2は、価格とGreeksの同時学習より前に、Black–Scholes教師あり価格サロゲートと独立検証済みMonte Carloラベル生成器から始めるべきです。</p></section>
<footer><span data-lang="en">Generated locally from synthetic GBM paths</span><span data-lang="ja">合成GBM経路からローカル生成</span> · profile {html.escape(config.profile)} · config {config.fingerprint()}</footer>
</main>
<script>
const chartTranslations = {chart_translations_json};
function translateCharts(language) {{
  Object.entries(chartTranslations).forEach(([index, translations]) => {{
    const chart = document.querySelector(`.chart[data-chart-index="${{index}}"] .plotly-graph-div`);
    if (!chart || !window.Plotly) return;
    const translation = translations[language];
    const updates = {{"title.text": translation.title, ...(translation.layout || {{}})}};
    Plotly.relayout(chart, updates);
    (translation.names || []).forEach((name, traceIndex) => Plotly.restyle(chart, {{name}}, [traceIndex]));
    if (translation.colorbar) Plotly.restyle(chart, {{"colorbar.title.text": translation.colorbar}}, [0]);
  }});
}}
function setLanguage(language) {{
  document.documentElement.lang = language;
  document.title = language === 'ja' ? 'Deep Hedging — 欧州コール' : 'Deep Hedging — European Call';
  document.querySelectorAll('[data-lang]').forEach(element => {{
    element.style.display = element.dataset.lang === language ? '' : 'none';
  }});
  document.querySelectorAll('[data-language-button]').forEach(button => {{
    const active = button.dataset.languageButton === language;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  }});
  translateCharts(language);
  try {{ localStorage.setItem('deepHedgeLanguage', language); }} catch (_) {{}}
}}
let initialLanguage = 'ja';
try {{ initialLanguage = localStorage.getItem('deepHedgeLanguage') || 'ja'; }} catch (_) {{}}
if (!['ja', 'en'].includes(initialLanguage)) initialLanguage = 'ja';
requestAnimationFrame(() => setLanguage(initialLanguage));
</script></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output
