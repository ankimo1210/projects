"""The saved compound lesson and complete M23 predecessor stay executable."""

import importlib
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]


def test_gate_writes_to_compound_evidence_directory():
    gate = importlib.import_module("johnhull.scripts.verify_compound_notebook")
    assert gate.RECORD.parent == PROJECT / "docs/validation/section-26-7"


def test_saved_notebook_has_four_compound_figures_and_prices():
    notebook = _without_chooser(
        _without_market_risk_extension(
            nbformat.read(PROJECT / "volumes/10_exotics_martingales/exotics.ipynb", as_version=4)
        )
    )
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 4.14 "))
    end = next(
        i
        for i in range(start + 1, len(notebook.cells))
        if notebook.cells[i].source.startswith("## 5. ")
    )
    cells = notebook.cells[start:end]
    assert len(cells) == 11
    keys = {
        output["data"]["application/vnd.plotly.v1+json"]["layout"]["meta"]["figure"]
        for cell in cells
        for output in cell.get("outputs", [])
        if "application/vnd.plotly.v1+json" in output.get("data", {})
    }
    assert keys == {
        "compound_threshold",
        "compound_strikes",
        "compound_timing",
        "compound_validation",
    }
    printed = "".join(
        output.get("text", "") for cell in cells for output in cell.get("outputs", [])
    )
    assert "call_on_call=3.256827" in printed and "put_on_put=4.722822" in printed


def test_notebook_gate_preserves_all_m23_cells_and_rejects_mutations():
    gate = importlib.import_module("johnhull.scripts.verify_compound_notebook")
    notebook = _without_chooser(
        _without_market_risk_extension(nbformat.read(gate.NOTEBOOK, as_version=4))
    )
    base, fresh = gate._base(), gate._fresh()
    assert gate.compare(notebook, base, fresh) == []
    assert len(gate._outside(notebook)) == 191
    assert all(row["rejected"] for row in gate.negative_controls(notebook, base, fresh))


def _without_chooser(notebook):
    # Historical M24 gate owns §4.14; M25 verifies every predecessor cell.
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 4.15 "))
    end = next(
        i
        for i in range(start + 1, len(notebook.cells))
        if notebook.cells[i].source.startswith("## 5. ")
    )
    notebook.cells = notebook.cells[:start] + notebook.cells[end:]
    return notebook


def _without_market_risk_extension(notebook):
    # Historical acceptance is preserved; M26 verifies all 213 predecessor cells.
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 6.1 "))
    end = next(
        i
        for i in range(start + 1, len(notebook.cells))
        if notebook.cells[i].source.startswith("## 7. ")
    )
    notebook.cells = notebook.cells[:start] + notebook.cells[end:]
    return notebook
