# Prompts (v1)

LLM呼び出しに使うプロンプトのバージョン管理ディレクトリ。

## 規約

- ファイル名: `<purpose>_v<n>.md` (例: `classify_document_v1.md`)
- 各ファイルは以下を含む:
  - `version`
  - `model_recommendations` (Claude/GPT どれが向くか)
  - `system` (system message)
  - `user_template` (ユーザーメッセージのテンプレート)
  - `output_schema` (JSON Schema 抜粋)
  - `examples` (1-3件)
  - `changelog`

## ファイル一覧

| Purpose | File | Model | Status |
|---|---|---|---|
| 資料分類 | `classify_document_v1.md` | Haiku | draft |
| 販売図面抽出 | `property_brochure_v1.md` | Haiku (text) / Sonnet (vision) | draft |
| レントロール抽出 | `rent_roll_v1.md` | Haiku / Sonnet | draft |
| 3行サマリー | `summary_3line_v1.md` | Haiku | draft |
| 確認質問リスト | `inquiry_questions_v1.md` | Haiku | draft |
| 業者資料の甘さ説明 | `assumption_critique_v1.md` | Sonnet | draft |

## 共通ルール (すべてのプロンプトに必須)

1. **計算をLLMに任せない**: 数値計算は financial-engine。LLMは抽出と説明のみ
2. **null safe**: 不明な値は `null`、推測は `inferred_fields` に追加
3. **PII除去**: 賃借人個人名・電話・メールは抽出しない
4. **法務NG表現禁止**: 「買うべき」「お得」「狙い目」「儲かる」等は出力しない
5. **構造化出力**: 必ず JSON schema で強制 (Anthropic tool use / OpenAI Structured Outputs)
6. **再現性**: prompt_version + model + raw_output を必ず保存

## 評価方法

各プロンプトには `tests/fixtures/documents/` 配下に入力サンプルと期待出力 (`*.expected.json`) を置き、
オフライン評価スクリプト (将来) で項目別正解率を計測する。

合格ライン (ai_document_extraction_spec.md §11.1):
- 価格・面積・所在地・賃料・築年月: **95%以上 exact**
- 構造・用途地域・接道: **85%以上**
- その他: **70%以上**
