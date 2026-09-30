"""The executed §26.4 notebook delivers four plots and the printed example."""

import re
from pathlib import Path

import nbformat
import pytest

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
PLOTLY = "application/vnd.plotly.v1+json"


def _lesson(notebook):
    start = next(i for i, c in enumerate(notebook.cells) if c.source.startswith("### 4.11 "))
    end = next(
        i
        for i in range(start + 1, len(notebook.cells))
        if notebook.cells[i].cell_type == "markdown"
        and notebook.cells[i].source.startswith(("### ", "## "))
    )
    return notebook.cells[start:end]


def test_six_subsections_deliver_four_executed_shared_figures():
    cells = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    headings = [
        line.split(" ", 2)[1]
        for c in cells
        if c.cell_type == "markdown"
        for line in c.source.splitlines()
        if line.startswith("#### 4.11.")
    ]
    assert headings == [f"4.11.{i}" for i in range(1, 7)]
    keys = []
    for c in cells:
        for out in c.get("outputs", ()):
            assert out.output_type != "error"
            payload = out.get("data", {}).get(PLOTLY)
            if payload:
                assert payload["layout"]["meta"]["section"] == "26.4"
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == ["gap_payoff", "gap_decomposition", "gap_insurance", "gap_premium"]


def test_executed_insurance_example_keeps_insurer_and_holder_separate():
    cells = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    output = "\n".join(out.get("text", "") for c in cells for out in c.get("outputs", ()))
    match = re.search(r"ordinary=([\d.]+) insurer=([\d.]+) holder=([\d.]+)", output)
    assert match
    assert tuple(map(float, match.groups())) == pytest.approx(
        (3435.947020, 1895.688944, 630.790352), abs=1e-6
    )
