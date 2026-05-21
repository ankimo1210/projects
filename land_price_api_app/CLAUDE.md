# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Respond in Japanese by default. Write code, filenames, commit messages, and technical identifiers in English.

## Commands

```bash
# Start / stop
./run_local.sh          # starts Streamlit at http://localhost:8501 (daemonized, PID in .streamlit.pid)
./stop_local.sh         # clean shutdown (prefer over Ctrl+C)

# Syntax check (no pytest config checked in)
python -m compileall app.py config.py db.py ui property_scraper.py geocoder.py normalize.py

# Run tests
python -m pytest tests/ -v
# or without pytest:
python tests/test_property_scraper.py

# Data sync CLI
python sync_public_notice.py --year 2026 --smoke-test          # quick API check
python sync_public_notice.py --year 2026 --z 13 --pref 13     # Tokyo public notice
python sync_trade_prices.py --pref 13 --year 2024             # Tokyo trade prices
python sync_rent_market.py --year 2023                         # e-Stat rent data
python geocode_trade_prices.py --limit 1000 --sleep 0.3       # geocode trade prices
python run_sync.py                                             # parallel multi-prefecture sync
python run_backfill.py --from 2010 --to 2026                  # bulk historical backfill
```

## Architecture

**Ingestion flow**: external API → raw files in `../_data/land_price/raw/` → normalized DataFrame → Parquet in `../_data/land_price/processed/` → DuckDB tables/views → Streamlit tabs.

**Key layer responsibilities:**

| Module | Role |
|--------|------|
| `config.py` | All env vars, paths, dir creation, logging. Single source of truth for configuration. |
| `db.py` | Table DDL, views, upserts, reusable reads. UI code must use helpers here, not ad hoc SQL. |
| `normalize.py` | Maps unstable external API fields → snake_case schema via `_FIELD_CANDIDATES`. Update here when API field names change. |
| `api_client.py` | HTTP client for MLIT Reinfolib API (XPT002 / XIT001 / XIT002). |
| `tiles.py` | XYZ tile coordinate math and scanning for z=13 Japan coverage. |
| `geocoder.py` | GSI address-search API (no key required). |
| `property_scraper.py` | HTML fetch → BeautifulSoup text → Ollama (gemma3:12b) JSON extraction. Regex/structured extraction is authoritative; Ollama may only fill missing fields. |
| `analytics.py` | Shared analysis functions for UI tabs. |
| `app.py` | Creates one `@st.cache_resource` DuckDB connection; delegates to `ui/*.py`. |
| `ui/*.py` | Thin orchestration only. Business logic belongs in `db.py` / `analytics.py`. |

**Sync modules**: `sync_public_notice.py` (XPT002), `sync_trade_prices.py` (XIT001), `sync_rent_market.py` (e-Stat), `geocode_trade_prices.py`.

**DB tables**: `land_prices_public_notice` (primary key: `(point_id, year)`), `trade_prices`, `rent_market`. Views: `city_summary`, `pref_summary`, `trade_city_summary`.

**DB path resolution**: `config.py` prefers `../_data/land_price/processed/land_prices.duckdb` (workspace), falling back to `data/processed/land_prices.duckdb` (legacy). Override with `DUCKDB_PATH` env var.

**DuckDB upsert pattern**: temp key table → delete existing keys → insert aligned rows (DuckDB has no `INSERT OR REPLACE`).

## Code Conventions

- Use `config.get_logger(__name__)` for all module loggers.
- Treat prefecture codes as zero-padded strings: `"13"` not `13`.
- Preserve `raw_properties` (raw JSON) when changing ingestion logic.
- `ui/unit_price.py` owns price display formatting (万円, 1 decimal, $/m² and $/tsubo columns).
- `st.cache_data(ttl=86400)` for external API results (Overpass, GSI elevation) in UI layers.

## External Services

| Service | Key | Used by |
|---------|-----|---------|
| MLIT Reinfolib API | `REINFOLIB_API_KEY` (required) | `api_client.py`, sync scripts |
| Anthropic Claude | `ANTHROPIC_API_KEY` (optional) | `property_scraper.py` (alternative to Ollama) |
| e-Stat | `ESTAT_APP_ID` (optional) | `sync_rent_market.py` |
| GSI address API | none | `geocoder.py` |
| Overpass API | none | `facility_sources.py`, `terrain_sources.py` |
| Ollama (local) | none | `property_scraper.py` — needs `gemma3:12b` at `127.0.0.1:11434` |

## Tests

Regression tests in `tests/` use HTML fixtures in `tests/fixtures/`. No network access. Each fixture has a companion expected-output JSON. `_FLOAT_TOL` and `_INT_TOL` dicts in `test_property_scraper.py` define per-field tolerances.

## Important Constraints

- App must bind to `127.0.0.1` (local-only). `run_local.sh` uses `0.0.0.0` for LAN access — keep consistent with existing behavior.
- Do not delete raw caches, Parquet files, or DuckDB files without explicit user request.
- `data/raw` and `data/processed` are legacy compatibility paths; canonical storage is `../_data/land_price/`.
