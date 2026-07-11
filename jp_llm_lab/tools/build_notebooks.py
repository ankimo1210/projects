"""Generate (and execute) the Milestone-1 notebooks.

Usage:
  uv run --no-sync python jp_llm_lab/tools/build_notebooks.py --execute
  uv run --no-sync python jp_llm_lab/tools/build_notebooks.py --execute --only 05
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nbkit import build_notebook, code, md

REPO = Path(__file__).resolve().parents[1]
NB_DIR = REPO / "notebooks"

SETUP = r'''
# 共通セットアップ（全ノートブック同一）
import warnings
warnings.filterwarnings("ignore")

import math
import time
from collections import Counter

import numpy as np
import pandas as pd
import torch
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "plotly_mimetype"

from jp_llm_lab.utils.io import repo_root, load_json, read_jsonl
ROOT = repo_root()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"ROOT={ROOT}")
print(f"device={DEVICE}, torch={torch.__version__}")
'''


# --------------------------------------------------------------------- NB00
def nb00() -> list:
    return [
        md(r'''
# 00. Project Overview — jp_llm_lab

## このプロジェクトは何か

日本語中心の**小型 Decoder-only Transformer** を PyTorch でゼロから実装し、
事前学習 → 計測 → 統制実験 → 較正 → SFT までを行う**教育用ラボ**です。

> **This project is not designed to build a competitive large language model.**
> 目的は高性能ではなく、言語モデルの内部機構・学習ダイナミクス・アーキテクチャの
> トレードオフ・確率較正・限界を**観測可能にし、理解すること**です。

設計原則は **Visualization-first**：主要な処理すべてに
「数式 → 小さな具体例 → tensor shape 追跡 → 可視化 → 実測 → 解釈 → 注意点」を付けます。
'''),
        md(r'''
## 学習の地図（この教材で答えられるようになる問い）

| 問い | どこで扱うか |
|---|---|
| 言語モデルは何を学習しているか | NB04 (bigram) → NB13 (training dynamics) |
| 次token予測はどう行われるか | NB06 (forward pass), NB21 (generation anatomy) |
| tensorはどう変換されるか | NB06 (shape trace) |
| Attention/MLP/Residual/Normは何をするか | NB05, NB14, NB16 |
| 学習中にパラメータ・勾配・活性はどう変わるか | NB13, NB16, NB17 |
| モデルサイズ・構成の違いは何を変えるか | NB18 (ablation), NB19 (scaling) |
| 学習率・初期化・バッチサイズの影響 | NB09–NB12 |
| Loss/Perplexity/Calibrationの読み方 | NB13, NB20 |
| 事前学習とSFTの違い | NB23 |
| 「もっともらしい生成」と「本当の能力」の区別 | NB22 (memorization), NB19 |

**Milestone 1（本リリース）では NB00, 01, 03, 04, 05, 06 が完成済み**です。
NB02（コーパス探索）と NB07 以降は Milestone 2+ で追加されます。
'''),
        md(r'''
## End-to-end データフロー（spec §8.1）

```text
Raw text 「私はその人を…」
  → Tokenizer（M1: 文字単位 / M2: BPE）
  → Token IDs                 [B, T]
  → Embeddings（token + position） [B, T, D]
  → Transformer blocks × N
      residual stream
        ├─ LayerNorm → Self-Attention → (+)
        └─ LayerNorm → MLP            → (+)
  → 最終 LayerNorm
  → LM head（token embeddingと重み共有）
  → Logits                    [B, T, V]
  → Softmax → 次token分布
  → Sampling（greedy / temperature / top-k / top-p）
  → 生成テキスト
```
'''),
        code(SETUP),
        code(r'''
# 環境の一言サマリ（詳細は NB01）
import jp_llm_lab
from jp_llm_lab.utils.env import collect_env_report
r = collect_env_report()
print(f"jp_llm_lab v{jp_llm_lab.__version__}")
print(f"GPU: {r.gpu_name} ({r.vram_gb} GB, BF16={r.bf16_supported})")
print(f"CUDA: {r.cuda_version} / SDPA backends: {r.sdpa_backends}")
'''),
        md(r'''
## リポジトリの歩き方

```text
jp_llm_lab/
├── src/jp_llm_lab/     # すべて手書きの実装（attention・学習ループ・計測フック…）
├── scripts/            # 実験の実行入口（configから再実行可能）
├── configs/            # 実験設定 YAML
├── experiments/runs/   # 実行成果物（metrics.jsonl / checkpoints / samples）
├── notebooks/          # 本教材（tools/build_notebooks.py から生成）
├── reports/html/       # 静的HTMLレポート（make report）
└── tests/              # 44 tests（因果マスク・SDPA一致・過学習 等）
```

### Milestone 1 の再現手順

```bash
make -C jp_llm_lab corpus       # 青空文庫サンプル取得
make -C jp_llm_lab test         # テスト
make -C jp_llm_lab train-bigram # bigram ベースライン
make -C jp_llm_lab train-smoke  # Model S (1.1M) 学習 (~40秒 on RTX 5080)
make -C jp_llm_lab bench        # explicit vs SDPA
make -C jp_llm_lab notebooks    # 本ノートブック群の再生成・実行
make -C jp_llm_lab report       # HTMLレポート
```
'''),
        md(r'''
## 測定の信頼性ポリシー

- **実測と例示を混ぜない**: 全run は `runmeta.json`（git hash・パッケージ版・GPU・時刻）と
  `config.json`（seed・ハイパーパラメータ）を保存。コーパスは `data/manifests/` に
  URL・ライセンス・sha256 を記録し、合成フォールバック使用時は `synthetic: true` を明記。
- **再学習なしで分析可能**: ノートブックとレポートは保存済み成果物のみを読む。
- **仮説に合わない結果もそのまま**: 例として、レポートの attention 分析では
  「文頭への注意が増える」という事前予想が**成り立たなかった**ことを数値ごと記載している。

## 確認問題

1. このプロジェクトの「完了」は何で定義されるか（性能か、観測可能性か）。
2. `experiments/runs/` に保存される3種類のレコード（train/eval/checkpoint）の役割は。
3. なぜ Milestone 1 では 30M モデルではなく 1M モデルから始めるのか。

**次へ**: [01_environment_and_gpu](01_environment_and_gpu.ipynb) — ハードウェアを実測し、設定を根拠づける。
'''),
    ]


# --------------------------------------------------------------------- NB01
def nb01() -> list:
    return [
        md(r'''
# 01. Environment and GPU

## 学習目標

- 学習に使うハードウェア（GPU・VRAM・BF16対応・SDPAバックエンド）を**実測で**把握する
- 「なぜ BF16 か」「なぜ SDPA か」を説明できるようになる
- ハードウェアから初期設定（micro batch / grad accum / モデルサイズ）を導く**根拠**を知る

## 前提知識

浮動小数点数が「符号・指数・仮数」で表現されること。
'''),
        code(SETUP),
        code(r'''
from dataclasses import asdict
from jp_llm_lab.utils.env import collect_env_report, recommend_setup

report = collect_env_report()
pd.Series(asdict(report)).to_frame("value")
'''),
        md(r'''
## 数値形式: なぜ BF16 か

| 形式 | 符号 | 指数 | 仮数 | 表現範囲 | 相対精度 |
|---|---|---|---|---|---|
| FP32 | 1 | 8 | 23 | ~1e±38 | ~7桁 |
| **BF16** | 1 | **8** | 7 | **~1e±38（FP32と同じ）** | ~2-3桁 |
| FP16 | 1 | 5 | 10 | ~6e±4 | ~3桁 |

- BF16 は**指数部が FP32 と同じ8bit** → 勾配のダイナミックレンジがそのまま収まり、
  FP16 で必要な loss scaling が不要。
- 仮数が7bitしかない粗さは、勾配ノイズ（ミニバッチ由来）より小さいオーダーであることが多く、
  学習品質への影響は限定的（これは M3 で fp32 と実測比較する）。
- メモリ半減・Tensor Core の高速パスが使える。
'''),
        code(r'''
setup = recommend_setup(report)
pd.Series(setup.as_dict()).to_frame("recommendation")
'''),
        md(r'''
### 推奨ロジック（`recommend_setup` の中身）

1. **dtype**: CUDA + BF16対応 → `bf16`、それ以外は `fp32`
2. **attn_impl**: 学習は SDPA（fused kernel）。教育・分析用に explicit 実装が常に併存（出力一致はテスト済み）
3. **micro_batch**: VRAM 段階表（<6GB / <12GB / ≥12GB）。活性メモリは概ね `n_layers·T·d_model` に比例するためモデルサイズ別
4. **grad_accum**: `ceil(目標トークン数 ÷ (micro_batch × context_len))` — マシンが違っても**1ステップあたりのトークン数**を揃える

**Caveat**: これは粗い事前推定。実測最適点は M3 §14.1 のハードウェア校正で決める。
'''),
        code(r'''
# 行列積のマイクロベンチ: fp32 vs bf16（Tensor Coreの効果を体感する）
def matmul_tflops(dtype, n=4096, reps=10):
    if DEVICE == "cpu":
        n, reps = 1024, 3
    a = torch.randn(n, n, device=DEVICE, dtype=dtype)
    b = torch.randn(n, n, device=DEVICE, dtype=dtype)
    for _ in range(3):
        a @ b  # warmup
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(reps):
        a @ b
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / reps
    return 2 * n**3 / dt / 1e12

rows = [("fp32", matmul_tflops(torch.float32))]
if DEVICE == "cuda":
    rows.append(("bf16", matmul_tflops(torch.bfloat16)))
df = pd.DataFrame(rows, columns=["dtype", "TFLOPs"])
if len(rows) == 2:
    print(f"bf16 は fp32 の ×{rows[1][1]/rows[0][1]:.1f}（4096×4096 行列積, 中央値でなく平均）")
fig = go.Figure(go.Bar(x=df["dtype"], y=df["TFLOPs"], marker_color=["#1f77b4", "#2ca02c"][:len(df)]))
fig.update_layout(title="行列積スループット（大きいほど速い）", yaxis_title="TFLOPs",
                  template="plotly_white", height=360)
fig.show()
df
'''),
        md(r'''
## 読み方と注意

- **Observation**: 上のセルの実測値がそのまま観察結果（このノートブックは実行のたびに再計測する）。
  RTX 5080 では bf16 が fp32 の数倍になるはず。
- **Interpretation**: 差は Tensor Core の bf16 パスによる。ただし**学習全体がこの倍率で速くなるわけではない**
  — 小さいモデルではカーネル起動・データ供給・評価がボトルネックになる（NB13で実測）。
- **Caveat**: この数値は行列サイズ・電力状態・ドライバに依存する。「GPUの公称TFLOPs」との差は
  実行効率であり異常ではない。

## 確認問題

1. FP16 ではなく BF16 を使う根拠を「指数部」という語を使って説明せよ。
2. `grad_accum` を増やしたとき、1 optimizer step あたりのトークン数はどうなるか。
3. VRAM が半分のマシンで同じ実験を再現するには、何を変えて何を固定すべきか。

**次へ**: [03_tokenizer_anatomy](03_tokenizer_anatomy.ipynb)（NB02 コーパス探索は M2 で追加）
'''),
    ]


# --------------------------------------------------------------------- NB03
def nb03() -> list:
    return [
        md(r'''
# 03. Tokenizer Anatomy — Part 1: 文字トークナイザ

## 学習目標

- テキスト ↔ token ID 列の対応を**1文字単位で完全に**追えるようになる
- `decode(encode(x)) == x`（round-trip）の意味と、それが破れる唯一の条件（未知文字）を知る
- 文字トークナイザの限界（語彙サイズ・系列長・被覆率）を実測し、BPE（M2）の動機を得る

## 数式

語彙 $\mathcal{V} = \{\text{特殊トークン6種}\} \cup \{\text{学習テキストの全文字}\}$ に対し

$$\operatorname{encode}: \text{str} \to \mathbb{N}^*, \quad \operatorname{decode}: \mathbb{N}^* \to \text{str}$$

$$\operatorname{decode}(\operatorname{encode}(x)) = x \quad (\forall x: \text{全文字が } \mathcal{V} \text{ 内})$$

特殊トークンは固定ID: `<PAD>`=0, `<UNK>`=1, `<BOS>`=2, `<EOS>`=3, `<USER>`=4, `<ASSISTANT>`=5
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.data.sample_corpus import load_sample_corpus
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer

corpus = load_sample_corpus("kokoro")  # 夏目漱石『こころ』（青空文庫・パブリックドメイン）
tok = CharTokenizer.train([corpus])
print(f"コーパス: {len(corpus):,} 文字")
print(f"語彙サイズ: {tok.vocab_size:,}（特殊6 + 文字 {tok.vocab_size - 6:,} 種）")
print(f"特殊トークン: {tok.itos[:6]}")
print(f"文字部分の先頭20: {tok.itos[6:26]}")
'''),
        code(r'''
# 手計算例: 1文字ずつ表引きするだけ
s = "私は猫である。"
ids = tok.encode(s)
pd.DataFrame({"char": list(s), "token_id": ids})
'''),
        code(r'''
# round-trip 恒等式（テストでも保証済み）と、破れる唯一のケース
assert tok.decode(tok.encode(corpus)) == corpus
print("decode(encode(corpus)) == corpus ✓")

print("未知文字の例:", tok.encode("𠮷"), "→", tok.decode(tok.encode("𠮷")))  # <UNK>=1
'''),
        code(r'''
# 頻出文字 top30
freq = Counter(corpus)
top = freq.most_common(30)
labels = [c.replace("\n", "⏎").replace("　", "␣") for c, _ in top]
fig = go.Figure(go.Bar(x=labels, y=[n for _, n in top], marker_color="#1f77b4"))
fig.update_layout(title="『こころ』頻出文字 top30", xaxis_title="文字", yaxis_title="出現回数",
                  template="plotly_white", height=380)
fig.show()
'''),
        code(r'''
# 文字種構成（ひらがな/カタカナ/漢字/英数字/記号）
def char_class(ch):
    o = ord(ch)
    if 0x3040 <= o <= 0x309F:
        return "ひらがな"
    if 0x30A0 <= o <= 0x30FF:
        return "カタカナ"
    if 0x4E00 <= o <= 0x9FFF:
        return "漢字"
    if ch.isascii() and ch.isalnum():
        return "英数字"
    return "記号・空白・その他"

occ = Counter(char_class(c) for c in corpus)                # 出現数ベース
uniq = Counter(char_class(c) for c in set(corpus))          # 語彙ベース
df = pd.DataFrame({"出現数": occ, "語彙数（異なり）": uniq}).fillna(0).astype(int)
fig = go.Figure()
for col in df.columns:
    fig.add_trace(go.Bar(x=df.index, y=df[col] / df[col].sum(), name=col))
fig.update_layout(barmode="group", title="文字種構成: 出現ベース vs 語彙ベース",
                  yaxis_title="割合", template="plotly_white", height=380)
fig.show()
df
'''),
        md(r'''
**How to read**: 出現ベース（テキストの何%か）と語彙ベース（異なり文字の何%か）は大きく食い違う。
ひらがなは**出現**の大半を占めるが種類は~80。漢字は逆に**語彙**の大半を占める。
これが「文字トークナイザの語彙サイズは漢字の異なり数で決まる」という構造。
'''),
        code(r'''
# 被覆率（OOV）: 『こころ』で学習した語彙で『走れメロス』を符号化すると？
merosu = load_sample_corpus("hashire_merosu")
ids_m = tok.encode(merosu)
unk_rate = sum(1 for i in ids_m if i == 1) / len(ids_m)
unk_chars = sorted({c for c in set(merosu) if c not in tok.stoi})
print(f"『走れメロス』{len(merosu):,} 文字中 UNK率 = {unk_rate:.2%}")
print(f"未知文字 {len(unk_chars)} 種（例）: {unk_chars[:30]}")
'''),
        md(r'''
## Observation / Interpretation / Caveat

- **Observation**: 語彙 ~2,000 のうち漢字が大半。別コーパス（メロス）では未知文字が発生し、
  UNK は**復元不可能な情報損失**になる（round-trip が破れる）。
- **Interpretation**: 文字トークナイザは (1) 実装が単純で対応が完全に追える、
  (2) 系列長=文字数で長い、(3) 未知**文字**に弱い。サブワード（BPE, M2）は
  バイト/文字の結合で語彙を「よく出る並び」に割り当て、この3点のトレードオフを変える。
- **Caveat**: UNK率はコーパスの組に依存する。「日本語一般」の値ではない。

## 確認問題

1. `<UNK>` が存在するのに round-trip テストが成立するのはなぜか（どんな入力に対する保証か）。
2. 語彙を『こころ』+『メロス』の和集合にすると何が改善し、何が解決しないか。
3. 文字トークナイザで context 256 は「何文字」か。BPE（1トークン≈2-3文字）では何文字相当か。

**次へ**: [04_bigram_language_model](04_bigram_language_model.ipynb)
'''),
    ]


# --------------------------------------------------------------------- NB04
def nb04() -> list:
    return [
        md(r'''
# 04. Bigram Language Model — 最小の言語モデル

## 学習目標

- 「言語モデル＝次トークンの条件付き分布」を最小構成で確認する
- **カウント（閉形式MLE）とSGD学習が同じ解に到達する**ことを実測で見る
- 平滑化ハイパーパラメータ α が損失を大きく動かすことを知る

## 数式

bigram モデルは直前1トークンだけで次を予測する:

$$P(x_{t+1}=j \mid x_t=i) = p_{ij}, \qquad
\hat p_{ij} = \frac{c_{ij} + \alpha}{\sum_k c_{ik} + \alpha V}$$

$c_{ij}$ は訓練データ中の遷移 $i \to j$ の回数、$\alpha$ は加算平滑化（未観測ペアに残す確率質量）。
損失は次トークンの負対数尤度（nats/token）。**一様分布なら $\ln V$**。
'''),
        md(r'''
## 手計算例

コーパス「あいあいう」（遷移: あ→い, い→あ, あ→い, い→う）、語彙 {あ,い,う}, α=0 の場合:

| from\to | あ | い | う | 行和 |
|---|---|---|---|---|
| あ | 0 | 2 | 0 | 2 |
| い | 1 | 0 | 1 | 2 |
| う | 0 | 0 | 0 | 0 |

→ $P(\text{い}\mid\text{あ}) = 2/2 = 1.0$、$P(\text{あ}\mid\text{い}) = P(\text{う}\mid\text{い}) = 0.5$。
「う」の行は観測ゼロ → α>0 が無いと定義できない（平滑化の必然性）。
'''),
        code(SETUP),
        code(r'''
# 実行済み run の成果物を読む（再学習不要）
BRUN = ROOT / "experiments/runs/m1_bigram_char_seed42"
assert BRUN.exists(), "先に `make -C jp_llm_lab train-bigram` を実行してください"
recs = read_jsonl(BRUN / "metrics.jsonl")
summary = load_json(BRUN / "summary.json")

fig = go.Figure()
fig.add_trace(go.Scatter(x=[r["step"] for r in recs], y=[r["val_loss"] for r in recs],
                         name="neural bigram (val)", line=dict(color="#ff7f0e")))
fig.add_hline(y=summary["count"]["val_loss"], line_dash="dash", line_color="#7f7f7f",
              annotation_text=f"count model (val {summary['count']['val_loss']:.3f})")
fig.add_hline(y=summary["uniform_loss_reference"], line_dash="dot", line_color="#bbb",
              annotation_text=f"uniform ln V = {summary['uniform_loss_reference']:.2f}")
fig.update_layout(title="neural bigram は count モデル（閉形式解）に収束する",
                  xaxis_title="SGD step", yaxis_title="val loss (nats/token)",
                  template="plotly_white", height=420)
fig.show()
print(f"neural val = {summary['neural']['val_loss']:.4f} / count val = {summary['count']['val_loss']:.4f}")
'''),
        code(r'''
# 遷移確率行列を「見る」: 頻出30文字 × 頻出30文字
from jp_llm_lab.data.sample_corpus import load_sample_corpus
from jp_llm_lab.models.bigram import CountBigramLM
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer

corpus = load_sample_corpus("kokoro")
tok = CharTokenizer.train([corpus])
ids = torch.tensor(tok.encode(corpus), dtype=torch.long)
cm = CountBigramLM(tok.vocab_size, alpha=0.05).fit(ids)

top_ids = [i for i, _ in Counter(ids.tolist()).most_common(30)]
labels = [tok.id_to_token(i).replace("\n", "⏎").replace("　", "␣") for i in top_ids]
sub = cm.log_probs.exp()[top_ids][:, top_ids]
fig = go.Figure(go.Heatmap(z=sub.tolist(), x=labels, y=labels, colorscale="Blues",
                           hovertemplate="P(%{x} | %{y}) = %{z:.3f}<extra></extra>"))
fig.update_layout(title="bigram 遷移確率（行=現在の文字, 列=次の文字）",
                  template="plotly_white", height=560)
fig.update_yaxes(autorange="reversed")
fig.show()
'''),
        md(r'''
**How to read**: 行「し」で「た」が明るい＝「し→た」が高確率、のように読む。
「。」の行は「⏎（改行）」や「」」が明るいはず — 句点の後の統計が既に captureされている。
'''),
        code(r'''
# 平滑化 α の感度（summary に保存済みのスイープ）
sweep = summary["alpha_sweep_val_loss"]
fig = go.Figure(go.Scatter(x=[float(a) for a in sweep], y=list(sweep.values()),
                           mode="lines+markers", line=dict(color="#7f7f7f")))
fig.add_hline(y=summary["neural"]["val_loss"], line_dash="dash", line_color="#ff7f0e",
              annotation_text="neural bigram")
fig.update_xaxes(type="log", title="α (log)")
fig.update_layout(title="加算平滑化 α と検証損失", yaxis_title="val loss (nats/token)",
                  template="plotly_white", height=400)
fig.show()
'''),
        code(r'''
# bigram からのサンプリング — 「1文字先の統計」だけでどこまで日本語に見えるか
g = torch.Generator().manual_seed(0)
sample_ids = cm.generate(tok.encode("私")[0], 120, g)
print(tok.decode(sample_ids))
'''),
        md(r'''
## Observation / Interpretation / Caveat

- **Observation**: neural bigram の val loss は count モデルとほぼ一致（差 ~0.05 nats は平滑化方式の差）。
  α は 1桁違うだけで val loss を大きく動かし、α=0.5 は明確に悪い（α·V ≈ 1000 擬似カウントが実カウント≈73/行を圧倒）。
  サンプルは局所的には日本語らしいが、文としては即座に破綻する。
- **Interpretation**: 「ニューラル＝賢い」のではなく、**表現力が同じなら学習法が違っても同じ解**。
  Transformer の価値は最適化ではなく「1トークンより長い文脈を条件にできる」表現力にある。
- **Caveat**: この一致は bigram という凸な問題だから成立する。深いモデルでは
  最適化の経路・初期化が解に影響する（M3 §14.3）。

## 確認問題

1. 一様分布の損失が $\ln V$ になることを導け。
2. α→∞ のとき count モデルはどんな分布に近づくか。
3. bigram が原理的に表現できない日本語の現象を1つ挙げよ（例: 係り受け）。

**次へ**: [05_attention_from_scratch](05_attention_from_scratch.ipynb) — 文脈を「選んで」参照する仕組み。
'''),
    ]


# --------------------------------------------------------------------- NB05
def nb05() -> list:
    return [
        md(r'''
# 05. Attention from Scratch

## 学習目標

- causal self-attention を**手計算**（3トークン・2次元）で1ステップずつ再現する
- 自作 explicit 実装と PyTorch SDPA の**出力が一致**することを確認する（速度は別物）
- attention 重みの性質（行和=1・未来ゼロ・エントロピー）を測る

## 数式（1 head 分）

$$Q = XW_Q,\quad K = XW_K,\quad V = XW_V \qquad X \in \mathbb{R}^{T \times d}$$

$$\text{scores} = \frac{QK^\top}{\sqrt{d_h}} \in \mathbb{R}^{T\times T},\qquad
\text{scores}_{tj} \leftarrow -\infty \;\; (j > t \text{: causal mask})$$

$$A = \operatorname{softmax}_{\text{row}}(\text{scores}),\qquad \text{out} = AV$$

$\sqrt{d_h}$ で割るのは、次元が増えても内積の分散を ~1 に保ち softmax の飽和を防ぐため。
'''),
        code(SETUP),
        code(r'''
# 手計算例: T=3, d_h=2 の小さな数値で全ステップを表示
np.set_printoptions(precision=3, suppress=True)
Q = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
K = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
V = np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]])

scores = Q @ K.T / np.sqrt(2)
print("scores = QKᵀ/√d_h =")
print(scores)

mask = np.triu(np.ones((3, 3), dtype=bool), k=1)
masked = np.where(mask, -np.inf, scores)
print("\ncausal mask 適用（未来 j>t を -inf に）=")
print(masked)

weights = np.exp(masked) / np.exp(masked).sum(axis=1, keepdims=True)
print("\nsoftmax（行ごとに正規化）=")
print(weights)
print("行和:", weights.sum(axis=1))

out = weights @ V
print("\nout = A V =")
print(out)
'''),
        md(r'''
**読み解き**:
- 1行目（t=0）は自分しか見えない → 重み `[1, 0, 0]`、出力は $v_0$ そのもの。
- 2行目（t=1）は $q_1 k_0^\top vs q_1 k_1^\top$ の大小で過去2トークンを按分。
- $-\infty$ は $e^{-\infty}=0$ となり、**softmax の分母からも消える** — 「見えない」の実装。
'''),
        code(r'''
# 自作モジュールの explicit パスを、手動再計算で完全一致検証
from jp_llm_lab.models.attention import CausalSelfAttention

torch.manual_seed(0)
attn = CausalSelfAttention(d_model=8, n_heads=2, context_len=8, attn_impl="explicit")
x = torch.randn(1, 4, 8)
t = {}
y = attn(x, trace=t, prefix="a")

q, k, v = attn.qkv(x).split(8, dim=2)
q = q.view(1, 4, 2, 4).transpose(1, 2)
k = k.view(1, 4, 2, 4).transpose(1, 2)
v = v.view(1, 4, 2, 4).transpose(1, 2)
scores = q @ k.transpose(-2, -1) / math.sqrt(4)
scores = scores.masked_fill(~torch.tril(torch.ones(4, 4, dtype=torch.bool)), float("-inf"))
w = scores.softmax(-1)
y_manual = attn.proj((w @ v).transpose(1, 2).reshape(1, 4, 8))

assert torch.allclose(w, t["a.attn_weights"], atol=1e-6)
assert torch.allclose(y_manual, y, atol=1e-6)
print("手動再計算 == モジュール出力 ✓")
print("重み行和（全head×全行）:", w.sum(-1).flatten().tolist())
'''),
        code(r'''
# causal mask の可視化
T = 8
mask = torch.tril(torch.ones(T, T))
fig = go.Figure(go.Heatmap(z=mask.tolist(), colorscale=[[0, "#eeeeee"], [1, "#3b4fd8"]],
                           showscale=False))
fig.update_layout(title="causal mask（青=参照可 / 灰=遮断） 行=query位置, 列=key位置",
                  template="plotly_white", height=380, width=420)
fig.update_yaxes(autorange="reversed", title="query t")
fig.update_xaxes(title="key j")
fig.show()
'''),
        code(r'''
# explicit と SDPA の出力一致（教育実装は「遅いが同じ計算」であることの確認）
import torch.nn.functional as F
torch.manual_seed(1)
attn2 = CausalSelfAttention(64, 4, 32, attn_impl="explicit")
x2 = torch.randn(2, 16, 64)
y_explicit = attn2(x2)
attn2.set_attn_impl("sdpa")
y_sdpa = attn2(x2)
print("max |explicit - sdpa| =", float((y_explicit - y_sdpa).abs().max()))
assert torch.allclose(y_explicit, y_sdpa, atol=1e-5)
print("一致 ✓（同一パラメータ・同一数式・異なるカーネル）")
'''),
        code(r'''
# 実測ベンチ（scripts/bench_attention.py の保存結果）
from jp_llm_lab.visualization.params_viz import attn_bench_figure
bench = load_json(ROOT / "reports/figures/attn_bench.json")
fig = attn_bench_figure(bench)
fig.show()
sdpa_512 = [r for r in bench["results"] if r["T"] == 512 and r["dtype"] == "bfloat16"]
if len(sdpa_512) == 2:
    e, s = (r["median_ms"] for r in sdpa_512)
    print(f"T=512 bf16: explicit {e:.2f}ms vs SDPA {s:.2f}ms → ×{e/s:.1f}")
'''),
        code(r'''
# 学習済みモデルの attention エントロピー（init vs trained）
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.training.trainer import load_checkpoint
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.visualization.attention_viz import attention_entropy, entropy_comparison_figure

RUN = ROOT / "experiments/runs/m1_model_s_smoke_seed42"
assert RUN.exists(), "先に `make -C jp_llm_lab train-smoke` を実行してください"
tok_run = CharTokenizer.load(RUN / "tokenizer.json")

def load_model(pattern):
    p = sorted(RUN.glob(f"checkpoints/{pattern}"))[0]
    payload = torch.load(p, map_location="cpu", weights_only=False)
    m = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
    load_checkpoint(p, m)
    return m.eval()

s = "私はその人を常に先生と呼んでいた。"
ids_s = torch.tensor([tok_run.encode(s)])
ent = {}
for label, m in [("init", load_model("ckpt_000pct_*.pt")), ("trained", load_model("ckpt_100pct_*.pt"))]:
    maps = m.attention_maps(ids_s)
    ent[label] = torch.stack([attention_entropy(w) for w in maps])
    print(f"{label:8s} 平均エントロピー: {float(ent[label].mean()):.3f} nats"
          f"  層別: {[round(float(e.mean()), 2) for e in ent[label]]}")
fig = entropy_comparison_figure(ent, n_layers=4, n_heads=4)
fig.show()
'''),
        md(r'''
## Observation / Interpretation / Caveat

- **Observation**: init では全 head のエントロピーがほぼ同一（≈1.97 nats、一様に近い）。
  学習後は平均が低下し、**最深層 layer 3 が最も選択的**。head 間のばらつきも学習後に生じる。
- **Interpretation**: 学習は「どこを見るか」を一様から特定パターンへ分化させる。
  ただしこの文では「直前トークン注視が支配的になる」という素朴な予想は部分的にしか成り立たず、
  特定の内容文字への集中が主だった（HTMLレポートの heatmap 参照）。
- **Caveat（重要）**: **attention 重み ≠ 説明**。重みが大きくても出力への因果的寄与が大きいとは
  限らない（値ベクトル $v_j$ が小さければ寄与も小さい）。因果性の検証には ablation /
  activation patching が必要（M2 §9 で実施）。
  また、行 $t$ のエントロピー上限は $\ln(t{+}1)$ なので、短い文の平均値は構造的に小さく出る。

## 確認問題

1. $\sqrt{d_h}$ スケーリングを外すと softmax はどうなるか（大きい $d_h$ で）。
2. mask を softmax の**後**に掛けると何が壊れるか。
3. SDPA が explicit より速い主因はメモリと計算のどちらか。

**次へ**: [06_transformer_forward_pass](06_transformer_forward_pass.ipynb)
'''),
    ]


# --------------------------------------------------------------------- NB06
def nb06() -> list:
    return [
        md(r'''
# 06. Transformer Forward Pass — text から logits まで

## 学習目標

- 実文を入力し、**全中間 tensor の shape と実値**を追跡する（spec §8.4）
- residual stream が層を通じてどう成長するかを測る
- logits → 次トークン分布 → 生成、の最後の1マイルを繋ぐ

## 追跡する形状（B=バッチ, T=系列長, D=隠れ次元, H=head数, V=語彙）

```text
input_ids              [B, T]
token_embeddings       [B, T, D]
Q, K, V                [B, H, T, D/H]
attention_scores       [B, H, T, T]
attention_weights      [B, H, T, T]
attention_output       [B, T, D]
mlp_output             [B, T, D]
residual_stream        [B, T, D]
logits                 [B, T, V]
probabilities          [B, T, V]
```
'''),
        code(SETUP),
        code(r'''
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.training.trainer import load_checkpoint
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer

RUN = ROOT / "experiments/runs/m1_model_s_smoke_seed42"
assert RUN.exists(), "先に `make -C jp_llm_lab train-smoke` を実行してください"
tok = CharTokenizer.load(RUN / "tokenizer.json")
ckpt = sorted(RUN.glob("checkpoints/ckpt_100pct_*.pt"))[0]
payload = torch.load(ckpt, map_location="cpu", weights_only=False)
model = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
load_checkpoint(ckpt, model)
model.eval()
print(f"loaded: {ckpt.name} (step {payload['step']}, {payload['tokens_seen']:,} tokens 学習済み)")
'''),
        code(r'''
from jp_llm_lab.visualization.params_viz import param_breakdown_figure
fig = param_breakdown_figure(model.param_breakdown())
fig.show()
'''),
        code(r'''
# 実文の forward pass を trace（学習と同一のコードパスに dict を通すだけ — 二重実装なし）
s = "私はその人を常に先生と呼んでいた。"
ids = torch.tensor([tok.encode(s)])
trace = model.trace_forward(ids)

rows = [(name, str(tuple(t.shape)), str(t.dtype).replace("torch.", "")) for name, t in trace.items()]
pd.DataFrame(rows, columns=["tensor", "shape", "dtype"])
'''),
        code(r'''
# debug mode: shape だけでなく実値の先頭を覗く
def peek(name, k=4):
    t = trace[name].float()
    vals = [round(float(v), 3) for v in t.flatten()[:k]]
    print(f"{name:28s} {str(tuple(t.shape)):>16s}  first{k}: {vals}")

for name in ["input_ids", "token_embeddings", "embeddings",
             "block0.attn.q", "block0.attn.scores", "block0.attn.attn_weights",
             "block0.resid_after_mlp", "logits", "probabilities"]:
    peek(name)
'''),
        code(r'''
# residual stream の RMS 成長と、各 branch の書き込み量 r_l = ‖Δh‖/‖h‖
from jp_llm_lab.instrumentation.activation_stats import residual_update_ratios

names = ["embeddings"] + [f"block{i}.resid_after_mlp" for i in range(4)] + ["final_norm"]
rms = [float(trace[n].float().pow(2).mean().sqrt()) for n in names]
fig = go.Figure(go.Scatter(x=[n.replace(".resid_after_mlp", "") for n in names], y=rms,
                           mode="lines+markers", line=dict(color="#1f77b4")))
fig.update_layout(title="residual stream RMS（層を経るごとに蓄積で成長）",
                  yaxis_title="RMS", template="plotly_white", height=380)
fig.show()

ratios = residual_update_ratios(trace, n_layers=4)
fig2 = go.Figure(go.Bar(x=list(ratios), y=list(ratios.values()), marker_color="#ff7f0e"))
fig2.update_layout(title="branch別 residual 書き込み比 r_l = ‖Δh‖/‖h‖（この1文に対して）",
                   yaxis_title="r_l", template="plotly_white", height=380)
fig2.show()
'''),
        code(r'''
# 最終位置の logits → 次トークン分布 top10
probs = trace["probabilities"][0, -1]
top = torch.topk(probs, 10)
chars_top = [tok.id_to_token(int(i)).replace("\n", "⏎") for i in top.indices]
entropy = float(-(probs * torch.log(probs.clamp(min=1e-12))).sum())
fig = go.Figure(go.Bar(x=chars_top, y=[float(v) for v in top.values], marker_color="#2ca02c"))
fig.update_layout(title=f"「{s}」の次トークン分布 top10（エントロピー {entropy:.2f} nats）",
                  yaxis_title="確率", template="plotly_white", height=380)
fig.show()
print(f"原文の続きは「だ」（…呼んでいた。だから…）→ モデルのP(だ) = {float(probs[tok.token_to_id('だ')]):.3f}")
'''),
        code(r'''
# 生成: greedy vs temperature 0.7（同じモデル・同じprompt）
from jp_llm_lab.generation.sampler import SamplingConfig, generate

ids0 = torch.tensor([tok.encode("私は")])
out_g, _ = generate(model, ids0, SamplingConfig(max_new_tokens=80, greedy=True))
out_s, _ = generate(model, ids0, SamplingConfig(max_new_tokens=80, temperature=0.7, seed=0))
print("greedy :", tok.decode(out_g[0].tolist()).replace("\n", "⏎"))
print()
print("temp0.7:", tok.decode(out_s[0].tolist()).replace("\n", "⏎"))
'''),
        md(r'''
## Observation / Interpretation / Caveat

- **Observation**: shape 表は spec §8.4 の理論形状と完全一致。residual RMS は層とともに単調増加
  （pre-LN 構成の既知挙動）。冒頭文の次トークン分布は「⏎（改行）0.28・私 0.14・先 0.10…」と
  **句点後の一般的統計**に集中し、原文の実際の続き「だ」は P=0.004 で top10 圏外 —
  この規模のモデルは学習データ冒頭文すら逐語再現しない。
- **Interpretation**: 「Transformer は residual stream に各 block が読み書きするパイプライン」
  という描像が、RMS 成長と r_l でそのまま数値化できる。greedy の反復と temperature の
  多様性のトレードオフは、同じ logits に対する**決定則の違い**にすぎない。
- **Caveat**: r_l や RMS は**この1文**に対する値。分布としての統計は NB16（M2）で
  学習中の全評価バッチに対して追跡する。生成品質の evaluation は定性であり、
  repetition率などの定量化は M5。

## 確認問題

1. `attention_scores` の shape が $[B,H,T,T]$ になる理由を $Q,K$ の shape から導け。
2. weight tying により `lm_head` の shape はどの tensor と一致するか。
3. residual stream の RMS が層とともに増えるのは、pre-LN のどの性質によるか。

**次へ（M2）**: NB02 コーパス探索、NB07 アーキテクチャ可視化、NB13+ 学習ダイナミクス。
'''),
    ]


NOTEBOOKS = {
    "00_project_overview.ipynb": nb00,
    "01_environment_and_gpu.ipynb": nb01,
    "03_tokenizer_anatomy.ipynb": nb03,
    "04_bigram_language_model.ipynb": nb04,
    "05_attention_from_scratch.ipynb": nb05,
    "06_transformer_forward_pass.ipynb": nb06,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="execute cells while building")
    ap.add_argument("--only", default=None, help="substring filter (e.g. '05')")
    args = ap.parse_args()
    for name, fn in NOTEBOOKS.items():
        if args.only and args.only not in name:
            continue
        path = build_notebook(fn(), NB_DIR / name, execute=args.execute, cwd=REPO)
        print(f"built{' + executed' if args.execute else ''}: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
