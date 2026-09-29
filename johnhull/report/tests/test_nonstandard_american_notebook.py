"""The §26.3 lesson presents the contract terms and saved reference plots."""

import json
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
REFERENCE = PROJECT / "docs/validation/section-26-3/reference.json"
PLOTLY = "application/vnd.plotly.v1+json"


def _lesson(notebook):
    start = next(i for i, cell in enumerate(notebook.cells) if cell.source.startswith("### 4.10 "))
    end = next(i for i, cell in enumerate(notebook.cells) if cell.source.startswith("## 5. "))
    return notebook.cells[start:end]


def test_six_subsections_and_four_executed_shared_figures():
    lesson = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    headings = [
        line.split(" ", 2)[1]
        for cell in lesson
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#### 4.10.")
    ]
    assert headings == [f"4.10.{i}" for i in range(1, 7)]
    keys = []
    for cell in lesson:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.3":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "scheduled_ordering",
        "scheduled_exercise",
        "scheduled_warrant",
        "scheduled_frequency",
    ]


def test_contract_years_and_synthetic_price_are_not_confused():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    lesson = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    prose = "\n".join(cell.source for cell in lesson if cell.cell_type == "markdown")
    assert "$30" in prose and "$32" in prose and "$33" in prose
    assert f"{data['warrant']['price']:.4f}" in prose
    assert "原典に価格はない" in prose
    assert "暗黙に丸め" in prose
