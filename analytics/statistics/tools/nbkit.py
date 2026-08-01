"""Tiny helpers for building notebooks programmatically with nbformat.

Used by ``build_notebooks.py`` and the per-notebook ``build_nbNN.py`` modules.
Keeping the notebooks under version control as *generated* artifacts means we
can regenerate them deterministically (seeds fixed) instead of hand-editing JSON.

Mirrors the sibling analytics books' ``nbkit`` (``md`` / ``code`` / ``write`` /
``build``).

An earlier draft carried a ``check_typography`` guard against bold markers
touching CJK punctuation, on the strength of a note that linear_algebra had
hit such a trap. Measurement retired it: markdown-it renders every spelling
the guard banned -- including ``**「これはダメ」**`` -- as ``<strong>``, and
the pattern appears on 56 admonition lines across the bayesian, neural_net
and linear_algebra books, all of which build and display correctly. The rule
rejected the series' own house style and caught nothing. Whatever the
original problem was, it was not this, so nothing is asserted about it here.
"""

from __future__ import annotations

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

# Prepended as the first code cell: make ``stats_textbook`` importable whether
# or not the project has been pip-installed, by walking up to the dir holding
# src/stats_textbook.
PREAMBLE = """
import sys, pathlib
_here = pathlib.Path.cwd().resolve()
for _p in [_here, *_here.parents]:
    if (_p / "src" / "stats_textbook").exists():
        sys.path.insert(0, str(_p / "src"))
        break
""".strip()


def md(text: str):
    """A markdown cell (leading/trailing blank lines trimmed)."""
    return new_markdown_cell(text.strip("\n"))


def code(src: str):
    """A code cell (leading/trailing blank lines trimmed)."""
    return new_code_cell(src.strip("\n"))


def _metadata() -> dict:
    return {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }


def write(cells, path: str):
    """Assemble cells into a v4 notebook and write it to ``path`` (no preamble)."""
    nb = new_notebook(cells=list(cells))
    nb["metadata"] = _metadata()
    nbformat.write(nb, path)
    return path


def build(cells, path: str, preamble: bool = True):
    """Write a notebook, prepending the import-path preamble by default."""
    all_cells = ([new_code_cell(PREAMBLE)] if preamble else []) + list(cells)
    write(all_cells, path)
    print(f"wrote {path} ({len(all_cells)} cells)")
    return path
