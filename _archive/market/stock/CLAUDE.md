# stock (stockkit) — Claude Code Guide

## Purpose

JP/US stock analysis toolkit. Pulls prices from yfinance + J-Quants +
Stooq, macro from FRED + e-Stat. Exposes a Dash dashboard (8 pages), a
Streamlit chat with Claude API, and analytical libraries (technical /
fundamental / portfolio / backtest / screener / basket weighting).

Respond to the user in Japanese by default; code and identifiers in English.

## Architecture

| Layer | Path | Role |
|---|---|---|
| Library | `src/stockkit/` | `data/` (yfinance/FRED/Stooq/J-Quants providers, cache, symbols, nikkei225, us_indices), `analysis/` (technical, fundamental, portfolio, backtest, screener, basket), `viz/` (charts) |
| Dash app | `app/app.py` + `app/pages/` | Multi-page dashboard (8 pages: ホーム, 個別銘柄, スクリーナー, ポートフォリオ, バックテスト, N225 basket, 米株 basket, AI chat) |
| API helpers | `app/api/` | Tools called by the AI chat page (e.g., `chat.py`) |
| Notebooks | `notebooks/` | Exploratory analyses |
| Docs | `docs/` | `ARCHITECTURE.md`, `DATA_SOURCES.md`, `METHODOLOGY.md`, ADRs under `decisions/` |
| Cache | `stock/_data/` (per-project) | yfinance / FRED cache (gitignored). Path: `STOCKKIT_DATA_DIR` env or default `parents[3] / "_data"`. |

## Run & Verify

Python deps live in the workspace `.venv` at `~/projects/`.

```bash
# One-time install (from workspace root)
cd ~/projects && make install      # = uv sync --all-packages

# Dash dashboard (port 8050 by default)
cd ~/projects/stock && ./start.sh   # = uv run python app/app.py

# Streamlit AI chat
uv run --no-sync streamlit run stock/app/pages/chat.py

# Tests
uv run --no-sync pytest stock/tests
```

`.env` lives in `stock/` (not workspace root) with `ANTHROPIC_API_KEY`,
`FRED_API_KEY`, `ESTAT_API_KEY`, etc. See `SETUP.md`.

## Conventions

- **Import name is `stockkit`** (project dir is `stock/` but the package
  is `stockkit`). All imports go through `from stockkit.X import Y`.
- **Data layer is the only place** that touches yfinance / FRED / e-Stat /
  J-Quants / Stooq. Pages and analyses must call into `stockkit.data.*`,
  never call providers directly.
- **Cache**: `stockkit.data.cache` controls Parquet/CSV caching under
  `stock/_data/`. Cached frames are the default; pass `force_refresh=True`
  only when the user explicitly asks for a refresh.
- **Symbols**: zero-padded JP codes are strings (`"7203"`), US tickers are
  ALL-CAPS (`"AAPL"`). The `symbols.py` module normalises.
- **AI chat**: when the chat code calls a function, it does so through
  the registered tool surface in `app/api/tools.py`. New analytical
  functions must be registered there to be reachable from chat.
- **ADRs** under `docs/decisions/` record non-obvious choices (Claude API
  vs Claude Max, Flask port choice, PAF approximation, etc.). Read them
  before re-litigating those decisions.

## Gotchas

- **`stock/_data/` is per-project**, not the workspace `_data/<project>/`
  convention (intentional — yfinance cache lives close to the toolkit).
  Don't move it without updating `STOCKKIT_DATA_DIR` defaults in 4 files
  (`cache.py`, `nikkei225.py`, `us_indices.py`, `analysis/basket.py`).
- **Anthropic key billing**: the AI chat consumes credits per turn. When
  debugging chat code, prefer fixture-based tests over live calls.
- **yfinance rate limits**: long batch fetches can get throttled. Use
  the cache and incremental updates rather than full refresh.
- **Two web frameworks coexist**: Dash for the main dashboard, Streamlit
  for the AI chat page. They are NOT interchangeable — check which
  context a file lives in before editing UI patterns.
- `notebooks/` here is local; the workspace `~/projects/notebooks/` is
  separate.
