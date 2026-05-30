# re_invest_os

> 個人投資家のための不動産買付前監査OS。  
> 業者資料をそのまま信じないための、AI駆動DDツール。

物件URLを貼るか販売図面PDFを投げると、AIが資料を読み取り、収支・融資耐性・出口シナリオ・前提の甘さ・代替資産比較を自動で提示する。**業者にユーザー情報を売らない**ことを技術的に担保した、買う側のための分析ツール。

> **MVP再定義 (2026-05-30):** プロダクトを「営業資料を金融プロ水準で検証する**中立DDエンジン**」へ再定義。
> 提供価値は「買いか？」ではなく **前提の甘さ／ストレス耐性／収支耐性価格帯／仲介確認事項**。
> 物件価値判断（健全/要警戒の100点スコア）は撤去し、**甘さスコア**（前提別 confidence A–D + risk_level）を中核に。
> NG表現（買い/推奨買付価格/おすすめ 等）はテストで担保。詳細: `docs/design/2026-05-30-mvp-redefinition-design.md`。

---

## できること（現在の実装）

| 機能 | 説明 |
|---|---|
| URL解析 | 楽待・健美家・SUUMOのURLを貼るとAIが物件情報を抽出 |
| PDF解析 | 販売図面・レントロールのPDFをアップロードして抽出 |
| 抽出確認 | AI抽出結果をユーザーが確認・修正してから分析実行 |
| 収支シミュレーション | NOI / DSCR / 税後CF / IRR / Equity Multiple / Payback |
| 出口シナリオ | 売却価格・残債・譲渡税・税後手残りを計算 |
| 感応度分析 | 賃料↓・空室↑・金利↑・OPEX増・複合ストレスの12シナリオ |
| 最大買付価格 | DSCR≥1.25 / IRR≥8% を維持できる上限価格を二分探索 |
| クロスアセット比較 | 税後IRRを全世界株・J-REIT・国債・定期預金と比較 |
| 前提甘さ検出 | 楽観的すぎる前提を自動フラグ（ルールベース + LLM） |
| AIサマリー | 3行監査サマリー + 仲介への確認質問リストを生成 |
| 分析保存・共有URL | 分析結果をUUIDリンクで保存・共有 |
| 分析履歴・比較ボード | 複数物件を横並びで比較（最大5件） |

---

## アーキテクチャ

```
ブラウザ (Next.js)
    │
    │ fetch /api/*  (同一オリジン、CORS回避)
    ▼
Next.js Route Handlers  ──proxy──▶  FastAPI (port 8001)
                                         │
                              ┌──────────┼──────────┐
                              ▼          ▼           ▼
                        financial-   LLM Client   SQLite / 
                         engine       (Anthropic   Supabase
                        (純粋関数)    / Ollama)    Postgres
```

**技術スタック**

| レイヤー | 技術 |
|---|---|
| Frontend | Next.js 16 (App Router) + TypeScript |
| Backend | FastAPI (Python 3.12+) + SQLAlchemy 2.x async |
| 計算エンジン | Python パッケージ `re_engine`（純粋関数、LLM不使用） |
| DB | SQLite（dev） / Supabase Postgres（本番） |
| LLM | Anthropic Claude Haiku（本番） / Ollama（ローカル開発） |
| Auth | Supabase Auth（未有効化） |
| Hosting | Vercel（web） + Fly.io（api） + Supabase |

---

## ディレクトリ構成

```
re_invest_os/
├── apps/
│   ├── api/                    # FastAPI バックエンド
│   │   ├── src/api/
│   │   │   ├── main.py         # エンドポイント定義
│   │   │   ├── db.py           # SQLAlchemy async
│   │   │   └── services/
│   │   │       ├── llm_client.py       # Ollama / Anthropic 切替
│   │   │       ├── pii.py              # LLM送信前PIIマスク
│   │   │       ├── prompts.py          # バージョン管理プロンプトローダー
│   │   │       ├── summarizer.py       # サマリー・確認質問・前提批判
│   │   │       └── extractors/         # URL・PDF・レントロール抽出
│   │   └── tests/
│   └── web/                    # Next.js フロントエンド
│       └── src/
│           ├── app/            # App Router ページ (14ページ / 11 API routes)
│           └── components/
│               ├── bloomberg.tsx       # Bloomberg Terminal 風 UI コンポーネント
│               └── report-panels.tsx   # 監査レポートパネル群
├── packages/
│   └── financial-engine/       # 計算ロジック（re_engine）
│       └── src/re_engine/
│           ├── analyze.py      # 統合分析エントリポイント
│           ├── cashflow.py     # 年次CF計算
│           ├── loan.py         # 元利均等返済
│           ├── tax.py          # 減価償却・譲渡税
│           ├── irr.py          # IRR二分探索
│           ├── score.py        # 100点スコアリング
│           ├── sensitivity.py  # 感応度分析（12シナリオ）
│           ├── max_offer.py    # 最大買付価格（制約付き二分探索）
│           └── cross_asset.py  # クロスアセット比較
├── docs/
│   ├── product/                # プロダクト仕様・青写真
│   ├── architecture/           # 計算エンジン・AI抽出・DB・インフラ仕様
│   ├── prompts/                # LLMプロンプトのバージョン管理
│   ├── legal/                  # 利用規約・プライバシー・特商法（草案）
│   ├── design/                 # UIデザイン原則・ワイヤーフレーム・モックアップ
│   └── roadmap/                # 開発計画・進捗
├── infra/
│   └── migrations/             # SQLスキーマ定義
└── scripts/                    # ETLスクリプト（公示地価・取引価格・賃料データ）
```

---

## セットアップ

### 前提条件

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- LLM: [Ollama](https://ollama.com/)（ローカル開発）または Anthropic API キー（本番）

### 1. リポジトリのクローン・依存インストール

```bash
git clone <repo>
cd re_invest_os

# Python 依存（financial-engine + api）
uv sync --all-packages

# Node 依存（web）
cd apps/web && npm install && cd ../..
```

### 2. 環境変数の設定

```bash
cp apps/api/.env.example apps/api/.env
# .env を編集して必要な値を入力
```

環境変数の詳細は [apps/api/.env.example](apps/api/.env.example) を参照。

### 3. 起動

```bash
# API サーバー（port 8001、初回起動時にSQLiteを自動生成）
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001

# Web サーバー（別ターミナル、port 3001）
cd apps/web && node_modules/.bin/next dev --port 3001
```

ブラウザで http://localhost:3001 を開く。

### 4. 動作確認

```bash
# Python テスト（135件）
uv run pytest -q

# TypeScript 型チェック
cd apps/web && node_modules/.bin/tsc --noEmit

# API ヘルスチェック
curl http://127.0.0.1:8001/health
```

---

## 画面フロー

```
/lp          ランディングページ（サービス説明）
/upload      物件URLまたはPDFを投入
/confirm     AI抽出結果を確認・修正
/report      監査レポート（Bloomberg UI）
  ├─ KPI パネル（Cap Rate / DSCR / IRR / Equity Multiple）
  ├─ AI Insight（3行サマリー + 確認質問）
  ├─ 前提甘さ検出（critical / warn フラグ）
  ├─ キャッシュフロー表（10年）
  ├─ 出口シナリオ
  ├─ スコアブレークダウン（100点）
  ├─ 感応度分析（12ストレスシナリオ）
  ├─ 最大買付価格（制約付き二分探索）
  └─ クロスアセット比較（vs 株・REIT・債券・定期預金）
/history     分析履歴一覧
/compare     物件比較ボード（最大5件）
/analyses/:id  共有URL（保存済み分析の閲覧）
/new         手動入力による直接分析
```

---

## API エンドポイント

FastAPI 起動後、http://127.0.0.1:8001/docs でSwagger UIを確認できる。

| メソッド | パス | 説明 |
|---|---|---|
| GET | /health | ヘルスチェック |
| GET | /version | エンジン・APIバージョン |
| POST | /analyze | Assumptions → AnalysisResult + Score |
| POST | /extract/url | URL → AI抽出 → Assumptions |
| POST | /extract/document | PDF → AI抽出 → Assumptions |
| POST | /summarize | 分析結果 → 3行サマリー + 確認質問 |
| POST | /critique | 前提甘さ検出 |
| POST | /sensitivity | 感応度分析（12シナリオ） |
| POST | /max_offer | 最大買付価格（二分探索） |
| POST | /cross_asset | クロスアセット比較 |
| POST | /analyses | 分析結果を保存 → UUID返却 |
| GET | /analyses | 分析履歴一覧 |
| GET | /analyses/:id | 共有URL用取得 |

---

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/product/blueprint_v0_1.md](docs/product/blueprint_v0_1.md) | プロダクト青写真（事業方針・機能・KPI・収益モデル） |
| [docs/architecture/calculation_engine_spec.md](docs/architecture/calculation_engine_spec.md) | 計算エンジン仕様（CF・税・IRR・スコア・感応度・最大買付） |
| [docs/architecture/ai_document_extraction_spec.md](docs/architecture/ai_document_extraction_spec.md) | AI抽出仕様（分類・抽出・PII・フォールバック） |
| [docs/architecture/data_schema.md](docs/architecture/data_schema.md) | DBスキーマ・JSONスキーマ定義 |
| [docs/architecture/technical_architecture.md](docs/architecture/technical_architecture.md) | インフラ・LLM・監視・課金設計 |
| [docs/legal/legal_risk_checklist.md](docs/legal/legal_risk_checklist.md) | 法務チェックリスト（弁護士レビュー前草案） |
| [docs/prompts/](docs/prompts/) | LLMプロンプトのバージョン管理 |
| [docs/roadmap/progress.md](docs/roadmap/progress.md) | 開発進捗 |

---

## 開発原則

1. **計算をLLMに任せない** — AI=読む・分類・説明、計算エンジン=純粋関数
2. **抽出結果は必ずPydanticスキーマ検証** — LLM出力をそのまま信用しない
3. **再現性の担保** — 全分析結果に `engine_version` + `prompt_versions` を記録
4. **PIIマスク** — LLM送信前に個人情報を除去
5. **業者送客しない** — ユーザー情報を外部サービスに送信しないことを技術的に担保

---

## ブランドの約束

```
当サービスは、不動産会社・仲介会社・販売会社にユーザー情報を販売しません。
個別の明示同意なしに、不動産会社・金融機関・営業会社へ情報提供することはありません。
物件提案・営業電話・面談誘導を目的としたサービスではありません。
```

---

## ライセンス・運用

個人事業として開発・運営（法人化は利益が安定してから検討）。  
法務ページ（利用規約・プライバシーポリシー・特商法）は弁護士レビュー前の草案。
