"""Fail-closed contracts for the §26.6 integrated acceptance record."""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest


def _gate():
    return importlib.import_module("johnhull.scripts.build_cliquet_acceptance_record")


def _write(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_record_rejects_stale_source(tmp_path: Path, monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "PROJECT", tmp_path)
    source = "scripts/source.py"
    artifact = "docs/reference.json"
    _write(tmp_path / source, "changed\n")
    record = {
        "section": "26.6",
        "status": "PASS",
        "source_sha256": {source: "0" * 64},
        "artifact_sha256": {artifact: _write(tmp_path / artifact, "{}\n")},
    }
    _write(tmp_path / "docs/record.json", json.dumps(record))
    with pytest.raises(ValueError, match="stale source_sha256"):
        gate.check_record("docs/record.json")


def test_browser_matrix_rejects_missing_state() -> None:
    gate = _gate()
    states = [
        {"figure": key, "width": width, "numeric_checked": True}
        for key in gate.KEYS
        for width in (1440, 1000)
    ]
    pages = {
        surface: {
            "states": deepcopy(states),
            "screenshots": [
                f"{gate.SECTION}{surface}-{row['figure']}-{row['width']}.png" for row in states
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
        "book_math": {"rendered": 833, "errors": 0},
    }
    gate.check_browser(browser)
    pages["book"]["states"].pop()
    with pytest.raises(ValueError, match="browser matrix"):
        gate.check_browser(browser)


def test_d1_payload_rejects_missing_mirror() -> None:
    gate = _gate()
    folder = gate.PROJECT / "docs/validation/d1-recheck/section-26-2"
    path = sorted(
        file for file in folder.glob("*.json") if not file.name.endswith(".browser.json")
    )[-1]
    name = path.relative_to(gate.PROJECT).as_posix()
    record = json.loads((gate.PROJECT / name).read_text(encoding="utf-8"))
    del record["storage_verification"]["mirror"]
    with pytest.raises(ValueError, match="mirror"):
        gate.check_d1_payload("26.2", name, record)


def test_integrated_record_covers_twenty_two_sections() -> None:
    gate = _gate()
    record = json.loads(gate.OUT.read_text(encoding="utf-8"))
    assert record["milestone"] == "M23"
    assert set(record["regression"]["d1"]) == set(gate.EARLIER)
    assert record["numerical"]["cases"] == 60
    assert record["browser"]["state_checks"] == 16


@pytest.mark.parametrize("category", ["source_sha256", "artifact_sha256"])
def test_d1_rejects_each_missing_required_hash(category) -> None:
    gate = _gate()
    integrated = json.loads(gate.OUT.read_text(encoding="utf-8"))
    name = integrated["regression"]["d1"]["26.5"]["record"]
    record = json.loads((gate.PROJECT / name).read_text(encoding="utf-8"))
    # Every hash emitted by the D1 producer is required, independently of the
    # reduced inventory an incomplete record might claim for itself.
    for source in record[category]:
        changed = deepcopy(record)
        del changed[category][source]
        with pytest.raises(ValueError, match=f"missing {category}"):
            gate.check_d1_payload("26.5", name, changed)
