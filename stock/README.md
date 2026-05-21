# stockkit

個人投資分析ツールキット。yfinance / FRED / e-Stat / J-Quants / Stooq から金融データを取得し、Jupyter で探索したり Dash ダッシュボードで可視化したり、Claude API による自然言語分析を行うためのワークスペース。

```
日本株・米株の価格 / 財務 / マクロ経済指標 / インデックスバスケット / AI チャット
```

---

## 何ができるか

| 機能 | 内容 |
|---|---|
| **株価取得** | yfinance（日米株・ETF・先物・FX・暗号資産）+ J-Quants（日本株） |
| **マクロ指標** | FRED（米CPI・FF金利・JGB10Y・USDJPY等）+ e-Stat（日本CPI最新月次） |
| **インデックス分析** | Nikkei 225 / DJIA / S&P 500 / NASDAQ-100 のバスケット vs 指数 vs ETF 比較 |
| **ウェイト分析** | 構成銘柄の現在/期初ウェイト・5年間のウェイト推移 |
| **AI チャット** | 自然言語で「アドバンテストの株価チャートを表示して」→ Claude がコード生成・実行・グラフ返却 |
| **Dash ダッシュボード** | 8ページ（ホーム/個別銘柄/スクリーナー/ポートフォリオ/バックテスト/N225バスケット/米株バスケット/AIチャット）|

---

## クイックスタート

### 1. セットアップ

```bash
uv sync                  # 依存関係インストール
# .env に必要なAPIキーを記入（詳細は SETUP.md）
```

詳細は [SETUP.md](./SETUP.md) を参照。

### 2. Dash ダッシュボード起動

```bash
./start.sh
# または
uv run python app/app.py
```

→ http://127.0.0.1:8050 を開く

| URL | ページ |
|---|---|
| `/` | ホーム |
| `/ticker` | 個別銘柄チャート + 財務 |
| `/screener` | スクリーニング |
| `/portfolio` | ポートフォリオ分析 |
| `/backtest` | バックテスト |
| `/basket` | Nikkei 225 バスケット vs 指数 + ウェイト分析 |
| `/us-basket` | 米株3指数（DJIA/SP500/NDX100）バスケット |
| `/chat` | AI チャット（要 ANTHROPIC_API_KEY） |

### 3. Python から直接使う

```python
from stockkit.data import get_prices, get_macro, get_jp_cpi
from stockkit.analysis import technical, portfolio, backtest as bt

df = get_prices("7203", period="1y")          # 4桁は自動で .T 付与
df = get_prices("AAPL", period="2y")

cpi = get_macro("CPIAUCSL")                    # FRED 米CPI
jp = get_jp_cpi()                              # e-Stat 日本CPI 月次

# バックテスト
df = get_prices("SPY", period="5y")
res = bt.run(df, bt.signal_sma_cross(50, 200))
res.metrics            # CAGR / Sharpe / MaxDD など
```

### 4. Jupyter Notebook

```bash
uv run jupyter lab notebooks/
```

- `01_data_quickstart.ipynb`
- `02_technical_demo.ipynb`
- `03_fundamental_demo.ipynb`
- `04_portfolio_demo.ipynb`
- `05_screener_demo.ipynb`

---

## プロジェクト構成

```
stock/
├── src/stockkit/
│   ├── data/                # データ取得層
│   │   ├── providers/       # 各データソース実装
│   │   ├── cache.py         # DuckDB キャッシュ
│   │   ├── nikkei225.py     # N225 構成銘柄
│   │   └── us_indices.py    # DJIA/SP500/NDX100 構成銘柄
│   ├── analysis/            # 分析モジュール
│   │   ├── basket.py        # インデックスバスケット計算
│   │   ├── backtest.py
│   │   ├── fundamental.py
│   │   ├── screener.py
│   │   ├── technical.py
│   │   └── portfolio.py
│   └── viz/                 # 可視化ヘルパー
├── app/
│   ├── app.py               # Dash エントリポイント
│   ├── pages/               # 各ダッシュボードページ
│   └── api/                 # AI チャット用バックエンド (Flask, port 8051)
├── _data/                   # DuckDB + CSVキャッシュ (gitignore)
└── docs/                    # 詳細ドキュメント
```

---

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [SETUP.md](./SETUP.md) | 環境構築・APIキー取得手順 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | システム構成・データフロー |
| [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md) | 全データソースの仕様と制限 |
| [docs/METHODOLOGY.md](./docs/METHODOLOGY.md) | バスケット計算の前提と既知の誤差 |
| [docs/decisions/](./docs/decisions/) | 設計判断記録 (ADR) |
| [CHANGELOG.md](./CHANGELOG.md) | 変更履歴 |

---

## 技術スタック

- **Python 3.12** / **uv** （パッケージ管理）
- **Dash 2.18** + **dash-bootstrap-components** （UI）
- **Plotly 5.24** （可視化）
- **DuckDB 1.1** （ローカルキャッシュ）
- **yfinance / fredapi / requests** （データ取得）
- **anthropic** （AI チャット、Claude Sonnet 4.6）
- **Flask** （AI チャット用 API サーバー）

---

## 注意事項

- 本ツールは**個人の投資分析支援用**であり、投資判断・売買執行は使用者の責任
- yfinance や Wikipedia 由来のデータは**遅延・欠損・誤りの可能性**あり
- インデックスバスケット計算は**現在構成銘柄を過去全期間に適用**する近似（survivorship bias あり、詳細は [METHODOLOGY.md](./docs/METHODOLOGY.md)）
