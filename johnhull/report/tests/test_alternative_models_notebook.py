"""The §27.1 saved notebook contains the lesson and all four shared figures."""

from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).resolve().parents[2] / "volumes/06_numerical_methods/numerical.ipynb"


def test_alternative_models_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(cell.source for cell in notebook.cells)
    for title in (
        "### 7.1 CEV",
        "### 7.2 Merton",
        "### 7.3 Table 27.1",
        "### 7.4 ジャンプ",
        "### 7.5 分散ガンマ",
        "### 7.6 使い分け",
    ):
        assert title in text
    keys = []
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("section") == "27.1":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "alternative_cev",
        "alternative_merton",
        "alternative_poisson",
        "alternative_vg",
    ]
