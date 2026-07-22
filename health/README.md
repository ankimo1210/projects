# health — Google Health personal dashboard

Google Health APIの本人データをOAuth 2.0で取得し、DuckDBへ保存して
Streamlit + Plotlyで閲覧するローカル専用ダッシュボードです。

## Google Cloud / OAuthの初期設定

1. Google Cloud projectを作成し、**Google Health API**を有効化します。
2. Google Auth PlatformのAudienceを**External / Testing**にし、自分のGoogle
   アカウントをtest userへ追加します。
3. Data Accessへ次の3 scopeだけを追加します。
   - `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
   - `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
   - `https://www.googleapis.com/auth/googlehealth.sleep.readonly`
4. Web application OAuth clientを作り、Authorized redirect URIへ
   `http://localhost:8501/`を完全一致で登録します。
5. workspace rootで設定ファイルを作り、発行された値を記入します。

   ```bash
   cp health/.env.example health/.env
   ```

   ```dotenv
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   HEALTH_BACKFILL_START=2021-01-01  # 任意。省略時は暦上5年前
   ```

6. workspace rootで依存関係を同期します。

   ```bash
   uv sync --all-packages
   # healthだけなら: uv sync --package health
   ```

Testing modeのrefresh tokenは通常7日で失効します。ただしGoogleのtoken
responseが明示的なrefresh token expiryを返した場合だけ、UIに残日数を表示します。
7日を推測したカウントダウンは表示しません。

## 起動・接続・同期

workspace rootで起動します。

```bash
uv run --no-sync streamlit run health/app/main.py
```

最初の画面で「Google Health と接続する」を選び、Googleの同意画面から戻ったら、
「管理 > 同期」で同期します。1回の同期はHealth APIへの物理requestを最大200件に
制限します。上限で止まった場合は、もう一度押すと未完了chunkから再開します。
HTTP 429の場合は表示された時間を待って再開してください。完了したchunkだけが保存され、
途中pageやparser errorでは既存データとwatermarkを変更しません。

認可をやり直すときは同期画面の「Google Health を再接続」を押します。保存tokenと
未完了OAuth状態を破棄したうえで、明示的に再認可できます。

## Acceptance probe

本同期の前に、実装済み14 metricを狭い期間で独立に確認できます。

```bash
uv run --no-sync python health/scripts/probe_datatypes.py
```

rollupは7日、日次reconcileは30日、intradayは1日だけ取得します。結果は
`health/data/probe/<metric>/page-000.json`と`manifest.json`へ保存され、DuckDBには
書きません。403やempty metricがあっても他metricを続行し、認証失効だけは全体を
停止します。stdoutには件数とshapeだけを出します。

**probe JSONは実際のprivate health dataです。共有・commitしないでください。**
`health/data/`全体はgitignoredです。

## データファイル

- `health/data/health.duckdb`: raw JSON、日次系列、睡眠session、intraday、同期状態
- `health/data/tokens.json`: OAuth token（mode 600）
- `health/data/oauth_pending.json`: PKCE/stateの一時情報（mode 600、10分で失効）
- `health/data/probe/`: acceptance probeのprivate raw JSON

UI開発用の架空DBは任意pathへ生成できます。実データを誤って上書きしないよう、一時pathを
指定してください。

```bash
uv run --no-sync python health/scripts/seed_demo.py --db-path /tmp/health-demo.duckdb
```

## 自動テスト

live APIを呼ばず、fixtureとfake HTTPだけで検証します。

```bash
uv run --no-sync pytest health/tests -q
uv run --no-sync ruff check health/src health/app health/scripts health/tests
uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
```
