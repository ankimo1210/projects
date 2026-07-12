"""Generate (and execute) the Milestone-2 notebooks: 02, 07, 08, 13-17.

Usage: uv run --no-sync python jp_llm_lab/tools/build_notebooks_m2.py --execute [--only 14]
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


def nb02() -> list:
    return [
        md(r'''
# 02. Corpus Exploration — スナップショットの解剖

## 学習目標
- 再現可能なコーパススナップショット（smoke/pilot/main/validation/calibration/test）の設計を理解する
- 文書長分布・文字種構成・日本語率・頻出文字を実測し、Web（FineWeb2）と Wikipedia の差を見る
- train/validation/calibration/test の分離がなぜ本質的かを説明できる

## スナップショット設計（spec §4.1）
1つの決定論的ストリーム走査で、フィルタ後の文書 index `i` に対し
`i%50==0→validation, ==1→calibration, ==2→test, それ以外→train pool` と割り当てる。
smoke⊂pilot⊂main は train pool の**先頭プレフィックス**なので、小実験は大実験の始点そのもの。
validation/calibration/test は**別文書**なので全学習集合と交わらない（暗記と汎化を分離できる）。
'''),
        code(SETUP),
        code(r'''
manifest = load_json(ROOT / "data/manifests/snapshots_v1.json")
stats = load_json(ROOT / "reports/figures/corpus_stats.json")

rows = []
for name, snap in manifest["snapshots"].items():
    if "n_chars" in snap:
        rows.append((name, snap.get("source",""), snap.get("n_docs","-"), snap["n_chars"]))
df = pd.DataFrame(rows, columns=["snapshot","source","n_docs","n_chars"]).sort_values("n_chars")
print("フィルタ設定:", manifest["filter"])
print("FineWeb2ja: streamed", manifest["sources"]["fineweb2ja"]["streamed_docs"],
      "kept", manifest["sources"]["fineweb2ja"]["kept_docs"],
      "filtered", manifest["sources"]["fineweb2ja"]["filtered_out"])
df
'''),
        code(r'''
# 文書長分布: FineWeb2 (pilot) vs Wikipedia
fig = go.Figure()
for name, color in [("pilot","#1f77b4"), ("wiki_pilot","#ff7f0e")]:
    lens = stats["snapshots"][name]["doc_len_hist"]
    fig.add_trace(go.Histogram(x=lens, name=name, opacity=0.6, marker_color=color, nbinsx=50))
fig.update_layout(barmode="overlay", title="文書長分布（文字数）: Web vs Wikipedia",
                  xaxis_title="文書の文字数", yaxis_title="文書数（サンプル）",
                  template="plotly_white", height=380)
fig.update_xaxes(range=[0, 6000])
fig.show()
for name in ["pilot","wiki_pilot"]:
    d = stats["snapshots"][name]["doc_len"]
    print(f'{name:11s} median {d["median"]:>6} chars  mean {d["mean"]:>7}  max {d["max"]:,}')
'''),
        code(r'''
# 文字種構成: Web vs Wikipedia
classes = ["hiragana","katakana","kanji","ascii_alnum","jp_punct","other","whitespace"]
fig = go.Figure()
for name, color in [("pilot","#1f77b4"),("wiki_pilot","#ff7f0e")]:
    frac = stats["snapshots"][name]["class_fraction"]
    fig.add_trace(go.Bar(x=classes, y=[frac.get(c,0) for c in classes], name=name, marker_color=color))
fig.update_layout(barmode="group", title="文字種構成: FineWeb2(pilot) vs Wikipedia",
                  yaxis_title="割合", template="plotly_white", height=380)
fig.show()
for name in ["pilot","wiki_pilot"]:
    print(f'{name:11s} 日本語率 {stats["snapshots"][name]["japanese_ratio_mean"]:.3f}')
'''),
        code(r'''
# 頻出文字 top20（pilot）
top = stats["snapshots"]["pilot"]["top_chars"][:20]
fig = go.Figure(go.Bar(x=[t["char"] for t in top], y=[t["count"] for t in top], marker_color="#1f77b4"))
fig.update_layout(title="FineWeb2(pilot) 頻出文字 top20", xaxis_title="文字", yaxis_title="出現数",
                  template="plotly_white", height=340)
fig.show()
'''),
        code(r'''
# token 単位の情報（chars/token = 圧縮率）
tk = manifest["tokenized"]
rows = [(k.replace("_bpe8k_v1",""), v["n_tokens"], v["chars_per_token"]) for k,v in tk.items()]
pd.DataFrame(rows, columns=["snapshot","n_tokens","chars_per_token"]).sort_values("n_tokens")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: Web(FineWeb2) は Wikipedia より文書長のばらつきが大きく、ASCII 比率が高い。日本語率は両者とも高い（フィルタ 0.5 以上）。BPE8K の圧縮率は約 1.6 文字/トークン。
- **Interpretation**: Web はノイズ（広告・定型文）と多様性を含み、Wikipedia は均質で百科事典的。学習コーパスの性格はモデルの生成傾向に直接効く（M4 で比較）。
- **Caveat**: 統計は各スナップショットの先頭数千文書のサンプル。フィルタ（min_japanese_ratio=0.5, 200–100k字）が分布を既に整形している。exact dedup は行ったが near-dup は未処理。

## 確認問題
1. なぜ validation を train の末尾から取るのではなく、別文書にすべきか。
2. smoke が pilot の先頭プレフィックスであることの再現性上の利点は。
3. 圧縮率 1.6 文字/トークンは、context 512 が「約何文字」に相当することを意味するか。

**次へ**: [07_architecture_visualization](07_architecture_visualization.ipynb)
'''),
    ]


def nb07() -> list:
    return [
        md(r'''
# 07. Architecture Visualization

## 学習目標
- Model M（Classical GPT, 10M params）の end-to-end データフローとブロック構造を図で把握する
- Classical と Modern の構成差（LayerNorm/RMSNorm, learned/RoPE, GELU/SwiGLU, bias）を対応づける

## Transformer block（residual stream 視点, spec §8.2）
```text
        ┌──────────────── residual stream ────────────────┐
 x ──┬─▶│ Norm → Self-Attention → (+) ─┬─▶ Norm → MLP → (+)│─▶
     └──┘                              └──────────────────┘
Classical: Norm=LayerNorm, pos=learned(加算), MLP=GELU(4d), bias=有
Modern   : Norm=RMSNorm,   pos=RoPE(attn内回転), MLP=SwiGLU(≈8d/3×3), bias=無
```
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT

cfg_c = ModelConfig(vocab_size=8192, d_model=320, n_heads=8, n_layers=6, context_len=512)
cfg_m = ModelConfig.modern(vocab_size=8192, d_model=320, n_heads=8, n_layers=6, context_len=512)
mc, mm = ClassicalGPT(cfg_c), ClassicalGPT(cfg_m)
print(f"Classical: {mc.param_breakdown()['total']:,} params")
print(f"Modern   : {mm.param_breakdown()['total']:,} params")
pd.DataFrame({
    "field": ["norm","pos","mlp","bias"],
    "classical": [cfg_c.norm, cfg_c.pos, cfg_c.mlp, cfg_c.bias],
    "modern": [cfg_m.norm, cfg_m.pos, cfg_m.mlp, cfg_m.bias],
})
'''),
        code(r'''
# モジュール木を表示（手書き実装が読めることを確認）
def tree(module, prefix="", depth=0, maxd=2):
    for name, child in module.named_children():
        n = sum(p.numel() for p in child.parameters())
        print(f"{'  '*depth}{name}: {child.__class__.__name__}  ({n:,} params)")
        if depth < maxd:
            tree(child, prefix, depth+1, maxd)
tree(mc, maxd=1)
print("--- block 0 ---")
tree(mc.blocks[0], maxd=1)
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: Classical と Modern はパラメータ数がほぼ同じ（SwiGLU の隠れ幅を 8d/3 に調整、RoPE は位置パラメータ0）。差はアーキテクチャのみ。
- **Interpretation**: これにより M3 のアブレーションが「容量」ではなく「構造」の効果を測れる（ceteris paribus）。
- **Caveat**: パラメータ一致は近似（±2%以内）。FLOPs はわずかに異なる（NB08）。

**次へ**: [08_parameter_and_flops_analysis](08_parameter_and_flops_analysis.ipynb)
'''),
    ]


def nb08() -> list:
    return [
        md(r'''
# 08. Parameter and FLOPs Analysis

## 学習目標
- パラメータ構成比と、学習 FLOPs の2つの見積り（厳密 vs 6ND 近似）の差を理解する
- 「パラメータ数 ≠ 計算量」を数値で確認する

## 数式
- 順伝播 FLOPs/token（context T, MAC=2FLOP）は各層で
  $\text{qkv}=6d^2,\ \text{attn}\approx 4Td,\ \text{proj}=2d^2,\ \text{MLP}\approx 16d^2$、
  加えて lm_head $=2dV$。
- 学習 ≈ 3× 順伝播（backward≈2×forward）。粗い近似 $C\approx 6ND$（N=params, D=tokens）。
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.models.flops import flops_per_token, training_flops
from jp_llm_lab.visualization.params_viz import param_breakdown_figure

cfg = ModelConfig(vocab_size=8192, d_model=320, n_heads=8, n_layers=6, context_len=512)
model = ClassicalGPT(cfg)
bd = model.param_breakdown()
param_breakdown_figure(bd).show()
'''),
        code(r'''
fp = flops_per_token(cfg, T=512)
print("forward FLOPs/token @T=512:", f'{fp["forward_per_token"]:,}')
print("  per-layer breakdown:", {k: f'{v:,}' for k,v in fp["per_layer"].items()})
print("  lm_head:", f'{fp["lm_head"]:,}')

tokens = 9_830_400  # Model M actual training tokens
tf = training_flops(cfg, tokens, n_params=bd["total"])
print(f"\ntraining FLOPs over {tokens:,} tokens:")
print(f'  exact-ish  : {tf["exact_estimate"]:.3e}')
print(f'  6·N·D approx: {tf["six_ND_approx"]:.3e}')
print(f'  ratio      : {tf["exact_estimate"]/tf["six_ND_approx"]:.2f}')
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: MLP と token embedding が支配的。厳密見積りと 6ND 近似は同オーダーだが一致はしない（lm_head と attention の T 項が近似では簡略化されるため）。
- **Interpretation**: 6ND は便利な目安だが、小語彙・短文脈では lm_head/attention の寄与で数十%ずれる。スケーリング則の議論では厳密側を使うべき場面がある。
- **Caveat**: FLOPs はハードウェアの実効効率（NB01の実測 TFLOPs）とは別物。実時間は kernel 効率・メモリ帯域に左右される。

**次へ**: [13_training_dynamics](13_training_dynamics.ipynb)
'''),
    ]


def nb13() -> list:
    return [
        md(r'''
# 13. Training Dynamics — Model M（BPE 8K, pilot 10M, <1 epoch）

## 学習目標
- 実コーパス・BPE・1エポック未満という M1 と異なる条件での学習曲線を読む
- train と validation が**別文書**のときのギャップの意味（汎化）を M1（同一小説）と対比する
- 横軸を step / tokens / 時間で切り替えて解釈する

## 前提
BPE 語彙 8192 なので一様分布損失は $\ln 8192 = 9.01$ nats。M1 の char（$\ln 2068=7.63$）とは単位が違うので、損失値の直接比較はできない（perplexity も同様）。
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.visualization import curves
records = read_jsonl(M2_RUN / "metrics.jsonl")
config = load_json(M2_RUN / "config.json")
summary = load_json(M2_RUN / "summary.json")
print(f'params {config["param_breakdown"]["total"]:,}  '
      f'tokens {summary["tokens_seen"]:,}  wallclock {summary["wallclock_sec"]:.1f}s')
curves.loss_curves_figure(records).show()
'''),
        code(r'''
evals = [r for r in records if r["type"]=="eval"]
ln_v = math.log(8192)
print(f"init val loss {evals[0]['val_eval']['loss']:.2f}  (uniform ln V = {ln_v:.2f})")
print(f"final train {evals[-1]['train_eval']['loss']:.2f}  val {evals[-1]['val_eval']['loss']:.2f}"
      f"  gap {evals[-1]['train_eval']['loss']-evals[-1]['val_eval']['loss']:+.3f}")
print(f"final val ppl {evals[-1]['val_eval']['ppl']:.0f}  top1_conf {evals[-1]['val_eval']['top1_conf']:.3f}")
'''),
        code(r'''
curves.lr_grad_figure(records, config["train_config"]["grad_clip"]).show()
curves.tokens_per_sec_figure(records).show()
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: init loss ≈ ln V。train と val がほぼ重なったまま低下し、M1 で見た train≪val の乖離が**ない**。1エポック未満なので同じ文書を繰り返し見ていない。
- **Interpretation**: train/val ギャップが小さい＝暗記していない＝損失改善は（この範囲では）汎化由来。これが M1 の「45エポックで暗記」との決定的な違い。ただし val loss 6.0 (ppl 400+) は絶対的には高く、10M params × 10M tokens では web テキストのモデル化は浅い。
- **Caveat**: BPE の loss/ppl は char と比較不可（単位が違う）。val は FineWeb2 の別文書で、話題ドリフトを含む。1シードのみ（M3 で複数シード）。

**次へ**: [14_attention_visualization](14_attention_visualization.ipynb)
'''),
    ]


def nb14() -> list:
    return [
        md(r'''
# 14. Attention Visualization（定量, spec §9）

## 学習目標
- attention を「説明」ではなく**測定対象**として扱い、エントロピー・距離・直前トークン率・head 類似度を定量化する
- 学習前後の変化を見る
- **head ablation（因果）** で「重み ≠ 因果的寄与」を実証する

## 数式
- head エントロピー $H_{l,h}=\overline{-\sum_j a_{tj}\log a_{tj}}$（行 t で平均、$j\le t$）
- 平均注意距離 $\overline{\sum_j a_{tj}\,|t-j|}$
- head ablation 効果 = その head の出力を0にしたときの loss 増加（因果量）
'''),
        code(SETUP),
        code(r'''
A = M2_RUN / "analysis"
stats = load_json(A / "attention_stats.json")
meta = load_json(A / "meta.json")
L, H = meta["n_layers"], meta["n_heads"]
ent_i = np.array(stats["init"]["entropy"]); ent_f = np.array(stats["final"]["entropy"])
print("probe:", stats["probe_text"])
print(f"平均エントロピー init {ent_i.mean():.2f} → final {ent_f.mean():.2f} nats")

fig = go.Figure()
fig.add_trace(go.Heatmap(z=ent_f, x=[f"H{h}" for h in range(H)], y=[f"L{l}" for l in range(L)],
                         colorscale="Viridis", colorbar_title="entropy"))
fig.update_layout(title="学習後 attention エントロピー（layer×head, 低い=選択的）",
                  template="plotly_white", height=360)
fig.update_yaxes(autorange="reversed")
fig.show()
'''),
        code(r'''
# 直前トークン率・平均距離を層別に
prev_f = np.array(stats["final"]["prev_token_ratio"]).mean(1)
dist_f = np.array(stats["final"]["distance"]).mean(1)
first_f = np.array(stats["final"]["first_token_ratio"]).mean(1)
fig = go.Figure()
fig.add_trace(go.Bar(x=[f"L{l}" for l in range(L)], y=prev_f, name="直前トークン率"))
fig.add_trace(go.Bar(x=[f"L{l}" for l in range(L)], y=first_f, name="先頭トークン率"))
fig.update_layout(barmode="group", title="層別 attention 集中先（final）",
                  yaxis_title="平均注意質量", template="plotly_white", height=340)
fig.show()
print("層別 平均注意距離:", [round(float(x),1) for x in dist_f], "tokens")
'''),
        code(r'''
# attention heatmap（実際のマップ, layer 0 と最終層）
maps = np.load(A / "attention_maps.npz", allow_pickle=True)
tokens = list(maps["tokens"])
from jp_llm_lab.visualization.attention_viz import attention_heatmap_grid
attention_heatmap_grid(torch.tensor(maps["layer0"]), tokens, "final model / layer 0", max_heads=4).show()
attention_heatmap_grid(torch.tensor(maps["layer_last"]), tokens, f"final model / layer {L-1}", max_heads=4).show()
'''),
        code(r'''
# head ablation: どの head が因果的に重要か
ha = np.array(load_json(A / "head_ablation.json")["head_ablation_delta_loss"])
fig = go.Figure(go.Heatmap(z=ha, x=[f"H{h}" for h in range(H)], y=[f"L{l}" for l in range(L)],
                           colorscale="Reds", colorbar_title="Δloss"))
fig.update_layout(title="head ablation: 各 head を0にしたときの loss 増加（因果的重要度）",
                  template="plotly_white", height=360)
fig.update_yaxes(autorange="reversed")
fig.show()
l,h = np.unravel_index(ha.argmax(), ha.shape)
print(f"最も重要な head: L{l}H{h} (Δloss {ha.max():.3f})")
print(f"その head のエントロピー {ent_f[l,h]:.2f}, 直前トークン率 {np.array(stats['final']['prev_token_ratio'])[l,h]:.3f}")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: 学習でエントロピーが低下し（選択性↑）、中間層が最も選択的。直前トークン率は 0.14–0.20、平均距離 2.6–3.1 トークンで局所的。head ablation では特定の head（上のセルが実測）だけが loss を大きく動かす。
- **Interpretation**: 多くの head は冗長（ablation の Δloss が小さい）で、少数の head が因果的に効く。エントロピーが低い head が必ずしも因果的に重要とは限らない点に注意（両者は別の量）。
- **Caveat（最重要）**: attention 重みマップは**説明ではない**。因果的重要度は ablation/patching で別途測る必要がある。すべて1つの probe 文・1シードの結果で、head の役割の一般化はできない。ablation は単純なゼロ化で、head 間の相互作用（冗長性）を過小評価しうる。

**次へ**: [15_embedding_analysis](15_embedding_analysis.ipynb)
'''),
    ]


def nb15() -> list:
    return [
        md(r'''
# 15. Embedding Analysis（spec §10）

## 学習目標
- token embedding のノルム・学習前後のドリフト・近傍・2次元投影を観察する
- 2次元投影の解釈上の危険性（情報損失・手法依存）を理解する
'''),
        code(SETUP),
        code(r'''
A = M2_RUN / "analysis"
emb = load_json(A / "embedding_stats.json")
pca = np.load(A / "embedding_pca.npz")
print(f"embedding norm: mean {emb['norm_mean']:.2f} ± {emb['norm_std']:.2f}")
print(f"init→final ドリフト: mean {emb['drift_mean']:.3f}, max {emb['drift_max']:.3f}")

# ノルム vs ドリフトの散布（頻出/稀トークンで挙動が違う）
fig = go.Figure(go.Scatter(x=pca["norms"], y=pca["drift"], mode="markers",
                           marker=dict(size=4, opacity=0.5, color=pca["drift"], colorscale="Viridis"),
                           text=[f"id {i}" for i in pca["ids"]]))
fig.update_layout(title="token embedding: ノルム vs 学習ドリフト",
                  xaxis_title="‖embedding‖ (final)", yaxis_title="‖final − init‖",
                  template="plotly_white", height=380)
fig.show()
'''),
        code(r'''
# PCA 2次元投影
fig = go.Figure(go.Scatter(x=pca["coords"][:,0], y=pca["coords"][:,1], mode="markers",
                           marker=dict(size=4, opacity=0.5, color=pca["norms"], colorscale="Plasma",
                                       colorbar_title="norm"),
                           text=[f"id {i}" for i in pca["ids"]]))
fig.update_layout(title="token embedding の PCA 2次元投影（色=ノルム）",
                  xaxis_title="PC1", yaxis_title="PC2", template="plotly_white", height=420)
fig.show()
'''),
        code(r'''
# 近傍トークン（学習済みモデルを読み込んで）
from jp_llm_lab.reporting.analysis_artifacts import _load_model, _load_tokenizer
from jp_llm_lab.instrumentation import embedding_analysis as ea
model = _load_model(sorted(M2_RUN.glob("checkpoints/*100pct*.pt"))[0])
tok = _load_tokenizer(M2_RUN)
for word in ["東京", "です", "年"]:
    tid = tok.encode(word)
    if tid:
        nbrs = ea.nearest_neighbors(model, tid[0], k=6)
        near = [tok.id_to_token(i) for i,_ in nbrs]
        print(f"{word!r}(id {tid[0]}) の近傍: {near}")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: 埋め込みノルムには幅があり、ドリフトはトークンにより大きく異なる（頻出トークンほど大きく動く傾向）。PCA 投影に緩いクラスタ構造が見える。
- **Interpretation**: よく出るトークンは勾配を多く受けるため init から大きく動く。近傍は表層的な共起を反映しがちで、意味的近さとは限らない。
- **Caveat**: PCA 2次元は高次元情報を大きく捨てる。クラスタの見え方は手法（PCA/UMAP/t-SNE）に依存し、距離を過度に解釈してはいけない。稀トークンの近傍は init 由来のノイズを含む。

**次へ**: [16_residual_stream_analysis](16_residual_stream_analysis.ipynb)
'''),
    ]


def nb16() -> list:
    return [
        md(r'''
# 16. Residual Stream and Activation Analysis（spec §11）

## 学習目標
- forward hook で記録した各層の活性 RMS を層×チェックポイントで俯瞰する
- 各ブロックが residual stream をどれだけ書き換えるか $r_l=\|\Delta h_l\|/\|h_l\|$ を測る
- 活性の異常（爆発/消失/外れ値チャネル）検出の観点を知る
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.visualization import curves
records = read_jsonl(M2_RUN / "metrics.jsonl")
curves.activation_rms_heatmap(records).show()
'''),
        code(r'''
# branch別 residual 書き込み比 r_l を最終モデルの forward trace から
from jp_llm_lab.reporting.analysis_artifacts import _load_model, _load_tokenizer
from jp_llm_lab.instrumentation.activation_stats import residual_update_ratios
model = _load_model(sorted(M2_RUN.glob("checkpoints/*100pct*.pt"))[0])
tok = _load_tokenizer(M2_RUN)
ids = torch.tensor([tok.encode("日本の首都は東京です。私はその街に住んでいます。")[:64]])
trace = model.trace_forward(ids)
ratios = residual_update_ratios(trace, n_layers=model.cfg.n_layers)
names = list(ratios)
fig = go.Figure(go.Bar(x=names, y=[ratios[n] for n in names],
                       marker_color=["#2ca02c" if "attn" in n else "#ff7f0e" for n in names]))
fig.update_layout(title="branch別 residual 書き込み比 r_l=‖Δh‖/‖h‖（緑=attn, 橙=mlp）",
                  yaxis_title="r_l", template="plotly_white", height=360)
fig.show()
'''),
        code(r'''
# 各観測点の活性統計（最終eval）
evals = [r for r in records if r["type"]=="eval"]
last = evals[-1]["activation_stats"]
rows = [(k, v["rms"], v["kurtosis"], v["absmax"], v["outlier_frac"]) for k,v in last.items()]
df = pd.DataFrame(rows, columns=["point","rms","kurtosis","absmax","outlier_frac"])
print("kurtosis>3 は重い裾（外れ値チャネルの兆候）。NaN/Inf:", evals[-1]["nonfinite"] or "なし")
df.round(3)
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: residual RMS は層とともに増加（pre-LN の蓄積）。$r_l$ は MLP branch が attention branch より大きい層が多い。NaN/Inf なし。一部の点で kurtosis>3（裾が重い）。
- **Interpretation**: 各ブロックは residual stream を「置換」ではなく「小さく加算」しており、深い層ほど絶対値が育つ。重い裾は特定チャネルに大きな値が乗る既知の現象（outlier feature）で、量子化などで問題になりうる。
- **Caveat**: $r_l$ は1文・1シードの値。RMS は分布の1統計にすぎず、kurtosis/absmax と併読が必要。

**次へ**: [17_gradient_analysis](17_gradient_analysis.ipynb)
'''),
    ]


def nb17() -> list:
    return [
        md(r'''
# 17. Gradient and Optimization Analysis（spec §12）

## 学習目標
- パラメータ群別の勾配ノルム・update-to-weight 比を時系列で追う
- 損失悪化時に「どの群が不安定か」を切り分ける観点を得る

## 数式
$u_g = \dfrac{\|\Delta W_g\|_2}{\|W_g\|_2}$（群 g の1ステップ更新の相対量）。健全な AdamW では概ね $10^{-3}$ 前後。
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.visualization import curves
records = read_jsonl(M2_RUN / "metrics.jsonl")
curves.update_ratio_figure(records).show()
curves.grad_norm_by_group_figure(records).show()
'''),
        code(r'''
trains = [r for r in records if r["type"]=="train" and "grad_norms" in r]
last = trains[-1]["grad_norms"]
rows = [(g, last[g]) for g in sorted(last, key=lambda x:-last[x])]
print("最終step 群別勾配ノルム:")
for g, n in rows:
    print(f"  {g:12s} {n:.4f}")
clip_rate = sum(r["clip_hit"] for r in [r for r in records if r["type"]=="train"]) / len([r for r in records if r["type"]=="train"])
print(f"\nクリップ発動率 {clip_rate:.0%}")
'''),
        md(r'''
## Observation / Interpretation / Caveat
- **Observation**: update 比は全群で 1e-3 近傍に収まり、cosine 減衰とともに低下。token_emb と mlp の勾配ノルムが大きい。クリップは主に序盤。
- **Interpretation**: 単一 lr で全群が妥当に更新されている（群別 lr 不要）。埋め込みは全トークンの誤差を直接受けるため勾配が大きいのは自然。
- **Caveat**: この run は安定していたため「不安定時の診断」は実演できていない。M3 の LR range test（NB11）で意図的に不安定化させ、この計測器で追跡する。

**次へ（M3）**: [09_initialization_diagnostics](09_initialization_diagnostics.ipynb) 以降で校正実験に進む。
'''),
    ]


NOTEBOOKS = {
    "02_corpus_exploration.ipynb": nb02,
    "07_architecture_visualization.ipynb": nb07,
    "08_parameter_and_flops_analysis.ipynb": nb08,
    "13_training_dynamics.ipynb": nb13,
    "14_attention_visualization.ipynb": nb14,
    "15_embedding_analysis.ipynb": nb15,
    "16_residual_stream_analysis.ipynb": nb16,
    "17_gradient_analysis.ipynb": nb17,
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
