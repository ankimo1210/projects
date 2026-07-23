# Health: Google Health Migration Completion + UI Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Execution outcome (2026-07-22):** COMPLETED and merged to main (aec630e9).
> During Task 0 the worktree was found to contain a prior session's uncommitted
> implementation of plan-a Tasks 6–8 (sync engine, inventory, app layer, probe,
> docs; 185 tests green). That work was adopted and committed as the baseline
> (a21dcf04), superseding this plan's Tasks 2, 3, 5 and most of 6/10/11/12.
> The remaining delta was then implemented as planned: Task 1 (sleep_minutes
> daily series), Task 4 (theme.py light/dark + cached loaders + period
> selector), Tasks 7–9 (view rewrites incl. nightly gantt, intensity stack,
> intraday steps viewer, deep-HRV series), sync/inventory UX polish, richer
> demo seed, onboarding copy. Final state: 187 tests, ruff clean, all 7 pages
> render via streamlit AppTest against seeded data.

> **Post-review corrections (2026-07-23):** The completed implementation keeps
> the existing `environ` keyword and the two DataFrame inventory builders
> (`build_inventory` / `build_series_inventory`) instead of the draft
> `env`/`Inventory` interfaces shown later in this historical plan. Follow-up
> fixes add injectable `max_requests`, distinguish `ok` from `in_progress`
> checkpoints so completed metrics always receive a trailing refetch, clear UI
> caches after partial-error outcomes, use calendar-based seven-day averages,
> migrate Streamlit sizing to `width="stretch"`, and preserve the seven-page
> AppTest smoke as a regression test.
> Follow-up validation: 196 tests passed, ruff and format checks were clean,
> imports succeeded, and seeded AppTest covered all seven pages plus the main
> app before and after connection without touching `health/data/`.

**Goal:** Finish the Fitbit→Google Health API v4 migration (sync engine, inventory, app layer) and overhaul the Streamlit UI (dark mode, shared period selector, richer views, sync UX).

**Architecture:** Core layers `auth/client/endpoints/store` are already migrated (commits 2ba05744..e8be4339). This plan rewrites `sync.py` + `inventory.py` against the new `HealthClient`/`RequestBudget`/`replace_chunk` interfaces, fixes the app layer imports and OAuth callback handling, then rebuilds the views on a new shared `app/theme.py` (dataviz palette, light+dark) and `app/common.py` (cached loaders, calendar-day period selector).

**Tech Stack:** Python 3.12, Streamlit 1.59 (`st.context.theme` available), Plotly 6, DuckDB, pandas, pytest, ruff (line-length 100).

**Spec:** `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md` (authoritative for API contracts). Prior plan `2026-07-20-health-google-migration-plan-a.md` Tasks 0–5 are DONE; its Tasks 6–9 are superseded by this plan.

## Global Constraints

- Worktree: `/home/kazumasa/projects/.claude/worktrees/health-google`, branch `claude/health-google-migration`. All commands run from the worktree root.
- Command prefix for every pytest/python run (worktree venv is shared with the main checkout, so PYTHONPATH must point at the worktree's src):
  `TMPDIR=/tmp UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-google/health/src uv run --no-sync ...`
  (abbreviated below as `ENVP uv run --no-sync ...`).
- ruff: line-length 100, target py312. Run `ruff check` + `ruff format --check` on `health/src health/app health/scripts health/tests` before each commit.
- No live API calls in tests. Fixtures contain invented values only.
- UI copy in Japanese; code/identifiers/commits in English.
- Never touch `health/data/`, `.env`, or tokens. `.env.example` is Read-denied by permission settings — attempt Write once in Task 12; if denied, document contents in README instead and note it.
- Palette (dataviz skill `references/palette.md`, July 2026 ordering) — exact hex values are in Task 4's `theme.py` listing; do not invent other colors.
- Commit after every task with the message given in the task.

---

### Task 0: Worktree sync and baseline

**Files:** none (git only)

- [ ] **Step 1: Fast-forward the branch to main**

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-google
git merge-base --is-ancestor claude/health-google-migration main && echo "branch is behind main: OK"
git merge --ff-only main
```

Expected: fast-forward to main's HEAD (30285c53 or later).

- [ ] **Step 2: Baseline test run**

```bash
ENVP uv run --no-sync pytest health/tests -q
```

Expected: `10 failed, 163 passed` — failures only in `test_sync.py` (8) and `test_inventory.py` (2).

---

### Task 1: Sleep parser emits `sleep_minutes` daily series

**Files:**
- Modify: `health/src/health/endpoints.py` (end of `parse_sleep_reconcile`, around line 492)
- Test: `health/tests/test_endpoints.py` (append)

**Interfaces:**
- Consumes: existing `parse_sleep_reconcile(pages) -> ParsedRows`.
- Produces: `ParsedRows.daily` now contains one `("sleep_minutes", wake_date, total_minutes_float)` row per wake date (sum of `minutes_asleep` over ALL sessions of that date, naps included). Spec catalog table: sleep → `sleep_minutes` + `sleep_sessions`. `Store.replace_chunk` already inserts `rows.daily` for full-history metrics, so no store change is needed.

- [ ] **Step 1: Write the failing tests** (append to `health/tests/test_endpoints.py`)

```python
def test_sleep_reconcile_emits_daily_sleep_minutes_per_wake_date():
    pages = [load_fixture("sleep_stages.json"), load_fixture("sleep_classic.json")]
    parsed = parse_sleep_reconcile(pages)
    assert parsed.daily == (
        ("sleep_minutes", date(2026, 7, 2), 420.0),
        ("sleep_minutes", date(2026, 7, 3), 390.0),
    )


def test_sleep_reconcile_daily_minutes_sum_all_sessions_of_a_date():
    page = load_fixture("sleep_stages.json")
    nap = json.loads(json.dumps(page))  # deep copy, same wake date as the main session
    point = nap["dataPoints"][0]
    point["dataPointName"] = "users/me/dataTypes/sleep/dataPoints/fake-nap-1"
    point["sleep"]["summary"]["minutesAsleep"] = "45"
    point["sleep"]["metadata"] = {"nap": True}
    parsed = parse_sleep_reconcile([page, nap])
    assert parsed.daily == (("sleep_minutes", date(2026, 7, 2), 465.0),)
```

- [ ] **Step 2: Run to verify they fail**

```bash
ENVP uv run --no-sync pytest health/tests/test_endpoints.py -q -k sleep_minutes
```

Expected: 2 FAIL (`parsed.daily == ()`).

- [ ] **Step 3: Implement** — in `parse_sleep_reconcile`, replace the final two lines

```python
    rows = tuple({k: e[k] for k in _SLEEP_ROW_KEYS} for e in entries)
    return ParsedRows(sleep=rows)
```

with

```python
    # Daily series alongside the sessions (catalog: sleep -> sleep_minutes +
    # sleep_sessions): total asleep minutes per wake date, naps included.
    daily = tuple(
        ("sleep_minutes", d, float(sum(e["minutes_asleep"] for e in group)))  # type: ignore[misc]
        for d, group in sorted(by_date.items())
    )
    rows = tuple({k: e[k] for k in _SLEEP_ROW_KEYS} for e in entries)
    return ParsedRows(daily=daily, sleep=rows)
```

- [ ] **Step 4: Run the full endpoints + store suites**

```bash
ENVP uv run --no-sync pytest health/tests/test_endpoints.py health/tests/test_store.py -q
```

Expected: all PASS (replace_chunk already handles `rows.daily` + `rows.sleep` together).

- [ ] **Step 5: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/src health/tests && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/src health/tests
git add health/src/health/endpoints.py health/tests/test_endpoints.py
git commit -m "feat(health): sleep parser emits sleep_minutes daily series"
```

---

### Task 2: Resumable sync engine on the Google client

**Files:**
- Rewrite: `health/src/health/sync.py`
- Rewrite: `health/tests/test_sync.py`

**Interfaces:**
- Consumes: `HealthClient.daily_rollup(metric, start, end, budget) -> dict`, `HealthClient.iter_reconciled(metric, start, end, budget) -> Iterator[dict]`, `RequestBudget(limit)` / `.used` / `.consume()`, `RateLimited.retry_after_s`, `RequestCapExceeded`, `Metric.method/full_history/max_range_days/parse_pages`, `chunk_ranges`, `Store.replace_chunk/get_sync_state`.
- Produces: `backfill_start(today: date, env: Mapping) -> date`; `MAX_REQUESTS_PER_RUN = 200`; `TRAILING_REFETCH_DAYS = 2`; `INTRADAY_LOOKBACK_DAYS = 30`; `MetricProgress(metric, fetched_ranges=0, done=False)`; `SyncReport(progress, paused=False, resume_in_s=None, stopped_early=False, requests_made=0)`; `SyncEngine(client, store, catalog=CATALOG, today=None, env=None, max_requests=MAX_REQUESTS_PER_RUN).sync_all(progress_cb=None) -> SyncReport` where `progress_cb(metric_name, "YYYY-MM-DD → YYYY-MM-DD (N req)")`. `AuthError`/`ApiError`/`PayloadError` propagate to the caller (sync view displays them by type).

- [ ] **Step 1: Rewrite `health/tests/test_sync.py`** with this exact content:

```python
"""SyncEngine tests: backfill windows, chunking, buffering, pause/cap/resume."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from health.client import RateLimited
from health.endpoints import CATALOG, Metric, PayloadError
from health.store import Store
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine, backfill_start

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 7, 22)


def by_name(name: str) -> Metric:
    return next(m for m in CATALOG if m.name == name)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def engine(client, store, names, today=TODAY, env=None, max_requests=MAX_REQUESTS_PER_RUN):
    return SyncEngine(client, store, catalog=[by_name(n) for n in names], today=today,
                      env=env if env is not None else {}, max_requests=max_requests)


def google_date(iso: str) -> dict:
    d = date.fromisoformat(iso)
    return {"year": d.year, "month": d.month, "day": d.day}


def rollup_page(day_values: dict[str, float]) -> dict:
    return {"rollupDataPoints": [
        {"civilStartTime": {"date": google_date(d), "time": {}},
         "steps": {"countSum": str(int(v))}}
        for d, v in day_values.items()]}


def hr_page(day_values: dict[str, float]) -> dict:
    return {"dataPoints": [
        {"dailyRestingHeartRate": {"date": google_date(d), "beatsPerMinute": str(v)}}
        for d, v in day_values.items()]}


class FakeHealthClient:
    """Catalog-shaped fake. `script[name]` is a list of per-chunk entries in
    call order: a list of page dicts (rollup serves entry[0]), or an Exception
    raised for that chunk. Unscripted chunks serve one empty page. Budget is
    consumed like the real client: one slot per rollup call, one per
    reconcile page (and one before a scripted failure)."""

    def __init__(self, script=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.calls = []

    def _next(self, metric):
        entries = self.script.get(metric.name)
        return entries.pop(0) if entries else [{}]

    def daily_rollup(self, metric, start, end, budget):
        self.calls.append((metric.name, start, end))
        budget.consume()
        entry = self._next(metric)
        if isinstance(entry, Exception):
            raise entry
        return entry[0]

    def iter_reconciled(self, metric, start, end, budget):
        self.calls.append((metric.name, start, end))
        entry = self._next(metric)
        if isinstance(entry, Exception):
            budget.consume()
            raise entry
        for page in entry:
            budget.consume()
            yield page


# -- backfill_start -----------------------------------------------------------


def test_backfill_start_env_override():
    assert backfill_start(TODAY, {"HEALTH_BACKFILL_START": "2024-01-15"}) == date(2024, 1, 15)


def test_backfill_start_invalid_env_raises():
    with pytest.raises(ValueError, match="ISO date"):
        backfill_start(TODAY, {"HEALTH_BACKFILL_START": "Jan 2024"})


def test_backfill_start_future_env_raises():
    with pytest.raises(ValueError, match="future"):
        backfill_start(TODAY, {"HEALTH_BACKFILL_START": "2027-01-01"})


def test_backfill_start_default_calendar_five_years():
    assert backfill_start(TODAY, {}) == date(2021, 7, 22)


def test_backfill_start_leap_day_rounds_to_feb_28():
    assert backfill_start(date(2028, 2, 29), {}) == date(2023, 2, 28)


# -- chunking and storage -----------------------------------------------------


def test_rollup_chunks_cover_backfill_range(store):
    client = FakeHealthClient()
    report = engine(client, store, ["steps"],
                    env={"HEALTH_BACKFILL_START": "2026-01-01"}).sync_all()
    assert [c[0] for c in client.calls] == ["steps"] * 3
    assert client.calls[0][1:] == (date(2026, 1, 1), date(2026, 3, 31))
    assert client.calls[-1][1:] == (date(2026, 6, 30), TODAY)
    assert report.progress[0].done and report.progress[0].fetched_ranges == 3
    assert report.requests_made == 3
    assert store.get_sync_state("steps") == TODAY


def test_reconcile_pages_buffered_into_single_chunk_replace(store):
    pages = [hr_page({"2026-07-20": 55}), hr_page({"2026-07-21": 57})]
    client = FakeHealthClient({"resting_hr": [pages]})
    report = engine(client, store, ["resting_hr"],
                    env={"HEALTH_BACKFILL_START": "2026-07-20"}).sync_all()
    assert len(store.daily_frame(["resting_hr"])) == 2
    assert report.requests_made == 2  # one budget slot per reconcile page
    assert store.get_sync_state("resting_hr") == TODAY


def test_parse_failure_leaves_store_and_watermark_untouched(store):
    client = FakeHealthClient({"resting_hr": [[{"dataPoints": "not-a-list"}]]})
    eng = engine(client, store, ["resting_hr"], env={"HEALTH_BACKFILL_START": "2026-07-20"})
    with pytest.raises(PayloadError):
        eng.sync_all()
    assert store.get_sync_state("resting_hr") is None
    assert store.daily_frame(["resting_hr"]).empty
    assert store.raw_stats().empty


def test_sleep_chunk_writes_sessions_and_daily_minutes(store):
    page = json.loads((FIXTURES / "sleep_stages.json").read_text())
    client = FakeHealthClient({"sleep": [[page]]})
    engine(client, store, ["sleep"], env={"HEALTH_BACKFILL_START": "2026-07-01"}).sync_all()
    assert len(store.sleep_frame()) == 1
    df = store.daily_frame(["sleep_minutes"])
    assert len(df) == 1 and df["sleep_minutes"].iloc[0] == 420.0


def test_empty_response_still_replaces_and_advances_watermark(store):
    store.upsert_daily([("steps", "2026-07-10", 999.0)])  # stale row, deleted upstream
    client = FakeHealthClient()
    engine(client, store, ["steps"], env={"HEALTH_BACKFILL_START": "2026-07-01"}).sync_all()
    assert store.get_sync_state("steps") == TODAY
    assert store.daily_frame(["steps"]).empty


# -- pause / cap / resume -----------------------------------------------------


def test_rate_limited_pauses_and_keeps_completed_chunks(store):
    client = FakeHealthClient({"steps": [
        [rollup_page({"2026-01-01": 100})],
        RateLimited(429, "quota", retry_after_s=120),
    ]})
    report = engine(client, store, ["steps"],
                    env={"HEALTH_BACKFILL_START": "2026-01-01"}).sync_all()
    assert report.paused and report.resume_in_s == 120
    assert not report.progress[0].done and report.progress[0].fetched_ranges == 1
    assert store.get_sync_state("steps") == date(2026, 3, 31)
    assert len(store.daily_frame(["steps"])) == 1


def test_cap_between_chunks_stops_early_after_committing_completed(store):
    client = FakeHealthClient()
    report = engine(client, store, ["steps"], env={"HEALTH_BACKFILL_START": "2026-01-01"},
                    max_requests=2).sync_all()
    assert report.stopped_early and report.requests_made == 2
    assert store.get_sync_state("steps") == date(2026, 6, 29)


def test_cap_mid_paging_discards_partial_chunk(store):
    pages = [hr_page({"2026-07-20": 55}), hr_page({"2026-07-21": 57}),
             hr_page({"2026-07-22": 58})]
    client = FakeHealthClient({"resting_hr": [pages]})
    report = engine(client, store, ["resting_hr"],
                    env={"HEALTH_BACKFILL_START": "2026-07-20"}, max_requests=2).sync_all()
    assert report.stopped_early
    assert store.get_sync_state("resting_hr") is None
    assert store.daily_frame(["resting_hr"]).empty


def test_second_run_resumes_with_trailing_refetch(store):
    store.set_sync_state("steps", date(2026, 6, 29))
    client = FakeHealthClient()
    engine(client, store, ["steps"], env={"HEALTH_BACKFILL_START": "2026-01-01"}).sync_all()
    assert client.calls[0][1] == date(2026, 6, 27)  # last_synced - 2 days


def test_up_to_date_metric_refetches_trailing_window_only(store):
    store.set_sync_state("steps", TODAY)
    client = FakeHealthClient()
    engine(client, store, ["steps"], env={"HEALTH_BACKFILL_START": "2026-01-01"}).sync_all()
    assert client.calls == [("steps", TODAY - timedelta(days=2), TODAY)]


def test_intraday_first_run_starts_29_days_back(store):
    client = FakeHealthClient()
    engine(client, store, ["intraday_hr"]).sync_all()
    assert client.calls[0][1:] == (TODAY - timedelta(days=29), TODAY - timedelta(days=29))
    assert len(client.calls) == 30  # 1-day chunks


def test_progress_callback_reports_metric_range_and_request_count(store):
    seen = []
    client = FakeHealthClient()
    engine(client, store, ["steps"], env={"HEALTH_BACKFILL_START": "2026-07-01"}).sync_all(
        progress_cb=lambda metric, msg: seen.append((metric, msg)))
    assert seen == [("steps", "2026-07-01 → 2026-07-22 (1 req)")]
```

- [ ] **Step 2: Run to verify failures**

```bash
ENVP uv run --no-sync pytest health/tests/test_sync.py -q
```

Expected: ImportError (`backfill_start` not defined) / failures — nothing passes against old sync.py.

- [ ] **Step 3: Rewrite `health/src/health/sync.py`** with this exact content:

```python
"""Resumable backfill/incremental sync over the Google Health metric catalog.

The engine owns chunking, buffering, and stop conditions only. Pacing and the
one-shot 401 refresh/retry live in `HealthClient`; atomicity lives in
`Store.replace_chunk`. Never add sleeps or retries here.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric, chunk_ranges
from health.store import Store

MAX_REQUESTS_PER_RUN = 200   # hard cap on physical API requests per sync run
TRAILING_REFETCH_DAYS = 2    # re-fetch last_synced - 2d .. today (3-day window)
INTRADAY_LOOKBACK_DAYS = 30  # non-full-history metrics: today - 29d start
BACKFILL_START_ENV = "HEALTH_BACKFILL_START"
BACKFILL_YEARS = 5


def backfill_start(today: date, env: Mapping[str, str] | None = None) -> date:
    """First day of a full-history backfill: HEALTH_BACKFILL_START if set,
    else the calendar date 5 years back (Feb 29 rounds to Feb 28)."""
    raw = (os.environ if env is None else env).get(BACKFILL_START_ENV)
    if raw:
        try:
            start = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(
                f"{BACKFILL_START_ENV} must be an ISO date (YYYY-MM-DD), got {raw!r}") from exc
        if start > today:
            raise ValueError(f"{BACKFILL_START_ENV} is in the future: {raw}")
        return start
    year = today.year - BACKFILL_YEARS
    if today.month == 2 and today.day == 29:
        return date(year, 2, 28)
    return today.replace(year=year)


@dataclass
class MetricProgress:
    metric: str
    fetched_ranges: int = 0
    done: bool = False


@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    paused: bool = False               # 429: resume after resume_in_s
    resume_in_s: int | None = None
    stopped_early: bool = False        # request cap: resume immediately
    requests_made: int = 0


class SyncEngine:
    def __init__(self, client, store: Store, catalog: list[Metric] = CATALOG,
                 today: date | None = None, env: Mapping[str, str] | None = None,
                 max_requests: int = MAX_REQUESTS_PER_RUN):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.env = env
        self.max_requests = max_requests

    def _start_date(self, m: Metric) -> date:
        if m.full_history:
            default = backfill_start(self.today, self.env)
        else:
            default = self.today - timedelta(days=INTRADAY_LOOKBACK_DAYS - 1)
        last = self.store.get_sync_state(m.name)
        if last is None:
            return default
        return max(default, min(last - timedelta(days=TRAILING_REFETCH_DAYS), self.today))

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None) -> SyncReport:
        report = SyncReport()
        budget = RequestBudget(self.max_requests)
        for m in self.catalog:
            prog = MetricProgress(metric=m.name)
            report.progress.append(prog)
            for s, e in chunk_ranges(self._start_date(m), self.today, m.max_range_days):
                try:
                    if m.method == DAILY_ROLLUP:
                        pages = [self.client.daily_rollup(m, s, e, budget)]
                    else:
                        pages = list(self.client.iter_reconciled(m, s, e, budget))
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    report.requests_made = budget.used
                    return report
                except RequestCapExceeded:
                    report.stopped_early = True
                    report.requests_made = budget.used
                    return report
                # Parse before replace: a PayloadError propagates and neither
                # raw pages nor the watermark move for this chunk.
                rows = m.parse_pages(pages)
                self.store.replace_chunk(m, s, e, pages, rows)
                prog.fetched_ranges += 1
                if progress_cb:
                    progress_cb(m.name, f"{s} → {e} ({budget.used} req)")
            prog.done = True
        report.requests_made = budget.used
        return report
```

- [ ] **Step 4: Run the sync suite, then the full suite**

```bash
ENVP uv run --no-sync pytest health/tests/test_sync.py -q
ENVP uv run --no-sync pytest health/tests -q
```

Expected: test_sync all PASS; full suite `2 failed` (only test_inventory remains).

- [ ] **Step 5: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/src health/tests && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/src health/tests
git add health/src/health/sync.py health/tests/test_sync.py
git commit -m "feat(health): resumable sync engine over google client with hard cap"
```

---

### Task 3: Inventory — published vs implemented vs stored

**Files:**
- Rewrite: `health/src/health/inventory.py`
- Rewrite: `health/tests/test_inventory.py`

**Interfaces:**
- Consumes: `KNOWN_DATA_TYPES: dict[str, tuple[label, scope]]`, `CATALOG`, `Store.sync_states/series_stats/intraday_stats/sleep_stats/raw_stats`.
- Produces: `Inventory` dataclass with `published` (columns `data_type, label, scope, implemented, metrics, method, last_synced, status`), `series` (columns `metric, table, n, first_date, last_date`), `raw` (Store.raw_stats passthrough). `build_inventory(store, catalog=CATALOG) -> Inventory`.

- [ ] **Step 1: Rewrite `health/tests/test_inventory.py`** with this exact content:

```python
"""Inventory tests: published/implemented mapping and stored-series stats."""

from datetime import date

import pytest
from health.endpoints import CATALOG, KNOWN_DATA_TYPES
from health.inventory import build_inventory
from health.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def sleep_row():
    return {
        "provider_id": "users/me/dataTypes/sleep/dataPoints/fake-1",
        "date": "2026-07-01", "start_ts": "2026-06-30 23:41:30",
        "end_ts": "2026-07-01 07:05:30", "minutes_asleep": 402, "minutes_deep": 80,
        "minutes_light": 220, "minutes_rem": 102, "minutes_wake": 42,
        "efficiency": 93, "is_main": True,
    }


def test_inventory_lists_every_published_data_type(store):
    pub = build_inventory(store).published
    assert set(pub["data_type"]) == set(KNOWN_DATA_TYPES)
    implemented = set(pub[pub["implemented"]]["data_type"])
    assert implemented == {m.data_type for m in CATALOG}


def test_inventory_steps_data_type_maps_both_metrics(store):
    row = build_inventory(store).published.set_index("data_type").loc["steps"]
    assert row["metrics"] == "steps, intraday_steps"
    assert row["method"] == "daily_rollup, reconcile"


def test_inventory_state_merged_into_published(store):
    store.set_sync_state("resting_hr", date(2026, 7, 20))
    row = build_inventory(store).published.set_index("data_type").loc[
        "daily-resting-heart-rate"]
    assert row["last_synced"] == "2026-07-20" and row["status"] == "ok"


def test_inventory_series_stats_cover_all_tables(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0), ("steps", "2026-07-02", 2.0)])
    store.upsert_intraday([("hr", "2026-07-01 00:00:00", 60.0)])
    store.upsert_sleep([sleep_row()])
    s = build_inventory(store).series.set_index("metric")
    assert s.loc["steps", "n"] == 2 and s.loc["steps", "table"] == "daily"
    assert s.loc["hr", "table"] == "intraday" and s.loc["hr", "n"] == 1
    assert s.loc["sleep_sessions", "table"] == "sleep" and s.loc["sleep_sessions", "n"] == 1


def test_inventory_empty_store_stable_columns(store):
    inv = build_inventory(store)
    assert list(inv.published.columns) == [
        "data_type", "label", "scope", "implemented", "metrics", "method",
        "last_synced", "status"]
    assert list(inv.series.columns) == ["metric", "table", "n", "first_date", "last_date"]
    assert list(inv.raw.columns) == [
        "metric", "n_pages", "first_range_start", "last_range_end"]
```

- [ ] **Step 2: Run to verify failures**

```bash
ENVP uv run --no-sync pytest health/tests/test_inventory.py -q
```

Expected: all FAIL (old build_inventory returns a bare DataFrame / crashes on `m.kind`).

- [ ] **Step 3: Rewrite `health/src/health/inventory.py`** with this exact content:

```python
"""Data inventory: published data types vs implemented catalog vs stored series."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from health.endpoints import CATALOG, KNOWN_DATA_TYPES, Metric
from health.store import Store


@dataclass
class Inventory:
    published: pd.DataFrame  # one row per KNOWN_DATA_TYPES id
    series: pd.DataFrame     # one row per stored series (daily/intraday/sleep)
    raw: pd.DataFrame        # raw page counts per metric


def _iso(value) -> str:
    return pd.Timestamp(value).date().isoformat()


def build_inventory(store: Store, catalog: list[Metric] = CATALOG) -> Inventory:
    states = store.sync_states()
    state_by_metric = {} if states.empty else {
        r.metric: r for r in states.itertuples(index=False)}

    by_data_type: dict[str, list[Metric]] = {}
    for m in catalog:
        by_data_type.setdefault(m.data_type, []).append(m)

    pub_rows = []
    for dt_id, (label, scope) in KNOWN_DATA_TYPES.items():
        ms = by_data_type.get(dt_id, [])
        st_rows = [s for s in (state_by_metric.get(m.name) for m in ms) if s is not None]
        pub_rows.append({
            "data_type": dt_id, "label": label, "scope": scope,
            "implemented": bool(ms),
            "metrics": ", ".join(m.name for m in ms),
            "method": ", ".join(sorted({m.method for m in ms})),
            "last_synced": ", ".join(_iso(s.last_synced_date) for s in st_rows) or None,
            "status": ", ".join(s.status for s in st_rows) or None,
        })
    published = pd.DataFrame(pub_rows)

    daily = store.series_stats()
    daily.insert(1, "table", "daily")
    intra = store.intraday_stats()
    intra.insert(1, "table", "intraday")
    sleep = store.sleep_stats()
    sleep.insert(0, "metric", "sleep_sessions")
    sleep.insert(1, "table", "sleep")
    series = pd.concat([daily, intra, sleep], ignore_index=True)[
        ["metric", "table", "n", "first_date", "last_date"]]

    return Inventory(published=published, series=series, raw=store.raw_stats())
```

- [ ] **Step 4: Run inventory suite, then full suite**

```bash
ENVP uv run --no-sync pytest health/tests/test_inventory.py -q
ENVP uv run --no-sync pytest health/tests -q
```

Expected: all PASS; full suite green (0 failed).

- [ ] **Step 5: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/src health/tests && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/src health/tests
git add health/src/health/inventory.py health/tests/test_inventory.py
git commit -m "feat(health): inventory over published data types and stored series"
```

---

### Task 4: Shared theme + common helpers (app foundation)

**Files:**
- Create: `health/app/theme.py`
- Rewrite: `health/app/common.py`

**Interfaces:**
- Produces (theme.py): `LIGHT`/`DARK` palette dicts (keys `surface, grid, axis, muted, ink, categorical, line_safe, sequential`), `palette() -> dict` (picks by `st.context.theme.type`), `style(fig, p=None) -> fig`.
- Produces (common.py): `get_store()`, `get_auth()` (returns `GoogleHealthAuth`), `load_daily(metrics: tuple) -> DataFrame`, `load_sleep() -> DataFrame`, `load_intraday(metric: str, day: date) -> DataFrame` (all `st.cache_data(ttl=300)`), `period_days(default="90日") -> int | None` (sidebar radio, shared session key `period_days`), `clip_days(df, days, date_col="date") -> DataFrame` (trailing calendar days, not rows).

- [ ] **Step 1: Create `health/app/theme.py`** with this exact content:

```python
"""Shared chart chrome: dataviz palette (light + dark) and Plotly styling.

Palette source: dataviz skill references/palette.md (July 2026 ordering).
Light and dark are both selected steps of the same hues — never an automatic
flip. The categorical slot order is the CVD-safety mechanism: assign hues in
fixed order, never cycled.
"""
import streamlit as st

_SEQ_LIGHT = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
              "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

LIGHT = {
    "surface": "#fcfcfb",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "muted": "#898781",
    "ink": "#0b0b0b",
    "categorical": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                    "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    # Thin 2px lines skip the sub-3:1 slots on the light surface (aqua,
    # yellow, magenta) — the palette's relief rule; fixed order preserved.
    "line_safe": ["#2a78d6", "#eb6834", "#008300"],
    "sequential": _SEQ_LIGHT,
}

DARK = {
    "surface": "#1a1a19",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "muted": "#898781",
    "ink": "#ffffff",
    "categorical": ["#3987e5", "#d95926", "#199e70", "#c98500",
                    "#d55181", "#008300", "#9085e9", "#e66767"],
    # Dark steps are >= 3:1 on the dark surface; keep the same leading hues
    # as light mode so series identity survives a theme switch.
    "line_safe": ["#3987e5", "#d95926", "#008300"],
    "sequential": list(reversed(_SEQ_LIGHT)),  # low=dark, high=light on dark surface
}


def palette() -> dict:
    """Palette for the viewer's current Streamlit theme (light by default)."""
    theme = getattr(st.context, "theme", None)
    dark = theme is not None and getattr(theme, "type", "light") == "dark"
    return DARK if dark else LIGHT


def style(fig, p: dict | None = None):
    """Common chart chrome: surface bg, hairline recessive grid, muted ink."""
    p = p or palette()
    fig.update_layout(plot_bgcolor=p["surface"], paper_bgcolor=p["surface"],
                      font_color=p["ink"], legend=dict(bgcolor="rgba(0,0,0,0)"),
                      margin=dict(t=30, l=10, r=10, b=10), hovermode="x unified")
    fig.update_xaxes(gridcolor=p["grid"], linecolor=p["axis"],
                     tickfont_color=p["muted"], zeroline=False)
    fig.update_yaxes(gridcolor=p["grid"], linecolor=p["axis"],
                     tickfont_color=p["muted"], zeroline=False)
    return fig
```

- [ ] **Step 2: Rewrite `health/app/common.py`** with this exact content:

```python
"""Shared app context: paths, cached resources, cached frames, period selector."""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from health.auth import GoogleHealthAuth
from health.store import Store

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

PERIOD_OPTIONS = {"30日": 30, "90日": 90, "180日": 180, "1年": 365, "全期間": None}


@st.cache_resource
def get_store() -> Store:
    return Store(DATA_DIR / "health.duckdb")


def get_auth() -> GoogleHealthAuth:
    return GoogleHealthAuth.from_env(DATA_DIR)


@st.cache_data(ttl=300)
def load_daily(metrics: tuple[str, ...]) -> pd.DataFrame:
    return get_store().daily_frame(list(metrics))


@st.cache_data(ttl=300)
def load_sleep() -> pd.DataFrame:
    return get_store().sleep_frame()


@st.cache_data(ttl=300)
def load_intraday(metric: str, day: date) -> pd.DataFrame:
    return get_store().intraday_frame(metric, day)


def period_days(default: str = "90日") -> int | None:
    """Sidebar period selector; one shared session key across all pages."""
    labels = list(PERIOD_OPTIONS)
    sel = st.sidebar.radio("表示期間", labels, index=labels.index(default), key="period_days")
    return PERIOD_OPTIONS[sel]


def clip_days(df: pd.DataFrame, days: int | None, date_col: str = "date") -> pd.DataFrame:
    """Keep the trailing `days` calendar days (not rows) of `df`."""
    if days is None or df.empty:
        return df
    dates = pd.to_datetime(df[date_col])
    return df[dates >= dates.max() - pd.Timedelta(days=days - 1)]
```

- [ ] **Step 3: Lint + commit** (import check comes after the views are migrated; the old views still import removed names until Tasks 5–9 land)

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/theme.py health/app/common.py
git commit -m "feat(health): shared theme (light/dark palette) and cached app helpers"
```

---

### Task 5: App shell — OAuth callback, onboarding, navigation

**Files:**
- Rewrite: `health/app/main.py`

**Interfaces:**
- Consumes: `get_auth()` from common; `GoogleHealthAuth.complete_auth(code, state, error=None, error_description=None)`, `.load_tokens()`, `.begin_auth()`.
- Produces: unchanged page functions/nav; callback handles denial (`?error=...`) and clears query params on every outcome before token exchange result is shown.

- [ ] **Step 1: Rewrite `health/app/main.py`** with this exact content:

```python
"""Streamlit entry: OAuth callback handling, onboarding, navigation."""
import streamlit as st

from health.auth import AuthError

from common import get_auth


def _handle_callback(auth) -> None:
    qp = st.query_params
    if ("code" not in qp and "error" not in qp) or auth.load_tokens() is not None:
        return
    code, state = qp.get("code"), qp.get("state", "")
    error, error_desc = qp.get("error"), qp.get("error_description")
    # The callback is single-use: clear the query params before exchanging so
    # a rerun or reload can never replay a stale authorization code.
    st.query_params.clear()
    try:
        auth.complete_auth(code, state, error=error, error_description=error_desc)
        st.success("Google Health と接続しました")
    except AuthError as exc:
        st.error(f"認証に失敗しました: {exc}")


def _connect_page(auth) -> None:
    st.title("Health ダッシュボード")
    st.markdown("**はじめに** — 2ステップで使い始められます。")
    st.markdown("1. 下のリンクから Google Health と接続する\n"
                "2. 接続後、管理 > 同期 ページでデータを同期する")
    st.markdown(f"### [Google Health と接続する]({auth.begin_auth()})")
    st.caption("Google Cloud の OAuth クライアント (Client ID/Secret) を health/.env に"
               "設定してから接続してください。手順は health/README.md を参照。")


def main() -> None:
    st.set_page_config(page_title="Health", page_icon="🏃", layout="wide")
    try:
        auth = get_auth()
    except AuthError as exc:
        st.error(f"設定エラー: {exc}")
        st.stop()

    _handle_callback(auth)
    if auth.load_tokens() is None:
        _connect_page(auth)
        st.stop()

    from views.activity_view import activity_page
    from views.body_view import body_page
    from views.heart_view import heart_page
    from views.inventory_view import inventory_page
    from views.overview_view import overview_page
    from views.sleep_view import sleep_page
    from views.sync_view import sync_page

    nav = st.navigation({
        "ダッシュボード": [
            st.Page(overview_page, title="概要", icon="🏠", default=True),
            st.Page(sleep_page, title="睡眠", icon="😴"),
            st.Page(activity_page, title="活動", icon="👟"),
            st.Page(heart_page, title="心拍", icon="❤️"),
            st.Page(body_page, title="身体", icon="⚖️"),
        ],
        "管理": [
            st.Page(sync_page, title="同期", icon="🔄"),
            st.Page(inventory_page, title="データ棚卸し", icon="📋"),
        ],
    })
    nav.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/main.py
git commit -m "fix(health): oauth denial handling, single-use callback, onboarding copy"
```

---

### Task 6: Sync view — error taxonomy, cap/429 UX, disconnect

**Files:**
- Rewrite: `health/app/views/sync_view.py`

**Interfaces:**
- Consumes: `SyncEngine(HealthClient(auth), get_store()).sync_all(progress_cb)`, `SyncReport.paused/resume_in_s/stopped_early/requests_made`, `MAX_REQUESTS_PER_RUN`, `ApiError.status_code/status/message`, `PayloadError.metric/.detail`, `GoogleHealthAuth.forget_tokens()/refresh_expires_in_days()/load_tokens()`.

- [ ] **Step 1: Rewrite `health/app/views/sync_view.py`** with this exact content:

```python
"""Sync page: on-demand sync with cap/429 reporting, token status, disconnect."""
from datetime import datetime, timedelta

import streamlit as st

from health.auth import AuthError
from health.client import ApiError, HealthClient
from health.endpoints import PayloadError
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine

from common import get_auth, get_store


def _show_last_report() -> None:
    last = st.session_state.pop("last_sync_report", None)
    if last is None:
        return
    if last["paused"]:
        resume_in = last["resume_in_s"] or 60
        mins = max(1, -(-resume_in // 60))
        at = (datetime.now() + timedelta(seconds=resume_in)).strftime("%H:%M")
        st.warning(f"レート制限 (429) に達しました。進捗は保存済みです。"
                   f"{at} 頃（約 {mins} 分後）にもう一度同期してください。")
    elif last["stopped_early"]:
        st.warning(f"1回の実行上限（{MAX_REQUESTS_PER_RUN} リクエスト）に達したため中断しました。"
                   "進捗は保存済みです。もう一度同期すると続きから再開します。")
    else:
        st.success(f"同期が完了しました（{last['requests_made']} リクエスト）")


def _token_panel(auth) -> None:
    tokens = auth.load_tokens()
    if tokens is None:
        return
    exp = datetime.fromtimestamp(tokens["expires_at"]).strftime("%m/%d %H:%M")
    st.caption(f"アクセストークン有効期限: {exp} / スコープ: {tokens.get('scope', '-')}")
    days = auth.refresh_expires_in_days()
    if days is None:
        return
    if days <= 2:
        st.warning(f"リフレッシュトークンの残りが約 {max(days, 0):.1f} 日です。"
                   "失効すると再接続が必要になります。")
    else:
        st.caption(f"リフレッシュトークン残り: 約 {days:.0f} 日")


def _run_sync(auth) -> None:
    engine = SyncEngine(HealthClient(auth), get_store())
    try:
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, msg: status.write(f"{metric}: {msg}"))
    except AuthError:
        st.error("認証が失効しています。下の「接続解除」を押してから、"
                 "トップページで Google Health と再接続してください。")
    except ApiError as exc:
        detail = f" / {exc.status}" if exc.status else ""
        st.error(f"Google Health API エラー (HTTP {exc.status_code}{detail}): {exc.message}")
        if exc.status_code == 403:
            st.caption("スコープ不足か API 未有効化の可能性があります。"
                       "health/README.md の OAuth 設定を確認してください。")
    except PayloadError as exc:
        st.error(f"想定外のレスポンス形式（{exc.metric}）: {exc.detail}。"
                 "このチャンクは保存せず停止しました。既存データは壊れていません。")
    else:
        st.cache_data.clear()
        st.session_state["last_sync_report"] = {
            "paused": report.paused, "resume_in_s": report.resume_in_s,
            "stopped_early": report.stopped_early, "requests_made": report.requests_made}
        st.rerun()


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    _show_last_report()
    _token_panel(auth)

    if st.button("Google Health からデータを同期", type="primary"):
        _run_sync(auth)

    states = get_store().sync_states()
    if not states.empty:
        st.subheader("メトリクス別の同期状態")
        st.dataframe(states, use_container_width=True, hide_index=True,
                     column_config={
                         "metric": st.column_config.TextColumn("メトリクス"),
                         "last_synced_date": st.column_config.DateColumn("最終同期日"),
                         "status": st.column_config.TextColumn("状態"),
                     })

    st.divider()
    if st.button("接続解除（トークンを削除。次回は再認可が必要です）"):
        auth.forget_tokens()
        st.cache_data.clear()
        st.rerun()
```

- [ ] **Step 2: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/views/sync_view.py
git commit -m "feat(health): sync view with error taxonomy, cap/429 ux, disconnect"
```

---

### Task 7: Overview view — dated cards, consecutive-day delta

**Files:**
- Rewrite: `health/app/views/overview_view.py`

- [ ] **Step 1: Rewrite `health/app/views/overview_view.py`** with this exact content:

```python
"""Overview: latest daily cards + 30-day sparklines."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import clip_days, load_daily
from theme import palette

METRICS = [("steps", "歩数", "{:,.0f}"), ("sleep_minutes", "睡眠(分)", "{:,.0f}"),
           ("resting_hr", "安静時心拍", "{:.0f}")]


def overview_page() -> None:
    st.title("概要")
    df = load_daily(tuple(m for m, _, _ in METRICS))
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, 30).copy()
    df["date"] = pd.to_datetime(df["date"])
    accent = palette()["categorical"][0]
    cols = st.columns(len(METRICS))
    for col, (metric, label, fmt) in zip(cols, METRICS):
        series = df[["date", metric]].dropna()
        with col:
            if series.empty:
                st.metric(label, "-")
                st.caption("データなし")
                continue
            last = series.iloc[-1]
            delta = None
            if len(series) > 1:
                prev = series.iloc[-2]
                if (last["date"] - prev["date"]).days == 1:
                    delta = last[metric] - prev[metric]
            st.metric(label, fmt.format(last[metric]),
                      delta=fmt.format(delta) if delta is not None else None,
                      help="前日比は暦上の前日にデータがある場合のみ表示")
            st.caption(f"{last['date']:%-m/%-d} 時点")
            fig = px.line(df, x="date", y=metric, height=120)
            fig.update_traces(line_color=accent, line_width=2, hovertemplate=None)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                              xaxis_visible=False, yaxis_visible=False,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              hovermode="x")
            st.plotly_chart(fig, use_container_width=True, key=f"spark_{metric}", theme=None)
```

- [ ] **Step 2: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/views/overview_view.py
git commit -m "feat(health): overview cards with data dates and true day-over-day delta"
```

---

### Task 8: Sleep view — gantt nights, efficiency, classic-sleep notice

**Files:**
- Rewrite: `health/app/views/sleep_view.py`

- [ ] **Step 1: Rewrite `health/app/views/sleep_view.py`** with this exact content:

```python
"""Sleep: stage composition, duration/efficiency trends, nightly gantt, weekday pattern."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import clip_days, load_sleep, period_days
from theme import palette, style

STAGES = [("minutes_deep", "深い"), ("minutes_rem", "REM"),
          ("minutes_light", "浅い"), ("minutes_wake", "覚醒")]
GANTT_MAX_NIGHTS = 90
WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


def _stage_bar(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("ステージ構成")
    stages_missing = int(sf[["minutes_deep", "minutes_rem", "minutes_light"]].sum().sum()) == 0
    if stages_missing:
        st.info("詳細ステージなし（Classic sleep）: 深い/REM/浅いの内訳がないため、"
                "睡眠/覚醒の2区分で表示します。")
        parts = [("minutes_asleep", "睡眠"), ("minutes_wake", "覚醒")]
    else:
        parts = STAGES
    colors = {label: p["categorical"][i] for i, (_, label) in enumerate(parts)}
    long = sf.melt(id_vars=["date"], value_vars=[c for c, _ in parts],
                   var_name="stage", value_name="minutes")
    long["stage"] = long["stage"].map(dict(parts))
    fig = px.bar(long, x="date", y="minutes", color="stage", color_discrete_map=colors,
                 labels={"minutes": "分", "date": "日付", "stage": "ステージ"})
    # surface gap between stacked segments (mark spec) instead of a border stroke
    fig.update_traces(marker_line_color=p["surface"], marker_line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)


def _trends(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("睡眠時間トレンド（7日移動平均つき）")
    trend = sf[["date", "minutes_asleep"]].copy()
    trend["ma7"] = trend["minutes_asleep"].rolling(7).mean()
    trend = trend.rename(columns={"minutes_asleep": "実績", "ma7": "7日移動平均"})
    fig = px.line(trend, x="date", y=["実績", "7日移動平均"],
                  color_discrete_sequence=p["line_safe"],
                  labels={"date": "日付", "value": "分", "variable": ""})
    fig.update_traces(line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("睡眠効率")
    fig = px.line(sf, x="date", y="efficiency", labels={"date": "日付", "efficiency": "%"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)


def _night_gantt(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("就寝・起床（夜ごとの睡眠区間）")
    gd = sf.tail(GANTT_MAX_NIGHTS).copy()
    if len(sf) > GANTT_MAX_NIGHTS:
        st.caption(f"直近 {GANTT_MAX_NIGHTS} 夜のみ表示")
    gd["start_ts"] = pd.to_datetime(gd["start_ts"])
    gd["end_ts"] = pd.to_datetime(gd["end_ts"])
    # Normalize every night onto one clock axis anchored at the noon before the
    # wake date, so bedtimes crossing midnight stay continuous.
    anchor = pd.to_datetime(gd["date"]) - pd.Timedelta(hours=12)
    ref = pd.Timestamp("2000-01-01")
    gd["clock_start"] = ref + (gd["start_ts"] - anchor)
    gd["clock_end"] = ref + (gd["end_ts"] - anchor)
    gd["night"] = pd.to_datetime(gd["date"]).dt.strftime("%m/%d")
    fig = px.timeline(gd, x_start="clock_start", x_end="clock_end", y="night",
                      hover_data={"clock_start": False, "clock_end": False,
                                  "start_ts": "|%H:%M", "end_ts": "|%H:%M"})
    fig.update_traces(marker_color=p["categorical"][0],
                      marker_line_color=p["surface"], marker_line_width=1)
    fig.update_yaxes(autorange="reversed")
    ticks = list(range(6, 28, 3))
    fig.update_xaxes(tickvals=[ref + pd.Timedelta(hours=h) for h in ticks],
                     ticktext=[f"{(12 + h) % 24}:00" for h in ticks])
    fig.update_layout(height=max(300, min(900, 12 * len(gd) + 80)))
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)


def _weekday_pattern(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("曜日パターン")
    wp = sf.copy()
    wp["weekday"] = pd.to_datetime(wp["date"]).dt.weekday
    agg = wp.groupby("weekday")["minutes_asleep"].mean().reset_index()
    agg["weekday"] = agg["weekday"].map(dict(enumerate(WEEKDAY_LABELS)))
    fig = px.bar(agg, x="weekday", y="minutes_asleep",
                 category_orders={"weekday": WEEKDAY_LABELS},
                 labels={"weekday": "曜日", "minutes_asleep": "平均睡眠時間（分）"})
    fig.update_traces(marker_color=p["categorical"][0])
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)


def sleep_page() -> None:
    st.title("睡眠")
    p = palette()
    sf = load_sleep()
    sf = sf[sf["is_main"]].copy()
    if sf.empty:
        st.info("睡眠データがありません。まず「同期」ページで同期してください。")
        return
    sf = clip_days(sf, period_days())
    _stage_bar(sf, p)
    _trends(sf, p)
    _night_gantt(sf, p)
    _weekday_pattern(sf, p)
```

- [ ] **Step 2: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/views/sleep_view.py
git commit -m "feat(health): sleep view gantt nights, efficiency trend, classic notice"
```

---

### Task 9: Activity / Heart / Body views

**Files:**
- Rewrite: `health/app/views/activity_view.py`
- Rewrite: `health/app/views/heart_view.py`
- Rewrite: `health/app/views/body_view.py`

- [ ] **Step 1: Rewrite `health/app/views/activity_view.py`** with this exact content:

```python
"""Activity: steps/intensity/distance/calories trends, heatmap, intraday steps."""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from common import clip_days, load_daily, load_intraday, period_days
from theme import palette, style

INTENSITIES = [("minutes_lightly_active", "軽い"), ("minutes_fairly_active", "中程度"),
               ("minutes_very_active", "高強度")]
HEATMAP_MAX_WEEKS = 26
WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


def activity_page() -> None:
    st.title("活動")
    p = palette()
    df = load_daily(("steps", "calories", "distance_km", "minutes_lightly_active",
                     "minutes_fairly_active", "minutes_very_active"))
    if df.empty:
        st.info("活動データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days()).copy()

    st.subheader("歩数（7日移動平均つき）")
    df["ma7"] = df["steps"].rolling(7).mean()
    fig = px.bar(df, x="date", y="steps", labels={"date": "日付", "steps": "歩数"})
    fig.update_traces(marker_color=p["categorical"][0], name="歩数", showlegend=True)
    fig.add_scatter(x=df["date"], y=df["ma7"], mode="lines", name="7日平均",
                    line=dict(color=p["categorical"][1], width=2))
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("活動強度の内訳（分）")
    icols = [c for c, _ in INTENSITIES]
    im = df[["date", *icols]].dropna(how="all", subset=icols)
    if im.empty:
        st.caption("データなし（デバイス非対応の可能性）")
    else:
        long = im.melt(id_vars=["date"], var_name="intensity", value_name="minutes")
        long["intensity"] = long["intensity"].map(dict(INTENSITIES))
        colors = {label: p["categorical"][i] for i, (_, label) in enumerate(INTENSITIES)}
        fig = px.bar(long, x="date", y="minutes", color="intensity",
                     color_discrete_map=colors,
                     labels={"date": "日付", "minutes": "分", "intensity": "強度"})
        fig.update_traces(marker_line_color=p["surface"], marker_line_width=1)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("距離 (km)")
    fig = px.line(df, x="date", y="distance_km", labels={"date": "日付", "distance_km": "km"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("消費カロリー")
    fig = px.line(df, x="date", y="calories", labels={"date": "日付", "calories": "kcal"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("週間ヒートマップ（歩数）")
    hm = df.copy()
    hm["date"] = pd.to_datetime(hm["date"])
    hm["weekday"] = hm["date"].dt.weekday
    hm["week"] = hm["date"].dt.strftime("%G-W%V")
    pivot = hm.pivot_table(index="weekday", columns="week", values="steps")
    if pivot.shape[1] > HEATMAP_MAX_WEEKS:
        pivot = pivot.iloc[:, -HEATMAP_MAX_WEEKS:]
        st.caption(f"直近 {HEATMAP_MAX_WEEKS} 週のみ表示")
    pivot.index = [WEEKDAY_LABELS[i] for i in pivot.index]  # weekday number, not position
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale=p["sequential"],
                    labels=dict(color="歩数", x="週", y="曜日"))
    fig.update_layout(paper_bgcolor=p["surface"], plot_bgcolor=p["surface"],
                      font_color=p["ink"], margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.subheader("日内歩数ビューア")
    day = st.date_input("日付", value=date.today(), key="act_day")
    intra = load_intraday("steps", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        fig = px.bar(intra, x="ts", y="value", labels={"value": "歩数", "ts": "時刻"})
        fig.update_traces(marker_color=p["categorical"][0])
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
```

- [ ] **Step 2: Rewrite `health/app/views/heart_view.py`** with this exact content:

```python
"""Heart: resting HR / HRV (avg + deep sleep) trends, intraday HR viewer."""
from datetime import date

import plotly.express as px
import streamlit as st

from common import clip_days, load_daily, load_intraday, period_days
from theme import palette, style


def heart_page() -> None:
    st.title("心拍")
    p = palette()
    df = load_daily(("resting_hr", "hrv_rmssd", "hrv_deep_rmssd"))
    if df.empty:
        st.info("心拍データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days())

    st.subheader("安静時心拍")
    rh = df.dropna(subset=["resting_hr"])
    if rh.empty:
        st.caption("データなし（デバイス非対応の可能性）")
    else:
        fig = px.line(rh, x="date", y="resting_hr", labels={"date": "日付", "resting_hr": "bpm"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("HRV (RMSSD)")
    hrv = df.dropna(subset=["hrv_rmssd", "hrv_deep_rmssd"], how="all")
    if hrv.empty:
        st.caption("HRV データなし（デバイス非対応の可能性）")
    else:
        renamed = hrv.rename(columns={"hrv_rmssd": "平均", "hrv_deep_rmssd": "深い睡眠時"})
        fig = px.line(renamed, x="date", y=["平均", "深い睡眠時"],
                      color_discrete_sequence=p["line_safe"],
                      labels={"date": "日付", "value": "ms", "variable": ""})
        fig.update_traces(line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("分単位心拍ビューア")
    day = st.date_input("日付", value=date.today(), key="hr_day")
    intra = load_intraday("hr", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        fig = px.line(intra, x="ts", y="value", labels={"value": "bpm", "ts": "時刻"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
```

- [ ] **Step 3: Rewrite `health/app/views/body_view.py`** with this exact content:

```python
"""Body: weight, body fat, SpO2 (avg/lower/upper), skin temp, breathing rate."""
import plotly.express as px
import streamlit as st

from common import clip_days, load_daily, period_days
from theme import palette, style

# Metrics of different units are never combined on one axis (dataviz
# anti-pattern: mismatched-scale series flattens the smaller one); SpO2's
# three sub-series share one % scale so they stay combined.
PANELS = [(["weight_kg"], "体重"),
          (["fat_pct"], "体脂肪率"),
          (["spo2_avg", "spo2_lower_bound", "spo2_upper_bound"], "SpO2"),
          (["temp_skin_relative"], "皮膚温（基準比）"),
          (["breathing_rate"], "呼吸数")]

JP_LABELS = {"weight_kg": "kg", "fat_pct": "%", "spo2_avg": "平均",
             "spo2_lower_bound": "下限", "spo2_upper_bound": "上限",
             "temp_skin_relative": "基準比", "breathing_rate": "回/分"}


def body_page() -> None:
    st.title("身体")
    p = palette()
    df = load_daily(tuple(sorted({m for ms, _ in PANELS for m in ms})))
    if df.empty:
        st.info("身体データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days())
    for metrics, label in PANELS:
        sub = df[["date", *metrics]].dropna(how="all", subset=metrics)
        st.subheader(label)
        if sub.empty:
            st.caption("データなし（デバイス非対応の可能性）")
            continue
        if len(metrics) == 1:
            m = metrics[0]
            fig = px.line(sub, x="date", y=m, labels={"date": "日付", m: JP_LABELS[m]})
            fig.update_traces(line_color=p["categorical"][0], line_width=2)
        else:
            renamed = sub.rename(columns={m: JP_LABELS[m] for m in metrics})
            fig = px.line(renamed, x="date", y=[JP_LABELS[m] for m in metrics],
                          color_discrete_sequence=p["line_safe"],
                          labels={"date": "日付", "value": "%", "variable": ""})
            fig.update_traces(line_width=2)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
```

- [ ] **Step 4: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/views/activity_view.py health/app/views/heart_view.py health/app/views/body_view.py
git commit -m "feat(health): activity/heart/body views on shared theme with new series"
```

---

### Task 10: Inventory view — three sections

**Files:**
- Rewrite: `health/app/views/inventory_view.py`

**Interfaces:**
- Consumes: `build_inventory(store) -> Inventory` (`.published`, `.series`, `.raw` from Task 3).

- [ ] **Step 1: Rewrite `health/app/views/inventory_view.py`** with this exact content:

```python
"""Inventory page: published data types, implemented catalog, stored series."""
import streamlit as st

from health.inventory import build_inventory

from common import get_store


def inventory_page() -> None:
    st.title("データ棚卸し")
    inv = build_inventory(get_store())

    st.subheader("公開データタイプと実装状況")
    st.caption("Google Health が公開する全データタイプ。実装済みはこのアプリが同期する対象。")
    st.dataframe(inv.published, use_container_width=True, hide_index=True, height=600,
                 column_config={
                     "data_type": st.column_config.TextColumn("データタイプ"),
                     "label": st.column_config.TextColumn("名称"),
                     "scope": st.column_config.TextColumn("スコープ"),
                     "implemented": st.column_config.CheckboxColumn("実装済み"),
                     "metrics": st.column_config.TextColumn("メトリクス"),
                     "method": st.column_config.TextColumn("取得方法"),
                     "last_synced": st.column_config.TextColumn("最終同期日"),
                     "status": st.column_config.TextColumn("状態"),
                 })

    st.subheader("保存済み系列")
    st.dataframe(inv.series, use_container_width=True, hide_index=True,
                 column_config={
                     "metric": st.column_config.TextColumn("系列"),
                     "table": st.column_config.TextColumn("テーブル"),
                     "n": st.column_config.NumberColumn("件数"),
                     "first_date": st.column_config.DateColumn("開始日"),
                     "last_date": st.column_config.DateColumn("最終日"),
                 })

    st.subheader("raw ページ")
    st.dataframe(inv.raw, use_container_width=True, hide_index=True,
                 column_config={
                     "metric": st.column_config.TextColumn("メトリクス"),
                     "n_pages": st.column_config.NumberColumn("ページ数"),
                     "first_range_start": st.column_config.DateColumn("範囲開始"),
                     "last_range_end": st.column_config.DateColumn("範囲終了"),
                 })
```

- [ ] **Step 2: App import check** (all views are now migrated)

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-google
ENVP uv run --no-sync python -c "
import sys
sys.path[:0] = ['health/app', 'health/src']
import common, main, theme
import views.activity_view, views.body_view, views.heart_view
import views.inventory_view, views.overview_view, views.sleep_view, views.sync_view
print('imports ok')"
```

Expected: `imports ok`.

- [ ] **Step 3: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/app && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/app
git add health/app/views/inventory_view.py
git commit -m "feat(health): inventory view with published/stored/raw sections"
```

---

### Task 11: seed_demo rewrite + probe script

**Files:**
- Rewrite: `health/scripts/seed_demo.py`
- Create: `health/scripts/probe_datatypes.py`
- Create: `health/tests/test_probe.py`

**Interfaces:**
- Produces: `seed_demo.py [target_data_dir]` (defaults to `health/data/`; never writes tokens). `probe_datatypes.py` pure helpers `probe_window(metric, today) -> (start, end)` and `page_summary(page) -> {"top_level_keys", "data_point_count"}`.

- [ ] **Step 1: Write the failing probe-helper tests** — create `health/tests/test_probe.py`:

```python
"""Pure-helper tests for scripts/probe_datatypes.py (no network)."""

import importlib.util
from datetime import date
from pathlib import Path

from health.endpoints import CATALOG

_spec = importlib.util.spec_from_file_location(
    "probe_datatypes",
    Path(__file__).parents[1] / "scripts" / "probe_datatypes.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def by_name(name):
    return next(m for m in CATALOG if m.name == name)


def test_probe_window_per_method():
    today = date(2026, 7, 22)
    assert probe.probe_window(by_name("steps"), today) == (date(2026, 7, 16), today)
    assert probe.probe_window(by_name("resting_hr"), today) == (date(2026, 6, 23), today)
    assert probe.probe_window(by_name("intraday_hr"), today) == (today, today)


def test_page_summary_counts_points_and_keys():
    page = {"dataPoints": [{"a": 1}], "nextPageToken": "t"}
    assert probe.page_summary(page) == {
        "top_level_keys": ["dataPoints", "nextPageToken"], "data_point_count": 1}


def test_page_summary_rollup_and_empty_pages():
    assert probe.page_summary({"rollupDataPoints": [{}, {}]}) == {
        "top_level_keys": ["rollupDataPoints"], "data_point_count": 2}
    assert probe.page_summary({}) == {"top_level_keys": [], "data_point_count": 0}
```

- [ ] **Step 2: Run to verify failure**

```bash
ENVP uv run --no-sync pytest health/tests/test_probe.py -q
```

Expected: FAIL (file `scripts/probe_datatypes.py` not found).

- [ ] **Step 3: Create `health/scripts/probe_datatypes.py`** with this exact content:

```python
"""Acceptance probe: fetch a narrow window per catalog metric, save raw pages.

Writes health/data/probe/<metric>/page-NNN.json plus manifest.json. Output
contains PRIVATE health data — it is gitignored; never commit it or copy real
values into test fixtures. Prints shape summaries only, never payload values.
Does not write to DuckDB.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from health.auth import GoogleHealthAuth
from health.client import ApiError, HealthClient, RequestBudget
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROBE_DIR = DATA_DIR / "probe"
ROLLUP_DAYS = 7
DAILY_RECONCILE_DAYS = 30
PROBE_BUDGET = 100


def probe_window(metric: Metric, today: date) -> tuple[date, date]:
    """Narrow acceptance range: rollup 7d, daily reconcile 30d, intraday 1d."""
    if metric.method == DAILY_ROLLUP:
        days = ROLLUP_DAYS
    elif not metric.full_history:
        days = 1
    else:
        days = DAILY_RECONCILE_DAYS
    return today - timedelta(days=days - 1), today


def page_summary(page: dict) -> dict:
    key = "rollupDataPoints" if "rollupDataPoints" in page else "dataPoints"
    points = page.get(key)
    count = len(points) if isinstance(points, list) else 0
    return {"top_level_keys": sorted(page), "data_point_count": count}


def main() -> None:
    auth = GoogleHealthAuth.from_env(DATA_DIR)
    client = HealthClient(auth)
    budget = RequestBudget(PROBE_BUDGET)
    today = date.today()
    manifest: dict[str, dict] = {}
    # AuthError deliberately propagates: expired auth stops the whole probe.
    for m in CATALOG:
        start, end = probe_window(m, today)
        entry = {"data_type": m.data_type, "method": m.method,
                 "start": start.isoformat(), "end": end.isoformat()}
        try:
            if m.method == DAILY_ROLLUP:
                pages = [client.daily_rollup(m, start, end, budget)]
            else:
                pages = list(client.iter_reconciled(m, start, end, budget))
        except ApiError as exc:
            entry |= {"status": "error", "page_count": 0, "data_point_count": 0,
                      "top_level_keys": [], "error_status": exc.status,
                      "error_message": exc.message}
            manifest[m.name] = entry
            print(f"{m.name}: ERROR HTTP {exc.status_code} {exc.status or ''}")
            continue
        out_dir = PROBE_DIR / m.name
        out_dir.mkdir(parents=True, exist_ok=True)
        keys: set[str] = set()
        n_points = 0
        for idx, page in enumerate(pages):
            (out_dir / f"page-{idx:03d}.json").write_text(json.dumps(page, indent=2))
            summary = page_summary(page)
            keys |= set(summary["top_level_keys"])
            n_points += summary["data_point_count"]
        entry |= {"status": "ok", "page_count": len(pages), "data_point_count": n_points,
                  "top_level_keys": sorted(keys), "error_status": None,
                  "error_message": None}
        manifest[m.name] = entry
        print(f"{m.name}: {len(pages)} pages, {n_points} points, keys={sorted(keys)}")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    (PROBE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("manifest:", PROBE_DIR / "manifest.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rewrite `health/scripts/seed_demo.py`** with this exact content:

```python
"""Seed a DuckDB with 90 days of plausible fake data (UI dev without credentials).

Usage: python scripts/seed_demo.py [target_data_dir]
Defaults to health/data/. Never writes tokens.
"""
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from health.store import Store

random.seed(7)
DATA_DIR = (Path(sys.argv[1]) if len(sys.argv) > 1
            else Path(__file__).resolve().parents[1] / "data")
store = Store(DATA_DIR / "health.duckdb")
today = date.today()

daily, sleep_rows = [], []
for i in range(90):
    d = today - timedelta(days=89 - i)
    ds = d.isoformat()
    steps = 6000 + 3000 * math.sin(i / 7) + random.randint(-1500, 1500)
    asleep = 380 + random.randint(-60, 60)
    spo2 = 96 + random.random()
    daily += [
        ("steps", ds, max(0, steps)),
        ("calories", ds, 1800 + steps * 0.04),
        ("distance_km", ds, steps * 0.0007),
        ("minutes_lightly_active", ds, random.randint(120, 260)),
        ("minutes_fairly_active", ds, random.randint(10, 45)),
        ("minutes_very_active", ds, random.randint(0, 60)),
        ("resting_hr", ds, 60 + 3 * math.sin(i / 14) + random.random()),
        ("hrv_rmssd", ds, 35 + 8 * math.sin(i / 10) + random.random() * 3),
        ("hrv_deep_rmssd", ds, 40 + 8 * math.sin(i / 10) + random.random() * 3),
        ("sleep_minutes", ds, asleep),
        ("spo2_avg", ds, spo2),
        ("spo2_lower_bound", ds, spo2 - 1.5 - random.random()),
        ("spo2_upper_bound", ds, spo2 + 1.0 + random.random()),
        ("weight_kg", ds, 72 - i * 0.01 + random.random() * 0.4),
        ("fat_pct", ds, 21 + math.sin(i / 20) + random.random() * 0.5),
        ("breathing_rate", ds, 15 + random.random()),
        ("temp_skin_relative", ds, random.random() - 0.5),
    ]
    # Bed time varies around 23:30 and crosses midnight every few nights.
    bed_minutes = 23 * 60 + 30 + random.randint(-40, 80)
    bed_day = d - timedelta(days=1) if bed_minutes < 24 * 60 else d
    bm = bed_minutes % (24 * 60)
    wake = 7 * 60 + random.randint(-30, 40)
    sleep_rows.append({
        "provider_id": f"users/me/dataTypes/sleep/dataPoints/demo-{i:03d}",
        "date": ds,
        "start_ts": f"{bed_day.isoformat()} {bm // 60:02d}:{bm % 60:02d}:00",
        "end_ts": f"{ds} {wake // 60:02d}:{wake % 60:02d}:00",
        "minutes_asleep": asleep,
        "minutes_deep": int(asleep * 0.18),
        "minutes_light": int(asleep * 0.55),
        "minutes_rem": int(asleep * 0.22),
        "minutes_wake": int(asleep * 0.05),
        "efficiency": random.randint(88, 97),
        "is_main": True,
    })
store.upsert_daily(daily)
store.upsert_sleep(sleep_rows)

intraday = []
for day_off in (0, 1):
    d = today - timedelta(days=day_off)
    intraday += [("hr", f"{d.isoformat()} {h:02d}:{mnt:02d}:00",
                  62 + 25 * math.exp(-((h - 18) ** 2) / 8) + random.random() * 4)
                 for h in range(24) for mnt in range(0, 60, 5)]
    intraday += [("steps", f"{d.isoformat()} {h:02d}:{mnt:02d}:00",
                  max(0.0, random.gauss(35, 30)) if 7 <= h <= 22 else 0.0)
                 for h in range(24) for mnt in range(0, 60, 5)]
store.upsert_intraday(intraday)

for name in ("steps", "sleep", "resting_hr", "intraday_hr", "intraday_steps"):
    store.set_sync_state(name, today)
print("seeded:", DATA_DIR / "health.duckdb")
```

- [ ] **Step 5: Run probe tests + seed smoke test in a temp dir**

```bash
ENVP uv run --no-sync pytest health/tests/test_probe.py -q
SEED_TMP=$(mktemp -d /tmp/health-seed-XXXX)
ENVP uv run --no-sync python health/scripts/seed_demo.py "$SEED_TMP"
ls -la "$SEED_TMP"
rm -rf "$SEED_TMP"
```

Expected: probe tests PASS; seed prints `seeded: .../health.duckdb`; no writes to `health/data/`.

- [ ] **Step 6: Lint + commit**

```bash
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/scripts health/tests && \
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/scripts health/tests
git add health/scripts/seed_demo.py health/scripts/probe_datatypes.py health/tests/test_probe.py
git commit -m "feat(health): acceptance probe script and google-era demo seed"
```

---

### Task 12: Documentation — README, CLAUDE.md, pyproject, .env.example

**Files:**
- Rewrite: `health/README.md`
- Rewrite: `health/CLAUDE.md`
- Modify: `health/pyproject.toml` (description only, if it mentions Fitbit)
- Modify: `health/src/health/__init__.py` (docstring only, if it mentions Fitbit)
- Modify: `health/.env.example` (attempt once; Read/Write may be permission-denied — if denied, skip and note it in the final report; README carries the canonical contents either way)

- [ ] **Step 1: Rewrite `health/README.md`** with this exact content:

````markdown
# health — Personal Google Health dashboard

Streamlit + Plotly + DuckDB. Google Health API v4 (OAuth 2.0 + PKCE, personal use).
Design: `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md`
(this app previously used the legacy Fitbit Web API, which Google shuts down in
September 2026).

## Google Cloud setup (one-time)

1. Create a Google Cloud project and enable the **Google Health API**.
2. OAuth consent screen: External / **Testing**; add yourself as a test user.
3. Data Access: add exactly these 3 scopes:
   - `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
   - `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
   - `https://www.googleapis.com/auth/googlehealth.sleep.readonly`
4. Credentials: create a **Web application** OAuth client with the exact
   redirect URI `http://localhost:8501/`.
5. Create `health/.env` (same shape as `health/.env.example`):

       GOOGLE_CLIENT_ID=...
       GOOGLE_CLIENT_SECRET=...
       # optional; default is 5 years back
       # HEALTH_BACKFILL_START=2021-01-01

6. From the workspace root: `uv sync --all-packages` (or `uv sync --package health`).

Note: in Testing mode Google may expire refresh tokens after ~7 days. The sync
page shows the remaining days only when the token response reports an expiry.

## Run

    uv run --no-sync streamlit run health/app/main.py

First visit: click "Google Health と接続する", authorize, land back in the app.
Then open 管理 > 同期 and press the sync button. One run sends at most 200 API
requests (progress is saved per chunk); press sync again to continue where it
stopped. A 429 rate limit shows the resume time.

## Acceptance probe

    uv run --no-sync python health/scripts/probe_datatypes.py

Fetches a narrow window per implemented metric into `health/data/probe/`
(**private health data — gitignored, never commit**) and writes
`manifest.json` with status / page counts / top-level keys per metric.

## Data

- `health/data/health.duckdb` — raw JSON pages + typed layer (`daily_series`,
  `sleep_sessions`, `intraday`, `sync_state`). Gitignored.
- `health/data/tokens.json` — OAuth tokens (mode 600). Gitignored. Use the
  接続解除 button on the sync page (or delete the file) to re-auth.

## UI dev without credentials

    uv run --no-sync python health/scripts/seed_demo.py

then create a dummy `health/data/tokens.json` (any JSON with `access_token`,
`refresh_token`, and a far-future `expires_at`); delete both afterwards.

## Tests

    uv run --no-sync pytest health/tests        # from workspace root
    cd health && uv run --no-sync pytest tests  # standalone (slim worktree venv)
````

- [ ] **Step 2: Rewrite `health/CLAUDE.md`** with this exact content:

```markdown
# health — Claude Code Guide

Personal Google Health dashboard. Respond in Japanese; code/identifiers/commits
in English.

- Layers: `src/health/` core (endpoints → auth/client → store → sync →
  inventory), `app/` thin Streamlit UI. Keep API/IO out of views; views read
  via cached loaders in `app/common.py`; chart chrome (light/dark palette)
  lives in `app/theme.py`.
- `endpoints.py` CATALOG is the single source of truth for metrics. New metric
  = new `Metric` entry + parser + (usually) nothing else — store/sync are
  generic.
- Sync invariants: per-metric `sync_state` watermark, trailing 2-day refetch,
  hard cap 200 requests/run, `Store.replace_chunk` transactional replacement
  (raw pages + typed rows + watermark move together). The engine never sleeps
  or retries — pacing and the one-shot 401 retry live in `client.py`.
- No live API in tests. HTTP is faked via `tests/fakes.py`; fixtures are
  invented values shaped like the official schemas. Probe output under
  `data/probe/` is real private data — never commit it or copy it into
  fixtures.
- Tests: `cd health && uv run --no-sync pytest tests` (worktree) or
  `uv run --no-sync pytest health/tests` (workspace root).
- UI dev without credentials: `uv run --no-sync python health/scripts/seed_demo.py`
  then create a dummy `data/tokens.json`; delete both afterwards.
- `data/` is gitignored (DuckDB + tokens + probe). Never commit tokens or `.env`.
```

- [ ] **Step 3: Update `health/pyproject.toml` description and `health/src/health/__init__.py` docstring** — read each; if they mention Fitbit, replace with `Personal Google Health dashboard (Streamlit + DuckDB)` wording. Attempt `health/.env.example` once with:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
# optional; default is 5 years back
# HEALTH_BACKFILL_START=2021-01-01
```

If the permission system denies the read/write, skip and note it in the final report.

- [ ] **Step 4: Stale-reference check**

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-google
grep -rn "FITBIT_\|FitbitAuth\|FitbitClient\|api.fitbit.com\|dev.fitbit.com" \
  health/src health/app health/scripts health/tests health/README.md health/CLAUDE.md || echo "no stale refs"
```

Expected: `no stale refs` (migration-history mention of "Fitbit Web API" in README prose is allowed — the patterns above target env vars, class names, and URLs only).

- [ ] **Step 5: Commit**

```bash
git add health/README.md health/CLAUDE.md health/pyproject.toml health/src/health/__init__.py
git add health/.env.example 2>/dev/null || true
git commit -m "docs(health): google health setup, invariants, env template"
```

---

### Task 13: Final validation and merge

**Files:** none (verification + git)

- [ ] **Step 1: Full suite + lint + format + import check**

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-google
ENVP uv run --no-sync pytest health/tests -q
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff check health/src health/app health/scripts health/tests
UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
ENVP uv run --no-sync python -c "
import sys
sys.path[:0] = ['health/app', 'health/src']
import common, main, theme
import views.activity_view, views.body_view, views.heart_view
import views.inventory_view, views.overview_view, views.sleep_view, views.sync_view
print('imports ok')"
```

Expected: all tests pass (≈180), ruff clean, `imports ok`.

- [ ] **Step 2: Seeded headless boot smoke test** (temp data dir + dummy tokens so the nav renders; nothing under `health/data/` is touched)

```bash
SMOKE=$(mktemp -d /tmp/health-smoke-XXXX)
ENVP uv run --no-sync python health/scripts/seed_demo.py \
  --db-path "$SMOKE/health.duckdb"
python3 - "$SMOKE" <<'EOF'
import json, sys, time
json.dump({"access_token": "x", "refresh_token": "y",
           "expires_at": time.time() + 86400, "scope": "demo"},
          open(sys.argv[1] + "/tokens.json", "w"))
EOF
# boot streamlit against the temp dir by overriding DATA_DIR via a shim
cat > /tmp/claude-1000/-home-kazumasa-projects/322d9e0a-9a7d-4be4-803a-30a0ff36a782/scratchpad/smoke_shim.py <<'EOF'
import pathlib, sys
sys.path[:0] = ["health/app", "health/src"]
import common
common.DATA_DIR = pathlib.Path(sys.argv.pop(1))
import main
main.main()
EOF
ENVP timeout 30 uv run --no-sync streamlit run \
  /tmp/claude-1000/-home-kazumasa-projects/322d9e0a-9a7d-4be4-803a-30a0ff36a782/scratchpad/smoke_shim.py \
  --server.headless true --server.port 8599 -- "$SMOKE" &
sleep 8 && curl -sf http://localhost:8599/ -o /dev/null && echo "boot ok"
wait; rm -rf "$SMOKE"
```

Expected: `boot ok`. (GOOGLE_CLIENT_ID/SECRET must be present in env or `health/.env` for `get_auth()`; if absent, export dummy values `GOOGLE_CLIENT_ID=x GOOGLE_CLIENT_SECRET=y` for the boot command.)

- [ ] **Step 3: Git hygiene**

```bash
git diff --check && git status --short
git log --oneline main..claude/health-google-migration
```

Expected: no whitespace errors; changes confined to `health/` and this plan file; task commits listed.

- [ ] **Step 4: Merge to main** (superpowers:finishing-a-development-branch)

```bash
cd /home/kazumasa/projects
git merge --no-ff claude/health-google-migration -m "Merge branch 'claude/health-google-migration': google health sync + UI overhaul"
uv run --no-sync pytest health/tests -q   # post-merge verification from main checkout
```

---

## Self-Review Notes

- Spec coverage: sync engine (§Sync engine → Task 2), inventory (§Inventory → Tasks 3/10), UI changes (§UI changes → Tasks 5–10: provider wording, OAuth denial, refresh expiry display, reconnect, spo2 lower/upper, classic-sleep notice, cap/429 display), probe (§Probe → Task 11), sleep_minutes series (catalog table → Task 1), docs (Task 12). Review items: A1–A5 (Tasks 2–5, 11), B1–B5 (Tasks 1, 5, 9, 12), C1–C4 (Tasks 6–8), D items (Tasks 4–10).
- Final type consistency (see post-review correction above): `SyncEngine(client, store, catalog, today, environ, max_requests)` matches all call sites; `build_inventory()` and `build_series_inventory()` each return the DataFrame consumed by `inventory_view`; `palette()["categorical"]` / `style(fig, p)` are consumed identically in all views; `load_daily(tuple)` is used everywhere (never list — cache hashing).
- Known deviation from plan-a: progress_cb keeps the `(metric, msg)` 2-arg shape (request count folded into msg) so `st.status` wiring stays one line.
