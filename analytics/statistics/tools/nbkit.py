"""Tiny helpers for building notebooks programmatically with nbformat.

Used by ``build_notebooks.py`` and the per-notebook ``build_nbNN.py`` modules.
Keeping the notebooks under version control as *generated* artifacts means we
can regenerate them deterministically (seeds fixed) instead of hand-editing JSON.

Mirrors the sibling analytics books' ``nbkit`` (``md`` / ``code`` / ``write`` /
``build``).

``md`` refuses to emit a cell whose bold markup will not render. CommonMark
decides whether ``**`` opens or closes emphasis from the characters on *both*
sides of it, and CJK punctuation counts as punctuation, so two spellings that
read naturally in Japanese silently fail:

- ``**「信頼区間」**は難しい`` -- the closing ``**`` follows punctuation and
  precedes a letter, so it cannot close. Put a space after it.
- ``各章には**「核心」**を置いた`` -- the opening ``**`` follows a letter and
  precedes punctuation, so it cannot open. Move the bracket outside the
  emphasis: ``「**核心**」``.

Both render as literal asterisks rather than bold, and neither raises a
warning at build time -- linear_algebra shipped three such lines before they
were caught by scanning the built HTML.

The check renders each line and asks whether emphasis actually formed, which
is the only reliable test: an earlier attempt at a regex over one side of the
delimiter produced both false positives (it rejected the correct
``**実測する**。``) and false negatives (it passed both spellings above).
"""

from __future__ import annotations

import nbformat
from markdown_it import MarkdownIt
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

_MD = MarkdownIt("commonmark")

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


def check_bold(text: str) -> list[str]:
    """Return lines whose paired ``**`` markers fail to produce emphasis.

    Only lines with an even, non-zero number of ``**`` are judged: an odd
    count is a literal asterisk the author meant, and inline maths or code
    spans keep their own delimiters. Rendering is the oracle -- see the
    module docstring for why a regex cannot do this job.
    """
    offenders = []
    for line in text.splitlines():
        n = line.count("**")
        if n == 0 or n % 2 == 1:
            continue
        if "<strong>" not in _MD.render(line):
            offenders.append(line)
    return offenders


def md(text: str):
    """A markdown cell (leading/trailing blank lines trimmed)."""
    body = text.strip("\n")
    offenders = check_bold(body)
    if offenders:
        raise ValueError(
            "bold markers do not render -- CommonMark flanking rejects them "
            "next to CJK punctuation (see nbkit's docstring):\n  " + "\n  ".join(offenders)
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
