# AGENTS.md — projects workspace guide

Canonical agent guide for this workspace. `CLAUDE.md` and
`.github/copilot-instructions.md` defer to this file.

## What this repo is

A personal multi-project workspace: each top-level directory is an
independent project, managed together in one git repository. Docs are
Japanese-first; code, identifiers, and commit messages are English.

**Start here:** read the target project's `README.md` first (source of
truth), then its `CLAUDE.md` / `AGENTS.md` if present. The project index
lives in the root [`README.md`](README.md).

## Workspace Policy

- **Scope your work to one project.** Do not grep or scan the whole
  repository; search within the project directory you are working on.
- **Do not inspect by default:** `_data/`, `_logs/`, `_archive/`,
  `_scratch/`, `_docs/` (ephemeral notes), generated outputs
  (`models/*/`, `reports/`, `**/dist/`, `**/build/`), lock files, and
  heavy binaries. `.agentignore` is the machine-readable version of this
  list.
- **Respond to the user in Japanese** unless asked otherwise.
- **Secrets:** only `.env.example` files are tracked. Never commit real
  keys; real `.env` files are gitignored and stay local.
- Preserve user changes; make the smallest coherent change; ask before
  adding production dependencies or making broad refactors.

## Python: single uv workspace

One `.venv` at the repo root manages every Python member (see
`[tool.uv.workspace]` in the root `pyproject.toml`).

```bash
uv sync --all-packages              # install everything (run at repo root)
uv run --no-sync pytest <project>/tests   # test one project
make lint / make test / make fmt    # cross-workspace checks
```

Run `uv` from the repo root — running it inside a member directory can
create a stray venv. Non-Python projects: `EitanQuest` / `NeonThread` /
`WSET` / `My Tianjin` (Xcode), `ts-rosetta` / `b737-ops-sim` (pnpm),
`pokemon` (npm), `eagle` (cargo + npm), `csharp_calc` / `CsharpApp`
(.NET), `cpp_algo_lab` (make + CUDA).

The root `conftest.py` imports same-named packages explicitly so that a
full-workspace `pytest` run does not break them via namespace packages
(pytest 9 behavior); keep it when touching test config.

`make lint` and the full-workspace `pytest` are green as of 2026-08-16
(2977 passed, 45 skipped), so a red
result means the change under test broke something — diagnose it rather than
assuming it predates you. Every member declares what it imports, including
indirect (`health` declares `scipy` for `pandas.corr(method="spearman")`) and
dev tooling its own CI invokes; the shared `.venv` hides omissions that
`uv sync --package <member>` exposes. See
`docs/decisions/0002-workspace-green-and-declared-dependencies.md`.

**That green is not full coverage.** `make test` runs only the `testpaths`
list in the root `pyproject.toml`, and three suites are missing from it —
`deep_hedge_price/tests` (206), `analytics/fourier/tests` (47), and
`johnhull/report/tests` (10). All 263 run green when invoked directly, but
never under `make test`. Do not read "workspace green" as "every project
verified"; run the suite you actually touched. Adding them back is not
symmetric: `analytics/fourier` only needs the `testpaths` line (its import
name `fourier_book` differs from its directory), while `deep_hedge_price`
has dir name == package name and so needs a matching `import` in the root
`conftest.py` as well — `testpaths` alone makes it fail with
`ModuleNotFoundError: No module named 'deep_hedge_price.config'`.

`WSET/wset_l3_question_corpus` is a standalone uv project, not a member —
`uv sync --all-packages` does not install its `rapidfuzz`, so collecting it
from the root errors. Sync it in its own directory.

## Toolchains actually installed (WSL2, verified 2026-08-16)

`cargo` / `rustc`, `node` / `npm`, `nvcc` / `g++` / `make` are present.
**`dotnet` and `swift` / `xcodebuild` are not**, so `csharp_calc`,
`CsharpApp`, `EitanQuest`, `NeonThread`, `WSET`, and `My Tianjin` cannot be
built or tested here at all — say so rather than reporting them as checked.
`pnpm` is not on PATH either and `corepack` resolves to a Windows shim that
bash cannot exec; use `npx --yes pnpm@11.1.0 <cmd>` for `ts-rosetta` and
`b737-ops-sim`.

## Docs & knowledge layers (ADR 0001)

See `docs/decisions/0001-workspace-docs-and-knowledge-layers.md`.

| Location | Role |
|---|---|
| `<project>/README.md` + `<project>/docs/` | Source of truth for that project |
| `docs/decisions/` | Workspace-level ADRs (load-bearing "why" only) |
| `docs/superpowers/` | Skill-generated plans/specs (generated artifacts) |
| `_docs/` | Ephemeral worklogs/handoffs — not curated, do not rely on |
| git log | The what/when history |

Write an ADR only when a future reader cannot reconstruct the "why"
from the diff or log.
