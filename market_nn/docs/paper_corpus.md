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
| `metadata.json` | 原本、変換条件、抽出量、QA 指標 |
| `images/` | 抽出した図表画像 |

`corpus/papers/_index.json` は全論文のメタデータをまとめる。原本との対応は
`source.path` と `source.sha256` で固定する。

## 現在のコーパス

2026-07-21 時点で22論文・449ページを変換し、1,326 chunks、200数式ブロック、
584 PNGを保存している。chunk上限は480 tokenを指定しているが、分割できない表を
含む `ref_tran_bin_2003.00598` の2 chunksは525/536 tokenとなる。実測最大値は各論文の
`metadata.json` に記録するため、512 tokenを厳密な入力上限とする利用側ではこの2件を
追加分割する。

## 生成と検証

通常の変換は隔離した Docling `2.114.0` を使うため、workspace の依存関係を変更しない。

```bash
make -C market_nn paper-corpus
make -C market_nn paper-corpus-check
```

GPU を明示する場合:

```bash
make -C market_nn paper-corpus PAPER_CORPUS_ARGS="--device cuda"
```

数式を LaTeX として補完する場合は `--enrich-formula` を追加する。CUDA の初回実行時に
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
- 変換は一時領域で完了させてから `corpus/papers/` を置換し、失敗時は既存 corpus を
  保持する。

## 制約

PDF から復元した数式と複雑な結合セルは完全一致を保証しない。`metadata.json` の
`quality` と原本ページを参照し、重要な式・表は必ず PDF と照合する。
