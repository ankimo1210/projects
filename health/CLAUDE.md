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
