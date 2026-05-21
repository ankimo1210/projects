# Workspace Agent Guide

This root is a multi-project workspace. Do not scan the whole root by default.

## Active Projects

- `land_price_api_app/`
- `rates_volatility_model/`
- `johnhull/`
- `notebooks/`

## Shared Docs

Use `_docs/capability_index/` first to find relevant files.

## Do Not Inspect By Default

- `_data/`
- `_logs/`
- `_archive/`
- `_scratch/`
- `reports/`
- `tmp/`
- `*.duckdb`
- `*.parquet`
- `*.geojson`
- `*.csv`
- `*.ipynb` unless explicitly requested
- `venv/`
- `.venv/`
- `__pycache__/`

## Workflow

1. Identify the relevant project.
2. Read the project README and AGENTS.md.
3. Read the relevant capability index in `_docs/capability_index/`.
4. Inspect only targeted source files.
5. Avoid broad search unless necessary.

## Context Policy

- Avoid resuming old AI sessions unless continuing the exact same task.
- Use handoff summaries for new phases.
- If context is large, recommend `/clear` or `/compact` before continuing.
- Do not read heavy data files unless explicitly requested.
