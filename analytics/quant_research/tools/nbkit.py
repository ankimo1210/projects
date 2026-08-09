"""Small, deterministic helpers for generating the textbook notebooks.

The ``.ipynb`` files are build artifacts.  Authors edit ``build_nbNN.py`` and
regenerate them with ``build_notebooks.py`` instead of hand-editing JSON.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

PREAMBLE = """
import pathlib
import sys

_here = pathlib.Path.cwd().resolve()
for _parent in [_here, *_here.parents]:
    if (_parent / "src" / "quant_textbook").exists():
        sys.path.insert(0, str(_parent / "src"))
        break
""".strip()


def check_bold(text: str) -> list[str]:
    """Return lines with unbalanced ``**`` markers.

    This deliberately performs only a dependency-free structural check.  The
    Jupyter Book build remains the rendering oracle for CommonMark flanking.
    """
    offenders: list[str] = []
    for line in text.splitlines():
        marker_count = line.count("**")
        if marker_count % 2:
            offenders.append(line)
    return offenders


def md(text: str):
    """Create a stripped Markdown cell and reject broken CJK bold markup."""
    body = text.strip("\n")
    offenders = check_bold(body)
    if offenders:
        joined = "\n  ".join(offenders)
        raise ValueError(f"bold markers do not render in these lines:\n  {joined}")
    return new_markdown_cell(body)


def code(source: str):
    """Create a stripped code cell."""
    return new_code_cell(source.strip("\n"))


def _metadata() -> dict:
    return {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }


def build(cells: Iterable, path: str | Path, *, preamble: bool = True) -> Path:
    """Write one notebook with stable metadata and no execution outputs."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    notebook_cells = ([new_code_cell(PREAMBLE)] if preamble else []) + list(cells)
    for cell_number, cell in enumerate(notebook_cells):
        cell["id"] = f"cell-{cell_number:03d}"
    notebook = new_notebook(cells=notebook_cells, metadata=_metadata())
    nbformat.validate(notebook)
    nbformat.write(notebook, output)
    print(f"wrote {output} ({len(notebook_cells)} cells)")
    return output
