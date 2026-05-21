# SETUP

stockkit の環境構築手順。所要時間: 10〜20分（API キー取得を含む）。

> 📦 stockkit は [projects monorepo](../README.md) の uv workspace メンバー。`.venv` はワークスペース全体で共有されます。

---

## 必要要件

- **Python 3.12+**
- **uv** （Astral 製パッケージマネージャ）— [インストール手順](https://docs.astral.sh/uv/getting-started/installation/)
- **WSL2 (Ubuntu)** または Linux / macOS （Windows ネイティブは未検証）
- インターネット接続

---

## 1. リポジトリ取得 & 依存関係

```bash
# ワークスペース全体をクローン
git clone https://github.com/ankimo1210/projects.git ~/projects
cd ~/projects

# ワークスペース全体を一括sync（推奨。stockkit含む全メンバーをインストール）
uv sync --all-packages
# または Makefile経由
make install

# stockkit の依存だけ更新したい場合（uv は単一の workspace .venv を共有するため、
# どこから実行しても workspace 全体が解決対象になる点に注意）
cd stock
uv sync --package stockkit
```

---

## 2. APIキー設定

`.env` ファイルを **`stock/` ディレクトリ直下**（ワークスペースルートではない）に作成し、以下のキーを設定する。**全て無料**で取得可能。

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-api03-...      # AI チャット用（最小 $5 のクレジット購入が必要）
FRED_API_KEY=...                          # マクロ経済指標
ESTAT_API_KEY=...                         # 日本 CPI
JQUANTS_API_KEY=...                       # 日本株（オプション、yfinanceでも代替可）
STOOQ_API_KEY=...                         # TOPIX 指数（オプション）
```

### 各キーの取得方法

#### ANTHROPIC_API_KEY（必須: AI チャット機能）

1. [console.anthropic.com](https://console.anthropic.com) でアカウント作成
2. **Billing** で最小 $5 のクレジット購入（Claude Max プランとは別課金）
3. **API Keys** → "Create Key" → コピー
4. 利用料金目安: Sonnet 4.6 入力 $3 / 出力 $15 per MTok。チャット1往復で $0.01〜0.05

#### FRED_API_KEY（必須: マクロ経済指標）

1. [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) でアカウント作成
2. "Request API Key" でキー発行（即時、無料）
3. 利用制限: なし（適度な利用なら）

#### ESTAT_API_KEY（推奨: 日本 CPI 最新月次）

1. [e-Stat](https://www.e-stat.go.jp/) で無料登録
2. マイページ → **API機能（アプリケーションID発行）** → 発行
3. 1アカウントで最大3つ発行可

#### JQUANTS_API_KEY（オプション）

1. [jpx-jquants.com](https://jpx-jquants.com/) で無料プラン登録
2. ダッシュボードからキー取得
3. 無料プランは株価約2年分。期限切れに注意（取得期限から2年）
4. **未設定でも yfinance で日本株は取れる**ので必須ではない

#### STOOQ_API_KEY（オプション: TOPIX 指数）

1. [stooq.com/q/d/?s=^tpx&get_apikey](https://stooq.com/q/d/?s=^tpx&get_apikey) で captcha 解答
2. 表示された URL に含まれる `apikey=XXX` をコピー
3. **TOPIX ETF (1306.T) で代用可能**なので必須ではない

---

## 3. 起動確認

### Dash ダッシュボード

```bash
cd ~/projects/stock
./start.sh
# または
uv run python app/app.py
```

ログに以下が出れば成功:
```
 * Serving Flask app 'api.server'
Dash is running on http://127.0.0.1:8050/
```

ブラウザで http://127.0.0.1:8050 → トップページが表示されれば OK。

### 各機能の動作確認

| URL | 確認内容 |
|---|---|
| `/ticker` で `AAPL` を入力 → "Load" | 米株データ取得（yfinance） |
| `/basket` → 「分析実行」 | Nikkei 225 構成銘柄取得 + バスケット計算 |
| `/us-basket` → DJIA 選択 → 「分析実行」 | 米株指数取得 |
| `/chat` で「1+1は？」 | AI チャット（要 ANTHROPIC_API_KEY） |

---

## 4. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `ModuleNotFoundError: stockkit` | ワークスペース sync 未実行 | ルートで `make install` (= `uv sync --all-packages`) |
| `/chat` で "credit balance is too low" | Anthropic クレジット未購入 | console.anthropic.com で課金 |
| `JQuantsError: subscription` | J-Quants 無料プラン期限切れ | `.env` の `JQUANTS_API_KEY` を削除すれば yfinance にフォールバック |
| `/basket` でデータ取得失敗 | yfinance のレート制限 | 数分待ってリトライ |
| ポート 8050/8051 が使用中 | 既存プロセス | `kill $(lsof -ti:8050,8051)` |
| AI チャットの応答が遅い | Claude のツール使用で複数往復 | 通常 10〜60 秒。タイムアウトは未設定 |

---

## 5. ディレクトリの意味

| ディレクトリ | 用途 | git管理 |
|---|---|---|
| `src/stockkit/` | コアライブラリ | ✅ |
| `app/` | Dash UI + AI API | ✅ |
| `notebooks/` | Jupyter ノート | ✅ |
| `docs/` | ドキュメント | ✅ |
| `_data/` | DuckDBキャッシュ + 構成銘柄CSV | ❌ (gitignore) |
| `.env` | API キー | ❌ (gitignore) |

`_data/` を削除すれば全キャッシュがクリアされ、次回起動時に再取得される。
