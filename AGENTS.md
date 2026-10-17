# AGENTS.md — projects workspace guide

Canonical agent guide for this workspace. `CLAUDE.md` and
`.github/copilot-instructions.md` defer to this file.

## What this repo is

A personal multi-project workspace: each top-level directory is an
independent project, managed together in one git repository. Docs are
Japanese-first; code, identifiers, and commit messages are English. The
project index is in the root [`README.md`](README.md).

## Workspace policy

- **Respond to the user in Japanese** unless asked otherwise.
- **Scope your work to one project.** Follow its `AGENTS.md` and consult its
  `README.md` as needed. Do not grep or scan the whole repository; search
  within the project directory you are working on.
- **Paths:** the repository lives at `/home/kazumasa/projects` in Ubuntu WSL.
  Run Git and build commands in WSL with Linux paths. For Windows-side file
  links or operations, use `//wsl.localhost/Ubuntu/home/kazumasa/projects/...`
  (or the corresponding UNC path for a worktree), and verify the target exists.
  Do not combine Windows drive paths with WSL paths.
- **Do not inspect by default:** `_data/`, `_logs/`, `_archive/`,
  `_scratch/`, `_docs/` (ephemeral notes), generated outputs
  (`models/*/`, `reports/`, `**/dist/`, `**/build/`), lock files, and
  heavy binaries. `.agentignore` is the machine-readable version of this
  list.
- **Secrets:** only `.env.example` files are tracked. Never commit real
  keys; real `.env` files are gitignored and stay local.
- Preserve user changes; make the smallest coherent change; ask before
  adding production dependencies or making broad refactors.

## Large outputs & worktrees

Research runs here have produced 100+ GiB of intermediate data that nobody
needed and that one routine cleanup then destroyed (johnhull RB-F04,
2026-10-17). Keep data small by design:

- **Estimate before you run.** Before a long or large run, estimate its disk
  and peak memory (runs × arrays × bytes). If one output root may exceed
  30 GiB, write the estimate in the project's design/status doc and get the
  user's approval first. Record the measured size (`du -sh`) when it finishes.
- **Store what cannot be regenerated, nothing else.** Keep the code commit,
  seeds, config, input hashes, final results, and verification summaries.
  Regenerate intermediate arrays deterministically and compare hashes instead
  of saving them. Record a failed run as a summary (where, why, hashes), not
  as its raw arrays.
- **One output root per run.** A root replaced by a newer completed run may
  be deleted. Do not keep every retry "for the record".
- Compress (`np.savez_compressed`, Parquet), share identical bytes, and
  never commit large binaries (pre-commit caps added files at 2 MB). Heavy
  artifacts that must survive go to the vaults in
  `docs/decisions/0004-artifact-storage-and-evidence.md`.
- **Untracked working data lives under `_data/<project>/`**, never inside a
  worktree or a tool scratch directory such as `.superpowers/` (skills may
  put small notes there, not outputs).
- **`git worktree remove` silently deletes gitignored files inside the
  worktree.** Before removing one, run `git -C <wt> status --ignored --short`
  and `du -sh <wt>`, move anything needed to `_data/`, and check that no other
  branch, worktree, or doc references it. Branch containment proves only that
  tracked files are safe.

johnhull adds research-specific rules in `johnhull/AGENTS.md`
("研究データの保存方針").

## Agent instruction files

| Layer | Canonical file | Notes |
|---|---|---|
| Global (all repos) | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` symlinks to it; backed up in `agentic-setup/` |
| Workspace | `AGENTS.md` (this file) | |
| Project | `<project>/AGENTS.md` | Project-specific rules only |

- `AGENTS.md` is the canonical text at every level. Claude Code reads only
  `CLAUDE.md`, so each directory with an `AGENTS.md` also has a `CLAUDE.md`
  adapter that imports it with `@AGENTS.md`. Never copy the guide into
  `CLAUDE.md`, or the two drift apart.
- `.github/copilot-instructions.md` links to `AGENTS.md` with a normal
  Markdown link; Copilot does not expand `@` imports.
- Do not repeat global or workspace rules in a project guide; write only what
  differs or is specific to that project.
- Personal skills live in `~/.claude/skills/`; settings, Codex rules, and
  skills are backed up in `agentic-setup/`. That directory is a backup, not
  the live configuration: change the live file first, then sync the copy as
  its README describes.

## Python: single uv workspace

One `.venv` at the repo root manages every Python member (see
`[tool.uv.workspace]` in the root `pyproject.toml`).

```bash
uv sync --all-packages              # install everything (run at repo root)
uv run --no-sync pytest <project>/tests   # test one project
make lint / make test / make fmt    # cross-workspace checks
```

Run `uv` from the repo root — running it inside a member directory can
create a stray venv. Non-Python projects and their toolchains are listed in
the root `README.md`.

- Every member declares what it imports, including indirect imports and the
  dev tooling its own CI invokes; the shared `.venv` hides omissions that
  `uv sync --package <member>` exposes. See
  `docs/decisions/0002-workspace-green-and-declared-dependencies.md`.
- A historical green run does not establish the cause of a current failure.
  Compare with a relevant baseline before attributing failures to a change.

### What `make test` covers

`make test` runs only the `testpaths` list in the root `pyproject.toml` with
single-threaded BLAS/OpenMP (`OMP_NUM_THREADS=1` etc., which the johnhull
research studies require; a bare `pytest` run fails them), plus
`sde-check` (typecheck + lint + build + node tests for
`analytics/differential_equation/sde-book`, skipped with a notice when `npm`
is not on PATH). Python suites outside the uv workspace (WSET, the WSET
corpus, aisan_lbo_case, interactive-email-demo, komorebi-3d,
tokyo_subway_3d) run with `make test-extra`. "Workspace green" does not mean
every project was verified; run the suite you actually touched.

Traps when adding a suite:

- A member whose directory name equals its package name (e.g.
  `deep_hedge_price`) needs a matching `import` in the root `conftest.py` as
  well as a `testpaths` line; otherwise pytest 9 namespace packages make it
  fail with `ModuleNotFoundError: No module named '<pkg>.config'`. Keep that
  conftest when touching test config.
- `analytics/report` and `johnhull/report` are not workspace members; their
  test conftests prepend their own directory to `sys.path`, so their package
  names must stay distinct (`analytics_portal` vs `report_builder`) or one
  suite silently imports the other's package in a full run.
- `WSET/wset_l3_question_corpus` is a standalone uv project, not a member;
  `uv sync --all-packages` does not install its `rapidfuzz`. Sync it in its
  own directory.

## Toolchains installed in WSL (verified 2026-10-17)

`uv`, `cargo` / `rustc`, `node` / `npm`, `nvcc` / `g++` / `make` are present.
**`dotnet` and `swift` / `xcodebuild` are not**, so `csharp_calc`,
`CsharpApp`, `EitanQuest`, `NeonThread`, `WSET`, and `My Tianjin` cannot be
built or tested here — say so rather than reporting them as checked.
`pnpm` is not on PATH and `corepack` resolves to a Windows shim that bash
cannot exec; use `npx --yes pnpm@11.1.0 <cmd>` for the pnpm projects.

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

Keep requested knowledge captures in this repository: project docs for
project-specific material, `docs/knowledge/` for shared material. Keep notes
concise, dated where facts can change, and free of secrets or
employer/client-confidential content. The former `~/wiki` is a legacy
archive; do not write new notes there.

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
