"""Regenerate all textbook notebooks from their builder modules.

    PYTHONPATH=src python tools/build_notebooks.py            # write notebooks/*.ipynb
    PYTHONPATH=src python tools/build_notebooks.py --check     # dry-run into a temp dir

Each ``build_nbNN.py`` exposes a ``cells`` list; this driver writes them via
``nbkit.build`` (which adds the import preamble). Notebooks are committed WITH
outputs, so after regenerating you must execute them (see README).
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
# Plan 1 fills 00-05; Plan 2 and 3 append 06-13.
NOTEBOOKS = [
    ("build_nb00", "00_overview"),
]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    import nbkit

    out_dir = (
        pathlib.Path(tempfile.mkdtemp(prefix="stats_nb_")) if check else (PROJECT / "notebooks")
    )
    for mod_name, stem in NOTEBOOKS:
        mod = importlib.import_module(mod_name)
        nbkit.build(mod.cells, str(out_dir / f"{stem}.ipynb"))
    print(f"\n{'checked' if check else 'wrote'} {len(NOTEBOOKS)} notebooks -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
