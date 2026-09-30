"""The saved §26.5 lesson includes the new API output and all shared figures."""

import importlib
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]


def test_saved_notebook_has_forward_start_output_and_four_figures():
    notebook = nbformat.read(PROJECT / "volumes/10_exotics_martingales/exotics.ipynb", as_version=4)
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 4.12 "))
    end = next(
        i
        for i, c in enumerate(notebook.cells[start + 1 :], start + 1)
        if c.cell_type == "markdown" and c.source.startswith(("### ", "## "))
    )
    cells = notebook.cells[start:end]
    assert len(cells) == 11
    figures = {
        output["data"]["application/vnd.plotly.v1+json"]["layout"]["meta"]["figure"]
        for cell in cells
        for output in cell.get("outputs", [])
        if "application/vnd.plotly.v1+json" in output.get("data", {})
    }
    assert figures == {
        "forward_contract",
        "forward_homogeneity",
        "forward_start_delay",
        "forward_fixed_expiry",
    }
    printed = "".join(
        output.get("text", "") for cell in cells for output in cell.get("outputs", [])
    )
    assert "forward=8.396808" in printed and "same_life_atm=8.652529" in printed


def test_notebook_gate_preserves_old_lesson_and_rejects_changed_plot():
    gate = importlib.import_module("johnhull.scripts.verify_forward_start_notebook")
    notebook = nbformat.read(gate.NOTEBOOK, as_version=4)
    base, fresh = gate._base(), gate._fresh()
    assert gate.compare(notebook, base, fresh) == []
    assert len(gate._outside(notebook)) == 169
    assert all(row["rejected"] for row in gate.negative_controls(notebook, base, fresh))
