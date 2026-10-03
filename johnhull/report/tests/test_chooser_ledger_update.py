"""The M25 ledger updater pins the integrated gate and selected D1 records."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


def _updater():
    return importlib.import_module("johnhull.scripts.update_chooser_ledger")


def test_missing_gate_leaves_ledger_untouched(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    ledger = tmp_path / "docs/section_ledger.json"
    ledger.parent.mkdir(parents=True)
    original = '{"sections": [{"id": "26.8", "status": "unreviewed"}]}\n'
    ledger.write_text(original, encoding="utf-8")
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    monkeypatch.setattr(updater, "LEDGER", ledger)
    with pytest.raises(ValueError, match="M25"):
        updater.main()
    assert ledger.read_text(encoding="utf-8") == original


def test_m25_record_rejects_changed_selected_file(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    selected = "docs/validation/d1-recheck/section-26-2/selected.json"
    record = tmp_path / selected
    record.parent.mkdir(parents=True)
    record.write_text("original\n", encoding="utf-8")
    digest = hashlib.sha256(record.read_bytes()).hexdigest()
    integrated = tmp_path / updater.M25_CHECK
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
    assert updater.m25_record("26.2") == selected
    record.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        updater.m25_record("26.2")


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
    integrated = tmp_path / updater.M25_CHECK
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
        updater.m25_record("26.2")
