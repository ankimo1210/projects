"""Source cash/units and shared display traces must agree with an independent account."""

import copy

import pytest
from hullkit import _chapter01_lesson as lesson

from johnhull.hullkit.tests import _chapter01_reference as reference


def test_all_37_source_values_and_four_shared_figures():
    expected = reference.build()
    assert expected["printed_value_count"] == 37
    assert reference.compare(lesson._values(), expected["values"]) < 1e-7
    actual = {
        key: [dict(role=t.meta["role"], x=list(t.x), y=list(t.y)) for t in fig.data]
        for key, fig in lesson._figures().items()
    }
    assert reference.compare(actual, expected["figures"]) < 1e-7


@pytest.mark.parametrize("mutation", ["premium", "quantity", "role", "missing", "nonfinite"])
def test_independent_oracle_rejects_material_display_errors(mutation):
    expected = reference.build()
    altered = copy.deepcopy(expected["figures"])
    if mutation == "premium":
        altered["intro_options"][0]["y"][0] += 2030
    elif mutation == "quantity":
        altered["intro_speculation"][1]["y"] = [
            v * 100 for v in altered["intro_speculation"][1]["y"]
        ]
    elif mutation == "nonfinite":
        altered["intro_options"][0]["y"][0] = float("nan")
    elif mutation == "role":
        altered["intro_forward"][0]["role"] = "short"
    else:
        altered.pop("intro_protection")
    with pytest.raises(ValueError):
        reference.compare(altered, expected["figures"])


def test_one_lesson_per_section_and_unrelated_notebook_cells_preserved():
    import json
    import subprocess
    from pathlib import Path

    notebook = (
        Path(__file__).parents[2] / "volumes/12_qualitative_summary/qualitative_summary.ipynb"
    )
    current = json.loads(notebook.read_text())["cells"]
    original = json.loads(
        subprocess.check_output(
            [
                "git",
                "show",
                "995188e6:johnhull/volumes/12_qualitative_summary/qualitative_summary.ipynb",
            ],
            text=True,
        )
    )["cells"]

    def source(cell):
        return "".join(cell["source"])

    text = "\n".join(map(source, current))
    for sid, _, _, _ in lesson.SECTIONS:
        assert text.count("### §" + sid + " ") == 1
    start = next(i for i, c in enumerate(current) if source(c).startswith("## 2."))
    old = next(i for i, c in enumerate(original) if source(c).startswith("## 2."))
    assert [source(c) for c in current[start:]] == [source(c) for c in original[old:]]
