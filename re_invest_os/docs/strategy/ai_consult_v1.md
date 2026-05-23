# re_invest_os — AI 相談用サマリ (v1)

作成日: 2026-05-22
目的: 別 AI (ChatGPT 等) に貼り付けて開発方向性を相談するための単一ファイル。
読み手前提: プロダクト未経験。背景ゼロでも判断できるよう自己完結させる。

---

## 0. 30 秒サマリ

- **何**: 個人投資家向け「不動産買付前 DD (デューデリ) Web アプリ」
- **誰に**: 区分 / 戸建を検討中の個人投資家。仲介に踊らされず自分で判断したい層
- **差別化**: **業者にユーザー情報を売らない**ことを技術的に担保した「買う側のためのツール」
- **状態**: ソロ開発、Phase C 完了 (2026-05-17)。全機能の "技術骨格" は動く。本番未デプロイ・課金未実装・ユーザーゼロ
- **次の意思決定**: 「先に何を verify するか」— ユーザー価値 / 収益 / 法務 / 運用コストの **どこから検証するか**

---

## 1. プロダクト現状

### 1.1 動く機能 (ローカル、135 tests passing)

| カテゴリ | 機能 |
|---|---|
| 入力 | 楽待 / 健美家 / SUUMO の URL 解析、販売図面 PDF / レントロール抽出 |
| AI | Anthropic Claude Haiku 4.5 で構造化抽出 (PII マスク経由)。Ollama (gemma3:12b) ローカル切替可 |
| 分析エンジン | NOI / DSCR / 税後 CF / IRR / Equity Multiple / Payback (純粋関数、84 tests) |
| 出口 | 売却価格・残債・譲渡税・税後手残り |
| 感応度 | 賃料↓・空室↑・金利↑・OPEX 増・複合の 12 シナリオ |
| 最大買付 | DSCR≥1.25 / IRR≥8% を満たす上限価格を二分探索 |
| クロスアセット | 税後 IRR を全世界株 / J-REIT / 国債 / 定期と比較 |
| AI Insight | 3 行サマリー + 仲介確認質問 + 前提甘さ検出 |
| 永続化 | SQLite 保存、UUID 共有 URL、履歴・最大 5 件比較ボード |
| 法務 | /terms /privacy /tokutei (弁護士レビュー前草案) |

### 1.2 サンプル出力 (西新宿レジデンス 504 号)

価格 3,980 万 / RC / 築 15 年 / 1LDK 38.4㎡ / 月 145,000 円
→ **Score 36.5 (要警戒)** 表面利回り 6.2% でも DSCR 0.96 / ATCF Y1 -¥45,362 / 出口損失

「数字上は買えそうに見える物件が実は危ない」ことを示せている。

### 1.3 技術スタック (詳細)

#### モノレポ構成

```
re_invest_os/
├── apps/
│   ├── api/      (re-invest-os-api)   FastAPI バックエンド
│   ├── web/      (@re_invest_os/web)  Next.js フロント
│   └── worker/                        バックグラウンド ジョブ (pyproject なし、未本格運用)
├── packages/
│   ├── financial-engine/  (re-engine) 計算エンジン (純粋関数)
│   ├── document-schemas/              抽出スキーマ (pyproject なし、path import)
│   └── shared-schemas/                クロスアプリ共通
├── infra/migrations/      SQL スキーマ
├── scripts/               ETL (公示地価 / 取引価格 / 賃料)
└── docs/                  仕様 / プロンプト / 法務 / ロードマップ
```

- **Python**: uv ワークスペース (`re-engine`, `re-invest-os-api`)。`pyproject.toml` で workspace cross-import
- **Node**: pnpm 11 ワークスペース (`apps/*`, `packages/*`)、Node >= 22

#### バックエンド (`apps/api`)

| 用途 | パッケージ | バージョン |
|---|---|---|
| Web framework | fastapi | >=0.115 |
| ASGI server | uvicorn[standard] | >=0.32 |
| ORM | sqlalchemy | >=2.0 (async) |
| SQLite driver | aiosqlite | >=0.20 |
| Validation | pydantic | >=2.9 |
| LLM (本番) | anthropic | >=0.50 (Claude Haiku 4.5) |
| LLM (フォールバック) | openai | >=2.36 |
| HTTP client | httpx | >=0.28 |
| HTML parser | selectolax | >=0.3.21 (楽待/SUUMO 抽出) |
| PDF parser | pypdf | >=5.1 |
| Multipart upload | python-multipart | >=0.0.20 |
| Env loader | python-dotenv | >=1.0 |
| Test | pytest | >=8.0 |
| PDF test fixture | reportlab | >=4.2 (dev) |

**サービス層** (`apps/api/src/api/services/`):
- `llm_client.py` — Ollama / Anthropic / OpenAI を `LLM_PROVIDER` env で切替
- `pii.py` — LLM 送信前マスク (氏名・電話・メール regex)
- `prompts.py` — `docs/prompts/*.md` バージョン管理ローダー
- `summarizer.py` — 3 行サマリ / 確認質問 / 前提甘さ批判
- `market_context.py` — 近傍地価コンテキスト (現在 stub)
- `extractors/` — classify / property_brochure / rent_roll / source_url / source_pdf / to_assumptions

#### 計算エンジン (`packages/financial-engine`, `re-engine`)

| 用途 | パッケージ |
|---|---|
| Validation | pydantic >=2.9 |
| 数値 | numpy >=2.0, numpy-financial >=1.0 |

**モジュール** (12 本、純粋関数のみ・I/O 禁止):
`constants / models / loan / cashflow / tax / exit / irr / score / max_offer / sensitivity / cross_asset / analyze`

- `engine_version` (semver) を全結果に埋め込み (再現性担保)
- LLM 呼び出し・ネットワーク・ファイル I/O すべて禁止

#### フロントエンド (`apps/web`)

| 用途 | パッケージ | バージョン |
|---|---|---|
| Framework | next | 16.2.6 (App Router) |
| UI | react / react-dom | 19.2.4 |
| 言語 | typescript | ^5 (strict) |
| Styling | tailwindcss + @tailwindcss/postcss | ^4 |
| Auth client | @supabase/ssr, @supabase/supabase-js | ^0.10 / ^2.105 |
| API 型生成 | openapi-typescript | ^7.13 (`pnpm gen:api` で FastAPI OpenAPI → `src/types/api.ts`) |

**App Router ルート** (14 ページ + 11 API route):
`/` `/lp` `/upload` `/confirm` `/report` `/history` `/compare` `/new`
`/analyses/[id]` `/login` `/signup` `/auth/callback` `/terms` `/privacy` `/tokutei`

**共通コンポーネント** (`src/components/`):
- `bloomberg.tsx` — Panel / Row / KpiCell / Badge / Btn / Field / Input / Select (Bloomberg Terminal 風)
- `report-panels.tsx` — SensitivityPanel / MaxOfferPanel / CrossAssetPanel など
- `nav.tsx` — グローバルナビ

**通信パターン**: ブラウザ → Next.js Route Handler → FastAPI (同一オリジン経由で CORS 回避)

#### データ層

| 環境 | DB | マイグレーション |
|---|---|---|
| dev | SQLite (`reio.db`, aiosqlite) | `infra/migrations/v1_analyses.sql` 自動適用 |
| 本番 (予定) | Supabase Postgres | 同 SQL を流用、未投入 |

**主要テーブル**: `analyses` / `extraction_corrections` / `uploaded_documents`

**外部データ ETL** (`scripts/`):
- `etl_public_notice.py` — 国交省 公示地価 (DuckDB → SQL INSERT)
- `etl_trade_prices.py` — 不動産取引価格
- `etl_rent_market.py` — 賃料相場
→ 出力は SQL ファイル、Supabase 投入は未実施

#### LLM 運用

| プロバイダ | モデル | 用途 |
|---|---|---|
| Anthropic (本番) | claude-haiku-4-5 | URL 抽出 / PDF 抽出 / サマリ / 質問生成 / 批判 |
| Ollama (ローカル) | gemma3:12b (8.1GB) / qwen2.5:7b (4.7GB) | dev 中の bench、PII を外に出さない検証 |
| OpenAI (フォールバック) | 未使用 | 切替インタフェースのみ |

- Ollama は `format="json"` 強制 (schema 渡しで optional フィールドが落ちる既知問題)
- プロンプトは `docs/prompts/<name>_v<n>.md` でバージョン管理、`prompt_versions` を結果に記録

#### インフラ (予定 / 未デプロイ)

| レイヤ | サービス |
|---|---|
| Web ホスティング | Vercel |
| API ホスティング | Fly.io |
| DB / Auth / Storage | Supabase |
| ドメイン / DNS | Cloudflare (予定) |
| 決済 | Stripe (未実装) |
| 監視 | Sentry (未統合) |
| 行動分析 | PostHog (未統合) |

#### CI / 開発ツール

| 用途 | ツール |
|---|---|
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Python lint/format | ruff |
| JS format | prettier |
| Python pkg管理 | uv (workspace) |
| Node pkg管理 | pnpm 11 (workspace) |
| 型生成 | openapi-typescript |

#### テスト・品質指標 (2026-05-17 時点)

```
Python tests   : 135 passing (engine 84 + api 51)
Ruff           : clean
TypeScript     : tsc --noEmit clean
Next build     : 14 routes (App Router)
API endpoints  : 13 (health/version/analyze/extract×2/summarize/critique
                    /sensitivity/max_offer/cross_asset/analyses×3)
```

#### 起動コマンド

```bash
# 依存 (workspace ルート)
make install                       # = uv sync --all-packages
cd re_invest_os && pnpm install

# API (port 8001)
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001

# Web (port 3001)
cd apps/web && node_modules/.bin/next dev --port 3001

# テスト
uv run pytest -q
cd apps/web && node_modules/.bin/tsc --noEmit
```

---

## 2. 未実装・未決定 (ブロッカー)

| 種別 | 項目 | 備考 |
|---|---|---|
| インフラ | Supabase プロジェクト未作成 | 認証・本番 DB |
| インフラ | ドメイン・本番デプロイ未着手 | Vercel + Fly.io |
| 課金 | Stripe 完全未実装 | プラン設計も未確定 |
| ブランド | プロダクト名・ロゴ未確定 | コードネーム re_invest_os |
| 法務 | 弁護士レビュー未実施 | 投資助言扱いのリスク |
| データ | ETL スクリプトは書いたが Supabase 投入未実施 | 公示地価 / 取引価格 / 賃料 |
| 検証 | **ユーザー 0 人**。価値の外部検証ゼロ | ← 一番の不確実性 |

---

## 3. 相談したい 4 つの論点

### Q1. プロダクト方向性・MVP 範囲

**現状の論点**:
- 機能は青写真 26 章フルで実装済 → 「機能過多なのに使ってもらえない」リスク
- 「個人投資家の DD」という Job To Be Done が広い。先に絞るべきか?
  - A. 区分マンション 1 室の "買う / 買わない判断" 特化
  - B. 戸建 / 一棟も含む汎用 DD
  - C. 「楽待スクレイピング → 簡易スコア」だけの最小 SaaS から始める
- 「買付前」だけでなく「保有中の物件モニタリング」まで広げるか?

**相談したいこと**:
1. このプロダクトで **最初に削ぎ落とすべき機能** はどれか
2. β 出すとき「1 つだけ尖らせる」なら何にするか (AI 質問生成? 最大買付? 感応度?)
3. "業者送客しない" のブランド主張は刺さるのか、それとも内輪ウケで終わるか

### Q2. 収益化・課金モデル

**現状の論点**:
- Stripe 未実装、価格未決定
- 想定: Free (月 10 分析) / Pro (¥1,980/月、無制限 + PDF 出力 + 感応度詳細)
- 単発レポート課金 (¥300-980) を別途出すかは未決
- 個人投資家は **月額課金に弱い** という仮説 (買付検討期間しか使わない)

**相談したいこと**:
1. 月額 vs 単発レポート vs ハイブリッド、どれが個人投資家層と相性良いか
2. 「買う / 買わない」を決めたら解約される → LTV をどう設計するか
3. 競合 (楽待のスコア機能、健美家、リレマ等) との価格ポジショニング
4. 法人 / 業者向けに転用すれば収益は太いが、ブランド (業者送客しない) と衝突。線引きの落とし所

### Q3. Go-to-market・初期ユーザー獲得

**現状の論点**:
- ソロ開発・マーケ未経験。週 20-25h 稼働
- 想定流入: X (旧 Twitter) の不動産投資クラスタ、note、ProductHunt
- 友人 β 5-10 人は確保可能。**それ以外の 20 人をどう連れてくるか** が未定
- 3 か月後 KPI: 月間分析 1,000 件 / 登録 100 / 有料 5

**相談したいこと**:
1. ソロ開発者がゼロイチで個人投資家コミュニティに入っていく現実的な経路
2. β 期間に「無料で価値を渡す代わりに何を回収するか」(フィードバック? 紹介? ケーススタディ?)
3. SEO ターゲット (例: 「楽待 スコア」「区分マンション DSCR」など) は最初から狙うべきか
4. インフルエンサー (不動産系 YouTuber / ブロガー) との連携の現実性と落とし穴

### Q4. 技術・運用 (インフラ / LLM コスト / 法務)

**現状の論点**:

- **LLM コスト**: 1 分析あたり Claude Haiku で URL 抽出 + 図面抽出 + サマリ + 質問生成 + 批判 = 5 回前後の呼び出し。原価試算未実施
- **インフラコスト**: Vercel + Fly.io + Supabase で月いくらに収まるか試算未
- **スクレイピング**: 楽待 / SUUMO の HTML 構造変更に追従する保守コスト。利用規約上の灰色
- **法務**: "投資助言" 扱い回避の表現指針はあるが、弁護士レビュー未。スコア表示は「助言」と取られないか
- **PII**: マスク実装済だが、業者連絡先・室内写真などの扱いは未整理
- **本番 DB**: SQLite → Supabase Postgres 移行時のマイグレーション順序

**相談したいこと**:
1. LLM コスト原価試算の妥当な方法 (1 ユーザー月あたりいくらまで許容できるか)
2. スクレイピングの利用規約リスクと、公式 API / 提携の現実性
3. "スコア表示 + 買付推奨" の境界線。日本の宅建業法・金商法・景表法の観点で本当に大丈夫か
4. ソロ運用で持続可能な監視 (Sentry / PostHog) の最低限セット

---

## 4. 開発原則 (動かしてはならないもの)

1. 計算を LLM に任せない (AI = 読む / 分類 / 説明、Engine = 純粋関数)
2. 抽出結果は Pydantic 検証 + coerce
3. `engine_version` + `prompt_versions` を全分析に記録 (再現性)
4. LLM 送信前に PII マスク
5. **業者送客しないことを技術的に担保** (ブランドの中核)

これらは相談の前提として固定。

---

## 5. 既存ドキュメント (深掘り用リンク)

| ファイル | 用途 |
|---|---|
| `docs/product/blueprint_v0_1.md` | 青写真 26 章 (事業方針 / 機能 / KPI / 収益) |
| `docs/product/product_requirements.md` | PRD (機能 25 個 P0-P2) |
| `docs/architecture/calculation_engine_spec.md` | 計算仕様 (CF / 税 / IRR / Score / 感応度 / 最大買付) |
| `docs/architecture/ai_document_extraction_spec.md` | AI 抽出パイプライン |
| `docs/architecture/technical_architecture.md` | インフラ・LLM・監視・課金設計 |
| `docs/legal/legal_risk_checklist.md` | 表現 NG/OK・PII・特商法 |
| `docs/roadmap/mvp_roadmap.md` | 12 週マイルストーン |
| `docs/prompts/` | 全プロンプト (バージョン管理) |

---

## 6. 相談者 (kazumasa) プロフィール

- ソロ開発、平日 2-3h / 週末 6-10h
- 不動産投資の実務知識あり (自身で買付検討経験)
- 法人化は利益安定後、現在は個人事業
- 「業者送客しない」は強い信念。収益のためでもここは譲らない方針
- 技術: Python / TypeScript 主戦場。インフラ・マーケは未経験寄り

---

## 7. AI への質問テンプレ (使用例)

> 上記の re_invest_os について、以下を順に答えてください:
>
> 1. このプロダクトでまず削るべき機能 Top 3 と理由
> 2. ソロ開発で 3 か月後に有料ユーザー 5 人を達成する現実的な道筋
> 3. 月額 vs 単発レポート、どちらを MVP に据えるか
> 4. "業者送客しない" を売りにすることの集客上のメリット・デメリット
> 5. スコア表示が投資助言と判定されないための最低限の表現指針
