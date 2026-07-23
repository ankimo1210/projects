# Google Health post-review fixes — 2026-07-23

The migration-completion/UI implementation was reviewed after its initial merge.
The review found that the automated tests and seeded UI rendered successfully,
but three correctness gaps and two maintenance gaps remained.

## What changed

- Sync checkpoints now distinguish `in_progress` from `ok`. Interrupted backfills
  resume at the first unfinished chunk; completed metrics re-fetch from two days
  before their watermark so late-arriving corrections and deletions are reconciled.
- `SyncEngine.max_requests` is injectable, so cap/resume behavior is tested without
  mutating a module global.
- Streamlit data caches are invalidated even when a later chunk fails after earlier
  chunks were committed.
- Activity and sleep seven-day averages use calendar windows rather than seven rows.
- Streamlit was raised to 1.51 and deprecated `use_container_width` calls were
  replaced with `width="stretch"`.
- Seeded AppTest coverage is committed for all seven pages and for the main app both
  before and after OAuth connection.

No DuckDB schema migration is required. Existing `sync_state.status = 'ok'` rows are
compatible; the first interrupted post-upgrade run changes the checkpoint to
`in_progress` atomically with its completed chunk.

## Validation

- `196 passed` for `health/tests`
- ruff check and format check passed
- imports and `uv lock --check` passed
- all seven seeded pages plus connected/disconnected main rendered without exceptions
- corrected seed CLI completed against a temporary DuckDB path
- no live Google API request, real token, `.env`, or `health/data/` file was used

Implementation plan and historical errata:
[`2026-07-22-health-google-migration-completion-and-ui.md`](../../docs/superpowers/plans/2026-07-22-health-google-migration-completion-and-ui.md).
