# CLAUDE.md — projects workspace

The canonical workspace guide is @AGENTS.md — follow it
(Workspace Policy, uv workspace usage, docs layers).

Claude-specific notes:

- Respond in Japanese; code, identifiers, and commits in English.
- Read the target project's `README.md` first, then its `CLAUDE.md` if
  present (several projects have their own with run/verify commands).
- Cross-project checks go through the root `Makefile`
  (`make lint` / `make test`); single-project tests via
  `uv run --no-sync pytest <project>/tests` from the repo root.
- HTML reports and Artifacts follow `docs/templates/claude-report/`
  (AGENTS.md § HTML reports & Artifacts). Load the `artifact-design` and
  `dataviz` skills as usual, then apply that template as the design system
  rather than inventing a new palette per report.
