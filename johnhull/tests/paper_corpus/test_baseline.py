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

    assert manifest["source_count"] == 50
    assert manifest["source_page_count"] == 1536
    assert manifest["corpus_chunk_count"] == 780
    assert all(item["corpus_present"] for item in manifest["sources"])
    assert all(item["source_hash_matches_metadata"] for item in manifest["sources"])
    assert all(item["page_count_matches_corpus"] for item in manifest["sources"])
    assert {item["paper_id"] for item in manifest["sources"]} == {
        path.stem for path in (REFERENCES_ROOT / "papers").glob("*.pdf")
    }


def test_required_missing_sources_are_explicit():
    manifest = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    missing = {item["source_id"]: item["status"] for item in manifest["required_semantic_sources"]}

    assert missing["2003-jarrow-yildirim-inflation-hjm"] == "missing_source"
    assert missing["japan-mof-jgbi-conventions"] == "missing_source"
