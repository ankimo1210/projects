# Google Health review fixes — 2026-07-25

The 16-task branch implementing Phase 0–3 (private-data safety, the resumable
sync engine, its UI surface, and the insights page) was reviewed in full
before merge. The review found one Critical issue, three Important issues,
and a set of Minor items worth closing in the same pass.

## What changed

- Phase 0 (private data): a shared `health.privacy.ensure_private_dir()`
  helper replaces three separate, unconditional `os.chmod(dir, 0o700)` calls
  in `store.py`, `export.py`, and `auth.py`. See "Critical fix" below.
- Phase 1 (sync engine): `SyncEngine.sync_all()`'s `history_remaining` no
  longer counts chunks for a metric that failed this run, so the sync page
  stops promising progress on a metric that fails every run (e.g. a scope
  never granted).
- Phase 2 (sync UI): the sync page's status table now renders
  `backfilled_from` with a `DateColumn`, matching the inventory page. The
  `ApiError`/`PayloadError` handlers in `_run_sync` — unreachable today
  because `SyncEngine._guarded()` isolates both per metric into
  `SyncReport.failures` and lets the run continue — are kept as defence in
  depth, with corrected copy and a comment explaining why they cannot fire
  via `sync_all()`.
- Phase 3 (insights): `insights_view._deviation_section` now scores
  `rolling_baseline_z` against the *full* stored history and clips only what
  is displayed, instead of clipping first. Clipping first starved the
  30-day baseline window of real prior observations whenever the selected
  display period was itself close to 30 days (worst at the 「30日」 option).
- `scripts/export_data.py` now checks `--db-path` exists before opening it,
  so a typo'd path fails loudly instead of silently creating an empty
  database and exporting four empty files as a reported success.
- `scripts/seed_demo.py --force` now also removes a stale `.wal` beside the
  old database file; left behind, DuckDB replays it into the freshly seeded
  database.
- `app/common.py`'s `calendar_rolling_mean` re-export shim is gone;
  `sleep_view.py` and `activity_view.py` import it from `health.analytics`
  directly.
- `Store.replace_chunk`'s docstring now documents the `None`-means-unchanged
  contract for `status`/`watermark`, that `backfill_from` only ever extends
  `backfilled_from` backwards, and why a metric with no checkpoint never gets
  a history chunk (a first-ever `replace_chunk` call would otherwise
  fabricate a forward watermark from wherever a history chunk happens to
  end).
- `tests/test_analytics.py` gained a case mixing a nap (`is_main=False`) with
  a main session on the same date, confirming `sleep_midpoints` excludes the
  nap rather than only being verified by reading the source.

### Critical fix: unconditional `os.chmod` on a directory the app does not own

`Store.__init__` ran `os.chmod(path.parent, 0o700)` on every open,
regardless of whether it had just created that directory. Reproduced before
the fix:

```
$ uv run --no-sync python health/scripts/seed_demo.py --db-path /tmp/health-demo.duckdb
PermissionError: [Errno 1] Operation not permitted: '/tmp'
```

— exactly the command this README and `health/CLAUDE.md` tell the user to
run for a demo database. When the parent directory *is* owned by the caller
(e.g. `--db-path ~/demo.duckdb`), the same unconditional chmod would have
silently re-permissioned it to `0700` as a side effect of opening a
database, well beyond what protecting health data requires. `export.py`
(`--out-dir`) and `auth.py` (`_write_private`'s `data_dir`) had the same
pattern.

The fix is `health.privacy.ensure_private_dir(path)`: it creates `path` if
missing and narrows it to `0700` only when this call is the one that created
it. A directory that already existed — owned by the app or not — is left
alone; the chmod itself is best-effort (`OSError` suppressed) since it can
fail outright on a directory like `/tmp`. The three call sites now share
this one helper instead of three copies of the same (buggy) pattern.

## Database migration

Opening a database created by an earlier version of this app runs one
migration automatically, before any query: `ALTER TABLE sync_state ADD
COLUMN IF NOT EXISTS backfilled_from DATE`, then `backfilled_from` is seeded
for every pre-existing row from `min(raw_json.range_start)` for that metric
(rows already carrying a value are left untouched). Both statements are
idempotent, so a fresh database and a database that already has the column
take the same code path with no branching in `Store.__init__`.

## Two upgrade caveats

- **Recent-first does not take effect immediately on an upgraded database.**
  `_recent_start` resumes a metric with `last_synced_date`/`status =
  in_progress` from `last_synced + 1`, continuing the old five-years-forward
  walk rather than jumping to the last 7 days. This is deliberate:
  `backfilled_from` is seeded from the oldest raw page ever fetched, so
  forcing the recent window immediately would leave the span between the old
  watermark and `today - 7` unreachable by either pass. With 14 metrics the
  forward backfill exceeds the 200-request default cap, so the first
  post-upgrade sync can still leave later catalog metrics empty — the
  symptom Task 7 removed only for fresh installs. `health/README.md`'s
  起動・接続・同期 section now states this explicitly instead of promising
  every page renders after one sync regardless of database age.
- **Raw pages written under pre-Task-5 chunk keys are never replaced, only
  duplicated under the new aligned keys.** `Store.replace_chunk` deletes raw
  pages by exact `(metric, start, end)` match. The old forward walk from the
  first caveat re-fetches the same calendar days but under the new,
  calendar-aligned chunk keys, so an upgraded database ends up holding both
  the old and the new raw page for the same days. No data is lost — typed
  rows and watermarks are correct either way — but `raw_stats()` overstates
  the page count for a metric until enough natural re-fetching happens to
  crowd the old pages out. No migration deletes the old rows: a one-shot
  cleanup that guesses which raw pages are obsolete was judged a bigger risk
  than an inflated page count that has no effect on correctness.

## Validation

- `245 passed` for `health/tests` immediately before this fix wave; `258
  passed` after it (13 new tests: a dedicated `test_privacy.py` for
  `ensure_private_dir` plus the Critical fix's `Store`/`export_tables`
  pre-existing-directory coverage, `history_remaining` exclusion,
  `export_data.py`'s existence check, `seed_demo.py --force`'s `.wal`
  cleanup, the `sleep_midpoints` nap case, and the insights baseline-window
  regression).
- `ruff check` and `ruff format --check` both clean over
  `health/src health/app health/scripts health/tests`.
- No live Google Health API call in any test; fixtures and fake HTTP only.
- No real token, `.env`, or `health/data/` file was read, written, or
  deleted — `git status --porcelain health/data health/.env` is empty
  throughout.

Implementation plan:
[`2026-07-25-health-review-fixes.md`](../../docs/superpowers/plans/2026-07-25-health-review-fixes.md).
Prior wave: [2026-07-23 post-review fixes](2026-07-23-post-review-fixes.md).
