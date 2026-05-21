# inquiry_questions v2

## version
v2 (2026-05-13)

## model_recommendations
- 主: `claude-haiku-4-5`
- ローカル: `gemma3:12b`
- 温度: 0
- max_tokens: 1024

## system

```
以下のJSONテンプレートを埋めてください。日本語、敬体 (です・ます調)。
不動産仲介への確認質問を最大8件、必須→精度向上→買付前の順で書いてください。
```

## user_template

```
分析データ:
{{analysis_summary}}

以下のJSONテンプレートを埋めて返してください（最大8件、少なくとも3件は必ず埋める）:
{
  "questions": [
    {
      "category": "essential",
      "question": "必須確認質問1",
      "rationale": "理由1"
    },
    {
      "category": "essential",
      "question": "必須確認質問2",
      "rationale": "理由2"
    },
    {
      "category": "precision",
      "question": "精度向上質問",
      "rationale": "理由"
    },
    {
      "category": "pre_purchase",
      "question": "買付前確認質問",
      "rationale": "理由"
    }
  ]
}
```

## output_schema

```json
{
  "type": "object",
  "required": ["questions"],
  "properties": {
    "questions": {
      "type": "array",
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["category", "question", "rationale"],
        "properties": {
          "category": {"type": "string", "enum": ["essential", "precision", "pre_purchase"]},
          "question": {"type": "string"},
          "rationale": {"type": "string"}
        }
      }
    }
  }
}
```

## changelog

- 2026-05-13 v2: テンプレート埋め込み方式。v1 は1件のみ生成される問題があった。
- 2026-05-12 v1: initial draft
