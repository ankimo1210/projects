# Technical Architecture — re_invest_os

作成日: 2026-05-12
ベース: blueprint_v0_1.md §14, README.md

---

## 1. 全体構成

```
┌────────────────┐    ┌──────────────────┐    ┌────────────────┐
│  Vercel        │    │  Fly.io / Cloud Run │    │  Supabase      │
│  Next.js (web) │←→→│  FastAPI (api)     │←→→│  Postgres      │
│  Edge SSR      │    │  Python 3.12       │    │  Storage       │
│                │    │  re_engine        │    │  Auth          │
└────────────────┘    └──────────────────┘    └────────────────┘
       ↑                       ↑                      ↑
       │                       │                      │
       │     ┌─────────────────┴──────┐               │
       │     │  Worker (Phase 4+)      │              │
       │     │  Celery + Redis        │←━━━━━━━━━━━━━┘
       │     │  AI extraction         │
       │     │  Scraping              │
       │     └────────────────────────┘
       │
       │     ┌─────────────────┐    ┌─────────────┐
       └────→│  Stripe         │    │  Sentry     │
             │  Webhooks       │    │  PostHog    │
             │  Checkout       │    │             │
             └─────────────────┘    └─────────────┘

External APIs:
- Anthropic Claude (Haiku/Sonnet)
- OpenAI (fallback)
- MLIT Reinfolib (公示地価・取引価格)
- e-Stat (人口・賃料)
- 国土地理院 (ジオコード・標高)
- Overpass API (周辺施設)
```

---

## 2. スタック詳細

### 2.1 Frontend: `apps/web`

| 項目 | 採用 |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript 5.9 (strict) |
| Styling | Tailwind CSS v4 + デザイントークン (`globals.css`) |
| UI components | shadcn/ui (Bloomberg基調にカスタマイズ) |
| Icons | lucide-react |
| Charts | Recharts または Tremor (端末感に合わせカスタムテーマ) |
| Forms | React Hook Form + zod |
| State (client) | Zustand (小さく) or React Server Components 中心 |
| Data fetching | Server Components (fetch) + Route Handlers |
| Tables | TanStack Table (比較ボード等) |
| Fonts | Next.js Google Fonts (JetBrains Mono + Noto Sans JP) |
| Auth client | @supabase/ssr |
| Stripe client | @stripe/stripe-js |
| Testing | Vitest + Testing Library + Playwright (E2E) |

### 2.2 Backend: `apps/api`

| 項目 | 採用 |
|---|---|
| Framework | FastAPI 0.115+ |
| Server | uvicorn + uvloop (本番は gunicorn worker) |
| Language | Python 3.12+ |
| Type system | Pydantic v2 |
| ORM | SQLAlchemy 2.0 + alembic (Phase 2-) もしくは Supabase Python client |
| Migrations | Supabase CLI (`infra/migrations/`) |
| Auth | JWT verification (`@supabase/supabase-js` 発行の JWT を decode) |
| LLM clients | anthropic, openai, instructor |
| HTTP | httpx |
| HTML parsing | BeautifulSoup4 + lxml |
| PDF parsing | pymupdf (PyMuPDF) |
| Excel parsing | openpyxl |
| Linting | ruff |
| Testing | pytest + httpx + hypothesis |
| Logging | structlog (JSON logs) |

### 2.3 Worker: `apps/worker` (Phase 4+)

| 項目 | 採用 |
|---|---|
| Queue | Redis (Upstash) |
| Worker | Celery 5.x + redis broker |
| Cron | Celery Beat (定期ジョブ) |
| Job types | URL解析 / PDF解析 / レントロール解析 / レポート生成 |

MVP 初期は **FastAPI BackgroundTasks** で代用。負荷が見えてから Celery 化。

### 2.4 Shared: `packages/`

- `financial-engine` (Python) — 計算エンジン
- `document-schemas` (TS + Python 同期) — AI抽出スキーマ
- `shared-schemas` (TS + Python 同期) — API request/response 型

スキーマ同期: API の OpenAPI から TS型を `openapi-typescript` で自動生成 (`apps/web/src/types/api.ts`)。

---

## 3. デプロイ構成

### 3.1 ホスティング

| サービス | 用途 | 月額目安 (初期) |
|---|---|---:|
| **Vercel** | Next.js (web) | $0 (Hobby) → $20 (Pro) |
| **Fly.io** | FastAPI (api) | $5-15 (1-2 shared-cpu-1x) |
| **Supabase** | Postgres + Auth + Storage | $0 (Free) → $25 (Pro) |
| **Upstash** | Redis (Phase 4+) | $0 (Free tier) |
| **Cloudflare** | DNS + CDN | $0 |
| **Stripe** | 決済 | 取扱高×3.6% (国内) |
| **Sentry** | エラー監視 | $0 (Developer) |
| **PostHog** | アナリティクス | $0 (Free, 1Mイベント/月) |
| **Anthropic** | Claude API | 従量 (推定 $50-300/月) |
| **OpenAI** | フォールバック | 従量 |

初期固定費目安: **約$50/月** + AI従量。月1,000分析×$0.05 = $50 → 合計 **$100/月** 程度。

### 3.2 環境

| 環境 | URL | 用途 |
|---|---|---|
| local | localhost | 開発 |
| preview | Vercel preview deployments | PR ごとに自動 |
| staging | staging.example.com | リリース前検証 |
| production | example.com | 本番 |

各環境ごとに Supabase プロジェクトを分ける (Free tier で staging、Pro tier で production)。

---

## 4. CI/CD

### 4.1 CI (GitHub Actions)

`.github/workflows/ci.yml`:

```yaml
- pytest (financial-engine + api)
- ruff check
- pnpm typecheck
- pnpm build (web)
- pnpm format:check
```

PR で全ジョブ実行、main にマージ前に必ず緑。

### 4.2 CD

| 対象 | 方法 |
|---|---|
| web | Vercel が main push を検知して自動デプロイ |
| api | Fly.io: `fly deploy` を GitHub Actions から発火 (main マージで) |
| DB migration | `supabase db push` を CI から (production はマニュアル承認) |
| 環境変数 | Vercel / Fly.io / Supabase のダッシュボードで管理 |

---

## 5. 環境変数

`.env.example` (リポジトリにコミット):

```bash
# Backend (apps/api)
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
SENTRY_DSN=...
CORS_ALLOW_ORIGINS=https://example.com,http://localhost:3001
REINFOLIB_API_KEY=...
ESTAT_APP_ID=...

# Frontend (apps/web)
NEXT_PUBLIC_API_BASE=https://api.example.com
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_...
NEXT_PUBLIC_POSTHOG_KEY=...
NEXT_PUBLIC_SENTRY_DSN=...
```

実 `.env` は git ignore。本番値は Vercel / Fly.io ダッシュボードに直接入れる。

---

## 6. 非同期ジョブ設計

### 6.1 MVP: FastAPI BackgroundTasks

軽量ジョブはレスポンス内で発火し、awaitしない:

```python
@app.post("/analyze/url")
async def analyze_url(req: Req, bg: BackgroundTasks) -> JobAccepted:
    job_id = create_job(...)
    bg.add_task(process_url_job, job_id, req.url)
    return JobAccepted(job_id=job_id)
```

クライアントは `/jobs/{id}` を poll してステータスを取得。

### 6.2 Phase 4+: Celery

- URL解析・PDF解析・レントロール解析を Celery タスク化
- Beat で定期ジョブ (公的データ更新、retention GC、メール通知)
- 結果保存は `analysis_runs.status` で管理 (queued → processing → completed / failed)

```python
@app.task(bind=True, max_retries=2)
def extract_pdf(self, document_id: str) -> None: ...

@app.task
def gc_expired_documents() -> None: ...
```

---

## 7. AI 呼び出し戦略

### 7.1 モデル選定 (ai_document_extraction_spec.md §9 と一致)

| タスク | 主モデル | フォールバック |
|---|---|---|
| 資料分類 | claude-haiku-4-5 | gpt-4.1-mini |
| 販売図面抽出 (テキスト) | claude-haiku-4-5 | gpt-4.1-mini |
| 販売図面抽出 (画像) | claude-sonnet-4-6 | gpt-4.1 vision |
| レントロール抽出 | claude-haiku-4-5 | gpt-4.1-mini |
| 3行サマリー生成 | claude-haiku-4-5 | gpt-4.1-mini |
| 質問リスト生成 | claude-haiku-4-5 | gpt-4.1-mini |
| 業者資料の甘さ説明 | claude-sonnet-4-6 | gpt-4.1 |

### 7.2 構造化出力

- Anthropic: Tool use で JSONSchema 強制
- OpenAI: Structured Outputs (`response_format`)
- どちらも `instructor` ライブラリで統一インタフェース

### 7.3 リトライ / フォールバック

```python
async def extract_with_fallback(doc) -> Extraction:
    for model in primary_models:
        try:
            return await call_model(model, doc, timeout=30)
        except (TimeoutError, ValidationError, RateLimitError):
            continue
    # 全失敗 → 手動入力フォーム誘導
    raise ExtractionFailed(...)
```

### 7.4 コスト管理

- ユーザーごとの月次LLM呼び出し回数をカウント
- Free プランの上限超過時は 429
- 1分析あたりの推定コストを `analysis_runs.cost_usd_estimated` に記録
- 月次総コストが上限超えたら Free 受付を停止 (kill switch)

---

## 8. 監視 / ロギング

### 8.1 Sentry

- web / api / worker すべて連携
- パフォーマンス計測 (transaction tracing) も有効
- リリースバージョンを `engine_version` と紐づけ

### 8.2 PostHog

主要イベント:

| イベント | 計測対象 |
|---|---|
| `analysis.started` | URL/資料投入 |
| `analysis.completed` | 結果表示 |
| `analysis.failed` | エラー (Tier1-4) |
| `extraction.user_corrected` | 抽出修正 (項目別) |
| `score.viewed` | スコア閲覧 |
| `max_offer.viewed` | 最大買付価格閲覧 |
| `comparison.added` | 比較ボード追加 |
| `subscription.upgraded` | Pro化 |
| `subscription.canceled` | 解約 |
| `supporter.donated` | 投げ銭 |

### 8.3 ログ

- 構造化JSON (`structlog`)
- 重要キー: `user_id`, `analysis_run_id`, `engine_version`, `model`, `prompt_version`, `processing_ms`, `cost_usd`
- PII (氏名・電話・メール) はログに出さない
- Fly.io / Vercel のログを 30日保持、重要ログのみ長期 (Supabase テーブル)

---

## 9. セキュリティ

### 9.1 認証・認可

- Supabase Auth (Email + Google + Magic Link)
- JWT 検証は API 側で行い、`req.state.user_id` にセット
- RLS で DB レベルでもユーザー隔離

### 9.2 シークレット管理

- リポジトリには `.env.example` のみ
- Vercel / Fly.io のシークレット機能を使用
- ローテーション: API key は四半期、JWT secret は年次

### 9.3 入力検証

- 全エンドポイントで Pydantic スキーマ (`extra='forbid'`)
- ファイルアップロードは MIME / マジックバイト / サイズ上限を二重チェック
- URL はスキーマと allowlist で検証

### 9.4 レート制限

- 認証ユーザー: プランに応じた月次上限
- 非認証: IP単位 (Cloudflare レート制限)
- Stripe webhook は署名検証必須

### 9.5 PIIマスク

LLM送信前に regex で除去 (氏名・電話・メール)。`ai_document_extraction_spec.md §8` 参照。

---

## 10. パフォーマンス目標

| 項目 | 目標 |
|---|---|
| 分析エンジン (1分析) | < 100ms |
| `/analyze` p95 | < 500ms |
| URL解析 (worker, 1回) | 中央値 15s / p95 30s |
| PDF1ファイル抽出 | 中央値 20s / p95 60s |
| 同時ジョブ | 初期 10並列、3か月で 50並列 |
| web TTFB (Vercel edge) | < 200ms |

---

## 11. バックアップ・災害復旧

- Supabase 自動日次バックアップ (7日保持, Pro tier で 14日)
- 重要テーブル (`analysis_runs`, `users`, `subscriptions`) は別 storage に週次ダンプ
- 復旧目標: RTO 4時間 / RPO 24時間
- Fly.io インスタンスは複数 region にしない (シングル region で OK、コスト優先)

---

## 12. スケーリング計画

| 段階 | ユーザー | 月間分析 | スタック変更 |
|---|---|---|---|
| MVP | 100 | 1,000 | 現構成のまま |
| 初期成長 | 1,000 | 10,000 | Worker分離 (Celery) + Redis |
| 中期 | 10,000 | 100,000 | Postgres read replica + CDN強化 |
| 大規模 | 100,000 | 1,000,000 | sharding 検討 / 専用LLM model |

---

## 13. ローカル開発

### 13.1 セットアップ

```bash
# Python
uv sync --all-packages

# Node
pnpm install

# DB (Supabase local stack)
brew install supabase/tap/supabase
supabase start

# 環境変数
cp .env.example .env
# 必要なキーを入力
```

### 13.2 起動

```bash
# API
cd apps/api && uv run uvicorn api.main:app --reload --port 8001

# Web
cd apps/web && pnpm dev --port 3001

# テスト全部
uv run pytest -q
pnpm typecheck
```

### 13.3 デバッグ

- VSCode: launch.json に FastAPI / Next.js 両方の構成
- Supabase Studio: http://localhost:54323 (local stack)
- Sentry: ローカルから本番Sentryに送らないよう環境分離

---

## 14. 既知の課題・将来課題

- **Worker分離タイミング**: 同時5ジョブ超えたら Celery 化
- **Postgres から DuckDB へ**: 公的データ統計クエリが重くなったら別ストア検討
- **LLMコスト最適化**: キャッシュ・小型モデル化・FT
- **マルチリージョン**: 日本国内のみなら不要、海外展開時に Vercel + Fly.io 複数region化
- **GDPR/個人情報保護法**: 海外ユーザー受け入れ時の対応
- **DDoS対策**: Cloudflare WAF を入れるか、本番直前で判断
