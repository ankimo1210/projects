# Health: Google Health API Migration — Design

**Date:** 2026-07-20
**Status:** Approved (design review passed; spec review pending)
**Project:** `/home/kazumasa/projects/health`
**Supersedes:** `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`

## Why

Google is turning down the legacy Fitbit Web API in September 2026 — roughly six
weeks from this date. The `health` app shipped against that API and will stop
receiving data at turndown. The replacement is the Google Health API
(`health.googleapis.com`), which uses Google OAuth 2.0, a different endpoint
schema, and a different response format.

The app has never been run against real credentials, so there is no stored
Fitbit data and no `health.duckdb` to migrate. This is a code migration only.

## Goal

Move `health` from the legacy Fitbit Web API to the Google Health API, keeping
the DuckDB store, the sync engine's resume semantics, and all seven Streamlit
pages working with the same metric names, so the dashboard behaves as designed
once the user completes Google Cloud setup.

## Decisions

| Topic | Decision |
|---|---|
| Approach | In-place replacement. Rewrite `auth.py`, `client.py`, `endpoints.py`; adapt `sync.py`; delete the Fitbit implementation. No provider-abstraction layer and no parallel package. |
| Data scope | Port the current catalog to its Google equivalents — 15 Fitbit entries collapse to 13, for the reasons given under Metric catalog. Data types with no legacy counterpart (ECG, IRN, glucose, blood pressure, nutrition, GPS) are listed but not fetched. |
| OAuth publishing status | Testing. All Google Health scopes are Restricted; the personal-use exception applies (owner is the sole user). Verification is not pursued. |
| Refresh-token lifetime | Testing mode expires refresh tokens after 7 days. Accepted; the UI surfaces remaining days and a reconnect action. |
| Parser development | Probe-first. Fetch and store one real response per data type, then write parsers against observed shapes. |
| Metric names | Unchanged from the Fitbit implementation wherever a counterpart exists, so `store.py` and `app/` need no changes. |

## Non-goals

- Provider abstraction or continued Fitbit support.
- Google OAuth verification / Production publishing status.
- New data types beyond the current catalog (ECG, IRN, glucose, blood pressure,
  nutrition, mindfulness, exercise GPS).
- Automatic scheduled sync.
- Migrating stored data (none exists).

## Architecture

```
health/
├── .env.example            # GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET /
│                           # HEALTH_BACKFILL_START   (replaces FITBIT_*)
├── src/health/
│   ├── auth.py             # REWRITE: GoogleHealthAuth (Google OAuth 2.0)
│   ├── client.py           # REWRITE: HealthClient (POST rollup + GET list/paging)
│   ├── endpoints.py        # REWRITE: dataType catalog, request builders, parsers
│   ├── sync.py             # ADAPT:   paging loop, request cap, no budget gate
│   ├── store.py            # UNCHANGED
│   └── inventory.py        # MINOR:   follow renamed catalog fields
├── scripts/
│   ├── probe_datatypes.py  # NEW: one request per data type, raw JSON to disk
│   └── seed_demo.py        # MINOR: minutes_very_active -> minutes_active
├── app/
│   ├── common.py           # MINOR: imports GoogleHealthAuth instead of FitbitAuth
│   ├── main.py             # MINOR: "Fitbit と接続" wording -> Google
│   ├── views/sync_view.py  # ADAPT: HealthClient, remaining-days + reconnect,
│   │                       #        wording, drop rate-limit-pause copy
│   ├── views/activity_view.py  # MINOR: minutes_very_active -> minutes_active
│   ├── views/inventory_view.py # MINOR: implemented / not-implemented listing
│   └── views/*             # UNCHANGED (overview, sleep, heart, body)
├── README.md / CLAUDE.md   # MINOR: Fitbit setup steps -> Google Cloud setup
└── tests/                  # REWRITE test_auth/test_client/test_endpoints/test_sync
```

`store.py` needs no change because `daily_series(metric, date, value)` is a long
format keyed only by metric name, and the views read it through
`store.daily_frame(["steps", "sleep_minutes", ...])`. Holding metric names
stable keeps the store and the four data-rendering views untouched.

The word "Fitbit" appears in 13 files. The four rendering views (overview, sleep,
heart, body) contain none of them, which is why they survive the migration
unedited; everything else in the list above is touched precisely because it names
the provider.

The Fitbit implementation is deleted rather than kept alongside; it is
recoverable via `git show main:health/src/health/<file>.py`.

## Authentication

Authorization Code + PKCE against Google's endpoints.

| | Fitbit (old) | Google (new) |
|---|---|---|
| Authorize | `www.fitbit.com/oauth2/authorize` | `accounts.google.com/o/oauth2/v2/auth` |
| Token | `api.fitbit.com/oauth2/token` | `oauth2.googleapis.com/token` |
| Access-token TTL | 8 h | 1 h |
| Refresh token | Rotates on every refresh | Does not rotate |

Two Google-specific authorization parameters are mandatory:

- `access_type=offline` — without it no refresh token is issued at all.
- `prompt=consent` — forces re-issue of a refresh token on repeat authorizations.

**Critical asymmetry.** Fitbit returned a new `refresh_token` on every refresh, so
the existing `_store_tokens` overwrites it unconditionally. Google omits
`refresh_token` from refresh responses. Carrying the old logic over would raise
`KeyError` or persist `None` and destroy the credential. The new implementation
must preserve the stored value:

```python
refresh = payload.get("refresh_token") or existing["refresh_token"]
```

A dedicated test covers this: after a refresh response containing no
`refresh_token`, the previously stored refresh token is still on disk.

Token persistence keeps the current mechanism — `data/tokens.json`, written to a
temp file, `chmod 0o600`, then `os.replace`.

Scopes (all read-only):

```
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.sleep.readonly
https://www.googleapis.com/auth/googlehealth.profile.readonly
```

Redirect URI stays `http://localhost:8501/`. Google permits the `http` scheme for
loopback addresses, so this is expected to be accepted; it is confirmed during
Google Cloud setup.

**Seven-day expiry.** When the refresh token lapses, the token endpoint returns
`400 invalid_grant`. The client maps this to `AuthError`. The sync page shows the
token's issue date and remaining days, and on expiry renders "token expired —
reconnect" with a reconnect button. Stored data is unaffected, so every
dashboard page keeps rendering while authorization is lapsed.

## Metric catalog

Verified against the views: no page references heart-rate-zone metrics, so the
Google change from zone *minutes* to zone *calories* has no UI impact.

`Metric.name` is the catalog entry's identity and the `sync_state` primary key, so
it must be unique. The series names a metric writes into `daily_series` /
`intraday` are a separate thing, and two catalog entries may legitimately emit the
same series name into different tables (daily `steps` vs intraday `steps`).

| Catalog entry (`Metric.name`) | Google dataType | Method | Max range | Series written |
|---|---|---|---|---|
| `steps` | `steps` | dailyRollUp | 90 d | `steps` (daily) |
| `distance` | `distance` | dailyRollUp | 90 d | `distance_km` (daily) |
| `calories` | `total-calories` | dailyRollUp | 14 d | `calories` (daily) |
| `active_minutes` | `active-minutes` | dailyRollUp | 14 d | `minutes_active` (daily) |
| `weight` | `weight` | dailyRollUp | 90 d | `weight_kg` (daily) |
| `resting_hr` | `daily-resting-heart-rate` | list | 30 d window | `resting_hr` (daily) |
| `hrv` | `daily-heart-rate-variability` | list | 30 d window | `hrv_rmssd` (daily) |
| `spo2` | `daily-oxygen-saturation` | list | 30 d window | `spo2_avg` / `spo2_min` / `spo2_max` (daily) |
| `temp_skin` | `daily-sleep-temperature-derivations` | list | 30 d window | `temp_skin_relative` (daily) |
| `br` | `respiratory-rate-sleep-summary` | list | 30 d window | `breathing_rate` (daily) |
| `sleep` | `sleep` | list | 30 d window | `sleep_minutes` (daily) + `sleep_sessions` rows |
| `intraday_hr` | `heart-rate` | list | 1 d window | `hr` (intraday) |
| `intraday_steps` | `steps` | list | 1 d window | `steps` (intraday) |

`full_history` is `True` for every entry except `intraday_hr` and
`intraday_steps`, which backfill only the trailing 30 days.

Three deliberate departures from the Fitbit catalog:

1. **Active minutes.** Fitbit exposed `minutes_very_active`,
   `minutes_fairly_active`, and `minutes_lightly_active`; Google exposes a single
   `active-minutes` type. The catalog emits `minutes_active`, and
   `activity_view.py`'s single reference is updated. Any intensity breakdown the
   probe reveals is out of scope for this migration.
2. **Heart-rate zones.** `calories-in-heart-rate-zone` is not fetched. Nothing
   displays it, and its 14-day chunking would consume request budget for no
   visible result.
3. **Body fat.** No Google data type corresponds to Fitbit's `fat_pct`.
   `body_view.py` is left as-is; `daily_frame` fills missing metrics with NaN, so
   the series renders empty rather than erroring. If the probe reveals a
   corresponding type, it is added.

**Sleep stages are required.** `sleep_view.py`'s hypnogram and stacked-duration
charts depend on `minutes_deep`, `minutes_light`, `minutes_rem`, and
`minutes_wake`. The Google sleep data point carries a `stages` array of
segments typed `AWAKE` / `LIGHT` / `DEEP` / `REM` with start and end times,
rather than Fitbit's pre-summed minutes, so the parser sums segment durations per
stage. If the probe shows the account returns only `CLASSIC` sessions without
stage segments, that is a blocker: stop and raise it rather than substituting an
invented fallback.

Two sleep fields have no direct counterpart. `efficiency` is stored as `0`; no
view reads it. `is_main` is derived — the longest session whose `date` matches is
marked main, matching how `sleep_view` and `overview_view` use the flag.

The `Metric` dataclass drops Fitbit's `path` template and gains `data_type`,
`method`, and `page_size` to carry both request styles:

```python
@dataclass(frozen=True)
class Metric:
    name: str              # catalog entry id / sync_state key, e.g. "intraday_hr"
    data_type: str         # Google dataType id, e.g. "heart-rate"
    method: str            # "dailyRollUp" (POST) | "list" (GET)
    max_range_days: int    # 14 / 90 for rollup; window width for list
    page_size: int         # list only: 25 for sleep, 1000 otherwise
    scope: str
    full_history: bool
    parse: Callable[[Any], ParsedRows]
```

`ParsedRows` (daily / sleep / intraday) and `chunk_ranges()` carry over unchanged.
A helper converts a `datetime.date` to Google's civil-datetime object
(`{"year", "month", "day", "utcOffsetSeconds"}`).

## Client

```python
class HealthClient:
    def daily_rollup(self, data_type: str, start: date, end: date) -> dict:
        # POST /v4/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp
        # body: {"range": {"start": civil(start), "end": civil(end)},
        #        "windowSizeDays": 1}

    def iter_list(self, data_type: str, start: date, end: date,
                  page_size: int) -> Iterator[dict]:
        # GET /v4/users/me/dataTypes/{data_type}/dataPoints
        #     ?filter=<range expression>&pageSize={page_size}[&pageToken=...]
        # yields each page until nextPageToken is absent
```

`pageSize` is not uniform: the documented default is 1440 and the maximum 10000,
except for sleep and exercise where both default and maximum are 25. Passing 1000
for sleep would be rejected, so page size is a per-metric catalog value —
`1000` for every `list` metric, `25` for `sleep`.

The single automatic retry after `401` (refresh once, replay the request) is
retained.

**Rate limiting changes shape.** Fitbit reported remaining quota in
`Fitbit-Rate-Limit-Remaining`, which the current engine used as a pre-flight
budget gate. Google returns no equivalent header and publishes no concrete quota
figure. The budget gate is therefore removed: `client.remaining`,
`client.reset_s`, and `sync_all(min_budget=...)` are deleted. A `429` raises
`RateLimited(retry_after_s)` using `Retry-After` when present and 60 s otherwise,
and the engine stops cleanly. Resume safety continues to come from the
`sync_state` watermark, so no capability is lost.

## Sync engine

Shrinking the maximum range from 1095 days to 90/14 multiplies the request count
for a full backfill. Over five years:

| Catalog entries | Chunk width | Requests |
|---|---|---|
| `steps`, `distance`, `weight` | 90 d | 21 each |
| `calories`, `active_minutes` | 14 d | 131 each |
| `list`-based entries | 30 d window + paging | period- and page-dependent |

With the real quota unknown, firing several hundred requests in one click is
reckless. `SyncEngine` gains `max_requests_per_run` (default 200). On reaching
it, the run reports as stopped-early and the user presses sync again to
continue; the existing watermark makes that free.

**Backfill start.** Fitbit's `/1/user/-/profile.json` supplied `memberSince`.
No equally reliable Google equivalent is confirmed, and that profile call was
already a source of unguarded-exception defects in the previous review. It is
replaced by configuration: `HEALTH_BACKFILL_START` in `.env`, defaulting to five
years before today. This removes an API call and a failure path, and lets the
user set their true start date. The trailing-30-day rule for intraday metrics is
unchanged, as is the trailing-3-day refetch window for recent data.

## Probe-first development

Response field names for the `list` method vary per data type and are not fully
documented. Writing parsers from guesswork risks rewriting all of them at
acceptance. Implementation therefore splits at a checkpoint:

1. **Before the checkpoint** — `.env` handling, `auth.py`, `client.py`, the
   catalog skeleton (data types, methods, ranges) without parsers, and
   `scripts/probe_datatypes.py`.
2. **Checkpoint (user action, ~15 min)** — create the Google Cloud project,
   enable `health.googleapis.com`, configure the consent screen (External /
   Testing / self as test user), create Web-application OAuth credentials, fill
   `health/.env`, authorize in the app, and run the probe.
3. **After the checkpoint** — parsers written against the captured shapes, then
   sync-engine changes, UI adjustments, and demo-seed updates.

`probe_datatypes.py` requests a narrow window (7 days for daily types, 1 day for
intraday) for every catalog data type and writes each raw response to
`health/data/probe/<data_type>.json`, printing a one-line shape summary per type.
It never writes to DuckDB.

## Data inventory page

The earlier brainstorming answer implied live has-data detection for
not-yet-implemented data types. That is dropped: the app never requests scopes
for those types, so probing them returns `403`, and the quota cost is unjustified.

The page instead lists every Google Health data type with an
implemented / not-implemented marker, and shows row counts and date ranges from
DuckDB for implemented ones only. This still answers "what else is there?"
without spending requests.

The full data-type list lives in `endpoints.py` as a module-level constant
`KNOWN_DATA_TYPES: dict[str, str]` mapping each Google dataType id to a
human-readable label, covering both the catalog's types and the unimplemented
ones (ECG, IRN, blood glucose, blood pressure, nutrition, mindfulness, exercise
GPS, and the remaining published types). `inventory.build_inventory` joins it
against `CATALOG` to derive the implemented flag, so the two can never drift
apart by hand.

## Error handling

| Condition | Behavior |
|---|---|
| `401` on a data request | Refresh once, replay; a second `401` raises `AuthError` |
| `400 invalid_grant` on refresh | `AuthError` — UI shows expiry and a reconnect button |
| `403` | Surface the message verbatim; usually a missing scope or an API that is not enabled |
| `429` | `RateLimited(retry_after_s)`; the run stops cleanly and persists progress |
| `max_requests_per_run` reached | Run reports stopped-early with counts; not an error |
| Missing optional field in a payload | Metric is skipped for that day rather than defaulted to zero |

## Testing

Tests stay hand-rolled with dependency-injected HTTP fakes; no live API and no
new test dependency. Coverage targets the migration's risk points:

- Refresh response without `refresh_token` preserves the stored one.
- `access_type=offline` and `prompt=consent` appear in the authorization URL.
- `400 invalid_grant` maps to `AuthError`.
- Civil-datetime conversion, including `utcOffsetSeconds`.
- `iter_list` follows `nextPageToken` across pages and stops when it is absent.
- `daily_rollup` issues a POST whose body carries the expected range.
- `429` stops the sync run and leaves the watermark resumable.
- `max_requests_per_run` stops the run and reports counts.
- Per-metric parsers against fixtures.
- Sleep stage segments sum to per-stage minutes; `is_main` picks the longest
  session of the day.

**Fixtures contain no real health data.** Probe output lands in `health/data/`,
which is gitignored. Test fixtures reproduce the *structure* of observed
responses with invented values, and are committed. Real responses are never
committed.

## Acceptance

1. `uv run --no-sync pytest health/tests` green from the repo root.
2. First sync writes real rows into `daily_series`, `sleep_sessions`, and
   `intraday`.
3. All seven pages render the user's own data.
4. Seven-day expiry handling cannot be observed on day one, so it is covered by
   tests rather than manual acceptance.

## Open unknowns

These are resolved by the probe, not by guessing. Each has a defined fallback.

| Unknown | Impact | Resolution |
|---|---|---|
| `DataPoint` field names per data type | All `list` parsers | Probe |
| Sleep stage segments present for this account | Blocker for `sleep_view` | Probe; stop and consult if absent |
| A data type matching `fat_pct` | One empty series in `body_view` | Probe; tolerate absence |
| Actual quota values | Backfill duration | Observed at runtime via `429` |
| `http://localhost:8501/` accepted as redirect URI | Auth flow | Confirmed during Cloud setup |
| Intensity breakdown within `active-minutes` | Not used in v1 | Probe; future work |
