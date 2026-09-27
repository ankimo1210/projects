# Changelog

stockkit の主要変更履歴。新しいものが上。

形式: [Keep a Changelog](https://keepachangelog.com/) に準拠。

---

## [0.4.0] - 2026-05-19

### Added
- **米株インデックス バスケットページ** (`/us-basket`)
  - DJIA (価格加重 30銘柄) / S&P 500 (時価加重 503銘柄) / NASDAQ-100 (時価加重 101銘柄)
  - 構成銘柄を Wikipedia から自動取得・CSVキャッシュ
  - 公式指数・ETF・先物との累積リターン比較
  - Top 30 ウェイト横棒・Top 10 ウェイト推移・ソート可能テーブル
- **N225 バスケットページに JPY/USD 切替トグル**
  - yfinance `JPY=X` で日次FXレート取得し換算
- **バスケット計算の高速化**
  - shares outstanding を `fast_info` で取得（10倍速）
  - ThreadPoolExecutor 20並列化
  - CSV 24h TTL キャッシュ
  - SP500: 150秒 → 9秒（初回）→ 7秒（キャッシュ後）

### Documentation
- ARCHITECTURE.md / DATA_SOURCES.md / METHODOLOGY.md / ADR 4本を追加

---

## [0.3.0] - 2026-05-18

### Added
- **Nikkei 225 バスケットページ** (`/basket`)
  - Wikipedia から225銘柄を自動取得 (`src/stockkit/data/nikkei225.py`)
  - 価格加重 (PAF=1.0近似) でバスケットリターン計算
  - ^N225 / 1321.T / NKD=F との累積リターン比較・トラッキングエラー
  - 構成銘柄ウェイト Top 30・5年ウェイト推移

### Changed
- 既存基盤の保守: `src/stockkit/analysis/basket.py` を追加

---

## [0.2.0] - 2026-05-17

### Added
- **AI チャット機能** (`/chat`)
  - Claude Sonnet 4.6 + tool_use ループ
  - 5種ツール: `get_price_data`, `get_macro`, `get_jp_cpi`, `search_fred`, `execute_python`
  - インプロセス Python サンドボックス（60秒タイムアウト、Plotly figure 自動キャプチャ）
  - Flask API サーバー (port 8051) + バックグラウンドジョブキュー
- **e-Stat プロバイダ** (`src/stockkit/data/providers/estat_provider.py`)
  - 日本 CPI 月次（2020年基準=100、〜2026年3月）

### Changed
- 日本 CPI は FRED (`JPNCPIALLMINMEI`) が 2021-06 で更新停止のため e-Stat に置換

---

## [0.1.0] - 2026-05-12

### Added
- **FRED プロバイダ** (`src/stockkit/data/providers/fred_provider.py`)
  - 米CPI/PCE/雇用/金利/JGB10Y/輸出入/USDJPY 等
  - DuckDB `macro_series` テーブルにキャッシュ
- **Stooq プロバイダ** (`src/stockkit/data/providers/stooq_provider.py`)
  - TOPIX 指数 (`^tpx`) を取得（要 STOOQ_API_KEY）
- `get_macro()` 公開API追加

---

## [0.0.x] - 2026-05 以前

### 既存基盤
- yfinance ベースの価格・財務取得 (`get_prices`, `get_info`, `get_financials`)
- J-Quants v2 プロバイダ（日本株、APIキー設定時に自動優先）
- DuckDB ローカルキャッシュ（差分更新）
- Dash multi-page アプリ
  - `/ticker` 個別銘柄チャート + 財務
  - `/screener` PER/ROE/配当でスクリーニング
  - `/portfolio` ポートフォリオ分析
  - `/backtest` SMAクロス・MACD・RSI・Donchian バックテスト
- `stockkit.analysis.*` モジュール（technical, fundamental, screener, portfolio, backtest）
- `stockkit.viz.charts` Plotly 可視化ヘルパー
