"""Regenerate all textbook notebooks from their builder modules.

    PYTHONPATH=src python tools/build_notebooks.py            # write notebooks/*.ipynb
    PYTHONPATH=src python tools/build_notebooks.py --check     # dry-run into a temp dir

Each ``build_nbNN.py`` exposes a ``cells`` list; this driver writes them via
``nbkit.build`` (which adds the import preamble). Notebooks are committed WITH
outputs, so after regenerating you must execute them:

    for nb in notebooks/*.ipynb; do \\
      PYTHONPATH=src jupyter nbconvert --to notebook --execute --inplace "$nb"; done

``--check`` builds into a temporary directory instead, so you can confirm the
builders run without overwriting the committed (executed) notebooks.
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
NOTEBOOKS = [
    ("build_nb01", "01_machine_learning_overview"),
    ("build_nb02", "02_data_preprocessing_and_features"),
    ("build_nb03", "03_linear_models"),
    ("build_nb04", "04_model_evaluation_and_validation"),
    ("build_nb05", "05_tree_based_models"),
    ("build_nb06", "06_svm_and_kernel_methods"),
    ("build_nb07", "07_unsupervised_learning"),
    ("build_nb08", "08_time_series_ml"),
    ("build_nb09", "09_model_interpretability"),
    ("build_nb10", "10_practical_ml_pipeline"),
    ("build_nb11", "11_capstone_four_lenses"),
    ("build_nb12", "12_exercise_solutions"),
    ("build_nb13", "13_imbalanced_learning"),
    ("build_nb14", "14_feature_selection"),
]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    import nbkit

    out_dir = pathlib.Path(tempfile.mkdtemp(prefix="ml_nb_")) if check else (PROJECT / "notebooks")
    for mod_name, stem in NOTEBOOKS:
        mod = importlib.import_module(mod_name)
        nbkit.build(mod.cells, str(out_dir / f"{stem}.ipynb"))
    print(f"\n{'checked' if check else 'wrote'} {len(NOTEBOOKS)} notebooks -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
