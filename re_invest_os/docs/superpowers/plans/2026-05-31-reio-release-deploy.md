# re_invest_os リリース（本番デプロイ）計画

> **For agentic workers:** これはコードのTDD計画ではなく **リリース/デプロイのランブック**。各タスクはチェックボックス（`- [ ]`）で進捗管理する。コード/設定ファイルを作る箇所は完全な内容を載せ、外部操作（アカウント作成・ダッシュボード設定）は手順と確認方法（Expected）を載せる。実行は未着手（ユーザー方針: 「まだ作らず計画だけ」）。

**Goal:** re_invest_os を「認証なし・無料で触れる本番URL」として公開できる状態にし、その先（課金・会員制・本番ドメイン）への拡張も同一計画で見通せるようにする。

**Architecture:** 既存設計（`docs/architecture/technical_architecture.md`）の **Vercel(web) + Fly.io(api) + Supabase(Postgres)** を踏襲。Web は全バックエンド呼び出しを `apps/web/src/app/api/backend/[...path]/route.ts`（`API_BASE` 環境変数）に集約済みのため、本番化は実質「API を Fly に上げ、`API_BASE` をそのURLに差す」だけが幹。

**Tech Stack:** FastAPI(Python 3.12) / Next.js 16 / SQLAlchemy async / Anthropic Haiku / Supabase Postgres / Docker / Fly.io / Vercel

---

## 前提・重要な構造的所見（実確認済み 2026-05-31）

| 項目 | 実状態 | 影響 |
|---|---|---|
| git root | `/home/kazumasa/projects`（**monorepo**：gto/stock 等も同居） | リポジトリ戦略の判断が必要（R0.2） |
| uv workspace root | `~/projects/pyproject.toml`。reio メンバーは `re_invest_os/apps/api` と `re_invest_os/packages/financial-engine`（**両方 re_invest_os 配下**） | API コンテナは `re_invest_os/` を文脈に自己完結ビルド可能 |
| API→engine 依存 | `apps/api` が `re-engine`（=financial-engine）に workspace 依存 | Docker では engine を先に install すれば pip でも解決可 |
| Web→API 接続 | `API_BASE`（既定 `http://127.0.0.1:8001`）の単一プロキシ集約 | 本番切替は env 1個 |
| 認証 | Supabase env 未設定で自動無効化（graceful） | 認証なし公開が可能 |
| DB | dev=SQLite（`reio.db` がコミット済）/ prod=Postgres 未プロビジョニング | prod は必ず `DATABASE_URL` を Postgres に |
| デプロイ資材 | `Dockerfile`/`fly.toml`/`vercel.json` **なし**、CI(`ci.yml`)はあるが CD なし | R1〜R3 で新規作成 |
| Market Grounding | 実データ（国交省 XIT001）実装済。`REINFOLIB_API_KEY` 必須 | prod secret に必要 |
| テスト/型 | `177 passed` / `tsc --noEmit` exit 0（2026-05-31 実行） | デプロイ前ゲートに使う |

**公開ブロッカー（技術外・段階で解禁）**
- 法務ページ（利用規約/プライバシー/特商法）が弁護士レビュー前の草案 → **課金開始時に特商法表記が法的必須**。無料・無会員の最小公開なら免責表示（`api/constants.py:DISCLAIMERS` 実装済）で運用可だが要自己判断。
- 構造的に市場データ未投入エリアで `overall_risk` が常に HIGH 表示になる既知挙動（Market Grounding v1 で緩和中）。公開前にコピーで「これは前提検証であり投資助言ではない」旨を明示。

---

## フェーズ構成（最小公開 = R0〜R4 で完了。R5 は将来の有料公開）

- **R0** 事前準備・意思決定（アカウント／リポジトリ戦略／キー収集）
- **R1** API コンテナ化 → Fly.io デプロイ
- **R2** 本番DB（Supabase Postgres）プロビジョニング＋マイグレーション適用
- **R3** Web → Vercel デプロイ
- **R4** 結線・E2E スモークテスト（= 最小公開の完了点）
- **R5**（将来）有料・会員制公開：認証有効化／法務確定／Stripe／監視／独自ドメイン

---

## Phase R0 — 事前準備・意思決定

### Task R0.1: デプロイ前ゲート（現行が緑であることの確認）

**Files:** （変更なし、確認のみ）

- [ ] **Step 1: テスト全緑を確認**

Run: `cd /home/kazumasa/projects/re_invest_os && uv run pytest -q`
Expected: `177 passed`（件数は増えていてもよいが 0 failed）

- [ ] **Step 2: 型チェック緑を確認**

Run: `cd /home/kazumasa/projects/re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`
Expected: 出力なし・exit 0

### Task R0.2: re_invest_os を独立 repo に切り出す（決定済み）

**決定（2026-05-31）:** 選択肢 **B**。切り出し先 `~/re_invest_os`（~/projects の外）／履歴は **git filter-repo** で保持／GitHub は **private**。

> 判断理由: reio は公開・商用狙いのプロダクトで、gto も将来商用化予定。monorepo 全体を Vercel/Fly に渡すと他プロジェクトのソースまで外部基盤に露出する。独立 repo 化で露出・権限粒度・運用事故耐性・プロダクト独立性を確保する。

**重要な前提:**
- `git filter-repo` は **git 履歴（コミット済み）しか引き継がない**。未コミット/gitignore 対象（`apps/api/.env`, `node_modules`, SQLite の `-wal`/`-shm`）は持ち越されない → Step 1 でコミット、Step 8 で手動コピー。
- `reio.db` は git 管理下（コミット済み）なので履歴と共に移動する。

- [ ] **Step 1: 切り出し前に未コミットの reio 変更をコミット**（この plan 自身を含む）

Run:
```bash
cd /home/kazumasa/projects
git add re_invest_os/docs/superpowers/plans/2026-05-31-reio-release-deploy.md
git commit -m "docs(reio): release deploy plan"
```
Expected: feat/reio-mvp-clean に plan が含まれる（filter-repo で引き継がれる）

- [ ] **Step 2: git-filter-repo を用意**

Run: `uv tool install git-filter-repo` （または `pipx install git-filter-repo`）
Expected: `git filter-repo --version` が動く

- [ ] **Step 3: monorepo を作業用に fresh clone**（filter-repo は新規 clone を要求）

Run:
```bash
git clone --no-local /home/kazumasa/projects /tmp/reio-split
cd /tmp/reio-split
git checkout feat/reio-mvp-clean
```
Expected: `feat/reio-mvp-clean` がローカルブランチとして存在

- [ ] **Step 4: 部分木を抽出（re_invest_os/ を repo ルート化）**

Run: `git filter-repo --subdirectory-filter re_invest_os --force`
Expected: 履歴が re_invest_os 配下のコミットのみに縮約され、パスがルート化。`origin` は filter-repo により自動除去。

- [ ] **Step 5: ブランチ名を main に**

Run: `git branch -m feat/reio-mvp-clean main`

- [ ] **Step 6: 新しい場所へ移動**

Run: `mv /tmp/reio-split ~/re_invest_os`
Expected: `~/re_invest_os/.git` が存在し、`apps/` `packages/` `docs/` 等がルート直下

- [ ] **Step 7: 独立 uv workspace を作成**

Create `~/re_invest_os/pyproject.toml`:
```toml
[tool.uv.workspace]
members = ["apps/api", "packages/financial-engine"]

[tool.uv.sources]
re-engine = { workspace = true }
```
Run: `cd ~/re_invest_os && uv sync --all-packages`
Expected: 新しい `uv.lock` 生成。torch 等 monorepo 固有依存を含まない。

- [ ] **Step 8: git 管理外の必須ファイルを手動コピー＋Node 再インストール**

Run:
```bash
cp /home/kazumasa/projects/re_invest_os/apps/api/.env ~/re_invest_os/apps/api/.env
cd ~/re_invest_os/apps/web && pnpm install
```
Expected: `.env`（ANTHROPIC_API_KEY 等）が新 repo に存在、node_modules 再構築

- [ ] **Step 9: 切り出し先で緑を確認**

Run:
```bash
cd ~/re_invest_os && uv run pytest -q
cd ~/re_invest_os/apps/web && node_modules/.bin/tsc --noEmit
```
Expected: `177 passed` / 型チェック clean（exit 0）

- [ ] **Step 10: private GitHub repo を作成して push**

Run: `cd ~/re_invest_os && gh repo create re_invest_os --private --source=. --remote=origin --push`
Expected: private repo 作成、`main` を push

- [ ] **Step 11: monorepo 側から reio を除去**

- `~/projects/pyproject.toml` の `[tool.uv.workspace].members` から `"re_invest_os/apps/api"` と `"re_invest_os/packages/financial-engine"` を削除。`[tool.uv.sources]` の `re-engine = { workspace = true }` も削除（`torch` は残す）。
- Run:
```bash
cd /home/kazumasa/projects
git rm -r re_invest_os
uv sync --all-packages
```
Expected: 他プロジェクトの lock 再生成、reio 不在で成功

- [ ] **Step 12: ドキュメント/メモリのパス更新**

- `~/projects/CLAUDE.md` の Active Projects から `re_invest_os` を除去（または「`~/re_invest_os` に分離」と注記）
- memory `project_re_invest_os.md` のパスを `~/re_invest_os` に更新

- [ ] **Step 13: monorepo 側をコミット**

Run:
```bash
cd /home/kazumasa/projects
git add -A
git commit -m "chore: extract re_invest_os into standalone repo"
```

> **Post-split note:** 以降 R1〜R4 のパスはすべて新 repo ルート `~/re_invest_os` 基準に読み替える（Docker 文脈 = `~/re_invest_os`、Vercel Root Directory = `apps/web`、`fly.toml`/`Dockerfile` = repo 直下）。

### Task R0.3: アカウント・キーの用意

- [ ] **Step 1: アカウント作成**：Fly.io / Vercel / Supabase（いずれも無料枠で開始可）
- [ ] **Step 2: CLI 導入**：`fly`（flyctl）, `vercel`（任意）, `supabase`（任意）
  Run（Fly 例）: `curl -L https://fly.io/install.sh | sh` → `fly auth login`
  Expected: ブラウザ認証完了
- [ ] **Step 3: キー収集**
  - `ANTHROPIC_API_KEY`（既存 `apps/api/.env` から）
  - `REINFOLIB_API_KEY`（国交省。`land_price_api_app/.env` の `REINFOLIB_API_KEY` を流用）
  - これらは **secrets に直接入れる。リポジトリ・本ドキュメントには書かない。**

---

## Phase R1 — API コンテナ化 → Fly.io

> Docker ビルド文脈は `re_invest_os/`。`re-engine` を先に install することで、`apps/api` の `re-engine` 依存をローカル解決する（PyPI には存在しないため順序が重要）。

### Task R1.1: API 用 Dockerfile を作成

**Files:**
- Create: `re_invest_os/Dockerfile`
- Create: `re_invest_os/.dockerignore`

- [ ] **Step 1: `re_invest_os/Dockerfile` を作成**

```dockerfile
# re_invest_os API — production image (Fly.io)
# Build context: re_invest_os/  (api と re-engine が同居するため自己完結)
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# 1) 計算エンジン(re-engine, 純粋関数)を先に install → api の `re-engine` 依存をローカル充足
COPY packages/financial-engine /app/financial-engine
RUN pip install /app/financial-engine

# 2) API パッケージ本体（残り依存は PyPI から、re-engine は充足済みで再取得しない）
COPY apps/api /app/api
RUN pip install /app/api

# 3) versioned プロンプトは src/api の wheel に含まれないため明示コピー＋環境変数で指す
COPY docs/prompts /app/docs/prompts
ENV REINVEST_PROMPTS_DIR=/app/docs/prompts

# Fly はコンテナ内ポートへルーティング（fly.toml の internal_port と一致させる）
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: `re_invest_os/.dockerignore` を作成**

```gitignore
**/__pycache__/
**/*.pyc
**/.pytest_cache/
**/.ruff_cache/
apps/web/
node_modules/
*.duckdb
*.parquet
reio.db
reio.db-shm
reio.db-wal
.venv/
tests/
```

- [ ] **Step 3: ローカルで image をビルドして起動確認**

Run:
```bash
cd /home/kazumasa/projects/re_invest_os
docker build -t reio-api:local .
docker run --rm -p 8080:8080 -e ANTHROPIC_API_KEY=dummy reio-api:local &
sleep 3 && curl -s localhost:8080/health && curl -s localhost:8080/version
```
Expected: `/health` が `{"status":"ok"}` 系、`/version` が engine/api バージョンを返す
（**確認事項**: プロンプトロードがエラーにならないこと。`/summarize` 等は実キー無しでは失敗するが `/health`/`/version`/`/analyze`（純粋計算）は通るはず）

### Task R1.2: fly.toml 生成と secrets 設定

**Files:**
- Create: `re_invest_os/fly.toml`（`fly launch` が生成。下記は参照値）

- [ ] **Step 1: `fly launch --no-deploy` で雛形生成**

Run:
```bash
cd /home/kazumasa/projects/re_invest_os
fly launch --no-deploy --dockerfile Dockerfile --name reio-api --region nrt
```
Expected: `fly.toml` 生成。Dockerfile を検出。DB プロビジョニングは「No」（Supabase を使うため）。

- [ ] **Step 2: `fly.toml` を以下に合わせて確認・調整**

```toml
app = "reio-api"            # 要: グローバル一意。既存と被ったら変更
primary_region = "nrt"      # Tokyo

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8080      # Dockerfile の EXPOSE と一致
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0  # アイドルで停止しコスト圧縮（コールドスタート許容）

  [[http_service.checks]]
    method = "GET"
    path = "/health"
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

- [ ] **Step 3: secrets を設定（値はシェル履歴に残さない運用で）**

Run:
```bash
fly secrets set \
  ANTHROPIC_API_KEY="sk-ant-..." \
  REINFOLIB_API_KEY="..." \
  LLM_PROVIDER="anthropic" \
  DATABASE_URL="<R2 で確定する Postgres URL>" \
  CORS_ALLOW_ORIGINS="<R3 で確定する Vercel URL>"
```
Expected: `fly secrets list` に5キーが表示（値は伏字）
（注: `DATABASE_URL` と `CORS_ALLOW_ORIGINS` は R2/R3 確定後に再 set する。順番上ここでは空でも可）

### Task R1.3: デプロイ

- [ ] **Step 1: デプロイ実行**

Run: `cd /home/kazumasa/projects/re_invest_os && fly deploy`
Expected: ビルド成功 → machine 起動 → `https://reio-api.fly.dev` 発行

- [ ] **Step 2: 本番ヘルスチェック**

Run: `curl -s https://reio-api.fly.dev/health`
Expected: `{"status":"ok"}` 系

---

## Phase R2 — 本番DB（Supabase Postgres）

### Task R2.1: Supabase プロジェクト作成と接続文字列取得

- [ ] **Step 1: Supabase で新規プロジェクト作成**（Region: Tokyo / 無料枠）
- [ ] **Step 2: 接続文字列を取得し asyncpg 形式へ変換**
  - Supabase の "Connection string" を取得。SQLAlchemy async 用に **`postgresql+asyncpg://`** へ書き換える。
  - **Gotcha**: Supabase の Transaction pooler(6543) は prepared statement 非対応。asyncpg で使うなら接続オプションで prepared statement cache を無効化する必要がある。**最小構成では Direct connection(5432) または Session pooler を使う**のが安全。
  - 例: `postgresql+asyncpg://postgres:<password>@db.<ref>.supabase.co:5432/postgres`

### Task R2.2: マイグレーション適用

> 本プロジェクトは alembic を使わず `infra/migrations/*.sql` を直接適用する方針。

- [ ] **Step 1: SQL を Supabase SQL Editor で順に実行**
  - `infra/migrations/v1_analyses.sql`
  - `infra/migrations/v2_deal_workspace.sql`
  Expected: `analyses` / `extraction_corrections` / `uploaded_documents` / deal workspace 系テーブル作成
- [ ] **Step 2: `db.py` が起動時 auto-init とマイグレーションSQLで二重定義にならないか確認**
  - `apps/api/src/api/db.py` の起動時テーブル作成が Postgres でも整合するか（SQLite前提のDDLがないか）を確認。差異があればこのタスクで吸収。

### Task R2.3: API に DATABASE_URL を反映

- [ ] **Step 1: Fly secret を更新**

Run: `fly secrets set DATABASE_URL="postgresql+asyncpg://postgres:...@db.<ref>.supabase.co:5432/postgres"`
Expected: machine 再起動
- [ ] **Step 2: 永続化の疎通確認（保存→取得）**

Run:
```bash
# 保存（/analyze→/analyses）後に返る UUID で GET
curl -s https://reio-api.fly.dev/analyses | head
```
Expected: 200 応答。保存した分析が Postgres から取得できる（SQLite ではなく）。

---

## Phase R3 — Web → Vercel

### Task R3.1: Vercel プロジェクト作成（monorepo 対応）

- [ ] **Step 1: GitHub 連携でプロジェクト import**
  - **Root Directory** = `re_invest_os/apps/web`（Task R0.2 で B を選んだ場合は `apps/web`）
  - Framework Preset = **Next.js**（自動検出）
  - Install/Build Command は既定（`next build`）。pnpm workspace を使う場合は Vercel の pnpm 検出に任せる。
- [ ] **Step 2: 環境変数を設定（Production / Preview）**
  - `API_BASE = https://reio-api.fly.dev`（**NEXT_PUBLIC ではない**。route handler のサーバ側で参照）
  - （認証を使う場合のみ）`NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`。最小公開では未設定＝認証「準備中」表示でOK。
- [ ] **Step 3: デプロイ**
  Expected: `https://<project>.vercel.app` 発行、トップ/LP が表示

### Task R3.2: CORS を Vercel ドメインに合わせる

- [ ] **Step 1: API の CORS を更新**

Run: `fly secrets set CORS_ALLOW_ORIGINS="https://<project>.vercel.app"`
Expected: machine 再起動
（注: Web のサーバ側 route handler 経由で API を叩く構成のため CORS はブラウザ直叩きが無ければ厳密には不要だが、`/docs` や将来のクライアント直叩きに備え正しいオリジンを設定）

---

## Phase R4 — 結線・E2E スモークテスト（= 最小公開の完了点）

### Task R4.1: 実フローのエンドツーエンド確認

- [ ] **Step 1: LP → Upload → Confirm → Report を実ブラウザで通す**
  - `https://<project>.vercel.app/upload` で実URL もしくは PDF を投入
  - `/confirm` で抽出結果が表示・修正できる
  - `/report` で KPI・AI Insight・前提甘さ・ストレス・収支耐性価格帯・クロスアセットが描画される
  Expected: 各パネルが本番 API から実データで描画。エラーパネルが出ない。
- [ ] **Step 2: 共有URL の往復**
  - `/report` 自動保存 → 共有URLバナーの `/analyses/[id]` を別タブで開く
  Expected: Postgres から復元表示
- [ ] **Step 3: Market Context（国交省実データ）の表示**
  Expected: 対象エリアの取引価格グラウンディングが出る（`REINFOLIB_API_KEY` 有効）

### Task R4.2: 公開前チェックリスト（Definition of Done）

- [ ] テスト全緑（R0.1）・型緑を最終確認
- [ ] secrets がコード/コミットに含まれていない（`git grep -i "sk-ant"` が空、`.env` は gitignore）
- [ ] prod が SQLite ではなく Postgres を使っている（`reio.db` 不使用）
- [ ] 免責表示（`DISCLAIMERS`）が LP/Report に出る・NG表現テスト緑（`test_ng_expressions.py`）
- [ ] 「投資助言ではない／前提検証ツール」の文言が初見導線に出る
- [ ] `overall_risk` が常時 HIGH に見える件の注記が UI に出る（誤解防止）
- [ ] Fly machine の min_machines_running=0 によるコールドスタートが許容範囲

**→ ここまでで「認証なし・無料の動く本番URL」公開が完了。**

---

## Phase R5 —（将来）有料・会員制公開

> 最小公開後に積み増す。各々が独立タスクなので別計画化推奨。

- [ ] **認証有効化**: Supabase Auth プロジェクト設定 → `NEXT_PUBLIC_SUPABASE_*` 設定 → `/login`/`/signup`/`/auth/callback` 有効化 → API 側の保護ルート判定追加
- [ ] **法務確定**: 利用規約/プライバシー/**特商法表記**を弁護士レビュー → `/terms` `/privacy` `/tokutei` 反映（課金開始の前提条件）
- [ ] **課金(Stripe)**: 商品/価格設定 → Checkout → webhook で権限付与。レポート課金 or サブスク（青写真の収益モデルに合わせる）
- [ ] **監視**: Sentry（API/Web のエラー）＋ PostHog（ファネル）。`analysis_runs.cost_usd_estimated` で LLM コスト監視＋上限 kill switch
- [ ] **独自ドメイン**: 取得 → Vercel/Fly に割当 → `API_BASE`/`CORS_ALLOW_ORIGINS` を独自ドメインに更新
- [ ] **CD 自動化**: `ci.yml` に Fly deploy（main マージで `fly deploy`）、Vercel は GitHub 連携で自動

---

## コスト見積もり（月額・概算）

| サービス | 役割 | 無料/最小 | スケール時 |
|---|---|---|---|
| Fly.io | API（shared-cpu-1x/512MB, idleで停止） | ~$0–5 | $5–15（常時起動/複数machine） |
| Vercel | Web | $0（Hobby） | $20（Pro、商用は要Pro） |
| Supabase | Postgres+Auth+Storage | $0（Free） | $25（Pro） |
| Anthropic | LLM（Haiku, 1分析あたり数¢想定） | 従量・低額 | 利用量比例（kill switch で上限管理） |
| ドメイン | 独自ドメイン（任意） | ¥0（vercel.app利用） | ~¥1,000–2,000/年 |
| Sentry / PostHog | 監視（R5） | $0（無料枠） | 従量 |
| Stripe | 決済（R5） | 固定費0 | 取扱高 × ~3.6%（国内） |

- **最小公開（R0〜R4）**: 実質 **~$0–5/月 + Anthropic 従量**。ドメイン無しで vercel.app/fly.dev を使えば固定費ほぼゼロ。
- **有料公開（R5まで）**: **~$45–60/月**（Vercel Pro + Supabase Pro + Fly）＋ LLM 従量 ＋ 決済手数料。

---

## Self-Review（spec カバレッジ確認）

- リポジトリ戦略（monorepo/分割）→ R0.2 でカバー
- API コンテナの uv workspace 依存解決問題 → R1.1 で engine 先行 install により解決
- 本番DB（SQLite→Postgres）＋ pooler の prepared statement gotcha → R2.1/R2.2 でカバー
- Web の API 切替（`API_BASE`）→ R3.1 でカバー
- 国交省キー（Market Grounding）→ R0.3/R1.2/R4.1 でカバー
- 法務・課金・認証・監視（公開ブロッカー）→ R5 に分離
- コスト見積もり → 専用セクションでカバー
- placeholder（TBD等）なし。ファイル内容・コマンド・Expected は具体化済み。
