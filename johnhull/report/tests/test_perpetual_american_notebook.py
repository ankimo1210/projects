"""The saved §26.2 Book lesson keeps its prose, data, and rendered figures together."""

import json
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
REFERENCE = PROJECT / "docs/validation/section-26-2/reference.json"
PLOTLY = "application/vnd.plotly.v1+json"


def _lesson(notebook):
    cells = notebook.cells
    start = next(i for i, cell in enumerate(cells) if cell.source.startswith("### 4.9 "))
    end = next(i for i, cell in enumerate(cells) if cell.source.startswith("## 5. "))
    return cells[start:end]


def test_saved_lesson_has_six_subsections_and_four_executed_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("### 4.")
    ]
    assert headings[-2:] == [
        "### 4.8 パッケージ（§26.1、GE pp.614–615）",
        "### 4.9 永久アメリカン・コールとプット（§26.2、GE pp.615–616）",
    ]
    lesson = _lesson(notebook)
    numbers = [
        line.split(" ", 2)[1]
        for cell in lesson
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#### 4.9.")
    ]
    assert numbers == [f"4.9.{n}" for n in range(1, 7)]
    keys = []
    for cell in lesson:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.2":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "perpetual_value",
        "perpetual_boundaries",
        "perpetual_zero_dividend",
        "perpetual_convergence",
    ]


def test_saved_lesson_numbers_and_exceptions_follow_reference():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    cases = {case["label"]: case for case in data["cases"]}
    symmetric = cases["symmetric"]
    zero = cases["zero_yield"]
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    prose = "\n".join(cell.source for cell in _lesson(notebook) if cell.cell_type == "markdown")
    rows = symmetric["lattice"]["rows"]
    claims = (
        f"$H_1={symmetric['call']['boundary']:.0f}$、$H_2={symmetric['put']['boundary']:.0f}$",
        "$C(S)=S$",
        f"プット境界{zero['put']['boundary']:.4f}",
        f"プット価値{zero['put']['value']:.4f}",
        "、".join(f"{row['call']:.4f}" for row in rows),
        f"160年・1600ステップでも差は約{rows[-1]['call_gap']:.4f}",
        f"160年の価格{zero['lattice']['rows'][-1]['call']:.4f}",
    )
    for phrase in claims:
        assert phrase in prose, phrase
    assert "負の金利・配当" in prose
    assert "満期を有限にした効果とツリー格子の誤差の両方" in prose
    assert "最適な**有限の**行使境界はありません" in prose
