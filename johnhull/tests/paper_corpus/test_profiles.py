"""Tests for the tracked source-page routing profile."""

from __future__ import annotations

from johnhull.scripts.paper_corpus.profiles import (
    DEFAULT_OUTPUT,
    build_profiles,
    render_profiles,
)


def test_tracked_page_profiles_are_deterministic_and_complete():
    expected = render_profiles(build_profiles())

    assert DEFAULT_OUTPUT.read_text(encoding="utf-8") == expected


def test_page_profiles_cover_all_sources_and_flag_known_damage():
    manifest = build_profiles()
    papers = {item["paper_id"]: item for item in manifest["papers"]}

    assert manifest["paper_count"] == 53
    assert manifest["page_count"] == 1586
    assert papers["1900-bachelier-theorie-de-la-speculation"]["ocr_language"] == "fra"
    assert papers["2000-mcneil-frey-tail-risk-evt"]["summary"]["damaged_pages"] == [5, 14, 24]
