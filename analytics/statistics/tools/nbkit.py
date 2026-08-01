"""Tiny helpers for building notebooks programmatically with nbformat.

Used by ``build_notebooks.py`` and the per-notebook ``build_nbNN.py`` modules.
Keeping the notebooks under version control as *generated* artifacts means we
can regenerate them deterministically (seeds fixed) instead of hand-editing JSON.

Mirrors the sibling analytics books' ``nbkit`` (``md`` / ``code`` / ``write`` /
``build``) and adds ``check_typography``: MyST admonitions render bold text
incorrectly when the ``**`` sits directly against a CJK bracket, which the
linear_algebra book hit in practice.
"""

from __future__ import annotations

import re

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

# ``**`` touching a CJK bracket from the *inside* of the emphasis. The
# negative lookahead spares the legitimate spelling 「…」**だ**, where the
# emphasis opens outside the bracket.
_CJK_PUNCT = "「」『』（）【】、。・"
_BAD_BOLD = re.compile(rf"\*\*[{_CJK_PUNCT}]|[{_CJK_PUNCT}]\*\*(?!\S)")


def check_typography(text: str) -> list[str]:
    """Return the offending lines where bold markers touch CJK punctuation."""
    return [line for line in text.splitlines() if _BAD_BOLD.search(line)]


def md(text: str):
    """A markdown cell (leading/trailing blank lines trimmed)."""
    body = text.strip("\n")
    offenders = check_typography(body)
    if offenders:
        raise ValueError(
            "bold marker touches CJK punctuation (MyST renders this wrong):\n  "
            + "\n  ".join(offenders)
        )
    return new_markdown_cell(body)


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
