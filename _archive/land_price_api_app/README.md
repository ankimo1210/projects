# 地価公示 & 不動産取引 ローカルアプリ

> ⚠️ **ARCHIVED (2026-06-13)** — この Streamlit PoC は `_archive/` に退避済み（uv workspace 非メンバー）。
> データ取得基盤は `~/re_invest_os` の `packages/market-data`（import 名 `market_data`）へ移植され、
> ローカル DuckDB / parquet レイクは `~/re_invest_os/data/market/` へ移動済み。
> 本ディレクトリの `data/raw` `data/processed` シンボリックリンクは移動により dangling（参照先は移管済み）。
> 現役の運用・同期手順は re_invest_os の `docs/data/market-data.md` を参照。以降は履歴保存用。

国土交通省「不動産情報ライブラリ」API を使って、全国の地価公示・不動産取引価格データをローカルで取得・保存・分析・可視化するツールです。

**ローカル専用**: 外部公開・クラウドデプロイ不要。API は Python サーバー側から呼び出します。

---

## 機能概要

- 全国の公示地価データを API（XPT002）から XYZ タイル走査で取得
- 不動産取引価格データ（XIT001）を都道府県・年・四半期単位で取得
- e-Stat 住宅・土地統計調査から市区町村別賃貸相場データを取得
- DuckDB にローカル保存・差分更新対応
- 国土地理院 API を使った住所ジオコーディング（取引価格の座標付与）
- Streamlit Web アプリ（地図 / 検索 / 都市トレンド / ランキング / 取引価格 / 物件分析 / 管理）
- 物件 URL（楽待・健美家等）を貼り付けて即時投資分析（Ollama LLM で情報抽出 → 近傍地価比較 → シミュレーション）
- Jupyter Notebook 基盤（探索分析・不動産投資シミュレーター連携）

---

## API キーの設定

1. https://www.reinfolib.mlit.go.jp/ にアクセスしてアカウント登録・API キーを取得
2. `.env.example` を `.env` にコピーして編集:

```bash
cp .env.example .env
# .env を編集して各キーを設定
```

| キー | 用途 | 必須 |
|---|---|---|
| `REINFOLIB_API_KEY` | 地価公示・取引価格 API | ✅ 必須 |
| `ANTHROPIC_API_KEY` | 物件分析タブの AI 抽出（Anthropic Claude）| ⬜ 省略可 |
| `ESTAT_APP_ID` | e-Stat 賃貸相場データ同期 | ⬜ 省略可 |

> **注意**: `.env` は `.gitignore` に含まれています。API キーをコードやノートブックに埋め込まないでください。

---

## セットアップ

このアプリはワークスペース（`~/projects/`）の uv メンバーです。Python 依存はワークスペースルートで一括管理されます。

```bash
cd ~/projects && make install     # = uv sync --all-packages
# (requirements.txt は移行期の互換用に残置。新規セットアップでは pyproject.toml が正)
```

物件分析タブで Ollama LLM を使う場合は別途 [Ollama](https://ollama.ai/) をインストールし、`gemma3:12b` モデルを用意してください:

```bash
ollama pull gemma3:12b
```

---

## アプリ起動

```bash
# ローカル起動
./run_local.sh
```

ブラウザで http://localhost:8501 を開く。

初回は **Admin タブ → データ同期** からデータを取得してください。

停止:

```bash
./stop_local.sh
```

`Ctrl+C` で止めると Streamlit の `Clear caches?` プロンプトが出るため、通常は `./stop_local.sh` を使ってください。

---

## CLI での同期

### 地価公示 (XPT002)

```bash
# 都道府県別（推奨: まず 1 都道府県でテスト）
python sync_public_notice.py --year 2026 --z 13 --pref 13   # 東京都

# 全国同期（数時間かかります）
python sync_public_notice.py --year 2026 --z 13

# スモークテスト
python sync_public_notice.py --year 2026 --smoke-test

# 2025年データ（2026が未公開の場合）
python sync_public_notice.py --year 2025 --z 13 --pref 13
```

### 不動産取引価格 (XIT001)

```bash
# 都道府県 × 年（四半期は全4期取得）
python sync_trade_prices.py --pref 13 --year 2024   # 東京都 2024年

# 特定四半期のみ
python sync_trade_prices.py --pref 13 --year 2024 --quarter 1

# 上書き再取得
python sync_trade_prices.py --pref 47 --year 2023 --overwrite
```

### バックフィル・並列取得

```bash
# 主要都府県 × 直近3年を並列取得
python run_sync.py

# 過去データ一括取得（DB クリア → 再インポート）
python run_backfill.py --from 2010 --to 2026

# Parquet→DB インポートのみ（取得スキップ）
python run_backfill.py --skip-fetch
```

### 賃貸相場データ (e-Stat)

```bash
python sync_rent_market.py           # 2023年（最新）
python sync_rent_market.py --year 2018
```

### ジオコーディング（取引価格の座標付与）

```bash
python geocode_trade_prices.py --limit 1000 --sleep 0.3
```

---

## Notebook の使い方

```bash
jupyter lab
# または
jupyter notebook
```

| ノートブック | 内容 |
|---|---|
| `00_api_smoke_test.ipynb` | API 疎通確認・GeoJSON の確認 |
| `01_sync_and_normalize.ipynb` | 1 年分の同期・正規化・DB 保存 |
| `02_exploratory_analysis.ipynb` | 価格分布・都道府県別・地図表示 |
| `03_city_trend_analysis.ipynb` | 時系列・年比較・近傍比較 |

> ノートブックは必ず上から順に実行してください。作業ディレクトリをプロジェクトルート（`land_price_api_app/`）に設定する必要があります。

> データ配置の標準パスは `../_data/land_price/{raw,processed}` です。`config.py` は未移行環境に限り従来の `data/` をフォールバックとして使用します。

---

## 全国同期の考え方

- API は XYZ タイル形式（Web Mercator）
- z=13 で日本全国をカバーするタイル数: 約 4 万〜5 万タイル
- 大半は海や空（データなし）→ HTTP 200 + 空配列で返ってくる
- 取得済みタイルを `_data/land_price/raw/fetched_tiles_*.json` に記録 → 再実行時はスキップ
- `--overwrite` フラグで全タイルを再取得可能
- リクエスト間に 0.3 秒のスリープを入れて過剰連続実行を防止

```
z=13 の 1 タイル ≈ 4.8km × 4.8km
全国タイル数 ≈ 50,000
取得時間目安 ≈ 5〜8 時間（0.3s/タイル × 空タイルのスキップなし）
```

---

## ディレクトリ構成

```
land_price_api_app/
  app.py                   # Streamlit エントリポイント
  api_client.py            # API HTTP クライアント層
  tiles.py                 # XYZ タイル座標演算・走査
  normalize.py             # GeoJSON → DataFrame 変換
  db.py                    # DuckDB 保存・読込・集計
  analytics.py             # 分析関数群
  geocoder.py              # 国土地理院API 住所→座標変換
  property_scraper.py      # 物件ページ HTML 解析・LLM データ抽出
  geocode_trade_prices.py  # 取引価格 lat/lon 一括付与バッチ
  generate_site_schema.py  # サイト固有抽出スキーマ自動生成
  notebook_utils.py        # ノートブック用高レベル API
  config.py                # 設定・ロガー
  sync_public_notice.py    # 地価公示 全国同期 CLI
  sync_trade_prices.py     # 取引価格 同期 CLI
  sync_rent_market.py      # 賃貸相場 e-Stat 同期 CLI
  run_sync.py              # 主要都府県 並列同期
  run_backfill.py          # 過去データ一括バックフィル
  requirements.txt
  .env.example
  data/
    site_schemas/          # サイト別LLM抽出スキーマ（Markdown）
  ui/
    map_tab.py
    search_tab.py
    trend_tab.py
    ranking_tab.py
    trade_tab.py           # 取引価格タブ
    property_tab.py        # 物件分析タブ
    admin_tab.py
    styles.py              # ダークテーマ CSS
  notebooks/
    00_api_smoke_test.ipynb
    01_sync_and_normalize.ipynb
    02_exploratory_analysis.ipynb
    03_city_trend_analysis.ipynb

../_data/land_price/
  raw/                     # raw GeoJSON・取得済みタイル記録
  processed/               # Parquet・DuckDB
```

---

## ローカル DB の構造

**テーブル: `land_prices_public_notice`**

| カラム | 型 | 説明 |
|---|---|---|
| point_id | VARCHAR | 標準地番号（主キー相当） |
| year | INTEGER | 調査年 |
| price_yen_per_sqm | DOUBLE | 価格（円/m²） |
| last_year_price_yen_per_sqm | DOUBLE | 前年価格（円/m²） |
| yoy_change_pct | DOUBLE | 前年比（%） |
| prefecture_code | VARCHAR | 都道府県コード |
| city_code | VARCHAR | 市区町村コード |
| lon / lat | DOUBLE | 座標（経緯度） |
| raw_properties | VARCHAR | 元 JSON（全フィールド保存） |
| ... | | その他詳細フィールド |

**テーブル: `trade_prices`**

| カラム | 型 | 説明 |
|---|---|---|
| trade_id | VARCHAR | 取引ID（主キー相当） |
| year / quarter | INTEGER | 取引年・四半期 |
| trade_type | VARCHAR | 取引種別（宅地・中古マンション等） |
| prefecture_code / name | VARCHAR | 都道府県 |
| city_code / name | VARCHAR | 市区町村 |
| district_name | VARCHAR | 地区名 |
| trade_price_total | DOUBLE | 取引総額（円） |
| trade_price_per_sqm | DOUBLE | 坪単価換算（円/m²） |
| area_sqm | DOUBLE | 面積（m²） |
| build_year | INTEGER | 建築年 |
| building_structure | VARCHAR | 建物構造 |
| lon / lat | DOUBLE | 座標（ジオコーディング後） |
| raw_properties | VARCHAR | 元 JSON |

**テーブル: `rent_market`**

| カラム | 型 | 説明 |
|---|---|---|
| city_code | VARCHAR | 市区町村コード |
| survey_year | INTEGER | 統計調査年 |
| ownership_type | VARCHAR | 所有関係区分（total / public / private 等） |
| rent_per_sqm | DOUBLE | 延べ面積1m²当たり家賃（円） |

**ビュー**:
- `city_summary`: 市区町村別・年別・用途別集計（地価公示）
- `pref_summary`: 都道府県別・年別集計（地価公示）
- `trade_city_summary`: 市区町村別・年別・四半期別取引価格集計

---

## API 仕様の前提

- **XPT002**: 地価公示・地価調査 ポイントデータ（XYZ タイル形式）
  - `priceClassification=0`: 地価公示（国土交通省）
  - `priceClassification=1`: 地価調査（都道府県地価調査）
- **XIT001**: 不動産取引価格情報（都道府県・年・四半期単位）
- **XIT002**: 都道府県内市区町村一覧
- 認証: `Ocp-Apim-Subscription-Key` ヘッダー
- レート制限: 連続リクエスト時は適切な待機が必要
- データなしタイル: HTTP 200 + `features: []` で返ってくる
- **国土地理院 アドレス検索 API**: `https://msearch.gsi.go.jp/address-search/AddressSearch` — APIキー不要・無料
- **e-Stat API**: 住宅・土地統計調査（市区町村別家賃）— `ESTAT_APP_ID` 必要

---

## 既知の制約

- フィールドマッピング: API レスポンスのプロパティキー名が変わる可能性があります。`normalize.py` の `_FIELD_CANDIDATES` を更新してください
- 全国同期時間: z=13 で 5〜8 時間程度。途中でも取得済みタイルは記録されるため再開可能
- 取引価格の座標: XIT001 レスポンスに座標が含まれないため、ジオコーディングが必要です（Admin タブまたは `geocode_trade_prices.py` で実行）
- 物件分析タブ: Ollama が `127.0.0.1:11434` で動作している必要があります。`gemma3:12b` モデルを推奨

---

## 将来拡張案

```python
# config.py の DEFAULT_PRICE_CLASSIFICATION を 1 に変更
# → 地価調査データの取得に対応

# tiles.py に都市計画用途地域レイヤを追加
# → GeoJSON ポリゴンとの結合分析

# property_tab.py の Ollama を Anthropic Claude に差し替え
# → ANTHROPIC_API_KEY を設定すると利用可能（property_scraper.py 修正が必要）
```

---

## ライセンス

このツールは個人・社内利用を想定したローカル専用ツールです。
API データの利用は国土交通省の利用規約に従ってください。
停止:

```bash
./stop_local.sh
```

`Ctrl+C` で止めると Streamlit の `Clear caches?` プロンプトが出るため、通常は `./stop_local.sh` を使ってください。
