# WSET Level 3 問題コーパス

WSET Level 3向け学習素材の構造、出題範囲、品質を調査した参照用コーパスです。

このディレクトリのデータは現在のアプリには読み込まれません。アプリは `../QuestionSources/wset_level3_original_questions_300_v2.xlsx` を正本とする、日本語の自作問題300問を使用します。

## 収録済みの調査結果

- 20件のソース候補
- 5,646件の質問候補を構造化（英語5,564件、日本語82件、解答付き5,524件）
- 重複クラスタを統合した推定ユニーク件数は5,008件
- 形式内訳はフラッシュカード4,536件、MCQ 1,000件、記述・因果説明・工程問題110件
- HTML/PDFからの質問候補検出、正規化、簡易分類、重複検出、透明な品質スコア
- 独自に作成した20件の抽象問題パターン
- ローカルHTML調査レポート

これらは過去の調査結果として保持し、アプリ用問題パックの生成には使用しません。

## セットアップ

```bash
cd /Users/ankimo1210/Documents/projects/WSET/wset_l3_question_corpus
uv sync --extra dev
```

Python 3.12以上を使用します。コア処理に有料APIやLLMは不要です。

## コマンド

```bash
uv run wset-corpus discover
uv run wset-corpus fetch
uv run wset-corpus extract
uv run wset-corpus normalize
uv run wset-corpus classify
uv run wset-corpus deduplicate
uv run wset-corpus score
uv run wset-corpus report --open
uv run wset-corpus pipeline --source wset_official_sample_paper
uv run python scripts/fetch_winerevision.py
uv run python scripts/fetch_ankiweb_deck.py
```

`discover` の既定動作は検索クエリを `data/exports/source_candidates.csv` に書く手動支援モードです。任意の検索APIは `.env.example` の共通JSONインターフェース経由でのみ利用します。

## データフロー

```text
config/sources.yaml
  → data/extracted/questions.jsonl
  → data/normalized/questions.jsonl
  → data/reviewed/questions.jsonl
  → data/exports/
  → reports/index.html
```

質問IDは `source_id + source_url + normalized_text + source_position` のSHA-256から決定的に生成します。取得物にはmanifestとSHA-256を付け、再実行時に内容変化を検証できます。

## レビュー手順

1. `config/sources.yaml` でソースID、URL、言語、形式を確認する。
2. 自動取得する場合だけ `enabled: true` と対象範囲を設定する。
3. `fetch` のステータスとHTTP結果を確認する。
4. 抽出候補をCSV/JSONLで人手レビューする。
5. `human_review_status` と品質タグを更新する。

レビュー状態は `unreviewed`, `machine_screened`, `human_reviewed`, `approved_for_pattern_analysis`, `rejected`, `fact_check_required` を使用します。

## ソース追加

`config/sources.yaml` に一意な `source_id`、URL、言語、種別、取得方針、レビュー日を記載します。最初は `enabled: false` とし、抽出対象とパーサーを確認してから有効化します。

## ディレクトリ

- `config/`: ソース台帳、分類体系、クローラ制御、日英用語
- `src/wset_corpus/`: 収集・抽出・分類・評価・出力
- `data/reviewed/question_patterns.jsonl`: 独自作成の抽象問題パターン
- `docs/`: データモデル、審査基準、調査記録
- `reports/`: ローカルHTMLレポート（生成物）
- `tests/`: 合成fixtureのみを使うテスト

## 再実行とレポート

個別ソースは `uv run wset-corpus pipeline --source <source_id>` で再実行できます。既存取得物はハッシュ付きmanifestによりキャッシュされます。`uv run wset-corpus report --open` でローカルレポートを開きます。

## 制約

- ヒューリスティック抽出は設問以外を拾い、複数行設問を分割する可能性があります。
- 言語・分類・品質スコアは人手確認が必要です。
- Semantic duplicate はオプションで、初期版ではexact/nearのみです。
- JavaScript専用ページを回避するためのPlaywrightはまだ有効化していません。

詳細は [データモデル](docs/DATA_MODEL.md)、[ソース審査](docs/SOURCE_REVIEW_GUIDE.md) を参照してください。
