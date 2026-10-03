"""Preserve all 213 predecessor cells and execute the §28.1 lesson."""

import importlib
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]


def test_gate_uses_market_price_of_risk_directory():
    m = importlib.import_module("johnhull.scripts.verify_market_price_of_risk_notebook")
    assert m.RECORD.parent == PROJECT / "docs/validation/section-28-1"


def test_saved_lesson_and_baseline_preservation():
    m = importlib.import_module("johnhull.scripts.verify_market_price_of_risk_notebook")
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 226
    assert len(m._outside(nb)) == 213
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == {"mpr_line", "mpr_riskless", "mpr_worlds", "mpr_validation"}
    text = "".join(
        o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", [])
    )
    assert "Example 28.2: λ=-0.1500, 2本目の期待収益=0.0150" in text
