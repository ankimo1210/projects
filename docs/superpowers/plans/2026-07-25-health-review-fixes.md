# Health: Review Fixes (Safety, Sync, UX, Insights) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Act on every finding of the 2026-07-25 review of `health/`: make destructive mistakes impossible, make a full backfill actually reachable and useful from the first sync, and add the analysis layer that turns stored series into something worth opening.

**Architecture:** Four phases, executed in order. Phase 0 removes ways to damage private data (seed script, file modes, WAL). Phase 1 reworks the sync engine: per-metric error isolation, calendar-aligned chunk keys (so re-fetches replace instead of accumulate), a `backfilled_from` watermark column, and a two-pass "recent first, history afterwards" run. Phase 2 surfaces the new state in the UI, fixes doc drift, and adds CI. Phase 3 adds `health.analytics` (pure, tested functions) plus an insights page and data export.

**Tech Stack:** Python 3.12, Streamlit 1.51+, Plotly 6, DuckDB 1.5, pandas 2.2, pytest 8, ruff (line-length 100).

**Source review:** findings are recorded in this plan; there is no separate spec document. Prior plans: `2026-07-20-health-google-migration-plan-a.md`, `2026-07-22-health-google-migration-completion-and-ui.md` (both COMPLETE).

## Global Constraints

- Worktree: `/home/kazumasa/projects/.claude/worktrees/health-review-fixes`, branch `worktree-health-review-fixes`, branched from main at `1cc5f208`. **Run every command from that worktree root**, never from `/home/kazumasa/projects` (another session is working there on a different branch).
- The workspace venv is shared with the main checkout, so every command needs this worktree's `src` on `PYTHONPATH`. Full prefix, abbreviated `ENVP` below:
  ```
  UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv \
  PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-review-fixes/health/src \
  uv run --no-sync ...
  ```
- Baseline confirmed in this worktree before Task 1: `196 passed`.
- Run before every commit: `ENVP uv run --no-sync pytest health/tests -q`, `ENVP uv run --no-sync ruff check health/src health/app health/scripts health/tests`, `ENVP uv run --no-sync ruff format --check health/src health/app health/scripts health/tests`.
- **Never read, write, or delete `health/data/`, `health/.env`, or any real token file.** Every test writes to `tmp_path`. No live Google API call in any test; fixtures contain invented values only.
- UI copy in Japanese; code, identifiers, commit messages in English.
- ruff line-length 100, target py312.
- Commit after every task using the message given in that task.
- Verified environment facts this plan relies on (already checked, do not re-derive):
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` is supported and idempotent on DuckDB 1.5.3.
  - `INSERT ... ON CONFLICT DO UPDATE SET col = greatest(table.col, coalesce(excluded.col, table.col))` works, and `coalesce(excluded.col, table.col)` is how a `None` parameter means "leave unchanged".
  - `CHECKPOINT` removes the `.wal` file entirely.
  - `duckdb.connect()` creates the database file with mode `0644`.

---

## Phase 0 — Make private data hard to damage

### Task 1: `seed_demo.py` cannot overwrite the real database

**Review finding:** `scripts/seed_demo.py` defaults `--db-path` to `health/data/health.duckdb`. A bare `python scripts/seed_demo.py` mixes fake data into real health history. README warns; code does not.

**Files:**
- Modify: `health/scripts/seed_demo.py:14` (`DEFAULT_DB`), `health/scripts/seed_demo.py:100-105` (`main`)
- Create: `health/tests/test_seed_demo.py`
- Modify: `health/README.md:81-86`

**Interfaces:**
- Consumes: `seed(db_path: Path, today: date | None = None) -> None` (unchanged).
- Produces: `build_parser() -> argparse.ArgumentParser`, `main(argv: Sequence[str] | None = None) -> None`. `main` raises `SystemExit` when `--db-path` is missing, or when the target exists without `--force`.

- [ ] **Step 1: Write the failing test**

Create `health/tests/test_seed_demo.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HEALTH_DIR = Path(__file__).resolve().parents[1]
if str(HEALTH_DIR) not in sys.path:
    sys.path.insert(0, str(HEALTH_DIR))

from scripts.seed_demo import main  # noqa: E402


def test_db_path_is_required():
    with pytest.raises(SystemExit):
        main([])


def test_refuses_to_overwrite_an_existing_database(tmp_path):
    target = tmp_path / "health.duckdb"
    target.write_bytes(b"pretend this is real health data")

    with pytest.raises(SystemExit, match="refusing to overwrite"):
        main(["--db-path", str(target)])

    assert target.read_bytes() == b"pretend this is real health data"


def test_force_allows_overwriting(tmp_path):
    target = tmp_path / "health.duckdb"
    target.write_bytes(b"pretend this is real health data")

    main(["--db-path", str(target), "--force"])

    assert target.stat().st_size > 0
    assert target.read_bytes() != b"pretend this is real health data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_seed_demo.py -q`
Expected: FAIL — `main()` takes no arguments (`TypeError`).

- [ ] **Step 3: Write minimal implementation**

In `health/scripts/seed_demo.py`, delete the `DEFAULT_DB` constant and replace `main`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a DuckDB database with plausible fake Google Health data."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        required=True,
        help="target DuckDB path; use a temporary path, never health/data/health.duckdb",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the target if it already exists",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    # No default path and no silent overwrite: the only database this script is
    # ever pointed at by accident is the one holding real health history.
    if args.db_path.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite an existing database: {args.db_path} (--force)")
    if args.db_path.exists():
        args.db_path.unlink()
    seed(args.db_path)
    print(f"seeded: {args.db_path}")
```

Add `from collections.abc import Sequence` to the imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (199 passed — 196 existing plus 3 new).

- [ ] **Step 5: Update the README**

In `health/README.md`, replace the demo-seed paragraph with:

```markdown
UI開発用の架空DBは任意pathへ生成できます。`--db-path`は必須で、既存ファイルがある場合は
`--force`を付けない限り上書きしません。実データ（`health/data/health.duckdb`）を指定しないでください。

```bash
uv run --no-sync python health/scripts/seed_demo.py --db-path /tmp/health-demo.duckdb
```
```

- [ ] **Step 6: Commit**

```bash
git add health/scripts/seed_demo.py health/tests/test_seed_demo.py health/README.md
git commit -m "fix(health): require an explicit --db-path for seed_demo and refuse overwrites"
```

---

### Task 2: Private file modes for the database, data directory, and tokens

**Review finding:** `duckdb.connect()` creates `health.duckdb` mode `0644` even though it holds the health history; `data/` is not `0700`; `auth._write_private` chmods the temp file only *after* writing it, so the token exists briefly under the process umask.

**Files:**
- Modify: `health/src/health/store.py:51-57` (`Store.__init__`)
- Modify: `health/src/health/auth.py:220-225` (`_write_private`)
- Modify: `health/tests/test_store.py` (add one test), `health/tests/test_auth.py` (add two tests)

**Interfaces:**
- Consumes: `Store(db_path)`, `GoogleHealthAuth(client_id, client_secret, data_dir, ...)` (signatures unchanged).
- Produces: `Store._restrict_permissions(path: Path) -> None` (static). After `Store(...)` returns, the database file is `0600` and its parent directory is `0700`. After any `_write_private` call, the target file is `0600` and was never created more permissively.

- [ ] **Step 1: Write the failing tests**

Append to `health/tests/test_store.py`:

```python
def test_database_and_data_dir_are_private(tmp_path):
    data_dir = tmp_path / "data"
    db_path = data_dir / "health.duckdb"

    created = Store(db_path)
    try:
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(data_dir.stat().st_mode) == 0o700
    finally:
        created.close()
```

Add `import stat` at the top of `test_store.py`.

Append to `health/tests/test_auth.py`:

```python
def test_write_private_creates_the_temp_file_already_restricted(tmp_path, monkeypatch):
    modes: list[int] = []
    real_open = os.open

    def spy(path, flags, mode=0o777, *args, **kwargs):
        modes.append(mode)
        return real_open(path, flags, mode, *args, **kwargs)

    monkeypatch.setattr(os, "open", spy)
    auth = GoogleHealthAuth("id", "secret", tmp_path)

    auth._write_private(tmp_path / "secret.json", {"token": "x"})

    # The file must be born 0600 -- chmod-after-write leaves a window where the
    # token is readable under a permissive umask.
    assert 0o600 in modes


def test_write_private_result_is_0600_under_a_permissive_umask(tmp_path):
    auth = GoogleHealthAuth("id", "secret", tmp_path)
    target = tmp_path / "secret.json"
    previous = os.umask(0o000)
    try:
        auth._write_private(target, {"token": "x"})
    finally:
        os.umask(previous)

    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
```

Add `import os` and `import stat` to `test_auth.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_store.py::test_database_and_data_dir_are_private health/tests/test_auth.py -q -k "private or umask"`
Expected: FAIL — database mode is `0644`, `os.open` is never called by `_write_private`.

- [ ] **Step 3: Write minimal implementation**

`health/src/health/store.py` — add `import os` and rewrite `__init__`:

```python
    def __init__(self, db_path: str | Path):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        self.path = path
        self.con = duckdb.connect(str(path))
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                self.con.execute(stmt)
        self._restrict_permissions(path)

    @staticmethod
    def _restrict_permissions(path: Path) -> None:
        """DuckDB creates its files with the process umask (0644 in practice).
        The database and its write-ahead log hold the health history itself, so
        both are narrowed to owner-only as soon as they exist."""
        for candidate in (path, path.with_name(path.name + ".wal")):
            if candidate.exists():
                os.chmod(candidate, 0o600)
```

`health/src/health/auth.py` — rewrite `_write_private`:

```python
    def _write_private(self, path: Path, obj: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.data_dir, 0o700)
        tmp = path.with_suffix(".tmp")
        # Created 0600 by os.open rather than chmod-ed afterwards: a token must
        # never exist, even briefly, under a permissive umask.
        handle = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(handle, "w") as stream:
            json.dump(obj, stream)
        os.replace(tmp, path)  # atomic: never leave a half-written token/pending file
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (202 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/store.py health/src/health/auth.py health/tests/test_store.py health/tests/test_auth.py
git commit -m "fix(health): create database, data dir, and token files owner-only"
```

---

### Task 3: Checkpoint the WAL so a killed Streamlit process leaves a clean database

**Review finding:** `health/data/health.duckdb` is 12 KB while `health.duckdb.wal` is 1.5 MB — `Store.close()` has no caller because `get_store()` caches the connection for the process lifetime.

**Files:**
- Modify: `health/src/health/store.py` (add `checkpoint`, call it from `close`)
- Modify: `health/app/common.py:16-18` (`get_store`)
- Modify: `health/tests/test_store.py` (add one test)

**Interfaces:**
- Produces: `Store.checkpoint() -> None` — folds the WAL into the database file. `Store.close()` checkpoints first, then closes. `app.common.get_store()` registers `store.close` with `atexit`.

- [ ] **Step 1: Write the failing test**

Append to `health/tests/test_store.py`:

```python
def test_checkpoint_folds_the_wal_into_the_database(tmp_path):
    db_path = tmp_path / "health.duckdb"
    created = Store(db_path)
    try:
        created.upsert_daily([("steps", date(2026, 1, d + 1), float(d)) for d in range(31)])
        wal = db_path.with_name(db_path.name + ".wal")
        assert wal.exists()

        created.checkpoint()

        assert not wal.exists()
    finally:
        created.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_store.py::test_checkpoint_folds_the_wal_into_the_database -q`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'checkpoint'`.

- [ ] **Step 3: Write minimal implementation**

In `health/src/health/store.py`:

```python
    def checkpoint(self) -> None:
        """Fold the write-ahead log back into the database file. Streamlit keeps
        one cached connection for the whole process, so without an explicit
        checkpoint a killed app leaves the entire recent history in a .wal."""
        self.con.execute("CHECKPOINT")

    def close(self) -> None:
        self.checkpoint()
        self.con.close()
```

In `health/app/common.py`, add `import atexit` and:

```python
@st.cache_resource
def get_store() -> Store:
    store = Store(DATA_DIR / "health.duckdb")
    atexit.register(store.close)
    return store
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (203 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/store.py health/app/common.py health/tests/test_store.py
git commit -m "feat(health): checkpoint the DuckDB WAL on close and register an atexit close"
```

---

## Phase 1 — Sync engine

### Task 4: One failing metric no longer stops the whole sync

**Review finding:** `sync_all()` catches only `RateLimited` and `RequestCapExceeded`. An `ApiError` (403/404/5xx) or `PayloadError` aborts the run, so every metric after the failing one is never synced — while `probe.py` isolates exactly these errors per metric.

**Files:**
- Modify: `health/src/health/sync.py:1-147`
- Modify: `health/tests/test_sync.py`

**Interfaces:**
- Produces:
  - `MetricFailure(metric: str, kind: str, status_code: int | None, message: str)` — frozen dataclass, `kind` is `"api"` or `"payload"`.
  - `SyncReport.failures: list[MetricFailure]` (new field, defaults to empty).
- Behavior: `ApiError`/`PayloadError` record a failure and skip the rest of *that metric's* chunks; the run continues with the next metric. `AuthError` still propagates (every later request would fail identically). `RateLimited`/`RequestCapExceeded` still end the run immediately.

- [ ] **Step 1: Write the failing tests**

Append to `health/tests/test_sync.py`:

```python
class FailingClient(FakeClient):
    """Fails every send for one metric, succeeds for the others."""

    def __init__(self, failing_metric, error):
        super().__init__()
        self.failing_metric = failing_metric
        self.error = error

    def _send(self, method, metric_, start, end, budget, payload):
        if metric_.name == self.failing_metric:
            budget.consume()
            raise self.error
        return super()._send(method, metric_, start, end, budget, payload)


def test_api_error_isolates_one_metric_and_continues(store):
    client = FailingClient("first", ApiError(403, "insufficient scope", code=403))
    report = SyncEngine(
        client,
        store,
        [metric(name="first"), metric(name="second")],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()

    assert [f.metric for f in report.failures] == ["first"]
    assert report.failures[0].kind == "api"
    assert report.failures[0].status_code == 403
    assert [call[1] for call in client.calls] == ["second"]
    assert store.get_sync_state("second") == date(2026, 1, 1)
    assert store.get_sync_state("first") is None


def test_payload_error_isolates_one_metric_and_continues(store):
    def explode(_pages):
        raise PayloadError("first", "rollupDataPoint missing civilStartTime.date")

    report = SyncEngine(
        FakeClient(),
        store,
        [metric(name="first", parser=explode), metric(name="second")],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()

    assert [f.metric for f in report.failures] == ["first"]
    assert report.failures[0].kind == "payload"
    assert store.get_sync_state("second") == date(2026, 1, 1)


def test_auth_error_stops_the_whole_run(store):
    client = FailingClient("first", AuthError("token revoked"))

    with pytest.raises(AuthError):
        SyncEngine(
            client,
            store,
            [metric(name="first"), metric(name="second")],
            today=date(2026, 1, 1),
            environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        ).sync_all()

    assert store.get_sync_state("second") is None
```

Add to the imports of `test_sync.py`:

```python
from health.auth import AuthError
from health.client import ApiError, RateLimited, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, RECONCILE, Metric, ParsedRows, PayloadError
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_sync.py -q -k "isolates or stops_the_whole_run"`
Expected: FAIL — `ApiError` propagates out of `sync_all` (`report.failures` does not exist).

- [ ] **Step 3: Write minimal implementation**

In `health/src/health/sync.py`, import the errors and add the dataclass:

```python
from health.client import ApiError, RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric, PayloadError, chunk_ranges


@dataclass(frozen=True)
class MetricFailure:
    """One metric gave up for this run; the run continued with the others."""

    metric: str
    kind: str  # "api" or "payload"
    status_code: int | None
    message: str
```

Add the field to `SyncReport`:

```python
@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    failures: list[MetricFailure] = field(default_factory=list)
    paused: bool = False
    resume_in_s: int | None = None
    stopped_early: bool = False
    requests_made: int = 0
```

In the chunk loop of `sync_all`, extend the except clauses (order matters — `RateLimited` is a subclass of `ApiError` and must stay first):

```python
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    report.requests_made = budget.used
                    return report
                except RequestCapExceeded:
                    report.stopped_early = True
                    report.requests_made = budget.used
                    return report
                except ApiError as exc:
                    # One data type can be unavailable (403 for a scope never
                    # granted, 404 for a device that produces nothing) without
                    # saying anything about the next metric -- same isolation
                    # rule probe.py already uses.
                    report.failures.append(
                        MetricFailure(metric.name, "api", exc.status_code, exc.message)
                    )
                    break
                except PayloadError as exc:
                    report.failures.append(MetricFailure(metric.name, "payload", None, exc.detail))
                    break
```

Note: `AuthError` is deliberately not caught — it is raised by `HealthClient` only after a refresh and retry both failed, so every later request would fail the same way.

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (206 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/sync.py health/tests/test_sync.py
git commit -m "feat(health): isolate API and payload errors to one metric per sync run"
```

---

### Task 5: Calendar-aligned chunk keys stop `raw_json` from accumulating overlaps

**Review finding:** `replace_chunk` deletes raw pages by an exact `(range_start, range_end)` match, but the sync start date shifts every run (watermark − 2 days), so each run writes a new range key. Five consecutive daily syncs of one metric leave six `raw_json` rows, four of them overlapping duplicates.

**Fix:** chunk boundaries become a function of the calendar and `max_days` only — never of where a sync happens to start. The same calendar days always map to the same chunk key, so a re-fetch replaces its predecessor. Requests are clipped to `[floor, today]`; the stored key stays the full aligned chunk.

**Files:**
- Modify: `health/src/health/endpoints.py:84-93` (`chunk_ranges`), add `CHUNK_EPOCH` and `aligned_chunk`
- Modify: `health/src/health/store.py` (`replace_chunk` gains a `watermark` keyword)
- Modify: `health/src/health/sync.py` (clip requests, pass the watermark)
- Modify: `health/tests/test_endpoints.py`, `health/tests/test_sync.py`, `health/tests/test_store.py`

**Interfaces:**
- Produces:
  - `CHUNK_EPOCH: date = date(2000, 1, 1)`
  - `aligned_chunk(day: date, max_days: int) -> tuple[date, date]` — the fixed chunk containing `day`.
  - `chunk_ranges(start, end, max_days) -> list[tuple[date, date]]` — aligned chunks covering `[start, end]`; the first chunk may begin before `start` and the last may end after `end`.
  - `Store.replace_chunk(..., *, status: str = SYNC_OK, watermark: date | None = None)` — `watermark` is the date written to `sync_state.last_synced_date`; `None` means "use `end`".

- [ ] **Step 1: Write the failing tests**

Replace the three `chunk_ranges` tests in `health/tests/test_endpoints.py` with:

```python
def test_chunk_ranges_are_calendar_aligned_regardless_of_start():
    # Both spans touch the same calendar days, so they must produce the same keys.
    from_first = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    from_middle = chunk_ranges(date(2026, 1, 3), date(2026, 1, 10), 4)
    assert from_first == from_middle
    for start, end in from_first:
        assert (end - start).days == 3


def test_chunk_ranges_cover_the_span_without_gap_or_overlap():
    out = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert out[0][0] <= date(2026, 1, 1)
    assert out[-1][1] >= date(2026, 1, 10)
    for (_, prev_end), (next_start, _) in pairwise(out):
        assert next_start == date.fromordinal(prev_end.toordinal() + 1)


def test_aligned_chunk_is_identical_for_every_day_inside_it():
    start, end = aligned_chunk(date(2026, 1, 1), 90)
    assert start <= date(2026, 1, 1) <= end
    assert (end - start).days == 89
    day = start
    while day <= end:
        assert aligned_chunk(day, 90) == (start, end)
        day += timedelta(days=1)


def test_chunk_ranges_single_day_returns_the_containing_chunk():
    out = chunk_ranges(date(2026, 1, 1), date(2026, 1, 1), 30)
    assert len(out) == 1
    assert out[0][0] <= date(2026, 1, 1) <= out[0][1]


@pytest.mark.parametrize("max_days", [0, -1])
def test_chunk_ranges_invalid_max_days_raises(max_days):
    with pytest.raises(ValueError):
        chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), max_days)


@pytest.mark.parametrize("max_days", [0, -1])
def test_aligned_chunk_invalid_max_days_raises(max_days):
    with pytest.raises(ValueError):
        aligned_chunk(date(2026, 1, 1), max_days)
```

Add `aligned_chunk` to the `health.endpoints` import list and `from datetime import timedelta` in that test module.

Append the regression test to `health/tests/test_sync.py`:

```python
def test_daily_syncs_reuse_one_raw_chunk_key(store):
    """The review's finding: five daily syncs used to leave six raw rows."""
    m = metric(days=90)
    for offset in range(5):
        SyncEngine(
            FakeClient(),
            store,
            [m],
            today=date(2026, 7, 20) + timedelta(days=offset),
            environ={"HEALTH_BACKFILL_START": "2026-07-01"},
        ).sync_all()

    ranges = store.con.execute(
        "SELECT DISTINCT range_start, range_end FROM raw_json WHERE metric = 'test'"
    ).fetchall()
    assert len(ranges) == 1


def test_request_range_is_clipped_to_floor_and_today(store):
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-07-01"},
    ).sync_all()

    _, _, request_start, request_end = client.calls[0]
    assert request_start == date(2026, 7, 1)  # never older than the floor
    assert request_end == date(2026, 7, 20)  # never in the future
    assert store.get_sync_state("test") == date(2026, 7, 20)  # watermark is the clipped end
```

Add `from datetime import date, timedelta` to `test_sync.py`.

Update these existing `test_sync.py` expectations, which asserted watermark-derived request ranges (aligned chunks now start at the chunk boundary):

```python
def test_completed_metric_refetches_trailing_three_days(store):
    store.set_sync_state("test", date(2026, 7, 20))
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric()],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    # 2026-07-18 falls in the aligned 90-day chunk 2026-05-14..2026-08-11,
    # requested clipped to [chunk start, today].
    assert client.calls[0][2:] == (date(2026, 5, 14), date(2026, 7, 20))


def test_completed_metric_refetches_from_previous_watermark_on_next_day(store):
    store.set_sync_state("test", date(2026, 7, 19), SYNC_OK)
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric()],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    # 2026-07-17 falls in the same aligned chunk as 2026-07-18.
    assert client.calls[0][2:] == (date(2026, 5, 14), date(2026, 7, 20))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_endpoints.py health/tests/test_sync.py -q`
Expected: FAIL — `ImportError: cannot import name 'aligned_chunk'`, and `test_daily_syncs_reuse_one_raw_chunk_key` finds more than one range.

- [ ] **Step 3: Write minimal implementation**

`health/src/health/endpoints.py` — replace `chunk_ranges` and add the epoch:

```python
CHUNK_EPOCH = date(2000, 1, 1)


def aligned_chunk(day: date, max_days: int) -> tuple[date, date]:
    """The fixed calendar chunk containing `day`.

    Boundaries depend only on CHUNK_EPOCH and max_days -- never on where a
    sync happens to start -- so the same calendar days always map to the same
    (range_start, range_end) key. That is what lets a re-fetch replace its
    predecessor in raw_json instead of adding an overlapping row.
    """
    if max_days < 1:
        raise ValueError(f"max_days must be >= 1, got {max_days}")
    index = (day - CHUNK_EPOCH).days // max_days
    start = CHUNK_EPOCH + timedelta(days=index * max_days)
    return start, start + timedelta(days=max_days - 1)


def chunk_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    """Aligned chunks covering [start, end], contiguous and non-overlapping.

    The first chunk may begin before `start` and the last may end after `end`;
    callers clip their actual request range and keep the chunk key intact.
    """
    if max_days < 1:
        raise ValueError(f"max_days must be >= 1, got {max_days}")
    out: list[tuple[date, date]] = []
    cur = aligned_chunk(start, max_days)[0]
    while cur <= end:
        chunk_start, chunk_end = aligned_chunk(cur, max_days)
        out.append((chunk_start, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return out
```

`health/src/health/store.py` — `replace_chunk` gains `watermark`:

```python
    def replace_chunk(
        self,
        metric: Metric,
        start: date,
        end: date,
        payloads: Sequence[dict],
        rows: ParsedRows,
        *,
        status: str = SYNC_OK,
        watermark: date | None = None,
    ) -> None:
```

and step 6 becomes:

```python
            # 6. advance the watermark. `watermark` is the last day actually
            # requested: an aligned chunk key can extend past today, and a
            # future watermark would make the next run skip real days.
            con.execute(
                "INSERT INTO sync_state VALUES (?, ?, ?, now()) "
                "ON CONFLICT DO UPDATE SET last_synced_date = excluded.last_synced_date, "
                "status = excluded.status, updated_at = excluded.updated_at",
                [metric.name, end if watermark is None else watermark, status],
            )
```

`health/src/health/sync.py` — clip the request inside the chunk loop:

```python
            floor = self._initial_start(metric)
            for chunk_start, chunk_end in chunk_ranges(start, self.today, metric.max_range_days):
                # The chunk key is the aligned range; the request is clipped so
                # we never ask for days before the configured floor or after today.
                request_start = max(chunk_start, floor)
                request_end = min(chunk_end, self.today)
                try:
                    if metric.method == DAILY_ROLLUP:
                        payloads = [
                            self.client.daily_rollup(metric, request_start, request_end, budget)
                        ]
                    else:
                        payloads = list(
                            self.client.iter_reconciled(metric, request_start, request_end, budget)
                        )
                    rows = metric.parse_pages(payloads)
                    status = SYNC_OK if chunk_end >= self.today else SYNC_IN_PROGRESS
                    self.store.replace_chunk(
                        metric,
                        chunk_start,
                        chunk_end,
                        payloads,
                        rows,
                        status=status,
                        watermark=request_end,
                    )
```

and the progress callback reports the requested range:

```python
                    progress_cb(
                        metric.name,
                        f"{request_start} → {request_end} ({budget.used} requests)",
                    )
```

- [ ] **Step 4: Run the whole suite**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (211 passed).

These already-computed facts mean no *other* existing test needs an edit — if one of them fails, the implementation is wrong, not the expectation:
- `test_rollup_chunking`: aligned 14-day chunks over 2026-01-01..2026-01-31 are still 3, aligned 90-day chunks are still 1.
- every `days=1` test (`test_429_keeps_only_completed_chunks`, `test_hard_cap_between_rollup_chunks`, `test_second_run_resumes_at_first_unfinished_chunk`, `test_legacy_ok_checkpoint_becomes_resumable_after_first_overlap_chunk`): a one-day chunk is its own aligned chunk, so ranges are unchanged.
- `test_progress_callback_reports_metric_range_and_request_count`: the chunk is 2025-11-15..2026-02-12 but the request is clipped to `[floor, today]` = 2026-01-01..2026-01-01, and the callback reports the *request* range, so the message string is unchanged.
- `test_reconcile_buffers_all_pages_and_replaces_once`: 2026-01-01 with `days=90` is still one chunk and `chunk_end (2026-02-12) >= today` still yields `SYNC_OK`.

- [ ] **Step 5: Commit**

```bash
git add health/src/health/endpoints.py health/src/health/store.py health/src/health/sync.py health/tests
git commit -m "fix(health): calendar-align chunk keys so re-fetches replace raw pages"
```

---

### Task 6: `sync_state.backfilled_from` and a typed checkpoint

**Purpose:** the watermark is a single point, which cannot express "history reaches back to X while the newest day is Y". Task 7 needs both ends.

**Files:**
- Modify: `health/src/health/store.py` (schema, migration, upsert SQL, `SyncCheckpoint`, `sync_states`)
- Modify: `health/src/health/sync.py:82-95` (`_start_date` reads the dataclass)
- Modify: `health/tests/test_store.py`, `health/tests/test_sync.py`

**Interfaces:**
- Produces:
  - `SyncCheckpoint(last_synced: date, status: str, backfilled_from: date | None)` — frozen dataclass returned by `Store.get_sync_checkpoint(metric) -> SyncCheckpoint | None`.
  - `Store.replace_chunk(..., *, status: str | None = SYNC_OK, watermark: date | None = None, backfill_from: date | None = None)` — a `None` field leaves the stored value unchanged; `last_synced_date` never regresses; `backfilled_from` never grows.
  - `Store.sync_states()` gains a `backfilled_from` column.
- Consumes: `Store.get_sync_state`, `Store.set_sync_state` keep their current signatures.

- [ ] **Step 1: Write the failing tests**

Append to `health/tests/test_store.py`:

```python
def test_checkpoint_exposes_both_ends_of_the_covered_range(store):
    m = _metric("steps")
    store.replace_chunk(
        m, date(2026, 6, 1), date(2026, 8, 29), [], ParsedRows(),
        status=SYNC_OK, watermark=date(2026, 7, 25), backfill_from=date(2026, 6, 1),
    )

    checkpoint = store.get_sync_checkpoint("steps")

    assert checkpoint.last_synced == date(2026, 7, 25)
    assert checkpoint.status == SYNC_OK
    assert checkpoint.backfilled_from == date(2026, 6, 1)


def test_backward_chunk_lowers_backfill_without_touching_watermark_or_status(store):
    m = _metric("steps")
    store.replace_chunk(
        m, date(2026, 6, 1), date(2026, 8, 29), [], ParsedRows(),
        status=SYNC_OK, watermark=date(2026, 7, 25), backfill_from=date(2026, 6, 1),
    )

    store.replace_chunk(
        m, date(2026, 3, 3), date(2026, 5, 31), [], ParsedRows(),
        status=None, watermark=None, backfill_from=date(2026, 3, 3),
    )

    checkpoint = store.get_sync_checkpoint("steps")
    assert checkpoint.last_synced == date(2026, 7, 25)  # unchanged
    assert checkpoint.status == SYNC_OK  # unchanged
    assert checkpoint.backfilled_from == date(2026, 3, 3)  # extended backwards


def test_legacy_database_without_backfilled_from_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.duckdb"
    legacy = duckdb.connect(str(db_path))
    legacy.execute(
        "CREATE TABLE sync_state(metric VARCHAR PRIMARY KEY, last_synced_date DATE, "
        "status VARCHAR, updated_at TIMESTAMP)"
    )
    legacy.execute("INSERT INTO sync_state VALUES ('steps', DATE '2026-07-25', 'ok', now())")
    legacy.execute(
        "CREATE TABLE raw_json(metric VARCHAR, range_start DATE, range_end DATE, "
        "page_index INTEGER, fetched_at TIMESTAMP, payload JSON, "
        "PRIMARY KEY(metric, range_start, range_end, page_index))"
    )
    legacy.execute("INSERT INTO raw_json VALUES ('steps', DATE '2021-07-25', DATE '2021-10-22', 0, now(), '{}')")
    legacy.close()

    migrated = Store(db_path)
    try:
        # The oldest raw chunk ever fetched is exactly how far back history goes.
        assert migrated.get_sync_checkpoint("steps").backfilled_from == date(2021, 7, 25)
    finally:
        migrated.close()
```

Add `import duckdb` to `test_store.py` and, if the module does not already have one, a helper that returns a real catalog metric:

```python
def _metric(name: str) -> Metric:
    return next(item for item in CATALOG if item.name == name)
```

with `from health.endpoints import CATALOG, Metric, ParsedRows` in the imports.

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_store.py -q -k "checkpoint_exposes or backward_chunk or legacy_database"`
Expected: FAIL — `replace_chunk() got an unexpected keyword argument 'backfill_from'`.

- [ ] **Step 3: Write minimal implementation**

`health/src/health/store.py` — schema, migration, dataclass, upsert:

```python
_SCHEMA = """
...
CREATE TABLE IF NOT EXISTS sync_state(
    metric VARCHAR PRIMARY KEY, last_synced_date DATE, status VARCHAR,
    updated_at TIMESTAMP, backfilled_from DATE);
"""

# Applied after _SCHEMA on every open. Each statement must be idempotent: an
# existing database predates the column, a fresh one already has it.
_MIGRATIONS = [
    "ALTER TABLE sync_state ADD COLUMN IF NOT EXISTS backfilled_from DATE",
]

_SEED_BACKFILL_FROM_RAW = """
UPDATE sync_state SET backfilled_from = (
    SELECT min(range_start) FROM raw_json WHERE raw_json.metric = sync_state.metric)
WHERE backfilled_from IS NULL
"""


@dataclass(frozen=True)
class SyncCheckpoint:
    """Both ends of what a metric has covered, plus the forward-pass status."""

    last_synced: date
    status: str
    backfilled_from: date | None
```

In `__init__`, after the schema loop:

```python
        for stmt in _MIGRATIONS:
            self.con.execute(stmt)
        self.con.execute(_SEED_BACKFILL_FROM_RAW)
```

Replace the reads:

```python
    def get_sync_checkpoint(self, metric: str) -> SyncCheckpoint | None:
        row = self.con.execute(
            "SELECT last_synced_date, status, backfilled_from FROM sync_state WHERE metric = ?",
            [metric],
        ).fetchone()
        return SyncCheckpoint(row[0], row[1], row[2]) if row else None

    def get_sync_state(self, metric: str) -> date | None:
        checkpoint = self.get_sync_checkpoint(metric)
        return checkpoint.last_synced if checkpoint else None

    def set_sync_state(self, metric: str, last_synced: date, status: str = SYNC_OK) -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO sync_state (metric, last_synced_date, status, updated_at) "
            "VALUES (?, ?, ?, now())",
            [metric, last_synced, status],
        )

    def sync_states(self) -> pd.DataFrame:
        return self.con.execute(
            "SELECT metric, last_synced_date, status, backfilled_from FROM sync_state "
            "ORDER BY metric"
        ).df()
```

Replace step 6 of `replace_chunk` (signature gains `backfill_from: date | None = None` and `status` becomes `str | None = SYNC_OK`):

```python
            # 6. move the covered range. greatest/least keep the pair monotone:
            # a backward history chunk lowers backfilled_from and leaves the
            # forward watermark and status alone (its parameters are None),
            # while a stale forward chunk can never pull the watermark back.
            con.execute(
                "INSERT INTO sync_state (metric, last_synced_date, status, updated_at, "
                "backfilled_from) VALUES (?, ?, ?, now(), ?) "
                "ON CONFLICT DO UPDATE SET last_synced_date = greatest("
                "  sync_state.last_synced_date, "
                "  coalesce(excluded.last_synced_date, sync_state.last_synced_date)), "
                "status = coalesce(excluded.status, sync_state.status), "
                "updated_at = excluded.updated_at, "
                "backfilled_from = least("
                "  coalesce(sync_state.backfilled_from, excluded.backfilled_from), "
                "  coalesce(excluded.backfilled_from, sync_state.backfilled_from))",
                [
                    metric.name,
                    end if watermark is None else watermark,
                    status,
                    start if backfill_from is None else backfill_from,
                ],
            )
```

`health/src/health/sync.py` — `_start_date` reads the dataclass:

```python
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None:
            return initial
        if checkpoint.status == SYNC_IN_PROGRESS:
            return max(initial, checkpoint.last_synced + timedelta(days=1))
        return max(initial, checkpoint.last_synced - timedelta(days=TRAILING_REFETCH_DAYS))
```

- [ ] **Step 4: Run the whole suite and fix tuple-unpacking call sites**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (214 passed). Existing assertions of the form `store.get_sync_checkpoint("test")[1] == SYNC_IN_PROGRESS` must become `.status`, and `== (date(...), SYNC_IN_PROGRESS)` becomes two attribute assertions.

- [ ] **Step 5: Commit**

```bash
git add health/src/health/store.py health/src/health/sync.py health/tests
git commit -m "feat(health): track backfilled_from alongside the sync watermark"
```

---

### Task 7: Recent data first, history afterwards

**Review finding:** a five-year backfill needs 532+ requests against a 200-request cap, and the catalog-order walk means run #1 touches only 4 of 14 metrics — sleep, heart rate, and weight stay empty until the third press.

**Fix:** every run does a short recency pass over *all* metrics first (about 30 requests), then spends the remaining budget walking history backwards, one aligned chunk per metric per round.

**Files:**
- Modify: `health/src/health/sync.py`
- Modify: `health/tests/test_sync.py`

**Interfaces:**
- Produces:
  - `RECENT_WINDOW_DAYS = 7`
  - `SyncEngine.sync_all(progress_cb=None) -> SyncReport` (same signature; two internal passes)
  - `SyncReport.history_remaining: dict[str, int]` — metric name → aligned chunks still missing before the floor.
  - `SyncEngine.history_remaining(metric: Metric) -> int`
  - `SyncEngine._initial_start` is renamed `SyncEngine._floor` (same body, clearer role now that it bounds both passes), and `_start_date` becomes `_recent_start`. Task 5's chunk loop moves into `_fetch_chunk`/`_guarded`.
- Consumes: `aligned_chunk`, `chunk_ranges` (Task 5), `SyncCheckpoint` (Task 6), `MetricFailure` (Task 4).

- [ ] **Step 1: Write the failing tests**

Append to `health/tests/test_sync.py`:

```python
def test_first_run_covers_every_metric_before_any_history(store):
    catalog = [metric(name=f"m{i}", days=90) for i in range(4)]
    client = FakeClient()

    SyncEngine(
        client,
        store,
        catalog,
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=4,
    ).sync_all()

    # With a budget of exactly one request per metric, every metric gets its
    # recent window; none of it is spent on one metric's history.
    assert [call[1] for call in client.calls] == ["m0", "m1", "m2", "m3"]
    for item in catalog:
        assert store.get_sync_state(item.name) == date(2026, 7, 20)


def test_history_walks_backward_round_robin_after_the_recent_pass(store):
    catalog = [metric(name="a", days=90), metric(name="b", days=90)]
    client = FakeClient()

    SyncEngine(
        client,
        store,
        catalog,
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=6,
    ).sync_all()

    names = [call[1] for call in client.calls]
    assert names[:2] == ["a", "b"]  # recency pass
    assert names[2:] == ["a", "b", "a", "b"]  # history, one chunk each per round
    # Two history rounds walk 2026-05-14 back through 2026-02-13 to 2025-11-15.
    assert store.get_sync_checkpoint("a").backfilled_from == date(2025, 11, 15)
    assert store.get_sync_state("a") == date(2026, 7, 20)  # watermark not dragged back


def test_history_stops_at_the_configured_floor(store):
    client = FakeClient()
    engine = SyncEngine(
        client,
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-06-01"},
        max_requests=50,
    )

    report = engine.sync_all()

    assert report.history_remaining == {"test": 0}
    # The aligned chunk holding today (2026-05-14..2026-08-11) already starts
    # before the floor, so there is no history left to walk.
    assert store.get_sync_checkpoint("test").backfilled_from <= date(2026, 6, 1)
    assert len(client.calls) == 1


def test_report_counts_remaining_history_chunks(store):
    report = SyncEngine(
        FakeClient(),
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=1,
    ).sync_all()

    # 2021-07-20..2026-05-18 still missing, in 90-day aligned chunks.
    assert report.history_remaining["test"] == 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_sync.py -q -k "first_run_covers or round_robin or stops_at_the_configured_floor or remaining_history"`
Expected: FAIL — the engine still drains one metric's whole history before moving on; `history_remaining` does not exist.

- [ ] **Step 3: Write minimal implementation**

Rewrite the body of `health/src/health/sync.py` below `backfill_start` as:

```python
MAX_REQUESTS_PER_RUN = 200
TRAILING_REFETCH_DAYS = 2
INTRADAY_LOOKBACK_DAYS = 30
RECENT_WINDOW_DAYS = 7


class _RunFinished(Exception):
    """Internal: the budget ran out or Google asked us to pause."""


class SyncEngine:
    def __init__(self, client, store, catalog=CATALOG, today=None, environ=None,
                 max_requests=MAX_REQUESTS_PER_RUN):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.environ = environ
        self.max_requests = max_requests

    # -- date bounds ---------------------------------------------------------

    def _floor(self, metric: Metric) -> date:
        """The oldest day this metric may ever request."""
        if metric.full_history:
            return backfill_start(self.today, self.environ)
        return self.today - timedelta(days=INTRADAY_LOOKBACK_DAYS - 1)

    def _recent_start(self, metric: Metric) -> date:
        """Where the forward pass starts. A metric with no checkpoint begins one
        short window back, not five years back: the point of the first run is
        that every page has something to show, not that one metric is complete."""
        floor = self._floor(metric)
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None:
            return max(floor, self.today - timedelta(days=RECENT_WINDOW_DAYS - 1))
        if checkpoint.status == SYNC_IN_PROGRESS:
            return max(floor, checkpoint.last_synced + timedelta(days=1))
        return max(floor, checkpoint.last_synced - timedelta(days=TRAILING_REFETCH_DAYS))

    def _next_history_chunk(self, metric: Metric) -> tuple[date, date] | None:
        """The aligned chunk immediately older than everything covered so far,
        or None once history reaches the floor."""
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None or checkpoint.backfilled_from is None:
            return None
        floor = self._floor(metric)
        if checkpoint.backfilled_from <= floor:
            return None
        return aligned_chunk(checkpoint.backfilled_from - timedelta(days=1), metric.max_range_days)

    def history_remaining(self, metric: Metric) -> int:
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None or checkpoint.backfilled_from is None:
            return 0
        floor = self._floor(metric)
        if checkpoint.backfilled_from <= floor:
            return 0
        return len(
            chunk_ranges(floor, checkpoint.backfilled_from - timedelta(days=1),
                         metric.max_range_days)
        )

    # -- one chunk -----------------------------------------------------------

    def _fetch_chunk(self, metric, chunk_start, chunk_end, budget, *, status, watermark):
        request_start = max(chunk_start, self._floor(metric))
        request_end = min(chunk_end, self.today)
        if metric.method == DAILY_ROLLUP:
            payloads = [self.client.daily_rollup(metric, request_start, request_end, budget)]
        else:
            # Buffer every reconcile page. Parsing and replacement only begin
            # once the entire chunk is present.
            payloads = list(
                self.client.iter_reconciled(metric, request_start, request_end, budget)
            )
        rows = metric.parse_pages(payloads)
        self.store.replace_chunk(
            metric, chunk_start, chunk_end, payloads, rows,
            status=status, watermark=watermark, backfill_from=chunk_start,
        )
        return request_start, request_end

    # -- the run -------------------------------------------------------------

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None) -> SyncReport:
        report = SyncReport()
        budget = RequestBudget(self.max_requests)
        progress = {m.name: MetricProgress(metric=m.name) for m in self.catalog}
        report.progress = list(progress.values())
        try:
            self._recent_pass(report, budget, progress, progress_cb)
            self._history_pass(report, budget, progress, progress_cb)
        except _RunFinished:
            pass
        report.requests_made = budget.used
        report.history_remaining = {m.name: self.history_remaining(m) for m in self.catalog}
        return report

    def _recent_pass(self, report, budget, progress, progress_cb) -> None:
        for metric in self.catalog:
            start = self._recent_start(metric)
            for chunk_start, chunk_end in chunk_ranges(start, self.today, metric.max_range_days):
                status = SYNC_OK if chunk_end >= self.today else SYNC_IN_PROGRESS
                if not self._guarded(report, metric, budget, progress, progress_cb,
                                     chunk_start, chunk_end, status=status,
                                     watermark=min(chunk_end, self.today)):
                    break
            else:
                progress[metric.name].done = True

    def _history_pass(self, report, budget, progress, progress_cb) -> None:
        pending = [m for m in self.catalog if self._next_history_chunk(m) is not None]
        while pending:
            next_round = []
            for metric in pending:
                chunk = self._next_history_chunk(metric)
                if chunk is None:
                    continue
                # status/watermark stay None: a history chunk says nothing about
                # how current the metric is.
                if not self._guarded(report, metric, budget, progress, progress_cb,
                                     *chunk, status=None, watermark=None):
                    continue
                if self._next_history_chunk(metric) is not None:
                    next_round.append(metric)
            pending = next_round

    def _guarded(self, report, metric, budget, progress, progress_cb,
                 chunk_start, chunk_end, *, status, watermark) -> bool:
        """Fetch one chunk, translating each error into this run's policy.
        Returns False when this metric should stop; raises _RunFinished when
        the whole run should stop."""
        try:
            request_start, request_end = self._fetch_chunk(
                metric, chunk_start, chunk_end, budget, status=status, watermark=watermark
            )
        except RateLimited as exc:
            report.paused = True
            report.resume_in_s = exc.retry_after_s
            raise _RunFinished from exc
        except RequestCapExceeded as exc:
            report.stopped_early = True
            raise _RunFinished from exc
        except ApiError as exc:
            report.failures.append(MetricFailure(metric.name, "api", exc.status_code, exc.message))
            return False
        except PayloadError as exc:
            report.failures.append(MetricFailure(metric.name, "payload", None, exc.detail))
            return False
        progress[metric.name].fetched_ranges += 1
        if progress_cb:
            progress_cb(metric.name, f"{request_start} → {request_end} ({budget.used} requests)")
        return True
```

Update `SyncReport` with the new field:

```python
@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    failures: list[MetricFailure] = field(default_factory=list)
    history_remaining: dict[str, int] = field(default_factory=dict)
    paused: bool = False
    resume_in_s: int | None = None
    stopped_early: bool = False
    requests_made: int = 0
```

and import `aligned_chunk` from `health.endpoints`.

- [ ] **Step 4: Run the whole suite and reconcile the older sync tests**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (218 passed). One existing test now describes superseded behavior and must be updated, not deleted — `test_intraday_initial_sync_is_last_thirty_days`. A first run fetches the 7 recent one-day chunks, then the history pass walks the remaining 23 backwards (verified: 7 + 23 = 30). Rename and rewrite it as:

```python
def test_intraday_first_run_takes_the_recent_window_then_backfills(store):
    client = FakeClient()
    m = next(item for item in CATALOG if item.name == "intraday_hr")

    SyncEngine(client, store, [m], today=date(2026, 7, 20), environ={}, max_requests=50).sync_all()

    assert len(client.calls) == 30
    assert client.calls[0][2] == date(2026, 7, 14)  # recency pass runs first
    assert min(call[2] for call in client.calls) == date(2026, 6, 21)  # floor still reached
    assert store.get_sync_state("intraday_hr") == date(2026, 7, 20)
```

- [ ] **Step 5: Commit**

```bash
git add health/src/health/sync.py health/tests/test_sync.py
git commit -m "feat(health): sync recent data for every metric first, then backfill history"
```

---

### Task 8: Cache the token file inside one auth instance

**Review finding:** `HealthClient._dispatch` calls `auth.access_token()` before every send, so a 200-request run reads and parses `tokens.json` 200 times.

**Files:**
- Modify: `health/src/health/auth.py`
- Modify: `health/tests/test_auth.py`

**Interfaces:**
- Produces: `GoogleHealthAuth.load_tokens()` returns a per-instance cached dict; `_store_tokens` refreshes the cache and `forget_tokens` clears it. No signature changes.

- [ ] **Step 1: Write the failing test**

Append to `health/tests/test_auth.py`:

```python
def test_load_tokens_reads_the_file_once_per_instance(tmp_path, monkeypatch):
    auth = GoogleHealthAuth("id", "secret", tmp_path)
    auth._store_tokens(
        {"access_token": "a", "refresh_token": "r", "expires_in": 3600}, existing=None
    )
    reads = 0
    real_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal reads
        if self.name == "tokens.json":
            reads += 1
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    for _ in range(5):
        assert auth.load_tokens()["access_token"] == "a"

    assert reads <= 1


def test_forget_tokens_invalidates_the_cache(tmp_path):
    auth = GoogleHealthAuth("id", "secret", tmp_path)
    auth._store_tokens(
        {"access_token": "a", "refresh_token": "r", "expires_in": 3600}, existing=None
    )
    assert auth.load_tokens() is not None

    auth.forget_tokens()

    assert auth.load_tokens() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_auth.py -q -k "reads_the_file_once or invalidates_the_cache"`
Expected: FAIL — `reads == 5`.

- [ ] **Step 3: Write minimal implementation**

In `GoogleHealthAuth.__init__` add `self._tokens: dict | None = None`, then:

```python
    def load_tokens(self) -> dict | None:
        # One Streamlit process owns this file; re-reading it before every one
        # of a run's ~200 sends buys nothing.
        if self._tokens is not None:
            return self._tokens
        if not self.tokens_path.exists():
            return None
        try:
            self._tokens = json.loads(self.tokens_path.read_text())
        except json.JSONDecodeError:
            return None  # corrupt token file: behave like "not connected"
        return self._tokens

    def forget_tokens(self) -> None:
        self._tokens = None
        self.tokens_path.unlink(missing_ok=True)
        self.pending_path.unlink(missing_ok=True)
```

and at the end of `_store_tokens`, before `return tokens`:

```python
        self._write_private(self.tokens_path, tokens)
        self._tokens = tokens
        return tokens
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (220 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/auth.py health/tests/test_auth.py
git commit -m "perf(health): cache the token file per auth instance"
```

---

## Phase 2 — Surface it, document it, gate it

### Task 9: Sync page shows history coverage, per-metric failures, and a request cap selector

**Files:**
- Modify: `health/app/views/sync_view.py`
- Modify: `health/src/health/inventory.py` (`STORED_COLUMNS` gains `backfilled_from`)
- Modify: `health/app/views/inventory_view.py` (column config for the new column)
- Modify: `health/tests/test_sync_view.py`, `health/tests/test_inventory.py`

**Interfaces:**
- Consumes: `SyncReport.failures`, `SyncReport.history_remaining`, `Store.sync_states()` with `backfilled_from`.
- Produces: `sync_view.CAP_OPTIONS: dict[str, int]` mapping the Japanese label to a request cap; `sync_view._run_sync(auth, max_requests: int)`.

- [ ] **Step 1: Write the failing test**

Rewrite `health/tests/test_sync_view.py`'s fake Streamlit to record warnings and add:

```python
class FakeStreamlit:
    def __init__(self):
        self.cache_data = FakeCacheData()
        self.session_state = {}
        self.errors = []
        self.warnings = []

    def status(self, *_args, **_kwargs):
        return nullcontext(type("Status", (), {"write": lambda *_args: None})())

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def caption(self, _message):
        pass

    def rerun(self):
        raise AssertionError("error outcomes must not rerun")


def test_run_sync_passes_the_selected_cap_and_records_failures(monkeypatch):
    fake_st = FakeStreamlit()
    fake_st.rerun = lambda: None
    seen = {}

    class RecordingEngine:
        def __init__(self, _client, _store, max_requests=None):
            seen["max_requests"] = max_requests

        def sync_all(self, progress_cb):
            return SyncReport(
                failures=[MetricFailure("sleep", "api", 403, "insufficient scope")],
                history_remaining={"sleep": 4},
                requests_made=12,
            )

    monkeypatch.setattr(sync_view, "st", fake_st)
    monkeypatch.setattr(sync_view, "SyncEngine", RecordingEngine)
    monkeypatch.setattr(sync_view, "HealthClient", lambda _auth: object())
    monkeypatch.setattr(sync_view, "get_store", lambda: object())

    sync_view._run_sync(object(), 500)

    assert seen["max_requests"] == 500
    assert fake_st.session_state["last_sync_report"]["failures"] == [
        {"metric": "sleep", "kind": "api", "status_code": 403, "message": "insufficient scope"}
    ]
    assert fake_st.session_state["last_sync_report"]["history_remaining"] == 4
```

Add `from health.sync import MetricFailure, SyncReport` to that module's imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_sync_view.py -q`
Expected: FAIL — `_run_sync() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Write minimal implementation**

In `health/app/views/sync_view.py`:

```python
CAP_OPTIONS = {"200 requests（既定）": 200, "500 requests": 500, "1000 requests": 1000}


def _run_sync(auth, max_requests: int) -> None:
    try:
        engine = SyncEngine(HealthClient(auth), get_store(), max_requests=max_requests)
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, message: status.write(f"{metric}: {message}")
            )
    except AuthError as exc:
        st.error(f"Google Health の認証が失効しています: {exc}。再接続してください。")
    except ApiError as exc:
        st.error(f"Google Health API エラー（HTTP {exc.status_code}）: {exc.message}")
        if exc.status_code == 403:
            st.caption(
                "スコープ不足か API 未有効化の可能性があります。"
                "health/README.md の OAuth 設定を確認してください。"
            )
    except PayloadError as exc:
        st.error(
            f"{exc.metric} の応答を解釈できません: {exc.detail}。"
            "このchunkは保存せず、既存データを維持して停止しました。"
        )
    else:
        st.session_state["last_sync_report"] = {
            "paused": report.paused,
            "resume_in_s": report.resume_in_s,
            "stopped_early": report.stopped_early,
            "requests_made": report.requests_made,
            "history_remaining": sum(report.history_remaining.values()),
            "failures": [
                {
                    "metric": f.metric,
                    "kind": f.kind,
                    "status_code": f.status_code,
                    "message": f.message,
                }
                for f in report.failures
            ],
        }
        st.rerun()
    finally:
        # The engine commits one completed chunk at a time. A later API or
        # payload error can therefore follow real DB changes, so invalidate
        # cached frames on every outcome once a sync attempt has started.
        st.cache_data.clear()
        get_store().checkpoint()
```

Extend `_show_last_report` with the new fields (keep the existing paused/stopped_early/success branches, then append):

```python
    remaining = last.get("history_remaining", 0)
    if remaining:
        st.info(
            f"履歴の残りは約 {remaining} chunk です。もう一度同期すると古い期間へ遡ります。"
            "直近のデータは全メトリクスで取得済みです。"
        )
    for failure in last.get("failures", []):
        st.warning(
            f"{failure['metric']}: 取得できませんでした"
            f"（{failure['kind']} {failure['status_code'] or ''} {failure['message']}）。"
            "他のメトリクスは同期済みです。"
        )
```

and replace the button block in `sync_page`:

```python
    label = st.selectbox("1回の同期の上限", list(CAP_OPTIONS), index=0)
    if st.button("Google Health からデータを同期", type="primary"):
        _run_sync(auth, CAP_OPTIONS[label])
```

Add `"backfilled_from"` to `STORED_COLUMNS` in `health/src/health/inventory.py` and populate it in `_series_row` with `_value(states, metric.name, "backfilled_from")`; add the matching `st.column_config.DateColumn("履歴開始日")` entry in `inventory_view.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (221 passed). `test_all_seeded_pages_render_without_exception` must still pass — it renders the sync page with the new selectbox.

- [ ] **Step 5: Commit**

```bash
git add health/app/views/sync_view.py health/app/views/inventory_view.py health/src/health/inventory.py health/tests
git commit -m "feat(health): show history coverage, metric failures, and a cap selector on the sync page"
```

---

### Task 10: Documentation matches the implementation

**Review finding:** `README.md:55` tells the user to press "Google Health を再接続", but the button reads "接続解除（トークンを削除。次回は再認可が必要です）". The sync description also still describes the old catalog-order behavior.

**Files:**
- Modify: `health/app/views/sync_view.py:114` (button label)
- Modify: `health/README.md:40-56`, `health/README.md:88-96`
- Modify: `health/CLAUDE.md:9-16`

- [ ] **Step 1: Align the button with the documented name**

In `sync_view.py`:

```python
    if st.button("Google Health を再接続（保存トークンを破棄して再認可）"):
        auth.forget_tokens()
        st.cache_data.clear()
        st.rerun()
```

- [ ] **Step 2: Rewrite the sync section of `health/README.md`**

Replace the "起動・接続・同期" body after the launch command with:

```markdown
最初の画面で「Google Health と接続する」を選び、Googleの同意画面から戻ったら、
「管理 > 同期」で同期します。1回の同期はまず全メトリクスの直近7日を取得し、残りの
request予算で古い期間へ遡ります。したがって**1回目の同期でも全ページが表示できます**。
1回の上限は同期画面で 200 / 500 / 1000 requests から選べます（既定200）。

履歴が残っている場合は同期後に残りchunk数が表示されます。もう一度押すと続きから遡ります。
HTTP 429の場合は表示された時間を待って再開してください。完了したchunkだけが保存され、
途中pageやparser errorでは既存データとwatermarkを変更しません。取得済みの期間は次回同期時に
前回watermarkの2日前から再取得し、遅れて反映された値や削除も取り込みます。

1つのメトリクスが403などで失敗しても、他のメトリクスの同期は継続します。失敗したメトリクスは
同期後に警告として一覧表示されます。

認可をやり直すときは同期画面の「Google Health を再接続」を押します。保存tokenと
未完了OAuth状態を破棄したうえで、明示的に再認可できます。
```

- [ ] **Step 3: Update `health/CLAUDE.md`**

Replace the two bullets describing chunking and watermarks with:

```markdown
- raw pages、typed rows、watermarkは`Store.replace_chunk()`でchunk単位に原子的置換する。
  chunk境界は`CHUNK_EPOCH`と`max_range_days`だけで決まるカレンダー整列（`aligned_chunk`）。
  同じ暦日は常に同じchunk keyになるので、再取得はraw pageを置換し重複を残さない。
  requestは`[floor, today]`にクリップし、保存keyは整列chunk全体のまま。
- sync runはまず全metricの直近`RECENT_WINDOW_DAYS`を取得し（forward pass）、残予算で
  `backfilled_from`から古い方向へ1 chunkずつラウンドロビンする（history pass）。
  `sync_state`は`last_synced_date`（前方）と`backfilled_from`（後方）の両端を持つ。
  history chunkはstatus/watermarkを更新しない。物理sendは最大200件（UIで可変）。
  ApiError/PayloadErrorはmetric単位で隔離し`SyncReport.failures`へ記録して続行、
  AuthError/429/hard capはrun全体を止める。engineへsleep/自動retryを追加しない。
```

- [ ] **Step 4: Verify the app still renders and tests pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (221 passed).

- [ ] **Step 5: Commit**

```bash
git add health/README.md health/CLAUDE.md health/app/views/sync_view.py
git commit -m "docs(health): document the two-pass sync and align the reconnect button label"
```

---

### Task 11: CI for the health package

**Review finding:** `.github/workflows/` contains only `gto-ts.yml`; nothing runs health's 221 tests on push.

**Files:**
- Create: `.github/workflows/health.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# Test + lint gate for the health package (Streamlit dashboard over the
# Google Health API). No live API call runs here: the suite is fixtures and
# fake HTTP only.
name: health

on:
  push:
    branches: [main]
    paths:
      - "health/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/health.yml"
  pull_request:
    paths:
      - "health/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/health.yml"

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install
        run: uv sync --package health

      - name: Test
        run: uv run --no-sync pytest health/tests -q

      - name: Lint
        run: uv run --no-sync ruff check health/src health/app health/scripts health/tests

      - name: Format check
        run: uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
```

- [ ] **Step 2: Validate the YAML locally**

Run: `ENVP uv run --no-sync python -c "import pathlib,yaml;print(sorted(yaml.safe_load(pathlib.Path('.github/workflows/health.yml').read_text())))"`
Expected: prints the top-level keys including `jobs` and `on` (PyYAML parses `on` as `True`; both are acceptable).

If PyYAML is not installed in the workspace venv, skip this step and rely on the first CI run.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/health.yml
git commit -m "ci(health): run pytest and ruff on health changes"
```

---

## Phase 3 — Turn stored series into insight

### Task 12: `health.analytics` — baseline deviation and lagged correlation

**Review finding:** the dashboard plots what was fetched and stops there. The two highest-value derived signals need no extra API data.

**Files:**
- Create: `health/src/health/analytics.py`
- Modify: `health/app/common.py` (import `calendar_rolling_mean` from the new module)
- Create: `health/tests/test_analytics.py`
- Delete: `health/tests/test_common.py` — its three tests (`..._uses_days_not_observation_count`, `..._preserves_original_row_order`, `..._rejects_non_positive_window`) move verbatim into `test_analytics.py` with the import changed from `common` to `health.analytics`; nothing else lives in that file, so it goes away rather than becoming empty.

**Interfaces:**
- Produces:
  - `calendar_rolling_mean(df, value_col, days=7, date_col="date") -> pd.Series` (moved verbatim from `app/common.py`)
  - `rolling_baseline_z(df, value_col, *, window_days=30, min_observations=10, date_col="date") -> pd.DataFrame` with columns `[date_col, value_col, "baseline", "sd", "z"]`
  - `lagged_correlation(df, x_col, y_col, *, lags=(0, 1, 2, 3), date_col="date", min_pairs=20) -> pd.DataFrame` with columns `["lag", "n", "spearman"]`
- Consumes: nothing outside pandas — no Streamlit import, so the module is testable headless.

- [ ] **Step 1: Write the failing tests**

Create `health/tests/test_analytics.py`:

```python
from datetime import date, timedelta

import pandas as pd
import pytest
from health.analytics import calendar_rolling_mean, lagged_correlation, rolling_baseline_z


def _daily(values, start=date(2026, 1, 1)):
    return pd.DataFrame(
        {"date": [start + timedelta(days=i) for i in range(len(values))], "value": values}
    )


def test_baseline_uses_only_prior_days():
    df = _daily([10.0] * 20 + [40.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    last = out.iloc[-1]
    assert last["baseline"] == pytest.approx(10.0)  # the spike is not in its own baseline
    assert last["value"] == 40.0


def test_days_without_enough_history_get_no_z():
    df = _daily([10.0, 11.0, 12.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert out["z"].isna().all()


def test_zero_variance_history_yields_no_z_instead_of_infinity():
    df = _daily([10.0] * 15 + [12.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert pd.isna(out.iloc[-1]["z"])


def test_z_is_positive_for_a_value_above_its_baseline():
    df = _daily([10.0, 11.0, 9.0, 10.5, 9.5] * 3 + [20.0])

    out = rolling_baseline_z(df, "value", window_days=30, min_observations=10)

    assert out.iloc[-1]["z"] > 3


def test_lagged_correlation_matches_by_calendar_date_not_row_position():
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(40)]
    sleep = [float(i % 7) for i in range(40)]
    df = pd.DataFrame({"date": days, "sleep": sleep, "hr": [0.0] * 40})
    # hr on day d+1 mirrors sleep on day d, with day 5 missing entirely.
    df["hr"] = [0.0] + sleep[:-1]
    df = df.drop(index=5).reset_index(drop=True)

    out = lagged_correlation(df, "sleep", "hr", lags=(0, 1), min_pairs=5)

    lag1 = out[out["lag"] == 1].iloc[0]
    lag0 = out[out["lag"] == 0].iloc[0]
    assert lag1["spearman"] > 0.95
    assert lag1["spearman"] > lag0["spearman"]
    assert lag1["n"] < len(df)  # the missing day drops its pairs instead of shifting them


def test_lagged_correlation_reports_nan_below_min_pairs():
    df = _daily([1.0, 2.0, 3.0]).rename(columns={"value": "x"})
    df["y"] = [3.0, 2.0, 1.0]

    out = lagged_correlation(df, "x", "y", lags=(0,), min_pairs=20)

    assert pd.isna(out.iloc[0]["spearman"])
    assert out.iloc[0]["n"] == 3


def test_calendar_rolling_mean_ignores_missing_days():
    df = pd.DataFrame(
        {"date": [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 20)], "value": [10.0, 20.0, 5.0]}
    )

    out = calendar_rolling_mean(df, "value", days=7)

    assert out.tolist() == [10.0, 15.0, 5.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_analytics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.analytics'`.

- [ ] **Step 3: Write minimal implementation**

Create `health/src/health/analytics.py`:

```python
"""Derived signals over the stored daily series. Pure pandas, no Streamlit."""

from __future__ import annotations

import pandas as pd


def calendar_rolling_mean(
    df: pd.DataFrame,
    value_col: str,
    days: int = 7,
    date_col: str = "date",
) -> pd.Series:
    """Average observations in the trailing calendar window, preserving row order.

    Missing dates are not treated as zero. They simply contribute no
    observation, which is appropriate for device data that was not recorded.
    """
    if days < 1:
        raise ValueError("days must be positive")
    if df.empty:
        return pd.Series(index=df.index, dtype=float, name=f"{value_col}_ma{days}")

    work = pd.DataFrame(
        {
            "_date": pd.to_datetime(df[date_col]),
            "_value": df[value_col].to_numpy(),
            "_position": range(len(df)),
        }
    ).sort_values(["_date", "_position"])
    work["_mean"] = work.rolling(f"{days}D", on="_date", min_periods=1)["_value"].mean()
    values = work.sort_values("_position")["_mean"].to_numpy()
    return pd.Series(values, index=df.index, name=f"{value_col}_ma{days}")


def rolling_baseline_z(
    df: pd.DataFrame,
    value_col: str,
    *,
    window_days: int = 30,
    min_observations: int = 10,
    date_col: str = "date",
) -> pd.DataFrame:
    """Score each day against its own trailing calendar-window history.

    The window ends on the *previous* observation, so a day never contributes
    to the baseline it is scored against -- otherwise a large excursion damps
    its own z. Days with fewer than `min_observations` prior readings get NaN
    rather than a z computed from too little history, and a zero-variance
    history yields NaN rather than an infinite z.
    """
    work = df[[date_col, value_col]].dropna().sort_values(date_col).reset_index(drop=True)
    if work.empty:
        return pd.DataFrame(columns=[date_col, value_col, "baseline", "sd", "z"])

    dates = pd.to_datetime(work[date_col])
    values = work[value_col].to_numpy(dtype=float)
    baseline: list[float] = []
    sd: list[float] = []
    z: list[float] = []
    for position in range(len(work)):
        window_start = dates.iloc[position] - pd.Timedelta(days=window_days)
        in_window = ((dates < dates.iloc[position]) & (dates >= window_start)).to_numpy()
        prior = values[in_window]
        if len(prior) < min_observations:
            baseline.append(float("nan"))
            sd.append(float("nan"))
            z.append(float("nan"))
            continue
        mean = float(prior.mean())
        spread = float(prior.std(ddof=1))
        baseline.append(mean)
        sd.append(spread)
        z.append(float("nan") if spread == 0 else (values[position] - mean) / spread)

    out = work.copy()
    out["baseline"] = baseline
    out["sd"] = sd
    out["z"] = z
    return out


def lagged_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    *,
    lags: tuple[int, ...] = (0, 1, 2, 3),
    date_col: str = "date",
    min_pairs: int = 20,
) -> pd.DataFrame:
    """Spearman correlation between x on day d and y on day d+lag.

    Rank correlation rather than Pearson: these series are skewed and carry
    outlier days, and the question is monotone association, not linearity.
    Pairs are matched by calendar date, so a missing day drops its own pairs
    instead of silently shifting every later one.
    """
    work = df[[date_col, x_col, y_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col])
    rows = []
    for lag in lags:
        shifted = work[[date_col, y_col]].copy()
        shifted[date_col] = shifted[date_col] - pd.Timedelta(days=lag)
        merged = work[[date_col, x_col]].merge(shifted, on=date_col, how="inner").dropna()
        pairs = len(merged)
        rho = (
            merged[x_col].corr(merged[y_col], method="spearman")
            if pairs >= min_pairs
            else float("nan")
        )
        rows.append({"lag": lag, "n": pairs, "spearman": rho})
    return pd.DataFrame(rows)
```

In `health/app/common.py`, delete the local `calendar_rolling_mean` definition and re-export it so view imports keep working:

```python
from health.analytics import calendar_rolling_mean  # noqa: F401  (re-exported for views)
```

Move all three tests from `health/tests/test_common.py` into `test_analytics.py` verbatim, changing only the import line (`from common import calendar_rolling_mean` → `from health.analytics import calendar_rolling_mean`, already covered by the module import above), then delete `test_common.py` and its now-unused `sys.path` preamble.

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (228 passed — 221 plus 7 new; the 3 moved tests are a wash).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/analytics.py health/app/common.py health/tests/test_analytics.py
git rm health/tests/test_common.py
git commit -m "feat(health): add baseline-deviation and lagged-correlation analytics"
```

---

### Task 13: Sleep rhythm and data-coverage helpers

**Files:**
- Modify: `health/src/health/analytics.py`
- Modify: `health/tests/test_analytics.py`

**Interfaces:**
- Produces:
  - `sleep_midpoints(sleep_df) -> pd.DataFrame` with `["date", "midpoint_hours_after_noon", "is_free_day"]`
  - `social_jetlag_hours(sleep_df) -> float | None`
  - `coverage_calendar(daily_df, value_col, start, end, date_col="date") -> pd.DataFrame` with `["date", "has_data"]`
- Consumes: `Store.sleep_frame()` columns (`date`, `start_ts`, `end_ts`, `is_main`) and `Store.daily_frame()` output.

- [ ] **Step 1: Write the failing tests**

Append to `health/tests/test_analytics.py`:

```python
def _sleep(date_value, start, end, is_main=True):
    return {
        "date": date_value,
        "start_ts": start,
        "end_ts": end,
        "is_main": is_main,
        "minutes_asleep": 400,
    }


def test_midpoint_is_measured_from_the_noon_before_the_wake_date():
    df = pd.DataFrame(
        [_sleep(date(2026, 1, 6), "2026-01-05 23:00:00", "2026-01-06 07:00:00")]
    )

    out = sleep_midpoints(df)

    # midnight+3h = 15 hours after the previous noon
    assert out.iloc[0]["midpoint_hours_after_noon"] == pytest.approx(15.0)


def test_social_jetlag_is_free_day_minus_work_day_midpoint():
    rows = []
    for day in range(5):  # Mon 2026-01-05 .. Fri 2026-01-09
        rows.append(_sleep(date(2026, 1, 5) + timedelta(days=day),
                           f"2026-01-{4 + day:02d} 23:00:00", f"2026-01-{5 + day:02d} 07:00:00"))
    for day in (10, 11):  # Sat, Sun: same duration, two hours later
        rows.append(_sleep(date(2026, 1, day),
                           f"2026-01-{day:02d} 01:00:00", f"2026-01-{day:02d} 09:00:00"))

    jetlag = social_jetlag_hours(pd.DataFrame(rows))

    assert jetlag == pytest.approx(2.0, abs=0.01)


def test_social_jetlag_needs_both_kinds_of_day():
    rows = [
        _sleep(date(2026, 1, 5), "2026-01-04 23:00:00", "2026-01-05 07:00:00"),
        _sleep(date(2026, 1, 6), "2026-01-05 23:00:00", "2026-01-06 07:00:00"),
    ]

    assert social_jetlag_hours(pd.DataFrame(rows)) is None


def test_coverage_calendar_marks_every_day_in_the_span():
    df = pd.DataFrame(
        {"date": [date(2026, 1, 1), date(2026, 1, 3)], "steps": [100.0, float("nan")]}
    )

    out = coverage_calendar(df, "steps", date(2026, 1, 1), date(2026, 1, 4))

    assert len(out) == 4
    assert out["has_data"].tolist() == [True, False, False, False]
```

Extend the module import line with `coverage_calendar, sleep_midpoints, social_jetlag_hours`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `ENVP uv run --no-sync pytest health/tests/test_analytics.py -q`
Expected: FAIL — `ImportError: cannot import name 'sleep_midpoints'`.

- [ ] **Step 3: Write minimal implementation**

Append to `health/src/health/analytics.py`:

```python
def sleep_midpoints(sleep_df: pd.DataFrame) -> pd.DataFrame:
    """Sleep midpoint per wake date, in hours after the noon before it.

    The noon anchor is the same one the nightly gantt uses: it keeps bedtimes
    that cross midnight on a continuous scale instead of wrapping to 0.
    """
    columns = ["date", "midpoint_hours_after_noon", "is_free_day"]
    if sleep_df.empty:
        return pd.DataFrame(columns=columns)
    work = sleep_df[sleep_df["is_main"]].copy() if "is_main" in sleep_df else sleep_df.copy()
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["date"] = pd.to_datetime(work["date"])
    start = pd.to_datetime(work["start_ts"])
    end = pd.to_datetime(work["end_ts"])
    anchor = work["date"] - pd.Timedelta(hours=12)
    midpoint = start + (end - start) / 2
    work["midpoint_hours_after_noon"] = (midpoint - anchor).dt.total_seconds() / 3600
    work["is_free_day"] = work["date"].dt.weekday >= 5
    return work[columns].reset_index(drop=True)


def social_jetlag_hours(sleep_df: pd.DataFrame) -> float | None:
    """Free-day minus work-day mean sleep midpoint, in hours.

    None when either kind of day has fewer than two nights -- a single night
    is not a rhythm.
    """
    midpoints = sleep_midpoints(sleep_df)
    if midpoints.empty:
        return None
    free = midpoints[midpoints["is_free_day"]]["midpoint_hours_after_noon"]
    work_days = midpoints[~midpoints["is_free_day"]]["midpoint_hours_after_noon"]
    if len(free) < 2 or len(work_days) < 2:
        return None
    return float(free.mean() - work_days.mean())


def coverage_calendar(
    daily_df: pd.DataFrame,
    value_col: str,
    start,
    end,
    date_col: str = "date",
) -> pd.DataFrame:
    """One row per calendar day in [start, end] and whether a value exists.

    Distinguishes "the device recorded nothing" from "we never synced that
    day" only in combination with the sync watermark; on its own it shows the
    gaps a line chart hides by connecting across them.
    """
    days = pd.date_range(start, end, freq="D")
    if daily_df.empty or value_col not in daily_df:
        return pd.DataFrame({"date": days, "has_data": [False] * len(days)})
    present = set(pd.to_datetime(daily_df.dropna(subset=[value_col])[date_col]))
    return pd.DataFrame({"date": days, "has_data": [day in present for day in days]})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (232 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/analytics.py health/tests/test_analytics.py
git commit -m "feat(health): add sleep-rhythm and coverage-calendar analytics"
```

---

### Task 14: Insights page

**Files:**
- Create: `health/app/views/insights_view.py`
- Modify: `health/app/main.py:46-68` (import and register the page)
- Modify: `health/tests/test_app_smoke.py` (add the page to the render list)

**Interfaces:**
- Consumes: `load_daily`, `load_sleep`, `period_days`, `clip_days` from `common`; `palette`, `style` from `theme`; `rolling_baseline_z`, `lagged_correlation`, `social_jetlag_hours`, `coverage_calendar` from `health.analytics`.
- Produces: `insights_page() -> None`.

- [ ] **Step 1: Write the failing test**

In `health/tests/test_app_smoke.py`, add to the `pages` list in `test_all_seeded_pages_render_without_exception`:

```python
        ("insights_view", "insights_page", "気づき"),
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_app_smoke.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'views.insights_view'`.

- [ ] **Step 3: Write minimal implementation**

Create `health/app/views/insights_view.py`:

```python
"""Insights: baseline deviations, lagged relationships, sleep rhythm, coverage."""

import pandas as pd
import plotly.express as px
import streamlit as st
from common import clip_days, load_daily, load_sleep, period_days
from health.analytics import (
    coverage_calendar,
    lagged_correlation,
    rolling_baseline_z,
    social_jetlag_hours,
)
from theme import palette, style

# Deviation is only meaningful for metrics with a stable personal baseline.
DEVIATION_METRICS = [
    ("resting_hr", "安静時心拍", "bpm"),
    ("hrv_rmssd", "HRV (RMSSD)", "ms"),
    ("temp_skin_relative", "皮膚温（基準比）", "℃"),
]
PAIRS = [
    ("sleep_minutes", "睡眠時間", "resting_hr", "安静時心拍"),
    ("sleep_minutes", "睡眠時間", "hrv_rmssd", "HRV"),
    ("steps", "歩数", "sleep_minutes", "睡眠時間"),
]
ALERT_Z = 2.0


def _deviation_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("ベースラインからの逸脱")
    st.caption("直近30日の自分の平均と比べた標準化スコア。|z| >= 2 を注目日として扱います。")
    for metric, label, unit in DEVIATION_METRICS:
        if metric not in df:
            continue
        scored = rolling_baseline_z(df[["date", metric]], metric)
        scored = scored.dropna(subset=["z"])
        if scored.empty:
            st.caption(f"{label}: 判定に必要な履歴が不足しています（30日で10日以上必要）")
            continue
        latest = scored.iloc[-1]
        st.metric(
            label,
            f"{latest[metric]:.1f} {unit}",
            delta=f"z = {latest['z']:+.1f}",
            delta_color="off",
        )
        fig = px.line(scored, x="date", y="z", labels={"date": "日付", "z": "z"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        fig.add_hline(y=ALERT_Z, line_dash="dot", line_color=p["muted"])
        fig.add_hline(y=-ALERT_Z, line_dash="dot", line_color=p["muted"])
        fig.update_layout(height=180)
        st.plotly_chart(style(fig, p), width="stretch", theme=None)


def _relationship_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("翌日への影響（ラグ相関）")
    st.caption("Spearman順位相関。lag=1 は「その日の値」と「翌日の値」の関係です。")
    rows = []
    for x_col, x_label, y_col, y_label in PAIRS:
        if x_col not in df or y_col not in df:
            continue
        table = lagged_correlation(df, x_col, y_col)
        for _, row in table.iterrows():
            rows.append(
                {
                    "関係": f"{x_label} → {y_label}",
                    "lag（日）": int(row["lag"]),
                    "相関": row["spearman"],
                    "日数": int(row["n"]),
                }
            )
    if not rows:
        st.caption("相関を計算できる系列がありません。")
        return
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("日数が20未満の組み合わせは相関を計算せず空欄になります。")


def _rhythm_section(sleep_df: pd.DataFrame) -> None:
    st.subheader("睡眠リズム")
    jetlag = social_jetlag_hours(sleep_df)
    if jetlag is None:
        st.caption("平日・休日それぞれ2晩以上の記録が必要です。")
        return
    st.metric("ソーシャル・ジェットラグ", f"{jetlag:+.1f} 時間")
    st.caption("休日の睡眠中央時刻から平日の中央時刻を引いた差。プラスは休日に遅寝遅起き。")


def _coverage_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("データ欠損カレンダー")
    if df.empty:
        return
    start, end = df["date"].min(), df["date"].max()
    coverage = coverage_calendar(df, "steps", start, end)
    coverage["weekday"] = coverage["date"].dt.weekday
    coverage["week"] = coverage["date"].dt.strftime("%G-W%V")
    pivot = coverage.pivot_table(index="weekday", columns="week", values="has_data")
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=p["sequential"],
        labels=dict(color="記録あり", x="週", y="曜日"),
    )
    fig.update_layout(
        paper_bgcolor=p["surface"],
        plot_bgcolor=p["surface"],
        font_color=p["ink"],
        margin=dict(t=30, l=10, r=10, b=10),
    )
    st.plotly_chart(fig, width="stretch", theme=None)
    st.caption("色が薄い日は歩数データがありません（未装着か未同期）。")


def insights_page() -> None:
    st.title("気づき")
    p = palette()
    df = load_daily(
        ("steps", "sleep_minutes", "resting_hr", "hrv_rmssd", "temp_skin_relative")
    )
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days()).copy()
    df["date"] = pd.to_datetime(df["date"])
    _deviation_section(df, p)
    _relationship_section(df, p)
    _rhythm_section(load_sleep())
    _coverage_section(df, p)
```

In `health/app/main.py`, add the import next to the others and register the page after 概要:

```python
    from views.insights_view import insights_page
```

```python
                st.Page(insights_page, title="気づき", icon="💡"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (232 passed, with the smoke test now covering eight pages).

- [ ] **Step 5: Commit**

```bash
git add health/app/views/insights_view.py health/app/main.py health/tests/test_app_smoke.py
git commit -m "feat(health): add an insights page for deviations, lags, rhythm, and coverage"
```

---

### Task 15: Export the stored tables

**Files:**
- Create: `health/src/health/export.py`
- Create: `health/scripts/export_data.py`
- Create: `health/tests/test_export.py`
- Modify: `health/app/views/inventory_view.py` (CSV download buttons)
- Modify: `health/README.md` (document the script)

**Interfaces:**
- Produces:
  - `EXPORT_TABLES: tuple[str, ...] = ("daily_series", "sleep_sessions", "intraday", "sync_state")`
  - `export_tables(store, out_dir: Path, fmt: str = "parquet") -> list[Path]` — raises `ValueError` for a format outside `{"parquet", "csv"}`; writes files `0600` inside a `0700` directory.
- Consumes: `Store.con`.

- [ ] **Step 1: Write the failing test**

Create `health/tests/test_export.py`:

```python
import stat
from datetime import date

import pytest
from health.export import EXPORT_TABLES, export_tables
from health.store import Store


@pytest.fixture
def store(tmp_path):
    created = Store(tmp_path / "health.duckdb")
    created.upsert_daily([("steps", date(2026, 1, 1), 1000.0)])
    yield created
    created.close()


def test_export_writes_one_file_per_table(store, tmp_path):
    out_dir = tmp_path / "export"

    written = export_tables(store, out_dir, "parquet")

    assert [path.name for path in written] == [f"{t}.parquet" for t in EXPORT_TABLES]
    assert all(path.exists() and path.stat().st_size > 0 for path in written)


def test_exported_files_are_private(store, tmp_path):
    out_dir = tmp_path / "export"

    written = export_tables(store, out_dir, "csv")

    assert stat.S_IMODE(out_dir.stat().st_mode) == 0o700
    for path in written:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_unknown_format_is_rejected(store, tmp_path):
    with pytest.raises(ValueError, match="unsupported export format"):
        export_tables(store, tmp_path / "export", "sqlite")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_export.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'health.export'`.

- [ ] **Step 3: Write minimal implementation**

Create `health/src/health/export.py`:

```python
"""Export the typed tables to files. Everything written is private health data."""

from __future__ import annotations

import os
from pathlib import Path

EXPORT_TABLES: tuple[str, ...] = ("daily_series", "sleep_sessions", "intraday", "sync_state")
_FORMATS = {"parquet": "PARQUET", "csv": "CSV"}


def export_tables(store, out_dir: Path, fmt: str = "parquet") -> list[Path]:
    """Write one file per table into `out_dir`, owner-only.

    `fmt` is checked against a fixed map rather than interpolated: it lands
    inside a COPY statement, and the table names are the only other dynamic
    part (they come from this module's own tuple, never from a caller).
    """
    if fmt not in _FORMATS:
        raise ValueError(f"unsupported export format: {fmt!r} (parquet or csv)")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    written: list[Path] = []
    for table in EXPORT_TABLES:
        path = out_dir / f"{table}.{fmt}"
        store.con.execute(f"COPY {table} TO '{path}' (FORMAT {_FORMATS[fmt]})")
        os.chmod(path, 0o600)
        written.append(path)
    return written
```

Create `health/scripts/export_data.py`:

```python
"""Export the local DuckDB tables to parquet or csv."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from health.export import export_tables
from health.store import Store


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export local health tables.")
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--format", choices=("parquet", "csv"), default="parquet")
    args = parser.parse_args(argv)

    store = Store(args.db_path)
    try:
        written = export_tables(store, args.out_dir, args.format)
    finally:
        store.close()
    for path in written:
        print(f"wrote: {path}")


if __name__ == "__main__":
    main()
```

In `health/app/views/inventory_view.py`, append a download section:

```python
    st.subheader("エクスポート")
    st.caption("表示中の棚卸し表をCSVとして保存します（実データを含みます。取り扱いに注意）。")
    st.download_button(
        "保存系列をCSVでダウンロード",
        series.to_csv(index=False).encode("utf-8-sig"),
        file_name="health_series_inventory.csv",
        mime="text/csv",
    )
```

Add to `health/README.md` under データファイル:

```markdown
DuckDBの中身をファイルへ書き出すこともできます。出力先は`0700`、ファイルは`0600`で作成されます。

```bash
uv run --no-sync python health/scripts/export_data.py \
  --db-path health/data/health.duckdb --out-dir /tmp/health-export --format parquet
```

**出力は実際のprivate health dataです。共有・commitしないでください。**
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (235 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/export.py health/scripts/export_data.py health/tests/test_export.py health/app/views/inventory_view.py health/README.md
git commit -m "feat(health): export stored tables to parquet or csv"
```

---

### Task 16: Small cleanups the review flagged

**Review findings:** `build_inventory(store)` takes a parameter it immediately `del`s; `endpoints._metric()` linearly scans `CATALOG` on every parser call.

**Files:**
- Modify: `health/src/health/inventory.py:36-46`
- Modify: `health/src/health/endpoints.py:179-185`
- Modify: `health/app/views/inventory_view.py:13` (call site)
- Modify: `health/tests/test_inventory.py` (call sites)

**Interfaces:**
- Produces: `build_inventory(catalog=CATALOG, known_data_types=KNOWN_DATA_TYPES) -> pd.DataFrame` — the unused `store` parameter is gone. `endpoints._metric(name)` resolves through a lazily built `dict` instead of a scan; behavior is identical.

- [ ] **Step 1: Write the failing test**

Append to `health/tests/test_inventory.py`:

```python
def test_build_inventory_needs_no_store():
    frame = build_inventory()

    assert not frame.empty
    assert set(frame.columns) == set(PUBLISHED_COLUMNS)
```

Import `PUBLISHED_COLUMNS` from `health.inventory` in that module.

- [ ] **Step 2: Run test to verify it fails**

Run: `ENVP uv run --no-sync pytest health/tests/test_inventory.py -q -k needs_no_store`
Expected: FAIL — `build_inventory() missing 1 required positional argument: 'store'`.

- [ ] **Step 3: Write minimal implementation**

In `health/src/health/inventory.py`, drop the parameter and the `del`:

```python
def build_inventory(
    catalog: Sequence[Metric] = CATALOG,
    known_data_types: dict[str, tuple[str, str]] = KNOWN_DATA_TYPES,
) -> pd.DataFrame:
    """Return every published data type, whether or not the app implements it."""

    by_type: dict[str, list[Metric]] = {}
```

In `health/src/health/endpoints.py`:

```python
_CATALOG_BY_NAME: dict[str, Metric] = {}


def _metric(name: str) -> Metric:
    """Look up this module's own CATALOG entry by name. Parsers use this to
    get the Metric object response_points() needs (.method / .name); the index
    is built on first use -- CATALOG is only fully built after this module's
    top-level code finishes running, which is always true by the time any
    parser is actually invoked."""
    if not _CATALOG_BY_NAME:
        _CATALOG_BY_NAME.update({item.name: item for item in CATALOG})
    return _CATALOG_BY_NAME[name]
```

Update the call site in `health/app/views/inventory_view.py` from `build_inventory(store)` to `build_inventory()`, and the same in every `test_inventory.py` call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `ENVP uv run --no-sync pytest health/tests -q`
Expected: PASS (236 passed).

- [ ] **Step 5: Commit**

```bash
git add health/src/health/inventory.py health/src/health/endpoints.py health/app/views/inventory_view.py health/tests/test_inventory.py
git commit -m "refactor(health): drop the unused inventory store parameter and index the catalog"
```

---

## Deliberately out of scope

- **Static type checking (mypy/pyright).** The review noted its absence and the `# type: ignore` comments in `endpoints.py`. Adding a type checker is a workspace-wide decision (every sibling project would inherit the config and the CI gate), not a health-local one, so it is not planned here. Raise it separately if you want it.
- **A richer intraday history browser.** Intraday storage already keeps everything ever fetched; only the date picker is thin. That is a UI enhancement with no correctness or safety content, and Task 14 already adds the page where it would belong.

---

## Final verification

- [ ] **Step 1: Full suite, lint, format**

```bash
ENVP uv run --no-sync pytest health/tests -q
ENVP uv run --no-sync ruff check health/src health/app health/scripts health/tests
ENVP uv run --no-sync ruff format --check health/src health/app health/scripts health/tests
```

Expected: `236 passed`, `All checks passed!`, `NN files already formatted`.

Running total per task, so a mid-plan drift is visible immediately: 196 baseline → 199 (T1) → 202 (T2) → 203 (T3) → 206 (T4) → 211 (T5) → 214 (T6) → 218 (T7) → 220 (T8) → 221 (T9) → 221 (T10, T11) → 228 (T12) → 232 (T13) → 232 (T14) → 235 (T15) → 236 (T16).

- [ ] **Step 2: Confirm no real data was touched**

```bash
git status --porcelain health/data health/.env
```

Expected: empty output (both are gitignored and must be unmodified).

- [ ] **Step 3: Sanity-check the new sync shape against a fake client**

Write a throwaway script under the session scratchpad (not the repo) that runs `SyncEngine` with the real `CATALOG`, a fake client that consumes budget and returns empty payloads, `max_requests=200`, and a temporary DuckDB path. Confirm: every one of the 14 metrics appears in `client.calls` during the first run, and `report.history_remaining` is non-zero for the 90-day metrics.

- [ ] **Step 4: Update the plan's status and write the change note**

Create `health/docs/2026-07-25-review-fixes.md` summarizing what changed, mirroring the structure of `health/docs/2026-07-23-post-review-fixes.md`: what changed, whether a DuckDB migration is required (yes — `sync_state.backfilled_from`, applied automatically on open and seeded from `raw_json`), and the validation output.

```bash
git add health/docs/2026-07-25-review-fixes.md
git commit -m "docs(health): record the 2026-07-25 review fixes"
```

- [ ] **Step 5: Finish the branch**

Use the `superpowers:finishing-a-development-branch` skill to decide how this lands (merge to main vs PR).
