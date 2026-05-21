# Workspace Agent Guide

This root is a multi-project workspace. Do not scan the whole root by default.

## Active Projects

Application / product projects:

- `land_price_api_app/` — 地価公示・不動産取引ローカルアプリ (FastAPI + DuckDB)
- `re_invest_os/` — 不動産買付前 DD Web アプリ (Next.js + FastAPI + Supabase)
- `gto/` — GTO ポーカー分析アプリ (Rust + FastAPI + Next.js)
- `stock/` — `stockkit` 株式分析ツールキット (Python + Dash)
- `market-viz/` — マーケット可視化アプリ (Streamlit + Plotly + DuckDB)
- `nbody-gpu/` — GPU N 体シミュレーション (CuPy + VisPy)
- `line_backup/` — LINE バックアップ解析 CLI (Python)

Research / notebook projects:

- `johnhull/` — John Hull 金利モデル研究ノート
- `rates_volatility_model/` — 金利ボラ研究ノート
- `notebooks/` — 単発の分析ノートブック置き場

Each project has its own `README.md` and (in some cases) its own `CLAUDE.md` /
`AGENTS.md`. Read those before editing files inside a project.

## Shared Docs

- Workspace overview: root `README.md`
- Per-project entry point: `<project>/README.md` (and `<project>/CLAUDE.md` /
  `<project>/AGENTS.md` when present)
- Recipes / worklogs: `_docs/`

## Do Not Inspect By Default

- `_data/`
- `_logs/`
- `_archive/`
- `_scratch/`
- `reports/`
- `*.duckdb`
- `*.parquet`
- `*.geojson`
- `*.csv`
- `*.ipynb` unless explicitly requested
- `venv/`
- `.venv/`
- `node_modules/`
- `target/` (Rust build output)
- `__pycache__/`

## Workflow

1. Identify the relevant project (root `README.md` lists all).
2. Read that project's `README.md` and, if present, its `CLAUDE.md` / `AGENTS.md`.
3. Inspect only targeted source files.
4. Avoid broad search unless necessary.
5. For workspace-wide checks, use the root `Makefile` (`make lint`, `make test`).

## Context Policy

- Avoid resuming old AI sessions unless continuing the exact same task.
- Use handoff summaries for new phases.
- If context is large, recommend `/clear` or `/compact` before continuing.
- Do not read heavy data files unless explicitly requested.
