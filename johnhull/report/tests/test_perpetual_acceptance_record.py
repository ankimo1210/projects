"""Fail-closed contracts for the §26.2 integrated acceptance record."""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest


def _write(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gate():
    return importlib.import_module("johnhull.scripts.build_perpetual_acceptance_record")


def test_record_rejects_stale_source_even_when_status_pass(tmp_path: Path, monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    source = "scripts/source.py"
    artifact = "docs/reference.json"
    _write(tmp_path / source, "changed source\n")
    artifact_hash = _write(tmp_path / artifact, "{}\n")
    record = {
        "section": "26.2",
        "status": "PASS",
        "source_sha256": {source: "0" * 64},
        "artifact_sha256": {artifact: artifact_hash},
    }
    _write(tmp_path / "docs/record.json", json.dumps(record))

    with pytest.raises(ValueError, match="stale source_sha256"):
        gate.check_record("docs/record.json")


def test_browser_record_uses_hashes_without_a_section_field(tmp_path: Path, monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    source = "scripts/browser.cjs"
    artifact = "docs/browser.png"
    record = {
        "status": "PASS",
        "source_sha256": {source: _write(tmp_path / source, "browser source\n")},
        "artifact_sha256": {artifact: _write(tmp_path / artifact, "image\n")},
    }
    name = "docs/browser-check.json"
    _write(tmp_path / name, json.dumps(record))

    assert gate.check_record(name) == record


def test_record_rejects_missing_required_artifact_hash(tmp_path: Path, monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    source = "scripts/browser.cjs"
    artifact = "report/site/exotics.html"
    record = {
        "status": "PASS",
        "source_sha256": {source: _write(tmp_path / source, "browser source\n")},
        "artifact_sha256": {artifact: _write(tmp_path / artifact, "<html/>\n")},
    }
    name = "docs/browser-check.json"
    _write(tmp_path / name, json.dumps(record))

    with pytest.raises(ValueError, match="missing artifact_sha256"):
        gate.check_record(
            name,
            required_sources={source},
            required_artifacts={artifact, "book/_build/html/notebooks/10_exotics.html"},
        )


def test_integrated_record_fingerprints_the_vol06_verifier_it_runs() -> None:
    gate = _gate()
    record = json.loads(gate.OUT.read_text(encoding="utf-8"))

    assert "scripts/verify_american_mc_notebook.py" in record["source_sha256"]
    assert "scripts/verify_accepted_vol06_notebook.py" not in record["source_sha256"]


def test_browser_matrix_rejects_missing_width_state() -> None:
    gate = _gate()
    keys = gate.KEYS
    states = [
        {"figure": key, "width": width, "numeric_checked": True}
        for key in keys
        for width in (1440, 1000)
    ]
    pages = {
        surface: {
            "states": states.copy(),
            "screenshots": [
                f"docs/validation/section-26-2/{surface}-{row['figure']}-{row['width']}.png"
                for row in states
            ],
            "numeric_mutation_rejected": True,
            "page_errors": [],
            "unapproved_requests": [],
        }
        for surface in ("book", "portal")
    }
    browser = {
        "status": "PASS",
        "state_checks": 16,
        "screenshots": 16,
        "pages": pages,
        "book_math": {"rendered": 700, "errors": 0},
    }
    gate.check_browser(browser)

    pages["portal"]["states"].pop()
    with pytest.raises(ValueError, match="browser matrix"):
        gate.check_browser(browser)


def test_d1_reuse_rejects_missing_baseline(tmp_path: Path, monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    folder = tmp_path / "docs/validation/d1-recheck/section-26-1"
    record = {
        "schema_version": 2,
        "status": "PASS",
        "section_id": "26.1",
        "decision": "reused",
        "baseline": {"record": "docs/validation/missing-baseline.json"},
        "checks": {"pytest": {"status": "PASS", "passed": 1}},
        "storage_verification": {"status": "PASS"},
        "source_sha256": {},
        "artifact_sha256": {},
        "images": [],
        "observations": {"stored_new_bytes": 0},
    }
    _write(folder / "latest.json", json.dumps(record))

    with pytest.raises(ValueError, match="baseline"):
        gate.check_d1("26.1")


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("checks", "runtime_probe"),
        ("images", "images"),
        ("source_sha256", "source_sha256"),
        ("artifact_sha256", "artifact_sha256"),
        ("mirror", "mirror"),
    ],
)
def test_d1_payload_rejects_incomplete_record(field: str, expected: str) -> None:
    gate = _gate()
    folder = gate.PROJECT / "docs/validation/d1-recheck/section-26-1"
    path = sorted(
        file for file in folder.glob("*.json") if not file.name.endswith(".browser.json")
    )[-1]
    record = deepcopy(json.loads(path.read_text(encoding="utf-8")))
    if field == "checks":
        del record["checks"]["runtime_probe"]
    elif field == "images":
        record["images"] = []
    elif field == "source_sha256":
        record["source_sha256"] = {}
    elif field == "artifact_sha256":
        record["artifact_sha256"] = {}
    else:
        del record["storage_verification"]["mirror"]

    with pytest.raises(ValueError, match=expected):
        gate.check_d1_payload("26.1", path.relative_to(gate.PROJECT).as_posix(), record)
