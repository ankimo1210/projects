# Health: Google Health API Migration — Revised Design

**Date:** 2026-07-20
**Status:** Revised after spec review; implementation pending
**Project:** `health/`（worktree: `/home/kazumasa/projects/.claude/worktrees/health-google`）
**Supersedes:** `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`

## Why

Googleは2026年9月にlegacy Fitbit Web APIを停止する。`health`は同APIとFitbit OAuthに依存しているため、Google Health API（`health.googleapis.com/v4`）とGoogle OAuth 2.0へ移行する。

このアプリは実認証情報で運用されておらず、移行対象の`health.duckdb`も存在しない。したがって、既存データのマイグレーションではなく、APIクライアント・保存契約・同期処理のコード移行として扱う。

## Goal

以下を満たすGoogle Health版の個人用ダッシュボードを完成させる。

- Google OAuth 2.0で本人だけが認可できる。
- 現行7ページがGoogle Health由来のデータで動く。
- 日次・睡眠・intradayデータをDuckDBに保存する。
- 再同期で上流の更新・削除を正しく反映する。
- レート制限、認証失効、部分同期から安全に再開できる。
- 実レスポンスや個人の健康データをgitへ追加しない。

## Authoritative API references

実装時は次の公式資料を契約の正とする。Google Health APIは発展中のため、着手時にも差分を再確認する。

- [Data types](https://developers.google.com/health/data-types)
- [About the Google Health API and legacy shutdown](https://developers.google.com/health/about)
- [`dailyRollUp`](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp)
- [`reconcile`](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile)
- [`list` filter syntax](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list)
- [DataPoint schemas](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints)
- [OAuth setup and token behavior](https://developers.google.com/health/setup)
- [Quotas and rate limits](https://developers.google.com/health/rate-limits)

## Decisions

| Topic | Decision |
|---|---|
| 移行方式 | `auth.py`、`client.py`、`endpoints.py`、`sync.py`をin-placeで置換する。provider抽象化やFitbitとの並行運用は行わない。 |
| 集約データ | 日次合計・平均は`dailyRollUp`を使う。これは全データソースをreconcileした結果を返す。 |
| 詳細・派生データ | `list`ではなく`reconcile`を使い、複数デバイス・複数ソースを1ストリームに統合する。現行DBの「1 metric・1 timestamp・1 value」と整合する。 |
| パーサー | 公式RESTスキーマを基に実装し、発明したfixtureでテストする。実データprobeは受入確認であり、実装開始の前提条件にはしない。 |
| 保存 | チャンク単位でraw JSON・typed rows・watermarkを同一トランザクションで置換する。upsertだけでは済ませない。 |
| OAuth | External / Testing / selfをtest userとする。必要な3 read-only scopeだけを要求する。verificationは行わない。 |
| refresh token | APIが返す`refresh_token_expires_in`を保存する。refreshレスポンスで`refresh_token`が省略された場合は既存値を保持する。 |
| quota | 公開値はper-user 300 requests/minute、標準5 QPS。ただし本アプリはunverified / Testingで運用するため、2.5 QPS/userの目安にも余裕を持たせて2 QPS以下へpaceする。1 runのhard capは200 HTTP requests。 |
| backfill | `HEALTH_BACKFILL_START`を優先し、未指定時は暦上の5年前。intradayは直近30日だけ取得する。 |

## Non-goals

- legacy Fitbit Web APIの継続サポート。
- 公開アプリ化、OAuth verification、third-party security review。
- webhookまたは自動定期同期。
- ECG、IRN、血糖、血圧、栄養、GPSなど新規画面の追加。
- 既存DuckDBデータの移行。実データがないことが前提。

## Architecture

```text
health/
├── .env.example
├── src/health/
│   ├── auth.py          # Google OAuth 2.0 + PKCE、token persistence
│   ├── client.py        # dailyRollUp / reconcile、paging、pace、API errors
│   ├── endpoints.py     # API契約、catalog、filter path、parsers
│   ├── store.py         # chunk replacement transaction、VARCHAR sleep id
│   ├── sync.py          # resumable chunking、hard request budget
│   └── inventory.py     # published / implemented / stored series inventory
├── app/
│   ├── common.py
│   ├── main.py
│   └── views/
├── scripts/
│   ├── probe_datatypes.py
│   └── seed_demo.py
└── tests/
    └── fixtures/        # official schemaを模した架空値だけ
```

## API request contracts

### `dailyRollUp`

リクエスト範囲はclosed-openであり、アプリ内部の`start` / `end`は両端包含とする。このため終了日は1日進めて送る。

```python
def civil_midnight(d: date) -> dict[str, object]:
    return {
        "date": {"year": d.year, "month": d.month, "day": d.day},
        "time": {},
    }

body = {
    "range": {
        "start": civil_midnight(start),
        "end": civil_midnight(end + timedelta(days=1)),
    },
    "windowSizeDays": 1,
}
```

`CivilDateTime`にはtimezoneやUTC offsetを含めない。旧案の`utcOffsetSeconds`は使用しない。

成功レスポンスは`rollupDataPoints[]`に日次windowを返す。各要素の`civilStartTime.date`を保存日とし、対象union field自体がないwindowはrowを書かない。値が明示的に0なら0として保存する。protobuf JSONでは空のrepeated fieldが省略され得るため、`rollupDataPoints`欠落は空配列として扱うが、配列以外なら`PayloadError`とする。

### `reconcile`

```text
GET /v4/users/me/dataTypes/{dataType}/dataPoints:reconcile
    ?filter={full_filter_expression}
    &pageSize={page_size}
    [&pageToken=...]
```

filterには裸の`date`や`sample_time`ではなく、データ型名を含む完全なsnake_case pathを使う。

```python
def closed_open_filter(path: str, start: date, end: date) -> str:
    stop = end + timedelta(days=1)
    return f'{path} >= "{start}" AND {path} < "{stop}"'
```

成功レスポンスは`dataPoints[]`と`nextPageToken`を返す。`dataPoints`欠落は空配列として扱うが、配列以外なら`PayloadError`とする。この設計で使用するpathはMetric catalogに固定する。

## Authentication

Authorization Code + PKCEを使用する。

| Item | Value |
|---|---|
| Authorize URL | `https://accounts.google.com/o/oauth2/v2/auth` |
| Token URL | `https://oauth2.googleapis.com/token` |
| Redirect URI | `http://localhost:8501/` |
| Access type | `offline` |
| Prompt | `consent`（新規接続・明示的再接続時のみ） |
| Additional parameter | `include_granted_scopes=true` |

要求scopeは次の3つだけとする。

```text
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.sleep.readonly
```

`profile.readonly`は呼び出すendpointがないため要求しない。

token保存は既存と同じく`data/tokens.json`をmode `0600`でatomic replaceする。保存フィールドは以下とする。

```text
access_token
refresh_token
expires_at
refresh_expires_at       # refresh_token_expires_inが返った場合だけ
scope
```

refreshレスポンスに`refresh_token`がなければ保存済みの値を維持する。`refresh_token_expires_in`がなければ既存の`refresh_expires_at`を維持し、どちらにもない場合はUIで残日数を推測しない。

OAuth callbackの`error` / `error_description`、state mismatch、pending file欠落、token endpointのエラー、network errorはすべて`AuthError`へ正規化する。callback queryは成功・失敗にかかわらず処理後にURLから削除する。

## Metric catalog

`Metric.name`はsync watermarkのキー、`series_names`はtyped tableへ書く系列である。1つのcatalog entryが複数系列を出力できる。

| `Metric.name` | Google dataType | Method | Chunk | Filter path | Series |
|---|---|---:|---:|---|---|
| `steps` | `steps` | dailyRollUp | 90 d | — | `steps` |
| `distance` | `distance` | dailyRollUp | 90 d | — | `distance_km` |
| `calories` | `total-calories` | dailyRollUp | 14 d | — | `calories` |
| `active_minutes` | `active-minutes` | dailyRollUp | 14 d | — | `minutes_lightly_active`, `minutes_fairly_active`, `minutes_very_active` |
| `weight` | `weight` | dailyRollUp | 90 d | — | `weight_kg` |
| `body_fat` | `body-fat` | dailyRollUp | 90 d | — | `fat_pct` |
| `resting_hr` | `daily-resting-heart-rate` | reconcile | 90 d | `daily_resting_heart_rate.date` | `resting_hr` |
| `hrv` | `daily-heart-rate-variability` | reconcile | 90 d | `daily_heart_rate_variability.date` | `hrv_rmssd`, `hrv_deep_rmssd` |
| `spo2` | `daily-oxygen-saturation` | reconcile | 90 d | `daily_oxygen_saturation.date` | `spo2_avg`, `spo2_lower_bound`, `spo2_upper_bound` |
| `temp_skin` | `daily-sleep-temperature-derivations` | reconcile | 90 d | `daily_sleep_temperature_derivations.date` | `temp_skin_relative` |
| `br` | `daily-respiratory-rate` | reconcile | 90 d | `daily_respiratory_rate.date` | `breathing_rate` |
| `sleep` | `sleep` | reconcile | 90 d | `sleep.interval.civil_end_time` | `sleep_minutes` + `sleep_sessions` |
| `intraday_hr` | `heart-rate` | reconcile | 1 d | `heart_rate.sample_time.civil_time` | `hr` |
| `intraday_steps` | `steps` | reconcile | 1 d | `steps.interval.civil_start_time` | `steps` (intraday) |

`full_history=False`はintraday 2件だけで、初回も直近30日とする。

### Typed parser mapping

- Steps: `steps.countSum`。
- Distance: `distance.millimetersSum / 1_000_000`でkmへ変換。
- Calories: `totalCalories.kcalSum`。
- Active minutes: `activeMinutes.activeMinutesRollupByActivityLevel[]`を`LIGHT`、`MODERATE`、`VIGOROUS`から既存3系列へ写す。欠けたactivity levelは0ではなく欠損扱いにする。
- Weight: `weight.weightGramsAvg / 1000`。
- Body fat: `bodyFat.bodyFatPercentageAvg`。
- Resting HR: `dailyRestingHeartRate.beatsPerMinute`。
- HRV: `averageHeartRateVariabilityMilliseconds`と`deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds`。
- SpO2: `averagePercentage`、`lowerBoundPercentage`、`upperBoundPercentage`。confidence boundsを旧Fitbitのmin/maxとして偽装しない。
- Skin temperature: `nightlyTemperatureCelsius - baselineTemperatureCelsius`。baseline欠落時は系列を書かない。`relativeNightlyStddev30dCelsius`は代用しない。
- Respiratory rate: `dailyRespiratoryRate.breathsPerMinute`。
- Intraday HR: `heartRate.sampleTime.civilTime`と`beatsPerMinute`。
- Intraday steps: `steps.interval.civilStartTime`と`count`。

### Sleep mapping

- Primary keyは`ReconciledDataPoint.dataPointName`全体を`VARCHAR`で保存する。
- `date`はwake dayである`interval.civilEndTime.date`。
- `start_ts` / `end_ts`はcivil timeをnaive local timestampとして保存する。civil time欠落時だけphysical RFC3339 timeとoffsetから復元する。
- `minutes_asleep`は`summary.minutesAsleep`。
- `minutes_deep` / `minutes_light` / `minutes_rem` / `minutes_wake`は`summary.stagesSummary[]`から得る。raw stage segmentの再集計は検算にだけ使う。
- `efficiency = round(minutesAsleep / minutesInSleepPeriod * 100)`。分母0または欠落時は0。
- 同じwake dayでは、`metadata.nap == false`の最長sessionをmainとする。全件napなら最長sessionをmainとする。
- Classic sleepでも`minutesAsleep`と`minutesAwake`は保存し、DEEP/LIGHT/REMは0とする。DEEP/LIGHT/REMがないことは同期全体のblockerにしない。UIは3系列がすべて0ならステージ未提供の旨を表示する。

## Store and replacement semantics

既存データがないため、新しいschemaを直接作る。

```sql
CREATE TABLE raw_json(
    metric VARCHAR,
    range_start DATE,
    range_end DATE,
    page_index INTEGER,
    fetched_at TIMESTAMP,
    payload JSON,
    PRIMARY KEY(metric, range_start, range_end, page_index)
);

CREATE TABLE sleep_sessions(
    provider_id VARCHAR PRIMARY KEY,
    date DATE,
    start_ts TIMESTAMP,
    end_ts TIMESTAMP,
    minutes_asleep INTEGER,
    minutes_deep INTEGER,
    minutes_light INTEGER,
    minutes_rem INTEGER,
    minutes_wake INTEGER,
    efficiency INTEGER,
    is_main BOOLEAN
);
```

`Store.replace_chunk(metric, start, end, payloads, rows)`は1 transactionで次を行う。

1. 同一`metric/start/end`の旧raw pagesを削除する。
2. 今回取得した全pagesを挿入する。
3. `Metric.series_names`に属し、対象日付範囲にあるdaily/intraday rowsを削除する。
4. sleep metricならwake dateが対象範囲のsleep sessionsを削除する。
5. 新しいtyped rowsを挿入する。
6. `sync_state` watermarkを更新する。
7. commitする。

取得、paging、parseの途中で失敗した場合は`replace_chunk`を呼ばない。これにより、古いページ、上流で削除されたデータ、partial pagesを残さない。

## Client and errors

```python
class ApiError(Exception):
    status_code: int
    code: int | None
    status: str | None
    message: str

class RateLimited(ApiError):
    retry_after_s: int

class RequestCapExceeded(Exception):
    pass
```

`status_code`にはHTTP statusを入れ、Google error JSONの`error.code`、`error.status`、`error.message`もそれぞれ保持する。動作は次の通り。

| Condition | Behavior |
|---|---|
| 401 | access tokenを1回refreshし、HTTP requestを1回だけ再送する |
| 再送後401 | `AuthError` |
| refreshの`invalid_grant` | `AuthError`。保存済みデータは維持する |
| 403 | messageを保持した`ApiError`。UIに表示する |
| 429 | `RateLimited`。`Retry-After`の秒数またはHTTP-dateを解釈し、欠落時60秒 |
| network error / malformed JSON | messageを保持した`ApiError` |
| hard request cap | `RequestCapExceeded`。未完了チャンクは保存しない |

クライアントはmonotonic clockとwait関数を注入可能にし、HTTP送信を2 QPS以下（連続送信間隔0.5秒以上）にpaceする。テストでは実sleepを行わない。

## Sync engine

- `HEALTH_BACKFILL_START`があればISO dateとして検証する。
- 未指定時は`today.replace(year=today.year - 5)`を使い、2月29日だけ2月28日に丸める。
- watermarkがあるmetricは`last_synced - 2 days`から再取得する。
- intradayの初回開始日は`today - 29 days`。
- request budgetはGoogle Health APIへの物理HTTP requestごとに消費する。401の元requestと再送、pagingを含み、OAuth token endpointへのrefresh requestは含めない。
- reconcile chunkは全pagesを一時的にメモリへ集め、parse完了後にtransactional replaceする。
- 429またはrequest capではrunを終了し、完了済みchunkだけを残す。
- progressにはmetric、range、HTTP request countを表示する。

`SyncReport`は次を持つ。

```text
progress
paused
resume_in_s
stopped_early
requests_made
```

`RateLimited`と`RequestCapExceeded`だけは上記の停止状態へ変換する。`AuthError`、`ApiError`、`PayloadError`は`SyncReport`へ文字列化せず呼び出し元へ伝播し、UIが型別に表示する。

## Inventory

`KNOWN_DATA_TYPES`は公式data types一覧から手動管理する。`CATALOG`はその部分集合であることをテストする。

inventory pageは以下を表示する。

- published data typeとimplemented / not implemented。
- method、scope、last synced、status。
- 各typed seriesのrow countとdate range。
- raw page count。

未実装data typeをAPI probeしない。不要なscopeやquotaを消費しないためである。

## Probe and manual acceptance

`scripts/probe_datatypes.py`は実装済みcatalogに対して狭い範囲を取得し、`health/data/probe/`へ保存する。ただし役割は次に限定する。

- OAuth・scope・filter pathが実環境で受け付けられることの確認。
- 本人のアカウントに各データ型が存在するかの確認。
- optional fieldとClassic/Stages sleepの実例確認。

空payloadでも失敗扱いにしない。全ページを保存し、metricごとにstatus、page count、row count、top-level keysをmanifestへ記録する。実レスポンスはgitignoredのままとし、test fixtureには架空値だけを手作業で転記する。

## UI changes

- Provider表記をFitbitからGoogle Healthへ変更する。
- OAuth denialとAPI errorをユーザー向けに表示する。
- refresh token残日数は`refresh_expires_at`がある場合だけ表示する。
- reconnectでtokensとpending stateを削除する。
- activity viewは既存の`minutes_very_active`を維持する。
- body viewは`spo2_min/max`を`spo2_lower_bound/upper_bound`へ変更し、「下限/上限」と表示する。
- Classic sleepではtotal sleepを表示し、ステージ構成に「詳細ステージなし」と表示する。
- sync viewはrequest capと429の再開時刻を表示する。

## Testing

live APIをunit testから呼ばない。必須テストは以下。

- OAuth URLのoffline、consent、PKCE、最小scope。
- refresh token省略時の保持と`refresh_token_expires_in`の保存。
- nested `CivilDateTime`とexclusive end。
- 全Metricの完全なfilter path。
- reconcile paging、2 QPS pacing、401 one-shot retry、403/429 error mapping。
- request hard capがpaging中にも効き、partial chunkを保存しないこと。
- 14 catalog entriesのparser fixtures。
- 省略された空のrepeated fieldをempty responseとして扱い、配列型の破損は`PayloadError`にすること。
- active minute 3強度、単位変換、SpO2 bounds、skin temperature差分。
- daily / intraday / sleepのlogical key重複を`PayloadError`にし、arbitrary overwriteしないこと。
- string sleep ID、Classic/Stages、main session選択、cross-midnight civil time。
- `replace_chunk`が古い余剰ページ・削除済みtyped rowを消すこと。
- transaction failureでraw、typed、watermarkがすべて旧状態に戻ること。
- resume、trailing refetch、calendar-aware five-year start。
- inventoryのimplemented flagとseries stats。

## Acceptance

1. plan記載のworktree用環境変数を付け、worktree rootで`uv run --no-sync pytest health/tests -q`がgreen。
2. worktree rootで`uv run --no-sync ruff check health/src health/app health/scripts health/tests`と対応する`ruff format --check`がgreen。
3. OAuth接続、probe、初回syncを本人アカウントで完了できる。
4. `daily_series`、`sleep_sessions`、`intraday`に実データが入る。
5. 7ページすべてが例外なく表示される。データがないmetricは明示的なempty stateになる。
6. 同じ期間を再同期しても件数が不自然に増えず、上流削除をlocalから除去できる。
7. 429、失効token、request capから再開できる。
8. `health/data/`、`.env`、token、probe outputがgit statusへ出ない。

## Remaining runtime uncertainties

実装を止める設計上のunknownはない。次は実アカウントでのみ確認できるが、いずれもempty stateまたはdegraded displayで処理する。

- 本人アカウントに各data typeが存在するか。
- sleepがClassicかStagesか。
- token endpointが`refresh_token_expires_in`を返すか。
- 実際のresponse latencyとbackfill所要時間。
