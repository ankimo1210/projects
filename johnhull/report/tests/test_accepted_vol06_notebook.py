"""Accepted vol06 lessons remain checkable after later sections are inserted."""

import copy
import sys
from pathlib import Path

import nbformat

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_accepted_vol06_notebook import compare, load_current  # noqa: E402


def test_accepted_lessons_match_their_own_snapshots():
    assert compare(load_current()) == []


def test_accepted_lesson_source_mutation_is_rejected():
    altered = copy.deepcopy(load_current())
    cell = next(c for c in altered.cells if c.source.startswith("### 9.1 モデル"))
    cell.source += " changed"
    assert any("27.3" in message for message in compare(altered))


def test_accepted_plot_value_mutation_is_rejected():
    altered = copy.deepcopy(load_current())
    for cell in altered.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("figure") == "cb_tree":
                payload["data"][0]["customdata"][0][0] += 1
                assert any("cb_tree" in message for message in compare(altered))
                return
    raise AssertionError("missing saved cb_tree")


def test_accepted_path_dependent_lesson_is_pinned_after_section_27_6():
    altered = copy.deepcopy(load_current())
    cell = next(c for c in altered.cells if c.source.startswith("### 11.3 代表平均"))
    cell.source += " changed"
    assert any("27.5" in message for message in compare(altered))
