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
- CSVは表示対象と選択中の表の列を出力。金額は10億単位、率は%値。通貨、指標ごとの基準期末（EPS・BPS等・損益TTM・CF TTM・BS）、予想EPSの対象年度、†/‡の判定、決算日時（ET）と推定/確定・状態、取得時刻、価格時点、取得状態も付与。
- テーマは共通 `docs/templates/claude-report/tokens.css` の全文をHTMLへ埋込み。外部フォント・JS・CSSを読み込まない構成。

## データと定義

取得元は[Yahoo Finance](https://finance.yahoo.com/)を[yfinance](https://ranaroussi.github.io/yfinance/reference/yfinance.financials.html)経由で取得。
各社の株価・指標・財務ページと公式IRへのリンクを画面内に表示します。
取得元の財務値を公式開示と独立照合したものではありません。確認が必要な値はIRの原本へ戻れます。

| 指標 | 定義・期間 |
|---|---|
| 株価・前日比 | `regularMarketPrice`、`regularMarketTime`、前営業日終値からの変化率。時間外価格は混ぜない |
| 日足 | 1年のClose、`auto_adjust=False`、配当調整なし。当日分は未確定の場合あり |
| PER (TTM) | 株価 / 提供元`trailingEps`。EPSが正の場合のみ。† 純利益TTM > 営業利益TTM（投資評価益など営業外損益でPERが低く見える）。§ `trailingEps`が報告済み四半期EPSの4期合計と一致しない |
| 予想PER | 株価 / 提供元`forwardEps`。対象会計年度を`earnings_estimate`の0y/+1yと`nextFiscalYearEnd`から判定して「FY年/月」で表示。1%以内なら一致、10%以内で他方より3倍以上近ければ「≈」付きで推定、それ以外は「年度不明」。各社の決算月が違うため対象期間はそろわない |
| PBR | 株価 / 提供元`bookValue`。BPSが正の場合のみ |
| PSR | 時価総額 / 売上TTM。‡ 時価総額 ÷ 株価の株数と、純利益TTM ÷ EPSの株数（同じ4四半期と確認できた場合）が5%超異なる |
| EV/EBITDA・ROE | 提供元の値。EBITDAが非正なら倍率を表示しない |
| 損益・CF TTM | 連続する直近の完全な4四半期（損益は売上・純利益・営業利益、CFは営業CF・設備投資がそろう期）。隣接期末の間隔60–120日を検査。提供元が新しい期を一部項目だけ（EPSのみ等）で載せている場合はその期を除いてTTMを作り、除いた期を「一部欠損」として表示 |
| 設備投資・FCF | 設備投資の絶対額を支出とし、FCF = 営業CF − 設備投資。4期分を合計 |
| FCF利回り | FCF TTM / 時価総額 |
| 利益率 | 同期間の営業利益/純利益TTM / 売上TTM |
| 現預金等 | 主要4項目（現預金等・Total Debt・株主資本・総資産）がそろう最新BSの現金・現金同等物・短期投資 |
| 借入金・リース | 提供元`Total Debt`。リース債務を含み、範囲は企業で異なる（2026-10-31時点でAMZNは2,099億ドル中908億ドルがリース、AAPLはリース行なし）。`Capital Lease Obligations`があれば「うちリース」を表示 |
| ネットキャッシュ | 現預金等 − 借入金・リース |
| 自己資本比率・D/E | 株主資本 / 総資産、借入金・リース / 正の株主資本 |
| 基準期末 | 指標ごとの元データの期末。EPS = PER（四半期EPSの4期合計が`trailingEps`と一致する期。照合できなければ提供元`mostRecentQuarter`）、BPS等 = PBR・EV/EBITDA・ROE（`mostRecentQuarter`。Appleなど月末でない期末は20日以内の財務表の期末に寄せる）、損益 = PSR・利益率、CF = FCF利回り、BS = 現預金等・D/E等。期末が異なれば比較表に並べて表示 |
| 決算予定 | 提供元`earningsTimestampStart/End`（次回）と`earningsTimestamp`（前回の発表が残っている場合）を米国東部時間に変換し、`isEarningsDateEstimate`で推定/確定を表示。寄り前/引け後を表示し、ちょうど何時ちょうどの値は区分用の仮置きとみなして時刻は出さない。確定日時は公式IRで要確認 |

株価と財務の通貨が不明または異なる場合、通貨をまたぐ倍率とFCF利回りは算出しません。
異なる決算年度を架空の共通四半期に揃えず、実際の期末を表示します。

決算予定に`ticker.calendar`の日付は使いません。yfinanceはこの日付を実行環境のタイムゾーン（日本時間）で変換するため、引け後の発表が1日遅れて出ます。2026-10-31の実通信では、AAPL 11-03（正しくは11-02）、NVDA 11-18（同11-17）、AMZN 10-30（同10-29）でした。
`earningsTimestamp`の時刻は区分を示す仮置きの値です。同日の実通信では7社すべてが20:00:00 UTCでした。米国の夏時間（EDT）では16:00ですが、標準時（EST、11月1日から）では15:00 ETになります。このため20:00 UTCは常に「引け後」と判定します。
MSFTは`earningsTimestamp`が直前の10-28の発表のまま、Start/Endだけ次回の推定日（2027-01-27）になっていました。そのため、次回と前回を分けて保持します。

画面は閲覧時の時計で鮮度を判定します。保存データの取得からの経過時間を表示し、24時間以上なら状態表示を警告色にします。
取得後に発表時刻を過ぎた銘柄は、カード・決算予定・通知に「発表済み・要更新」と表示し、表示中の株価・財務が発表前の値であることを示します。
取得前に発表済みで次回予定が未掲載の銘柄は「発表済み（取得前）」と表示します。
倍率比較のバーは、ゼロ起点の共通目盛りを中央値の3倍で打ち切ります。超過した銘柄は数値に≫を付け、バーに切れ目を入れます。

一部の取得（株価・指標、日足、損益、BS、CF）だけ失敗した場合は、その部分だけ前回の値を使います。前回の取得時刻を`section_fetched_at`とエラー文に残します。前回の値を使えるよう、提供元の株価・指標の必要項目を`provider_info`として保存します。
全取得失敗の銘柄は、以前の値と元の取得時刻を保持して「旧データ」と表示します。以前の品質メッセージも残します。
価格時点、各社の取得時刻、全体の更新試行時刻は別々に保持します。
PITバックテストの入力や、取得時刻を市場のリアルタイム時刻と見なす用途には使いません。

2026-10-31の実通信では、AMZNの2026-09・2026-06期の損益が希薄化EPSだけでした。このため損益TTMは2026-03期までの4四半期（売上7,428億ドル）とし、PER・PBRの基準（2026-06期）と分けて表示しました。
NVDAは`trailingEps` 7.58が四半期EPSの合計7.91と一致しないため、§を付けています。

## 検証

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  uv run --no-sync pytest market-research/tests -q

# 任意の描画・操作検証。起動中のlocalhost:8767にアクセスし、末尾で実データ更新も行う
# Playwrightは一時検証環境に入り、本番の依存宣言は変えない
uv run --no-project --with playwright python market-research/scripts/verify_megacap_browser.py
```

画面のDOMを使わない判定（鮮度・発表済み判定・バーの目盛り・基準期末のまとめ）は、HTML内の `tracker-logic` マーカーの間にあります。`tests/test_megacap_server.py` がnodeで実行して検査し、nodeがない環境ではskipします。
ブラウザ検証は既存のWSL Chromiumパスを使います。他環境では検証スクリプトの実行ファイル指定を合わせてください。
証拠は同じデータルートの `qa/` へ保存。通常の取得・閲覧にPlaywrightは不要です。
