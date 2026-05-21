# Copilot instructions for `land_price_api_app`

## Run, smoke-test, and verification commands

There is no checked-in `pytest`, `unittest`, lint, or type-check configuration in this repository. The narrowest built-in verification commands are `compileall`, the CLI smoke test, and targeted sync commands.

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the local Streamlit app
streamlit run app.py --server.address 127.0.0.1 --server.port 8501

# Narrow local syntax check for touched modules
python -m compileall app.py config.py db.py ui property_scraper.py geocoder.py geocode_trade_prices.py sync_rent_market.py generate_site_schema.py

# Narrowest built-in smoke test (API key + XIT002 + XPT002 + DuckDB write/read)
python sync_public_notice.py --year 2026 --smoke-test

# Targeted land-price sync for one prefecture/year
python sync_public_notice.py --year 2025 --z 13 --pref 13

# Targeted trade-price sync for one prefecture/year/quarter
python sync_trade_prices.py --pref 13 --year 2024 --quarter 1

# Rent-market sync for a single supported survey year
python sync_rent_market.py --year 2023

# Targeted trade geocoding batch
python geocode_trade_prices.py --limit 100 --sleep 0.3
```

## High-level architecture

- This is a **local-only** Streamlit + DuckDB application for ingesting, storing, and analyzing Japanese land-price and real-estate trade datasets. External APIs are called server-side from Python, not from the browser.
- The core ingestion pipeline is: **external API -> raw file in `data/raw/` -> normalized `pandas.DataFrame` -> Parquet in `data/processed/` -> DuckDB tables/views -> Streamlit UI**.
- `sync_public_notice.py` handles XPT002 land-price tiles. It scans Web Mercator XYZ tiles, tracks fetched tiles in `data/raw/fetched_tiles_*.json`, deduplicates features across tiles, writes raw GeoJSON, writes Parquet, then upserts DuckDB.
- `sync_trade_prices.py` handles XIT001 trade-price data by prefecture/year/quarter. `sync_rent_market.py` handles e-Stat rent data. `geocode_trade_prices.py` later fills missing trade `lat/lon` using the GSI geocoder.
- `normalize.py` is the schema bridge between inconsistent API payload keys and the repo's snake_case analytical schema. `db.py` owns table DDL, views, upserts, and all reusable read/query helpers.
- `app.py` creates one cached DuckDB connection, loads the current year of land-price data once, and passes shared filters/connection into tab renderers in `ui/`.
- The property-analysis flow spans multiple modules: `ui/property_tab.py` fetches listing HTML via `property_scraper.py`, uses regex-first extraction with Ollama fallback, geocodes the address with `geocoder.py`, finds nearby comps through `analytics.py`/`db.py`, then imports the investment simulation engine from `notebooks/real_estate_app`.

## Codebase-specific conventions

- Default to replying to the user in Japanese. Keep code, filenames, technical identifiers, and commit messages primarily in English.
- **Use `config.py` as the central boundary for environment and logging.** Modules are expected to call `get_logger()`, `ensure_dirs()`, and `validate_api_key()` / related validators instead of re-reading env vars themselves.
- **Preserve raw source data whenever you touch ingestion.** This codebase keeps both raw payloads on disk and `raw_properties` JSON in DuckDB rows; do not replace that with normalized-only persistence.
- **Use `db.py` helpers instead of ad hoc SQL where possible.** The repo standardizes reads through helper functions like `read_land_prices()`, `read_trade_prices()`, `get_city_summary()`, and `get_trade_city_summary()`.
- **Upserts are implemented as delete-then-insert, not `INSERT OR REPLACE`.** DuckDB writes use temp key tables plus `DELETE` + `INSERT`, so follow that pattern when adding new persisted datasets.
- **Normalization must tolerate unstable API field names.** Extend `_FIELD_CANDIDATES` and existing parsing helpers in `normalize.py` instead of hardcoding a single response key.
- **Prefer regex/structured extraction over LLM guesses.** In `property_scraper.py`, regex-extracted fields are authoritative; the Ollama pass is only allowed to fill fields that remain `None`, never overwrite structured values.
- **Handle DB contention with the repo's fallback patterns.** `db.get_connection()` may fall back to read-only mode, and `notebook_utils.py` falls back to Parquet when DuckDB is unavailable; preserve that behavior rather than forcing writes.
- **Keep prefecture and city filters aligned with the DB helper API.** Prefecture codes are treated as zero-padded strings (for example `"13"`), and tab/UI code usually passes filter dictionaries straight into `db.py`.
- **UI tabs are thin orchestration layers.** Put reusable data access, normalization, or analysis logic in `db.py`, `normalize.py`, `analytics.py`, or the sync modules instead of embedding it directly in `ui/*.py`.
- **If the worktree is dirty, inspect existing changes before editing and preserve unrelated user work.** Do not delete raw caches, processed files, DuckDB files, or other local data unless the user explicitly asks.
