"""The M28 ledger updater pins the integrated gate and selected D1 records."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from pathlib import Path

import pytest


def _updater():
    return importlib.import_module("johnhull.scripts.update_martingale_ledger")


def test_registered_source_pages_use_the_ledger_range_contract(monkeypatch):
    section = {"id": "28.3"}
    updater = _updater()
    assert updater.M28_CHECK == "docs/validation/section-28-3/m28-check.json"
    monkeypatch.setattr(updater, "item", lambda path, kind: {"path": path, "kind": kind})
    updater.register_martingale(section)
    assert section["source_pages"] == [675, 676]
    assert [r["id"] for r in section["requirements"]] == [f"MT{n:02}" for n in range(1, 7)]


def test_missing_gate_leaves_ledger_untouched(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    ledger = tmp_path / "docs/section_ledger.json"
    ledger.parent.mkdir(parents=True)
    original = '{"sections": [{"id": "28.3", "status": "unreviewed"}]}\n'
    ledger.write_text(original, encoding="utf-8")
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    monkeypatch.setattr(updater, "LEDGER", ledger)
    with pytest.raises(ValueError, match="M28"):
        updater.main()
    assert ledger.read_text(encoding="utf-8") == original


def test_failed_integrated_check_leaves_ledger_untouched(tmp_path, monkeypatch):
    updater = _updater()
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    ledger = tmp_path / "docs/section_ledger.json"
    ledger.parent.mkdir(parents=True)
    original = '{"sections": [{"id": "28.3", "status": "unreviewed"}]}\n'
    ledger.write_text(original)
    monkeypatch.setattr(updater, "LEDGER", ledger)
    gate = tmp_path / updater.M28_CHECK
    gate.parent.mkdir(parents=True)
    gate.write_text(json.dumps({"section": "28.3", "milestone": "M28", "status": "PASS"}))

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(updater.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        updater.main()
    assert ledger.read_text() == original


def test_m28_record_rejects_changed_selected_file(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    selected = "docs/validation/d1-recheck/section-26-2/selected.json"
    record = tmp_path / selected
    record.parent.mkdir(parents=True)
    record.write_text("original\n", encoding="utf-8")
    digest = hashlib.sha256(record.read_bytes()).hexdigest()
    integrated = tmp_path / updater.M28_CHECK
    integrated.parent.mkdir(parents=True)
    integrated.write_text(
        json.dumps(
            {
                "regression": {"d1": {"26.2": {"record": selected}}},
                "source_sha256": {selected: digest},
            }
        ),
        encoding="utf-8",
    )
    assert updater.m28_record("26.2") == selected
    record.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        updater.m28_record("26.2")


@pytest.mark.parametrize(
    "selected",
    [
        "docs/validation/d1-recheck/section-26-2/../section-26-3/selected.json",
        "/docs/validation/d1-recheck/section-26-2/selected.json",
        "docs/validation/d1-recheck/section-26-3/selected.json",
        "docs/validation/d1-recheck/section-26-2/selected.txt",
        "docs/validation/d1-recheck/section-26-2/..\\selected.json",
    ],
)
def test_selected_path_cannot_escape_its_section(tmp_path, monkeypatch, selected):
    updater = _updater()
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    integrated = tmp_path / updater.M28_CHECK
    integrated.parent.mkdir(parents=True)
    integrated.write_text(
        json.dumps(
            {
                "regression": {"d1": {"26.2": {"record": selected}}},
                "source_sha256": {selected: "0" * 64},
            }
        )
    )
    with pytest.raises(ValueError, match="path is invalid"):
        updater.m28_record("26.2")
