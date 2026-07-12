# market-viz

`market-viz` は個人用のマーケット可視化・分析アプリ。yfinance / ccxt で株式・暗号資産の価格を取得して DuckDB に蓄積し、ボラティリティ・z スコア・ドローダウン・相関・シグナル・バックテスト・アラートを Streamlit 上で対話的に確認する。

探索 UI は Streamlit、構造化データの配信は FastAPI バックエンド、フロントエンドとして任意の Next.js スキャフォールドを持つ。Phase 1 MVP 完了。

## 主な機能

- **マーケットダッシュボード / チャートワークベンチ**: 価格・リターンの俯瞰と個別チャート探索
- **相関モニター**: 銘柄間の相関の可視化
- **シグナルランキング**: `analytics/signals.py` によるシグナルの横断ランキング
- **バックテスト**: `analytics/backtest.py` による検証
- **アラートモニター**: 条件監視（backend の `alerts` ルーター）
- **データ更新**: `data/update.py` の `update_daily`（日次）/ `update_crypto_intraday`（暗号資産イントラデイ）がサイドバーから実行できる唯一の正規経路

## 技術スタック

| 層 | 技術 |
|---|---|
| UI | Streamlit（`app/main.py` + `pages/01`–`06`）+ Plotly |
| ライブラリ | Python 3.12+ / pandas / numpy / scipy |
| データ取得 | yfinance（株式ほか）・ccxt（暗号資産） |
| ストレージ | DuckDB（`storage/duckdb_client.py` が唯一の接続点） |
| バックエンド | FastAPI + uvicorn（port 8000） |
| フロントエンド | Next.js + pnpm（任意、port 3000） |

## セットアップと実行

依存関係はワークスペースルート `~/projects/` の単一 `.venv` に入る（uv workspace）。

```bash
# 初回インストール（ワークスペースルートで）
cd ~/projects
uv sync --all-packages        # = make install

# 環境変数（JQUANTS_API_KEY など）
cp market-viz/.env.example market-viz/.env   # 値を記入

# Streamlit アプリ起動
uv run --no-sync streamlit run market-viz/app/main.py
```

バックエンド・フルスタックを使う場合:

```bash
# フルスタック（backend :8000 + frontend :3000）
cd ~/projects/market-viz && ./start.sh

# バックエンドのみ（market-viz/ で）
uv run --no-sync uvicorn backend.app.main:app --reload --port 8000
```

初回はサイドバーの「日次データ更新」（`update_daily`）を一度実行すること。実行時 DB `market-viz/data/market.duckdb` は gitignore されており、未作成のままだと各ページは空表示になる。

## プロジェクト構成

```text
market-viz/
├── app/                 # Streamlit（main.py + pages/01_market_dashboard … 06_alert_monitor）
│   └── components/      # charts / filters / tables
├── backend/app/         # FastAPI（routers: prices, instruments, analytics, backtest, alerts, data_update）
├── frontend/            # Next.js スキャフォールド（任意）
├── src/market_viz/      # ライブラリ本体（import は market_viz、src からは import しない）
│   ├── analytics/       # volatility, zscore, correlation, drawdown, returns, signals, backtest
│   ├── data/            # yfinance / ccxt ローダと更新オーケストレーション
│   ├── storage/         # DuckDB クライアント
│   └── config/          # instruments.yaml / settings.yaml
├── tests/               # pytest スイート
├── data/                # 実行時 DuckDB（gitignore）
└── start.sh             # backend + frontend 同時起動
```

分析関数は DataFrame in / DataFrame out の決定的・副作用なしで書き、IO は `data/` と `storage/` に置く。ページから yfinance / ccxt を直接呼ばない。

## テスト

```bash
cd ~/projects
uv run --no-sync pytest market-viz/tests
```
