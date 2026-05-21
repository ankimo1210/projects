# AI Agent Prompt: `~/projects` Workspace Restructure

## Role

You are an implementation agent helping restructure a personal multi-project development workspace.

The current workspace root is:

```text
~/projects
```

Do **not** create another nested `projects/` directory.  
The current root itself is already the projects workspace.

The goal is to make the workspace more efficient for AI-assisted development by separating:

- real projects
- shared AI docs
- heavy data
- logs
- archives
- one-off scratch work
- VS Code workspaces

This is partly to avoid huge context/cache usage in Claude Code, Codex, Copilot CLI, and other AI coding agents.

---

## Critical Requirements

### Safety first

Before moving or editing anything:

1. Inspect the current tree.
2. Check `git status` in each relevant project directory if it is a Git repo.
3. Do **not** delete source files.
4. Do **not** delete notebooks.
5. Do **not** delete data unless explicitly told.
6. Do **not** expose or print secrets from `.env`.
7. Prefer `git mv` when the directory is inside a Git repo.
8. Prefer `mv` only for non-Git workspace-level moves.
9. Make small, reviewable changes.
10. After every meaningful move, run a quick validation.

### Important path rewrite requirement

Some files contain hard-coded relative paths.  
When moving directories, you must update internal paths accordingly.

Examples of path-sensitive files may include:

- `.env`
- `.env.example`
- `config.py`
- `db.py`
- `run_local.sh`
- `run_sync.py`
- `run_backfill.py`
- notebooks
- scripts that read/write `data/`
- Streamlit launch scripts
- README / AGENTS / CLAUDE docs
- tests that refer to fixtures or local files

You must search for old paths and update them after each move.

Search examples:

```bash
rg "land_price_api_app/data|data/processed|data/raw|land_prices\.duckdb|backfill_log|sync_log|streamlit\.log|notebooks/output|rates_volatility_model/venv" .
```

Do not blindly replace everything. Review each occurrence and update only when needed.

---

## Target Workspace Structure

Create the following top-level structure under `~/projects`:

```text
~/projects/
  AGENTS.md
  CLAUDE.md
  .gitignore
  .agentignore
  .env.example

  _docs/
    ai/
      handoffs/
      worklogs/
      session_registry.md
    capability_index/
    recipes/

  _data/
    land_price/
      raw/
      processed/
      backup/
    real_estate/
      raw/
      processed/

  _logs/
    ai-terminal/
    ai-diffs/
    app/

  _scratch/
    README.md
    notebooks/
    scripts/
    outputs/
    tmp/

  _archive/
    old_notebooks/
    oneoff_tests/
    old_projects/
    tmp/

  _workspaces/
    land_price.code-workspace
    rates_volatility.code-workspace
    real_estate.code-workspace

  land_price_api_app/
  rates_volatility_model/
  johnhull/
  notebooks/
  reports/
```

Do not force every item to exist if it is unnecessary, but at minimum create:

```text
_docs/
_data/
_logs/
_scratch/
_archive/
_workspaces/
```

---

## Phase 0: Preflight

Run from `~/projects`.

```bash
pwd
find . -maxdepth 2 -type d | sort
find . -maxdepth 2 -type f | sort | sed -n '1,200p'
```

Check whether the root is a Git repo:

```bash
git rev-parse --show-toplevel 2>/dev/null || true
git status --short 2>/dev/null || true
```

Check important child projects:

```bash
for d in land_price_api_app rates_volatility_model johnhull notebooks; do
  if [ -d "$d/.git" ]; then
    echo "=== $d ==="
    git -C "$d" status --short
  fi
done
```

Record a preflight note in:

```text
_docs/ai/worklogs/YYYY-MM-DD-restructure.md
```

Include:

- timestamp
- current branch if any
- current Git status
- high-level plan
- directories to be moved
- known risks

---

## Phase 1: Create Shared Directories

Create the workspace-level directories.

```bash
mkdir -p \
  _docs/ai/handoffs \
  _docs/ai/worklogs \
  _docs/capability_index \
  _docs/recipes \
  _data/land_price/raw \
  _data/land_price/processed \
  _data/land_price/backup \
  _data/real_estate/raw \
  _data/real_estate/processed \
  _logs/ai-terminal \
  _logs/ai-diffs \
  _logs/app \
  _scratch/notebooks \
  _scratch/scripts \
  _scratch/outputs \
  _scratch/tmp \
  _archive/old_notebooks \
  _archive/oneoff_tests \
  _archive/old_projects \
  _archive/tmp \
  _workspaces
```

Create `_scratch/README.md`:

```md
# Scratch area

This directory is for one-off notebooks, quick scripts, experiments, and temporary analysis.

Rules:
- Put disposable experiments here first.
- Organize by month: `notebooks/YYYY-MM/`, `scripts/YYYY-MM/`, `outputs/YYYY-MM/`.
- Do not store secrets.
- Do not treat this as production code.
- If an experiment becomes reusable, promote it to a proper project directory.
- If it is no longer useful, move it to `_archive/` or delete it.

AI agents:
- Do not scan this directory unless explicitly requested.
- Do not use scratch code as canonical implementation.
- Prefer project code and `_docs/capability_index/` first.
```

---

## Phase 2: Add Workspace Ignore Files

Create or update `~/projects/.agentignore`.

```gitignore
# Heavy data and outputs
_data/
_logs/
_archive/
tmp/
test_app/

# Scratch is intentionally excluded unless explicitly requested
_scratch/

# Binary / large files
**/*.duckdb
**/*.duckdb.wal
**/*.parquet
**/*.geojson
**/*.csv
**/*.xlsx
**/*.pdf
**/*.log
**/*_log.txt

# Python generated
**/__pycache__/
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/.ipynb_checkpoints/
**/venv/
**/.venv/

# Node / generated
**/node_modules/
**/dist/
**/build/

# Windows metadata
**/*:Zone.Identifier
```

Create or update `~/projects/.gitignore`.

```gitignore
# secrets
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.ipynb_checkpoints/

# workspace-level generated data
_data/
_logs/
_archive/tmp/
_scratch/outputs/
_scratch/tmp/

# heavy local data
*.duckdb
*.duckdb.wal
*.parquet
*.geojson
*.csv
*.xlsx

# logs
*.log
*_log.txt
backfill_log*.txt
sync_log*.txt
streamlit.log

# OS / Windows
.DS_Store
Thumbs.db
*:Zone.Identifier
```

Be careful: if existing `.gitignore` has useful project-specific rules, merge rather than overwrite.

---

## Phase 3: Add Root Agent Guides

Create or update `~/projects/AGENTS.md`.

```md
# Workspace agent guide

This root is a multi-project workspace. Do not scan the whole root by default.

## Active projects

- `land_price_api_app/`
- `rates_volatility_model/`
- `johnhull/`
- `notebooks/`

## Shared docs

Use `_docs/capability_index/` first to find relevant files.

## Do not inspect by default

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
- `*.ipynb` unless explicitly requested
- `venv/`
- `__pycache__/`

## Workflow

1. Identify the relevant project.
2. Read the project README and AGENTS.md.
3. Read the relevant capability index in `_docs/capability_index/`.
4. Inspect only targeted source files.
5. Avoid broad search unless necessary.

## Context policy

- Avoid resuming old AI sessions unless continuing the exact same task.
- Use handoff summaries for new phases.
- If context is large, recommend `/clear` or `/compact` before continuing.
- Do not read heavy data files unless explicitly requested.
```

Create or update `~/projects/CLAUDE.md`.

```md
# Claude Code workspace guide

This root is a multi-project workspace.

Do not scan the whole root by default. First identify the relevant project.

## Token and context budget policy

Before substantial work:
- Check whether this is an old resumed session.
- If context is above 150k tokens, recommend `/clear` before continuing.
- Do not scan the whole repository unless explicitly requested.
- Do not read large notebooks, logs, generated files, data files, lock files, or vendor directories unless necessary.
- Prefer targeted file reads over broad grep/find.
- Prefer `_docs/capability_index/` and project docs before source search.
- When switching to an unrelated task, ask the user to run `/clear`.
- When continuing a long task, suggest `/compact` with a task-focused summary.

## Do not inspect by default

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
- `venv/`
- `.venv/`
- `__pycache__/`
```

---

## Phase 4: Move Heavy Land Price Data Out of App

Current likely source:

```text
land_price_api_app/data/raw
land_price_api_app/data/processed
```

Target:

```text
_data/land_price/raw
_data/land_price/processed
```

Before moving, inspect:

```bash
find land_price_api_app/data -maxdepth 2 -type f | sed -n '1,80p'
```

Move carefully:

```bash
mkdir -p _data/land_price

if [ -d land_price_api_app/data/raw ]; then
  mkdir -p _data/land_price/raw
  mv land_price_api_app/data/raw/* _data/land_price/raw/ 2>/dev/null || true
fi

if [ -d land_price_api_app/data/processed ]; then
  mkdir -p _data/land_price/processed
  mv land_price_api_app/data/processed/* _data/land_price/processed/ 2>/dev/null || true
fi
```

If empty, remove old directories:

```bash
find land_price_api_app/data -type d -empty -delete 2>/dev/null || true
```

Then update paths.

Search:

```bash
rg "land_price_api_app/data|data/processed|data/raw|land_prices\.duckdb|DUCKDB_PATH|RAW_DIR|PROCESSED_DIR" land_price_api_app .env.example AGENTS.md CLAUDE.md _docs -n
```

Expected new `.env.example` style:

```env
REINFOLIB_API_KEY=
DUCKDB_PATH=../_data/land_price/processed/land_prices.duckdb
LAND_PRICE_RAW_DIR=../_data/land_price/raw
LAND_PRICE_PROCESSED_DIR=../_data/land_price/processed
LOG_LEVEL=INFO
```

If app code assumes paths relative to `land_price_api_app`, update it to read from environment variables with safe defaults.

Preferred Python pattern:

```python
from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent

DUCKDB_PATH = Path(
    os.getenv(
        "DUCKDB_PATH",
        str(WORKSPACE_DIR / "_data" / "land_price" / "processed" / "land_prices.duckdb"),
    )
)
```

Adjust `parents[...]` based on actual file location.

---

## Phase 5: Move Logs Out of Project Directories

Move obvious logs to `_logs/app/<project>/`.

Examples:

```bash
mkdir -p _logs/app/land_price_api_app

find land_price_api_app -maxdepth 1 -type f \( -name "*.log" -o -name "*_log.txt" -o -name "backfill_log*.txt" -o -name "sync_log*.txt" \) -print
```

Then:

```bash
find land_price_api_app -maxdepth 1 -type f \( -name "*.log" -o -name "*_log.txt" -o -name "backfill_log*.txt" -o -name "sync_log*.txt" \) \
  -exec mv {} _logs/app/land_price_api_app/ \;
```

Update references if any scripts write logs to old project root.

Search:

```bash
rg "backfill_log|sync_log|streamlit\.log|_logs/app" land_price_api_app -n
```

Prefer log paths from environment variables or `logs_dir`.

---

## Phase 6: Clean Generated Python Artifacts

Remove generated caches only.

```bash
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
find . -type d -name ".ipynb_checkpoints" -prune -exec rm -rf {} +
```

Do not delete source code.

For `rates_volatility_model/venv`, do not delete automatically unless instructed.  
Instead, report:

```text
rates_volatility_model/venv exists and should normally be recreated via .venv or project env management.
Recommend deleting it after confirming it is not needed.
```

---

## Phase 7: Create Capability Index Stubs

Create `_docs/capability_index/land_price_api_app.md`.

```md
# Land Price API App Capability Index

## Run local app

Relevant files:
- `land_price_api_app/app.py`
- `land_price_api_app/run_local.sh`
- `land_price_api_app/config.py`

Do not inspect:
- `_data/`
- parquet files
- duckdb files
- geojson files
- logs

Validation:
- run the local app only if requested
- otherwise run import checks or targeted tests

## Sync public notice land prices

Relevant files:
- `land_price_api_app/sync_public_notice.py`
- `land_price_api_app/api_client.py`
- `land_price_api_app/normalize.py`
- `land_price_api_app/db.py`
- `land_price_api_app/config.py`

Validation:
- do not run full backfill unless explicitly requested
- run targeted smoke checks only

## Trade price sync

Relevant files:
- `land_price_api_app/sync_trade_prices.py`
- `land_price_api_app/geocode_trade_prices.py`
- `land_price_api_app/db.py`
- `land_price_api_app/config.py`

## Property scraper

Relevant files:
- `land_price_api_app/property_scraper.py`
- `land_price_api_app/collect_search_results.py`
- `land_price_api_app/collect_listings_batch.py`
- `land_price_api_app/tests/test_property_scraper.py`
- `land_price_api_app/tests/fixtures/`

Validation:
- `pytest land_price_api_app/tests/test_property_scraper.py -q`
```

Create `_docs/capability_index/rates_volatility_model.md`.

```md
# Rates Volatility Model Capability Index

## Main notebook

Relevant files:
- `rates_volatility_model/rates_volatility_models.ipynb`
- `rates_volatility_model/generate_notebook_part2.py`
- `rates_volatility_model/generate_notebook_part3.py`
- `rates_volatility_model/merge_notebooks.py`

Prefer editing Python generation scripts over editing `.ipynb` directly.

## Validation

Relevant files:
- `rates_volatility_model/test_suite_validation.py`
- `rates_volatility_model/VALIDATION_SUMMARY.md`
- `rates_volatility_model/SABR_CORRECTION.md`

Validation:
- run targeted test script
- do not inspect `venv/`
```

Create `_docs/capability_index/johnhull.md`.

```md
# John Hull Notebook Capability Index

## Interest rate models notebook

Relevant files:
- `johnhull/interest_rate_models/build_ir_models_notebook.py`
- `johnhull/interest_rate_models/market_data.py`
- `johnhull/interest_rate_models/ir_models.ipynb`
- `johnhull/interest_rate_models/PROGRESS.md`

Prefer editing notebook builder scripts and source modules over direct `.ipynb` edits.
```

Create `_docs/capability_index/scratch.md`.

```md
# Scratch Capability Index

`_scratch/` is for one-off experiments only.

Do not inspect `_scratch/` unless explicitly requested by the user.

Do not infer canonical project behavior from scratch notebooks or scripts.
```

---

## Phase 8: Create VS Code Workspace Files

Create `_workspaces/land_price.code-workspace`.

```json
{
  "folders": [
    { "path": "../land_price_api_app" },
    { "path": "../_docs" }
  ],
  "settings": {
    "python.analysis.diagnosticMode": "openFilesOnly",
    "files.watcherExclude": {
      "**/_data/**": true,
      "**/_logs/**": true,
      "**/_archive/**": true,
      "**/_scratch/**": true,
      "**/__pycache__/**": true,
      "**/venv/**": true,
      "**/.venv/**": true,
      "**/*.parquet": true,
      "**/*.duckdb": true,
      "**/*.geojson": true
    },
    "search.exclude": {
      "**/_data/**": true,
      "**/_logs/**": true,
      "**/_archive/**": true,
      "**/_scratch/**": true,
      "**/__pycache__/**": true,
      "**/venv/**": true,
      "**/.venv/**": true
    }
  }
}
```

Create `_workspaces/rates_volatility.code-workspace`.

```json
{
  "folders": [
    { "path": "../rates_volatility_model" },
    { "path": "../_docs" }
  ],
  "settings": {
    "python.analysis.diagnosticMode": "openFilesOnly",
    "files.watcherExclude": {
      "**/venv/**": true,
      "**/.venv/**": true,
      "**/__pycache__/**": true,
      "**/.ipynb_checkpoints/**": true
    },
    "search.exclude": {
      "**/venv/**": true,
      "**/.venv/**": true,
      "**/__pycache__/**": true,
      "**/.ipynb_checkpoints/**": true
    }
  }
}
```

---

## Phase 9: Optional Scratch Migration

Move obvious one-off notebooks into `_scratch/`.

Only move files that are clearly one-off experiments, such as:

- `gpt4o_test_0.ipynb`
- `gemini_test_0.ipynb`
- `grok_test_0.ipynb`
- `haiku_test_0.ipynb`
- `opus_test_0.ipynb`
- `sonnet_test_0.ipynb`
- `codex_test_0.ipynb`

Suggested target:

```text
_scratch/notebooks/YYYY-MM/
```

Use the file modification date or current month if unsure.

Do not move domain notebooks like real estate simulations, John Hull chapters, or rates models unless explicitly requested.

After moving, search for references:

```bash
rg "gpt4o_test_0|gemini_test_0|grok_test_0|haiku_test_0|opus_test_0|sonnet_test_0|codex_test_0" .
```

---

## Phase 10: Validation

Run lightweight validation only.

### General

```bash
find . -maxdepth 2 -type d | sort
```

### Land price app

```bash
python -m py_compile \
  land_price_api_app/config.py \
  land_price_api_app/db.py \
  land_price_api_app/api_client.py \
  land_price_api_app/normalize.py
```

If tests exist and dependencies are installed:

```bash
pytest land_price_api_app/tests/test_property_scraper.py -q
pytest land_price_api_app/tests/test_facility_sources.py -q
pytest land_price_api_app/tests/test_terrain_sources.py -q
```

Do not run full data backfills unless explicitly requested.

### Rates volatility

```bash
python -m py_compile rates_volatility_model/*.py
```

If safe:

```bash
python rates_volatility_model/test_suite_validation.py
```

### Search for broken old paths

```bash
rg "land_price_api_app/data|data/processed|data/raw|rates_volatility_model/venv|notebooks/output" .
```

Review every remaining match.  
Some matches in archived docs may be acceptable, but active code/config should be updated.

---

## Phase 11: Final Report

At the end, produce a concise report:

```md
# Workspace Restructure Report

## Summary

## Directories created

## Files moved

## Path rewrites performed

## Files intentionally not moved

## Validation run

## Validation results

## Remaining risks

## Recommended next steps
```

Save it to:

```text
_docs/ai/worklogs/YYYY-MM-DD-restructure.md
```

Also summarize in chat:

- what changed
- what was not changed
- what needs manual confirmation
- exact commands to open the recommended VS Code workspace

Example:

```bash
code ~/projects/_workspaces/land_price.code-workspace
```

---

## Important Do Not Do List

Do not:

- create `~/projects/projects`
- scan the whole workspace unnecessarily
- read `_data` files
- read large `.ipynb` files unless explicitly requested
- read parquet/duckdb/geojson/csv files
- delete notebooks
- delete data
- print `.env` contents
- run full backfills
- commit changes unless explicitly requested
- assume path rewrites are safe without searching and validating

---

## Preferred Implementation Style

- Make minimal, reversible changes.
- Prefer moving heavy data/logs first.
- Keep actual source projects stable.
- Record every move in the worklog.
- Use targeted validation.
- When uncertain, leave the file in place and report the uncertainty.
