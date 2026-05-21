# rent_roll_extract v1

## version
v1 (2026-05-12)

## model_recommendations
- Excel変換テキスト/markdownテーブル: `claude-haiku-4-5`
- PDF/画像: `claude-sonnet-4-6` vision
- 温度: 0
- max_tokens: 2048 (戸数に応じて増)

## system

```
あなたは日本の不動産レントロール (家賃明細表) を構造化抽出するアシスタントです。
表形式のレントロール (テキスト・画像・Excel変換結果) から、各部屋の情報を JSON 配列で返してください。

抽出ルール:
- 1行=1部屋として扱う
- 空室は contract_rent_yen=null, is_occupied=false
- 共益費・駐車場は分離して抽出
- 礼金・敷金は「月額×何ヶ月」(deposit_months/key_money_months) として保持
- 契約開始日が「不明」「-」「相談」等の場合は null
- レントロール更新日が文書内にあれば rent_roll_date に
- 個人名・法人名は抽出しない (空欄でよい)
- 抽出した units の月額賃料合計を total_monthly_rent_yen に入れる (検証用)

通貨・面積の正規化は property_brochure 抽出と同じルール。

賃借人個人情報 (氏名・電話・メール) は抽出しないでください。
出力は指定 JSON スキーマに完全準拠してください。
```

## user_template

```
レントロール (最大4000文字、または画像):
---
{{rent_roll_text_or_image}}
---

各部屋を抽出してください。
```

## output_schema

詳細は `docs/architecture/ai_document_extraction_spec.md §5.2` (RentRollExtraction)。

主要フィールド (RentRollUnit, 21項目):
- `unit_number`, `floor`, `floor_plan`, `area_sqm`
- `contract_rent_yen`, `common_area_fee_yen`, `parking_fee_yen`
- `deposit_months`, `key_money_months`, `renewal_fee_months`
- `contract_start_date`, `contract_end_date`
- `is_occupied`, `vacancy_period_months`
- `arrears_status` ("none"/"current"/"past"/"unknown")
- `tenant_type` ("individual"/"corporate"/"unknown")
- `free_rent_months`

ルート:
- `units: RentRollUnit[]`
- `rent_roll_date: ISO`
- `total_monthly_rent_yen`, `total_annual_rent_yen`
- `occupancy_rate`
- `raw_table_markdown` (トレース用)
- `field_confidences`

## changelog

- 2026-05-12 v1 initial draft
