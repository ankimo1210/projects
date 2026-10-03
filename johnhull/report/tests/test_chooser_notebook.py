"""Preserve all 202 predecessor cells and execute the chooser lesson."""

import importlib
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]


def test_gate_uses_chooser_directory():
    m = importlib.import_module("johnhull.scripts.verify_chooser_notebook")
    assert m.RECORD.parent == PROJECT / "docs/validation/section-26-8"


def test_saved_chooser_lesson_and_baseline_preservation():
    m = importlib.import_module("johnhull.scripts.verify_chooser_notebook")
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 213
    assert len(m._outside(nb)) == 202
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == {
        "chooser_choice",
        "chooser_package",
        "chooser_timing",
        "chooser_validation",
    }
    text = "".join(
        o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", [])
    )
    assert "chooser=13.344280" in text
