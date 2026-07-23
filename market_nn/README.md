# lob-paper-reproductions

Limit-order-book（LOB）予測研究を、論文と公式コードの差を隠さずに検証する
Python 再現スイートです。既定のテストは決定論的な合成データだけを使い、
実データ上の数値結果を再現したとは主張しません。

## 現在の再現範囲

| profile | fidelity | 既定の検証 |
|---|---|---|
| `gould_bonart_2015_paper` | `B_PAPER_EXACT` | 標本化、ロジスティック、local logistic、ROC-AUC、MSR |
| `deeplob_ieee_2019` | `B_PAPER_EXACT` | 論文記載アーキテクチャの形状・パラメータ |
| `deeplob_author_tf2_ff14d7c` | `A_AUTHOR_CODE_EXACT` | 実行仕様・解析的パラメータ数、任意の TensorFlow 実行 |
| `deeplob_author_pytorch_ff14d7c` | `A_AUTHOR_CODE_EXACT` | clean-room port の形状・パラメータ数・forward |
| `tlob_author_repo_f1c0af4` | `A_AUTHOR_CODE_EXACT` | forward、軸交互化、BiN、埋め込み detach、EMA lifecycle |
| `mlplob_author_repo_f1c0af4` | `A_AUTHOR_CODE_EXACT` | forward、軸混合、BiN、埋め込み detach |
| TLOB / MLPLOB paper profiles | `C_PAPER_CONSTRAINED` | 未開示事項を明示した構造再現 |
| `sirignano_cont_2019_paper_constrained` | `C_PAPER_CONSTRAINED` | 3層 LSTM と pooled/unseen-asset protocol |

`A_AUTHOR_CODE_EXACT` は指定コミットの挙動を対象とするプロファイル名です。
合成データでの通常 smoke は「architecture verified」であり、論文の数値再現では
ありません。TLOB/MLPLOB は FI-2010 実行入口による `hidden_dim: 40 -> 144` の
runtime override を含めて author-code profile に固定しています。DeepLOB 公式
リポジトリには指定コミットで明示的ライセンスがないため、
公式ノートブック自体は同梱せず、ローカル取得した参照コードに対する clean-room
検証だけを行います。

## セットアップ

このリポジトリは親ディレクトリの単一 `uv` workspace を使います。

```bash
cd /home/kazumasa/projects
uv sync --package lob-paper-reproductions
uv run --package lob-paper-reproductions lob-repro sources verify
uv run --package lob-paper-reproductions lob-repro fixtures generate --seed 7
uv run --package lob-paper-reproductions lob-repro inspect \
  --profile deeplob_ieee_2019 --show-shapes --show-parameters
uv run --package lob-paper-reproductions lob-repro smoke \
  --profile deeplob_author_pytorch_ff14d7c --data synthetic
uv run --package lob-paper-reproductions lob-repro run \
  --profile gould_bonart_2015_paper --data synthetic
uv run --package lob-paper-reproductions python \
  market_nn/scripts/run_reproduction_matrix.py
```

短縮形:

```bash
make -C market_nn verify-provenance
make -C market_nn test
make -C market_nn smoke
make -C market_nn paper-corpus
make -C market_nn paper-corpus-verify-sources
make -C market_nn paper-corpus-retrieval-qa
make -C market_nn paper-corpus-deep-qa
```

コマンドの import 時にダウンロードや学習は発生しません。TensorFlow は公式 TF2
ノートブックを実行比較するときだけ `tensorflow` extra として導入します。

## 一次資料とデータ

- 論文・公式コードの版、SHA-256、ライセンス状態は `manifests/sources/` に固定。
- PDF は自己完結した監査資料として `sources/papers/` で Git 管理する。取得した公式
  コードは `sources/references/` の Git 管理外領域に置く。
- FI-2010 の既定テストは `149 x N` の合成 fixture を使う。
- 公開データ取得は明示的な `--accept-terms` が必要で、raw data は commit しない。
  pinned optional archive は DeepLOB の decimal-precision variant 用であり、TLOB の
  ZScore variant は別途正当な取得・hash 固定が必要。
- 取得済み archive は `lob-repro data audit-fi2010` で構造監査できる
  （shape・ラベル分布・windowing のみ。学習・数値再現は行わない）。

根拠、差分、未解決事項は [docs/source_audit.md](docs/source_audit.md)、
[docs/evidence_ledger.md](docs/evidence_ledger.md)、
[docs/discrepancy_matrix.md](docs/discrepancy_matrix.md) を参照してください。

## AI 向け論文コーパス

`sources/papers/` の PDF は Docling `2.114.0` で Markdown、構造化 JSON、検索用
JSONL chunk、画像へ変換できる。生成物は Git 管理対象の `corpus/papers/` に置き、
各 chunk から原本 PDF、ページ、SHA-256 を追跡できる。生成方法、出力形式、数式補完の
要件は [docs/paper_corpus.md](docs/paper_corpus.md) を参照。数式は一次資料との一致と、
文脈・定義・形状制約による意味的復元を別レイヤーで記録し、不確実な候補は元式を
置換せずnoteへ残す。全22論文を式・方法・結果の66問で横断する検索QAは
`paper-corpus-retrieval-qa` で再実行できる。全449ページのPDF-to-document token照合、
強い英語言い換え66問、日本語66問、exact formula evidenceを含む追加監査は
`paper-corpus-deep-qa` で実行する。

## 主張できること / できないこと

主張できるのは、合成 fixture 上の構造・整列・lifecycle 検証と、利用可能な場合の
指定コミットに対する挙動比較です。FI-2010 または proprietary LOBSTER data 上の
accuracy/F1 を実行していない結果について、`replicated` や「論文結果を再現した」
とは表現しません。
