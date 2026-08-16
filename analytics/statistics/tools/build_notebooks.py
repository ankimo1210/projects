"""Regenerate textbook notebooks from their builder modules.

    PYTHONPATH=src python tools/build_notebooks.py            # ALL notebooks
    PYTHONPATH=src python tools/build_notebooks.py 08         # just chapter 08
    PYTHONPATH=src python tools/build_notebooks.py 08 09      # chapters 08 and 09
    PYTHONPATH=src python tools/build_notebooks.py --check    # dry-run into a temp dir

Each ``build_nbNN.py`` exposes a ``cells`` list; this driver writes them via
``nbkit.build`` (which adds the import preamble).

**Writing a notebook strips its outputs**, and notebooks are committed WITH
outputs, so anything regenerated has to be re-executed:

    PYTHONPATH=../src jupyter nbconvert --to notebook --execute --inplace <nb>

Passing chapter numbers keeps that obligation small. Regenerating all nine
chapters to change one of them wipes the other eight -- which happened once,
and the stripped notebooks were only noticed because they were still in the
working tree. Restoring them was a ``git checkout``; catching it later would
have meant committing a book whose pages had gone blank.
"""

from __future__ import annotations

import importlib
import pathlib
import sys
import tempfile

TOOLS = pathlib.Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

# (builder module, output notebook stem) in book order.
# Plan 1 filled 00-05; Plan 2 adds 06-10; Plan 3 appends 11-13.
NOTEBOOKS = [
    ("build_nb00", "00_overview"),
    ("build_nb01", "01_probability_foundations"),
    ("build_nb02", "02_random_variables_expectation"),
    ("build_nb03", "03_distributions_zoo"),
    ("build_nb04", "04_limit_theorems"),
    ("build_nb05", "05_stochastic_processes"),
    ("build_nb06", "06_estimation_mle"),
    ("build_nb07", "07_confidence_intervals_bootstrap"),
    ("build_nb08", "08_hypothesis_testing"),
    ("build_nb09", "09_regression_inference"),
    ("build_nb10", "10_glm"),
    ("build_nb11", "11_frequentist_vs_bayes"),
    ("build_nb12", "12_capstone_three_lenses"),
]


def _select(argv: list[str]) -> list[tuple[str, str]]:
    """Chapters named on the command line, or all of them if none are."""
    wanted = [a for a in argv if not a.startswith("-")]
    if not wanted:
        return NOTEBOOKS
    chosen = []
    for token in wanted:
        stem = token.zfill(2)
        matches = [entry for entry in NOTEBOOKS if entry[1].startswith(stem)]
        if not matches:
            raise SystemExit(f"no chapter matches {token!r}; known: {[s for _, s in NOTEBOOKS]}")
        chosen.extend(matches)
    return chosen


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    selected = _select(argv)
    import nbkit

    out_dir = (
        pathlib.Path(tempfile.mkdtemp(prefix="stats_nb_")) if check else (PROJECT / "notebooks")
    )
    for mod_name, stem in selected:
        mod = importlib.import_module(mod_name)
        nbkit.build(mod.cells, str(out_dir / f"{stem}.ipynb"))
    print(f"\n{'checked' if check else 'wrote'} {len(selected)} notebooks -> {out_dir}")
    if not check:
        print("outputs were stripped -- re-execute these with nbconvert before committing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
