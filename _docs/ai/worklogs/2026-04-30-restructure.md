# Workspace Restructure Report

## Preflight

- Timestamp: 2026-04-30T16:31:42+09:00
- Workspace root: `/home/kazumasa/projects`
- Environment: WSL2 / bash
- `land_price_api_app` branch: `main`
- `land_price_api_app` git status at start: clean

## DB Candidate Comparison

- Candidate A: `/home/kazumasa/projects/data/processed/land_prices.duckdb`
  - Size: 274,432 bytes
  - Modified: 2026-04-05 13:07:33 +0900
  - `land_prices_public_notice`: 0 rows
  - `trade_prices` table: absent
- Candidate B: `/home/kazumasa/projects/land_price_api_app/data/processed/land_prices.duckdb`
  - Size: 668,217,344 bytes
  - Modified: 2026-04-30 12:28:53 +0900
  - `land_prices_public_notice`: 354,893 rows
  - Year coverage: 2000-2026
  - `trade_prices` table: present

Decision:
- Canonical DuckDB source for migration is `land_price_api_app/data/processed/land_prices.duckdb`.
- The root-level `data/processed/land_prices.duckdb` is not a valid primary data source.

## High-Level Plan

1. Update `config.py` and CLI path resolution with workspace-aware defaults and legacy fallback.
2. Run compile-based validation before touching existing data.
3. Create shared workspace directories and root guide files.
4. Copy data into `_data/land_price/` with `rsync`, verify, and only then rename old directories to `*.migrated`.
5. Update docs and examples, sweep old path references, then add workspace indexes and VS Code workspace files.

## Known Risks

- `pytest` is not installed in the available virtual environments, so automated validation is limited to compile/import checks unless dependencies are added.
- `land_price_api_app/notebooks/*.ipynb` still contain legacy `data/raw` and `data/processed` references.
- `notebooks/real_estate_data_collection.ipynb` references `notebooks/output`, so scratch migration must remain selective.
- `rates_volatility_model/venv` exists and should not be removed automatically.

## Validation Run

- `py_compile` passed for:
  - `config.py`
  - `db.py`
  - `api_client.py`
  - `normalize.py`
  - `run_sync.py`
  - `run_backfill.py`
  - `sync_public_notice.py`
  - `sync_trade_prices.py`
  - `geocode_trade_prices.py`
- `pytest` could not be run because `pytest` is not installed in either `/home/kazumasa/projects/land_price_api_app/.venv` or `/home/kazumasa/projects/.venv`.

## Summary

- Added workspace-level directories and root guidance files for AI-assisted work.
- Updated `land_price_api_app` path resolution to prefer `_data/land_price/` and `_logs/app/land_price_api_app/` while preserving legacy compatibility.
- Copied land-price raw and processed data into `_data/land_price/` and verified file counts plus DuckDB row counts.
- Renamed legacy `land_price_api_app/data/raw` and `land_price_api_app/data/processed` to `raw.migrated` and `processed.migrated`, then restored `raw` and `processed` as symlinks to the new workspace locations.
- Copied existing app log files into `_logs/app/land_price_api_app/` and moved legacy root logs into `_logs/app/land_price_api_app/legacy/`.
- Moved one-off AI comparison notebooks into `_scratch/notebooks/2026-04/`.

## Directories Created

- `_docs/ai/handoffs`
- `_docs/ai/worklogs`
- `_docs/capability_index`
- `_docs/recipes`
- `_data/land_price/raw`
- `_data/land_price/processed`
- `_data/land_price/backup`
- `_data/real_estate/raw`
- `_data/real_estate/processed`
- `_logs/ai-terminal`
- `_logs/ai-diffs`
- `_logs/app/land_price_api_app`
- `_logs/app/land_price_api_app/legacy`
- `_scratch/notebooks`
- `_scratch/scripts`
- `_scratch/outputs`
- `_scratch/tmp`
- `_archive/old_notebooks`
- `_archive/oneoff_tests`
- `_archive/old_projects`
- `_archive/tmp`
- `_workspaces`

## Files Moved

- Copied `land_price_api_app/data/raw/*` to `_data/land_price/raw/`
- Copied `land_price_api_app/data/processed/*` to `_data/land_price/processed/`
- Moved `notebooks/{gpt4o,gemini,grok,haiku,opus,sonnet,codex}_test_0.ipynb` to `_scratch/notebooks/2026-04/`
- Copied `land_price_api_app/{backfill_log.txt,backfill_log2.txt,backfill_log3.txt,streamlit.log,sync_log.txt}` to `_logs/app/land_price_api_app/`
- Moved legacy log files to `_logs/app/land_price_api_app/legacy/`

## Path Rewrites Performed

- `land_price_api_app/config.py`
  - Added workspace-aware path resolution with legacy fallback and legacy-env auto-upgrade.
- `land_price_api_app/run_sync.py`
  - Switched `processed_dir` to `config.PROCESSED_DIR`.
- `land_price_api_app/run_backfill.py`
  - Switched `processed_dir` to `config.PROCESSED_DIR`.
- `land_price_api_app/run_local.sh`
  - Switched Streamlit log output to `_logs/app/land_price_api_app/`.
- `land_price_api_app/.env.example`
  - Documented workspace-level data and log paths.
- `land_price_api_app/README.md`
  - Updated canonical storage documentation to `_data/land_price/`.
- `land_price_api_app/AGENTS.md`
  - Updated agent guidance to prefer workspace data/log paths.
- `land_price_api_app/hazard_sources.py`
  - Updated hazard-data placement notes.

## Files Intentionally Not Moved

- `/home/kazumasa/projects/data/processed/land_prices.duckdb`
  - Left untouched because it is not the canonical DB and may still be referenced manually.
- `notebooks/output/`
  - Left untouched because `notebooks/real_estate_data_collection.ipynb` still points to it.
- `land_price_api_app/notebooks/*.ipynb`
  - Left in place; legacy `data/raw` and `data/processed` references remain compatible through symlinks.
- `rates_volatility_model/venv`
  - Left untouched by design.

## Validation Results

- `land_price_api_app/.venv/bin/python -m py_compile ...` passed after the path migration changes.
- `db.get_connection(read_only=True)` succeeded against `_data/land_price/processed/land_prices.duckdb`.
- Read-only DB stats after cutover:
  - `total_records=354893`
  - year coverage still includes `2000-2026`
- `bash -n run_local.sh` and `bash -n stop_local.sh` passed.
- Data copy verification:
  - `raw`: `82` source files and `82` destination files
  - `processed`: `217` source files and `217` destination files
  - canonical DuckDB size and row counts match between source and destination

## Remaining Risks

- `pytest` remains unavailable in the current virtual environments, so behavior-level automated tests were not run.
- Historical references to old paths remain in worklogs, `tree.txt`, and migrated log files by design.
- `notebooks/real_estate_data_collection.ipynb` still references `notebooks/output`.

## Recommended Next Steps

1. Install `pytest` into the intended environment if automated tests should be part of future validation.
2. If the stale root-level `data/processed/land_prices.duckdb` is no longer needed, archive it explicitly after confirming no manual workflows depend on it.
3. Once notebook compatibility updates are complete, consider removing the `land_price_api_app/data/{raw,processed}` symlinks.
4. Open the focused VS Code workspace instead of the whole `~/projects` tree.
