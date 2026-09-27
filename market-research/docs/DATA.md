# 価格取得と時点別保存

更新日: 2026-09-27。実装範囲と検証結果は [STATUS](STATUS.md)。

## WSLで実行する

WindowsのPowerShellからは、先に `wsl.exe -d Ubuntu` でWSLへ入ります。
以降は作業中のリポジトリのルートから実行してください。WindowsパスをLinuxコマンドに渡しません。
`uv sync --package market-research --group dev` の後、以下のCLIを利用できます。

```bash
uv run --no-sync market-research fetch-prices \
  --provider binance --market CRYPTO --symbol BTCUSDT --provider-symbol BTCUSDT \
  --currency USDT --timezone UTC --adjustment raw --start 2026-09-24 --end 2026-09-25
uv run --no-sync market-research snapshots --limit 10
```

`start` / `end` は両端を含むセッション日です。返された `snapshot_id` と
`observed_at` を、次のオフライン読取へ指定します。プレースホルダーは実際の出力へ置換します。

```bash
uv run --no-sync market-research prices \
  --snapshot-id '<snapshot_id>' --as-of '<observed_at: UTCオフセット付きISO日時>'
```

出力はJSONで、価格の品質、除外行と理由、入力の `raw_hash`、取得時刻を含みます。
`snapshots` はmanifestの一覧で、入力実体の全件検査ではありません。
`prices` は選んだsnapshotのSHA256を照合します。取得前の日時には、その取得で初めて知った価格を返しません。
当時の版を持たない過去の意思決定を、今日のダウンロードで再現したとは扱いません。

## 取得元

| provider | adjustment | 入力・制約 |
|---|---|---|
| yfinance | `raw` / `unknown` | `auto_adjust=False`。`Adj Close` は `unknown`。ライブラリから返った表を精度を落とさず保存する（HTTP応答そのものではない） |
| stooq | `unknown` | CSVの調整方式をrawと決めつけない。HTMLの検証画面は `provider_challenge` エラー |
| jquants | `raw` / `split` | V2日足。環境変数 `JQUANTS_API_KEY`。4桁指定に対する5桁コードも照合。配当込みとは扱わない |
| binance | `raw` | 公開Spot APIのUTC日足。`BTCUSDT`なら通貨は `USDT`。出来高の単位はbase asset |

取得元・銘柄記号・市場・通貨は呼出側が明示します。別providerへの自動代替はありません。
暗号資産はUTCの0時から翌日0時。FXは明示時間表があってもlive quoteとして未確定・warnを維持します。

仕様確認先: [yfinance history](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html)、
[J-Quants V2日足](https://jpx-jquants.com/ja/spec/eq-bars-daily)、
[Binance Spot市場データ](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)。

## 日米株の取引時間表

`--calendar /absolute/path/sessions.json` に次の形式を渡します。
これは形式例です。利用する全日付の休日・短縮日・DSTを確認した時間表を用意してください。
未登録日や市場不一致はエラーになり、通常取引日へ補完しません。

```json
{
  "market": "XTKS",
  "version": "verified-source-and-date",
  "sessions": [
    {"date": "2026-09-25", "open": "2026-09-25T09:00:00+09:00", "close": "2026-09-25T15:30:00+09:00"}
  ]
}
```

確認先は [JPX取引時間](https://www.jpx.co.jp/english/equities/trading/domestic/01.html)、
[NYSE休日・取引時間](https://www.nyse.com/trade/hours-calendars)。
スケジュールの版・ハッシュ・使用期間の内容をsnapshotの `key.request_json` に保存します。
自動カレンダー用の新規依存は確認待ちです。現状の株価取得にはファイル指定が必要です。

## 保存・失敗・再開

- 既定の保存先は `Path.home() / '.local/share/market-research'`。cwdから独立しています。
  変更する場合は `market-research --data-root /absolute/path ...` とサブコマンドの前に指定します。
- `research.duckdb` にmanifest・価格revision・マクロvintage、`raw/<hash先頭2文字>/<hash>` に入力を保存。
  rawが同じなら実体を共有し、異なる版は上書きしません。DBは単一writerを前提とします。
- 同じrevisionに違う内容が届いたら保存batch全体をrollbackします。既に書いたrawだけが残る場合が
  ありますが、完成manifestに結び付かず、問い合わせには使われません。自動削除は行いません。
- HTTPは最大3試行、各10秒timeout。429・5xx・networkを再試行し、認証エラーは即座に止めます。
  `Retry-After` が30秒を超える場合は早く再送せず失敗します。yfinanceは専用ライブラリの
  10秒timeout付き呼出を1回行い、共通HTTPの再試行は適用しません。
- 通常は失敗をエラーにします。`fetch-prices --allow-stale` を付けた場合だけ、同じ条件の
  完成snapshotを使い、`stale: true` と失敗理由を返します。保存済み価格の取得日時は更新しません。
- J-Quantsが途中で失敗した場合、取得済みページと次のcursorを未完成manifestに保持します。
  同じ引数に `--resume` を足すと続きから再開。未完成データは価格読取へ渡しません。
  完成後は古い未完成snapshotを再開対象にしません。cursor失効時は `--resume` なしで再取得します。
- 未確定足は取得時の状態を保持します。後日読んでも確定へ昇格しません。
  確定した値が必要なら再取得し、別revisionとして保存します。

入力raw・DB・credentialをGitへ追加しないでください。共有の定時処理や旧DBはこのCLIから変更しません。

## 今回の検証

81件のオフラインテストで、未確定足、取引時刻、認証・再試行、保存・rollback・破損、
改定前後、取得→再open→読取、明示stale fallback、ページ再開を確認しました。

2026-09-27のライブ確認（2026-09-24〜25の公開データ、Git外の一時保存先）:

| 取得元 | 結果 |
|---|---|
| Binance BTCUSDT | 2行取得・保存・再読込一致。実CLIのfetch/prices/snapshotsも成功 |
| yfinance BTC-USD | 2行取得・保存・再読込一致 |
| Stooq IBM | JavaScriptによるブラウザ検証HTMLが返り、CSV取得できず。回避せずエラーとして記録 |
| J-Quants | 合成V2応答で検証。ライブ認証・契約範囲の疎通は未検証 |

Binance入力SHA256: `a8c9098137659555289a1ffac9394c45193cf1e0924c4f23ef79a01b8b6808d2`。
ライブの入力実体はGitへ入れていません。取得元の将来の稼働や任意の銘柄・期間まで保証する結果ではありません。
