"""Source-integrity tests for the tracked paper-corpus baseline."""

from __future__ import annotations

import json
from pathlib import Path

from johnhull.scripts.paper_corpus.baseline import (
    DEFAULT_OUTPUT,
    REFERENCES_ROOT,
    build_baseline,
    render_baseline,
)


def test_tracked_baseline_is_deterministic_and_current():
    expected = render_baseline(build_baseline(REFERENCES_ROOT))

    assert DEFAULT_OUTPUT.read_text(encoding="utf-8") == expected


def test_baseline_has_complete_source_and_corpus_integrity():
    manifest = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    assert manifest["source_count"] == 53
    assert manifest["source_page_count"] == 1586
    assert all(
        item["source_hash_matches_metadata"] and item["page_count_matches_corpus"]
        for item in manifest["sources"]
        if item["corpus_present"]
    )
    assert {item["paper_id"] for item in manifest["sources"]} == {
        path.stem for path in (REFERENCES_ROOT / "papers").glob("*.pdf")
    }


def test_required_semantic_sources_are_present_and_hashed():
    manifest = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    required = {item["source_id"]: item for item in manifest["required_semantic_sources"]}

    assert set(required) == {
        "2003-jarrow-yildirim-inflation-hjm",
        "2021-mof-jgbi-indexation-notice",
        "2024-mof-jgbi-bei-guide",
    }
    assert all(item["status"] == "present" for item in required.values())
    assert all(len(item["source_sha256"]) == 64 for item in required.values())
