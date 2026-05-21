# Data Schema — re_invest_os

作成日: 2026-05-12
ベース: blueprint_v0_1.md §15, product_requirements.md
DB: PostgreSQL 16+ (Supabase)
方針: **ユーザー削除可能 / PII最小化 / 分析の再現性 (engine_version + prompt_version 保存)**

---

## 1. 設計原則

1. **PII を別テーブルに分離** → 統計用途では join せずに集計できる
2. **engine_version / prompt_version / model を分析結果に必ず付与** → 再現性
3. **論理削除 (`deleted_at`) → 30日後 GC で物理削除**
4. **すべてのテーブルに `created_at`, `updated_at`**
5. **UUID v7** (時系列ソート可能、推測不能)
6. **JSONB は確定スキーマがない/可変のフィールドだけ** (raw_extraction, assumptions スナップショット)
7. **RLS (Row Level Security)**: `auth.uid() = user_id` を全テーブルに

---

## 2. ER図 (主要関係)

```
users ─┬─< user_profiles
       ├─< user_investment_criteria
       ├─< subscriptions
       ├─< saved_properties >── properties
       ├─< analysis_runs >── properties
       │      ├─< cashflow_schedules
       │      ├─< loan_schedules
       │      ├─< sensitivity_results
       │      ├─< score_results >── score_components
       │      ├─< max_offer_price_results
       │      └─< cross_asset_comparisons
       └─< uploaded_documents >── document_extractions
                                    └─< extraction_corrections (修正履歴)

properties ─┬─< property_sources (URL/書類由来)
            ├─< property_attributes
            └─< rent_rolls >── rent_roll_units
```

---

## 3. テーブル定義

### 3.1 ユーザー・課金

#### `users`
Supabase Auth が管理する。我々は `auth.users` を参照するだけ。

#### `user_profiles`
```sql
create table user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  acquired_at timestamptz default now(),  -- サービス利用開始日
  locale text default 'ja',
  timezone text default 'Asia/Tokyo',
  marketing_opt_in boolean default false,
  research_use_opt_in boolean default true,  -- 匿名統計利用
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);
```
PIIは `display_name` のみ。実名・電話・住所は保持しない。

#### `user_investment_criteria`
```sql
create table user_investment_criteria (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,                       -- "メイン基準" 等
  min_dscr numeric(4, 2) default 1.25,
  min_irr numeric(5, 4) default 0.08,
  min_first_year_atcf_yen bigint default 0,
  max_equity_yen bigint,
  stress_interest_rate numeric(5, 4),       -- 例 0.030
  preferred_ltv numeric(4, 2) default 0.70,
  preferred_hold_years integer default 10,
  is_default boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create unique index on user_investment_criteria(user_id) where is_default = true;
```

#### `subscriptions`
```sql
create table subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan text not null check (plan in ('free', 'light', 'pro', 'heavy')),
  status text not null check (status in ('active', 'canceled', 'past_due', 'trialing')),
  stripe_customer_id text,
  stripe_subscription_id text,
  current_period_end timestamptz,
  cancel_at_period_end boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create unique index on subscriptions(stripe_subscription_id);
create index on subscriptions(user_id, status);
```

#### `supporter_payments`
```sql
create table supporter_payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,  -- 匿名投げ銭も可
  amount_yen integer not null,
  type text not null check (type in ('one_time', 'recurring')),
  stripe_payment_intent_id text,
  message text,                              -- ユーザー任意メッセージ
  created_at timestamptz default now()
);
```

---

### 3.2 物件

#### `properties`
分析対象の物件。同一物件は複数ユーザーに共有される (URLが同じなら同じproperty)。
```sql
create table properties (
  id uuid primary key default gen_random_uuid(),
  property_type text not null check (property_type in (
    'kuubun', 'ittou_apt', 'ittou_mansion', 'kodate', 'land'
  )),
  name text,                                -- "西新宿レジデンス 504号" 等
  address text,                             -- 住所 (PII相当だが公開情報)
  pref_code text,                           -- "13" 等
  city_code text,                           -- 5桁市区町村コード
  lat numeric(9, 6),
  lon numeric(9, 6),
  structure text check (structure in ('wood', 'steel', 'rc', 'src')),
  building_completion_ym text,              -- "YYYY-MM"
  building_area_sqm numeric(10, 2),
  land_area_sqm numeric(10, 2),
  num_units integer,
  floor_plan text,
  nearest_station text,
  station_walk_min integer,
  zoning text,
  bcr_pct numeric(5, 2),
  far_pct numeric(7, 2),
  source_url text,                          -- 元URL
  source_url_hash text,                     -- URL正規化ハッシュ (重複検出)
  raw_attributes jsonb,                     -- 抽出時の生データスナップショット
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);
create index on properties(source_url_hash);
create index on properties(pref_code, city_code);
create index on properties using gist (
  ll_to_earth(lat::float8, lon::float8)
);
```

#### `property_listing_prices`
価格の履歴 (掲載価格は変動する)。
```sql
create table property_listing_prices (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  asking_price_yen bigint not null,
  observed_at timestamptz not null default now(),
  source text,                              -- "rakumachi", "suumo", "user_input"
  created_at timestamptz default now()
);
create index on property_listing_prices(property_id, observed_at desc);
```

#### `property_sources`
どのURL・資料からこの物件情報が来たか。
```sql
create table property_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  source_type text not null check (source_type in (
    'url', 'document', 'manual'
  )),
  source_ref text,                          -- URL or document_id
  fetched_at timestamptz default now()
);
```

---

### 3.3 アップロード資料

#### `uploaded_documents`
```sql
create table uploaded_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  storage_path text not null,                -- Supabase Storage パス
  original_filename text,
  mime_type text,
  size_bytes bigint,
  classified_type text check (classified_type in (
    'property_brochure', 'rent_roll', 'income_statement',
    'fixed_asset_tax', 'registry_certificate', 'repair_history',
    'management_report', 'lease_contract', 'construction_cert',
    'long_term_repair', 'important_matter', 'listing_url', 'unknown'
  )),
  classified_confidence numeric(3, 2),
  pages_count integer,
  pii_masked boolean default false,
  retention_until timestamptz,               -- 30日後に物理削除
  created_at timestamptz default now(),
  deleted_at timestamptz
);
create index on uploaded_documents(user_id, created_at desc);
create index on uploaded_documents(retention_until) where deleted_at is null;
```

#### `document_extractions`
LLM抽出結果。
```sql
create table document_extractions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references uploaded_documents(id) on delete cascade,
  user_id uuid not null,                    -- 冗長化 (RLS高速化)
  document_type text not null,
  schema_version text not null,             -- "property_brochure_v1" 等
  model text not null,                      -- "claude-haiku-4-5"
  prompt_version text not null,             -- "v1"
  raw_output jsonb not null,
  validated_output jsonb not null,
  extraction_confidence numeric(3, 2),
  field_confidences jsonb,                  -- 項目別 confidence
  inferred_fields text[],
  warnings text[],
  processing_ms integer,
  cost_usd numeric(10, 6),
  created_at timestamptz default now()
);
```

#### `extraction_corrections`
ユーザーが修正した内容 (将来のFT用教師データ)。
```sql
create table extraction_corrections (
  id uuid primary key default gen_random_uuid(),
  extraction_id uuid not null references document_extractions(id) on delete cascade,
  user_id uuid not null,
  field_path text not null,                 -- "asking_price_yen" 等
  ai_value jsonb,
  user_value jsonb,
  correction_reason text,
  created_at timestamptz default now()
);
```

#### `rent_rolls` / `rent_roll_units`
```sql
create table rent_rolls (
  id uuid primary key default gen_random_uuid(),
  property_id uuid references properties(id) on delete cascade,
  document_id uuid references uploaded_documents(id) on delete set null,
  rent_roll_date date,
  total_monthly_rent_yen bigint,
  total_annual_rent_yen bigint,
  occupancy_rate numeric(4, 3),
  created_at timestamptz default now()
);

create table rent_roll_units (
  id uuid primary key default gen_random_uuid(),
  rent_roll_id uuid not null references rent_rolls(id) on delete cascade,
  unit_number text,
  floor integer,
  floor_plan text,
  area_sqm numeric(7, 2),
  contract_rent_yen integer,
  common_area_fee_yen integer,
  parking_fee_yen integer,
  deposit_months numeric(3, 1),
  key_money_months numeric(3, 1),
  contract_start_date date,
  contract_end_date date,
  is_occupied boolean,
  arrears_status text check (arrears_status in ('none', 'current', 'past', 'unknown')),
  tenant_type text check (tenant_type in ('individual', 'corporate', 'unknown')),
  created_at timestamptz default now()
);
```

---

### 3.4 分析

#### `analysis_runs`
1分析 = 1行。
```sql
create table analysis_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  property_id uuid references properties(id) on delete set null,
  engine_version text not null,            -- "0.1.0"
  assumptions_snapshot jsonb not null,     -- Pydantic Assumptions JSON
  market_context jsonb,                    -- MarketContext (近傍データ)
  data_quality jsonb,                      -- DataQuality
  processing_ms integer,
  created_at timestamptz default now(),
  deleted_at timestamptz
);
create index on analysis_runs(user_id, created_at desc);
create index on analysis_runs(property_id, created_at desc);
```

#### `cashflow_schedules`
年次CF (10年×行)。`analysis_run_id` で全行取得。
```sql
create table cashflow_schedules (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  year integer not null,
  gpi_yen bigint,
  vacancy_loss_yen bigint,
  egi_yen bigint,
  opex_yen bigint,
  noi_yen bigint,
  debt_service_yen bigint,
  btcf_yen bigint,
  depreciation_yen bigint,
  interest_expense_yen bigint,
  principal_payment_yen bigint,
  taxable_income_yen bigint,
  tax_yen bigint,
  atcf_yen bigint,
  loan_balance_end_yen bigint
);
create unique index on cashflow_schedules(analysis_run_id, year);
```

#### `loan_schedules`
月次返済 (360行)。
```sql
create table loan_schedules (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  period_month integer not null,
  payment_yen integer,
  interest_yen integer,
  principal_yen integer,
  balance_yen bigint
);
create unique index on loan_schedules(analysis_run_id, period_month);
```

#### `score_results` / `score_components`
```sql
create table score_results (
  analysis_run_id uuid primary key references analysis_runs(id) on delete cascade,
  total numeric(5, 2),
  evaluation text check (evaluation in ('健全', '中立', '要警戒')),
  created_at timestamptz default now()
);

create table score_components (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  name text not null,
  score numeric(5, 2),
  max_score numeric(5, 2),
  detail text
);
create index on score_components(analysis_run_id);
```

#### `max_offer_price_results`
```sql
create table max_offer_price_results (
  analysis_run_id uuid primary key references analysis_runs(id) on delete cascade,
  current_price_yen bigint,
  max_price_yen bigint,
  safe_price_yen bigint,
  required_discount_yen bigint,
  binding_constraints text[],
  iterations integer,
  converged boolean,
  targets_used jsonb,
  created_at timestamptz default now()
);
```

#### `sensitivity_results`
```sql
create table sensitivity_results (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  scenario text not null,                  -- 'base', 'rent_down_5', 等
  atcf_year1_yen bigint,
  irr numeric(7, 4),
  dscr_min numeric(5, 2),
  net_proceeds_yen bigint,
  judgment text check (judgment in ('good', 'warn', 'bad'))
);
create unique index on sensitivity_results(analysis_run_id, scenario);
```

#### `cross_asset_comparisons`
```sql
create table cross_asset_comparisons (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  asset_class text not null,
  expected_return numeric(7, 4),
  premium_over_re_pt numeric(7, 2),
  liquidity text,
  effort text
);
```

#### `warning_flags`
業者資料の甘さ・矛盾検出。
```sql
create table warning_flags (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  flag_type text not null,                 -- 'gross_yield_only', 'rent_roll_outdated', 等
  severity text check (severity in ('info', 'warn', 'critical')),
  message text not null,
  detected_at timestamptz default now()
);
```

---

### 3.5 保存・比較

#### `saved_properties`
```sql
create table saved_properties (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  property_id uuid not null references properties(id) on delete cascade,
  notes text,
  pinned boolean default false,
  created_at timestamptz default now(),
  unique (user_id, property_id)
);
```

#### `watchlist_items`
```sql
create table watchlist_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  property_id uuid not null references properties(id) on delete cascade,
  last_known_price_yen bigint,
  price_alert_pct numeric(4, 2),
  enabled boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

#### `comparison_boards` / `comparison_board_items`
```sql
create table comparison_boards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  description text,
  created_at timestamptz default now()
);

create table comparison_board_items (
  id uuid primary key default gen_random_uuid(),
  board_id uuid not null references comparison_boards(id) on delete cascade,
  analysis_run_id uuid not null references analysis_runs(id) on delete cascade,
  position integer,
  created_at timestamptz default now()
);
```

---

### 3.6 公的データ (MLIT, e-Stat, 国土数値情報)

#### `mlit_land_prices_public_notice`
```sql
create table mlit_land_prices_public_notice (
  point_id bigint not null,
  year integer not null,
  pref_code text not null,
  city_code text,
  ward_town_village_name text,
  lat numeric(9, 6),
  lon numeric(9, 6),
  current_price_yen integer,
  last_year_price_yen integer,
  raw jsonb,
  fetched_at timestamptz,
  primary key (point_id, year)
);
create index on mlit_land_prices_public_notice (pref_code, year);
```

#### `mlit_trade_prices`
```sql
create table mlit_trade_prices (
  id uuid primary key default gen_random_uuid(),
  pref_code text,
  city_code text,
  district text,
  trade_year integer,
  trade_quarter integer,
  building_type text,
  area_sqm numeric(10, 2),
  price_yen bigint,
  price_per_sqm_yen integer,
  raw jsonb,
  fetched_at timestamptz
);
create index on mlit_trade_prices (pref_code, city_code, trade_year);
```

#### `rent_market`
```sql
create table rent_market (
  city_code text not null,
  survey_year integer not null,
  ownership_type text not null,
  rent_per_sqm_yen integer,
  primary key (city_code, survey_year, ownership_type)
);
```

---

### 3.7 イベント・品質

#### `user_events`
PostHog補完用。匿名化済みアクション。
```sql
create table user_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  session_id text,
  event_name text not null,
  properties jsonb,
  occurred_at timestamptz default now()
);
create index on user_events(user_id, occurred_at desc);
create index on user_events(event_name, occurred_at desc);
```

#### `data_quality_scores`
分析ごとの信頼度ログ。
```sql
create table data_quality_scores (
  analysis_run_id uuid primary key references analysis_runs(id) on delete cascade,
  document_completeness numeric(3, 2),
  extraction_confidence numeric(3, 2),
  user_confirmed boolean,
  created_at timestamptz default now()
);
```

---

## 4. JSONスキーマ (アプリ内データ構造)

### 4.1 Assumptions (分析入力)

Pydantic v2 で定義。`packages/financial-engine/src/re_engine/models.py` が正本。
DB の `analysis_runs.assumptions_snapshot` には JSON 化したものを保存。

```jsonc
{
  "engine_version": "0.1.0",
  "property": {
    "property_type": "kuubun",
    "purchase_price_yen": 39800000,
    "land_value_yen": 8000000,
    "building_value_yen": 31800000,
    "structure": "rc",
    "building_completion_ym": "2011-04",
    "acquisition_year": 2026,
    "building_area_sqm": 38.4,
    "location_pref": "13",
    "location_city": "新宿区"
  },
  "income": {
    "gpi_monthly_yen": 145000,
    "vacancy_rate": 0.05,
    "rent_growth_rate": -0.005
  },
  "opex": { /* ... */ },
  "loan": { /* ... */ },
  "tax": { /* ... */ },
  "exit": { /* ... */ },
  "acquisition": { /* ... */ }
}
```

### 4.2 PropertyBrochureExtraction

仕様: `ai_document_extraction_spec.md §5.1`

### 4.3 RentRollExtraction

仕様: `ai_document_extraction_spec.md §5.2`

---

## 5. インデックス戦略

| クエリ | インデックス |
|---|---|
| ユーザーの最近の分析 | `analysis_runs(user_id, created_at desc)` |
| 物件の過去分析 | `analysis_runs(property_id, created_at desc)` |
| URL重複検出 | `properties(source_url_hash)` |
| 公的データ (近傍検索) | `properties(pref_code, city_code)` + `gist(ll_to_earth(lat, lon))` |
| 保有期限切れ書類 | `uploaded_documents(retention_until) where deleted_at is null` |
| 価格履歴 | `property_listing_prices(property_id, observed_at desc)` |

---

## 6. RLS (Row Level Security)

すべてのユーザー個別テーブルに `policy` を設定:

```sql
alter table analysis_runs enable row level security;
create policy "users see own analyses"
  on analysis_runs for select
  using (auth.uid() = user_id);
create policy "users insert own analyses"
  on analysis_runs for insert
  with check (auth.uid() = user_id);
create policy "users update own analyses"
  on analysis_runs for update
  using (auth.uid() = user_id);
create policy "users delete own analyses"
  on analysis_runs for delete
  using (auth.uid() = user_id);
```

同パターンを以下に適用:
- user_profiles, user_investment_criteria, subscriptions
- uploaded_documents, document_extractions, extraction_corrections
- saved_properties, watchlist_items, comparison_boards
- analysis_runs と全子テーブル

公的データ (`mlit_*`, `rent_market`) は read-only / public。

---

## 7. データ保持・削除

| データ | 保持期間 | 削除トリガー |
|---|---|---|
| 生HTML (`raw_html_snapshots`) | 30日 | バッチGC |
| アップロード原資料 | 30日 | retention_until で expire |
| 抽出済み構造化データ | 長期 | ユーザー削除 or 退会 |
| 分析履歴 | 長期 | ユーザー削除 or 退会 |
| ユーザー削除 | `deleted_at` set → 30日後に物理削除 (バッチ) | アカウント設定 |
| `user_events` | 12ヶ月 | バッチGC (匿名化済みなので緩い) |
| PII (実名・電話) | **保存しない** | — |

---

## 8. マイグレーション運用

- **ツール**: Supabase CLI (`supabase migration new <name>`)
- **配置**: `infra/migrations/YYYYMMDDHHMMSS_<name>.sql`
- **方針**:
  - 1マイグレーション = 1論理変更
  - データ変換が必要なら別マイグレーションに分離
  - ロールバック手順を migration コメントに記載
  - production 適用前に staging で必ず走らせる
  - DDL のみ (DMLは別ジョブで)

---

## 9. シーケンス: 物件分析の典型フロー

```
1. ユーザーがURL貼り付け
   → POST /api/analyze/url { url }
   → job 作成 (analysis_jobs ※将来テーブル)
2. Worker が url fetch + raw_html_snapshots に保存
3. AI で extraction → document_extractions に保存
4. properties (なければ新規 / あれば既存に紐付け)
5. property_listing_prices に価格追加
6. 抽出結果をユーザーが確認・修正
   → extraction_corrections に保存
7. ユーザーが「分析実行」
   → POST /api/analyze { assumptions }
   → run_full_analysis() → AnalysisResult
   → analysis_runs + cashflow_schedules + loan_schedules + score_results + ...
8. 比較ボード追加・保存
   → saved_properties / comparison_boards
9. ユーザー削除
   → deleted_at = now() を関連テーブルに
   → 30日後にバッチで物理削除
```

---

## 10. 未確定 / TODO

- `analysis_jobs` テーブル (非同期ジョブ管理) は Phase 4 で追加
- `property_features` (地理的特徴量) は Phase 5 で追加
- `hazard_features` (公的ハザード判定) は Phase 6 で追加
- `nlni_*` (国土数値情報) のインポート手順は別ドキュメント
- 物件の重複統合 (同一物件で複数URLがある場合) の運用ルール
- 監査ログ (誰が誰の何を見た) の保持方針 (Pro+のみ?)
