# Google Health API Migration — Corrected End-to-End Implementation Plan

> ファイル名の`plan-a`は既存リンク互換のため維持する。この文書は旧Plan A / Plan B分割を廃止し、公式仕様から実装、実アカウント受入までを一つにまとめた実行計画である。

**Goal:** legacy Fitbit Web API実装をGoogle Health APIへ完全移行し、OAuth、同期、typed parser、DuckDB置換、7ページ、probe、ドキュメントまで完成させる。

**Design:** `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md`

**Stack:** Python 3.12、requests、python-dotenv、DuckDB、Streamlit、Plotly、pytest。新規dependencyは追加しない。

## Execution rules

- Worktree: `/home/kazumasa/projects/.claude/worktrees/health-google`
- Branch: `claude/health-google-migration`
- 対象は`health/`と上記design/planだけ。ほかのprojectを変更しない。
- 実健康データ、`.env`、token、probe outputをcommitしない。
- unit testからlive APIを呼ばない。
- HTTP fakeは`health/tests/fakes.py`を拡張し、mocking dependencyを追加しない。
- test-firstで各taskの対象testを失敗させ、最小実装後に対象testをgreenにする。Task 1〜6の移行途中は対象testを必須とし、旧inventoryも更新するTask 7以降は対象testに加えて全suiteもgreenにする。
- `uv`は単一workspaceを管理するため、すべてworktree rootで実行し、`health/`内に`.venv`を作らない。
- worktreeからは共有環境とworktree側sourceを使うため、すべての`uv run`に次を付ける。`TMPDIR=/tmp`はpermission testをWindows mountのmode semanticsから隔離する。

```bash
TMPDIR=/tmp \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync ...
```

- production dependency、公開API、remote systemを変更しない。
- commitはtaskごとにbranch上で行う（user指示 2026-07-20）。pushはこの計画の完了条件に含めない。commit messageは英語`type(health): summary`形式とし、次のtrailerで終える。

```text
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
```

- API contractの正は`.superpowers/sdd/health-google-api-contracts.md`（discovery rev 20260715から抽出、全field名検証済み）。designとの矛盾があればcontracts fileが勝つ。

## Corrected contracts that must not regress

1. `CivilDateTime`は`{"date": {...}, "time": {...}}`であり、UTC offsetを含まない。
2. `dailyRollUp`の終了はexclusive。内部の包含終了日に1日加えて送る。
3. reconcile filterは`date`ではなく`daily_resting_heart_rate.date`等の完全なpath。
4. detailed dataには`list`ではなく`reconcile`を使い、複数sourceを1ストリームへ統合する。
5. sleep IDは`VARCHAR`。Googleのdata point IDを`BIGINT`へ変換しない。
6. chunk refetchはraw / typed / watermarkをtransactional replaceし、古い余剰pageと削除済みrowを残さない。
7. `body-fat`を実装し、active-minutesの強度別値を既存3系列へ保存する。
8. quotaは既知。unverified / Testingの2.5 QPS/user目安を下回る2 QPS paceと、200 HTTP requestのhard capを両方守る。
9. parserは公式schemaから実装する。probe待ちの`_parse_pending`は出荷しない。
10. 使用しない`profile.readonly` scopeを要求しない。

## Final file scope

| File | Change |
|---|---|
| `health/.env.example` | Google credentialsとbackfill設定へ更新 |
| `health/src/health/auth.py` | Google OAuth 2.0 + PKCEへrewrite |
| `health/src/health/client.py` | dailyRollUp / reconcile / errors / pacing / budgetへrewrite |
| `health/src/health/endpoints.py` | 14-entry catalog、request helpers、全parserへrewrite |
| `health/src/health/store.py` | raw schema、string sleep ID、atomic chunk replacement |
| `health/src/health/sync.py` | hard request budget、resumable replacement sync |
| `health/src/health/inventory.py` | implemented data typeとseries stats |
| `health/app/common.py` | auth class rename |
| `health/app/main.py` | callback/error/provider wording |
| `health/app/views/sync_view.py` | token status、errors、pause/resume |
| `health/app/views/body_view.py` | SpO2 confidence bound labels |
| `health/app/views/sleep_view.py` | Classic sleep degraded state |
| `health/app/views/inventory_view.py` | published/implemented/series表示 |
| `health/scripts/probe_datatypes.py` | create: acceptance probe + manifest |
| `health/scripts/seed_demo.py` | new schema/seriesへ更新 |
| `health/README.md`, `health/CLAUDE.md`, `health/pyproject.toml` | setup/architecture/provider更新 |
| `health/tests/**` | contract、parser、transaction、UI-adjacent test更新 |

---

## Task 0: Baseline and safety checks

**Files:** none

- [ ] `git branch --show-current`が`claude/health-google-migration`であることを確認する。
- [ ] `git status --short`を記録し、既存のuser changesを把握する。
- [ ] `test -x /home/kazumasa/projects/.venv/bin/python`で共有環境を確認する。存在しない場合はworktree内に`.venv`を作らず、workspace rootの環境準備についてuserへ確認する。
- [ ] baselineを実行する。

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests -q
```

- [ ] 現行provider参照の範囲を記録する。

```bash
rg -n "Fitbit|FITBIT_|FitbitAuth|FitbitClient" \
  health/src health/app health/scripts health/tests health/README.md health/CLAUDE.md \
  health/.env.example health/pyproject.toml
```

- [ ] `health/data/health.duckdb`が存在する場合は削除せず、作業を止めて内容の要否を確認する。設計上は実DBなしが前提である。

**Done when:** baseline結果と変更前provider参照が確認でき、既存データを誤って上書きしない状態になっている。

---

## Task 1: Google OAuth 2.0 authentication

**Files:**

- Rewrite: `health/src/health/auth.py`
- Rewrite: `health/tests/test_auth.py`
- Rewrite: `health/.env.example`

### Interface

```python
class AuthError(Exception): ...

class GoogleHealthAuth:
    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> "GoogleHealthAuth": ...
    def begin_auth(self) -> str: ...
    def complete_auth(self, code: str | None, state: str | None,
                      error: str | None = None,
                      error_description: str | None = None) -> None: ...
    def refresh(self) -> dict: ...
    def access_token(self) -> str: ...
    def load_tokens(self) -> dict | None: ...
    def forget_tokens(self) -> None: ...
    def refresh_expires_in_days(self) -> float | None: ...
```

### Tests first

- [ ] authorization URLが以下を含むtestを書く。
  - Google authorize URL
  - exact 3 scopes: activity, health metrics, sleep
  - `profile.readonly`なし
  - `access_type=offline`
  - `prompt=consent`
  - `include_granted_scopes=true`
  - PKCE S256、state、exact redirect URI
- [ ] pending fileに`state`、`verifier`、`created_at`がmode `0600`で保存されるtestを書く。
- [ ] 古いpending stateは再利用せず生成し直すtestを書く。TTLは10分とする。
- [ ] token exchangeがcredentialsをform bodyへ送り、Basic authを使わないtestを書く。
- [ ] callback state mismatch、pending file欠落、OAuth `error/error_description`を`AuthError`へするtestを書く。
- [ ] callback成功・denial・state mismatch後にpending fileが残らず、同じcallbackを再利用できないtestを書く。
- [ ] refreshレスポンスが`refresh_token`を省略しても既存tokenを保持するtestを書く。
- [ ] 新refresh tokenが返れば置換するtestを書く。
- [ ] `refresh_token_expires_in`を`refresh_expires_at`へ変換し、refresh時に既存expiryを保持・更新するtestを書く。
- [ ] `invalid_grant`とnetwork errorを`AuthError`へするtestを書く。
- [ ] access token expiryの60秒前にrefreshするtestを書く。
- [ ] `forget_tokens()`がtokenとpendingをidempotentに消すtestを書く。
- [ ] token fileがatomic writeかつmode `0600`であるtestを書く。

Run and confirm failure:

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_auth.py -q
```

### Implementation

- [ ] constantsをGoogle endpointと3 scopesへ置換する。
- [ ] `GoogleHealthAuth`へrenameする。
- [ ] `begin_auth()`で新規接続に必要なGoogle parametersを生成する。
- [ ] pending TTLを実装し、壊れたJSONも安全に捨てて再生成する。
- [ ] `complete_auth()`でtoken responseのGoogle error messageを保持する。
- [ ] callback処理後は成功・失敗にかかわらずpending stateを破棄し、再試行は`begin_auth()`からやり直す。
- [ ] `_store_tokens(payload, existing)`で以下を満たす。
  - access token expiryは`expires_in`から計算。
  - refresh token省略時は既存値を保持。
  - refresh expiryは`refresh_token_expires_in`優先、なければ既存値、どちらもなければ未設定。
- [ ] `.env.example`を次の3変数へ更新する。

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
HEALTH_BACKFILL_START=
```

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_auth.py -q
```

**Done when:** auth testsがgreenで、refresh tokenを省略レスポンスで失わず、未使用scopeを要求しない。

---

## Task 2: API contracts and 14-entry metric catalog

**Files:**

- Rewrite: `health/src/health/endpoints.py`
- Rewrite: `health/tests/test_endpoints.py`
- Create: `health/tests/fixtures/*.json`

### Interface

```python
DAILY_ROLLUP = "daily_rollup"
RECONCILE = "reconcile"

DailyRow = tuple[str, date, float]
IntradayRow = tuple[str, datetime, float]
SleepRow = dict[str, object]

class PayloadError(ValueError):
    metric: str
    detail: str

@dataclass(frozen=True)
class ParsedRows:
    daily: tuple[DailyRow, ...] = ()
    sleep: tuple[SleepRow, ...] = ()
    intraday: tuple[IntradayRow, ...] = ()

@dataclass(frozen=True)
class Metric:
    name: str
    data_type: str
    method: str
    max_range_days: int
    scope: str
    full_history: bool
    series_names: tuple[str, ...]
    parse_pages: Callable[[Sequence[dict]], ParsedRows]
    page_size: int = 1000
    filter_path: str | None = None

def civil_midnight(d: date) -> dict: ...
def daily_rollup_body(start: date, end: date) -> dict: ...
def closed_open_filter(path: str, start: date, end: date) -> str: ...
def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]: ...
def response_points(metric: Metric, page: dict) -> list[dict]: ...
```

### Contract tests first

- [ ] `civil_midnight()`がnested `date/time` shapeを返し、offset fieldを含まないtestを書く。
- [ ] `daily_rollup_body(7/1, 7/3)`のendが7/4 00:00であるtestを書く。
- [ ] 単日rangeのendが翌日になるtestを書く。
- [ ] `response_points()`がdaily rollupの`rollupDataPoints[]`、reconcileの`dataPoints[]`を読み分けるtestを書く。
- [ ] repeated field欠落を空配列、配列以外を`PayloadError`にするtestを書く。
- [ ] `closed_open_filter()`が完全なpathをそのまま使い、end + 1 dayにするtestを書く。
- [ ] `chunk_ranges()`のgap/overlapなし、single day、invalid max daysをtestする。
- [ ] catalog nameがuniqueで14件であるtestを書く。
- [ ] `KNOWN_DATA_TYPES`がcatalog全data typeを含むtestを書く。published total件数には固定しない。
- [ ] rollupの14/90-day limitsをtestする。
- [ ] reconcile entryのfilter pathをexact matchでtestする。

Expected filter paths:

```text
daily_resting_heart_rate.date
daily_heart_rate_variability.date
daily_oxygen_saturation.date
daily_sleep_temperature_derivations.date
daily_respiratory_rate.date
sleep.interval.civil_end_time
heart_rate.sample_time.civil_time
steps.interval.civil_start_time
```

- [ ] sleepのpage size 25、その他reconcileの1000をtestする。
- [ ] intraday 2件だけ`full_history=False`をtestする。
- [ ] active_minutesが既存3系列を宣言し、body_fatが`fat_pct`を宣言するtestを書く。

### Fixtures

- [ ] 公式schemaを模した架空値fixtureを作る。少なくとも以下を分離する。

```text
rollup_steps.json
rollup_distance.json
rollup_calories.json
rollup_active_minutes.json
rollup_weight.json
rollup_body_fat.json
daily_resting_hr.json
daily_hrv.json
daily_spo2.json
daily_skin_temperature.json
daily_respiratory_rate.json
sleep_stages.json
sleep_classic.json
intraday_hr.json
intraday_steps.json
```

- [ ] fixtureの値は明らかな架空値とし、probe outputをcopyしない。

### Implementation

- [ ] request / response helperとMetric dataclassを実装する。
- [ ] designの14-entry catalogをそのまま実装する。
- [ ] `KNOWN_DATA_TYPES`を公式data types一覧から作り、labelとscopeを保持する。
- [ ] parserは次Taskで完成させる。このTaskでは各metric専用のnamed parser callableを定義し、必要なら`NotImplementedError`を送出するstubとする。`_parse_pending`のような共有placeholderをcatalogへ入れず、このTaskのcontract testsからstubを呼ばない。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_endpoints.py -q
```

**Done when:** request shapeとcatalog contractがgreenで、旧案のflat civil time、bare filter、13-entry assumptionが消えている。

---

## Task 3: Google Health HTTP client, pacing, and request budget

**Files:**

- Rewrite: `health/src/health/client.py`
- Extend: `health/tests/fakes.py`
- Rewrite: `health/tests/test_client.py`

### Interface

```python
class ApiError(Exception):
    status_code: int
    code: int | None
    status: str | None
    message: str

class RateLimited(ApiError):
    retry_after_s: int

class RequestCapExceeded(Exception): ...

@dataclass
class RequestBudget:
    limit: int
    used: int = 0
    def consume(self) -> None: ...

class HealthClient:
    def daily_rollup(self, metric: Metric, start: date, end: date,
                     budget: RequestBudget) -> dict: ...
    def iter_reconciled(self, metric: Metric, start: date, end: date,
                        budget: RequestBudget) -> Iterator[dict]: ...
```

Constructorには`session`、`clock=time.monotonic`、`wait=time.sleep`、`min_interval_s=0.5`を注入できるようにする。

### Fakes first

- [ ] `FakeSession.get()`が`params`を記録するようにする。
- [ ] `FakeSession.post()`が`json`と`data`を両方記録するようにする。
- [ ] fake responseがGoogle error JSON、malformed JSON、headersを表現できるようにする。
- [ ] fake clock/wait helperを追加し、testで実sleepしない。

### Client tests first

- [ ] daily rollup URL、POST、nested body、Authorization headerをtestする。
- [ ] reconcile URLの`:reconcile` suffix、exact filter、page sizeをtestする。
- [ ] `nextPageToken`を全ページ追跡するtestを書く。
- [ ] sleep page size 25を送るtestを書く。
- [ ] request budgetが各物理HTTP送信で増えるtestを書く。
- [ ] paging途中でhard capに達したら`RequestCapExceeded`になるtestを書く。
- [ ] 401 refresh retryも2 requestsとして数えるtestを書く。
- [ ] 二度目の401が`AuthError`になるtestを書く。
- [ ] 403がGoogle `error.message`を保持する`ApiError`になるtestを書く。
- [ ] 403でHTTP statusとGoogle `error.code/error.status/error.message`を別々に保持するtestを書く。
- [ ] 429のnumeric `Retry-After`、HTTP-date、missing headerをtestする。
- [ ] network errorとmalformed success JSONを`ApiError`へするtestを書く。
- [ ] 連続request間隔が0.5秒以上になるtestを書く。
- [ ] 最初のrequestは不要にwaitしないtestを書く。

### Implementation

- [ ] `RequestBudget.consume()`を送信直前に呼び、limit到達後はHTTPを送らない。
- [ ] `_pace()`を全HTTP送信に適用する。OAuth token endpointはauth class側のため対象外。
- [ ] 401だけone-shot refresh/retryする。
- [ ] Google error JSONを`ApiError`へ正規化する。
- [ ] `Retry-After`をstdlib `email.utils.parsedate_to_datetime`でも解釈する。
- [ ] `iter_reconciled()`でpage token以外のquery parametersを不変に保つ。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_client.py -q
```

**Done when:** hard capがpaging中にも効き、2 QPS以下、reconcile paging、error mappingがunit testで保証される。

---

## Task 4: DuckDB schema and atomic chunk replacement

**Files:**

- Rewrite: `health/src/health/store.py`
- Rewrite: `health/tests/test_store.py`

### Schema changes

- [ ] `raw_json`を以下のlogical keyへ変更する。

```text
(metric, range_start, range_end, page_index)
```

- [ ] `sleep_sessions.log_id BIGINT`を`provider_id VARCHAR`へ置換する。
- [ ] `daily_series`、`intraday`、`sync_state`のkeyは維持する。

### Interface

```python
def replace_chunk(
    self,
    metric: Metric,
    start: date,
    end: date,
    payloads: Sequence[dict],
    rows: ParsedRows,
) -> None: ...

def raw_stats(self) -> pd.DataFrame: ...
def series_stats(self) -> pd.DataFrame: ...
def sleep_stats(self) -> pd.DataFrame: ...
def intraday_stats(self) -> pd.DataFrame: ...
```

既存`upsert_daily/sleep/intraday`はseed scriptと低レベルtest用に残してよいが、sync engineから直接呼ばない。

### Tests first

- [ ] new databaseのschemaでsleep IDにUUID-like stringを保存できるtestを書く。
- [ ] `replace_chunk`が全raw pagesを保存するtestを書く。
- [ ] 同じrangeを3 pagesから1 pageで再置換すると古いpage 1/2が消えるtestを書く。
- [ ] daily seriesの対象range内だけを置換し、range外を維持するtestを書く。
- [ ] active_minutesの3 seriesをまとめて置換するtestを書く。
- [ ] sleepのwake-date rangeを置換し、上流から消えたsessionがlocalから消えるtestを書く。
- [ ] intradayの対象日だけを置換するtestを書く。
- [ ] parser row insertを意図的に失敗させ、raw、typed、watermarkがすべてrollbackするtestを書く。
- [ ] 成功時だけwatermarkがendへ進むtestを書く。
- [ ] empty payloadで対象rangeの旧typed rowsを削除できるtestを書く。emptyは「削除を反映する」ための有効な置換である。

### Implementation

- [ ] `BEGIN` / `COMMIT` / `ROLLBACK`を明示する。
- [ ] raw delete/insert、typed delete/insert、watermark updateを同一transactionへ入れる。
- [ ] typed deleteは`metric.series_names`を使う。
- [ ] sleep deleteは`date BETWEEN start AND end`、intraday deleteは`CAST(ts AS DATE)`を使う。
- [ ] SQL placeholderを使い、series名や日付を文字列展開しない。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_store.py -q
```

**Done when:** stale page、upstream deletion、partial transactionの3リスクをtestで再現し、すべて防げる。

---

## Task 5: Typed parsers from official schemas

**Files:**

- Complete: `health/src/health/endpoints.py`
- Complete: `health/tests/test_endpoints.py`
- Use: `health/tests/fixtures/*.json`

### Parser behavior shared by all metrics

- [ ] inputはchunkの全response pagesとする。
- [ ] reconcile responseは`dataPoints[]`、identifierは`dataPointName`を読む。
- [ ] `rollupDataPoints` / `dataPoints`が欠落したpageは空配列として扱い、値が配列以外なら`PayloadError`にする。
- [ ] required field欠落は`PayloadError(metric, field)`としてchunk全体を失敗させる。
- [ ] optional measurement欠落はそのseries rowだけをskipする。
- [ ] numeric stringとJSON numberの両方を`float` / `int`へ安全に変換する。
- [ ] Google date objectをISO dateへ変換するhelperを作る。
- [ ] civil date/timeをlocal naive timestampへ変換するhelperを作る。
- [ ] zero valueを欠損と混同せず保存する。
- [ ] daily `(series, date)`、intraday `(series, ts)`、sleep `provider_id`の重複は`PayloadError`にし、後勝ちで上書きしない。

### Rollup parser tests

- [ ] `steps.countSum -> steps`。
- [ ] `distance.millimetersSum / 1_000_000 -> distance_km`。
- [ ] `totalCalories.kcalSum -> calories`。
- [ ] active levelsを次のように写す。

```text
LIGHT     -> minutes_lightly_active
MODERATE  -> minutes_fairly_active
VIGOROUS  -> minutes_very_active
```

- [ ] missing activity levelはrowなし、明示的な`activeMinutesSum="0"`は0 rowになるtestを書く。
- [ ] `weight.weightGramsAvg / 1000 -> weight_kg`。
- [ ] `bodyFat.bodyFatPercentageAvg -> fat_pct`。
- [ ] `civilStartTime.date`がdaily rowの日付になるtestを書く。

### Daily reconcile parser tests

- [ ] resting HRの`beatsPerMinute -> resting_hr`。
- [ ] HRVのaverage/deep RMSSDを2系列へ出す。
- [ ] SpO2のaverage/lower/upperを`spo2_avg/spo2_lower_bound/spo2_upper_bound`へ出す。
- [ ] skin temperatureはnightly-baselineを計算し、baselineなしはskipする。
- [ ] `relativeNightlyStddev30dCelsius`をrelative temperatureとして使わないtestを書く。
- [ ] daily respiratory rateを`breathing_rate`へ出す。

### Sleep parser tests

- [ ] UUID-like `dataPointName`をそのまま`provider_id`へ保存する。
- [ ] wake dayを`civilEndTime.date`から得る。
- [ ] `summary.minutesAsleep`と`stagesSummary[]`を使う。
- [ ] efficiencyを`minutesAsleep / minutesInSleepPeriod`から計算する。
- [ ] 同一wake dayでnon-nap最長を1件だけmainにする。
- [ ] 全件napなら最長をmainにする。
- [ ] Classic sleepはtotal/wakeを保存し、deep/light/remを0にする。
- [ ] physical timeとUTC offsetからのfallbackをtestする。
- [ ] cross-midnight sessionの日付と時刻をtestする。

### Intraday parser tests

- [ ] heart rateのcivil sample timeとBPMを出す。
- [ ] stepsのcivil interval startとcountを出す。
- [ ] 複数pagesを順序に依存せず統合する。
- [ ] duplicate timestampが来た場合は`PayloadError`にする。reconcile後も重複するならstoreへarbitrary overwriteしない。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_endpoints.py -q
```

**Done when:** 14 catalog entriesすべてがcommitted fixtureでparseされ、`_parse_pending`がcodebaseに存在しない。

---

## Task 6: Resumable sync engine with hard cap

**Files:**

- Rewrite: `health/src/health/sync.py`
- Rewrite: `health/tests/test_sync.py`

### Interface

```python
MAX_REQUESTS_PER_RUN = 200
TRAILING_REFETCH_DAYS = 2
INTRADAY_LOOKBACK_DAYS = 30

@dataclass
class SyncReport:
    progress: list[MetricProgress]
    paused: bool = False
    resume_in_s: int | None = None
    stopped_early: bool = False
    requests_made: int = 0

class SyncEngine:
    def sync_all(self, progress_cb=None) -> SyncReport: ...
```

### Tests first

- [ ] `HEALTH_BACKFILL_START` override、invalid date、future dateをtestする。
- [ ] defaultが暦上5年前で、leap dayを2/28へ丸めるtestを書く。
- [ ] rollup 14/90-day chunkingをtestする。
- [ ] reconcile pagingを全page取得してから1回だけ`replace_chunk`するtestを書く。
- [ ] parser failureでreplaceとwatermarkが呼ばれないtestを書く。
- [ ] 429で完了chunkだけ残し、`paused/resume_in_s`を返すtestを書く。
- [ ] hard capがrollup間とpaging途中の両方で効くtestを書く。
- [ ] cap途中のchunkは保存せず、watermarkを進めないtestを書く。
- [ ] second runが未完了chunkから再開するtestを書く。
- [ ] watermark済みmetricが末尾3日をrefetchするtestを書く。
- [ ] intraday初回が直近30日だけになるtestを書く。
- [ ] empty API responseもchunk成功としてreplacementとwatermarkを行うtestを書く。
- [ ] progress callbackがmetric、range、request countを報告するtestを書く。

### Implementation

- [ ] `backfill_start()`をcalendar-awareに実装する。
- [ ] `RequestBudget(MAX_REQUESTS_PER_RUN)`をrunごとに1つ作る。
- [ ] rollupは1 payload、reconcileは全pagesをlistへbufferする。
- [ ] 全pages取得後に1回parseし、1回`Store.replace_chunk()`する。
- [ ] `RateLimited`をcatchしてpaused reportを返す。
- [ ] `RequestCapExceeded`をcatchしてstopped-early reportを返す。
- [ ] `AuthError`、`ApiError`、`PayloadError`は握りつぶさずUIへ伝播する。
- [ ] engine内部にsleepやautomatic retryを入れない。paceと401 retryはclient責務。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_sync.py -q
```

**Done when:** resumability、atomic replacement、hard cap、429 pauseが統合testでgreen。

---

## Task 7: Inventory and all Streamlit pages

**Files:**

- Rewrite: `health/src/health/inventory.py`
- Rewrite: `health/tests/test_inventory.py`
- Modify: `health/app/common.py`
- Modify: `health/app/main.py`
- Rewrite: `health/app/views/sync_view.py`
- Modify: `health/app/views/body_view.py`
- Modify: `health/app/views/sleep_view.py`
- Modify: `health/app/views/inventory_view.py`
- Modify: `health/scripts/seed_demo.py`

### Inventory tests first

- [ ] `KNOWN_DATA_TYPES`全件がimplemented flag付きで表示されるtestを書く。
- [ ] catalog data typeだけimplementedになるtestを書く。
- [ ] 1 catalog entryが複数seriesを持つ場合に各series statsが表示されるtestを書く。
- [ ] daily、sleep、intraday、raw page count/date rangeをtestする。
- [ ] dataなしでも安定したcolumnsを返すtestを書く。

### App changes

- [ ] `FitbitAuth` / `FitbitClient` importをGoogle版へ変更する。
- [ ] callback queryの`code/state/error/error_description`を`complete_auth()`へ渡し、`AuthError`を説明付きで表示する。
- [ ] callback成功・失敗のどちらでもquery paramsをclearする。
- [ ] auth成功後もauthorization codeをURLから必ず除去する。
- [ ] provider wordingをGoogle Healthへ統一する。
- [ ] sync viewで以下をcatch/displayする。
  - `AuthError`: reconnect案内
  - `ApiError`: statusとGoogle message
  - `PayloadError`: metricとmissing field、データを壊さず停止した旨
- [ ] refresh expiryは値がある場合だけ残日数を表示する。Testing modeの7日を推測でカウントしない。
- [ ] request capと429のreportを表示する。
- [ ] reconnectでtokens/pendingを破棄し、明示的に再認可させる。
- [ ] activity viewは`minutes_very_active`のまま維持する。
- [ ] body viewを次へ変更する。

```text
spo2_min -> spo2_lower_bound（下限）
spo2_max -> spo2_upper_bound（上限）
```

- [ ] sleep viewでStagesが全て0のsessionには「詳細ステージなし」と表示し、total trendや就寝・起床は表示する。
- [ ] inventory viewをpublished data typesとstored seriesの2セクションにする。

### Seed demo

- [ ] sleep row keyを`provider_id` stringへ変更する。
- [ ] body fat、SpO2 lower/upper、3 active-minute seriesを生成する。
- [ ] seed dataにtokenは作成しない。

### Import validation

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync python -c "
import sys
sys.path[:0] = ['health/app', 'health/src']
import common, main
import views.activity_view, views.body_view, views.heart_view
import views.inventory_view, views.overview_view, views.sleep_view, views.sync_view
print('imports ok')"
```

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests/test_inventory.py -q
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests -q
```

**Done when:** 7ページがimportでき、metric semanticsがGoogle fieldsと一致し、empty/Classic sleepも例外にならない。

---

## Task 8: Acceptance probe and documentation

**Files:**

- Create: `health/scripts/probe_datatypes.py`
- Rewrite: `health/README.md`
- Update: `health/CLAUDE.md`
- Update: `health/pyproject.toml`
- Update: `health/src/health/__init__.py`
- Add tests for pure probe helpers if introduced

### Probe behavior

- [ ] catalogの各metricを独立に取得する。
- [ ] rollupは7日、daily reconcileは30日、intradayは1日の狭いrangeを使う。
- [ ] reconcileは最初のpageだけでなく全pageを保存する。
- [ ] outputは`health/data/probe/<metric>/page-000.json`形式とする。
- [ ] `manifest.json`へmetricごとに以下を保存する。

```text
status
data_type
method
start
end
page_count
data_point_count
top_level_keys
error_status
error_message
```

- [ ] 一つのmetricの403/empty/errorで残りを止めない。ただしauth失効は全体を止める。
- [ ] DuckDBへ書かない。
- [ ] 実payloadをstdoutへ表示しない。shape summaryだけ表示する。
- [ ] output fileはprivate health dataである旨をREADMEに明記する。

### README setup flow

- [ ] Google Cloud projectを作る。
- [ ] Google Health APIをenableする。
- [ ] OAuth audienceをExternal / Testing、自分をtest userにする。
- [ ] Data Accessでexact 3 scopesを追加する。
- [ ] Web application clientを作り、`http://localhost:8501/`をexact redirect URIとして登録する。
- [ ] `.env`を作る。
- [ ] `uv sync --package health`またはworkspace rootの`uv sync --all-packages`を案内する。
- [ ] Testing mode refresh tokenは通常7日で失効するが、UI countdownはtoken responseがexpiryを返した場合だけ表示する、と説明する。
- [ ] run、probe、sync、reconnect、data files、testsを記載する。

### Project docs

- [ ] `CLAUDE.md`をGoogle Health architectureへ更新する。
- [ ] chunk replacement、reconcile、hard cap、no live API testsをproject invariantsとして記載する。
- [ ] package descriptionとmodule docstringからPersonal Fitbit表記を除く。

### Validate stale references

```bash
rg -n "FITBIT_|FitbitAuth|FitbitClient|api.fitbit.com|www.fitbit.com/oauth" \
  health/src health/app health/scripts health/tests health/.env.example health/pyproject.toml
```

Expected: no matches.

README/CLAUDEではmigration historyとして「legacy Fitbit Web API」の記述を許可する。

### Validate

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests -q
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
uv run --no-sync ruff check health/src health/app health/scripts health/tests
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
```

**Done when:** probeがcredentialsなしでclean errorを返し、docsだけでCloud setupと実行手順が再現できる。

---

## Task 9: Final automated validation

- [ ] full suiteを再実行する。

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync pytest health/tests -q
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
uv run --no-sync ruff check health/src health/app health/scripts health/tests
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
```

- [ ] demo databaseをtemporary directoryで生成するか、既存scriptを一時data path注入可能にして検証する。実`health/data/`を勝手に上書きしない。
- [ ] app import checkを再実行する。
- [ ] `git diff --check`を実行する。
- [ ] `git diff --stat`と`git status --short`でhealth外の変更がないことを確認する。
- [ ] secretsらしき値がdiffにないことを確認する。

**Done when:** tests/lint/format/import/diff checksがすべてgreen。失敗が残る場合は完了としない。

---

## Manual checkpoint: Google Cloud and real-account acceptance

このcheckpointだけはuser actionが必要であり、自動実装を止めて引き渡す。

1. `health/README.md`のGoogle Cloud / OAuth setupを完了する。
2. `health/.env`へclient ID/secretを保存する。
3. appを起動する。

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync streamlit run health/app/main.py
```

4. Google Healthへ接続する。
5. acceptance probeを実行する。

```bash
TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src \
uv run --no-sync python health/scripts/probe_datatypes.py
```

6. manifestのstatusとempty metricsを確認する。
7. syncを実行し、必要ならrequest capごとに続行する。
8. 7ページを確認する。

### Manual acceptance checklist

- [ ] redirect URI mismatchがない。
- [ ] requested scopesが3つだけである。
- [ ] probeで不正なfilter/bodyによる400がない。
- [ ] 403がある場合、scope/API enablement messageがUIとmanifestに表示される。
- [ ] daily、sleep、intradayの少なくとも存在するデータ型がDBへ入る。
- [ ] active minutesが強度別に保存される。
- [ ] body fatがアカウントにあれば`fat_pct`へ入る。
- [ ] sleep IDがstringのまま保存される。
- [ ] Classic sleepでもページ全体は動く。
- [ ] 同じ3日を再同期してrow countが重複増加しない。
- [ ] request capまたは429後に続きから再開できる。
- [ ] probe/token/databaseがgit statusへ出ない。

## Completion criteria

以下をすべて満たした時だけmigration completeとする。

- Automated validationが全green。
- Manual acceptanceで本人のGoogle Healthデータを少なくとも1件同期できる。
- 7ページがrenderできる。
- stale page / deletion / transaction rollbackがtest済み。
- Fitbit endpoint、credential env var、runtime class参照がcodeから消えている。
- 実健康データとsecretがgit diffに含まれない。

## If manual acceptance finds a schema difference

Google Health APIは発展中のため、optional fieldの差分はあり得る。その場合は次の順で対処する。

1. 最新の公式REST referenceとrelease notesを再確認する。
2. probe outputをgitへ追加せず、構造だけを架空値fixtureへ再現する。
3. failing parser testを追加する。
4. 最小のparser/catalog修正を行う。
5. 対象test、full suite、probe、該当metric syncを再実行する。

実データに合わせてfilter path、単位、日付境界を推測で変更してはならない。
