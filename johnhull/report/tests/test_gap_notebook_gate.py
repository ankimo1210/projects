"""The §26.4 gate detects old prose and saved-data plot mutations."""

import copy
import importlib

import nbformat


def test_preservation_gate_rejects_changed_old_cell_and_new_plot():
    gate = importlib.import_module("johnhull.scripts.verify_gap_notebook")
    current = _without_market_price_of_risk(nbformat.read(gate.NOTEBOOK, as_version=4))
    base, fresh = gate._base(), gate._fresh()
    assert not gate.compare(current, base, fresh)
    changed = copy.deepcopy(current)
    next(c for c in changed.cells if c.source.startswith("#### 4.10.4 ")).source += " altered"
    assert gate.compare(changed, base, fresh)
    changed = copy.deepcopy(current)
    for c in changed.cells:
        for out in c.get("outputs", ()):
            payload = out.get("data", {}).get(gate.PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("figure") == "gap_decomposition":
                payload["data"][0]["y"][0] += 0.5
                assert gate.compare(changed, base, fresh)
                return
    raise AssertionError("gap_decomposition plot missing")


def _without_market_price_of_risk(notebook):
    # M26 owns vol10 §6.1–6.6 and verifies every predecessor cell.
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 6.1 "))
    end = next(
        i
        for i in range(start + 1, len(notebook.cells))
        if notebook.cells[i].source.startswith("## 7. ")
    )
    notebook.cells = notebook.cells[:start] + notebook.cells[end:]
    return notebook
