# メガテック・トラッカー

Mag7の株価、PER/PBR、決算予定と財務状況を比較する自己完結HTML。
既存のStreamlit 7画面と保存snapshot契約から独立した、現在時点のモニタリング用画面です。

## 起動

WSLのリポジトリルート `/home/kazumasa/projects` から実行します。
新しい本番依存やAPIキーは不要です。既存のuv環境のpandas/yfinanceを使います。

```bash
# 明示取得して起動（ブラウザで http://localhost:8767 を開く）
uv run --no-sync python market-research/scripts/megacap_tracker.py --refresh

# 保存データだけで起動。閲覧ではデータ取得しない
uv run --no-sync python market-research/scripts/megacap_tracker.py

# 取得・HTML保存だけで終了
uv run --no-sync python market-research/scripts/megacap_tracker.py --refresh --no-serve

# 保存済みデータから、通信なしで任意の場所へHTMLを書き出す
uv run --no-sync python market-research/scripts/megacap_tracker.py \
  --no-serve --export /tmp/megacap-tracker.html
```

既定の保存先は `_data/market-research/megacap-tracker/`。
`snapshot.json` と `index.html` を1セットだけ保存し、更新時に置換します。
`--data-root /absolute/path` と `--port 8768` で変更できます。
終了は起動した端末でCtrl+C。HTTPサーバーは127.0.0.1だけで待ち受けます。

Windowsから保存版を開くパス:
`\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\market-research\megacap-tracker\index.html`

## 操作と保存

- 対象はAAPL、MSFT、GOOGL、AMZN、META、NVDA、TSLA。銘柄カードまたは表の行で詳細を選択。
- 比較表の「バリュエーション」「財務状況」を切替。見出しで昇順/降順を変更。欠損は末尾。
- 検索と「ウォッチのみ」はカード、合計/中央値、比較表、比較グラフ、決算予定、CSVに共通適用。
- ☆でウォッチ登録。ウォッチとテーマはブラウザのlocalStorageへ保存。
- 日足は1M/3M/6M/1Y切替。ポインターまたは左右の矢印キーで価格確認。四半期棒グラフにもツールチップ。
- 「データ更新」で7社を明示取得。定期取得や外部通知は設定しません。
- 「HTML保存」は7社分のデータと現在の検索・選択・表示条件を同梱。保存版はサーバーも外部通信も不要です。保存版からのデータ更新にはローカルサーバーを起動します。
- CSVは表示対象と選択中の表の列を出力。金額は10億単位、率は%値。通貨、損益/CF/BSの期末、取得時刻、価格時点、取得状態も付与。
- テーマは共通 `docs/templates/claude-report/tokens.css` の全文をHTMLへ埋込み。外部フォント・JS・CSSを読み込まない構成。

## データと定義

取得元は[Yahoo Finance](https://finance.yahoo.com/)を[yfinance](https://ranaroussi.github.io/yfinance/reference/yfinance.financials.html)経由で取得。
各社の株価・指標・財務ページと公式IRへのリンクを画面内に表示します。
取得元の財務値を公式開示と独立照合したものではありません。確認が必要な値はIRの原本へ戻れます。

| 指標 | 定義・期間 |
|---|---|
| 株価・前日比 | `regularMarketPrice`、`regularMarketTime`、前営業日終値からの変化率。時間外価格は混ぜない |
| 日足 | 1年のClose、`auto_adjust=False`、配当調整なし。当日分は未確定の場合あり |
| PER (TTM) | 株価 / 提供元`trailingEps`。EPSが正の場合のみ |
| 予想PER | 株価 / 提供元`forwardEps`。対象期間・調整基準は提供元に従う |
| PBR | 株価 / 提供元`bookValue`。BPSが正の場合のみ |
| PSR | 時価総額 / 売上TTM |
| EV/EBITDA・ROE | 提供元の値。EBITDAが非正なら倍率を表示しない |
| 損益・CF TTM | 連続する直近4四半期。隣接期末の間隔60–120日を検査し、1期でも必要値が欠ければ空欄 |
| 設備投資・FCF | 設備投資の絶対額を支出とし、FCF = 営業CF − 設備投資。4期分を合計 |
| FCF利回り | FCF TTM / 時価総額 |
| 利益率 | 同期間の営業利益/純利益TTM / 売上TTM |
| 現預金等 | 最新BSの現金・現金同等物・短期投資 |
| ネットキャッシュ | 現預金等 − 有利子負債 |
| 自己資本比率・D/E | 株主資本 / 総資産、有利子負債 / 正の株主資本 |
| 決算予定 | 提供元calendarの日付または日付範囲。米国東部の暦日。確定日時ではなく、公式IRで要確認 |

株価と財務の通貨が不明または異なる場合、通貨をまたぐ倍率とFCF利回りは算出しません。
異なる決算年度を架空の共通四半期に揃えず、実際の期末を表示します。
TTM EPS/BPS等と財務表の更新タイミングは提供元の都合で異なる場合があります。
損益・CF TTMが不完全、BSの主要項目が欠損などの場合は「一部欠損」を表示します。
2026-10-27の実通信ではAMZNの2026-06期売上が欠損しており、売上TTM・PSR等を空欄にしました。

全取得失敗の銘柄は以前の値と元の取得時刻を保持し「旧データ」と表示。
価格時点、各社の取得時刻、全体の更新試行時刻は別々に保持します。
PITバックテストの入力や、取得時刻を市場のリアルタイム時刻と見なす用途には使いません。

## 検証

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  uv run --no-sync pytest market-research/tests -q

# 任意の描画・操作検証。起動中のlocalhost:8767にアクセスし、末尾で実データ更新も行う
# Playwrightは一時検証環境に入り、本番の依存宣言は変えない
uv run --no-project --with playwright python market-research/scripts/verify_megacap_browser.py
```

ブラウザ検証は既存のWSL Chromiumパスを使います。他環境では検証スクリプトの実行ファイル指定を合わせてください。
証拠は同じデータルートの `qa/` へ保存。通常の取得・閲覧にPlaywrightは不要です。
