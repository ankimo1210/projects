# Claude Code Workspace Guide

This root is a multi-project workspace.

## Language

- Respond to the user in Japanese by default.
- Write code, comments, filenames, commit messages, and technical identifiers primarily in English.
- Keep explanations concise unless asked for detail.

## Environment

- Primary environment: Windows 11 + WSL2 + VSCode
- Assume the repo is opened from WSL
- Prefer Linux paths over `/mnt/c` paths

## Coding Style

- Prefer Python for data tasks unless the project uses another stack.
- Make minimal, surgical changes first.
- Before editing, explain the plan briefly.
- After editing, summarize changed files and validation steps.

## Workspace Policy

Do not scan the whole root by default. First identify the relevant project.
Prefer targeted file reads and the project's `README.md` / `CLAUDE.md` before broad search.

### Active Projects

Applications:

- `land_price_api_app/` — 地価公示・不動産取引ローカルアプリ (FastAPI + DuckDB)
- `re_invest_os/` — 不動産買付前 DD Web アプリ (Next.js + FastAPI + Supabase)
- `gto/` — GTO ポーカー分析アプリ (Rust + FastAPI + Next.js)
- `stock/` — `stockkit` 株式分析ツールキット (Python + Dash)
- `market-viz/` — マーケット可視化アプリ (Streamlit + Plotly + DuckDB)
- `nbody-gpu/` — GPU N 体シミュレーション (CuPy + VisPy)
- `line_backup/` — LINE バックアップ解析 CLI (Python)

Research / notebooks:

- `johnhull/`, `rates_volatility_model/`, `notebooks/`

Each project has its own `README.md` and sometimes its own `CLAUDE.md` /
`AGENTS.md` — prefer those over the workspace root for project-specific work.

### Shared Tooling

- Python uses a single uv workspace rooted at `~/projects/`. Members are
  listed in the root `pyproject.toml` (`[tool.uv.workspace]`).
- Workspace-wide make targets (run from the repo root): `make install`
  (= `uv sync --all-packages`), `make lint`, `make fmt` / `make fmt-fix`,
  `make test`, `make clean`, `make tree`. `make help` lists them.
- Cross-project recipes / worklogs live in `_docs/`.

## Definition of Done

Not done until: the full test suite passes (not just new tests); new behavior has a
test that fails without the change; real output was observed (not just an exit code);
and the feature was exercised through its real entry point (UI / API / CLI). Report any
gap explicitly.

Project-specific checks (when they apply):

- **UI wired** — new fields actually render on the page (visit it).
- **Types regenerated** — if the API schema changed, regenerate `api.ts`.
- **Test mocks** — monkeypatch where the name is looked up, not where it is defined.
- **Dead code removed** — delete replaced functions/imports, don't abandon them.
- **Nav/links updated** — new pages are reachable from nav.
- **Numerical / CPU-GPU** — verify against a hand-computed or reference value; if both
  CPU and GPU implementations exist, they must agree on shared inputs.

## Reporting

State bugs, limitations, and skipped verification plainly — no "honesty" labels,
emoji badges, or banned-word lists. When you claim a test passed, quote 1-3 lines of
its actual output. When something is unverified, say which parts and why.

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
