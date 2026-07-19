# Health: Fitbit Personal Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A personal Streamlit dashboard for Fitbit data (sleep / activity / heart / body) with in-app OAuth2 auth and a resumable in-app sync button, backed by DuckDB.

**Architecture:** Layered mini-package `health` (new uv workspace member): `endpoints.py` (metric catalog + parsers) → `client.py`/`auth.py` (HTTP + OAuth2 PKCE) → `store.py` (DuckDB) → `sync.py` (resumable engine) → thin Streamlit UI in `app/`. Core is fully testable with fake sessions/clients; no HTTP-mocking library needed.

**Tech Stack:** Python ≥3.12, streamlit, plotly, duckdb, pandas, requests, python-dotenv, pytest. Spec: `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`.

## Global Constraints

- **Workspace:** uv workspace at `/home/kazumasa/projects`. The main checkout has uncommitted johnhull work on `codex/johnhull-inflation-jgbi` — do NOT switch branches there. All work happens in a git worktree:
  `git -C /home/kazumasa/projects worktree add .claude/worktrees/health-fitbit-v1 -b claude/health-fitbit-v1 main`
  Worktree root below: `WT = /home/kazumasa/projects/.claude/worktrees/health-fitbit-v1`. All file paths in tasks are relative to `WT`.
- **Env:** inside `WT`, run `uv sync --package health` once (creates a slim `WT/.venv` with only health's deps — avoids the 2.5 GB torch resolution). Never run plain `uv sync` in the worktree.
- **Tests during development:** run from `WT/health` so pytest's rootdir is `health/` and the workspace-root `conftest.py` (which imports gto/quantkit, absent from the slim venv) is not loaded:
  `cd WT/health && uv run --no-sync pytest tests -v`
- **Language:** code, identifiers, commits in English. Streamlit UI labels in Japanese.
- **Commits:** small, per task. Append this trailer to every commit message:
  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011b3F76ZJJXGstFzyki1PF9
  ```
- **Charts:** before writing any Plotly view code (Task 9), invoke the `dataviz` skill and follow its palette/mark rules.
- **Fitbit API facts used here** (verify against responses during implementation; adjust `max_range_days` down if the API rejects a range): rate limit 150 req/h/user via `Fitbit-Rate-Limit-Remaining`/`-Reset` headers; access token TTL 8 h; refresh tokens rotate; range limits — activity series 1095 d, heart 365 d, sleep 100 d, weight log 31 d, hrv/spo2/temp/br 30 d.
- **Known spec deviations:** (1) the Fitbit public API does not expose the app's "sleep score"; we store `efficiency` instead. (2) The typed layer is one long table `daily_series(metric, date, value)` rather than per-domain wide tables; UI reads pivots via `Store.daily_frame`. (3) The exercise-log table (activities list API) is deferred from v1 — it uses a different pagination model (`afterDate`/`offset`) than the range/per-day catalog; active-minutes series cover the activity view initially. Add later as a new `Metric` kind if wanted.

---

### Task 1: Worktree, spec commit, project scaffold

**Files:**
- Create: `health/pyproject.toml`, `health/src/health/__init__.py`, `health/.gitignore`, `health/.env.example`, `health/README.md`
- Modify: `pyproject.toml` (root: members, testpaths), `conftest.py` (root: import)
- Commit: `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`

**Interfaces:**
- Produces: importable empty package `health`; workspace member registration all later tasks rely on.

- [ ] **Step 1: Create worktree and commit the spec**

```bash
git -C /home/kazumasa/projects worktree add .claude/worktrees/health-fitbit-v1 -b claude/health-fitbit-v1 main
cd /home/kazumasa/projects/.claude/worktrees/health-fitbit-v1
cp /home/kazumasa/projects/docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md docs/superpowers/specs/
git add docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md
git commit -m "docs(health): fitbit dashboard design spec"   # + trailer
rm /home/kazumasa/projects/docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md
```

Expected: worktree on branch `claude/health-fitbit-v1`; spec committed there; untracked copy removed from the main checkout.

- [ ] **Step 2: Write scaffold files**

`health/pyproject.toml`:

```toml
[project]
name = "health"
version = "0.1.0"
description = "Personal Fitbit dashboard (Streamlit + Plotly + DuckDB)"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.45",
    "plotly>=6.0",
    "duckdb>=1.1",
    "pandas>=2.2",
    "requests>=2.32",
    "python-dotenv>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/health"]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
addopts = "-ra --import-mode=importlib"
```

(The `[tool.pytest.ini_options]` section pins pytest's rootdir to `health/` for in-worktree runs, keeping the workspace-root conftest out of the slim venv's way.)

`health/src/health/__init__.py`:

```python
"""Personal Fitbit dashboard: OAuth2 client, DuckDB store, sync engine."""
```

`health/.gitignore`:

```
/data/
```

`health/.env.example`:

```
FITBIT_CLIENT_ID=
FITBIT_CLIENT_SECRET=
```

`health/README.md` (stub; completed in Task 10):

```markdown
# health — Personal Fitbit dashboard

Streamlit + Plotly + DuckDB. See `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`.

Setup/run/verify: see Task 10 of the plan until this README is completed.
```

- [ ] **Step 3: Register workspace member**

Root `pyproject.toml`: add `"health",` to `[tool.uv.workspace] members` (after `"autostock",`) and `"health/tests",` to `[tool.pytest.ini_options] testpaths` (after `"autostock/tests",`).

Root `conftest.py`: add `import health  # noqa: F401` to the import block (alphabetical position) and mention `health` in the docstring's project list (directory name equals package name, so it needs the namespace-shadow fix).

- [ ] **Step 4: Sync env and smoke-test import**

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-fitbit-v1
uv sync --package health
uv run --no-sync python -c "import health, streamlit, duckdb, plotly; print(health.__doc__)"
```

Expected: prints the package docstring; no ImportError.

- [ ] **Step 5: Commit**

```bash
git add health pyproject.toml conftest.py uv.lock
git commit -m "feat(health): scaffold fitbit dashboard workspace member"   # + trailer
```

---

### Task 2: Metric catalog and parsers (`endpoints.py`)

**Files:**
- Create: `health/src/health/endpoints.py`
- Test: `health/tests/test_endpoints.py`

**Interfaces:**
- Produces (used by store/sync/inventory/UI):
  - `API = "https://api.fitbit.com"`
  - `@dataclass(frozen=True) Metric(name: str, path: str, kind: str, max_range_days: int, scope: str, full_history: bool, parse: Callable[[Any], ParsedRows])` — `kind` is `"range"` (path has `{start}`/`{end}`) or `"per_day"` (path has `{date}`)
  - `@dataclass(frozen=True) ParsedRows(daily: tuple = (), sleep: tuple = (), intraday: tuple = ())` — `daily` items `(metric: str, date: "YYYY-MM-DD", value: float)`; `sleep` items dicts matching `sleep_sessions` columns; `intraday` items `(metric: str, ts: "YYYY-MM-DD HH:MM:SS", value: float)`
  - `chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]` (inclusive)
  - `CATALOG: list[Metric]` — names: `steps, distance, calories, minutes_very_active, minutes_fairly_active, minutes_lightly_active, heart, sleep, weight, hrv, spo2, temp_skin, br, intraday_hr, intraday_steps`

- [ ] **Step 1: Write the failing tests**

`health/tests/test_endpoints.py`:

```python
from datetime import date

from health.endpoints import CATALOG, ParsedRows, chunk_ranges


def by_name(name):
    return next(m for m in CATALOG if m.name == name)


def test_chunk_ranges_splits_inclusive():
    out = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert out == [
        (date(2026, 1, 1), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 10)),
    ]


def test_chunk_ranges_single_day():
    assert chunk_ranges(date(2026, 1, 1), date(2026, 1, 1), 30) == [
        (date(2026, 1, 1), date(2026, 1, 1))
    ]


def test_catalog_shape():
    names = [m.name for m in CATALOG]
    assert len(names) == len(set(names))
    for m in CATALOG:
        assert m.path.startswith("/")
        if m.kind == "range":
            assert "{start}" in m.path and "{end}" in m.path
        else:
            assert m.kind == "per_day" and "{date}" in m.path and m.max_range_days == 1


def test_parse_steps():
    payload = {"activities-steps": [{"dateTime": "2026-07-01", "value": "8123"}]}
    rows = by_name("steps").parse(payload)
    assert rows.daily == [("steps", "2026-07-01", 8123.0)]
    assert rows.sleep == () and rows.intraday == ()


def test_parse_heart_resting_and_zones():
    payload = {"activities-heart": [{
        "dateTime": "2026-07-01",
        "value": {"restingHeartRate": 62, "heartRateZones": [
            {"name": "Fat Burn", "minutes": 40},
            {"name": "Cardio", "minutes": 12},
        ]},
    }]}
    daily = dict((m, v) for m, d, v in by_name("heart").parse(payload).daily)
    assert daily["resting_hr"] == 62.0
    assert daily["hr_zone_fat_burn_min"] == 40.0
    assert daily["hr_zone_cardio_min"] == 12.0


def test_parse_heart_missing_resting_hr_skipped():
    payload = {"activities-heart": [{"dateTime": "2026-07-01", "value": {"heartRateZones": []}}]}
    metrics = [m for m, d, v in by_name("heart").parse(payload).daily]
    assert "resting_hr" not in metrics


def test_parse_sleep_sessions_and_daily():
    payload = {"sleep": [{
        "logId": 44, "dateOfSleep": "2026-07-01", "startTime": "2026-06-30T23:41:30.000",
        "endTime": "2026-07-01T07:05:30.000", "minutesAsleep": 402, "efficiency": 93,
        "isMainSleep": True,
        "levels": {"summary": {"deep": {"minutes": 80}, "light": {"minutes": 220},
                               "rem": {"minutes": 102}, "wake": {"minutes": 42}}},
    }]}
    rows = by_name("sleep").parse(payload)
    (s,) = rows.sleep
    assert s["log_id"] == 44 and s["minutes_deep"] == 80
    assert s["start_ts"] == "2026-06-30 23:41:30"
    assert rows.daily == [("sleep_minutes", "2026-07-01", 402.0)]


def test_parse_sleep_classic_log_defaults_stages_to_zero():
    payload = {"sleep": [{"logId": 45, "dateOfSleep": "2026-07-02",
                          "startTime": "2026-07-02T01:00:00.000",
                          "endTime": "2026-07-02T07:00:00.000",
                          "minutesAsleep": 330, "efficiency": 90, "isMainSleep": False}]}
    (s,) = by_name("sleep").parse(payload).sleep
    assert s["minutes_deep"] == 0 and s["is_main"] is False
    assert by_name("sleep").parse(payload).daily == []  # non-main sleep: no daily row


def test_parse_spo2_bare_list():
    payload = [{"dateTime": "2026-07-01", "value": {"avg": 96.1, "min": 93.0, "max": 98.4}}]
    daily = dict((m, v) for m, d, v in by_name("spo2").parse(payload).daily)
    assert daily == {"spo2_avg": 96.1, "spo2_min": 93.0, "spo2_max": 98.4}


def test_parse_weight_fat_optional():
    payload = {"weight": [{"date": "2026-07-01", "weight": 72.5, "fat": 21.1},
                          {"date": "2026-07-02", "weight": 72.1}]}
    daily = by_name("weight").parse(payload).daily
    assert ("weight_kg", "2026-07-01", 72.5) in daily
    assert ("fat_pct", "2026-07-01", 21.1) in daily
    assert ("weight_kg", "2026-07-02", 72.1) in daily
    assert not any(m == "fat_pct" and d == "2026-07-02" for m, d, v in daily)


def test_parse_intraday_hr():
    payload = {
        "activities-heart": [{"dateTime": "2026-07-01"}],
        "activities-heart-intraday": {"dataset": [{"time": "00:00:00", "value": 62},
                                                  {"time": "00:01:00", "value": 63}]},
    }
    rows = by_name("intraday_hr").parse(payload)
    assert rows.intraday[0] == ("hr", "2026-07-01 00:00:00", 62.0)
    assert len(rows.intraday) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_endpoints.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.endpoints'`

- [ ] **Step 3: Implement `health/src/health/endpoints.py`**

```python
"""Fitbit metric catalog: endpoint definitions, range chunking, payload parsers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

API = "https://api.fitbit.com"


@dataclass(frozen=True)
class ParsedRows:
    daily: Any = ()      # [(metric, "YYYY-MM-DD", value)]
    sleep: Any = ()      # [dict] matching sleep_sessions columns
    intraday: Any = ()   # [(metric, "YYYY-MM-DD HH:MM:SS", value)]


@dataclass(frozen=True)
class Metric:
    name: str
    path: str            # contains {start}/{end} (kind="range") or {date} (kind="per_day")
    kind: str
    max_range_days: int
    scope: str
    full_history: bool   # False: backfill only trailing 30 days
    parse: Callable[[Any], ParsedRows] = field(repr=False)


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=max_days - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def _series_parser(key: str, metric: str) -> Callable[[Any], ParsedRows]:
    def parse(payload: Any) -> ParsedRows:
        rows = [(metric, e["dateTime"], float(e["value"])) for e in payload.get(key, [])]
        return ParsedRows(daily=rows)
    return parse


_ZONES = {"Out of Range": "out_of_range", "Fat Burn": "fat_burn",
          "Cardio": "cardio", "Peak": "peak"}


def _parse_heart(payload: Any) -> ParsedRows:
    rows = []
    for e in payload.get("activities-heart", []):
        d, v = e["dateTime"], e.get("value") or {}
        if "restingHeartRate" in v:
            rows.append(("resting_hr", d, float(v["restingHeartRate"])))
        for z in v.get("heartRateZones", []):
            slug = _ZONES.get(z.get("name"))
            if slug and "minutes" in z:
                rows.append((f"hr_zone_{slug}_min", d, float(z["minutes"])))
    return ParsedRows(daily=rows)


def _parse_sleep(payload: Any) -> ParsedRows:
    daily, sessions = [], []
    for s in payload.get("sleep", []):
        summary = (s.get("levels") or {}).get("summary") or {}

        def mins(k: str) -> int:
            return int((summary.get(k) or {}).get("minutes", 0))

        sessions.append({
            "log_id": s["logId"], "date": s["dateOfSleep"],
            "start_ts": s["startTime"].replace("T", " ")[:19],
            "end_ts": s["endTime"].replace("T", " ")[:19],
            "minutes_asleep": int(s.get("minutesAsleep", 0)),
            "minutes_deep": mins("deep"), "minutes_light": mins("light"),
            "minutes_rem": mins("rem"), "minutes_wake": mins("wake"),
            "efficiency": int(s.get("efficiency", 0)),
            "is_main": bool(s.get("isMainSleep", False)),
        })
        if s.get("isMainSleep", False):
            daily.append(("sleep_minutes", s["dateOfSleep"], float(s.get("minutesAsleep", 0))))
    return ParsedRows(daily=daily, sleep=sessions)


def _parse_weight(payload: Any) -> ParsedRows:
    rows = []
    for e in payload.get("weight", []):
        rows.append(("weight_kg", e["date"], float(e["weight"])))
        if "fat" in e:
            rows.append(("fat_pct", e["date"], float(e["fat"])))
    return ParsedRows(daily=rows)


def _value_fields_parser(key: str | None, fields: dict[str, str]) -> Callable[[Any], ParsedRows]:
    """Parser for hrv/spo2/temp/br shapes: entries with dateTime + value{...}.

    key=None means the payload itself is the entry list (spo2).
    fields maps response field -> our metric name.
    """
    def parse(payload: Any) -> ParsedRows:
        entries = payload if key is None else payload.get(key, [])
        rows = []
        for e in entries:
            v = e.get("value") or {}
            for src, metric in fields.items():
                if v.get(src) is not None:
                    rows.append((metric, e["dateTime"], float(v[src])))
        return ParsedRows(daily=rows)
    return parse


def _intraday_parser(summary_key: str, dataset_key: str, metric: str) -> Callable[[Any], ParsedRows]:
    def parse(payload: Any) -> ParsedRows:
        summary = payload.get(summary_key, [])
        if not summary:
            return ParsedRows()
        d = summary[0]["dateTime"]
        rows = [(metric, f"{d} {e['time']}", float(e["value"]))
                for e in payload.get(dataset_key, {}).get("dataset", [])]
        return ParsedRows(intraday=rows)
    return parse


CATALOG: list[Metric] = [
    Metric("steps", "/1/user/-/activities/steps/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-steps", "steps")),
    Metric("distance", "/1/user/-/activities/distance/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-distance", "distance_km")),
    Metric("calories", "/1/user/-/activities/calories/date/{start}/{end}.json",
           "range", 1095, "activity", True, _series_parser("activities-calories", "calories")),
    Metric("minutes_very_active", "/1/user/-/activities/minutesVeryActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesVeryActive", "minutes_very_active")),
    Metric("minutes_fairly_active", "/1/user/-/activities/minutesFairlyActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesFairlyActive", "minutes_fairly_active")),
    Metric("minutes_lightly_active", "/1/user/-/activities/minutesLightlyActive/date/{start}/{end}.json",
           "range", 1095, "activity", True,
           _series_parser("activities-minutesLightlyActive", "minutes_lightly_active")),
    Metric("heart", "/1/user/-/activities/heart/date/{start}/{end}.json",
           "range", 365, "heartrate", True, _parse_heart),
    Metric("sleep", "/1.2/user/-/sleep/date/{start}/{end}.json",
           "range", 100, "sleep", True, _parse_sleep),
    Metric("weight", "/1/user/-/body/log/weight/date/{start}/{end}.json",
           "range", 31, "weight", True, _parse_weight),
    Metric("hrv", "/1/user/-/hrv/date/{start}/{end}.json",
           "range", 30, "heartrate", True,
           _value_fields_parser("hrv", {"dailyRmssd": "hrv_rmssd", "deepRmssd": "hrv_deep_rmssd"})),
    Metric("spo2", "/1/user/-/spo2/date/{start}/{end}.json",
           "range", 30, "oxygen_saturation", True,
           _value_fields_parser(None, {"avg": "spo2_avg", "min": "spo2_min", "max": "spo2_max"})),
    Metric("temp_skin", "/1/user/-/temp/skin/date/{start}/{end}.json",
           "range", 30, "temperature", True,
           _value_fields_parser("tempSkin", {"nightlyRelative": "temp_skin_relative"})),
    Metric("br", "/1/user/-/br/date/{start}/{end}.json",
           "range", 30, "respiratory_rate", True,
           _value_fields_parser("br", {"breathingRate": "breathing_rate"})),
    Metric("intraday_hr", "/1/user/-/activities/heart/date/{date}/1d/1min.json",
           "per_day", 1, "heartrate", False,
           _intraday_parser("activities-heart", "activities-heart-intraday", "hr")),
    Metric("intraday_steps", "/1/user/-/activities/steps/date/{date}/1d/1min.json",
           "per_day", 1, "activity", False,
           _intraday_parser("activities-steps", "activities-steps-intraday", "steps")),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_endpoints.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add health/src/health/endpoints.py health/tests/test_endpoints.py
git commit -m "feat(health): metric catalog, chunking, payload parsers"   # + trailer
```

---

### Task 3: DuckDB store (`store.py`)

**Files:**
- Create: `health/src/health/store.py`
- Test: `health/tests/test_store.py`

**Interfaces:**
- Consumes: row shapes from `endpoints.ParsedRows`.
- Produces (used by sync/inventory/UI):
  - `class Store: __init__(self, db_path: str | Path)` — connects, creates schema idempotently
  - `upsert_raw(endpoint: str, date_key: str, payload: Any) -> None`
  - `upsert_daily(rows) / upsert_sleep(rows) / upsert_intraday(rows) -> None` (iterables; empty ok)
  - `get_sync_state(metric: str) -> date | None`, `set_sync_state(metric: str, last_synced: date, status: str = "ok") -> None`
  - `sync_states() -> pd.DataFrame` (metric, last_synced_date, status)
  - `series_stats() -> pd.DataFrame` (metric, n, first_date, last_date)
  - `daily_frame(metrics: list[str]) -> pd.DataFrame` (columns: date + one per metric, wide)
  - `sleep_frame() -> pd.DataFrame` (all sleep_sessions, date-ordered)
  - `intraday_frame(metric: str, day: date) -> pd.DataFrame` (ts, value)
  - `close() -> None`

- [ ] **Step 1: Write the failing tests**

`health/tests/test_store.py`:

```python
from datetime import date

import pytest

from health.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_upsert_daily_idempotent(store):
    rows = [("steps", "2026-07-01", 100.0), ("steps", "2026-07-02", 200.0)]
    store.upsert_daily(rows)
    store.upsert_daily([("steps", "2026-07-02", 250.0)])  # overwrite
    df = store.daily_frame(["steps"])
    assert len(df) == 2
    # date dtype after duckdb->pandas may be datetime64 or object; compare as prefix
    mask = df["date"].astype(str).str.startswith("2026-07-02")
    assert df.loc[mask, "steps"].iloc[0] == 250.0


def test_daily_frame_missing_metric_gives_nan_column(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0)])
    df = store.daily_frame(["steps", "resting_hr"])
    assert "resting_hr" in df.columns and df["resting_hr"].isna().all()


def test_upsert_daily_empty_noop(store):
    store.upsert_daily([])
    assert store.daily_frame(["steps"]).empty


def test_sleep_roundtrip_idempotent(store):
    row = {"log_id": 1, "date": "2026-07-01", "start_ts": "2026-06-30 23:41:30",
           "end_ts": "2026-07-01 07:05:30", "minutes_asleep": 402, "minutes_deep": 80,
           "minutes_light": 220, "minutes_rem": 102, "minutes_wake": 42,
           "efficiency": 93, "is_main": True}
    store.upsert_sleep([row])
    store.upsert_sleep([row])
    assert len(store.sleep_frame()) == 1


def test_intraday_roundtrip(store):
    store.upsert_intraday([("hr", "2026-07-01 00:00:00", 62.0),
                           ("hr", "2026-07-01 00:01:00", 63.0),
                           ("hr", "2026-07-02 00:00:00", 60.0)])
    df = store.intraday_frame("hr", date(2026, 7, 1))
    assert len(df) == 2 and list(df["value"]) == [62.0, 63.0]


def test_sync_state_roundtrip(store):
    assert store.get_sync_state("steps") is None
    store.set_sync_state("steps", date(2026, 7, 1))
    store.set_sync_state("steps", date(2026, 7, 5))
    assert store.get_sync_state("steps") == date(2026, 7, 5)
    states = store.sync_states()
    assert list(states["metric"]) == ["steps"] and list(states["status"]) == ["ok"]


def test_series_stats(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0), ("steps", "2026-07-03", 2.0),
                        ("resting_hr", "2026-07-02", 60.0)])
    stats = store.series_stats().set_index("metric")
    assert stats.loc["steps", "n"] == 2
    assert str(stats.loc["steps", "first_date"]).startswith("2026-07-01")


def test_raw_upsert_idempotent(store):
    store.upsert_raw("steps", "2026-07-01_2026-07-02", {"a": 1})
    store.upsert_raw("steps", "2026-07-01_2026-07-02", {"a": 2})
    n = store.con.execute("SELECT count(*) FROM raw_json").fetchone()[0]
    assert n == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.store'`

- [ ] **Step 3: Implement `health/src/health/store.py`**

```python
"""DuckDB store: raw payloads, typed layer, sync state."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_json(
    endpoint VARCHAR, date_key VARCHAR, fetched_at TIMESTAMP, payload JSON,
    PRIMARY KEY(endpoint, date_key));
CREATE TABLE IF NOT EXISTS daily_series(
    metric VARCHAR, date DATE, value DOUBLE, PRIMARY KEY(metric, date));
CREATE TABLE IF NOT EXISTS sleep_sessions(
    log_id BIGINT PRIMARY KEY, date DATE, start_ts TIMESTAMP, end_ts TIMESTAMP,
    minutes_asleep INT, minutes_deep INT, minutes_light INT, minutes_rem INT,
    minutes_wake INT, efficiency INT, is_main BOOLEAN);
CREATE TABLE IF NOT EXISTS intraday(
    metric VARCHAR, ts TIMESTAMP, value DOUBLE, PRIMARY KEY(metric, ts));
CREATE TABLE IF NOT EXISTS sync_state(
    metric VARCHAR PRIMARY KEY, last_synced_date DATE, status VARCHAR,
    updated_at TIMESTAMP);
"""

_SLEEP_COLS = ["log_id", "date", "start_ts", "end_ts", "minutes_asleep", "minutes_deep",
               "minutes_light", "minutes_rem", "minutes_wake", "efficiency", "is_main"]


class Store:
    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(db_path))
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                self.con.execute(stmt)

    def close(self) -> None:
        self.con.close()

    # -- writes ------------------------------------------------------------
    def upsert_raw(self, endpoint: str, date_key: str, payload: Any) -> None:
        self.con.execute(
            "INSERT INTO raw_json VALUES (?, ?, now(), ?) "
            "ON CONFLICT DO UPDATE SET payload = excluded.payload, fetched_at = now()",
            [endpoint, date_key, json.dumps(payload)])

    def upsert_daily(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO daily_series VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value", rows)

    def upsert_sleep(self, rows) -> None:
        for r in rows:
            self.con.execute(
                f"INSERT INTO sleep_sessions VALUES ({', '.join('?' * len(_SLEEP_COLS))}) "
                "ON CONFLICT DO UPDATE SET minutes_asleep = excluded.minutes_asleep, "
                "efficiency = excluded.efficiency",
                [r[c] for c in _SLEEP_COLS])

    def upsert_intraday(self, rows) -> None:
        rows = list(rows)
        if rows:
            self.con.executemany(
                "INSERT INTO intraday VALUES (?, ?, ?) "
                "ON CONFLICT DO UPDATE SET value = excluded.value", rows)

    # -- sync state --------------------------------------------------------
    def get_sync_state(self, metric: str) -> date | None:
        row = self.con.execute(
            "SELECT last_synced_date FROM sync_state WHERE metric = ?", [metric]).fetchone()
        return row[0] if row else None

    def set_sync_state(self, metric: str, last_synced: date, status: str = "ok") -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO sync_state VALUES (?, ?, ?, now())",
            [metric, last_synced, status])

    def sync_states(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, last_synced_date, status FROM sync_state ORDER BY metric").df()

    # -- reads -------------------------------------------------------------
    def series_stats(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, count(*) AS n, min(date) AS first_date, max(date) AS last_date "
            "FROM daily_series GROUP BY metric ORDER BY metric").df()

    def daily_frame(self, metrics: list[str]) -> pd.DataFrame:
        ph = ", ".join("?" * len(metrics))
        df = self.con.execute(
            f"SELECT date, metric, value FROM daily_series WHERE metric IN ({ph}) "
            "ORDER BY date", metrics).df()
        if df.empty:
            return pd.DataFrame(columns=["date", *metrics])
        wide = df.pivot(index="date", columns="metric", values="value").reset_index()
        for m in metrics:
            if m not in wide.columns:
                wide[m] = float("nan")
        return wide[["date", *metrics]]

    def sleep_frame(self) -> pd.DataFrame:
        return self.con.execute("SELECT * FROM sleep_sessions ORDER BY date").df()

    def intraday_frame(self, metric: str, day: date) -> pd.DataFrame:
        return self.con.execute(
            "SELECT ts, value FROM intraday WHERE metric = ? AND CAST(ts AS DATE) = ? "
            "ORDER BY ts", [metric, day]).df()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_store.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add health/src/health/store.py health/tests/test_store.py
git commit -m "feat(health): duckdb store with raw/typed layers and sync state"   # + trailer
```

---

### Task 4: OAuth2 PKCE auth (`auth.py`)

**Files:**
- Create: `health/src/health/auth.py`, `health/tests/fakes.py`
- Test: `health/tests/test_auth.py`

**Interfaces:**
- Produces (used by client/app):
  - `AUTHORIZE_URL`, `TOKEN_URL`, `SCOPES` (space-separated scope string)
  - `class AuthError(Exception)`
  - `class FitbitAuth: __init__(self, client_id: str, client_secret: str, data_dir: Path, redirect_uri: str = "http://localhost:8501/", session=None, clock=time.time)`
  - `FitbitAuth.from_env(data_dir: Path, env_path: Path | None = None) -> FitbitAuth` — loads `health/.env` (i.e. `data_dir.parent / ".env"`), needs `FITBIT_CLIENT_ID`/`FITBIT_CLIENT_SECRET`
  - `begin_auth() -> str` (authorize URL; persists verifier/state to `data_dir/oauth_pending.json`, reuses pending if present)
  - `complete_auth(code: str, state: str) -> None`
  - `refresh() -> dict`, `access_token() -> str`, `load_tokens() -> dict | None`
  - Token file `data_dir/tokens.json`, mode 600, keys: `access_token, refresh_token, expires_at, scope`
- `tests/fakes.py` produces (reused by Task 5):
  - `class FakeResponse(status_code=200, json_data=None, headers=None)` with `.json()`, `.headers`, `.raise_for_status()`
  - `class FakeSession` with `.queue: list[FakeResponse]`, `.calls: list[dict]`, and `get/post` popping the queue and recording `{"method", "url", "data", "auth", "headers"}`

- [ ] **Step 1: Write test fakes**

`health/tests/fakes.py`:

```python
"""Hand-rolled HTTP fakes (no mocking library in the workspace)."""


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, queue=None):
        self.queue = list(queue or [])
        self.calls = []

    def _record(self, method, url, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        return self.queue.pop(0)

    def get(self, url, headers=None, timeout=None):
        return self._record("GET", url, headers=headers)

    def post(self, url, data=None, auth=None, headers=None, timeout=None):
        return self._record("POST", url, data=data, auth=auth, headers=headers)
```

- [ ] **Step 2: Write the failing tests**

`health/tests/test_auth.py`:

```python
import json
import stat
from urllib.parse import parse_qs, urlparse

import pytest

from health.auth import TOKEN_URL, AuthError, FitbitAuth
from tests.fakes import FakeResponse, FakeSession


def make_auth(tmp_path, session=None, clock=lambda: 1000.0):
    return FitbitAuth("CID", "SECRET", tmp_path, session=session, clock=clock)


def token_payload(n=1):
    return {"access_token": f"AT{n}", "refresh_token": f"RT{n}",
            "expires_in": 28800, "scope": "activity"}


def test_begin_auth_builds_pkce_url_and_persists_pending(tmp_path):
    auth = make_auth(tmp_path)
    url = auth.begin_auth()
    q = parse_qs(urlparse(url).query)
    assert q["response_type"] == ["code"]
    assert q["code_challenge_method"] == ["S256"]
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    assert q["state"] == [pend["state"]]
    # second call reuses the pending verifier (the rendered link stays valid)
    assert auth.begin_auth() == url


def test_complete_auth_exchanges_code_and_saves_tokens(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload())])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    auth.complete_auth("THECODE", pend["state"])
    call = session.calls[0]
    assert call["url"] == TOKEN_URL and call["auth"] == ("CID", "SECRET")
    assert call["data"]["code"] == "THECODE"
    assert call["data"]["code_verifier"] == pend["verifier"]
    tokens = auth.load_tokens()
    assert tokens["access_token"] == "AT1" and tokens["expires_at"] == 1000.0 + 28800
    mode = stat.S_IMODE((tmp_path / "tokens.json").stat().st_mode)
    assert mode == 0o600
    assert not (tmp_path / "oauth_pending.json").exists()


def test_complete_auth_rejects_state_mismatch(tmp_path):
    auth = make_auth(tmp_path, session=FakeSession())
    auth.begin_auth()
    with pytest.raises(AuthError):
        auth.complete_auth("C", "WRONG_STATE")


def test_refresh_rotates_tokens(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    auth.refresh()
    assert session.calls[1]["data"] == {"grant_type": "refresh_token", "refresh_token": "RT1"}
    assert auth.load_tokens()["refresh_token"] == "RT2"


def test_refresh_failure_raises(tmp_path):
    session = FakeSession([FakeResponse(200, token_payload()), FakeResponse(401, {})])
    auth = make_auth(tmp_path, session=session)
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    with pytest.raises(AuthError):
        auth.refresh()


def test_access_token_refreshes_when_expired(tmp_path):
    now = [1000.0]
    session = FakeSession([FakeResponse(200, token_payload(1)),
                           FakeResponse(200, token_payload(2))])
    auth = make_auth(tmp_path, session=session, clock=lambda: now[0])
    auth.begin_auth()
    auth.complete_auth("C", json.loads((tmp_path / "oauth_pending.json").read_text())["state"])
    assert auth.access_token() == "AT1"
    now[0] = 1000.0 + 28800  # past expiry
    assert auth.access_token() == "AT2"


def test_access_token_without_tokens_raises(tmp_path):
    with pytest.raises(AuthError):
        make_auth(tmp_path).access_token()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.auth'`

- [ ] **Step 4: Implement `health/src/health/auth.py`**

```python
"""Fitbit OAuth2 (authorization code + PKCE) with rotating-refresh token store."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

AUTHORIZE_URL = "https://www.fitbit.com/oauth2/authorize"
TOKEN_URL = "https://api.fitbit.com/oauth2/token"
SCOPES = ("activity heartrate sleep weight oxygen_saturation "
          "respiratory_rate temperature profile")


class AuthError(Exception):
    pass


class FitbitAuth:
    def __init__(self, client_id: str, client_secret: str, data_dir: Path,
                 redirect_uri: str = "http://localhost:8501/",
                 session: Any = None, clock=time.time):
        self.client_id = client_id
        self.client_secret = client_secret
        self.data_dir = Path(data_dir)
        self.redirect_uri = redirect_uri
        self.session = session or requests.Session()
        self.clock = clock
        self.tokens_path = self.data_dir / "tokens.json"
        self.pending_path = self.data_dir / "oauth_pending.json"

    @classmethod
    def from_env(cls, data_dir: Path, env_path: Path | None = None) -> "FitbitAuth":
        load_dotenv(env_path or Path(data_dir).parent / ".env")
        cid = os.environ.get("FITBIT_CLIENT_ID")
        secret = os.environ.get("FITBIT_CLIENT_SECRET")
        if not cid or not secret:
            raise AuthError("FITBIT_CLIENT_ID / FITBIT_CLIENT_SECRET not set (health/.env)")
        return cls(cid, secret, Path(data_dir))

    # -- flow --------------------------------------------------------------
    def begin_auth(self) -> str:
        if self.pending_path.exists():
            pend = json.loads(self.pending_path.read_text())
        else:
            pend = {"verifier": secrets.token_urlsafe(64),
                    "state": secrets.token_urlsafe(16)}
            self._write_private(self.pending_path, pend)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(pend["verifier"].encode()).digest()).rstrip(b"=").decode()
        return AUTHORIZE_URL + "?" + urlencode({
            "response_type": "code", "client_id": self.client_id, "scope": SCOPES,
            "code_challenge": challenge, "code_challenge_method": "S256",
            "state": pend["state"], "redirect_uri": self.redirect_uri})

    def complete_auth(self, code: str, state: str) -> None:
        pend = json.loads(self.pending_path.read_text())
        if state != pend["state"]:
            raise AuthError("OAuth state mismatch")
        resp = self.session.post(TOKEN_URL, auth=(self.client_id, self.client_secret),
                                 data={"grant_type": "authorization_code",
                                       "client_id": self.client_id, "code": code,
                                       "code_verifier": pend["verifier"],
                                       "redirect_uri": self.redirect_uri},
                                 timeout=30)
        if resp.status_code != 200:
            raise AuthError(f"token exchange failed: HTTP {resp.status_code}")
        self._store_tokens(resp.json())
        self.pending_path.unlink()

    def refresh(self) -> dict:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Fitbit first")
        resp = self.session.post(TOKEN_URL, auth=(self.client_id, self.client_secret),
                                 data={"grant_type": "refresh_token",
                                       "refresh_token": tokens["refresh_token"]},
                                 timeout=30)
        if resp.status_code != 200:
            raise AuthError(f"token refresh failed: HTTP {resp.status_code}")
        return self._store_tokens(resp.json())

    def access_token(self) -> str:
        tokens = self.load_tokens()
        if tokens is None:
            raise AuthError("no tokens saved; connect Fitbit first")
        if tokens["expires_at"] <= self.clock() + 60:
            tokens = self.refresh()
        return tokens["access_token"]

    # -- storage -----------------------------------------------------------
    def load_tokens(self) -> dict | None:
        if not self.tokens_path.exists():
            return None
        return json.loads(self.tokens_path.read_text())

    def _store_tokens(self, payload: dict) -> dict:
        tokens = {"access_token": payload["access_token"],
                  "refresh_token": payload["refresh_token"],
                  "expires_at": self.clock() + payload.get("expires_in", 28800),
                  "scope": payload.get("scope", "")}
        self._write_private(self.tokens_path, tokens)
        return tokens

    def _write_private(self, path: Path, obj: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)  # atomic: rotating refresh tokens must never be half-written
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_auth.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add health/src/health/auth.py health/tests/fakes.py health/tests/test_auth.py
git commit -m "feat(health): oauth2 pkce auth with rotating token store"   # + trailer
```

---

### Task 5: API client (`client.py`)

**Files:**
- Create: `health/src/health/client.py`
- Test: `health/tests/test_client.py`

**Interfaces:**
- Consumes: `FitbitAuth.access_token() / refresh()`, `endpoints.API`.
- Produces (used by sync/app):
  - `class RateLimited(Exception)` with `.retry_after_s: int`
  - `class FitbitClient: __init__(self, auth: FitbitAuth, session=None)`
  - `FitbitClient.get(path: str) -> Any` — path like `/1/user/-/...json`; auto-refresh once on 401; raises `RateLimited` on 429
  - `FitbitClient.remaining: int | None`, `FitbitClient.reset_s: int | None` — from rate-limit headers, updated per request

- [ ] **Step 1: Write the failing tests**

`health/tests/test_client.py`:

```python
import json

import pytest

from health.auth import FitbitAuth
from health.client import FitbitClient, RateLimited
from tests.fakes import FakeResponse, FakeSession


def make_client(tmp_path, api_queue):
    auth_session = FakeSession([FakeResponse(200, {"access_token": "AT1", "refresh_token": "RT1",
                                                   "expires_in": 28800})])
    auth = FitbitAuth("CID", "SECRET", tmp_path, session=auth_session, clock=lambda: 0.0)
    auth.begin_auth()
    pend = json.loads((tmp_path / "oauth_pending.json").read_text())
    auth.complete_auth("C", pend["state"])
    return FitbitClient(auth, session=FakeSession(api_queue)), auth


def test_get_returns_json_and_tracks_budget(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"ok": 1},
                            headers={"Fitbit-Rate-Limit-Remaining": "42",
                                     "Fitbit-Rate-Limit-Reset": "1200"})])
    assert client.get("/1/user/-/profile.json") == {"ok": 1}
    assert client.remaining == 42 and client.reset_s == 1200
    call = client.session.calls[0]
    assert call["url"].endswith("/1/user/-/profile.json")
    assert call["headers"]["Authorization"] == "Bearer AT1"


def test_401_triggers_single_refresh_and_retry(tmp_path):
    client, auth = make_client(tmp_path, [FakeResponse(401, {}), FakeResponse(200, {"ok": 2})])
    auth.session.queue.append(FakeResponse(200, {"access_token": "AT2", "refresh_token": "RT2",
                                                 "expires_in": 28800}))
    assert client.get("/x.json") == {"ok": 2}
    assert client.session.calls[1]["headers"]["Authorization"] == "Bearer AT2"


def test_429_raises_rate_limited_with_reset(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(429, {}, headers={"Fitbit-Rate-Limit-Reset": "900"})])
    with pytest.raises(RateLimited) as exc:
        client.get("/x.json")
    assert exc.value.retry_after_s == 900


def test_http_error_propagates(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(500, {})])
    with pytest.raises(RuntimeError):
        client.get("/x.json")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.client'`

- [ ] **Step 3: Implement `health/src/health/client.py`**

```python
"""Thin Fitbit Web API client: auth header, auto-refresh, rate-limit tracking."""
from __future__ import annotations

from typing import Any

import requests

from health.auth import FitbitAuth
from health.endpoints import API


class RateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__(f"rate limited; retry after {retry_after_s}s")
        self.retry_after_s = retry_after_s


class FitbitClient:
    def __init__(self, auth: FitbitAuth, session: Any = None):
        self.auth = auth
        self.session = session or requests.Session()
        self.remaining: int | None = None
        self.reset_s: int | None = None

    def get(self, path: str) -> Any:
        resp = self._get(path)
        if resp.status_code == 401:
            self.auth.refresh()
            resp = self._get(path)
        if resp.status_code == 429:
            raise RateLimited(int(resp.headers.get("Fitbit-Rate-Limit-Reset", 3600)))
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str):
        resp = self.session.get(
            API + path,
            headers={"Authorization": f"Bearer {self.auth.access_token()}"},
            timeout=30)
        if "Fitbit-Rate-Limit-Remaining" in resp.headers:
            self.remaining = int(resp.headers["Fitbit-Rate-Limit-Remaining"])
            self.reset_s = int(resp.headers.get("Fitbit-Rate-Limit-Reset", 3600))
        return resp
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_client.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add health/src/health/client.py health/tests/test_client.py
git commit -m "feat(health): rate-limit-aware api client with auto refresh"   # + trailer
```

---

### Task 6: Resumable sync engine (`sync.py`)

**Files:**
- Create: `health/src/health/sync.py`
- Test: `health/tests/test_sync.py`

**Interfaces:**
- Consumes: `FitbitClient.get/remaining/reset_s`, `RateLimited`, `Store` write/state methods, `endpoints.CATALOG/chunk_ranges/Metric`.
- Produces (used by app):
  - `@dataclass MetricProgress(metric: str, fetched_ranges: int = 0, done: bool = False)`
  - `@dataclass SyncReport(progress: list[MetricProgress], paused: bool = False, resume_in_s: int | None = None)`
  - `class SyncEngine: __init__(self, client, store, catalog=CATALOG, today: date | None = None, member_since: date | None = None)` — `today` defaults to `date.today()`; `member_since` fetched from `/1/user/-/profile.json` (`user.memberSince`) on first `sync_all` if not given
  - `sync_all(progress_cb: Callable[[str, str], None] | None = None, min_budget: int = 5) -> SyncReport`
  - Behavior: full-history metrics backfill from `member_since`; trailing metrics from `today - 29d`; resume = `max(default_start, min(last_synced - 2d, today))` (the −2 d gives the trailing-3-day refetch); pause cleanly when budget `< min_budget` or on `RateLimited`.

- [ ] **Step 1: Write the failing tests**

`health/tests/test_sync.py`:

```python
from datetime import date

import pytest

from health.client import RateLimited
from health.endpoints import CATALOG, Metric, ParsedRows
from health.store import Store
from health.sync import SyncEngine


class FakeClient:
    """Scripted FitbitClient stand-in: returns {} and records paths."""

    def __init__(self, remaining=100, fail_after=None):
        self.calls = []
        self.remaining = remaining
        self.reset_s = 1800
        self.fail_after = fail_after  # raise RateLimited after N calls

    def get(self, path):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise RateLimited(900)
        self.calls.append(path)
        if path.endswith("/profile.json"):
            return {"user": {"memberSince": "2026-05-01"}}
        return {}


def steps_only():
    m = next(m for m in CATALOG if m.name == "steps")
    return [m]


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_backfill_uses_member_since_and_sets_state(store):
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20))
    report = engine.sync_all()
    assert client.calls[0].endswith("/profile.json")
    assert "/date/2026-05-01/2026-07-20.json" in client.calls[1]
    assert store.get_sync_state("steps") == date(2026, 7, 20)
    assert report.progress[0].done and not report.paused


def test_incremental_refetches_trailing_3_days(store):
    store.set_sync_state("steps", date(2026, 7, 19))
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all()
    assert "/date/2026-07-17/2026-07-20.json" in client.calls[0]


def test_up_to_date_metric_skips_requests(store):
    # fully synced through today: only the trailing refetch window remains
    store.set_sync_state("steps", date(2026, 7, 20))
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all()
    assert "/date/2026-07-18/2026-07-20.json" in client.calls[0]


def test_trailing_metric_starts_30_days_back(store):
    m = next(m for m in CATALOG if m.name == "intraday_hr")
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2020, 1, 1))
    engine.sync_all()
    assert "/date/2026-06-21/1d/1min.json" in client.calls[0]
    assert len(client.calls) == 30  # one per day
    assert store.get_sync_state("intraday_hr") == date(2026, 7, 20)


def test_budget_exhaustion_pauses_and_resumes(store):
    client = FakeClient(remaining=3)  # below min_budget after first check
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    report = engine.sync_all(min_budget=5)
    assert report.paused and report.resume_in_s == 1800
    assert client.calls == []  # stopped before any fetch


def test_rate_limited_mid_run_pauses_with_retry_after(store):
    m = next(m for m in CATALOG if m.name == "intraday_hr")
    client = FakeClient(fail_after=5)
    engine = SyncEngine(client, store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2020, 1, 1))
    report = engine.sync_all()
    assert report.paused and report.resume_in_s == 900
    # progress persisted: 5 days done -> resume window starts near there
    assert store.get_sync_state("intraday_hr") == date(2026, 6, 25)


def test_progress_callback_invoked(store):
    seen = []
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all(progress_cb=lambda metric, msg: seen.append((metric, msg)))
    assert seen and seen[0][0] == "steps"


def test_parsed_rows_are_stored(store):
    parsed = ParsedRows(daily=[("steps", "2026-07-19", 1.0)])
    m = Metric("steps", "/1/user/-/activities/steps/date/{start}/{end}.json",
               "range", 1095, "activity", True, lambda payload: parsed)
    engine = SyncEngine(FakeClient(), store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2026, 7, 1))
    engine.sync_all()
    assert not store.daily_frame(["steps"]).empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.sync'`

- [ ] **Step 3: Implement `health/src/health/sync.py`**

```python
"""Resumable backfill/incremental sync over the metric catalog."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import RateLimited
from health.endpoints import CATALOG, Metric, chunk_ranges
from health.store import Store

TRAILING_REFETCH_DAYS = 2   # re-fetch last_synced - 2d .. today (3-day window)
TRAILING_BACKFILL_DAYS = 29  # non-full-history metrics: today - 29d start


@dataclass
class MetricProgress:
    metric: str
    fetched_ranges: int = 0
    done: bool = False


@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    paused: bool = False
    resume_in_s: int | None = None


class SyncEngine:
    def __init__(self, client, store: Store, catalog: list[Metric] = CATALOG,
                 today: date | None = None, member_since: date | None = None):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.member_since = member_since

    def _fetch_member_since(self) -> date:
        payload = self.client.get("/1/user/-/profile.json")
        return date.fromisoformat(payload["user"]["memberSince"])

    def _start_date(self, m: Metric, member_since: date) -> date:
        default = member_since if m.full_history else (
            self.today - timedelta(days=TRAILING_BACKFILL_DAYS))
        last = self.store.get_sync_state(m.name)
        if last is None:
            return default
        return max(default, min(last - timedelta(days=TRAILING_REFETCH_DAYS), self.today))

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None,
                 min_budget: int = 5) -> SyncReport:
        report = SyncReport()
        member_since = self.member_since
        if member_since is None:
            member_since = self.member_since = self._fetch_member_since()
        for m in self.catalog:
            prog = MetricProgress(metric=m.name)
            report.progress.append(prog)
            start = self._start_date(m, member_since)
            for s, e in chunk_ranges(start, self.today, m.max_range_days):
                if self.client.remaining is not None and self.client.remaining < min_budget:
                    report.paused = True
                    report.resume_in_s = self.client.reset_s
                    return report
                path = m.path.format(start=s.isoformat(), end=e.isoformat(),
                                     date=s.isoformat())
                try:
                    payload = self.client.get(path)
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    return report
                self.store.upsert_raw(m.name, f"{s}_{e}", payload)
                rows = m.parse(payload)
                self.store.upsert_daily(rows.daily)
                self.store.upsert_sleep(rows.sleep)
                self.store.upsert_intraday(rows.intraday)
                self.store.set_sync_state(m.name, e)
                prog.fetched_ranges += 1
                if progress_cb:
                    progress_cb(m.name, f"{s} → {e}")
            prog.done = True
        return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_sync.py -v`
Expected: all PASS. Note for `test_rate_limited_mid_run_pauses_with_retry_after`: 5 fetched days starting 2026-06-21 → state 2026-06-25; if this assert fails by one day, re-check `chunk_ranges` off-by-one, not the test.

- [ ] **Step 5: Commit**

```bash
git add health/src/health/sync.py health/tests/test_sync.py
git commit -m "feat(health): resumable sync engine with rate-limit budgeting"   # + trailer
```

---

### Task 7: Data inventory (`inventory.py`)

**Files:**
- Create: `health/src/health/inventory.py`
- Test: `health/tests/test_inventory.py`

**Interfaces:**
- Consumes: `Store.series_stats() / sync_states()`, `endpoints.CATALOG`.
- Produces (used by UI):
  - `build_inventory(store: Store, catalog=CATALOG) -> pd.DataFrame` with columns `metric, source ("catalog"|"derived"), kind, scope, n_days, first_date, last_date, last_synced, status` — one row per catalog entry plus one per derived `daily_series` metric (e.g. `spo2_avg`), sorted by `metric`.

- [ ] **Step 1: Write the failing tests**

`health/tests/test_inventory.py`:

```python
from datetime import date

import pytest

from health.inventory import build_inventory
from health.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_inventory_lists_all_catalog_metrics_even_empty(store):
    inv = build_inventory(store)
    assert (inv["source"] == "catalog").sum() >= 15
    steps = inv[inv["metric"] == "steps"].iloc[0]
    assert steps["n_days"] == 0 and steps["last_synced"] is None


def test_inventory_merges_stats_and_state(store):
    store.upsert_daily([("spo2_avg", "2026-07-01", 96.0), ("spo2_avg", "2026-07-02", 95.5)])
    store.set_sync_state("spo2", date(2026, 7, 2))
    inv = build_inventory(store).set_index("metric")
    assert inv.loc["spo2", "status"] == "ok"
    assert inv.loc["spo2_avg", "source"] == "derived"
    assert inv.loc["spo2_avg", "n_days"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd health && uv run --no-sync pytest tests/test_inventory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.inventory'`

- [ ] **Step 3: Implement `health/src/health/inventory.py`**

```python
"""Data inventory: what the account actually has, per catalog and derived series."""
from __future__ import annotations

import pandas as pd

from health.endpoints import CATALOG, Metric
from health.store import Store


def build_inventory(store: Store, catalog: list[Metric] = CATALOG) -> pd.DataFrame:
    stats = store.series_stats().set_index("metric")
    states = store.sync_states().set_index("metric")

    def stat(idx, name, col, default):
        return idx.loc[name, col] if name in idx.index else default

    rows = []
    for m in catalog:
        rows.append({
            "metric": m.name, "source": "catalog", "kind": m.kind, "scope": m.scope,
            "n_days": int(stat(stats, m.name, "n", 0)),
            "first_date": stat(stats, m.name, "first_date", None),
            "last_date": stat(stats, m.name, "last_date", None),
            "last_synced": stat(states, m.name, "last_synced_date", None),
            "status": stat(states, m.name, "status", None),
        })
    catalog_names = {m.name for m in catalog}
    for name, row in stats.iterrows():
        if name not in catalog_names:
            rows.append({"metric": name, "source": "derived", "kind": "", "scope": "",
                         "n_days": int(row["n"]), "first_date": row["first_date"],
                         "last_date": row["last_date"], "last_synced": None, "status": None})
    return pd.DataFrame(rows).sort_values("metric").reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd health && uv run --no-sync pytest tests/test_inventory.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add health/src/health/inventory.py health/tests/test_inventory.py
git commit -m "feat(health): data inventory over catalog and derived series"   # + trailer
```

---

### Task 8: Streamlit shell — auth flow, sync view, inventory view

**Files:**
- Create: `health/app/common.py`, `health/app/main.py`, `health/app/views/__init__.py`, `health/app/views/sync_view.py`, `health/app/views/inventory_view.py`

**Interfaces:**
- Consumes: `FitbitAuth.from_env/begin_auth/complete_auth/load_tokens`, `FitbitClient`, `SyncEngine.sync_all`, `build_inventory`, `Store`.
- Produces: `app/common.py` with `DATA_DIR: Path` (=`health/data`), `get_store() -> Store` (cached), `get_auth() -> FitbitAuth` — main.py and all views import from `common`, never from `main` (under `streamlit run`, main.py is module `__main__`; importing it as `main` would execute the script a second time).

- [ ] **Step 1: Implement the app shell**

`health/app/views/__init__.py`: empty file.

`health/app/common.py`:

```python
"""Shared app context: paths and cached resources."""
from pathlib import Path

import streamlit as st

from health.auth import FitbitAuth
from health.store import Store

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@st.cache_resource
def get_store() -> Store:
    return Store(DATA_DIR / "health.duckdb")


def get_auth() -> FitbitAuth:
    return FitbitAuth.from_env(DATA_DIR)
```

`health/app/main.py`:

```python
"""Streamlit entry: OAuth callback handling, navigation."""
import streamlit as st

from health.auth import AuthError

from common import get_auth


def main() -> None:
    st.set_page_config(page_title="Health", page_icon="🏃", layout="wide")
    try:
        auth = get_auth()
    except AuthError as exc:
        st.error(f"設定エラー: {exc}")
        st.stop()

    qp = st.query_params
    if "code" in qp and auth.load_tokens() is None:
        try:
            auth.complete_auth(qp["code"], qp.get("state", ""))
            st.query_params.clear()
            st.success("Fitbit と接続しました")
        except AuthError as exc:
            st.error(f"認証に失敗しました: {exc}")

    if auth.load_tokens() is None:
        st.title("Health ダッシュボード")
        st.markdown(f"[Fitbit と接続する]({auth.begin_auth()})")
        st.caption("dev.fitbit.com の個人アプリ (Client ID/Secret) を health/.env に設定してから接続してください。")
        st.stop()

    from views.body_view import body_page
    from views.heart_view import heart_page
    from views.inventory_view import inventory_page
    from views.overview_view import overview_page
    from views.sleep_view import sleep_page
    from views.activity_view import activity_page
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

Note: Task 8 creates only `sync_view`/`inventory_view`; add temporary one-line stubs for the other five pages (each `def X_page(): st.info("Task 9 で実装")` in its own file) so navigation renders — Task 9 replaces them.

`health/app/views/sync_view.py`:

```python
"""Sync page: on-demand sync with progress, token status."""
from datetime import datetime

import streamlit as st

from health.client import FitbitClient
from health.sync import SyncEngine

from common import get_auth, get_store


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    store = get_store()

    tokens = auth.load_tokens()
    exp = datetime.fromtimestamp(tokens["expires_at"]).strftime("%H:%M") if tokens else "-"
    st.caption(f"アクセストークン有効期限: {exp} / スコープ: {tokens.get('scope', '') if tokens else '-'}")

    states = store.sync_states()
    if not states.empty:
        st.dataframe(states, use_container_width=True)

    if st.button("Fitbit からデータを同期", type="primary"):
        client = FitbitClient(auth)
        engine = SyncEngine(client, store)
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, msg: status.write(f"{metric}: {msg}"))
        if report.paused:
            mins = (report.resume_in_s or 3600) // 60 + 1
            st.warning(f"レート制限に達しました。進捗は保存済みです。約 {mins} 分後にもう一度同期してください。")
        else:
            st.success("同期が完了しました")
        st.rerun()
```

`health/app/views/inventory_view.py`:

```python
"""Inventory page: which metrics have data, ranges, sync status."""
import streamlit as st

from health.inventory import build_inventory

from common import get_store


def inventory_page() -> None:
    st.title("データ棚卸し")
    st.caption("カタログ上の全エンドポイントと、取得済み派生系列の一覧")
    inv = build_inventory(get_store())
    st.dataframe(inv, use_container_width=True, height=600)
```

- [ ] **Step 2: Run existing tests (no regression) and boot the app**

```bash
cd health && uv run --no-sync pytest tests -v && cd ..
cp health/.env.example health/.env   # placeholder values are fine for boot test
uv run --no-sync streamlit run health/app/main.py --server.headless true &
sleep 6 && curl -s localhost:8501 | grep -o '<title>[^<]*' ; kill %1
```

Expected: tests PASS; curl prints a `<title>Streamlit` (or similar) tag — app boots without traceback in the terminal. With empty `.env` values the page shows 設定エラー; that is correct behavior. (If port 8501 is busy, add `--server.port 8599` and curl that.)

- [ ] **Step 3: Commit**

```bash
git add health/app
git commit -m "feat(health): streamlit shell with oauth flow, sync and inventory pages"   # + trailer
```

---

### Task 9: Dashboard views (overview / sleep / activity / heart / body) + demo seed

**Files:**
- Create: `health/app/views/overview_view.py`, `health/app/views/sleep_view.py`, `health/app/views/activity_view.py`, `health/app/views/heart_view.py`, `health/app/views/body_view.py` (replacing Task 8 stubs), `health/scripts/seed_demo.py`

**Interfaces:**
- Consumes: `get_store()` from `app/common.py`, `Store.daily_frame/sleep_frame/intraday_frame`.
- Produces: page callables `overview_page, sleep_page, activity_page, heart_page, body_page` (names must match the Task 8 imports in `main.py`).

- [ ] **Step 0: Invoke the `dataviz` skill** (Global Constraints) and apply its palette/mark rules to all code below — adjust colors/templates accordingly; the code here shows structure and data wiring.

- [ ] **Step 1: Implement demo seed for credential-free UI verification**

`health/scripts/seed_demo.py`:

```python
"""Seed data/health.duckdb with 90 days of plausible fake data (UI dev without credentials)."""
import math
import random
from datetime import date, timedelta
from pathlib import Path

from health.store import Store

random.seed(7)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
store = Store(DATA_DIR / "health.duckdb")
today = date.today()

daily, sleep_rows = [], []
for i in range(90):
    d = today - timedelta(days=89 - i)
    ds = d.isoformat()
    steps = 6000 + 3000 * math.sin(i / 7) + random.randint(-1500, 1500)
    daily += [("steps", ds, max(0, steps)),
              ("calories", ds, 1800 + steps * 0.04),
              ("distance_km", ds, steps * 0.0007),
              ("minutes_very_active", ds, random.randint(0, 60)),
              ("resting_hr", ds, 60 + 3 * math.sin(i / 14) + random.random()),
              ("hrv_rmssd", ds, 35 + 8 * math.sin(i / 10) + random.random() * 3),
              ("sleep_minutes", ds, 380 + random.randint(-60, 60)),
              ("spo2_avg", ds, 96 + random.random()),
              ("weight_kg", ds, 72 - i * 0.01 + random.random() * 0.4),
              ("breathing_rate", ds, 15 + random.random()),
              ("temp_skin_relative", ds, random.random() - 0.5)]
    asleep = 380 + random.randint(-60, 60)
    sleep_rows.append({"log_id": 1000 + i, "date": ds,
                       "start_ts": f"{(d - timedelta(days=1)).isoformat()} 23:30:00",
                       "end_ts": f"{ds} 07:10:00", "minutes_asleep": asleep,
                       "minutes_deep": int(asleep * 0.18), "minutes_light": int(asleep * 0.55),
                       "minutes_rem": int(asleep * 0.22), "minutes_wake": int(asleep * 0.05),
                       "efficiency": random.randint(88, 97), "is_main": True})
store.upsert_daily(daily)
store.upsert_sleep(sleep_rows)
store.upsert_intraday([("hr", f"{today.isoformat()} {h:02d}:{mnt:02d}:00",
                        62 + 25 * math.exp(-((h - 18) ** 2) / 8) + random.random() * 4)
                       for h in range(24) for mnt in range(0, 60, 5)])
print("seeded:", DATA_DIR / "health.duckdb")
```

Run: `uv run --no-sync python health/scripts/seed_demo.py`
Expected: prints the seeded path.

- [ ] **Step 2: Implement the five views**

`health/app/views/overview_view.py`:

```python
"""Overview: today's cards + 30-day sparklines."""
import plotly.express as px
import streamlit as st

from common import get_store

METRICS = [("steps", "歩数", "{:,.0f}"), ("sleep_minutes", "睡眠(分)", "{:,.0f}"),
           ("resting_hr", "安静時心拍", "{:.0f}")]


def overview_page() -> None:
    st.title("概要")
    df = get_store().daily_frame([m for m, _, _ in METRICS]).tail(30)
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    cols = st.columns(len(METRICS))
    for col, (metric, label, fmt) in zip(cols, METRICS):
        series = df[metric].dropna()
        with col:
            if series.empty:
                st.metric(label, "-")
                continue
            delta = series.iloc[-1] - series.iloc[-2] if len(series) > 1 else None
            st.metric(label, fmt.format(series.iloc[-1]),
                      delta=fmt.format(delta) if delta is not None else None)
            fig = px.line(df, x="date", y=metric, height=120)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                              xaxis_visible=False, yaxis_visible=False)
            st.plotly_chart(fig, use_container_width=True, key=f"spark_{metric}")
```

`health/app/views/sleep_view.py`:

```python
"""Sleep: stage composition, duration trend, bed/wake scatter."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_store

STAGES = [("minutes_deep", "深い"), ("minutes_rem", "REM"),
          ("minutes_light", "浅い"), ("minutes_wake", "覚醒")]


def sleep_page() -> None:
    st.title("睡眠")
    sf = get_store().sleep_frame()
    sf = sf[sf["is_main"]].copy()
    if sf.empty:
        st.info("睡眠データがありません。")
        return
    days = st.slider("表示日数", 14, 180, 60, key="sleep_days")
    sf = sf.tail(days)

    long = sf.melt(id_vars=["date"], value_vars=[c for c, _ in STAGES],
                   var_name="stage", value_name="minutes")
    long["stage"] = long["stage"].map(dict(STAGES))
    st.subheader("ステージ構成")
    st.plotly_chart(px.bar(long, x="date", y="minutes", color="stage"),
                    use_container_width=True)

    st.subheader("睡眠時間トレンド（7日移動平均）")
    trend = sf[["date", "minutes_asleep"]].copy()
    trend["ma7"] = trend["minutes_asleep"].rolling(7).mean()
    st.plotly_chart(px.line(trend, x="date", y=["minutes_asleep", "ma7"]),
                    use_container_width=True)

    st.subheader("就寝・起床時刻")
    tt = pd.DataFrame({
        "date": sf["date"],
        "就寝": pd.to_datetime(sf["start_ts"]).dt.hour + pd.to_datetime(sf["start_ts"]).dt.minute / 60,
        "起床": pd.to_datetime(sf["end_ts"]).dt.hour + pd.to_datetime(sf["end_ts"]).dt.minute / 60,
    }).melt(id_vars="date", var_name="event", value_name="hour")
    st.plotly_chart(px.scatter(tt, x="date", y="hour", color="event"),
                    use_container_width=True)
```

`health/app/views/activity_view.py`:

```python
"""Activity: steps/calories trends, weekly heatmap."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_store


def activity_page() -> None:
    st.title("活動")
    df = get_store().daily_frame(
        ["steps", "calories", "distance_km", "minutes_very_active"])
    if df.empty:
        st.info("活動データがありません。")
        return
    days = st.slider("表示日数", 30, 365, 90, key="act_days")
    df = df.tail(days).copy()

    st.subheader("歩数（7日移動平均つき）")
    df["ma7"] = df["steps"].rolling(7).mean()
    fig = px.bar(df, x="date", y="steps")
    fig.add_scatter(x=df["date"], y=df["ma7"], mode="lines", name="7日平均")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("消費カロリー / 高強度アクティブ分")
    st.plotly_chart(px.line(df, x="date", y=["calories", "minutes_very_active"]),
                    use_container_width=True)

    st.subheader("週間ヒートマップ（歩数）")
    hm = df.copy()
    hm["date"] = pd.to_datetime(hm["date"])
    hm["weekday"] = hm["date"].dt.weekday
    hm["week"] = hm["date"].dt.strftime("%G-W%V")
    pivot = hm.pivot_table(index="weekday", columns="week", values="steps")
    labels = ["月", "火", "水", "木", "金", "土", "日"]
    pivot.index = [labels[i] for i in pivot.index]  # index by weekday number, not position
    st.plotly_chart(px.imshow(pivot, aspect="auto"), use_container_width=True)
```

`health/app/views/heart_view.py`:

```python
"""Heart: resting HR / HRV trends, intraday viewer."""
from datetime import date

import plotly.express as px
import streamlit as st

from common import get_store


def heart_page() -> None:
    st.title("心拍")
    store = get_store()
    df = store.daily_frame(["resting_hr", "hrv_rmssd"])
    if df.empty:
        st.info("心拍データがありません。")
        return

    st.subheader("安静時心拍（長期トレンド）")
    st.plotly_chart(px.line(df.dropna(subset=["resting_hr"]), x="date", y="resting_hr"),
                    use_container_width=True)

    st.subheader("HRV (RMSSD)")
    hrv = df.dropna(subset=["hrv_rmssd"])
    if hrv.empty:
        st.caption("HRV データなし（デバイス非対応の可能性）")
    else:
        st.plotly_chart(px.line(hrv, x="date", y="hrv_rmssd"), use_container_width=True)

    st.subheader("分単位心拍ビューア")
    day = st.date_input("日付", value=date.today(), key="hr_day")
    intra = store.intraday_frame("hr", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        st.plotly_chart(px.line(intra, x="ts", y="value", labels={"value": "bpm"}),
                        use_container_width=True)
```

`health/app/views/body_view.py`:

```python
"""Body: weight, SpO2, skin temp, breathing rate."""
import plotly.express as px
import streamlit as st

from common import get_store

PANELS = [(["weight_kg", "fat_pct"], "体重・体脂肪"),
          (["spo2_avg", "spo2_min", "spo2_max"], "SpO2"),
          (["temp_skin_relative"], "皮膚温（基準比）"),
          (["breathing_rate"], "呼吸数")]


def body_page() -> None:
    st.title("身体")
    df = get_store().daily_frame(sorted({m for ms, _ in PANELS for m in ms}))
    if df.empty:
        st.info("身体データがありません。")
        return
    for metrics, label in PANELS:
        sub = df[["date", *metrics]].dropna(how="all", subset=metrics)
        st.subheader(label)
        if sub.empty:
            st.caption("データなし（デバイス非対応の可能性）")
            continue
        st.plotly_chart(px.line(sub, x="date", y=metrics), use_container_width=True)
```

- [ ] **Step 3: Verify with seeded data**

```bash
uv run --no-sync python health/scripts/seed_demo.py
echo 'FITBIT_CLIENT_ID=dummy' > health/.env && echo 'FITBIT_CLIENT_SECRET=dummy' >> health/.env
uv run --no-sync streamlit run health/app/main.py
```

Expected: with dummy credentials the app still requires "connect" — temporarily bypass by writing a fake token file for UI dev:
`python -c "import json,time,pathlib; p=pathlib.Path('health/data'); p.mkdir(exist_ok=True); (p/'tokens.json').write_text(json.dumps({'access_token':'x','refresh_token':'x','expires_at':time.time()+9e9,'scope':'demo'}))"`
Then all five pages render seeded charts; sync page loads (do NOT press sync with fake tokens — it will show an auth error, which is acceptable). Delete `health/data/tokens.json` and `health/data/health.duckdb` after visual verification.

- [ ] **Step 4: Run full test suite (no regression)**

Run: `cd health && uv run --no-sync pytest tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add health/app/views health/scripts
git commit -m "feat(health): dashboard views for sleep/activity/heart/body + demo seed"   # + trailer
```

---

### Task 10: Docs, full-suite verification, acceptance

**Files:**
- Modify: `health/README.md`
- Create: `health/CLAUDE.md`

**Interfaces:**
- Consumes: everything; no new code.

- [ ] **Step 1: Write final README**

`health/README.md`:

```markdown
# health — Personal Fitbit dashboard

Streamlit + Plotly + DuckDB. Fitbit Web API (OAuth2 PKCE, personal app).
Spec: `docs/superpowers/specs/2026-07-20-health-fitbit-dashboard-design.md`.

## Setup (one-time)

1. Register a **Personal** app at <https://dev.fitbit.com/apps/new>
   - OAuth 2.0 Application Type: Personal
   - Callback URL: `http://localhost:8501/`
2. `cp health/.env.example health/.env` and fill `FITBIT_CLIENT_ID` / `FITBIT_CLIENT_SECRET`.
3. From the workspace root: `uv sync --all-packages` (or `uv sync --package health` in a worktree).

## Run

    uv run --no-sync streamlit run health/app/main.py

First visit: click "Fitbit と接続する", authorize, you land back in the app.
Then open 管理 > 同期 and press the sync button. Initial backfill may hit the
150 req/h rate limit — progress is saved; press sync again after the shown wait.

## Data

- `health/data/health.duckdb` — raw JSON + typed layer (`daily_series`,
  `sleep_sessions`, `intraday`, `sync_state`). Gitignored.
- `health/data/tokens.json` — OAuth tokens (mode 600). Gitignored. Delete to re-auth.

## Tests

    uv run --no-sync pytest health/tests        # from workspace root
    cd health && uv run --no-sync pytest tests  # standalone (slim worktree venv)
```

- [ ] **Step 2: Write `health/CLAUDE.md`**

```markdown
# health — Claude Code Guide

Personal Fitbit dashboard. Respond in Japanese; code/identifiers/commits in English.

- Layers: `src/health/` core (endpoints → auth/client → store → sync → inventory),
  `app/` thin Streamlit UI. Keep API/IO out of views; views read via `Store` frames.
- `endpoints.py` CATALOG is the single source of truth for metrics. New metric =
  new `Metric` entry + parser + (usually) nothing else — store/sync are generic.
- Sync is resumable by design: `sync_state` watermark per metric, trailing 3-day
  refetch, clean pause on rate limit. Don't add sleeps/retries inside the engine.
- Tests: `cd health && uv run --no-sync pytest tests` (worktree) or
  `uv run --no-sync pytest health/tests` (workspace root). HTTP is faked via
  `tests/fakes.py` — no live API in tests.
- UI dev without credentials: `uv run --no-sync python health/scripts/seed_demo.py`
  then create a dummy `data/tokens.json` (see plan Task 9); delete both afterwards.
- `data/` is gitignored (DuckDB + tokens). Never commit tokens or `.env`.
```

- [ ] **Step 3: Full verification**

```bash
cd health && uv run --no-sync pytest tests -v
```

Expected: all tests PASS (≈35+). Then boot check:

```bash
cd /home/kazumasa/projects/.claude/worktrees/health-fitbit-v1
uv run --no-sync streamlit run health/app/main.py --server.headless true &
sleep 6 && curl -s -o /dev/null -w "%{http_code}" localhost:8501; kill %1
```

Expected: `200`.

- [ ] **Step 4: Commit**

```bash
git add health/README.md health/CLAUDE.md
git commit -m "docs(health): README and agent guide"   # + trailer
```

- [ ] **Step 5: User acceptance (requires the user)**

The user must: register the dev.fitbit.com personal app, fill `health/.env`,
run the app, authorize, and run the first sync (possibly multiple rounds due to
rate limits). Acceptance = dashboard pages show their real data. Afterwards,
use superpowers:finishing-a-development-branch to decide merge/PR (note:
`main` merge will also need `uv sync --all-packages` in the main checkout so
root conftest's `import health` resolves).
```
