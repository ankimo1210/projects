"""The saved §26.6 lesson includes the new API output and all shared figures."""

import importlib
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]


def test_saved_notebook_has_cliquet_output_and_four_figures():
    notebook = nbformat.read(PROJECT / "volumes/10_exotics_martingales/exotics.ipynb", as_version=4)
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 4.13 "))
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
        "cliquet_reset",
        "cliquet_components",
        "cliquet_frequency",
        "cliquet_limits",
    }
    printed = "".join(
        output.get("text", "") for cell in cells for output in cell.get("outputs", [])
    )
    assert "call=23.584836" in printed and "put=19.750719" in printed


def test_notebook_gate_preserves_old_lesson_and_rejects_changed_plot():
    gate = importlib.import_module("johnhull.scripts.verify_cliquet_notebook")
    notebook = nbformat.read(gate.NOTEBOOK, as_version=4)
    base, fresh = gate._base(), gate._fresh()
    assert gate.compare(notebook, base, fresh) == []
    assert len(gate._outside(notebook)) == 180
    assert all(row["rejected"] for row in gate.negative_controls(notebook, base, fresh))
