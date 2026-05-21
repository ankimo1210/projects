# AI Document Extraction Spec — re_invest_os

作成日: 2026-05-11
パッケージ: `packages/document-schemas/`, 利用者: `apps/api/` & `apps/worker/`
方針: **AIは「読む・分類する・説明する」のみ / 数値計算は financial-engine に任せる / 抽出結果は必ずスキーマ検証**

---

## 1. 設計原則

1. **classification-first**: 資料を最初に種別分類 → 種別ごとのスキーマで抽出
2. **structured output**: OpenAI Structured Outputs / Anthropic tool_use で JSON Schema 強制
3. **null safe**: 不明な項目は `null`、推測は `inferred=true`、確信度を項目ごとに付与
4. **regex/parser first**: 構造化テキスト (Excel/HTMLテーブル) は決定論パーサーを先に試す。LLMは補完用
5. **PII除去**: LLM送信前にできる範囲で氏名・電話・メールをマスク
6. **ログ重視**: prompt_version, model, raw_output, validated_output, user_corrections をすべて保存
7. **失敗時のフォールバック**: 3段階 (Tier1=取得失敗 / Tier2=抽出失敗 / Tier3=ジオコード失敗) のフォールバックUI

---

## 2. パイプライン全体像

```
入力 (URL / PDF / 画像 / Excel)
  ↓
資料種別分類 (classify_document)
  ↓
種別固有のスキーマ選択 (SCHEMA_BY_TYPE)
  ↓
前処理
  - URL: requests + BeautifulSoup → テキスト化 (8000字上限)
  - PDF: PyMuPDF → page-by-page テキスト (+ 画像はvision)
  - Excel: openpyxl → table-as-markdown
  - 画像: そのままvision model へ
  ↓
PII マスク (mask_pii)
  ↓
regex/parser pass (decision-rule抽出)
  ↓
LLM 抽出 (Structured Output)
  ↓
スキーマ検証 (pydantic)
  ↓
正規化 (normalize_currency, normalize_area, normalize_date)
  ↓
矛盾検出 (cross_check)
  ↓
信頼度スコア計算
  ↓
DB保存 + ユーザー確認UI
```

---

## 3. 資料種別 (DocumentType)

```python
class DocumentType(str, Enum):
    property_brochure = "property_brochure"        # 販売図面
    rent_roll = "rent_roll"                        # レントロール
    income_statement = "income_statement"          # 簡易収支表
    fixed_asset_tax_statement = "fixed_asset_tax"  # 固定資産税通知
    registry_certificate = "registry_certificate"  # 登記簿
    repair_history = "repair_history"              # 修繕履歴
    management_report = "management_report"        # 管理報告書
    lease_contract = "lease_contract"              # 賃貸借契約書
    construction_certificate = "construction_cert" # 建築確認・検査済証
    long_term_repair_plan = "long_term_repair"     # 長期修繕計画
    important_matter_report = "important_matter"   # 重要事項調査報告書
    listing_url = "listing_url"                    # 物件URL (楽待/SUUMO等)
    unknown = "unknown"
```

MVP対応 (v0): `property_brochure`, `rent_roll`, `income_statement`, `listing_url`
v1: `fixed_asset_tax_statement`, `repair_history`
v2: 残り全部

---

## 4. 分類プロンプト

### 4.1 system

```text
あなたは日本の不動産投資資料を分類するアシスタントです。
ユーザーがアップロードした資料が以下のどれに該当するか判定してください。

- property_brochure (販売図面・物件概要書)
- rent_roll (レントロール・家賃明細)
- income_statement (簡易収支表・キャッシュフロー表)
- fixed_asset_tax (固定資産税納税通知書・課税明細)
- registry_certificate (登記事項証明書・登記簿謄本)
- repair_history (修繕履歴・大規模修繕実施記録)
- management_report (管理委託・管理状況報告)
- lease_contract (賃貸借契約書)
- construction_cert (建築確認済証・検査済証)
- long_term_repair (長期修繕計画)
- important_matter (重要事項調査報告書)
- unknown

判断基準:
- 文書の表題、定型書式、含まれる項目から判定する
- 推測で断定しない。確信度が低ければ unknown
- 複数該当の可能性があれば最も主要なものを返す

出力: 指定JSONスキーマに従う
```

### 4.2 出力スキーマ

```json
{
  "type": "object",
  "required": ["document_type", "confidence", "reason"],
  "properties": {
    "document_type": {"type": "string", "enum": ["property_brochure", ...]},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "reason": {"type": "string", "description": "判定理由を1文で"}
  }
}
```

### 4.3 モデル

- 主: `claude-haiku-4-5` (安価・高速)
- フォールバック: `gpt-4.1-mini`

---

## 5. 抽出スキーマ

### 5.1 販売図面 (PropertyBrochureExtraction)

```python
class PropertyBrochureExtraction(BaseModel):
    # 物件基本
    property_name: str | None
    address: str | None
    asking_price_yen: int | None
    transaction_type: Literal["sale", "lease", "unknown"] | None
    ad_expiration_date: str | None         # ISO

    # 交通
    nearest_station: str | None
    station_walk_min: int | None
    second_station: str | None

    # 土地・建物
    land_area_sqm: float | None
    building_area_sqm: float | None
    exclusive_area_sqm: float | None       # 区分の専有面積
    structure: Literal["wood", "steel", "rc", "src", "unknown"] | None
    floors_above: int | None
    floors_below: int | None
    num_units: int | None
    floor_plan: str | None                 # "2LDK"等
    build_year_month: str | None           # "YYYY-MM"

    # 用途・法規
    zoning: str | None                     # 用途地域
    fire_zone: str | None                  # 防火地域等
    bcr_pct: float | None                  # 建ぺい率
    far_pct: float | None                  # 容積率
    road_frontage: str | None              # 接道
    rights: Literal["fee_simple", "leasehold", "other", "unknown"] | None
    current_status: str | None             # 現況 (居住中・空室等)
    delivery_condition: str | None

    # 収益
    gross_yield_pct: float | None
    estimated_full_rent_monthly_yen: int | None  # 満室想定月額賃料
    actual_rent_monthly_yen: int | None
    management_fee_monthly_yen: int | None
    repair_reserve_monthly_yen: int | None

    # メタ
    notes: str | None
    field_confidences: dict[str, float]    # 項目ごとの確信度
    inferred_fields: list[str]             # 推測で埋めた項目
```

抽出項目数: 26項目 (青写真6.2準拠)。

### 5.2 レントロール (RentRollExtraction)

```python
class RentRollUnit(BaseModel):
    unit_number: str | None                # 部屋番号
    floor: int | None
    floor_plan: str | None
    area_sqm: float | None
    contract_rent_yen: int | None          # 月額
    common_area_fee_yen: int | None        # 共益費
    parking_fee_yen: int | None
    other_income_yen: int | None
    deposit_months: float | None
    key_money_months: float | None
    contract_start_date: str | None        # ISO
    contract_end_date: str | None
    is_occupied: bool | None
    vacancy_period_months: int | None
    arrears_status: Literal["none", "current", "past", "unknown"] | None
    tenant_type: Literal["individual", "corporate", "unknown"] | None
    renewal_fee_months: float | None
    free_rent_months: int | None

class RentRollExtraction(BaseModel):
    units: list[RentRollUnit]
    rent_roll_date: str | None             # 更新日 ISO
    total_monthly_rent_yen: int | None     # AIが集計した合計 (検証用)
    total_annual_rent_yen: int | None
    occupancy_rate: float | None
    raw_table_markdown: str | None         # トレース用
    field_confidences: dict[str, float]
```

抽出項目: 21項目 (青写真6.3準拠)。

### 5.3 簡易収支表 (IncomeStatementExtraction)

```python
class IncomeStatementExtraction(BaseModel):
    period_label: str | None               # "年間" / "月間" / "2025年度"
    gross_income_yen: int | None
    vacancy_loss_yen: int | None
    effective_gross_income_yen: int | None
    management_fee_yen: int | None
    repair_cost_yen: int | None
    insurance_yen: int | None
    fixed_asset_tax_yen: int | None
    other_opex_yen: int | None
    total_opex_yen: int | None
    noi_yen: int | None
    debt_service_yen: int | None
    btcf_yen: int | None
    field_confidences: dict[str, float]
```

### 5.4 物件URL (ListingExtraction)

楽待・SUUMO・健美家など。PoCの `property_scraper.py` の知見を継承するが、新規実装。

```python
class ListingExtraction(BaseModel):
    platform: Literal["rakumachi", "suumo", "kenbiya", "other"]
    url: str
    fetched_at: str                        # ISO datetime
    raw_html_hash: str                     # snapshot参照
    brochure_data: PropertyBrochureExtraction  # サブセット
    listing_meta: dict                     # platform固有
```

スクレイピング方針:
- ユーザーが貼ったURLのみ取得 (一覧クロール禁止)
- User-Agent: ブラウザ偽装
- 同一ホストへのrate limit: 5秒1リクエスト
- HTML snapshot: 30日保管、ユーザー削除で30日後物理削除
- allowlist: rakumachi.jp / suumo.jp / kenbiya.com (起動時)
- kill switch: 環境変数 `SCRAPING_DISABLED_HOSTS` で即停止

### 5.5 固定資産税通知 (FixedAssetTaxExtraction) — v1

```python
class FixedAssetTaxExtraction(BaseModel):
    tax_year: int | None
    land_taxable_value_yen: int | None     # 土地課税標準額
    building_taxable_value_yen: int | None # 建物課税標準額
    land_property_tax_yen: int | None      # 土地固定資産税
    building_property_tax_yen: int | None  # 建物固定資産税
    city_planning_tax_yen: int | None      # 都市計画税
    total_yen: int | None
```

---

## 6. 抽出プロンプト方針

### 6.1 共通ルール

```text
- 不明な項目は null
- 推測した値は inferred_fields に追加
- 項目ごとに field_confidences (0.0〜1.0) を付与
- 賃料: 月額/年額/週額/日額を明示。不明なら notes に記録
- 通貨: 円/万円/千円を正規化 (円int)
- 日付: ISO 8601 (YYYY-MM-DD)
- 面積: ㎡ (坪表記なら 1坪=3.30578㎡で換算)
- 税込/税別が不明なら notes に記録
- 賃借人個人名・電話番号・メールは抽出しない (マスク済みのテキストを受け取る)
- 出力は指定JSONスキーマに完全準拠
```

### 6.2 販売図面プロンプト (system)

```text
あなたは日本の不動産販売図面を構造化抽出するアシスタントです。
販売図面の文字列・画像から、所定のスキーマに従ってJSONで返してください。

注意:
- 表面利回りは「年間想定賃料 / 価格 × 100」。掲載なくても計算できる場合は inferred_fields に追加
- 構造は「木造」→ "wood"、「RC造/鉄筋コンクリート」→ "rc"、「鉄骨/S造」→ "steel"、「SRC」→ "src"
- 区分マンションの管理費・修繕積立金は monthly_yen で
- 一棟の satellite (戸数・各階数) は num_units / floors_above / floors_below に分離
- 接道は文字列で保持 ("南側公道6m" 等)
- "現況" は文字列で ("空室" / "賃貸中" / "オーナーチェンジ" 等)

出力: PropertyBrochureExtraction スキーマ
```

### 6.3 レントロールプロンプト (system)

```text
あなたは日本の不動産レントロールを構造化抽出するアシスタントです。
表形式のレントロール (テキスト・画像・Excel変換結果) から、各部屋の情報をJSON配列で返してください。

注意:
- 1行=1部屋として扱う
- 空室は contract_rent_yen=null, is_occupied=false
- 共益費・駐車場は分離して抽出
- 礼金・敷金は「月額×何ヶ月」(deposit_months/key_money_months) として保持
- 契約開始日が「不明」「-」「相談」等の場合は null
- レントロール更新日が文書内にあれば rent_roll_date に
- 個人名・法人名は抽出しない (空欄でよい)
- 抽出した units の月額賃料合計を total_monthly_rent_yen に入れる (検証用)

出力: RentRollExtraction スキーマ
```

---

## 7. 信頼度・矛盾検出

### 7.1 抽出信頼度の計算

```python
def extraction_confidence(extraction: BaseModel) -> ExtractionConfidence
```

- 必須項目 (e.g., 価格・所在地・面積) の埋まり率
- field_confidences の平均
- inferred_fields の割合 (高いほど↓)
- スキーマ検証の通過

ランク:
- `high`: 0.85+
- `partial`: 0.5〜0.85
- `low`: <0.5

### 7.2 矛盾検出 (cross_check)

| チェック | 内容 |
|---|---|
| brochure × rent_roll | 戸数一致、満室想定賃料 ≒ レントロール合計 |
| brochure × income_statement | NOI整合性 |
| brochure: 面積妥当性 | 専有面積 ≤ 建物面積 |
| brochure: 利回り再計算 | gross_yield_pct ≒ rent*12 / price |
| rent_roll: 部屋数 | brochure.num_units と一致 |
| 築年月 | 通知書の年と整合 |

矛盾は `warning_flags` テーブルに保存し、UIで警告表示。

---

## 8. PII マスク

LLM送信前に regex で除去:
- 氏名候補 (「○○ 様」「○○様方」)
- 電話番号 (`\d{2,4}-\d{2,4}-\d{4}`, `0\d{9,10}`)
- メール (`\S+@\S+\.\S+`)
- 印影画像は OCR 前に除去 (将来)

マスク後のテキスト/画像のみLLMへ送信。原本は Supabase Storage の private bucket に暗号化保存、30日後削除。

---

## 9. モデル選定

| タスク | 主モデル | フォールバック | 想定コスト/req |
|---|---|---|---:|
| 資料分類 | claude-haiku-4-5 | gpt-4.1-mini | <$0.001 |
| 販売図面抽出 (テキスト) | claude-haiku-4-5 | gpt-4.1-mini | ~$0.005 |
| 販売図面抽出 (画像) | claude-sonnet-4-6 | gpt-4.1 vision | ~$0.02 |
| レントロール (Excel/markdown) | claude-haiku-4-5 | gpt-4.1-mini | ~$0.005 |
| レントロール (画像) | claude-sonnet-4-6 | gpt-4.1 vision | ~$0.03 |
| 3行サマリー生成 | claude-haiku-4-5 | gpt-4.1-mini | ~$0.002 |
| 確認質問リスト生成 | claude-haiku-4-5 | gpt-4.1-mini | ~$0.003 |
| 業者資料の甘さ説明 | claude-sonnet-4-6 | gpt-4.1 | ~$0.01 |

月間1000分析 × 平均$0.05 = **$50/月** が初期想定。$300/月上限。

---

## 10. 学習データ蓄積

将来の特化AI / ファインチューニング用に以下を保存:

```python
class ExtractionRecord(BaseModel):
    id: UUID
    document_id: UUID
    document_type: DocumentType
    model: str
    prompt_version: str
    raw_input_hash: str                    # PIIマスク後のテキスト/画像
    raw_output: dict                       # LLM生出力
    validated_output: dict                 # スキーマ検証後
    extraction_confidence: float
    user_corrections: list[FieldCorrection] | None  # ユーザー修正
    final_output: dict                     # 最終確定値
    created_at: datetime
```

`FieldCorrection`:
```python
class FieldCorrection(BaseModel):
    field_path: str                        # "asking_price_yen"
    ai_value: Any
    user_value: Any
    correction_reason: str | None
```

ファインチューニング検討目安 (青写真11.5):
- 販売図面 300〜500件
- レントロール 200〜300件
- 収支表 100〜200件

---

## 11. テスト・評価

### 11.1 fixture-based テスト

```
tests/fixtures/documents/
  brochure_kuubun_01.pdf  +  brochure_kuubun_01.expected.json
  brochure_ittou_01.pdf   +  brochure_ittou_01.expected.json
  rent_roll_01.pdf        +  rent_roll_01.expected.json
  rent_roll_02.xlsx       +  rent_roll_02.expected.json
  url_rakumachi_01.html   +  url_rakumachi_01.expected.json
```

評価指標 (項目別):
- exact_match
- numerical_within_tolerance (±1%)
- text_normalized_match
- field_recall (null率)

合格ライン:
- 価格・面積・所在地・賃料・築年月: **95%以上 exact** (規定許容)
- 構造・用途地域・接道: **85%以上**
- その他: **70%以上**

### 11.2 prompt version 管理

```
docs/prompts/
  classify_document_v1.md
  property_brochure_v1.md
  rent_roll_v1.md
  income_statement_v1.md
  summary_3line_v1.md
  inquiry_questions_v1.md
```

各プロンプトは `version`, `model_recommendations`, `system`, `user_template`, `examples`, `changelog` を含む。

### 11.3 オンライン評価

- 抽出後のユーザー修正率を項目別に計測 (PostHog event)
- 修正率10%超の項目 → プロンプト改善 or スキーマ見直し
- A/B (prompt v1 vs v2) は同じ document に対して並行実行可能

---

## 12. 失敗時のフォールバックUI (青写真6.8, 13.3関連)

| Tier | 失敗ケース | 対処 |
|---|---|---|
| Tier1 | HTML取得失敗 (403/timeout) | エラー + 「手動でPDFアップロード or 直接入力」フォーム |
| Tier2 | 抽出で価格=None | エラー + fallback form。部分抽出はwarningで継続 |
| Tier3 | ジオコーディング失敗 | warning、近傍比較スキップ、シミュレーションは続行 |
| Tier4 | LLMタイムアウト | retry 1回 → フォールバックモデル → 手動入力誘導 |

---

## 13. 法務・倫理

- スクレイピングは allowlist + ユーザー貼り付けのみ。一覧クロールしない
- スクレイピング先からの停止要請があれば即 kill switch
- ユーザーアップロード資料は不動産会社・第三者に提供しない (利用規約に明記)
- 賃借人個人情報 (PII) は LLM 送信前にマスク、最終出力にも含めない
- ユーザー削除APIでは raw_input_hash も含めて削除

---

## 14. 既知の制約・将来課題

- 手書きレントロールの抽出精度は低い (OCR + LLM併用検討)
- スキャンPDF (画像のみ) は vision モデルが必要 (コスト↑)
- 複数物件が1ファイルに含まれる場合は v0 では非対応 (警告のみ)
- 海外不動産・外貨建ては v0 対象外
- 民泊・サービスアパートメントの収益構造は v0 対象外
- 共有持分・底地・借地権は v0 では警告のみ
