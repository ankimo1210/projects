# property_brochure_extract v4

## version
v4 (2026-05-13)

## model_recommendations
- 主: `claude-haiku-4-5`
- ローカル: `gemma3:12b` / `qwen2.5:7b`
- 温度: 0
- max_tokens: 1024

## system

```
以下のJSONテンプレートをテキストの内容で埋めてください。記載がなければ null のまま。
```

## user_template

```
テキスト:
---
{{brochure_text}}
---

変換ルール: 万円→×10000 / RC造→"rc" 木造→"wood" S造→"steel" SRC→"src" / 利回り%はそのまま(6.2%→6.2) / 築年月はYYYY-MM / 面積はfloat / 駅名は路線名なし

テンプレートを埋めて返してください:
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

- 2026-05-13 v4: 超短縮 system (1行) + user テンプレート埋め込み。gemma3:12b で全フィールド取得確認。
- 2026-05-13 v3: テンプレート方式 (system 長すぎた)
- 2026-05-13 v2: 2ステップ方式 (STEP 1 のみ出力の欠陥)
- 2026-05-12 v1: 初期 draft
