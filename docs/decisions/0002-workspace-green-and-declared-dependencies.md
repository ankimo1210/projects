# 0002. The workspace is green, and every package declares what it imports

- Status: Accepted
- Date: 2026-08-01

## Context

Until 2026-08-01 two workspace-wide signals were permanently red, and had been
for long enough that both read as scenery rather than as findings:

- `make lint` (`ruff check .` from the root) reported 226 errors.
- The full-workspace `pytest` reported 5 failures and 3 collection errors.

Because they were always red, nobody could tell a new regression from the
existing noise, and the habit became "check only the paths I touched". That is
not a workable invariant: the whole point of a workspace-level gate is that it
goes red *when you break something*.

Investigating them turned up a defect class that matters beyond lint hygiene.
Every member resolves its imports through the shared `.venv`, which contains the
union of all 26 members' dependencies. A package can therefore import something
it never declared and still pass every local check — the module arrives through
some *other* member's dependency tree. The failure only appears when the package
is installed on its own, which is exactly what CI does (`uv sync --package X`).

Seven such cases existed. `health` imported `scipy` (indirectly, via
`pandas.corr(method="spearman")`) and its workflow had **never once passed** as a
result; `market-viz` never declared `streamlit` or `plotly`, so a standalone
install produced an app that could not start; `jp_llm_lab` imported `tokenizers`
in a core module; `gto` imported `pandas`; `market_nn` imported `PIL`. The same
shape applied to test tooling — a `uv sync --package X` does not install the
workspace-root dev group, so `health`'s workflow called a `ruff` that was not
there, and fourteen members lacked `pytest` in their own dev group.

## Decision

1. **`ruff check .` and the full `pytest` run are green, and stay green.** A red
   result is now evidence of a regression in the change being made, not
   background noise. This is the reason the cleanup was worth doing at all.

2. **Naming rules are relaxed by configuration, not by renaming.** `X_train`,
   `h/l/c`, and `S0/K/T/r/sigma` are the universal spellings in DS, market-data
   and quantitative code; renaming them to satisfy PEP-8 would make that code
   harder to read. Projects in that category are listed in the root
   `per-file-ignores`, extending a policy that already covered `johnhull`,
   `quantkit` and friends. Notebook code gets the same treatment for `E402` /
   `F401` / `F841`, and the glob is `**/notebooks/**` — the previous
   `notebooks/**` matched only the top-level directory, so per-project notebooks
   were held to library standards by accident.

3. **Every package declares what it imports, including indirect and
   test-only.** "It works in the shared venv" is not evidence; the standard is
   whether `uv sync --package X` produces something that runs. Indirect
   dependencies count: `health` declares `scipy` even though no `health` module
   names it, because pandas dispatches to it. Dev tooling counts too: a package
   whose workflow runs `ruff` or `pytest` declares them in *its own* dev group.

   The deliberate exception is an optional backend that is imported inside a
   function and fails with an install hint — `quantkit`'s `torch` is the example.
   Those stay undeclared on purpose.

## Consequences

- A future red `make lint` or `pytest` is actionable. Diagnose it; do not
  assume it predates you.
- Adding a member project means giving it a dev group containing the tools its
  own CI invokes, not relying on the root group.
- Adding an import means checking it is declared. The check used here is
  reproducible: resolve the member's dependency closure from `uv.lock` and
  compare it against the top-level imports in its source. It found seven real
  cases and exactly one false positive (the intentional optional backend).
- The naming exemptions are per-project by design. A new quantitative project
  needs its own `per-file-ignores` entry rather than a blanket relaxation.
- **CI covers three of twenty-six members** (`eagle`, `health`, `gto`'s
  TypeScript). Every bug in this ADR would have been caught automatically by a
  workspace-level workflow, and `health`'s was — it is the only Python project
  with CI, and it is where the first `scipy` failure surfaced. Extending CI to
  the workspace is the open follow-up; it is not done here.
