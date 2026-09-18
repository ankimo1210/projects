# AGENTS.md — projects workspace guide

Canonical agent guide for this workspace. `CLAUDE.md` and
`.github/copilot-instructions.md` defer to this file.

## What this repo is

A personal multi-project workspace: each top-level directory is an
independent project, managed together in one git repository. Docs are
Japanese-first; code, identifiers, and commit messages are English.

Follow the target project's applicable `AGENTS.md` / `CLAUDE.md`. Consult
its `README.md` for project context as needed; the project index is in the
root [`README.md`](README.md).

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

A historical green run does not establish the cause of a current failure.
Compare with a relevant baseline before attributing failures to this change.
Every member declares what it imports, including
indirect (`health` declares `scipy` for `pandas.corr(method="spearman")`) and
dev tooling its own CI invokes; the shared `.venv` hides omissions that
`uv sync --package <member>` exposes. See
`docs/decisions/0002-workspace-green-and-declared-dependencies.md`.

**That green is not full coverage.** `make test` runs only the `testpaths`
list in the root `pyproject.toml`, and two suites are still missing from it —
`deep_hedge_price/tests` (206) and `johnhull/report/tests` (registered since 2026-09-14). Both run
green when invoked directly, but never under `make test`. Do not read
"workspace green" as "every project verified"; run the suite you actually
touched. `analytics/fourier/tests` (47) was in this list until 2026-08-16 and
needed only the `testpaths` line, because its import name `fourier_book`
differs from its directory; `deep_hedge_price` has dir name == package name
and so needs a matching `import` in the root `conftest.py` as well —
`testpaths` alone makes it fail with
`ModuleNotFoundError: No module named 'deep_hedge_price.config'`.

`make test` also runs `sde-check` (typecheck + lint + build + 12 node tests
for `analytics/differential_equation/sde-book`), skipping it with a printed
notice when `npm` is not on PATH.

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

## Docs & knowledge layers

See `docs/decisions/0001-workspace-docs-and-knowledge-layers.md` and
`docs/decisions/0003-keep-knowledge-in-repository.md`.

| Location | Role |
|---|---|
| `<project>/README.md` + `<project>/docs/` | Source of truth for that project |
| `docs/knowledge/` | Shared environment notes and reusable troubleshooting knowledge |
| `docs/decisions/` | Workspace-level ADRs (load-bearing "why" only) |
| `docs/superpowers/` | Skill-generated plans/specs (generated artifacts) |
| `docs/templates/` | Reusable output formats (see HTML reports below) |
| `_docs/` | Ephemeral worklogs/handoffs — not curated, do not rely on |
| git log | The what/when history |

Keep requested knowledge captures in this repository: use the relevant
project docs for project-specific material and `docs/knowledge/` for shared
material. Keep notes concise, dated where facts can change, and free of
secrets or employer/client-confidential content. The former `~/wiki` is a
legacy archive; do not write new notes there.

Write an ADR only when a future reader cannot reconstruct the "why"
from the diff or log.

## Development progress & recaps

For ongoing development, reuse the project's existing roadmap or status
document; if none exists and progress needs to persist, use its
`docs/STATUS.md`. Reconcile it with evidence when resuming work and update
the current state when meaningful progress or a plan change occurs.
Include the goal and completion criteria, milestone-wide done/current/pending
status, validation evidence, blockers, next steps, and the update date.
Distinguish implemented-but-unverified from complete; reflect approved plan
changes in remaining work and completion criteria. Preserve other agents' work.

Keep progress in that document, not in instruction files or an append-only
turn diary. For a compact final recap and status guidance, consult
`docs/templates/development-recap.md` when needed. Simple tasks need no new
status document; do not initialize other projects' progress speculatively.

## HTML reports & Artifacts

Any HTML report or published Artifact in this workspace uses
**`docs/templates/claude-report/`** unless the user asks for something else.
`tokens.css` is the source of truth; `skeleton.html` is the skeleton;
`README.md` covers usage and the traps.

- Paste `tokens.css` into the page's `<style>` block — an Artifact must be
  self-contained, and the CSP admits no external stylesheet but Google Fonts.
- Take every color from a `var(--...)` token; never write a raw hex in the page.
  Chart series are `--series-1` / `--series-2`, validated on both surfaces.
- Render the page and look at it before publishing. A color validator does not
  catch collided labels or overflow.

Changing the palette or the type pairing means editing `tokens.css`, not the
individual report — that is the point of the file.
