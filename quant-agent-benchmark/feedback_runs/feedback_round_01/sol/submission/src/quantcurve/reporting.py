"""Deterministic charts and self-contained HTML research report."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .curve import ZeroCurve


def create_charts(
    chart_dir: Path,
    selected_curve: ZeroCurve,
    baseline_curve: ZeroCurve,
    advanced_curve: ZeroCurve,
    repricing: pd.DataFrame,
    comparison: dict[str, object],
) -> list[Path]:
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})
    grid = np.linspace(1.0 / 12.0, 30.0, 721)
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(grid, 100 * np.asarray(baseline_curve.zero(grid)), label="Baseline PCHIP", lw=1.5)
    ax.plot(grid, 100 * np.asarray(advanced_curve.zero(grid)), label="Robust smooth spline", lw=2.0)
    ax.set(title="Continuously Compounded Zero Curves", xlabel="Maturity (years)", ylabel="Zero rate (%)")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "curve.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(grid, 100 * np.asarray(selected_curve.forward(grid)), color="#cc5500", lw=1.8, label="Instantaneous forward")
    ax.plot(grid, 100 * np.asarray(selected_curve.zero(grid)), color="#1f77b4", lw=1.2, alpha=0.8, label="Zero rate")
    ax.axhline(0.0, color="black", lw=0.7)
    ax.set(title="Selected Curve: Forward and Zero Rates", xlabel="Maturity (years)", ylabel="Rate (%)")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "forward_rate.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.3))
    rate_rows = repricing[repricing["instrument_type"] != "bond"]
    for instrument_type, group in rate_rows.groupby("instrument_type"):
        axes[0].scatter(group["maturity_years"], 10_000 * group["residual"], s=20, alpha=0.75, label=instrument_type)
    axes[0].axhline(0.0, color="black", lw=0.7)
    axes[0].set_yscale("symlog", linthresh=5.0)
    axes[0].set(title="Rate-instrument residuals", xlabel="Maturity (years)", ylabel="Model - market (bp)")
    axes[0].legend()
    bonds = repricing[repricing["instrument_type"] == "bond"]
    axes[1].scatter(bonds["maturity_years"], bonds["residual"], s=22, alpha=0.75, color="#2ca02c")
    axes[1].axhline(0.0, color="black", lw=0.7)
    axes[1].set_yscale("symlog", linthresh=0.10)
    axes[1].set(title="Bond residuals", xlabel="Maturity (years)", ylabel="Model - market (price points)")
    fig.tight_layout()
    path = chart_dir / "repricing.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    labels = ["Train", "Holdout"]
    baseline = [
        comparison["baseline"]["train"]["weighted_normalized_rmse"],
        comparison["baseline"]["holdout"]["weighted_normalized_rmse"],
    ]
    advanced = [
        comparison["advanced"]["train"]["weighted_normalized_rmse"],
        comparison["advanced"]["holdout"]["weighted_normalized_rmse"],
    ]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar(x - 0.18, baseline, 0.36, label="Baseline")
    ax.bar(x + 0.18, advanced, 0.36, label="Advanced")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Spread-normalized weighted RMSE")
    ax.set_title("Visible Maturity-block Validation")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "model_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)
    return paths


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _mapping_table(mapping: dict[str, object]) -> str:
    rows = []
    for key, value in mapping.items():
        if isinstance(value, float):
            shown = f"{value:.6g}"
        else:
            shown = html.escape(str(value))
        rows.append(f"<tr><th>{html.escape(str(key))}</th><td>{shown}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def build_html_report(
    report_path: Path,
    valuation_date: str,
    comparison: dict[str, object],
    sensitivity: dict[str, object],
    validation: dict[str, object],
    cleaning: pd.DataFrame,
    repricing: pd.DataFrame,
    chart_paths: list[Path],
    config_summary: dict[str, object],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    action_counts = cleaning["action"].value_counts().to_dict()
    selected = str(comparison["selected_model"])
    baseline_holdout = float(comparison["baseline"]["holdout"]["weighted_normalized_rmse"])
    advanced_holdout = float(comparison["advanced"]["holdout"]["weighted_normalized_rmse"])
    improvement = 100.0 * (baseline_holdout - advanced_holdout) / max(baseline_holdout, 1e-12)
    if improvement >= 0:
        holdout_comparison = f"{improvement:.2f}%改善"
    else:
        holdout_comparison = f"{abs(improvement):.2f}%悪化"
    worst = repricing.assign(abs_standardized=lambda x: x["standardized_residual"].abs()).nlargest(8, "abs_standardized")
    worst_rows = "".join(
        f"<tr><td>{html.escape(str(r.instrument_id))}</td><td>{html.escape(str(r.instrument_type))}</td>"
        f"<td>{r.maturity_years:.3f}</td><td>{r.residual:.6g}</td><td>{r.weight:.4f}</td></tr>"
        for r in worst.itertuples()
    )
    images = "".join(
        f"<figure><img src=\"{_image_data_uri(path)}\" alt=\"{html.escape(path.stem)}\"><figcaption>{html.escape(path.stem.replace('_', ' ').title())}</figcaption></figure>"
        for path in chart_paths
    )
    sensitivity_json = html.escape(json.dumps(sensitivity, indent=2, sort_keys=True))
    validation_json = html.escape(json.dumps(validation, indent=2, sort_keys=True))
    document = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>USDゼロカーブ調査レポート</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1050px;margin:28px auto;padding:0 22px;color:#1f2933;line-height:1.48}}
h1,h2{{color:#123b5d}} .callout{{background:#eef6fb;border-left:5px solid #2779a7;padding:12px 16px}}
table{{border-collapse:collapse;width:100%;margin:10px 0 20px}}th,td{{border:1px solid #cad4dc;padding:7px;text-align:left}}th{{background:#edf2f5}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}figure{{margin:0}}img{{width:100%;border:1px solid #d4dce2}}figcaption{{text-align:center;color:#52606d}}
pre{{background:#f5f7f8;padding:12px;overflow:auto;font-size:12px}}code{{font-family:Menlo,monospace}} .small{{font-size:0.9em;color:#52606d}}
@media(max-width:760px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>USDゼロカーブ調査レポート</h1>
<p class="small">評価日（Valuation date）: {html.escape(valuation_date)}。特記がない金利は連続複利の年率小数です。</p>
<p class="small">Valuation date: {html.escape(valuation_date)}.</p>

<h2>要約（Executive Summary）</h2>
<div class="callout"><strong>採用モデル: {html.escape(selected)}。</strong> 高度モデルの公開ホールドアウトにおけるスプレッド正規化RMSEは、基準モデル比で {holdout_comparison}。採用には2%超の改善と数値ガードレール通過を同時に要求し、複雑さ自体は根拠にしていません。{html.escape(str(comparison['selection_rationale']))}</div>

<h2>手法（Methodology）</h2>
<p>基準モデルは各預金・OIS・債券を単体で再現する平坦な連続複利利回りへ変換し、流動性・スプレッド重み付きの半年バケット中央値をPCHIP補間します。高度モデルは、公開仕様の各商品の価格式へ自然三次ゼロ金利スプラインを直接適合し、bid/ask由来の残差尺度、流動性重み、曲率ペナルティ、反復Huber重みを使います。割引因子は <code>exp(-z(T)T)</code> なので、負金利を許容しつつ常に正です。</p>
{_mapping_table(config_summary)}
<p>公開ホールドアウトは決定的な半年年限ブロックで割り当て、同一年限・近接年限の学習／検証間漏洩を抑えています。結果は短期・中期・長期、商品別、定期／端数満期別にも機械可読JSONへ分離して保存します。</p>

<h2>データ品質（Data Quality）</h2>
{_mapping_table({str(k): int(v) for k, v in action_counts.items()})}
<p>全入力行を <code>diagnostics/cleaning.csv</code> に残します。単位変換、中央値補完、bid/ask反転、鮮度、重複、低流動性、除外、ロバスト重みを明示し、問題行を黙って削除しません。</p>

<h2>モデル比較（Model Comparison）</h2>
<table><tr><th>Model</th><th>Train normalized RMSE</th><th>Holdout normalized RMSE</th></tr>
<tr><td>Baseline</td><td>{comparison['baseline']['train']['weighted_normalized_rmse']:.6g}</td><td>{baseline_holdout:.6g}</td></tr>
<tr><td>Advanced</td><td>{comparison['advanced']['train']['weighted_normalized_rmse']:.6g}</td><td>{advanced_holdout:.6g}</td></tr></table>

<h2>感度分析（Sensitivity Analysis）</h2>
<p>平滑化強度、ロバスト閾値、決定的な10%観測除去、流動性・スプレッド重み除去を一要因ずつ確認します。各条件・数値結果・解釈を分け、カーブ差は最終高度モデルに対する0–30年の密な格子で測定します。</p>
<pre>{sensitivity_json}</pre>

<h2>検証と再価格付け（Validation and Repricing）</h2>
<pre>{validation_json}</pre>
<table><tr><th>Instrument</th><th>Type</th><th>Maturity</th><th>Residual</th><th>Final weight</th></tr>{worst_rows}</table>

<h2>図表（Charts）</h2><p>ゼロ金利、フォワード、商品別残差、固定ホールドアウトのモデル差を、単位を分離して示します。</p><div class="charts">{images}</div>

<h2>限界（Limitations）</h2>
<ul><li>営業日規則・有効日がないため、公開の年限と規則的な支払間隔を使用します。端数満期債の端数クーポンは仕様上未確定です。</li>
<li>平坦ゼロ外挿は安定的ですが、長期フォワードのリスクは終端ノットに依存します。</li>
<li>公開ホールドアウトは単一評価日の内部検証であり、複数日のバックテストや未知の真値ではありません。</li>
<li>ロバストな低重み付けはカーブを保護しますが、対象クォートが誤りだとは証明しません。</li></ul>

<h2>推奨する次の手順（Recommended Next Steps）</h2>
<ol><li>本番評価では有効日、営業日カレンダー、実支払日、経過利息を追加する。</li>
<li>複数日と負金利ストレスでノット・平滑化をバックテストする。</li>
<li>修正単位、鮮度、外れ値フラグを原データ管理者と照合する。</li>
<li>実現カーブ変動と商品固有スプレッドに対してヘッジ損益を検証する。</li></ol>
</body></html>"""
    report_path.write_text(document, encoding="utf-8")
