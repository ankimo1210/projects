# health — Google Health personal archive & dashboard

Google Health APIで取得できる本人データを原本のままローカルへ保存し、
Next.js + shadcn/ui + Rechartsで閲覧する個人向けポータルです。
認可・同期はPython CLI、画面は読み取り専用の静的サイトです。

## 保存と表示

- APIの応答本文をJSON解析前に保存します。SHA-256による重複排除とgzip圧縮は可逆です。
  未知フィールド・複数source・取得時点ごとの版・エラー応答も保持します。
- 公式資料を確認した62の取得経路をカタログ化しています。取得候補56、読み取り不可4、
  未確認2。追加scopeが未許可でも他の経路を続行します。
- APIが期間指定なしの要求に応答しても、全履歴が返る保証がなければ`unknown_history`です。
  成功・空・未試行・途中・権限不足・未対応・失敗を分け、成功した期間だけを記録します。
  Google Takeoutの作成・取得は自動化していません。**Google上の全データを保存済みとは表示しません。**
- 原本に30日・5年などの保存期限や削除処理はありません。日内データは全点を書き出し、
  画面を描く際だけ間引きます。ズーム時は選択日の元データから再描画します。
- 既存の17日次系列・睡眠session・日内心拍/歩数を表示し、新しい型は原本保存から始めます。
  typed系列の同期状態と原本の取得状態は別です。

根拠とAPI制約は[取得契約](docs/google-health-source-contracts.md)、
表示形式は[Webデータ契約](docs/web-data-contract.md)を参照してください。

## 初期設定と認可

Google CloudでGoogle Health APIを有効化し、Google Auth PlatformのTesting利用では
自分のGoogleアカウントをtest userへ追加します。Web application OAuth clientの
redirect URIは`http://localhost:8501/`です。

workspace rootで実行します。

```bash
cp health/.env.example health/.env
# .env の GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET を設定
uv sync --package health
uv run --no-sync health auth
```

CLIは取得カタログの読み取り専用scopeを要求し、ブラウザで同意後に戻ります。
8501番は認可中だけ待ち受けます。ポートが使用中なら既存プロセスを自動終了せずエラーを表示します。
ブラウザが開かない場合は`health auth --no-browser`で表示されるURLを手動で開いてください。
scope不足や認可期限切れの場合も`health auth`で再認可します。

## 同期・再開

```bash
uv run --no-sync health sync --max-requests 200
# 中断したページから再開。同じコマンドを繰り返せます。
# 期間を明示して集計・表示用履歴も遡る場合:
uv run --no-sync health sync --history-start 2020-01-01 --max-requests 500
# 保存済みの走査を先頭からやり直す場合（旧原本は保持）:
uv run --no-sync health sync --rescan --max-requests 200
```

1回のHTTP予算を原本取得と表示用同期で共有します。429・認可エラー・保存失敗では停止し、
403など型単位の失敗では他の型を続行します。自動retryや待機ループはありません。
`--history-start`は要求する期間の下限であり、アカウントの最古日を証明するものではありません。
省略時の表示用履歴は、保存済みの公式プロフィールの日付・確認範囲・観測した原本の日付・
既存ローカル履歴を参照します。下限不明なら直近表示を維持し、`projection_history`へ
`unknown_history`と記録します。既存の古い記録は削除しません。
終了時のJSONで件数・失敗・未完了の状態を確認できます。

既存DBを開く前に、checkpoint後のバックアップを作ります。バックアップが失敗した場合は
DBの更新を開始しません。同じDBを使う旧Streamlitや別CLIの書き込みは終了させてください。
既存の`raw_json`も原本アーカイブへ一度取り込みますが、解析済みJSONなので`legacy_json`と区別します。

別checkoutから使う場合は絶対パスを指定できます。

```bash
uv run --no-sync health --data-dir /absolute/private/health/data \
  --env-file /absolute/private/health/.env sync --max-requests 200
```

## ポータルの起動

```bash
uv run --no-sync health export-web --out-dir health/web/public/data
cd health/web
npm ci
npm run dev
# http://127.0.0.1:3000
```

概要・気づき・睡眠・活動・心臓・身体・データ棚卸しの7画面があります。
期間切り替え、日単位の詳細、全点からの拡大、CSV出力、原本取得状態を確認できます。

静的ビルドもローカルだけで配信できます。

```bash
# health/web で実行
npm run build
npm start
```

ビルド後の更新はworkspace rootから`health export-web --out-dir health/web/out/data`を実行します。
次のビルドで`out`は作り直されます。データは全ファイルの書き出し成功後に一括で新世代へ切り替わります。
詳しくは[Web README](web/README.md)を参照してください。

## ローカルファイル

| パス | 内容 |
|---|---|
| `health/data/health.duckdb` | typed系列、旧raw JSON、取得履歴、再開cursor |
| `health/data/archive/objects/` | 元の応答本文を可逆圧縮した不変オブジェクト |
| `health/data/backups/` | DBを開く前のバックアップ |
| `health/data/tokens.json` | OAuth token（0600） |
| `health/data/oauth_pending.json` | 認可中のstate/PKCE（0600） |
| `health/web/public/data/`, `health/web/out/data/` | ローカル画面用JSON（0600） |

これらと`.env`はgitignoredです。原本・tokenをWeb配信先へ書き出しません。
画面用JSON自体は健康データなので、配信先は127.0.0.1に限定します。

## Probe・架空データ・検証

```bash
uv run --no-sync python health/scripts/probe_datatypes.py --help
uv run --no-sync python health/scripts/seed_demo.py --db-path /tmp/health-demo.duckdb
uv run --no-sync python health/scripts/export_data.py \
  --db-path health/data/health.duckdb --out-dir /tmp/health-export --format parquet
uv run --no-sync pytest health/tests -q
uv run --no-sync ruff check health/src health/scripts health/tests
uv run --no-sync ruff format --check health/src health/scripts health/tests
```

UIの検証は`health/web`で`npm run typecheck && npm run lint && npm test && npm run build`。
自動テストはfake HTTPとfixtureのみを使い、実APIを呼びません。
