"""The M19 ledger updater must not accept incomplete provenance."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def _updater():
    return importlib.import_module("johnhull.scripts.update_perpetual_ledger")


def test_missing_m19_gate_leaves_ledger_untouched(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    ledger = tmp_path / "docs/section_ledger.json"
    ledger.parent.mkdir(parents=True)
    original = '{"sections": [{"id": "26.2", "status": "unreviewed"}]}\n'
    ledger.write_text(original, encoding="utf-8")
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    monkeypatch.setattr(updater, "LEDGER", ledger)

    with pytest.raises((ValueError, FileNotFoundError), match=r"M19|m19"):
        updater.main()

    assert ledger.read_text(encoding="utf-8") == original


def test_refresh_earlier_replaces_m18_links_with_m19(tmp_path: Path, monkeypatch) -> None:
    updater = _updater()
    monkeypatch.setattr(updater, "PROJECT", tmp_path)
    for relative in (
        "docs/validation/section-26-1/m18-check.json",
        "docs/validation/section-26-2/m19-check.json",
        "docs/validation/d1-recheck/section-26-1/latest.json",
    ):
        file = tmp_path / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("{}\n", encoding="utf-8")
    section = {
        "id": "26.1",
        "evidence": {
            "m18_check": {
                "path": "docs/validation/section-26-1/m18-check.json",
                "kind": "record",
                "sha256": "old",
            },
            "m18_recheck": {
                "path": "docs/validation/section-26-1/m18-check.json",
                "kind": "record",
                "sha256": "old",
            },
            "browser_run": {
                "path": "docs/validation/section-26-1/m18-check.json",
                "kind": "record",
                "sha256": "old",
            },
            "notebook_check": {
                "path": "docs/validation/section-26-1/m18-check.json",
                "kind": "record",
                "sha256": "old",
            },
        },
        "requirements": [
            {
                "coverage": {
                    "independent_validation": {"refs": ["m18_check", "m18_recheck"]},
                    "rendered": {"refs": ["browser_run", "notebook_check"]},
                }
            }
        ],
    }
    d1 = tmp_path / "docs/validation/d1-recheck/section-26-1/latest.json"
    d1.write_text(json.dumps({"section_id": "26.1", "status": "PASS"}), encoding="utf-8")

    updater.refresh_earlier(section)

    assert "m18_check" not in section["evidence"]
    assert "m18_recheck" not in section["evidence"]
    assert section["evidence"]["m19_check"]["path"].endswith("m19-check.json")
    assert section["evidence"]["m19_recheck"]["path"].endswith("latest.json")
    assert section["requirements"][0]["coverage"]["independent_validation"]["refs"] == [
        "m19_check",
        "m19_recheck",
    ]
