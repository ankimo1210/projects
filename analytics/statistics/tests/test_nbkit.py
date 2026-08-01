"""The notebook builder emits well-formed cells.

No typography guard here on purpose. An earlier draft rejected bold markers
touching CJK punctuation; measurement showed markdown-it renders all such
spellings as <strong>, and the pattern is in production use across the
sibling books. The test that matters is that the series' house style
survives the builder.
"""

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nbkit  # noqa: E402


def test_md_makes_a_markdown_cell():
    cell = nbkit.md("信頼区間は **長期頻度** の性質である")
    assert cell.cell_type == "markdown"
    assert cell.source == "信頼区間は **長期頻度** の性質である"


def test_md_accepts_the_series_callout_style():
    """`**「核心」**` appears on 56 admonition lines across the sibling books."""
    body = "```{admonition} 核心 — ひとことで\n:class: tip\n**「長期頻度」** が定義である。\n```"
    assert nbkit.md(body).cell_type == "markdown"


def test_code_strips_surrounding_blank_lines():
    cell = nbkit.code("\n\nprint('hi')\n\n")
    assert cell.cell_type == "code"
    assert cell.source == "print('hi')"


def test_build_prepends_the_import_preamble(tmp_path):
    path = nbkit.build([nbkit.md("# title")], str(tmp_path / "nb.ipynb"))
    import nbformat

    nb = nbformat.read(path, as_version=4)
    assert len(nb.cells) == 2
    assert "stats_textbook" in nb.cells[0].source
