# Top7 実装計画 — 既存コードとの整合性レビュー

作成日: 2026-05-23
対象: `docs/roadmap/top7_implementation_plan.md`
目的: 計画を着手前にギャップを洗い出し、最小差分で実装するための前準備。

---

## 0. 結論サマリ

| 区分 | 件数 | 概要 |
|---|---|---|
| そのまま再利用可 | 4 | max_offer 二分探索 / sensitivity / NG表現フィルタ / engine_version + prompt_versions 保存 |
| 拡張で対応 | 5 | max_offer に shock 適用ラッパー / 既存 `analyses` → `analysis_runs` リネーム / source 追跡フィールド追加 / `/api/*` プレフィックス整備 / Next 既存ルート → /deals/[id] への動線 |
| 新規実装 | 7 | deals / bid_ranges / assumption_risks / checklist (ルール版) / investment_memos / watchlist / evidence_cards |
| 計画と既存の対立 | 3 | データモデル粒度 / バックエンド ディレクトリ命名 / 既存 inquiry_questions と Plan C3 の二重化 |
| 計画の前提が未充足 | 2 | `normalized_property` のスキーマ / `Assumptions` への source 情報の追加 |

詳細は §1 以降。

---

## 1. データモデル整合性

### 1.1 既存スキーマ

`infra/migrations/v1_analyses.sql` の `analyses` テーブルが現状の中核:

| 列 | 用途 |
|---|---|
| `id` | UUID |
| `source_type` | url / document / manual |
| `source_ref` | URL or filename |
| `engine_version`, `prompt_versions` | 再現性 |
| `extracted` (JSON) | PropertyBrochureExtraction |
| `assumptions` (JSON) | Assumptions |
| `analysis_result` (JSON) | AnalysisResult |
| `score_total`, `score_result` | スコア |
| `noi_cap`, `dscr_y1`, `atcf_y1`, `equity_irr` | ソート用 KPI |
| `user_id` (Phase 3) | 認証 |
| `pii_redactions`, `warnings` | メタ |

→ 1 物件 = 1 行。**deal 概念なし、複数分析の履歴なし**。

### 1.2 計画とのギャップ

| 計画 | 既存 | 判断 |
|---|---|---|
| `deals` (1:N analysis_runs) | 存在しない | **新規追加** |
| `analysis_runs` | `analyses` が事実上同等 | **リネーム + `deal_id` FK 追加** |
| `input_snapshot_json` | `assumptions` 列で代替可 | 列名統一 (rename or alias) |
| `normalized_property_json` | `extracted` 列があるが正規化前 | **新規列 or 抽出層に正規化ステップ追加** |
| `metrics_json` | `analysis_result.kpi` で代替可 | 既存列にマップ |
| `sensitivity_json`, `max_bid_json` | 都度API呼び出し (永続化なし) | **新規列 or 子テーブル化検討** |

### 1.3 推奨マイグレーション (v2)

最小差分案:

```sql
-- v2: deals 概念導入 + analyses → analysis_runs
CREATE TABLE deals (...);  -- 計画 A1 のまま
ALTER TABLE analyses RENAME TO analysis_runs;
ALTER TABLE analysis_runs ADD COLUMN deal_id TEXT REFERENCES deals(id);
ALTER TABLE analysis_runs ADD COLUMN normalized_property_json TEXT;
ALTER TABLE analysis_runs ADD COLUMN sensitivity_json TEXT;
ALTER TABLE analysis_runs ADD COLUMN max_bid_json TEXT;
-- 既存 1 行 = 暗黙 deal、バックフィル不要 (dev のみ、prod 未稼働)
```

`assumptions` 列は `input_snapshot_json` の役割を兼ねる前提で残す (列名は変えない)。

### 1.4 新規テーブル (Plan A3-A8)

`bid_ranges`, `assumption_risks`, `checklist_items`, `market_evidence_cards`, `investment_memos`, `watchlist_items` は **すべて新規**。計画通りでよい。
ただし `analysis_run_id` FK は **rename 後の `analysis_runs(id)`** を参照。

---

## 2. バックエンド再利用ポイント

### 2.1 max_offer (✅ 再利用可、ただし拡張必要)

既存: `packages/financial-engine/src/re_engine/max_offer.py`
- `InvestorTargets(min_dscr, min_irr, min_first_year_atcf_yen, max_equity_yen, stress_interest_rate)`
- `max_offer_price()` が二分探索で1価格を返す
- `_rebuild_at_price()` で LTV 維持リバランス済

**ギャップ**: Plan C1 の `BidPolicy` には `rent_shock`, `vacancy_shock`, `rate_shock`, `opex_shock` の 4 種が必要。
現状の `stress_interest_rate` のみでは不足。

**実装方針**:
```python
# packages/financial-engine/src/re_engine/bid_ranges.py (新規)
def _apply_shocks(base: Assumptions, policy: BidPolicy) -> Assumptions:
    a = copy.deepcopy(base)
    a.income.gpi_monthly_yen = int(a.income.gpi_monthly_yen * (1 + policy.rent_shock))
    a.income.vacancy_rate = min(1.0, a.income.vacancy_rate + policy.vacancy_shock)
    a.loan.interest_rate = min(1.0, a.loan.interest_rate + policy.rate_shock)
    # opex_shock は固定費系を一律スケール
    return a

def bid_ranges(base: Assumptions, policies: list[BidPolicy]) -> BidRangesResult:
    results = {}
    for policy in policies:
        shocked = _apply_shocks(base, policy)
        targets = InvestorTargets(min_dscr=policy.min_dscr, min_irr=policy.min_after_tax_irr, ...)
        results[policy.name] = max_offer_price(shocked, targets)
    # 単調性 (conservative ≤ base ≤ aggressive) を保証する後処理
    return BidRangesResult(...)
```

→ `re-engine` 内に純粋関数として追加。LLM 不使用。

### 2.2 sensitivity (✅ 再利用可)

既存: `packages/financial-engine/src/re_engine/sensitivity.py` (12シナリオ)
Plan C2 (assumption_risks) は別ロジックだが、shock 適用部分は `_apply_shocks()` と共通化できる。

### 2.3 summarizer NG ワードフィルタ (✅ 再利用可)

既存: `apps/api/src/api/services/summarizer.py`
- `generate_critique()`, `generate_summary_3line()`, `generate_inquiry_questions()` が存在
- NG ワード regex フィルタ + リトライ済

Plan C4 (memo builder) で要求される NG 表現チェックは、既存のロジックを抽出して `services/ng_filter.py` に切り出すと共有しやすい。

### 2.4 既存 inquiry_questions と Plan C3 の関係 (⚠️ 二重化リスク)

既存: `summarizer.generate_inquiry_questions()` + `docs/prompts/inquiry_questions_v2.md`
→ **LLM が物件と分析結果を読んで質問を生成** (8 件 / 楽待 fixture 検証済)

Plan C3: **ルールベース** で生成 → LLM は文面整形のみ

**選択肢**:
- (A) 既存を廃止し、Plan C3 ルールベース版に統一
- (B) 両立: ルールベースを `checklist_items` に保存、既存 LLM 質問は AI Insight 表示専用に降格
- (C) ハイブリッド: ルールベース質問 + LLM 補完を統合し `checklist_items` に保存

→ **推奨 (C)**。決定性とカバレッジの両取り。ただし「LLM が優先度・カテゴリを変えてはいけない」という Plan の制約は遵守。

### 2.5 source 追跡 (⚠️ Assumptions 拡張が必要)

Plan C2 が要求する `confidence` (A/B/C/D) は、各フィールドの **データ出所** を知っている必要がある。
既存 `Assumptions` モデルは **値しか持たない** → 出所情報なし。

**実装方針**:
```python
# packages/financial-engine/src/re_engine/models.py
class FieldSource(BaseModel):
    source: Literal["pdf", "url", "user_input", "default"]
    confidence: Literal["A", "B", "C", "D"]
    raw_value: Any | None = None  # 元データ

# normalized_property 側に source map を持たせる
class NormalizedProperty(BaseModel):
    field_sources: dict[str, FieldSource]
    ...
```

→ `Assumptions` を破壊せず、**並行する `NormalizedProperty` を新設** するのが安全。
extractors/to_assumptions.py を `to_normalized_property() → to_assumptions()` の 2 段に分解する。

### 2.6 既存 API エンドポイントとの命名衝突

既存 (全てルートパス):
```
/health /version /analyze /sample/nishi-shinjuku /max_offer /sensitivity
/cross_asset /extract/url /extract/document /analyses /analyses/{id}
/summarize /critique /admin/purge-expired-documents
```

Plan は `/api/analysis/...` / `/api/deals/...` 系の **新プレフィックス**。

**選択肢**:
- (A) 新 API を `/api/...` で実装し、既存はそのまま (二重露出、Next 側でだけ整理)
- (B) 既存を `/api/...` にリネーム + 旧パスを deprecation alias (1 ヶ月)
- (C) Plan の `/api/` プレフィックスを廃止し、既存規約 (`/deals/...`) に合わせる

→ **推奨 (C)**。ユーザーゼロのうちは旧 alias 不要、Next route handler のディレクトリ名と一致して見通しが良い。

### 2.7 バックエンド ディレクトリ命名

Plan: `backend/app/domains/{deals, analysis, assumptions, checklist, memo, market, watchlist}/`
既存: `apps/api/src/api/{main.py, db.py, services/{extractors/, ...}}`

→ 既存はフラット。CLAUDE.md 「最小差分」「既存構成を優先」より、**既存に合わせる**:

```
apps/api/src/api/
  main.py
  db.py
  routers/                    # main.py から分割
    deals.py
    analysis.py
    checklist.py
    memo.py
    watchlist.py
    market.py
  services/
    extractors/               # 既存
    bid_ranges.py             # 新規 (or re-engine 側)
    risk_engine.py            # 新規
    checklist_rules.py        # 新規
    memo_builder.py           # 新規
    evidence_cards.py         # 新規
    ng_filter.py              # summarizer.py から抽出
```

純粋計算 (`bid_ranges`) は `re-engine` 側に置く方が再利用性が高い。

---

## 3. フロントエンド再利用ポイント

### 3.1 既存資産

| ファイル | 再利用度 |
|---|---|
| `src/components/bloomberg.tsx` (Panel/Row/KpiCell/Badge/Btn/Field/Input/Select) | ✅ そのまま |
| `src/components/report-panels.tsx` (SensitivityPanel/MaxOfferPanel/CrossAssetPanel) | ✅ Deal Workspace に組み込み |
| `src/components/nav.tsx` | 拡張 (Deals / Watchlist リンク追加) |
| `src/app/report/page.tsx` | Deal Workspace 内タブに移植 |
| `src/app/compare/page.tsx` | Plan C6 で置換 (sessionStorage → DB 駆動) |
| `src/types/api.ts` | OpenAPI 再生成必要 |

### 3.2 ルート整理

| 既存 | Top7 後 |
|---|---|
| `/upload` `/confirm` | 残置 (entry flow) |
| `/report` | `/deals/[id]` に統合・Summary タブとして残す |
| `/history` | `/deals` 一覧に置換 |
| `/compare` | `/deals/compare?...` に置換 |
| `/analyses/[id]` | 共有 URL 互換のため残置 → 内部で `/deals/[id]` リダイレクト |
| `/new` | 残置 (手動入力フロー) |
| 新規 | `/deals/[id]` `/deals` `/watchlist` |

### 3.3 Plan D2 コンポーネントパス

Plan: `frontend/src/components/deal/`
実際: `apps/web/src/components/deal/`

→ パス読み替えのみ。

---

## 4. 表現・原則の整合

| 計画 | 既存 | 状態 |
|---|---|---|
| NG ワードリスト (買い/見送り/おすすめ/...) | `services/summarizer.py` で実装済 | ✅ 拡張で対応 |
| engine_version 記録 | 既存 `analyses.engine_version` | ✅ |
| prompt_versions 記録 | 既存 `analyses.prompt_versions` | ✅ |
| PII マスク | `services/pii.py` | ✅ |
| 業者送客しない | 既存 `/lp` でも訴求済 | ✅ |
| `input_snapshot_json` | `assumptions` 列で代替 | ✅ (列名で混乱しないよう README 更新) |
| `normalized_property_json` | 未実装 | ⚠️ 新規 (§2.5) |

---

## 5. テスト整合

既存: `pytest` 135 件 (engine 84 + api 51)
Plan F: 新規必須テスト 6 セクション (bid_ranges / risks / checklist / memo / watchlist / compare)

- Plan F1 (bid_ranges) は engine 側で 5 テスト → engine 計 89 件
- Plan F2-6 は api 側で各 4-5 テスト → api 計 25 件追加
- 合計 +30 件、目標 165 件

CI (`.github/workflows/ci.yml`) は uv + pytest 構成のため追加設定不要。

---

## 6. リスクと未解決論点

| # | 論点 | 影響 |
|---|---|---|
| 1 | `normalized_property` 設計を先に確定しないと C2 (risk) / C5 (compare) / C7 (evidence) が同じ概念を別実装する | High |
| 2 | 既存 inquiry_questions と Plan C3 の関係 (§2.4 選択肢 A/B/C) を未決のまま着手すると重複コード発生 | Medium |
| 3 | API プレフィックス選択 (§2.6) を Week 1 までに決めないと OpenAPI 型生成が二度手間 | Medium |
| 4 | `/report` → `/deals/[id]` への移行で既存共有 URL が壊れないか (旧 `/analyses/[id]` 互換維持) | Medium |
| 5 | `evidence_cards` (C7) は market_context.py が stub + ETL 未投入で実データなし → MVP は `unknown` 固定で出す | Low (Plan も認識) |
| 6 | Plan の Week 1 が「既存 analysis_run 表示」と書くが、現状 `analysis_runs` テーブル未存在 → Week 0 として §1.3 マイグレーションを先行 | High |

---

## 7. 推奨着手順 (整合性を踏まえた修正案)

Plan の Week 1-4 を以下に置換:

### Week 0: 基盤整備 (新規追加、3-4日)

1. v2 マイグレーション (`deals` 追加 + `analyses` → `analysis_runs` rename)
2. `Assumptions` を壊さず `NormalizedProperty` モデル新設
3. extractors/to_assumptions.py を 2 段化
4. API プレフィックス方針確定 (§2.6 推奨 C)
5. `services/ng_filter.py` 切り出し
6. OpenAPI 型再生成

### Week 1: Deal Workspace 基盤 + bid_ranges (Plan 通り)

`/deals/[id]` 骨格 + `re_engine/bid_ranges.py` (純粋関数) + BidRangeCard

### Week 2: assumption_risks + checklist

`risk_engine.py` (NormalizedProperty 経由) + checklist ルール (既存 inquiry_questions と統合方針確定)

### Week 3: memo + watchlist + compare 再設計

memo_builder + watchlist + 既存 sessionStorage compare → DB 駆動 compare

### Week 4: evidence_cards 初期版 + 既存ルート移行 + 共有 URL 互換

`/analyses/[id]` 旧 URL を `/deals/[id]` に redirect、evidence_cards は `unknown` 固定で枠だけ実装

---

## 8. 次の判断ポイント (ユーザーへ)

着手前に以下を決めると手戻りが減る:

1. **§1.3 v2 マイグレーション方針**: rename 案でよいか / 別案か
2. **§2.4 inquiry_questions の扱い**: (A) 廃止 / (B) 分離 / (C) ハイブリッド
3. **§2.6 API プレフィックス**: (A) `/api/*` 新設 / (B) 既存 rename / (C) プレフィックスなし統一
4. **§7 Week 0 を追加するか**: それとも Plan 通り Week 1 から進めて遭遇時に対処するか
