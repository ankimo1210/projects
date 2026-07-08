# Workspace Agent Guide

This root is a multi-project workspace. Do not scan the whole root by default.

## Active Projects

Application / product projects:

- `gto/` — GTO ポーカー分析アプリ (Rust + FastAPI + Next.js)
- `stock/` — `stockkit` 株式分析ツールキット (Python + Dash)
- `market-viz/` — マーケット可視化アプリ (Streamlit + Plotly + DuckDB)
- `nbody-gpu/` — GPU N 体シミュレーション (CuPy + VisPy)
- `line_backup/` — LINE バックアップ解析 CLI (Python)
- `akinator/` — Wikidata ベースのアキネーター風推測ゲーム (FastAPI)
- `pokemon/` — Quokka Wilds: オリジナル 3D モンスター収集ゲーム (Vite + React Three Fiber)

Research / notebook projects:

- `johnhull/` — Hull『Options, Futures, and Other Derivatives』11e の章別学習ボリューム + `hullkit` 共有パッケージ
- `autostock/` — Mag7 株ストラテジー自律探索デモ (read-only バックテスト + OOS 評価)
- `rates_volatility_model/` — 金利ボラ研究ノート
- `aisan_lbo_case/` — アイサンテクノロジー (4667.T) 非公開化 LBO ケーススタディ
- `notebooks/` — 単発の分析ノートブック置き場

Analytics (体験型インタラクティブ教科書, Jupyter Book + Plotly):

- `analytics/` — 線形代数・NN・ベイズ・フーリエ・ラプラス・微分方程式 (ODE/PDE)・機械学習の
  教科書群 + 統合オフラインポータル (`analytics/report/`)。索引は `analytics/README.md`

Samples:

- `csharp_calc/` — WinForms 電卓サンプル (C# / .NET 9)

Note: `re_invest_os` was moved out to its own repo (`~/re_invest_os`,
GitHub `ankimo1210/re_invest_os`) — it is no longer in this workspace.

Note: `land_price_api_app` (Streamlit PoC) was archived to
`_archive/land_price_api_app/` (2026-06-13). Its market-data engine was ported
to `~/re_invest_os` (`packages/market-data`).

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

<!-- BEGIN KAZ_PREFS -->
# User preferences

Use Japanese for chat conversations by default.
Keep responses concise and start with the conclusion.
If uncertain, say so clearly and do not guess.
Use English only when explicitly requested, or when technically necessary for code, commands, logs, file names, API names, configuration files, or quoted source text.
For time-sensitive topics, verify current information and cite sources when possible.

# AI agent operating rules

For coding, data analysis, and mathematical modeling tasks:

- Treat the task as context engineering, not just prompt following.
- Identify the minimum context needed: files, data, logs, assumptions, constraints, prior decisions, tools, and validation criteria.
- Prefer safe, copy-pasteable commands.
- Do not suggest or run destructive operations, migrations, deletes, force pushes, deploys, database changes, or irreversible changes without explicit confirmation.
- Use search first, then inspect narrow file ranges.
- Avoid reading entire large files, logs, notebooks, CSVs, parquet dumps, or generated outputs unless necessary.
- Prefer small, reviewable diffs.
- Check data quality before modeling.
- Establish a simple baseline before complex models.
- Define variables, units, assumptions, and validation criteria.
- Validate with tests, diagnostics, backtests, cross-validation, residual checks, or sensitivity analysis as appropriate.
- Do not declare completion until validation passes, or explain exactly why validation could not be run.
- If validation fails, fix the smallest relevant issue and rerun.
- Stop after 3 failed repair attempts and summarize the blocker, what was tried, and the next recommended step.

# Financial, rates, market, and time-series modeling rules

For financial, rates, market, and time-series analysis:

- Be explicit about units, conventions, calendars, time zones, sample periods, and data frequency.
- Clearly distinguish bp, %, decimals, price, yield, spread, DV01, duration, notional, and currency.
- Check business days, holidays, day count, compounding, settlement lag, and timestamp alignment.
- Avoid look-ahead bias, leakage, survivorship bias, and accidental use of future information.
- Separate signal, carry, roll-down, liquidity effects, funding effects, and mark-to-market effects when relevant.
- For backtests, report assumptions, transaction costs, slippage, sample period, turnover, drawdown, hit rate, Sharpe-like metrics, and regime sensitivity.
- Do not infer causality from correlation unless the identification strategy is explicitly justified.
- Prefer interpretable baselines and sanity checks before complex models.
- Quantify uncertainty when possible and clearly explain limitations, failure modes, and when not to use the model.
<!-- END KAZ_PREFS -->

## Decisions (ADR)

Load-bearing decisions whose rationale git log can't recover — rejected
alternatives, no-diff policy/constraint choices — go in `docs/decisions/` as
ADRs (`NNNN-slug.md`: Status / Context / Decision / Consequences). Rule of
thumb: if a future reader can't reconstruct the "why" from the diff/log, write
an ADR; otherwise leave it to git log. Propose a new ADR when a session makes a
significant design change or reversal. Repo-specific only — cross-project
lessons distill to `~/wiki`. No CHANGELOG/releases/runbooks/glossary until
there's a reader.
