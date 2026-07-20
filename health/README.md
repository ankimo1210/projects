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
