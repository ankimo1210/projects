# jp_llm_lab — 日本語小型LLMの「内部を見る」教育ラボ

> **This project is not designed to build a competitive large language model.**
> **It is designed to make the internal mechanics, training dynamics, architectural
> trade-offs, probability calibration, and limitations of language models
> observable and understandable.**

日本語中心の小型 Decoder-only Transformer を PyTorch でゼロから実装し、
事前学習 → 計測 → 統制実験 → 確率較正 → 簡易SFT までを **Visualization-first** で進める教育プロジェクト。
Attention・Transformer block・学習/評価/生成ループ・計測フックはすべて手書き
（`F.scaled_dot_product_attention` は explicit 実装と出力一致を検証した上で高速パスとしてのみ使用）。

## Status: 全 Milestone 完了（M1–M6）

| Milestone | 内容 | 主な成果物 |
|---|---|---|
| M1 教育的最小 | char tok・bigram・explicit attention・Model S(1.1M)・全計測 | `reports/html/index.html`, NB00-06 |
| M2 計測付き学習 | コーパススナップショット・BPE(自作+HF)・attention/embedding定量・Model M(10M) | NB02,07,08,13-17 |
| M3 統制実験 | LR/batch/init 校正・Classical→Modern アブレーション(3 seeds) | NB09-12,18 |
| M4 本事前学習 | Model L(30M)×100M tokens・スケーリング | NB19 |
| M5 較正とSFT | reliability/temperature scaling・生成解剖・暗記分析・instruction SFT | NB20-23 |
| M6 最終成果物 | 評価219問・マルチページHTMLサイト・最終レポート | `reports/site/`, NB24 |

**主要な実測結果**

- Model L (30M, Modern/RoPE): main 98M tokens → val loss 3.51 (ppl 33.5)。流暢な日本語を生成するが**事実は誤る**（「日本の首都は上海」）。
- アブレーション: 改善のほぼ全ては **RoPE 由来**（−0.34 nats, 3 seeds で有意）。RMSNorm はノイズ内。
- スケーリング: 固定トークン予算では**最大モデルが最良でない**（データ枯渇＝Chinchilla）。
- 較正: Model L は次トークン較正が良好（T≈0.98, ECE 0.004）だが、それは**事実的正しさとは別物**。
- 暗記: <1epoch の Model L は train≈val で暗記が弱い（M1 の45エポック暗記と対照）。
- テスト 78件（因果マスク・SDPA一致・grad-accum等価・過学習・ECE・temp scaling・SFTマスク・calibration split分離 等）。
- Notebook 25冊（00-24、`tools/build_notebooks*.py` で生成・全冊実行済み）。

## Quickstart（WSL2 / uv ワークスペースのメンバー）

```bash
# ワークスペースルート（~/projects）から
uv pip install -e jp_llm_lab --no-deps

make -C jp_llm_lab env      # 環境診断（GPU/VRAM/BF16/SDPA 自動検出）
make -C jp_llm_lab test     # pytest 78件（学習成果物なしで通る単体テスト）
```

追加依存（コーパス/BPE 用、venv のみ・lock 非変更）:

```bash
uv pip install datasets tokenizers
```

## Reproduction guide

各段階は config から再実行でき、分析は保存済み成果物のみ読む（再学習不要）。

```bash
# M1（サンプルコーパス＝青空文庫、~1分）
make -C jp_llm_lab corpus m1

# M2（スナップショット取得は要ネットワーク、fineweb2ja 170M chars ~10分）
make -C jp_llm_lab snapshots     # data/snapshots/（git-ignore, ~170M chars）
make -C jp_llm_lab tokenizers    # 自作BPE + HF-BPE8K + tokenized cache
make -C jp_llm_lab train-m       # Model M(10M) + 解析成果物 + corpus stats

# M3（校正 ~5分、アブレーション15 runs ~8分）
make -C jp_llm_lab calibrations ablation

# M4（Model L 30M×100M tokens ~11分、スケーリング4サイズ ~5分）
make -C jp_llm_lab train-l scaling

# M5（較正/生成/暗記/SFT、~5分）
make -C jp_llm_lab m5-analysis

# M6（評価219問 + マルチページサイト）
make -C jp_llm_lab eval site

# 全 Notebook 生成・実行（25冊）
make -C jp_llm_lab notebooks-all
```

各 run は `experiments/runs/<name>_seed<seed>/` に `config.json`・`runmeta.json`（git hash+dirty・
パッケージ版・GPU・時刻）・`metrics.jsonl`・`checkpoints/`・`samples.jsonl`・`summary.json`・
`analysis/` を保存。コーパスは `data/manifests/` に URL/license/sha256 を記録。

## 閲覧方法

- **マルチページサイト**: `reports/site/index.html`（全マイルストーン横断、14ページ）
- **M1レポート**: `reports/html/index.html`
- **Notebook**: `notebooks/00-24_*.ipynb` を JupyterLab で（上から順に実行可能）
- **限界**: `LIMITATIONS.md`

## リポジトリ構成

```text
jp_llm_lab/
├── src/jp_llm_lab/{data,tokenization,models,training,evaluation,calibration,
│                   instrumentation,generation,visualization,reporting}/
├── scripts/          # 実験の実行入口（config駆動）
├── configs/{smoke,pilot,main,ablations}/
├── tools/            # nbkit + notebook builders
├── notebooks/        # 00-24（生成物）
├── experiments/{cards,runs,comparisons,calibrations,analysis_m5}/
├── reports/{html,site,figures,env}/
├── data/{manifests,samples,snapshots,tokenized,sft}/  # 大物は git-ignore
└── tests/            # 78 tests
```

## 設計原則（spec より）

1. 教育的明瞭さ > 抽象化 — 重要な処理は読んで理解できる形で明示的に実装
2. すべての図に What / Why / How to read / Observation / Interpretation / Caveat / Next
3. 統制実験 — 比較対象以外を固定し、固定できない場合は明記
4. **仮説に合わない結果もそのまま記録**（RoPE の大改善もスケーリングの非単調も実測どおり）
5. 実測データと例示データを混ぜない
