"""The notebook builder rejects the CJK-punctuation bold trap."""

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nbkit  # noqa: E402


def test_check_typography_flags_bold_against_cjk_bracket():
    assert nbkit.check_typography("**「信頼区間」** は難しい")
    assert nbkit.check_typography("難しいのは「信頼区間」**だ**") == []


def test_md_raises_on_bad_bold():
    with pytest.raises(ValueError, match="CJK punctuation"):
        nbkit.md("**「これはダメ」**")


def test_md_accepts_clean_bold():
    cell = nbkit.md("信頼区間は **長期頻度** の性質である")
    assert cell.cell_type == "markdown"
