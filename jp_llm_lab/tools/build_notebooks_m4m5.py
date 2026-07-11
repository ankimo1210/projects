"""Generate (and execute) Milestone 4-5 notebooks: 19 (scaling), 20-23.

Usage: uv run --no-sync python jp_llm_lab/tools/build_notebooks_m4m5.py --execute [--only 21]
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
M4 = 'L_RUN = ROOT / "experiments/runs/m4_model_l_modern_seed42"\nM5 = ROOT / "experiments/analysis_m5"\n'


def nb19() -> list:
    return [
        md(r'''
# 19. Scaling Analysis（spec §19）

## 学習目標
- 同一条件（コーパス・トークン数・アーキ・optimizer）で**サイズだけ**を変えたときの val loss を見る
- パラメータ数と性能・計算コストの trade-off を理解する
- 「大きいほど良い」の限界と前提（同一トークン予算）を意識する
'''),
        code(SETUP + M4),
        code(r'''
from jp_llm_lab.visualization.comparison import size_scaling_figure
scaling = load_json(ROOT / "experiments/comparisons/scaling.json")
pts = scaling["points"]
size_scaling_figure(pts).show()
pd.DataFrame(pts)[["name","n_params","val_loss","ppl","wallclock_sec"]]
'''),
        code(r'''
# パラメータ vs val loss。単調か？ 最小 loss のサイズは？
import numpy as np
best = min(pts, key=lambda p: p["val_loss"])
print(f"最小 val_loss は {best['name']}（{best['n_params']:,} params, val {best['val_loss']:.3f}）")
mono = all(pts[i]["val_loss"] >= pts[i+1]["val_loss"] for i in range(len(pts)-1))
print(f"単調減少か？ {mono}")
print(f"総トークン予算 {scaling['tokens_budget']:,}（全サイズ同一）— 大きいモデルほど token/param が不足")
for p in pts:
    print(f'  {p["name"]:3s} {p["n_params"]:>10,} params  val {p["val_loss"]:.3f}  '
          f'tokens/param={scaling["tokens_budget"]/p["n_params"]:.2f}')
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation（実測・非単調）**: xs→s→m では val loss が下がる（6.24→5.65→5.32）が、**最大の l（30M）は m（13.7M）より悪化**（上のセルが実測）。つまり「大きいほど良い」は**この固定トークン予算では成り立たなかった**。
- **Interpretation**: 全サイズ同じ ~6M トークンしか与えていないため、最大モデルは **token/param が不足（データ枯渇）** して十分に学習できていない。これは Chinchilla 的な「計算最適」の核心 — パラメータを増やすなら**それに見合うトークン数**が要る。実際 M4 の Model L は同じ構成を 100M トークン（16倍）で学習し val 3.51 に到達しており、データを与えれば大モデルが勝つことを別途示している。
- **Caveat**: 固定トークン予算・小規模・単一シード・500 step。最適トークン数調整（サイズごとに変える）はしていないので、これは「compute-optimal 曲線」ではなく「固定予算での断面」。100M+ への外挿不可。

## 確認問題
1. なぜ最大モデルが最良でないのか。「容量」と「トークン数」のどちらが律速か。
2. Model L が M4 で val 3.51 に到達できたのに、この曲線で l が 5.58 なのはなぜか。
3. 「大きいほど良い」を正しく主張するには、独立変数に何を加える必要があるか。

**次へ**: [20_probability_calibration](20_probability_calibration.ipynb)
'''),
    ]


def nb20() -> list:
    return [
        md(r'''
# 20. Probability Calibration（spec §15）

## 学習目標
- モデルの確信度が信頼できるか（confidence 0.7 の予測は約70%正しいか）を測る
- ECE（equal-width / equal-mass）・Brier・reliability diagram を読む
- Temperature Scaling を**calibration split で最適化し test split で評価**する（データ分離）

## 数式
次トークンの確信度 $c_t=\max_v p(v\mid x_{<t})$、正誤 $\mathbb{1}[\hat y_t=y_t]$。
ECE $=\sum_b \frac{n_b}{N}\,|\text{acc}_b-\text{conf}_b|$。Temperature scaling: $p_T=\text{softmax}(z/T)$。
'''),
        code(SETUP + M4),
        code(r'''
cal = load_json(M5 / "calibration.json")
print(f"test top-1 confidence(平均) {cal['test_top1_conf_mean']:.3f} vs 実精度 {cal['test_accuracy']:.3f}")
print(f"raw: NLL {cal['raw']['nll']:.3f}  ECE(width) {cal['raw']['ece_equal_width']:.4f}  Brier {cal['raw']['brier']:.4f}")
print(f"fitted T = {cal['fitted_T']:.3f}（calibration splitで最適化, test splitで評価）")
print(f"scaled: NLL {cal['temperature_scaled']['nll']:.3f}  ECE(mass) {cal['temperature_scaled']['ece_equal_mass']:.4f}")
print(f"accuracy raw {cal['raw']['accuracy']:.4f} vs scaled {cal['temperature_scaled']['accuracy']:.4f}（不変のはず）")
'''),
        code(r'''
# reliability diagram（equal-width）
bins = [b for b in cal["reliability_equal_width"] if b["n"] > 0]
fig = go.Figure()
fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode="lines", line=dict(dash="dash", color="#999"), name="完全較正"))
fig.add_trace(go.Scatter(x=[b["avg_conf"] for b in bins], y=[b["acc"] for b in bins],
                         mode="lines+markers", name="実測", line=dict(color="#1f77b4"),
                         marker=dict(size=[max(4, b["n"]**0.5/8) for b in bins])))
fig.update_layout(title="Reliability diagram（対角線=完全較正, 点サイズ=サンプル数）",
                  xaxis_title="平均確信度", yaxis_title="実精度", template="plotly_white", height=420)
fig.show()
'''),
        code(r'''
# raw vs temperature-scaled の指標比較
raw, sc = cal["raw"], cal["temperature_scaled"]
df = pd.DataFrame({
    "metric": ["NLL","ECE(equal-mass)","accuracy","entropy"],
    "raw": [raw["nll"], sc["ece_equal_mass"] if False else cal["raw"].get("ece_equal_width"), raw["accuracy"], raw["entropy"]],
    "temperature_scaled": [sc["nll"], sc["ece_equal_mass"], sc["accuracy"], sc["entropy"]],
})
df.round(4)
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: fitted T と ECE の値は上のセルが実測。Temperature scaling で NLL/ECE が変化し、**accuracy は不変**（argmax を変えないため）。
- **Interpretation**: T>1 なら「過信」、T<1 なら「過小」だった。温度スケーリングは分布の鋭さだけを調整する後処理で、順位や top-1 正解率は変えない。
- **Caveat（重要）**: 次トークン確率の較正は、**回答全体の事実的正しさや hallucination 率とは別物**。よく較正されたモデルでも「もっともらしい誤り」を出す（Model L の生成が示す通り）。T は calibration split で最適化し test で評価した（test で最適化してはいけない）。

**次へ**: [21_generation_anatomy](21_generation_anatomy.ipynb)
'''),
    ]


def nb21() -> list:
    return [
        md(r'''
# 21. Generation Anatomy（spec §16）

## 学習目標
- 生成を1トークンずつ観察する（確信度・エントロピー・top候補）
- 同一 logits に対し sampling 手法（greedy/temperature/top-k/top-p）だけを変えた差を見る
- 多様性指標（repetition率・distinct-n）で「反復」を定量化する
'''),
        code(SETUP + M4),
        code(r'''
ga = load_json(M5 / "generation_anatomy.json")
rows = ga["steps"][:15]
df = pd.DataFrame([{
    "step": r["index"], "chosen": r["chosen"], "prob": r["chosen_prob"], "entropy": r["entropy"],
    "top5": ", ".join(f'{t}:{p}' for t,p in r["top5"][:3])
} for r in rows])
print(f"prompt: {ga['prompt']} （greedy 生成の各ステップ）")
df
'''),
        code(r'''
# step ごとの確信度とエントロピー
steps = ga["steps"]
fig = go.Figure()
fig.add_trace(go.Scatter(x=[s["index"] for s in steps], y=[s["chosen_prob"] for s in steps],
                         name="選択トークン確率", line=dict(color="#1f77b4")))
fig.add_trace(go.Scatter(x=[s["index"] for s in steps], y=[s["entropy"] for s in steps],
                         name="エントロピー(nats)", yaxis="y2", line=dict(color="#ff7f0e")))
fig.update_layout(title="生成ステップごとの確信度とエントロピー", template="plotly_white", height=380,
                  xaxis_title="生成ステップ", yaxis=dict(title="P(選択)"),
                  yaxis2=dict(title="entropy", overlaying="y", side="right"))
fig.show()
'''),
        code(r'''
# sampling 手法スイープ: 多様性 vs 反復
sweep = ga["sampling_sweep"]
names = list(sweep)
fig = go.Figure()
fig.add_trace(go.Bar(x=names, y=[sweep[n]["metrics"]["repetition_rate"] for n in names], name="repetition率", marker_color="#d62728"))
fig.add_trace(go.Bar(x=names, y=[sweep[n]["metrics"]["distinct_2"] for n in names], name="distinct-2", marker_color="#2ca02c"))
fig.update_layout(barmode="group", title="sampling 手法別の反復率と多様性（同一モデル・同一prompt）",
                  template="plotly_white", height=380)
fig.show()
for n in ["greedy","temp0.7","temp1.5","top_p0.9"]:
    print(f'[{n}] {sweep[n]["sample"][:80]}')
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: greedy は反復率が高く distinct-2 が低い（ループ）。温度を上げ、top-k/top-p を使うと反復が下がり多様性が上がるが、高温では意味崩壊も増える。エントロピーが高いステップで「分岐」が起きている。
- **Interpretation**: 反復は決定則（greedy）とモデルの過信の相互作用で生じる小型LMの典型failure mode。sampling は同じ logits の**読み方**を変えるだけで、モデルの知識は変わらない。温度は多様性と一貫性の trade-off ノブ。
- **Caveat**: distinct-n が低い=悪い、ではない（箇条書きや定型文は正当に低い）。多様性指標は品質の代理にすぎない。1プロンプト系列の観察。

**次へ**: [22_memorization_analysis](22_memorization_analysis.ipynb)
'''),
    ]


def nb22() -> list:
    return [
        md(r'''
# 22. Memorization Analysis（spec §20）

## 学習目標
- 「学習データの再現」と「汎化」を区別する
- train文書の接頭辞からの greedy 継続が、val文書（対照）よりどれだけ原文に一致するかを測る
- 低い val loss だけでは汎化を証明できないことを理解する
'''),
        code(SETUP + M4),
        code(r'''
mem = load_json(M5 / "memorization.json")
tr, va = mem["train"], mem["validation"]
print(f"prefix {mem['prefix_len']} tokens → greedy continue {mem['continue_len']} tokens")
df = pd.DataFrame({
    "split": ["train (学習済み)","validation (未学習・対照)"],
    "mean_exact_match": [tr.get("mean_exact_match"), va.get("mean_exact_match")],
    "mean_lcs": [tr.get("mean_lcs"), va.get("mean_lcs")],
    "max_exact_match": [tr.get("max_exact_match"), va.get("max_exact_match")],
    "n": [tr.get("n"), va.get("n")],
})
df.round(2)
'''),
        code(r'''
fig = go.Figure()
fig.add_trace(go.Bar(x=["train","validation"],
                     y=[tr.get("mean_exact_match"), va.get("mean_exact_match")],
                     marker_color=["#d62728","#1f77b4"], name="mean exact-match"))
fig.update_layout(title="接頭辞からの greedy 継続が原文と一致した token 数（train vs val）",
                  yaxis_title="mean exact-match length", template="plotly_white", height=360)
fig.show()
gap = (tr.get("mean_exact_match") or 0) - (va.get("mean_exact_match") or 0)
print(f"train − val exact-match gap = {gap:.2f} tokens")
print(mem["note"])
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: train文書と val文書の exact-match 継続長は上のセルが実測。両者が近ければ暗記は弱く、train が大きく上回れば暗記のサイン。
- **Interpretation**: Model L は main を約0.9エポックしか見ておらず、逐語暗記は限定的なはず（train≈val なら汎化優位）。M1（45エポック）と対比すると、エポック数が暗記に効くことが分かる。
- **Caveat**: exact-match は暗記の一側面（近似再現は捉えない）。文書サンプルは各コーパスの先頭付近に限定。greedy 継続なので、サンプリングでは一致率が下がる。「低 val loss=汎化」は依然として証明にならない。

**次へ**: [23_sft_analysis](23_sft_analysis.ipynb)
'''),
    ]


def nb23() -> list:
    return [
        md(r'''
# 23. SFT Analysis（spec §21）

## 学習目標
- 事前学習モデルに簡易 Instruction SFT を施し、応答形式の変化を見る
- **assistant-only loss** と **full-sequence loss** を比較する
- 「SFTは知識を大量に増やすのではなく、主に出力形式・応答方針を変える」ことを結果から検討する

## 形式
```
<BOS> <USER> 指示 <ASSISTANT> 応答 <EOS>
```
assistant-only: 応答部分だけに loss。full-sequence: 全トークンに loss。
'''),
        code(SETUP + M4),
        code(r'''
sft = load_json(M5 / "sft.json")
print(f"SFT examples: {sft['sft_examples']}（dolly-15k-ja のclosed-book短文サブセット）")
for regime in ["assistant_only","full_sequence"]:
    c = sft["regimes"][regime]["curve"]
    print(f'{regime:16s} final SFT loss {sft["regimes"][regime]["final_loss"]:.3f}')
fig = go.Figure()
for regime, color in [("assistant_only","#2ca02c"),("full_sequence","#ff7f0e")]:
    c = sft["regimes"][regime]["curve"]
    fig.add_trace(go.Scatter(x=[p["step"] for p in c], y=[p["loss"] for p in c], name=regime, line=dict(color=color)))
fig.update_layout(title="SFT 学習曲線: assistant-only vs full-sequence",
                  xaxis_title="SFT step", yaxis_title="loss", template="plotly_white", height=380)
fig.show()
'''),
        code(r'''
# 事前学習(base) vs SFT の応答を同じ指示で比較
print("=== base（事前学習のみ, 指示に continuation するだけ）===")
for s in sft["base_pretrained_samples"]:
    print(f'Q: {s["instruction"]}')
    print(f'  → {s["completion"][:80]}')
print("\n=== assistant-only SFT ===")
for s in sft["regimes"]["assistant_only"]["samples"]:
    print(f'Q: {s["instruction"]}')
    print(f'  → {s["response"][:80]}')
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: base モデルは指示を「続けて書く」だけで応答形式になりにくい。SFT後は `<ASSISTANT>` 以降に応答らしい形で出力し、`<EOS>` で止まりやすくなる（上のセルが実測）。assistant-only と full-sequence は最終 loss の絶対値が異なる（full は prompt も含むので基準が違う）。
- **Interpretation**: SFT の主効果は**出力形式・応答方針**の獲得であり、新しい事実知識の大量獲得ではない（回答内容の正確さは base の知識に依存し、しばしば誤る）。assistant-only は prompt をモデル化しない分、応答生成に集中する。
- **Caveat**: 小モデル・少数例・短時間 SFT。応答は依然として事実誤りを含む（知識は事前学習由来）。2 regime の loss 値は損失対象が違うため直接比較できず、比較すべきは生成の質・形式。instruction-following の定量評価は本デモの範囲外。

**次へ**: [24_final_report](24_final_report.ipynb)
'''),
    ]


NOTEBOOKS = {
    "19_scaling_analysis.ipynb": nb19,
    "20_probability_calibration.ipynb": nb20,
    "21_generation_anatomy.ipynb": nb21,
    "22_memorization_analysis.ipynb": nb22,
    "23_sft_analysis.ipynb": nb23,
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
