"""Self-contained local HTML reporting for a curve run."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import numpy as np
import pandas as pd


def _image_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _metric_line(name: str, metrics: dict[str, object]) -> str:
    return (
        f"<tr><td>{html.escape(name)}</td><td>{metrics['n']}</td>"
        f"<td>{float(metrics['weighted_normalized_rmse']):.4f}</td>"
        f"<td>{float(metrics['median_abs_standardized_error']):.4f}</td></tr>"
    )


def render_report(
    path: Path,
    valuation_date: str,
    raw: pd.DataFrame,
    audit: pd.DataFrame,
    comparison: dict[str, object],
    sensitivity: dict[str, object],
    repricing: pd.DataFrame,
    risk: pd.DataFrame,
    chart_paths: list[Path],
) -> None:
    """Create an intentionally dependency-free report that opens locally."""
    actions = audit["action"].value_counts().to_dict()
    selected = str(comparison["selected_model"])
    baseline = comparison["baseline"]
    advanced = comparison["advanced"]
    assert isinstance(baseline, dict) and isinstance(advanced, dict)
    base_train, base_hold = baseline["train"], baseline["holdout"]
    adv_train, adv_hold = advanced["train"], advanced["holdout"]
    assert all(isinstance(x, dict) for x in (base_train, base_hold, adv_train, adv_hold))
    residual_summary = repricing.groupby("instrument_type")["residual"].agg(["count", "mean", "std", "max", "min"]).round(8).to_html(classes="compact", border=0)
    risk_gap = float(np.max(np.abs(risk["key_sum_minus_dv01"]))) if len(risk) else float("nan")
    sensitivity_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(str(item['conditions']))}</td>"
        f"<td>{float(item['numerical_results']['max_zero_rate_change_bp']):.3f}</td>"
        f"<td>{html.escape(str(item['interpretation']))}</td></tr>"
        for name, item in sensitivity.items()
    )
    images = "".join(
        f'<figure><img src="{_image_data(image)}" alt="{html.escape(image.stem)}"><figcaption>{html.escape(image.stem.replace("_", " ").title())}</figcaption></figure>'
        for image in chart_paths
    )
    weak_points = [
        "公開データは単一評価日の断面だけであり、独立した時系列バックテストは実施していない。",
        "30年端点は流動性の高い観測が少なく、端点近傍のフォワードは外挿に敏感である。",
        "ACT/365F の年限分数とスタブ処理は簡略化している。本番利用には営業日・休日・受渡日を含むカレンダー検証が必要である。",
    ]
    advanced_configuration = comparison["advanced_configuration"]
    assert isinstance(advanced_configuration, dict)
    html_text = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>QuantCurve 調査レポート</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#1f2933;line-height:1.5}}
h1,h2{{color:#12395b}} .note{{background:#edf6fb;padding:14px;border-left:4px solid #246b99}}
table{{border-collapse:collapse;width:100%;margin:12px 0}} th,td{{border:1px solid #d9e2ec;padding:7px;text-align:left}} th{{background:#f0f4f8}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}} figure{{margin:0;border:1px solid #d9e2ec;padding:8px}} img{{width:100%;height:auto}} figcaption{{font-size:.9em;color:#52606d}}
code{{background:#f0f4f8;padding:2px 4px}} .small{{font-size:.92em;color:#52606d}}
</style></head><body>
<h1>USD 連続複利ゼロカーブ 調査レポート</h1>
<p class="small">評価日: {html.escape(valuation_date)} · 決定的ワークフロー · 特記なき金利は年率小数。</p>
<h2>エグゼクティブ・サマリー / Executive Summary</h2>
<div class="note"><strong>採用モデル: {html.escape(selected)}。</strong> {html.escape(str(comparison['selection_rationale']))}
ログ割引因子空間で推定するため、負のゼロ・フォワード金利を許しつつ割引因子を正に保つ。</div>
<p>{len(raw)} 件中、検証後の利用可能観測は {len(audit) - int(actions.get('exclude', 0))} 件。監査結果は補正 {int(actions.get('correct', 0))} 件、ダウンウェイト {int(actions.get('downweight', 0))} 件、除外 {int(actions.get('exclude', 0))} 件である。</p>
<h2>手法 / Methodology</h2>
<p>基準モデルは区分線形のログ割引因子カーブ、高度モデルは自然三次ログDFスプラインに瞬間フォワードの変化へのペナルティを加えたものとした。預金は単利恒等式、OISは固定脚アニュイティ等式、債券はクーポンと元本の割引現在価値で価格付けする。レート残差は商品別フロアとbid/ask・流動性品質で正規化し、高度モデルは決定的なHuber型IRLSを3回行う。</p>
<p>既存の平滑化係数 10.0 は固定した。今回の一要因で検証した長期曲率ペナルティ係数は {float(advanced_configuration['long_end_curvature_multiplier']):g} であり、平滑化係数との交互作用探索は行っていない。検証は成熟度順で5番目ごとのバケットを丸ごとホールドアウトし、同一満期の漏洩を防ぐ補間検証である。</p>
<h2>データ品質 / Data Quality</h2>
<p>較正前にスキーマ、時刻、単位、範囲、bid/ask、欠測、重複を検査する。レートはパーセントから小数へ、債券は100当たりの価格点のままとする。有効なbid/ask外の値は中点へ補正し、判断は <code>cleaning.csv</code> に残す。stale観測は品質重みを下げて保持し、重複は新しい観測を残す。</p>
<table><tr><th>Action</th><th>Count</th></tr>{''.join(f'<tr><td>{html.escape(str(k))}</td><td>{int(v)}</td></tr>' for k,v in sorted(actions.items()))}</table>
<h2>モデル比較 / Model Comparison</h2>
<table><tr><th>Model / sample</th><th>N</th><th>Weighted normalized RMSE</th><th>Median absolute standardized error</th></tr>
{_metric_line('Baseline / train', base_train)}{_metric_line('Baseline / holdout', base_hold)}{_metric_line('Advanced / train', adv_train)}{_metric_line('Advanced / holdout', adv_hold)}</table>
<p>ホールドアウト満期バケット: {', '.join(f'{float(x):g}Y' for x in comparison['holdout_maturity_years'])}。正規化RMSEは、レートは 0.5bp、債券は0.05 price pointsのフロアで割った無次元量であり、商品横断の価格単位比較には用いない。</p>
<h2>感度分析 / Sensitivity Analysis</h2>
<p>すべての再推定実験について条件、数値結果、解釈を記録する。これは採用根拠とは別の、全データに対する曲線形状の感応度である。</p>
<table><tr><th>実験</th><th>条件</th><th>最大ゼロ金利変化 (bp)</th><th>解釈</th></tr>{sensitivity_rows}</table>
<h2>検証と再価格付け / Validation and Repricing</h2>
<p>すべての感応度はゼロ金利の中心差分 ±1bp による。2Y・5Y・10Y・30Y のキー・レート形状は分割和が平行シフトになるよう設計した。キー合計とDV01の最大差は {risk_gap:.6g} 通貨単位である。</p>
<h3>商品別再価格付け残差</h3>{residual_summary}
<h2>図表 / Charts</h2><div class="grid">{images}</div>
<h2>制約・モデルリスク / Limitations</h2>
<ul>{''.join(f'<li>{html.escape(item)}</li>' for item in weak_points)}</ul>
<h2>推奨する次の手順 / Recommended Next Steps</h2>
<p>商品カレンダーと支払スケジュールを独立実装で検証し、履歴クロスバリデーションとストレスしたbid/ask条件を追加する。その後、取引・評価利用前に長期フォワードとキー・レートリスクへのガバナンス上限を設定する。</p>
</body></html>"""
    path.write_text(html_text, encoding="utf-8")
