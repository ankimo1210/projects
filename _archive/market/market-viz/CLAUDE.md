# market-viz — Claude Code Guide

## Purpose

Personal market visualisation & analysis app. Pulls prices (yfinance, ccxt)
and computes volatility, z-scores, drawdowns, correlations, signals,
backtests, and alerts. Streamlit pages for exploration; FastAPI backend
for the structured-data routes; optional Next.js frontend.

Respond to the user in Japanese by default; code and identifiers in English.

## Architecture

| Layer | Path | Role |
|---|---|---|
| Library | `src/market_viz/` | Reusable code. `analytics/` (vol, zscore, correlation, drawdown, returns, signals, backtest), `data/` (yfinance/ccxt loaders, update orchestration), `storage/` (DuckDB client), `config/` (`instruments.yaml`, `settings.yaml`). |
| Streamlit app | `app/` | `main.py` + `pages/01_market_dashboard.py` … `06_alert_monitor.py`. Thin pages; logic stays in `market_viz`. |
| Backend API | `backend/app/` | FastAPI (port 8000). Routers under `routers/` (`alerts`, `analytics`, `backtest`, `data_update`). Dependency injection via `deps.py`. |
| Frontend | `frontend/` | Next.js scaffold (optional). |
| Notebooks | `notebooks/` | Ad-hoc exploration. |
| Tests | `tests/` | Pytest suite. |

## Run & Verify

Python deps live in the workspace `.venv` at `~/projects/`.

```bash
# One-time install (from workspace root)
cd ~/projects && make install        # = uv sync --all-packages

# Full stack (backend :8000 + frontend :3000)
cd ~/projects/market-viz && ./start.sh

# Streamlit pages only
uv run --no-sync streamlit run market-viz/app/main.py

# Backend only
uv run --no-sync uvicorn backend.app.main:app --reload --port 8000

# Tests
uv run --no-sync pytest market-viz/tests
```

## Conventions

- **Import path is `market_viz`**, never `src`. The src layout was
  reorganised — `from src.X import Y` is wrong, use `from market_viz.X import Y`.
  Wheel is built from `src/market_viz` (see `pyproject.toml`).
- **Analytics functions** in `src/market_viz/analytics/` take DataFrames in
  and return DataFrames/Series. Keep them deterministic and side-effect
  free; storage/IO belongs in `data/` or `storage/`.
- **DuckDB is the single store**. `storage/duckdb_client.py` is the only
  module that opens connections. Streamlit pages must go through it.
- **Data update**: `data/update.py::update_daily` / `update_crypto_intraday`
  are the canonical entry points. Do not call yfinance / ccxt directly
  from a page.
- **`.gitignore` rule**: `/data/` (top-level only) excludes the project's
  DuckDB. `src/market_viz/data/` is a Python package and is tracked.
- New page numbering: keep the `NN_name.py` pattern under `app/pages/` so
  Streamlit orders them deterministically.

## Gotchas

- **`market-viz/data/market.duckdb`** is gitignored but used at runtime.
  Run `update_daily` once before opening pages, or pages will show empty.
- The frontend (Next.js) is optional and may lag the backend; if you only
  touch analytics, skip pnpm work.
- **Old `from src.X` imports**: any reintroduced reference will resolve to
  the empty namespace package on disk (no error, silent break). Use
  `market_viz.X` only.
- `notebooks/` here is project-local exploration, distinct from the
  workspace `notebooks/` at `~/projects/notebooks/`.
