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
create a stray venv. Non-Python projects: `EitanQuest` / `NeonThread`
(Xcode), `ts-rosetta` (pnpm), `pokemon` (npm), `csharp_calc` (.NET).

The root `conftest.py` imports same-named packages explicitly so that a
full-workspace `pytest` run does not break them via namespace packages
(pytest 9 behavior); keep it when touching test config.

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
