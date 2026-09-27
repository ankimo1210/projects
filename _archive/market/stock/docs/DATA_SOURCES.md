# Data Sources

stockkit が利用する全外部データソースの仕様・制限・利用箇所まとめ。

---

## サマリ

| ソース | 用途 | 認証 | 主な制限 |
|---|---|---|---|
| yfinance (Yahoo) | 価格データ、企業情報、財務 | 不要 | レート制限あり、銘柄により欠損 |
| FRED | マクロ経済指標 | 無料APIキー | 一部シリーズが更新停止（例: Japan CPI 2021-06） |
| e-Stat (総務省) | 日本CPI最新月次 | 無料APIキー | 約2ヶ月のラグ |
| J-Quants v2 | 日本株（公式データ） | 無料APIキー | 無料プランは直近約2年、5req/min |
| Stooq | TOPIX 指数 | captcha経由でAPIキー | 自動取得困難 |
| Wikipedia | インデックス構成銘柄 | 不要 | HTML構造変更リスク、更新遅延あり |
| Anthropic | AI チャット | 有料APIキー | 従量制（Sonnet 4.6 = $3/$15 per MTok） |

---

## 1. yfinance

### 概要
- パッケージ: `yfinance>=0.2.50`
- 実装: `src/stockkit/data/providers/yfinance_provider.py`

### 取れるもの

| データ | 関数 | カバレッジ |
|---|---|---|
| OHLCV 日次 | `get_prices(period="5y")` | 日米株 / ETF / 先物 / FX / 暗号資産 |
| 企業情報 | `get_info()` | 米株充実、日韓株は欠損あり |
| 財務諸表 | `get_financials()` | 年次4-5期、四半期5-6期（米株のみ充実） |

### 主要ティッカー形式

| カテゴリ | 例 |
|---|---|
| 米株 | `AAPL`, `NVDA`, `TSLA` |
| 日本株 | `7203.T`（4桁数字でも自動付与） |
| 韓国株 | `005930.KS` |
| 米国指数 | `^GSPC`, `^IXIC`, `^DJI`, `^RUT`, `^VIX`, `^NDX` |
| 日本指数 | `^N225`（TOPIX指数は不可、ETF `1306.T` で代替） |
| 海外指数 | `^STOXX50E`, `^GDAXI`, `^FTSE`, `^HSI`, `^KS11`, `^AXJO` |
| 米国先物 | `ES=F`, `NQ=F`, `YM=F`, `GC=F`, `SI=F`, `CL=F`, `BZ=F`, `HG=F`, `ZN=F` |
| FX | `JPY=X`, `EURUSD=X`, `GBPUSD=X`, `DX-Y.NYB` |
| 暗号資産 | `BTC-USD`, `ETH-USD` |
| 米国利回り | `^TNX` (10Y), `^IRX` (2Y), `^FVX` (5Y), `^TYX` (30Y) |

### 既知の制限

- **TOPIX 実指数**: `^TOPX`, `^TPX` 等すべて非対応 → Stooq または ETF (`1306.T`) で代替
- **JGB 先物・TOPIX 先物**: なし
- **韓国株の PER/PBR**: 欠損
- **yfinance 自動分割調整**: `auto_adjust=False` でも `Close` 列は遡及的に split-adjusted 済み（バスケット計算上は問題なし）

### レート制限対策
- `fast_info` は `info` より高速かつ crumb 不要
- ThreadPoolExecutor 並列度は 20 程度が安全（それ以上で 401 多発）

---

## 2. FRED (Federal Reserve Economic Data)

### 概要
- パッケージ: `fredapi>=0.5`
- 実装: `src/stockkit/data/providers/fred_provider.py`
- ドキュメント: https://fred.stlouisfed.org/docs/api/fred/

### 主要シリーズ

| 名称 | series_id | 頻度 | 状態 |
|---|---|---|---|
| US CPI | `CPIAUCSL` | 月次 | ✅ |
| US Core PCE | `PCEPILFE` | 月次 | ✅ |
| US 失業率 | `UNRATE` | 月次 | ✅ |
| US 非農業部門雇用 (NFP) | `PAYEMS` | 月次 | ✅ |
| Fed Funds Rate | `FEDFUNDS` | 月次 | ✅ |
| US GDP | `GDP` | 四半期 | ✅ |
| US 10Y 利回り | `DGS10` | 日次 | ✅ |
| US 2Y 利回り | `DGS2` | 日次 | ✅ |
| 米国逆イールド (10Y-2Y) | `T10Y2Y` | 日次 | ✅ |
| WTI 原油 | `DCOILWTICO` | 日次 | ✅ |
| VIX | `VIXCLS` | 日次 | ✅ |
| 米国小売売上高 | `RSAFS` | 月次 | ✅ |
| 住宅着工件数 | `HOUST` | 月次 | ✅ |
| Michigan消費者信頼感 | `UMCSENT` | 月次 | ✅ |
| US M2 | `M2SL` | 月次 | ✅ |
| **JGB 10Y** | `IRLTLT01JPM156N` | 月次 | ✅ |
| **日本 失業率** | `LRUNTTTTJPM156S` | 月次 | ✅ |
| **日本 輸出 (USD, SA)** | `XTEXVA01JPM667S` | 月次 | ✅ |
| **日本 輸入 (USD, SA)** | `XTIMVA01JPM667S` | 月次 | ✅ |
| USD/JPY | `DEXJPUS` | 日次 | ✅ |
| EUR/USD | `DEXUSEU` | 日次 | ✅ |
| Japan CPI | `JPNCPIALLMINMEI` | 月次 | ⚠️ **2021-06 で更新停止** → e-Stat 使用 |
| Japan 鉱工業生産 | `JPNPROINDMISMEI` | 月次 | ⚠️ 2024-03 で停止 |
| Japan 政策金利 | `IRSTCB01JPM156N` | 月次 | ⚠️ 2023-12 で停止 |
| TED Spread | `TEDRATE` | — | ❌ 2022-01 廃止 |

### キャッシュ
- DuckDB `macro_series` テーブル `(series_id, date)` PK
- 日次シリーズは 1日 TTL、月次は 28日 TTL

---

## 3. e-Stat (日本 統計局)

### 概要
- ドキュメント: https://www.e-stat.go.jp/api/
- 実装: `src/stockkit/data/providers/estat_provider.py`
- API バージョン: v3.0

### 取れるもの

| データ | 関数 | 統計表ID |
|---|---|---|
| 日本 CPI 月次 (2020年基準=100) | `get_jp_cpi()` | `0003427113` |

カバレッジ: 1970年1月〜最新（**約2ヶ月ラグ**）

### 時刻コード形式
- 月次: `YYYY00MMHH` (例: `2026000303` = 2026年3月)
- 年度・年次データは混在するので正規表現で月次のみフィルタ

### キャッシュ
- 一度全期間取得（〜800件）して DuckDB `macro_series` テーブル `ESTAT:JP_CPI` に格納
- TTL 28日

---

## 4. J-Quants v2

### 概要
- ドキュメント: https://jpx.gitbook.io/j-quants-api/
- 実装: `src/stockkit/data/providers/jquants_provider.py`
- 認証: `x-api-key` ヘッダー

### 利用エンドポイント

| パス | 用途 | プラン |
|---|---|---|
| `/v2/equities/bars/daily` | 日本株 日次 OHLCV | 無料（直近約2年） |
| `/v2/equities/master` | 上場銘柄マスタ | 無料 |
| `/v2/fins/details` | 財務詳細 | **有料のみ** |

### 制限
- レート制限: 5 req/min
- 無料プランの株価レンジ: 登録から約2年（過ぎると 400 エラー）
- ページング: `pagination_key` 必要

### 自動ルーティング
日本株 (`*.T` または4桁) かつ `JQUANTS_API_KEY` 設定済みなら自動で J-Quants を優先。期限切れの場合は手動で `.env` から削除すれば yfinance にフォールバックする。

---

## 5. Stooq

### 概要
- 実装: `src/stockkit/data/providers/stooq_provider.py`
- ベース URL: `https://stooq.com/q/d/l/`
- 認証: API キー（無料、ただし captcha 必要）

### 取得方法
1. https://stooq.com/q/d/?s=^tpx&get_apikey にアクセス
2. captcha 解答
3. 結果 URL の `apikey=XXX` をコピー
4. `.env` の `STOOQ_API_KEY=XXX` に設定

### 取れるもの

| ティッカー | 用途 |
|---|---|
| `^tpx` | TOPIX 指数（yfinance では取れない） |
| `^spx`, `^dji`, `^nkx` | 各種指数（yfinance で取れるので非優先） |

### 制限
- API キーは captcha なので **完全自動化は不可**
- 一度取得すれば長期間有効

---

## 6. Wikipedia (HTML スクレイピング)

### 利用箇所

| URL | 用途 |
|---|---|
| https://ja.wikipedia.org/wiki/日経平均株価 | N225 構成銘柄 225社 |
| https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average | DJIA 30社 + 公式ウェイト |
| https://en.wikipedia.org/wiki/List_of_S%26P_500_companies | SP500 503社 |
| https://en.wikipedia.org/wiki/Nasdaq-100 | NDX100 101社 |

### 取得方法
- `requests` + `pandas.read_html` で複数テーブル抽出
- 結果は `_data/*.csv` にキャッシュ（次回以降は CSV から読込、`refresh=True` で再取得）

### 既知のリスク
- **HTML 構造変更**: Wikipedia の表構造が変わるとパース失敗
- **更新遅延**: 構成銘柄入替が反映されるまで数日〜数週間
- **誤り**: コミュニティ編集のため間違いの可能性
- **N225 PAF 情報**: Wikipedia には主要銘柄の PAF が散発的に記載されているのみで完全リストなし

---

## 7. Anthropic API (Claude)

### 概要
- パッケージ: `anthropic>=0.40`
- 実装: `app/api/claude_agent.py`
- モデル: `claude-sonnet-4-6`

### 用途
AI チャット (`/chat`) で:
1. ユーザーの自然言語要求を解釈
2. 利用可能ツール (`get_price_data`, `get_macro`, `get_jp_cpi`, `search_fred`, `execute_python`) を組み合わせて実行
3. 結果を整形して返答

### 課金
- Sonnet 4.6: 入力 $3 / 出力 $15 per million tokens
- 1チャット往復で概ね **$0.01〜0.05**
- **Claude Max プランとは別課金**（API は console.anthropic.com で別途クレジット購入）

### Tool Use ループ
- 最大 10 ラウンド (`_MAX_ROUNDS`)
- `tool_use` ブロックがなくなった or `end_turn` で終了
- システムプロンプトに主要ティッカー/シリーズ一覧を含めて Claude の選択精度を上げている

---

## データソース選択フロー

```
価格データ (OHLCV):
  symbol.upper() in {"^TPX"} & STOOQ key  → Stooq
  symbol が日本株 & JQUANTS key             → J-Quants
  それ以外                                  → yfinance

マクロデータ:
  Japan CPI                                → e-Stat
  その他のマクロ                            → FRED

構成銘柄:
  Nikkei 225                               → Wikipedia (ja)
  DJIA / SP500 / NDX100                    → Wikipedia (en)
```
