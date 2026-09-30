"""The §26.4 lesson presents Example 26.1 and the saved reference plots."""

import json
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
REFERENCE = PROJECT / "docs/validation/section-26-4/reference.json"
PLOTLY = "application/vnd.plotly.v1+json"


def _lesson(notebook):
    start = next(i for i, cell in enumerate(notebook.cells) if cell.source.startswith("### 4.11 "))
    end = next(i for i, cell in enumerate(notebook.cells) if cell.source.startswith("## 5. "))
    return notebook.cells[start:end]


def test_lesson_follows_nonstandard_american_section():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("### 4.")
    ]
    start = headings.index("### 4.10 非標準アメリカン・オプション（§26.3、GE p.616）")
    assert headings[start + 1] == "### 4.11 ギャップ・オプション（§26.4、GE p.617）"


def test_six_subsections_and_four_executed_shared_figures():
    lesson = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    headings = [
        line.split(" ", 2)[1]
        for cell in lesson
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#### 4.11.")
    ]
    assert headings == [f"4.11.{i}" for i in range(1, 7)]
    keys = []
    for cell in lesson:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.4":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == ["gap_payoff", "gap_settlement_line", "gap_insurance", "gap_transfer_cost"]


def test_printed_values_and_trigger_role_are_stated():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    lesson = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    prose = "\n".join(cell.source for cell in lesson if cell.cell_type == "markdown")
    example = data["example_26_1"]
    for phrase in ("**3,436**", "**1,896**", "**約45%**", "44.83%", "トリガー $K_2$", "**負**"):
        assert phrase in prose
    assert f"{example['policyholder_put']:,.2f}" in prose
    assert f"{example['transfer_cost_present_value']:,.2f}" in prose
    assert "差の符号は $K_2-K_1$ に従います" in prose
    assert "合成" in prose


def test_prose_numbers_come_from_the_saved_reference():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    lesson = _lesson(nbformat.read(NOTEBOOK, as_version=4))
    prose = "\n".join(cell.source for cell in lesson if cell.cell_type == "markdown")
    cases = {row["label"]: row for row in data["cases"]}
    line = data["figure"]["settlement_line"]
    means = data["conditional_mean"]
    expected = [
        f"{line['call_slope']:.4f}".replace("-", "−"),
        f"{cases['base_call_K1_90_K2_100']['price']:.4f}",
        f"{cases['base_call_K1_90_K2_100']['regular_price']:.4f}",
        f"{means['call']['closed_form']:.4f}",
        f"{means['put']['closed_form']:.4f}",
        f"{100 * data['example_26_1']['claim_probability']:.2f}\\%",
        f"{100 * data['example_26_1']['reduction']:.2f}%",
    ]
    for phrase in expected:
        assert phrase in prose, phrase
    assert "382.18" not in prose
