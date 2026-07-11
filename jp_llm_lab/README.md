# jp_llm_lab — 日本語小型LLMの「内部を見る」教育ラボ

> **This project is not designed to build a competitive large language model.**
> **It is designed to make the internal mechanics, training dynamics, architectural
> trade-offs, probability calibration, and limitations of language models
> observable and understandable.**

日本語中心の小型 Decoder-only Transformer を PyTorch でゼロから実装し、
事前学習 → 計測 → 統制実験 → 確率較正 → SFT までを **Visualization-first** で進める教育プロジェクト。
Attention・Transformer block・学習/評価/生成ループ・計測フックはすべて手書きです
（`F.scaled_dot_product_attention` は explicit 実装と出力一致を検証した上で高速パスとしてのみ使用）。

## Status: Milestone 1 完了（educational minimum）

| 成果物 | 場所 |
|---|---|
| 実装計画（M1詳細 + M2-6ロードマップ） | `IMPLEMENTATION_PLAN.md` |
| 環境診断 + ハードウェア別推奨設定 | `scripts/diagnose_env.py` → `reports/env/` |
| 文字トークナイザ / bigram / explicit attention / Classical GPT (1.1M) | `src/jp_llm_lab/` |
| 計測つき学習ループ（loss・勾配・活性RMS・update比・checkpoint別生成） | `src/jp_llm_lab/training/trainer.py` |
| スモーク実走（『こころ』6.5M tokens, RTX 5080 41.6s, val ppl 23.9） | `experiments/runs/` |
| テスト 44件（因果マスク・SDPA一致・grad-accum等価・1バッチ過学習 等） | `tests/` |
| ノートブック 6冊（00,01,03,04,05,06 — 実行済み） | `notebooks/` |
| 静的HTMLレポート（全図に What/Why/How/Observation/Interpretation/Caveat/Next） | `reports/html/index.html` |
| 実験カード | `experiments/cards/` |

## Quickstart（WSL2 / uv ワークスペースのメンバーとして動作）

```bash
# ワークスペースルート（~/projects）から
uv pip install -e jp_llm_lab --no-deps

make -C jp_llm_lab env          # 環境診断（GPU/VRAM/BF16/SDPA 自動検出）
make -C jp_llm_lab corpus       # 青空文庫サンプル取得（manifest に URL/license/sha256 記録）
make -C jp_llm_lab test         # pytest 44件
make -C jp_llm_lab m1           # M1 一括: 診断→テスト→bigram→Model S→bench→NB→レポート
```

個別実行:

```bash
make -C jp_llm_lab train-bigram   # count vs neural bigram
make -C jp_llm_lab train-smoke    # Model S (1.1M) smoke 学習
make -C jp_llm_lab bench          # explicit vs SDPA microbench
make -C jp_llm_lab notebooks      # notebooks/ を再生成+実行
make -C jp_llm_lab report         # reports/html/index.html
```

CPUのみでも動作します（自動で fp32/CPU にフォールバック、`tests/test_smoke_cpu.py` で保証）。

## 再現性

各 run は `experiments/runs/<name>_seed<seed>/` に以下を保存:
`config.json`（モデル/学習設定・シード・パラメータ内訳）, `runmeta.json`（git hash・dirty flag・
パッケージ版・GPU・時刻）, `metrics.jsonl`（train/eval/checkpoint レコード）,
`checkpoints/ckpt_{0,1,5,10,25,50,75,100}pct_*.pt`, `samples.jsonl`（checkpoint別固定プロンプト生成）,
`tokenizer.json`, `summary.json`。分析（ノートブック・レポート）は保存済み成果物のみを読み、
再学習を要求しません。

## 設計原則（spec より）

1. 教育的明瞭さ > 抽象化 — 重要な処理は読んで理解できる形で明示的に実装
2. すべての図に What / Why / How to read / Observation / Interpretation / Caveat / Next
3. 統制実験 — 比較対象以外を固定し、固定できない場合は明記
4. 仮説に合わない結果もそのまま記録（cherry-picking しない）
5. 実測データと例示データを混ぜない

## Roadmap

- **M2**: コーパススナップショット（FineWeb2-ja/Wikipedia, streaming）・自作BPE・活性/勾配ダッシュボード・attention定量分析
- **M3**: LR range test・バッチサイズ/初期化校正・Classical→Modern アブレーション連鎖（RMSNorm/RoPE/SwiGLU/no-bias）
- **M4**: Model L (~30-50M) を ~100M tokens で本学習
- **M5**: 確率較正（reliability diagram/Temperature Scaling）・生成解剖・暗記分析・SFT
- **M6**: 評価プロンプト200問・全NB検証・最終HTMLサイト・限界文書

詳細は `IMPLEMENTATION_PLAN.md` を参照。
