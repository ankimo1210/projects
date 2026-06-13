"""Tiny helpers for building notebooks programmatically with nbformat.

Used by ``build_notebooks.py``. Keeping the notebooks under version control as
*generated* artifacts means we can regenerate them deterministically (seeds
fixed) instead of hand-editing JSON.
"""

from __future__ import annotations

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def md(text: str):
    """A markdown cell from a (stripped) string."""
    return new_markdown_cell(text.strip("\n"))


def code(src: str):
    """A code cell from a (stripped) string."""
    return new_code_cell(src.strip("\n"))


def write(cells, path: str):
    """Assemble cells into a v4 notebook and write it to ``path``."""
    nb = new_notebook(cells=cells)
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python"},
    }
    nbformat.write(nb, path)
    return path
