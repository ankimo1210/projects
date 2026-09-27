# Architecture

stockkit の構成・データフロー・主要コンポーネント。

> 📦 stockkit は **uv workspace のメンバー**として `/home/kazumasa/projects/` 配下に存在します。`.venv` は workspace ルートで共有。stock 個別の `pyproject.toml` で依存を宣言し、`uv sync --all-packages` で他メンバー（gto/market-viz/nbody-gpu等）と同時に解決されます。

---

## 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                         ユーザー (ブラウザ)                       │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
            │  http://127.0.0.1:8050          │  内部HTTP
            │  (Dash UI)                      │  (チャット非同期)
            ▼                                 ▼
┌───────────────────────────┐    ┌──────────────────────────────┐
│   Dash アプリケーション     │    │  Flask API サーバー (8051)    │
│   app/app.py              │───▶│  app/api/server.py            │
│                           │    │                              │
│   pages/                  │    │  /api/chat   (ジョブ投入)     │
│   ├─ home.py              │    │  /api/status (ポーリング)     │
│   ├─ ticker.py            │    └─────────┬────────────────────┘
│   ├─ screener.py          │              │
│   ├─ portfolio.py         │              ▼
│   ├─ backtest.py          │    ┌──────────────────────────────┐
│   ├─ basket.py            │    │  バックグラウンドスレッド       │
│   ├─ us_basket.py         │    │  app/api/job_store.py         │
│   └─ chat.py ─────────────┼───▶│                              │
│                           │    │  ┌────────────────────────┐  │
└───────────┬───────────────┘    │  │ Claude Agent           │  │
            │                     │  │ app/api/claude_agent   │  │
            │                     │  │ (tool_use loop)        │  │
            │                     │  └────────┬───────────────┘  │
            │                     │           ▼                  │
            │                     │  ┌────────────────────────┐  │
            │                     │  │ Sandbox                │  │
            │                     │  │ app/api/sandbox.py     │  │
            │                     │  │ (Python exec)          │  │
            │                     │  └────────┬───────────────┘  │
            │                     └───────────┼──────────────────┘
            │                                 │
            ▼                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                  src/stockkit/ (コアライブラリ)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  data/                          analysis/        viz/             │
│  ├─ __init__.py                 ├─ basket       └─ charts         │
│  │   (get_prices,               ├─ backtest                       │
│  │    get_macro,                ├─ technical                      │
│  │    get_jp_cpi)               ├─ fundamental                    │
│  ├─ symbols.py                  ├─ portfolio                      │
│  ├─ cache.py                    └─ screener                       │
│  ├─ nikkei225.py                                                  │
│  ├─ us_indices.py                                                 │
│  └─ providers/                                                    │
│      ├─ yfinance_provider                                         │
│      ├─ jquants_provider                                          │
│      ├─ stooq_provider                                            │
│      ├─ fred_provider                                             │
│      └─ estat_provider                                            │
└────────────┬──────────────────────────────────────┬───────────────┘
             │                                      │
             ▼                                      ▼
┌─────────────────────────┐          ┌──────────────────────────────┐
│  DuckDB ローカルキャッシュ │          │  外部 API                     │
│  _data/cache.duckdb      │          │  ├─ yfinance (Yahoo)          │
│  ├─ prices テーブル       │          │  ├─ FRED API                  │
│  └─ macro_series テーブル │          │  ├─ e-Stat API                │
└─────────────────────────┘          │  ├─ J-Quants v2 API           │
                                      │  ├─ Stooq                     │
                                      │  ├─ Wikipedia (HTML scrape)   │
                                      │  └─ Anthropic API (Claude)    │
                                      └──────────────────────────────┘
```

---

## レイヤー責務

### 1. データ層 (`src/stockkit/data/`)

**目的**: 外部 API の差異を吸収し、統一インターフェースで価格・マクロデータを返す。

| モジュール | 責務 |
|---|---|
| `__init__.py` | `get_prices()`, `get_macro()`, `get_jp_cpi()` の公開API。ソース自動切替 |
| `symbols.py` | 4桁数字→`.T` 付与など銘柄正規化 |
| `cache.py` | DuckDB の prices / macro_series テーブル管理 |
| `nikkei225.py` | Wikipedia から N225 構成銘柄取得 + CSVキャッシュ |
| `us_indices.py` | Wikipedia から DJIA/SP500/NDX100 構成銘柄取得 + CSVキャッシュ |
| `providers/` | 各データソースの実装。プロバイダ追加はここに新規 .py を置く |

**ソース自動振り分け** (`_resolve_source`):
- 米株/ETF/先物/FX → yfinance
- 日本株 (4桁 or .T) → J-Quants（キーあり）→ なければ yfinance
- `^TPX` (TOPIX指数) → Stooq（キーあり）→ なければエラー

### 2. 分析層 (`src/stockkit/analysis/`)

**目的**: pandas DataFrame を入力として指標・統計を計算。データ取得は行わない。

| モジュール | 責務 |
|---|---|
| `basket.py` | インデックスバスケット計算（価格加重 / 時価加重） + 通貨換算 + TE |
| `backtest.py` | シグナルベースのバックテスト (long/flat) |
| `fundamental.py` | PER/ROE 等のファンダメンタル指標 |
| `screener.py` | 複数銘柄のスクリーニング |
| `technical.py` | RSI/MACD/SMA 等 |
| `portfolio.py` | リターン/シャープ/最大DD/相関 |

### 3. 可視化層 (`src/stockkit/viz/`)

`charts.py` — Plotly でローソク足 + 各種オーバーレイの汎用関数。

### 4. UI 層 (`app/`)

**`app/app.py`**: Dash エントリポイント。`use_pages=True` で `pages/` 配下を自動ロード、起動時に Flask API サーバー (port 8051) も別スレッドで立ち上げる。

**`app/pages/*.py`**: 各ページ。`dash.register_page()` でルーティング自動登録。

**`app/api/`**: AI チャット用バックエンド（後述）。

---

## AI チャットの内部フロー

```
User: "アドバンテストの株価を表示して"

(1) chat.py の送信コールバック
    → POST http://127.0.0.1:8051/api/chat
    {"conversation": [...], "message": "アドバンテスト..."}

(2) Flask api/server.py
    → job_store.submit() でバックグラウンドスレッド起動
    → 即座に {"job_id": "uuid"} を返す

(3) claude_agent.run() (バックグラウンドで実行)
    Loop (最大10ラウンド):
      ├─ Anthropic API 呼び出し (Claude Sonnet 4.6)
      │   tools = [get_price_data, get_macro, get_jp_cpi,
      │            search_fred, execute_python]
      ├─ 応答に tool_use があれば実行:
      │   - get_price_data → stockkit.data.get_prices()
      │   - execute_python → sandbox.run() で exec、出力 + Plotly fig をキャプチャ
      └─ end_turn なら終了

(4) Dash chat.py の dcc.Interval (1秒ごと)
    → GET /api/status/{job_id} でポーリング
    → status=="done" でジョブ結果を取得し UI に表示
```

### サンドボックスの仕様

- インプロセス `exec()` 実行（subprocess より高速、個人ツールで許容）
- タイムアウト: 60秒 (`threading.Timer`)
- グローバル: `pd`, `np`, `go`, `px`, `get_prices`, `get_macro`, `get_jp_cpi`
- stdout を `io.StringIO` でキャプチャ
- Plotly の `fig.show()` を monkey-patch してフィギュア JSON を収集
- データ取得は `use_cache=False` で実行（DuckDBの並行アクセス回避）

---

## キャッシュ戦略

| データ種別 | キャッシュ先 | TTL | 用途 |
|---|---|---|---|
| 価格データ (OHLCV) | DuckDB `prices` テーブル | なし（差分更新） | yfinance/J-Quants/Stooq 共通 |
| マクロ時系列 | DuckDB `macro_series` テーブル | 28日（月次）/ 1日（日次） | FRED, e-Stat |
| N225 構成銘柄 | `_data/nikkei225_constituents.csv` | なし（手動更新） | Wikipedia取得結果 |
| US 構成銘柄 | `_data/us_index_{name}.csv` | なし | Wikipedia取得結果 |
| 米株 Shares Outstanding | `_data/shares_{name}.csv` | 24時間 | yfinance fast_info |
| Anthropic API | なし | — | ステートレス |

DuckDB の `prices` テーブルは `(symbol, date)` 複合主キー。`INSERT OR REPLACE` で差分更新。

---

## なぜ Flask を別ポートにしたか

最初は Dash の `app.server` (Flask) に `/api/chat` をルーティングしようとしたが、Dash 2.x の `callback_context` ContextVar が干渉して 500 エラーになった。

対処: Flask を独立して port 8051 で起動。Dash 側は HTTP クライアントとして呼ぶ。

詳細は [`docs/decisions/002-flask-on-separate-port.md`](./decisions/002-flask-on-separate-port.md)。

---

## 拡張ポイント

| 追加したいもの | 触るファイル |
|---|---|
| 新しいデータソース | `src/stockkit/data/providers/xxx_provider.py` 新規 + `data/__init__.py` |
| 新しい分析機能 | `src/stockkit/analysis/xxx.py` 新規 |
| 新しい Dash ページ | `app/pages/xxx.py` 新規（自動でナビ登録される） |
| 新しい AI ツール | `app/api/tools.py` の `TOOL_DEFINITIONS` + `execute_tool` |
| 別のLLMに切替 | `app/api/claude_agent.py` を書き換え（ツール定義は流用可） |
