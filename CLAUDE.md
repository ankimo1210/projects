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

## Token And Context Budget Policy

Before substantial work:
- Check whether this is an old resumed session.
- If context is above 150k tokens, recommend `/clear` before continuing.
- Do not scan the whole repository unless explicitly requested.
- Do not read large notebooks, logs, generated files, data files, lock files, or vendor directories unless necessary.
- Prefer targeted file reads over broad grep/find.
- Prefer the project's `README.md` (and `CLAUDE.md` / `AGENTS.md` when present) before source search.
- When switching to an unrelated task, ask the user to run `/clear`.
- When continuing a long task, suggest `/compact` with a task-focused summary.

## Definition of Done

A task is "Done" ONLY when ALL of the following are true. If any is missing,
the task is NOT done — report the gap explicitly.

### Evidence required (mandatory)

- **Existing tests still pass** — full test suite (not just new tests)
- **New behavior has a test** — at least one assertion that fails without the change
- **Output was observed** — actual program output was examined, not just exit code
- **Known input → expected output** — at least one concrete (input, output) pair verified
- **Integration verified** — feature was used through its real entry point (UI, API, CLI),
  not just unit-tested

### Domain-specific checks (verify all that apply)

- **UI wired** — new data/fields are actually displayed on screen (visit the page)
- **Test mocks correct** — monkeypatches target the module where the name is looked up,
  not where it is defined
- **Types regenerated** — if the API schema changed, `api.ts` has been regenerated
- **Dead code removed** — replaced functions/imports are deleted, not just abandoned
- **Nav/links updated** — new pages are reachable from nav and relevant link surfaces
- **Numerical algorithm** — verified against hand-computed answer OR reference implementation
- **CPU/GPU parity** — if both implementations exist, they agree on shared inputs

Skipping this check and saying "done" is the primary source of bugs found in review.

## Honest Reporting Rules

When reporting progress, distinguish *what was verified* from *what was assumed*.

### Banned phrases (without evidence)

These suggest completion but provide no proof:

- "実装完了" / "Done" / "Working" / "Correct" / "Should work"
- "正しく実装した" / "問題ないはず" / "動くはず"

### Required phrases (with evidence)

- ✅ "Test `<name>` passed: <quote actual output>"
- ✅ "Compiled clean, no errors"
- ⚠️ "Compiles, but integration not yet verified"
- ❌ "Not tested yet" / "Untested edge case: X"
- 📋 "Verified: A, B. NOT verified: C, D."

### When uncertain

Default to **未完了** (incomplete). Better to under-claim and verify than
over-claim and surprise.

### Test-output discipline

When a test passes, quote 1-3 lines of the actual output in the report.
This forces the test to actually have been run.

Example:
> ✅ `cargo test cfr_kuhn_poker` passed.
> ```
> test test_kuhn_nash_equilibrium ... ok
> ```

### When a verification step is skipped

State it explicitly. Do not let unverified parts pass as verified:

> ⚠️ Verified: tree structure (15 nodes confirmed), single-spot solve runs.
> ❌ Not verified: convergence to Nash, multi-spot batching, CPU/GPU parity.

This makes reviewers and the user aware of what to test before trusting the work.

## Algorithm Implementation Protocol

For any non-trivial algorithm (CFR, search, ML inference, etc.):

1. **Reference first** — find a known-correct version (paper, OSS, textbook) and
   match its structure before introducing optimizations.
2. **Small known cases** — test against hand-computable inputs (e.g., Kuhn poker
   for CFR) before scaling to production size.
3. **Property tests** — verify invariants that must hold (zero-sum, monotonic
   convergence, probability sums = 1).
4. **Differential testing** — if multiple implementations exist (CPU, GPU,
   reference), they must agree on shared inputs. Catch divergence early; do not
   accumulate features on top of a non-validated base.
5. **Optimization comes last** — only after correctness is proven. Premature
   GPU/SIMD/parallelization hides bugs.

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
