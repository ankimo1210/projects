# re_invest_os — Claude Code Guide

## Purpose

AI-driven DD / pre-purchase audit web app for individual real-estate
investors. Paste a listing URL or upload a brochure PDF; the app extracts
assumptions, runs full cashflow / IRR / sensitivity / exit-scenario
analysis, and surfaces critique on over-optimistic inputs.

Privacy promise: user data is never sold to brokers. Designed buy-side.

Respond to the user in Japanese by default; code and identifiers in English.

## Architecture

| Layer | Path | Role |
|---|---|---|
| Web frontend | `apps/web/` | Next.js (pnpm workspace) — URL/PDF input, analysis dashboard |
| API backend | `apps/api/` (`re-invest-os-api`) | FastAPI. Routers split under `src/api/` with services in `src/api/services/` (LLM client, extractors, PII redaction, summariser, market context). SQLAlchemy + aiosqlite for `reio.db`. |
| Worker | `apps/worker/` | Background jobs (no pyproject yet; not in uv workspace). |
| Calculation engine | `packages/financial-engine/` (`re-engine`) | **Pure functions only**, no I/O. Cashflow, tax, IRR, sensitivity, exit, score, max-offer. Spec: `docs/architecture/calculation_engine_spec.md`. |
| Document schemas | `packages/document-schemas/` | Pydantic models for extracted property documents (no pyproject; reused via path import). |
| Shared schemas | `packages/shared-schemas/` | Cross-app schemas. |
| Docs | `docs/{architecture,design,product,roadmap,prompts,legal}/` | Full design documentation, including all LLM prompts. |

## Run & Verify

Python deps live in the workspace `.venv` at `~/projects/`. Node deps under
`re_invest_os/` are managed by pnpm (`pnpm-workspace.yaml`).

```bash
# One-time install (from workspace root)
cd ~/projects && make install         # = uv sync --all-packages

# Node deps (from this project)
cd ~/projects/re_invest_os && pnpm install

# Backend API
uv run --no-sync uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 \
  --app-dir apps/api/src

# Frontend
cd apps/web && pnpm dev

# Engine tests (the place where most bug fixes belong)
uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -v

# API tests
uv run --no-sync pytest re_invest_os/apps/api/tests/ -v
```

## Conventions

- **`re_engine` is pure**. No file I/O, no LLM calls, no global state. All
  inputs come in via `Assumptions` (Pydantic), all outputs via
  `AnalysisResult`. New calculations must follow that contract.
- **`engine_version`** (semver) is written into every `AnalysisResult`.
  Bump major on backwards-incompatible math changes.
- **LLM calls live in `apps/api/src/api/services/`**, never inside
  `re_engine`. The engine must remain testable without network access.
- **Prompts are versioned files** under `docs/prompts/`. Reference them by
  filename + version (`property_brochure_v4.md`, etc.); do not inline
  prompts in code without keeping the file in sync.
- **PII**: `services/pii.py` redacts before any external LLM call. Do not
  bypass it.
- Workspace cross-import: `apps/api` depends on `re-engine` via
  `[tool.uv.sources] re-engine = { workspace = true }` at workspace root.

## Gotchas

- **`reio.db`** (local SQLite, ~committed) is the analysis history store.
  Do not commit migrations that would silently rewrite existing rows.
- **`apps/worker/` and `packages/document-schemas/` have no `pyproject.toml`**,
  so they are NOT uv workspace members. They are still used by `apps/api`
  via relative path imports / sibling code references — be careful when
  reorganising.
- **`apps/api/.env`** must hold the LLM key (`OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY`). Never commit.
- Frontend and backend run on separate ports (3000 / 8000); the dev setup
  expects both. If only API is needed (engine work), skip pnpm.
- Heavy docs under `docs/` (LLM prompts, architecture spec) are
  load-bearing — when changing engine math, also update
  `docs/architecture/calculation_engine_spec.md`.
