"""The notebook builder refuses bold markup that will not render.

CommonMark decides whether ``**`` opens or closes from the characters on
both sides, and CJK punctuation counts as punctuation. Two natural-looking
Japanese spellings therefore fail silently, with no build warning. These
tests pin both, plus the correct spellings they are easily confused with.
"""

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nbkit  # noqa: E402

# Closing ** preceded by punctuation and followed by a letter cannot close.
BROKEN_CLOSE = "**「信頼区間」**は難しい"
# Opening ** preceded by a letter and followed by punctuation cannot open.
BROKEN_OPEN = "各章には**「核心」**を置いた"


def test_check_bold_catches_the_closing_side_failure():
    assert nbkit.check_bold(BROKEN_CLOSE) == [BROKEN_CLOSE]


def test_check_bold_catches_the_opening_side_failure():
    assert nbkit.check_bold(BROKEN_OPEN) == [BROKEN_OPEN]


@pytest.mark.parametrize(
    "line",
    [
        "**「信頼区間」** は難しい",  # space after the closing marker
        "各章には「**核心**」を置いた",  # bracket outside the emphasis
        "予言なら実測できる。本書では**実測する**。",  # closing marker before punctuation
        "信頼区間は **長期頻度** の性質である",
        "1. **確率は長期頻度で定義する** — だから信頼区間は「真値」ではない",
    ],
)
def test_check_bold_accepts_correct_spellings(line):
    assert nbkit.check_bold(line) == []


def test_check_bold_ignores_odd_marker_counts():
    """An unpaired ** is a literal asterisk, not a failed emphasis."""
    assert nbkit.check_bold("x**2 + y**2 = r") == []


def test_md_raises_on_bold_that_will_not_render():
    with pytest.raises(ValueError, match="do not render"):
        nbkit.md(BROKEN_CLOSE)


def test_md_makes_a_markdown_cell():
    cell = nbkit.md("信頼区間は **長期頻度** の性質である")
    assert cell.cell_type == "markdown"
    assert cell.source == "信頼区間は **長期頻度** の性質である"


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
