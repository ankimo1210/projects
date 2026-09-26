"""The §27.2 saved notebook contains the lesson and all four shared figures."""

from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).resolve().parents[2] / "volumes/06_numerical_methods/numerical.ipynb"


def test_stochastic_volatility_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("## ")
    ]
    assert headings[6:10] == [
        "## 7. Black–Scholes–Merton 以外のモデル（§27.1）",
        "## 8. 確率ボラティリティ・モデル（§27.2）",
        "## 9. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）",
        "## 10. 練習問題",
    ]
    text = "\n".join(cell.source for cell in notebook.cells)
    for title in (
        "### 8.1 時間で決まるボラ",
        "### 8.2 確率ボラ",
        "### 8.3 無相関なら",
        "### 8.4 相関と Heston",
        "### 8.5 SABR",
        "### 8.6 GARCH",
    ):
        assert title in text
    keys = []
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("section") == "27.2":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == ["stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"]
