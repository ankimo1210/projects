# Progress & 全体ステップマップ

最終更新: 2026-05-12

---

## ✅ Phase 0 — 設計確定 (完了)

| # | 成果物 | 状態 |
|---|---|---|
| 0.1 | リポジトリ骨格 (apps/ packages/ infra/ docs/ tests/) | ✅ |
| 0.2 | README.md | ✅ |
| 0.3 | docs/product/product_requirements.md | ✅ |
| 0.4 | docs/architecture/calculation_engine_spec.md | ✅ |
| 0.5 | docs/architecture/ai_document_extraction_spec.md | ✅ |
| 0.6 | docs/design/mockups/ 5案 + Bloomberg基調採用決定 | ✅ |
| 0.7 | docs/design/design_principles.md | ✅ |
| 0.8 | docs/architecture/data_schema.md | ✅ |
| 0.9 | docs/architecture/technical_architecture.md | ✅ |
| 0.10 | docs/roadmap/mvp_roadmap.md | ✅ |
| 0.11 | docs/legal/legal_risk_checklist.md 草案 | ✅ |
| 0.12 | .github/workflows/ci.yml | ✅ |
| 0.13 | docs/roadmap/plan_review.md (現プラン精査・代替案) | ✅ |
| 0.14 | docs/prompts/ 5プロンプト v1 (classify/brochure/rent_roll/summary/inquiry/critique) | ✅ |
| 0.15 | docs/design/wireframes/ 6画面 ASCII (LP/upload/extraction/list/compare/pricing) | ✅ |

---

## ✅ Phase 1 — 基盤・計算エンジン・UI骨格 (完了)

### 1A. ツールチェイン
- pnpm 11 workspace + uv 0.11 workspace
- ruff, prettier, editorconfig
- TypeScript 5.9 strict
- openapi-typescript (Pydantic → TS型自動生成)

### 1B. packages/financial-engine (✅ 84テスト緑)

| モジュール | 役割 |
|---|---|
| constants.py | 法定耐用年数・税率・構造区分 |
| models.py | Pydantic v2 全モデル (Assumptions / AnalysisResult 等) |
| loan.py | 元利均等返済表・残債・年間集計 |
| cashflow.py | GPI/EGI/NOI/BTCF/ATCF プロジェクション |
| tax.py | 減価償却・課税所得・譲渡税 |
| exit.py | 売却シナリオ・net proceeds |
| irr.py | IRR / Equity Multiple / Payback / DSCR / Cap / LTV |
| score.py | 100点スコア (7コンポーネント) |
| max_offer.py | 二分探索 最大買付価格 solver |
| sensitivity.py | 11シナリオ感応度グリッド |
| cross_asset.py | 8資産クラス比較 (免責付き) |
| analyze.py | フル分析オーケストレーター |

### 1C. apps/api (✅ 10テスト緑)

| エンドポイント | 内容 |
|---|---|
| GET /health | ヘルスチェック |
| GET /version | api + engine バージョン |
| POST /analyze | Assumptions → AnalysisResult + Score |
| GET /sample/nishi-shinjuku | デモ物件 |
| POST /max_offer | 最大買付価格 |
| POST /sensitivity | 感応度グリッド |
| POST /cross_asset | クロスアセット比較 |

### 1D. apps/web (✅)

| ファイル | 内容 |
|---|---|
| src/app/page.tsx | サンプル分析画面 (西新宿・Server Component) |
| src/app/new/page.tsx | 新規分析フォーム (全フィールド → 結果インライン) |
| src/app/api/analyze/route.ts | Next.js → FastAPI プロキシ |
| src/components/bloomberg.tsx | 共通UI (Panel/Row/KpiCell/Badge/Btn/Field/Input/Select) |
| src/types/api.ts | OpenAPI から自動生成 (`pnpm gen:api`) |

### 1E. 現在の公開状態

| URL | 内容 |
|---|---|
| https://task-amino-featuring-pressure.trycloudflare.com | Web (サンプル + 新規分析フォーム) |
| http://127.0.0.1:8001 | FastAPI (内部) |

---

## ⏭️ Phase 2 — 抽出 de-risk (推奨: 最優先)

> plan_review.md §7 の推奨改訂により、認証より先に抽出を検証する。

| # | 作業 | 依存 |
|---|---|---|
| 2.1 | apps/api/services/llm_client.py (Ollama / Anthropic 切替可) | ← **今ここ (Ollama で実装中)** |
| 2.2 | apps/api/services/extractors/classify.py | 2.1 |
| 2.3 | apps/api/services/extractors/property_brochure.py | 2.2 |
| 2.4 | POST /api/extract/url (楽待URL → 抽出) | 2.3 |
| 2.5 | POST /api/extract/document (PDF/画像 → 抽出) | 2.3 |
| 2.6 | 抽出確認画面 (Next.js) | 2.4-2.5 |
| 2.7 | 20サンプルで精度評価 (80% 目標) | 2.4-2.5 |

**ブロッカー (Ollama は不要)**: なし → 今すぐ着手可

---

## ⏭️ Phase 3 — 認証・DB (Supabase待ち)

| # | 作業 | 依存 |
|---|---|---|
| 3.1 | Supabase プロジェクト作成 (dev/staging/prod) | **ユーザー** |
| 3.2 | マイグレーション v1-v3 | 3.1 |
| 3.3 | Next.js 認証 UI | Supabase URL/key |
| 3.4 | FastAPI JWT検証 | 3.1 |
| 3.5 | /me, /criteria エンドポイント | 3.4 |
| 3.6 | ダッシュボード骨格 | 3.3-3.5 |

---

## ⏭️ Phase 4 — PoC データ統合 (アカウント不要)

> plan_review.md §4, §7 より: land_price_api_app の公示地価データを Postgres へ ETL。
> Score の market_cap_rate を活性化する。

| # | 作業 | 依存 |
|---|---|---|
| 4.1 | scripts/etl_public_notice.py (DuckDB → SQL) | アカウント不要 |
| 4.2 | scripts/etl_trade_prices.py | アカウント不要 |
| 4.3 | scripts/etl_rent_market.py | アカウント不要 |
| 4.4 | Supabase へ投入 | Phase 3 |
| 4.5 | apps/api/services/market_context.py (近傍地価 → MarketContext) | 4.4 |
| 4.6 | Score の market_cap_rate を実データで駆動 | 4.5 |

---

## ⏭️ Phase 5 — 分析パイプライン統合 (Phase 2-3 完了後)

| # | 作業 | 依存 |
|---|---|---|
| 5.1 | 抽出 → Assumptions 組み立て | Phase 2 |
| 5.2 | 分析実行 → 結果 → DB保存 | Phase 3 |
| 5.3 | AI 3行サマリー (LLM) | Phase 2の llm_client |
| 5.4 | 確認質問リスト | 5.3 |
| 5.5 | 履歴一覧 /analyses | 5.2 |
| 5.6 | 結果のURL永続化 | 5.2 |

---

## ⏭️ Phase 6 — 課金・β (Stripe + ドメイン待ち)

| # | 作業 | 依存 |
|---|---|---|
| 6.1 | Stripe Checkout (Free/Pro) | **Stripe key** |
| 6.2 | Stripe Webhook | 6.1 |
| 6.3 | 機能ゲート | 6.2 |
| 6.4 | 比較ボード | Phase 3 |
| 6.5 | 退会・データ削除フロー | Phase 3 |
| 6.6 | 利用規約・プライバシー・特商法ページ | 弁護士レビュー後 |
| 6.7 | 本番デプロイ (Vercel + Fly.io + Supabase prod) | ドメイン |
| 6.8 | LP 公開 + 友人β | 6.7 |

---

## 🚦 ブロッカー一覧

| 種類 | 内容 | 解放されると |
|---|---|---|
| 🔑 Anthropic API key | Claude Haiku/Sonnet 利用 | Phase 2 高精度化 (今は Ollama で代用) |
| 🔑 OpenAI key | フォールバック | 優先度低 |
| 🏗 Supabase × 3 | Postgres + Auth + Storage | Phase 3 |
| 🏗 Stripe | 課金 | Phase 6 |
| 🏗 ドメイン + Vercel + Fly.io | 本番 URL | Phase 6 |
| 🏗 Sentry / PostHog | 監視・分析 | Phase 6 |
| 📝 プロダクト名 | 仮称 re_invest_os | LP 公開時 |
| 📝 LP デザイン基調 | Bloomberg統一 vs Stripe寄り | Phase 6 |
| ⚖️ 弁護士レビュー | 規約・表現確認 | Phase 6 直前 |
| ⚖️ 税理士 + 開業届 | 損益通算・経費計上 | **今すぐ** |

---

## 📊 数値スナップショット (2026-05-12)

```
Tests:        94 passed (engine 84 + api 10)
Ruff:         All checks passed
Format:       29 files clean
Typecheck:    OK (web)

Endpoints:    7 (health / version / analyze / sample / max_offer / sensitivity / cross_asset)
Web routes:   2 (/ サンプル, /new フォーム) + 1 API proxy

Docs:         18 markdown files
Prompts:      6 v1 drafts
Wireframes:   6 screen ASCII

Ollama:       gemma3:12b (8.1GB), qwen2.5:7b (4.7GB) 起動済み
```

---

## 🔗 主要ドキュメント索引

| ファイル | 内容 |
|---|---|
| docs/product/blueprint_v0_1.md | 元の青写真 26章 |
| docs/product/product_requirements.md | PRD (機能25個 P0-P2) |
| docs/architecture/calculation_engine_spec.md | 計算エンジン仕様 |
| docs/architecture/ai_document_extraction_spec.md | AI抽出パイプライン仕様 |
| docs/architecture/data_schema.md | DB ERD・全テーブルDDL |
| docs/architecture/technical_architecture.md | スタック・デプロイ・コスト |
| docs/design/design_principles.md | Bloomberg基調・原則10条 |
| docs/design/mockups/ | 5案HTML + 採用案 (03) |
| docs/design/wireframes/ | 6画面ASCII |
| docs/legal/legal_risk_checklist.md | NG/OK表現・PII・特商法草案 |
| docs/roadmap/mvp_roadmap.md | 12週マイルストーン |
| docs/roadmap/plan_review.md | 現プラン精査・代替案・推奨改訂 |
| docs/roadmap/progress.md | **このファイル** |
| docs/prompts/ | LLMプロンプト v1 × 6本 |
| apps/web/src/components/bloomberg.tsx | 共通UIコンポーネント |
| packages/financial-engine/src/re_engine/ | 計算エンジン 12モジュール |
