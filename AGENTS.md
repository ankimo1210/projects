# Workspace Agent Guide

This root is a multi-project workspace. Do not scan the whole root by default.

## Active Projects

Application / product projects:

- `land_price_api_app/` — 地価公示・不動産取引ローカルアプリ (FastAPI + DuckDB)
- `gto/` — GTO ポーカー分析アプリ (Rust + FastAPI + Next.js)
- `stock/` — `stockkit` 株式分析ツールキット (Python + Dash)
- `market-viz/` — マーケット可視化アプリ (Streamlit + Plotly + DuckDB)
- `nbody-gpu/` — GPU N 体シミュレーション (CuPy + VisPy)
- `line_backup/` — LINE バックアップ解析 CLI (Python)
- `akinator/` — Wikidata ベースのアキネーター風推測ゲーム (FastAPI)

Research / notebook projects:

- `johnhull/` — Hull『Options, Futures, and Other Derivatives』11e の章別学習ボリューム + `hullkit` 共有パッケージ
- `rates_volatility_model/` — 金利ボラ研究ノート
- `aisan_lbo_case/` — アイサンテクノロジー (4667.T) 非公開化 LBO ケーススタディ
- `notebooks/` — 単発の分析ノートブック置き場

Samples:

- `csharp_calc/` — WinForms 電卓サンプル (C# / .NET 9)

Note: `re_invest_os` was moved out to its own repo (`~/re_invest_os`,
GitHub `ankimo1210/re_invest_os`) — it is no longer in this workspace.

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
- `tmp/`
- `*.duckdb`
- `*.parquet`
- `*.geojson`
- `*.csv`
- `*.xlsx`
- `*.pdf`
- `*.log`
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
