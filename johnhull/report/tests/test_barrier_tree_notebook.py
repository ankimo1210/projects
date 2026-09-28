"""The saved vol06 §27.6 lesson has six subsections and four shared figures."""

from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).resolve().parents[2] / "volumes/06_numerical_methods/numerical.ipynb"


def test_barrier_tree_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("## ")
    ]
    assert headings[6:15] == [
        "## 7. Black–Scholes–Merton 以外のモデル（§27.1）",
        "## 8. 確率ボラティリティ・モデル（§27.2）",
        "## 9. IVF（局所ボラティリティ）モデル（§27.3）",
        "## 10. 転換社債（§27.4）",
        "## 11. 経路依存デリバティブ（§27.5）",
        "## 12. バリア・オプションのツリー評価（§27.6）",
        "## 13. 相関のある二資産のオプション（§27.7）",
        "## 14. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）",
        "## 15. 練習問題",
    ]
    text = "\n".join(cell.source for cell in notebook.cells)
    for number in range(1, 7):
        assert f"### 12.{number} " in text
    keys = []
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("section") == "27.6":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "barrier_convergence",
        "barrier_lattice",
        "barrier_errors",
        "barrier_near",
    ]
