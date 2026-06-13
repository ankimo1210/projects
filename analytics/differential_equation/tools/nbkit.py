"""Tiny helpers for building notebooks programmatically with nbformat.

Used by the build_*_notebook.py scripts. Not part of either shippable package.
Keeping the notebooks under version control as *generated* artifacts means we
can regenerate them deterministically (seeds fixed) instead of hand-editing
JSON.
"""

from __future__ import annotations

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def md(text: str):
    """A markdown cell from a (dedented) string."""
    return new_markdown_cell(text.strip("\n"))


def code(src: str):
    """A code cell from a (dedented) string."""
    return new_code_cell(src.strip("\n"))


def setup_cell(pkg: str):
    """Standard first code cell: make ``pkg`` importable + fix seeds/printing."""
    return code(
        f"""
# Shared setup. Make the book package importable whether or not it is pip-installed,
# then fix the random seed and tidy NumPy printing.
import sys
from pathlib import Path

try:
    import {pkg}  # noqa: F401
except ModuleNotFoundError:
    for _base in (Path.cwd(), *Path.cwd().parents):
        if (_base / "src" / "{pkg}").is_dir():
            sys.path.insert(0, str(_base / "src"))
            break

import numpy as np
import matplotlib.pyplot as plt

np.random.seed(0)
np.set_printoptions(precision=4, suppress=True)
"""
    )


def write(cells, path: str, title: str | None = None):
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
