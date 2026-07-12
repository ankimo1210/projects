"""Tiny notebook builder: cell lists → (optionally executed) .ipynb files.

Notebooks in this repo are GENERATED from tools/build_notebooks.py so they
stay reproducible and reviewable as plain Python; the executed .ipynb is the
artifact users read in JupyterLab.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def md(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(textwrap.dedent(source).strip())


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(textwrap.dedent(source).strip())


def build_notebook(
    cells: list[nbformat.NotebookNode],
    path: Path,
    execute: bool = True,
    cwd: Path | None = None,
    timeout: int = 900,
) -> Path:
    nb = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
        },
    )
    if execute:
        client = NotebookClient(
            nb,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(cwd or path.parent)}},
        )
        client.execute()
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, path)
    return path
