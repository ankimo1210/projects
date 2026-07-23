"""Full-corpus release helper tests."""

from __future__ import annotations

from johnhull.scripts.paper_corpus.release import (
    build_determinism_report,
    write_determinism_report,
)


def test_determinism_report_requires_same_paths_and_bytes(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "same.txt").write_text("same\n", encoding="utf-8")
    (second / "same.txt").write_text("same\n", encoding="utf-8")

    assert build_determinism_report(first, second)["status"] == "pass"
    report = write_determinism_report(first, second)
    assert report["compared_file_count"] == 1
    assert (first / "determinism_report.json").read_bytes() == (
        second / "determinism_report.json"
    ).read_bytes()

    (second / "same.txt").write_text("changed\n", encoding="utf-8")
    failed = build_determinism_report(first, second)
    assert failed["status"] == "fail"
    assert failed["changed_files"] == ["same.txt"]
