"""Generate (and execute) Milestone-3 notebooks: 09-12 (calibrations), 18 (ablation).

Usage: uv run --no-sync python jp_llm_lab/tools/build_notebooks_m3.py --execute [--only 11]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nbcommon import SETUP
from nbkit import build_notebook, code, md

REPO = Path(__file__).resolve().parents[1]
NB_DIR = REPO / "notebooks"
CAL = 'CAL = ROOT / "experiments/calibrations"\n'


def nb09() -> list:
    return [
        md(r'''
# 09. Initialization Diagnostics（spec §14.3）

## 学習目標
- 学習前の1回のforward/backwardだけで、初期化スキームがlogit分布・活性RMS・勾配ノルムに与える影響を測る
- 「良い初期化」は経験則でなく測定で選ぶ

## 比較スキーム
- `normal_0.02`（GPT-2既定 + 残差枝の 1/√(2L) スケーリング）
- `normal_0.02_noscale`（残差スケーリングなし）
- `xavier`（Glorot）/ `kaiming`（He, relu gain）

理想の初期化は logit がほぼ一様（loss≈ln V）で、活性・勾配が層間で安定していること。
'''),
        code(SETUP + CAL),
        code(r'''
res = load_json(CAL / "init.json")["results"]
import math
rows = []
for s, v in res.items():
    rows.append((s, v["init_loss"], v["logit_std"], v["softmax_entropy"], v["grad_norm_total"]))
df = pd.DataFrame(rows, columns=["scheme","init_loss","logit_std","softmax_entropy","grad_norm"])
print(f"理想 init_loss = ln V = {math.log(8192):.3f}")
df.round(3)
'''),
        code(r'''
# 残差ストリーム RMS の層プロファイル（爆発/消失の兆候）
fig = go.Figure()
for s, v in res.items():
    fig.add_trace(go.Scatter(y=v["resid_rms_by_layer"], mode="lines+markers", name=s))
fig.update_layout(title="初期化スキーム別 residual RMS（層プロファイル）",
                  xaxis_title="layer", yaxis_title="RMS", template="plotly_white", height=380)
fig.show()
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: `normal_0.02` は init_loss ≈ ln V（一様に近い＝過信していない）。`kaiming` は logit_std が大きく init_loss が ln V を超える（過信）。`xavier` は最も冷たい。残差スケーリングの有無で深い層のRMSプロファイルが変わる。
- **Interpretation**: 分類ヘッド前の logit が過大だと初期損失が悪化し、序盤に大きな勾配→不安定を招きうる。GPT-2既定が「logitほぼ一様＋残差RMS安定」を両立するため既定として妥当。
- **Caveat**: これは学習前1ステップの統計。最終性能への影響は短期runで別途確認すべき（初期化の差は数百ステップで縮小することも多い）。1シード。

**次へ**: [10_hardware_calibration](10_hardware_calibration.ipynb)
'''),
    ]


def nb10() -> list:
    return [
        md(r'''
# 10. Hardware Calibration（spec §14.1）

## 学習目標
- fp32/bf16・explicit/SDPA・micro batch・context を変えて実測スループットとVRAMを比較する
- 「最大バッチ」ではなく「安全余裕を残して tokens/sec が高い設定」を選ぶ
'''),
        code(SETUP + CAL),
        code(r'''
data = load_json(CAL / "hardware.json")
res = data["results"]
rows = []
for r in res:
    label = f'{r["dtype"]}/{r["attn"]}/compile={r["compile"]}/B{r["B"]}/T{r["T"]}'
    rows.append((label, r.get("tokens_per_sec"), r.get("peak_vram_gb"), r.get("error","")))
df = pd.DataFrame(rows, columns=["config","tokens_per_sec","peak_vram_gb","error"])
df
'''),
        code(r'''
ok = [r for r in res if "tokens_per_sec" in r and r.get("tokens_per_sec")]
labels = [f'{r["dtype"]}/{r["attn"]}/B{r["B"]}/T{r["T"]}' for r in ok]
fig = go.Figure(go.Bar(x=labels, y=[r["tokens_per_sec"] for r in ok],
                       text=[f'{r["peak_vram_gb"]}GB' for r in ok], marker_color="#2ca02c"))
fig.update_layout(title="学習スループット（tokens/sec, ラベル=peak VRAM）",
                  yaxis_title="tokens/sec", template="plotly_white", height=380)
fig.update_xaxes(tickangle=30)
fig.show()
best = max(ok, key=lambda r: r["tokens_per_sec"])
print(f"最速: {best['dtype']}/{best['attn']}/B{best['B']} → {best['tokens_per_sec']:,} tok/s, {best['peak_vram_gb']}GB")
compile_rows = [r for r in res if r["compile"]]
if compile_rows and "error" in compile_rows[0]:
    print(f"注: torch.compile はこの環境で失敗（{compile_rows[0]['error'][:60]}）— inductor の C++ コンパイラ不在。honestに記録。")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: bf16 + SDPA が fp32 + explicit の数倍。VRAM も削減。B=32 が最高スループット。torch.compile はこの環境では inductor の C++ コンパイラ不在で失敗（正直に記録）。
- **Interpretation**: この規模ではメモリ帯域よりカーネル効率が効き、bf16 の Tensor Core パスと SDPA の融合が支配的。B を上げると効率が上がるが VRAM 余裕が減る。
- **Caveat**: 数値はこのGPU・ドライバ・電力状態に固有。VRAM peak は実データ長依存。compile は環境が揃えば効く可能性があり「不要」の結論ではない。

**次へ**: [11_learning_rate_calibration](11_learning_rate_calibration.ipynb)
'''),
    ]


def nb11() -> list:
    return [
        md(r'''
# 11. Learning-Rate Range Test（spec §14.2）

## 学習目標
- 学習率を指数的に上げる短いrunで、loss・勾配ノルム・update比のLR依存を測る
- 不安定化点を検出し、推奨LRを根拠つきで自動提案する

## 数式
$$\eta_t = \eta_{\min}\left(\frac{\eta_{\max}}{\eta_{\min}}\right)^{t/T}$$
推奨LR = 「平滑化lossが最も急降下するLR」÷10（発散前の安全余裕）。
'''),
        code(SETUP + CAL),
        code(r'''
data = load_json(CAL / "lr_range.json")
recs = data["records"]
lrs = [r["lr"] for r in recs]
fig = go.Figure()
fig.add_trace(go.Scatter(x=lrs, y=[r["loss"] for r in recs], mode="lines+markers", name="loss",
                         line=dict(color="#1f77b4")))
fig.add_vline(x=data["suggested_lr"], line_dash="dash", line_color="#2ca02c",
              annotation_text=f'suggested {data["suggested_lr"]:.1e}')
if data["diverged_at_lr"]:
    fig.add_vline(x=data["diverged_at_lr"], line_dash="dot", line_color="#d62728",
                  annotation_text=f'diverged {data["diverged_at_lr"]:.1e}')
fig.update_xaxes(type="log", title="learning rate (log)")
fig.update_layout(title="LR range test: loss vs LR", yaxis_title="loss", template="plotly_white", height=400)
fig.show()
print(f"suggested_lr = {data['suggested_lr']:.2e}  (steepest {data['steepest_descent_lr']:.2e}, "
      f"diverged {data['diverged_at_lr']})")
print(data["logic"])
'''),
        code(r'''
fig = go.Figure()
fig.add_trace(go.Scatter(x=lrs, y=[r["grad_norm"] for r in recs], name="grad norm", line=dict(color="#d62728")))
fig.add_trace(go.Scatter(x=lrs, y=[r["update_ratio"] for r in recs], name="update ratio", yaxis="y2",
                         line=dict(color="#ff7f0e")))
fig.update_layout(title="LR vs 勾配ノルム / update比", template="plotly_white", height=380,
                  xaxis=dict(type="log", title="learning rate (log)"),
                  yaxis=dict(title="grad norm"), yaxis2=dict(title="update ratio", overlaying="y", side="right", type="log"))
fig.show()
print(f"Model M で実際に使った lr = 6e-4 は suggested {data['suggested_lr']:.1e} に対して"
      f" {'保守的' if 6e-4 < data['suggested_lr'] else '積極的'}")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: lossはLR増加とともに低下→ある点で急上昇（発散）。update比は単調増加。推奨LRは発散点の1–2桁下。
- **Interpretation**: 実運用の 6e-4 は推奨値より保守的で、安定性を優先した設定だったことが確認できる。範囲テストは「どこまで上げられるか」の上限を1回の短いrunで与える。
- **Caveat**: 単一バッチ列・1シードの short run。最適LRはバッチサイズ・スケジュール・モデルサイズに依存する。推奨ロジック（÷10）は経験則。

**次へ**: [12_batch_size_calibration](12_batch_size_calibration.ipynb)
'''),
    ]


def nb12() -> list:
    return [
        md(r'''
# 12. Batch-Size Calibration（spec §14.4）

## 学習目標
- 同じ**トークン予算**で有効バッチ（step あたりトークン数）を変え、per-step / per-token / per-wallclock の収束を比較する
- 「step が少ない＝速い」という誤解を、token と wall-clock の両軸で解く
'''),
        code(SETUP + CAL),
        code(r'''
res = load_json(CAL / "batch_size.json")["results"]
fig = go.Figure()
for r in res:
    c = r["curve"]
    fig.add_trace(go.Scatter(x=[p["tokens"] for p in c], y=[p["val_loss"] for p in c],
                             mode="lines+markers", name=f'{r["effective_tokens"]//1024}K tok/step'))
fig.update_layout(title="val loss vs トークン数（同一2Mトークン予算）",
                  xaxis_title="tokens seen", yaxis_title="val loss", template="plotly_white", height=400)
fig.show()
pd.DataFrame([(r["effective_tokens"], r["n_steps"], r["final_val_loss"], r["wallclock_sec"]) for r in res],
             columns=["eff_tokens","n_steps","final_val_loss","wallclock_s"])
'''),
        code(r'''
# per-step で見ると錯覚が起きる：横軸を step にすると大バッチが「1stepあたり」良く見える
fig = go.Figure()
for r in res:
    c = r["curve"]
    fig.add_trace(go.Scatter(x=[p["step"] for p in c], y=[p["val_loss"] for p in c],
                             mode="lines+markers", name=f'{r["effective_tokens"]//1024}K tok/step'))
fig.update_layout(title="同じデータを step 軸で見ると？（軸を変えると印象が反転）",
                  xaxis_title="optimizer step", yaxis_title="val loss", template="plotly_white", height=380)
fig.show()
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: 固定トークン予算では、小さい有効バッチ（=多い step 数）ほど低い val loss に到達。wall-clock はほぼ同等。step 軸で見ると大バッチが「1stepあたり良い」ように錯覚するが、token 軸では逆。
- **Interpretation**: 更新回数が多いほど収束が進む（勾配ノイズが正則化的に働く領域）。ただし大バッチは1step が重いので、時間軸で追うと差が縮む。どの軸で語るかで結論が変わる典型例。
- **Caveat**: 小モデル・2Mトークン・CPU/GPU混在の短期比較。大規模では大バッチが並列効率で有利になる領域があり、この結果を大規模へ外挿してはいけない。LRを固定したため、バッチに応じたLRスケーリング（linear/sqrt則）は未考慮。

**次へ**: [18_architecture_ablation](18_architecture_ablation.ipynb)
'''),
    ]


def nb18() -> list:
    return [
        md(r'''
# 18. Architecture Ablation — Classical → Modern（spec §7.3, §17, §18）

## 学習目標
- 1要素ずつ（LayerNorm→RMSNorm→RoPE→SwiGLU→bias無し）変えた統制実験を読む
- **効果量を seed 変動（3 seeds）と比較**し、「改善」を軽々に断定しない規律を身につける
- 「どちらが良いか」だけでなく、何が変わり・計算コストに見合うか・断定できないことを述べる

## 統制条件（ceteris paribus）
同一コーパス（pilot 8M）・同一 validation（別文書）・同一パラメータ規模（SwiGLU幅=8d/3でGELU 4dに一致）・
同一トークン予算（~3.7M, <1epoch）・同一 optimizer・各3 seeds。独立変数はアーキテクチャの1要素のみ。
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.visualization.comparison import ablation_val_loss_figure, ablation_table_rows
summary = load_json(ROOT / "experiments/comparisons/ablation_chain.json")
ablation_val_loss_figure(summary).show()
'''),
        code(r'''
rows = ablation_table_rows(summary)
df = pd.DataFrame(rows)
seed_std = np.mean([summary["results"][c]["val_loss_std"] for c in summary["chain"]])
print(f"平均 seed 標準偏差（ノイズ床）= {seed_std:.4f} nats")
print(f"classical→modern の総変化 = {rows[-1]['delta_vs_base']:+.4f} nats")
df
'''),
        code(r'''
# 各ステップの変化を seed ノイズと並べて可視化（|Δ| が 2σ を超えるか）
steps = summary["chain"][1:]
deltas = [r["delta_vs_prev"] for r in rows[1:]]
fig = go.Figure(go.Bar(x=steps, y=deltas,
                       marker_color=["#d62728" if abs(d) > 2*seed_std else "#7f7f7f" for d in deltas]))
fig.add_hline(y=2*seed_std, line_dash="dot", line_color="#d62728", annotation_text="+2σ")
fig.add_hline(y=-2*seed_std, line_dash="dot", line_color="#2ca02c", annotation_text="−2σ")
fig.update_layout(title="1要素変更ごとの Δval loss（赤=|Δ|>2σ で有意の可能性）",
                  yaxis_title="Δ val loss vs 前ステップ", template="plotly_white", height=380)
fig.show()
print("灰色バー = seed 変動と区別できない（この規模・この予算では有意と言えない）")
'''),
        code(r'''
# パラメータ数と較正（top-1 confidence）も比較
fig = go.Figure()
fig.add_trace(go.Bar(x=summary["chain"], y=[summary["results"][c]["n_params"] for c in summary["chain"]],
                     name="params", marker_color="#1f77b4"))
fig.update_layout(title="各構成のパラメータ数（ほぼ一定＝容量ではなく構造の比較）",
                  yaxis_title="parameters", template="plotly_white", height=320)
fig.show()
for c in summary["chain"]:
    r = summary["results"][c]
    print(f'{c:10s} val {r["val_loss_mean"]:.3f}±{r["val_loss_std"]:.3f}  '
          f'top1_conf {r["top1_conf_mean"]:.3f}  entropy {r["entropy_mean"]:.2f}')
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation（実測）**: 変更ごとに効果量が大きく異なった。**RMSNorm は seed 変動内（Δ≈+0.007, σ≈0.045）で改善なし**。**RoPE は大きな改善（Δ≈−0.34 nats）で 2σ を大きく超える**。SwiGLU はさらに小改善（Δ≈−0.07, 有意）。**bias 無し（→Modern）は Δ≈+0.08 だが自身の σ≈0.10 内で判定不能**。classical→modern の総改善は約 −0.33 nats。
- **Interpretation**: 事前予想（「小規模では全変更が seed ノイズに埋もれる」）は**RoPE について明確に外れた** — この10M・<1epoch の設定でも RoPE の相対位置符号化は学習を実質的に助けた。RMSNorm は「改善」ではなく**同等性能での簡素化**（パラメータ削減・mean中心化除去）として価値がある。bias 無しは中立（大規模での正則化/速度利点は別途）。**改善のほぼ全ては RoPE 由来**であり、「Modern が一律に良い」という粗い物語は誤り。
- **Caveat**: 3 seeds は区間推定が粗く、特に bias 無しの符号は確定できない。<1epoch・単一コーパス・10M規模。RoPE の利点が長文脈外挿でさらに広がるかは未検証（follow-up）。速度差はこの短期 run では測定ノイズが大きく比較していない。この結論を Model L 規模へ外挿してはいけない（M4 で確認）。

## 確認問題
1. 「step 軸で改善」を主張する前に確認すべき軸は何か（NB12 と関連）。
2. Δloss が seed σ の範囲内のとき、正しい結論は「改善なし」か「判定不能」か。
3. RoPE の利点を顕在化させるには、どんな追加実験（独立変数）が必要か。

**次へ（M4）**: [19_scaling_analysis](19_scaling_analysis.ipynb) — S/M/L のスケーリング比較。
'''),
    ]


NOTEBOOKS = {
    "09_initialization_diagnostics.ipynb": nb09,
    "10_hardware_calibration.ipynb": nb10,
    "11_learning_rate_calibration.ipynb": nb11,
    "12_batch_size_calibration.ipynb": nb12,
    "18_architecture_ablation.ipynb": nb18,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    for name, fn in NOTEBOOKS.items():
        if args.only and args.only not in name:
            continue
        path = build_notebook(fn(), NB_DIR / name, execute=args.execute, cwd=REPO)
        print(f"built{' + executed' if args.execute else ''}: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
