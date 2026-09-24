"""The delivered vol10 notebook includes the saved §26.17 lesson and figures."""

from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).resolve().parents[2] / "volumes/10_exotics_martingales/exotics.ipynb"


def test_section_26_17_has_six_teaching_parts_and_four_saved_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    sources = [cell.source for cell in notebook.cells]
    for index in range(1, 7):
        assert any(f"4.7.{index}" in source for source in sources)
    found = set()
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            meta = (payload or {}).get("layout", {}).get("meta", {})
            if meta.get("section") == "26.17":
                found.add(meta.get("figure"))
    assert found == {
        "static_boundary",
        "static_ladder",
        "static_boundary_error",
        "static_convergence",
    }
