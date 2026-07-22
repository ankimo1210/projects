# AI-readable paper corpus

`sources/papers/*.pdf` の原本を変更せず、Docling で AI が読みやすい派生コーパスへ
変換する。原本 PDF と生成物は、それぞれ `sources/papers/` と `corpus/` で Git 管理し、
論文監査を自己完結させる。

## 出力

各 PDF は `corpus/papers/<paper-id>/` に次の形で保存される。

| file | role |
|---|---|
| `document.md` | 見出し、表、数式、図参照を含む読みやすい本文 |
| `document.json` | Docling の lossless document structure |
| `chunks.jsonl` | section/page provenance と原本 SHA-256 を含む検索用 chunk |
| `formulas.jsonl` | 式ごとの品質状態、LaTeX、PDF text layer、ページ、bbox、原本画像 |
| `metadata.json` | 原本、変換条件、抽出量、QA 指標 |
| `images/` | 抽出した図表・ページ画像と `formula_NNNN.png` の原式 crop |

`corpus/papers/_index.json` は全論文のメタデータをまとめる。原本との対応は
`source.path` と `source.sha256` で固定する。

## 現在のコーパス

2026-07-22 時点で22論文・449ページを変換し、1,326 chunks、424式を保存している。
数式品質オーバーレイにより312式を LaTeX 化し、全424式に原本 crop を付けた。
chunk上限は480 tokenを指定しているが、分割できない表を
含む `ref_tran_bin_2003.00598` の2 chunksは525/536 tokenとなる。実測最大値は各論文の
`metadata.json` に記録するため、512 tokenを厳密な入力上限とする利用側ではこの2件を
追加分割する。

数式の品質内訳は次のとおり。検証済みは、著者が公開した正確な版の arXiv TeX と
対応付けた224式と、原本 PDF を手動確認した49式である。42式は両方で確認しているため、
重複を除く一次資料との検証済み総数は231式となる。さらに、式の定義、前後関係、
行列形状、確率過程の停止時刻、変換公式、漸近オーダーを意味的にレビューし、80式を
高信頼で確認・復元した。

| status | count | meaning |
|---|---:|---|
| `verified_source` | 182 | 正確な arXiv 版の著者 TeX と対応付けた LaTeX |
| `verified_source_and_manual` | 42 | 著者 TeX と原本 PDF の両方で確認した手動転記 LaTeX |
| `verified_manual` | 7 | 原本 PDF と照合したが、利用可能な著者 TeX がない手動転記 LaTeX |
| `semantic_high_confidence` | 80 | 文脈・定義・形状制約から高信頼で確認または復元した LaTeX |
| `semantic_not_formula` | 2 | 式番号や空括弧を数式として検出したレイアウト由来の誤検出 |
| `decoded_unverified` | 1 | Docling が復元したが、意味レビューで確定していない LaTeX |
| `text_layer_fallback` | 110 | 信頼できる LaTeX がなく、原式 crop と PDF text layer を保存 |

`semantic_high_confidence` は原文転記の検証とは区別する。意味レビュー83件のうち、
既存式の確認43件、復元29件、論文の疑わしい誤植修正8件、非数式2件、曖昧なため未変更1件
である。曖昧な式は元のstatusを維持し、`semantic_review` と `note` に根拠、仮定、
代替候補、不確実性を残す。

## 生成と検証

通常の変換は隔離した Docling `2.114.0` を使うため、workspace の依存関係を変更しない。

```bash
make -C market_nn paper-corpus
make -C market_nn paper-corpus-check
```

既存コーパスに数式品質オーバーレイだけを再適用する場合:

```bash
make -C market_nn paper-corpus-formulas
```

正確な arXiv 版のソースを取得し、SHA-256 を検証して数式を再照合する場合:

```bash
make -C market_nn paper-corpus-verify-sources
make -C market_nn paper-corpus-check
```

`manifests/arxiv_formula_sources.json` は19論文の正確な arXiv version、main TeX、
source archive SHA-256 と目視確認済み対応を固定する。うち17論文は TeX を含み、2論文の
source package は PDF wrapper のみである。`manifests/formula_source_matches.json` は
式ごとの source file/line、原本ページ、類似度、採用方法を保存する。既定の自動採用
閾値は0.90で、閾値未満の97件は原式 crop を個別に目視確認したものだけを明示的に
採用する。TeX環境とPDF側の式分割が一致しない、または順序整列が誤った15件は、
理由付きの拒否リストへ固定して自動採用を防ぐ。

`manifests/formula_semantic_reviews.json` とそこから参照するバッチmanifestは、意味レビューを
一次資料照合とは別レイヤーで管理する。LaTeXの置換はconfidence 0.90以上に限定し、
`evidence` を必須とする。
論文自体の誤植を修正する場合は、`paper_as_printed_latex` を保存して原文との差を隠さない。
confidenceが閾値未満の式は置換せず、`note` に不確実性を明記する。

GPU を明示する場合:

```bash
make -C market_nn paper-corpus PAPER_CORPUS_ARGS="--device cuda"
```

Docling 側でも数式を LaTeX として補完する場合は `--enrich-formula` を追加する。
CUDA の初回実行時に
Triton が小さな拡張をビルドするため、Ubuntu では `python3.12-dev` が必要になる。

```bash
sudo apt-get install python3.12-dev
make -C market_nn paper-corpus \
  PAPER_CORPUS_ARGS="--device cuda --enrich-formula"
```

`python3.12-dev` を導入できない環境では、数式補完なしでも本文、見出し、表、図、
page provenance、chunk は生成できる。

## 変換方針

- OCR は無効。現在の PDF 22 本はすべて埋め込みテキストを持つ。
- 表抽出は `accurate`、画像は外部 PNG 参照とする。
- chunk は Docling hybrid chunker で生成し、既定トークナイザーの 512 token 上限を
  越えないよう目標上限を 480 とする。
- 各 chunk に `paper_id`、title、page、source PDF、SHA-256、Docling version を付与する。
- wide equation box 由来の冗長な LaTeX spacing command は後処理で圧縮する。
- 変換後に `manifests/formula_overrides.json` の検証済み転記を適用する。
- 利用可能な場合は正確な arXiv 版の著者 TeX を式順序と正規化類似度で対応付け、
  source archive の版・SHA-256・ファイル・行番号を各式に記録する。
- 自動照合で確定できない式は、記号定義、前後の論理、行列形状、単位、漸近オーダー、
  標準的な恒等式を使って意味レビューし、confidenceと根拠を構造化して記録する。
- 数式ごとに安定した ID と品質状態を付け、原本ページの bbox から crop を生成する。
- 未復元式を空の placeholder のまま残さず、crop と PDF text layer にフォールバックする。
- 変換は一時領域で完了させてから `corpus/papers/` を置換し、失敗時は既存 corpus を
  保持する。

## 制約

`verified_source*` と `verified_manual` は表記と構造を一次資料に照合したもので、論文自体の
数式が理論的に正しいことまでは保証しない。たとえば FI-2010 の式 (14) は通常の RBF と
異なる正の指数を原文どおり保持している。arXiv source package が PDF wrapper のみの
2論文と arXiv TeX を利用できない3論文は、著者 TeX による検証対象外である。
`decoded_unverified`、`text_layer_fallback` と複雑な結合セルは完全一致を保証しないため、
重要な式・表は `formulas.jsonl` のページ・bbox・crop と原本 PDF で照合する。
`semantic_high_confidence` は複数の意味的制約から最も妥当な式を復元した状態であり、
原著者による訂正を意味しない。特に `correct_suspected_paper_typo` は監査上の提案なので、
引用時には `paper_as_printed_latex` と併記する。
