"""Extractor bake-off and selection-policy regression tests."""

from __future__ import annotations

from johnhull.scripts.paper_corpus.benchmark import (
    DEFAULT_BAKEOFF_OUTPUT,
    build_bakeoff,
    read_bakeoff,
    render_bakeoff,
    validate_bakeoff,
)


def test_tracked_bakeoff_is_current_and_valid():
    value = read_bakeoff()

    validate_bakeoff(value)
    assert DEFAULT_BAKEOFF_OUTPUT.read_text(encoding="utf-8") == render_bakeoff(build_bakeoff())


def test_bakeoff_records_known_hull_white_failures():
    cases = {item["case_id"]: item for item in read_bakeoff()["cases"]}

    assert cases["hw-p6-mean-reversion-equation-15"]["results"]["mineru-3.4.4-pipeline"] == "fail"
    assert (
        cases["hw-p17-table3-and-table4-other-cells"]["results"]["mineru-3.4.4-pipeline"] == "fail"
    )


def test_selection_never_promotes_raw_extractor_output_to_verified():
    selection = read_bakeoff()["selection"]

    assert selection["status"] == "accepted_with_controls"
    assert any("never verified" in item.lower() for item in selection["required_controls"])
    assert selection["dependency_policy"].startswith("optional pinned uvx")
