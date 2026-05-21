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
