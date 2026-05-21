# AGENTS.md

## Project

`land_price_api_app` is a local-only Streamlit + DuckDB application for ingesting, storing, and analyzing Japanese land-price, real-estate trade, rent-market, and listing data.

Respond to the user in Japanese by default. Keep code, filenames, technical identifiers, and commit messages primarily in English.

## Setup And Run

This project is a member of the uv workspace at `~/projects/`. Python
dependencies are declared in `land_price_api_app/pyproject.toml` and
resolved together with the other workspace members.

```bash
# One-time install (from workspace root)
cd ~/projects && make install     # = uv sync --all-packages

# Start the app (workspace .venv is auto-discovered)
cd ~/projects/land_price_api_app
uv run --no-sync streamlit run app.py --server.address 127.0.0.1 --server.port 8501
# or use the convenience scripts:
./run_local.sh     # daemonised, PID in .streamlit.pid
./stop_local.sh    # clean shutdown
```

`requirements.txt` is retained for legacy reference; `pyproject.toml` is
now canonical.

## Verification

There is no checked-in pytest, lint, or type-check configuration. Use the narrowest relevant command:

```bash
python -m compileall app.py config.py db.py ui property_scraper.py geocoder.py geocode_trade_prices.py sync_rent_market.py generate_site_schema.py
python sync_public_notice.py --year 2026 --smoke-test
python sync_public_notice.py --year 2025 --z 13 --pref 13
python sync_trade_prices.py --pref 13 --year 2024 --quarter 1
python sync_rent_market.py --year 2023
python geocode_trade_prices.py --limit 100 --sleep 0.3
```

Commands that call MLIT, e-Stat, GSI, Ollama, or package registries require working local services, credentials, or network access.

## Architecture

- Ingestion flow: external API -> raw files in `_data/land_price/raw/` -> normalized `pandas.DataFrame` -> Parquet in `_data/land_price/processed/` -> DuckDB tables/views -> Streamlit tabs.
- `sync_public_notice.py` handles XPT002 land-price tile ingestion.
- `sync_trade_prices.py` handles XIT001 trade-price ingestion.
- `sync_rent_market.py` handles e-Stat rent-market ingestion.
- `geocode_trade_prices.py` fills missing trade-price `lat/lon` using `geocoder.py` and the GSI address API.
- `normalize.py` maps unstable external payload fields into the repo's snake_case analytical schema.
- `db.py` owns table DDL, views, upserts, reusable reads, and query helpers.
- `app.py` creates one cached DuckDB connection and delegates rendering to `ui/*.py`.
- `ui/property_tab.py` orchestrates listing analysis through `property_scraper.py`, `geocoder.py`, `analytics.py`, and the investment simulation engine. `ui/property_investment.py` probes both `../notebooks/real_estate_app/` (legacy location) and `../_archive/notebooks/real_estate_app/` (current archived location) and adds whichever exists to `sys.path` before importing `sim_engine` / `formatters`. The simulator block is therefore alive against the archived copy.
- Canonical heavy-data storage is `../_data/land_price/{raw,processed}/`. `data/raw` and `data/processed` inside the project are symlinks into that workspace location — they remain for source-level compatibility but are not separate copies.

## Code Conventions

- Use `config.py` for environment, paths, directory creation, and logging.
- Preserve raw source data when changing ingestion: keep raw files and `raw_properties`.
- Prefer `db.py` helpers over ad hoc SQL in UI code.
- Follow the existing DuckDB upsert pattern: temp key table, delete existing keys, insert aligned rows.
- Extend `_FIELD_CANDIDATES` and parsing helpers in `normalize.py` when API field names change.
- In `property_scraper.py`, regex/structured extraction is authoritative. Ollama may fill missing fields only; it must not overwrite structured values.
- Keep UI tabs as orchestration layers. Reusable data access, normalization, and analysis logic belongs in `db.py`, `normalize.py`, `analytics.py`, or sync modules.
- Treat prefecture codes as zero-padded strings such as `"13"`.

## Data And Secrets

- `.env`, generated data, DuckDB files, logs, caches, and `.venv/` are ignored. Do not commit secrets or generated datasets.
- `.env.example` documents expected keys. `REINFOLIB_API_KEY` is required for MLIT API calls; `ESTAT_APP_ID` is required for rent-market sync; Ollama is optional for listing extraction.

## Working Notes

- The app is local-only and should bind to `127.0.0.1`.
- Be careful with existing local data and user edits. Do not delete raw caches, processed files, or database files unless the user explicitly asks.
- If the worktree is dirty, inspect changes before editing and preserve unrelated user work.
- Migration to `../_data/land_price/` is complete. `data/raw` and `data/processed` are symlinks into the workspace storage and exist only for backwards-compatible relative paths in legacy scripts.
