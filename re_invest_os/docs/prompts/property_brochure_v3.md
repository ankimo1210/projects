# property_brochure_extract v3

## version
v3 (2026-05-13)

## model_recommendations
- 主: `claude-haiku-4-5`
- ローカル: `gemma3:12b` / `qwen2.5:7b`
- 温度: 0
- max_tokens: 1024

## system

```
あなたは日本の不動産販売図面を構造化抽出するアシスタントです。
ユーザーが送るテキストから、指定のJSONテンプレートを埋めてください。

単位換算ルール:
- 〇〇万円 → 整数(× 10000)  例: 3980万円 → 39800000
- 〇〇億円 → 整数(× 100000000)
- 表面利回りは % 値をそのまま  例: 6.20% → 6.2
- 面積は小数 (㎡)
- 築年月は YYYY-MM  例: 2011年4月 → "2011-04"
- 構造コード: RC造→"rc"  木造→"wood"  S造/鉄骨→"steel"  SRC→"src"
- 駅名は路線名を除く  例: JR新宿線 新宿駅 徒歩9分 → 駅名"新宿駅" 分数9

記載がない項目は null のままにしてください。JSON のみ返してください。
```

## user_template

```
販売図面テキスト:
---
{{brochure_text}}
---

以下のJSONテンプレートを埋めて返してください:
{
  "asking_price_yen": null,
  "gross_yield_pct": null,
  "estimated_full_rent_monthly_yen": null,
  "management_fee_monthly_yen": null,
  "repair_reserve_monthly_yen": null,
  "structure": null,
  "build_year_month": null,
  "exclusive_area_sqm": null,
  "nearest_station": null,
  "station_walk_min": null,
  "floor_plan": null,
  "property_name": null,
  "address": null,
  "land_area_sqm": null,
  "building_area_sqm": null,
  "floors_above": null,
  "num_units": null,
  "zoning": null,
  "bcr_pct": null,
  "far_pct": null,
  "road_frontage": null,
  "notes": null,
  "field_confidences": {},
  "inferred_fields": []
}
```

## output_schema (JSON Schema)

```json
{
  "type": "object",
  "properties": {
    "property_name":                   {"type": ["string","null"]},
    "address":                         {"type": ["string","null"]},
    "asking_price_yen":                {"type": ["integer","null"]},
    "nearest_station":                 {"type": ["string","null"]},
    "station_walk_min":                {"type": ["integer","null"]},
    "land_area_sqm":                   {"type": ["number","null"]},
    "building_area_sqm":               {"type": ["number","null"]},
    "exclusive_area_sqm":              {"type": ["number","null"]},
    "structure":                       {"type": ["string","null"]},
    "floors_above":                    {"type": ["integer","null"]},
    "num_units":                       {"type": ["integer","null"]},
    "floor_plan":                      {"type": ["string","null"]},
    "build_year_month":                {"type": ["string","null"]},
    "zoning":                          {"type": ["string","null"]},
    "bcr_pct":                         {"type": ["number","null"]},
    "far_pct":                         {"type": ["number","null"]},
    "road_frontage":                   {"type": ["string","null"]},
    "gross_yield_pct":                 {"type": ["number","null"]},
    "estimated_full_rent_monthly_yen": {"type": ["integer","null"]},
    "management_fee_monthly_yen":      {"type": ["integer","null"]},
    "repair_reserve_monthly_yen":      {"type": ["integer","null"]},
    "notes":                           {"type": ["string","null"]},
    "field_confidences":               {"type": "object"},
    "inferred_fields":                 {"type": "array"}
  }
}
```

## changelog

- 2026-05-13 v3: テンプレート埋め込み方式 — モデルが全フィールドを出力するよう強制
- 2026-05-13 v2: 2ステップ指示型 (STEP 1 のみ出力される欠陥あり)
- 2026-05-12 v1: 初期 draft
