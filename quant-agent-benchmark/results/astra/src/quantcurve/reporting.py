"""Headless charts and a self-contained local HTML research report."""
from __future__ import annotations

import base64
import html
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = {"baseline": "#b36b27", "advanced": "#176981"}


def make_charts(output, frame, fits, selected, comparison, sensitivity_curves):
    chart_dir = output / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 130, "savefig.dpi": 160,
                         "axes.titleweight": "bold", "axes.grid": True, "grid.alpha": .2})
    t = np.linspace(1 / 12, 30, 721)
    charts = []

    def save(fig, name):
        fig.savefig(chart_dir / name, facecolor="white", bbox_inches="tight", metadata={"Software": "quantcurve"})
        plt.close(fig)
        charts.append(name)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, layout="constrained")
    for kind, fit in fits.items():
        axes[0].plot(t, fit.curve.zero(t) * 100, label=f"{kind}{' (selected)' if selected == kind else ''}", color=COLORS[kind])
        axes[1].plot(t, fit.curve.discount(t), color=COLORS[kind])
    axes[0].set(ylabel="Continuously compounded zero rate (%)", title="Zero curves and strictly positive discount factors")
    axes[0].legend(loc="best")
    axes[1].set(xlabel="Maturity (years)", ylabel="Discount factor")
    save(fig, "curve.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout="constrained")
    for kind, fit in fits.items():
        axes[0].plot(t, fit.curve.forward(t) * 100, label=kind, color=COLORS[kind])
        ts = np.linspace(0, 2, 401)
        axes[1].plot(ts, fit.curve.forward(ts) * 100, label=kind, color=COLORS[kind])
    for ax in axes:
        ax.axhline(0, color="#666", linewidth=.7)
        ax.set(xlabel="Maturity (years)", ylabel="Instantaneous forward rate (%)")
    axes[0].set_title("Analytic forwards: 1M–30Y")
    axes[1].set_title("Front-end detail: 0–2Y")
    axes[0].legend()
    save(fig, "forward_rate.png")

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), layout="constrained")
    for ax, typ in zip(axes, ("deposit", "ois_swap", "bond")):
        m = frame.instrument_type == typ
        multiplier = 1 if typ == "bond" else 1e4
        for kind, fit in fits.items():
            residual = (fit.quotes[m] - frame.loc[m, "normalized_quote"]) * multiplier
            ax.scatter(frame.loc[m, "maturity_years"], residual, s=24, alpha=.75, label=kind, color=COLORS[kind], marker="x" if kind == "baseline" else "o")
        ax.axhline(0, color="#555", linewidth=.8)
        ax.set(title=f"{typ}: full-sample repricing (all usable observations)", xlabel="Maturity (years)",
               ylabel="Residual (price points)" if typ == "bond" else "Residual (basis points)")
    axes[0].legend()
    save(fig, "repricing.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout="constrained")
    for ax, metric, label in zip(axes, ("weighted_huber_loss", "median_absolute_standardized_error"),
                                  ("Liquidity-weighted Huber loss", "Median absolute standardized error")):
        x = np.arange(2)
        for offset, kind in ((-.18, "baseline"), (.18, "advanced")):
            values = [comparison[kind][scope][metric] for scope in ("train", "holdout")]
            bars = ax.bar(x + offset, values, width=.34, label=kind, color=COLORS[kind])
            ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=9)
        ax.set_xticks(x, ["Training groups", "Holdout groups"])
        ax.set(ylabel=label, title=f"{label}\nLower is better")
        ax.margins(y=.2)
    axes[0].legend(loc="upper left")
    save(fig, "model_comparison.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout="constrained")
    for label, curve in sensitivity_curves:
        axes[0].plot(t, curve.zero(t) * 100, label=label)
        axes[1].plot(t, (curve.zero(t) - fits["advanced"].curve.zero(t)) * 1e4, label=label)
    axes[0].set(xlabel="Maturity (years)", ylabel="Zero rate (%)", title="Smoothing sensitivity")
    axes[1].set(xlabel="Maturity (years)", ylabel="Change from reference (basis points)", title="Smoothing: zero-rate changes")
    axes[0].legend()
    save(fig, "sensitivity.png")
    return charts


def table(rows):
    return pd.DataFrame(rows).to_html(index=False, border=0, escape=True, float_format=lambda x: f"{x:.5g}")


def build_report(output, frame, audit, comparison, sensitivity, validation, charts, config, dataset_hash, valuation_date):
    selected = comparison["model_selected"]
    improved = comparison["relative_holdout_improvement"] * 100
    counts = audit.action.value_counts().to_dict()
    robust_count = int((audit.robust_weight.between(0, .999, inclusive="neither")).sum())
    rows = []
    for kind in ("baseline", "advanced"):
        for scope in ("train", "holdout", "full_sample"):
            m = comparison[kind][scope]
            rows.append({"モデル": kind, "範囲": scope, "件数": m["n"], "Huber損失": m["weighted_huber_loss"],
                         "標準化RMSE": m["standardized_rmse"], "標準化誤差の絶対値中央値": m["median_absolute_standardized_error"],
                         "気配内比率": m["within_bid_ask_fraction"]})
    type_rows = []
    for kind in ("baseline", "advanced"):
        for typ, m in comparison[kind]["holdout"]["by_instrument_type"].items():
            type_rows.append({"モデル": kind, "商品": typ, "件数": m["n"],
                              "単位": "価格ポイント" if typ == "bond" else "金利bp", "RMSE": m["rmse"],
                              "絶対誤差中央値": m["median_absolute_error"], "平均符号付き誤差": m["mean_signed_error"]})
    perturbations = []
    for check in ("smoothing", "outlier_threshold", "terminal_coupon_assumption"):
        for record in sensitivity[check]:
            perturbations.append({"検証": {"smoothing": "平滑化", "outlier_threshold": "Huber閾値", "terminal_coupon_assumption": "端数利払"}[check],
                                  "設定": str(record.get("smoothing", record.get("huber_threshold", record.get("alternative")))),
                                  "RMS Δz (bp)": record["rms_zero_change_bp"], "最大 |Δz| (bp)": record["max_abs_zero_change_bp"],
                                  "短端 ≤1Y (bp)": record["short_end_max_abs_zero_change_bp"], "長端 ≥20Y (bp)": record["long_end_max_abs_zero_change_bp"]})
    removal = sensitivity["remove_10_percent"]
    removed_max = max(x["max_abs_zero_change_bp"] for x in removal)
    liq = sensitivity["liquidity_weighting"]
    caption = {"curve.png": "両モデルを同じ連続複利単位で表示。市場パー金利をゼロ金利として直接描いていません。",
               "forward_rate.png": "解析微分から計算した瞬間フォワード。負の値は許容し、単調な割引係数を強制していません。",
               "repricing.png": "全採用観測のインサンプル誤差。極端な誤差も表示し、金利bpと債券価格ポイントを別の軸で示します。",
               "model_comparison.png": "校正に用いなかった満期群で比較。全検証観測を含み、検証誤差による削除は行いません。",
               "sensitivity.png": "平滑化強度を10分の1・同一・10倍に変更した再校正。"}
    images = []
    for name in charts:
        encoded = base64.b64encode((output / "charts" / name).read_bytes()).decode("ascii")
        images.append(f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(name)}"><figcaption>{caption[name]}</figcaption></figure>')
    audit_preview = audit.loc[audit.action != "keep", ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]]
    status = "PASS" if validation["all_passed"] else "FAIL"
    content = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuantCurve — ゼロカーブ研究報告</title><style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1d2f38;background:#eef2f4;margin:0;line-height:1.7}}
main{{max-width:1120px;margin:auto;background:white;padding:40px 48px}}h1{{font-size:2em;margin-bottom:.2em}}h2{{margin-top:2.2em;border-bottom:2px solid #dbe6eb;padding-bottom:.3em}}h3{{margin-top:1.7em}}
.lead{{background:#e9f3f6;border-left:5px solid #176981;padding:18px 24px}}.meta{{color:#4c646f;font-size:.9em}}.meta code{{overflow-wrap:anywhere}}.scroll{{overflow:auto}}table{{border-collapse:collapse;font-size:.83em;width:100%;margin:16px 0}}td,th{{padding:8px;border-bottom:1px solid #dbe3e7;text-align:left;vertical-align:top}}th{{background:#edf3f6;white-space:nowrap}}figure{{margin:28px 0}}img{{width:100%;height:auto}}figcaption{{color:#4c646f;font-size:.9em}}code,pre{{font-family:ui-monospace,monospace}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f8;padding:16px;font-size:.83em}}li{{margin:.5em 0}}.warn{{border-left:4px solid #b36b27;padding-left:18px}}@media(max-width:700px){{main{{padding:20px}}h1{{font-size:1.6em}}}}
</style></head><body><main>
<p class="meta">評価日 {html.escape(valuation_date)} / 再現可能な単一スナップショット研究 / 外部データ不使用</p>
<h1>ゼロカーブの推定と検証</h1><p class="meta">入力 SHA-256: <code>{dataset_hash}</code></p>
<section><h2>要旨</h2><div class="lead"><strong>選択モデル: {selected}</strong>。高度モデルの満期群ホールドアウト Huber 損失改善率は {improved:.2f}% でした。追加の複雑さを採用する条件は改善率5%超です。入力 {len(audit)} 件から {len(frame)} 商品を採用しました。</div>
<p>これは市場の正解曲線を知った検証ではありません。同時点の可視データで得られた暫定的な比較結果です。金利・債券価格の外れ値、端数キャッシュフローの曖昧さ、複数モデルの誤指定が残り、取引判断にそのまま利用できる品質保証にはなりません。</p>
<p class="warn">採用 {len(frame)} 商品のうち {robust_count} 商品で頑健な重みが低下しています。これは異常データがその件数あるという確定判定ではありません。特定満期の OIS と長期債券には系統的な残差があり、規約差や過度な平滑化を含むモデル誤指定の可能性を示します。</p></section>
<section><h2>手法</h2><p>単純モデルは時定数2年を固定した3係数 Nelson–Siegel モデルです。高度モデルは log(1+T) 上の自然3次スプラインで、ゼロ金利の2階微分の二乗積分に罰則を加えます。係数は bp、時間は ACT/365F 年、金利出力は年率小数です。両モデルで同じビッド・アスク、流動性、Huber 処理を用い、曲線の自由度の効果を比較します。頑健化しない最小二乗モデルも別に記録しています。</p>
<pre>D(T) = exp(-T z(T)); f(T) = z(T) + T z'(T)
objective = sum_i reliability_i × Huber((model_quote_i - quote_i)/sigma_i, δ={config.huber_threshold:g})
            + n × λ × integral [d² z_bp(x)/dx²]² dx, x=log(1+T)
sigma = max(half bid/ask spread, {config.rate_sigma_floor * 1e4:g} bp for rates or {config.price_sigma_floor:g} price points for bonds)</pre>
<p>8回以下の再重み付けで開始し、データの Huber 損失と曲率の二乗罰則を区別した厳密な最適化で仕上げます。流動性は精度の乗数であり、外れ値の最終重みは min(1, {config.huber_threshold:g}/|標準化残差|) です。重みをゼロにして残差を隠す方法は採用しません。</p>
<p>預金は単利の満期支払、OIS は固定クーポン脚と 1−D(T) の変動脚、債券は額面100の固定利払と償還を割り引きます。OIS の頻度は2年以下で年1回、それより長い商品は全期間を半年ごとと解釈します。端数最終期間は実際の年数で按分します。債券も最終端数クーポンを按分する仮定で、端数なし・全額クーポンとの再校正差を下記に示します。評価日からの開始、経過利息なしという供給仕様に従い、settlement_days=2 は検証するメタデータとして扱います。</p>
<p>DV01 は固定受取の (PV[−1bp]−PV[+1bp])/2。預金・OIS の元本は1,000,000、債券の額面は100です。2/5/10/30年の線形ハット型ゼロ金利バンプは左右端を一定とし、全期間で和が1になります。これは曲線を直接動かしたリスクで、市場クォートを動かして再校正するヘッジ感応度とは異なります。</p></section>
<section><h2>データ品質</h2>{table([{'action': k, 'count': v} for k,v in counts.items()])}
<p>{config.stale_days:g}暦日より古い観測を除外し、同一 instrument_id は有効な最新観測を優先します。欠損クォートは両側が有効な場合だけ中点で回復します。逆転した気配は交換し、単位補正には同満期の複数商品、または近傍の債券価格と金利の整合性を要求します。単位推定はヒューリスティックであり、真正な低価格・特殊商品を誤認するリスクがあります。観測数や商品 ID はアルゴリズムへ固定していません。</p>
<p><code>cleaning.csv</code> は元の入力順で全行を保存し、元クォート、正規化後クォート、精度重み、補正・除外理由を含みます。流動性や頑健重みにより action が downweight となっても、先行する単位修正等の理由は残ります。</p>
<details><summary>採用時に注意または変更した全観測</summary><div class="scroll">{audit_preview.to_html(index=False,border=0,escape=True,float_format=lambda x:f'{x:.7g}')}</div></details></section>
<section><h2>単純モデルと高度モデルの比較</h2><p>0–2年は0.25年、2–10年は1年、10年以降は2年幅の近接満期群を全商品種類で共有し、分散した内側の群を検証へ回しました。端点群は訓練に残します。訓練 {comparison['training_n']} 件、検証 {comparison['holdout_n']} 件。平滑化係数 λ={comparison['chosen_smoothing']:g} は訓練データ内の3分割で選び、外側の検証で再調整していません。</p>
<div class="scroll">{table(rows)}</div><h3>ホールドアウト誤差を商品別の本来の単位で比較</h3><div class="scroll">{table(type_rows)}</div>
<p class="warn">単位補正は分割前の可視テープ全体を参照します。そのため完全に未使用の時間外データ検証ではありません。また、Huber 損失にも大きな誤差の寄与は残ります。中央値・無制限の RMSE・ビッド／アスク内比率を併記し、単一指標の改善を品質保証とは扱いません。</p>
<details><summary>最小二乗アブレーションと平滑化選択の詳細</summary><pre>{html.escape(json.dumps({'ordinary_least_squares':comparison['ordinary_least_squares_ablation'],'inner_cv':comparison['inner_cv']},ensure_ascii=False,indent=2))}</pre></details></section>
<section><h2>感度分析と安定性</h2><div class="scroll">{table(perturbations)}</div>
<p>seed={config.seed} で10%の採用商品をランダムに除いた {len(removal)} 回の再校正では、最大ゼロ金利変化は {removed_max:.3f} bp でした。このチェックは訓練データを減らす安定性実験であり、無作為なホールドアウト検証ではありません。</p>
<p>流動性等の信頼度乗数を1に揃え、スプレッド尺度を保った場合の最大変化は {liq['max_abs_zero_change_bp']:.3f} bp、長端では {liq['long_end_max_abs_zero_change_bp']:.3f} bp です。短端と長端の変化を分けて診断し、外挿は追加観測による検証をしていません。</p>
<details><summary>短端・長端と除去実験の数値</summary><pre>{html.escape(json.dumps({'edges':sensitivity['edge_behavior'],'removal':removal},ensure_ascii=False,indent=2))}</pre></details></section>
<section><h2>検証とリプライシング</h2><p>ワークフロー内の数値検証: <strong>{status}</strong>。すべての採用商品を再評価し、中央差分と解析的な一次感応度、キーの合計を照合しています。全テストの実行回数と成否はプロジェクトの <code>benchmark_summary.json</code> および <code>logs/test_run_*.json</code> に保存されます。</p><pre>{html.escape(json.dumps(validation,ensure_ascii=False,indent=2))}</pre></section>
<section><h2>主要チャート</h2>{''.join(images)}</section>
<section><h2>制約とモデルリスク</h2><ul>
<li>単一の合成市場スナップショットです。信用・担保・流動性プレミアムを一つの割引曲線に集約しており、無裁定の検証済み市場曲線ではありません。</li>
<li>端数期間の細目が未指定です。按分する仮定が供給データの作成規則と一致する保証はなく、特定満期で揃って生じる残差は外れ値ではなく規約差かもしれません。</li>
<li>外れ値と実在する急峻な曲率を一枚のテープだけから確実に区別できません。平滑化と頑健化は真の局所構造を弱める可能性があります。</li>
<li>自然境界条件は log(1+T) 上のゼロ金利に課します。最後のモデル節点より先は瞬間フォワードを一定に延長します。実観測の最長満期より後から節点までの区間も、観測の裏付けが弱い範囲です。0から最初の観測までは平滑化に依存します。</li>
<li>バンプ感応度は採用した曲線・固定キャッシュフローを条件とします。再校正リスク、異なる曲線間のベーシス、ヘッジ商品の選択や取引コストを含みません。</li>
<li>テストは実装と内部整合性の検証です。隠れた評価データ・正解曲線には一切アクセスしていません。信頼区間や時間をまたぐ性能は推定していません。</li></ul></section>
<section><h2>推奨する次の検証</h2><ol><li>端数期間、利払日、決済日の扱いをデータ供給者と確定し、商品ごとの価格差を再点検する。</li><li>別日の独立テープで単位推定ルールを固定した時間外検証を行い、満期群分割を複数変えた結果も比較する。</li><li>クォートを動かした再校正感応度、代替ノット、信用・流動性の複数曲線を調べる。</li></ol></section>
<footer><p class="meta">ローカルで開ける自己完結 HTML。画像は埋め込み済み。外部フォント・スクリプト・追跡は使用していません。</p></footer></main></body></html>'''
    return content
