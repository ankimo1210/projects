# Copilot instructions — projects workspace

Follow the canonical workspace guide in [`AGENTS.md`](../AGENTS.md).

Key points:

- Multi-project monorepo: each top-level directory is an independent
  project. Read that project's `README.md` (and `CLAUDE.md` /
  `AGENTS.md` if present) before editing; stay scoped to one project.
- Respond to the user in Japanese; code, identifiers, and commits in
  English.
- Python runs in a single uv workspace rooted at the repo root
  (`uv sync --all-packages`, `uv run --no-sync pytest <project>/tests`).
- Never inspect `_data/`, `_logs/`, `_archive/`, `_scratch/`, generated
  outputs, or heavy binaries (see `.agentignore`).
- Only `.env.example` is tracked — never commit real secrets.
