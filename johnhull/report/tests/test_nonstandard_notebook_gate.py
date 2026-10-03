"""The §26.3 verifier rejects old-cell and new-figure drift."""

import copy
import sys
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import verify_nonstandard_notebook as gate  # noqa: E402


def test_previous_cells_are_preserved_and_changed_figure_is_rejected():
    current = _without_market_risk_extension(nbformat.read(gate.NOTEBOOK, as_version=4))
    base = gate._base()
    fresh = gate._fresh()
    assert not gate.compare(current, base, fresh)
    changed = copy.deepcopy(current)
    old = next(cell for cell in changed.cells if cell.source.startswith("#### 4.9.4 "))
    old.source += " altered"
    assert gate.compare(changed, base, fresh)
    changed = copy.deepcopy(current)
    for cell in changed.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(gate.PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("figure") == "scheduled_ordering":
                payload["data"][0]["y"][0] += 0.5
                assert gate.compare(changed, base, fresh)
                return
    raise AssertionError("saved scheduled_ordering figure missing")


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
