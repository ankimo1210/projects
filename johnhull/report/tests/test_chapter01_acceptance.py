"""Acceptance must refuse omitted numerical checks and incomplete rendered evidence."""

import copy
import json
from pathlib import Path

import pytest

from johnhull.scripts.verify_chapter01_acceptance import check_sweep

PROJECT = Path(__file__).resolve().parents[2]


def records():
    """Use the actual generated chapter records as the positive control."""
    output = PROJECT / "docs/validation/chapter-01"
    return (
        json.loads((output / "browser-check.json").read_text()),
        json.loads((PROJECT / "docs/acceptance/chapters/ch01.json").read_text()),
        json.loads((output / "reference.json").read_text()),
    )


def test_complete_section_sweep_is_accepted():
    check_sweep(*records())


@pytest.mark.parametrize(
    "mutation",
    [
        "printed_count",
        "printed_unchecked",
        "figure_unchecked",
        "explanation",
        "missing_state",
        "duplicate_capture",
        "missing_capture",
        "mutation",
    ],
)
def test_omitted_checks_and_captures_are_rejected(mutation):
    browser, cfg, reference = records()
    browser = copy.deepcopy(browser)
    row = browser["sections"]["1.3"][0]
    if mutation == "printed_count":
        row["printed_value_count"] -= 1
    elif mutation == "printed_unchecked":
        row["printed_values_checked"] = False
    elif mutation == "figure_unchecked":
        row["figure_values_checked"] = False
    elif mutation == "explanation":
        row["explanation_checked"] = False
    elif mutation == "missing_state":
        browser["sections"]["1.2"].pop()
    elif mutation == "duplicate_capture":
        browser["captures"][-1] = copy.deepcopy(browser["captures"][0])
    elif mutation == "missing_capture":
        browser["captures"].pop()
    else:
        browser["book_mutation_rejected"] = False
    with pytest.raises(ValueError):
        check_sweep(browser, cfg, reference)


@pytest.mark.parametrize("existing", [False, True])
def test_chapter_page_is_created_and_stale_page_is_rebuilt(tmp_path, existing):
    """The generated companion must exist after both first and repeated builds."""
    from johnhull.scripts.build_chapter01_portal import build

    chapter = tmp_path / "chapters/ch01.html"
    if existing:
        chapter.parent.mkdir()
        chapter.write_text("STALE CHAPTER")
    assert build(output_dir=tmp_path) == chapter
    lesson = chapter.read_text()
    assert "STALE CHAPTER" not in lesson
    assert lesson.count("<h3>") == 10
    assert lesson.count('class="plotly-graph-div"') == 4
    assert "Jupyter Book" in lesson and "ポータルのホーム" in lesson
