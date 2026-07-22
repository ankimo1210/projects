"""Gold-set selection and verified-assertion tests."""

from __future__ import annotations

import json

from johnhull.scripts.paper_corpus.gold import (
    DEFAULT_ASSERTIONS_OUTPUT,
    DEFAULT_MANIFEST_OUTPUT,
    build_gold_manifest,
    render_assertions,
    render_json,
)
from johnhull.scripts.paper_corpus.gold_import import (
    DEFAULT_LAYOUT_LABELS_OUTPUT,
    table_cell_count,
    validate_layout_labels,
)
from johnhull.scripts.paper_corpus.schema import P0_PAPER_IDS


def test_tracked_gold_artifacts_are_current():
    assert DEFAULT_MANIFEST_OUTPUT.read_text(encoding="utf-8") == render_json(build_gold_manifest())
    assert DEFAULT_ASSERTIONS_OUTPUT.read_text(encoding="utf-8") == render_assertions()


def test_gold_page_selection_is_large_stratified_and_unique():
    manifest = json.loads(DEFAULT_MANIFEST_OUTPUT.read_text(encoding="utf-8"))
    pages = manifest["selected_pages"]

    assert manifest["paper_count"] >= 10
    assert manifest["page_count"] >= manifest["targets"]["minimum_pages"]
    assert len({item["gold_page_id"] for item in pages}) == len(pages)
    assert any("damaged" in item["selection_reasons"] for item in pages)
    assert any("math_dense" in item["selection_reasons"] for item in pages)
    assert set(P0_PAPER_IDS) <= {item["paper_id"] for item in pages}


def test_verified_assertions_have_source_pages_and_reviewers():
    manifest = json.loads(DEFAULT_MANIFEST_OUTPUT.read_text(encoding="utf-8"))
    selected = {item["gold_page_id"] for item in manifest["selected_pages"]}
    assertions = [
        json.loads(line)
        for line in DEFAULT_ASSERTIONS_OUTPUT.read_text(encoding="utf-8").splitlines()
    ]

    assert assertions
    assert len({item["assertion_id"] for item in assertions}) == len(assertions)
    for assertion in assertions:
        page_id = f"{assertion['paper_id']}:p{assertion['page_number']:04d}"
        assert page_id in selected
        assert assertion["verification_status"] == "verified"
        assert assertion["reviewer"]


def test_regression_cells_preserve_hull_white_table_four_values():
    assertions = [
        json.loads(line)
        for line in DEFAULT_ASSERTIONS_OUTPUT.read_text(encoding="utf-8").splitlines()
    ]
    cells = {
        (item.get("row_key"), item.get("column_key")): item.get("expected_numeric")
        for item in assertions
        if item["kind"] == "table_cell" and item.get("table_number") == "4"
    }

    assert cells[("1.0|Ext Vas", "1.02")] == 0.35
    assert cells[("1.0|Two-factor CIR", "1.02")] == 0.34


def test_reviewed_layout_labels_meet_all_annotation_targets():
    labels = json.loads(DEFAULT_LAYOUT_LABELS_OUTPUT.read_text(encoding="utf-8"))

    validate_layout_labels(labels)
    assert labels["totals"] == {
        "pages": 88,
        "display_equations": 173,
        "inline_equations": 431,
        "tables": 14,
        "table_cells": 585,
    }


def test_table_cell_counter_preserves_merged_headers_as_single_cells():
    html = "<table><tr><th colspan='2'>Header</th></tr><tr><td>A</td><td>B</td></tr></table>"

    assert table_cell_count(html) == 3
