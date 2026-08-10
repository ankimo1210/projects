from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _load_fetcher() -> ModuleType:
    path = Path(__file__).parents[1] / "tools" / "fetch_sec_b9_cache.py"
    spec = importlib.util.spec_from_file_location("fetch_sec_b9_cache", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load SEC cache fetcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetcher_fetches_every_archive_and_writes_hash_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_fetcher()
    archive_name = "CIK0000320193-submissions-001.json"
    submissions = {
        "filings": {
            "files": [{"name": archive_name}],
        }
    }
    companyfacts: dict[str, Any] = {"facts": {}}
    archive = {
        "accessionNumber": ["0000320193-14-000010"],
        "filingDate": ["2014-02-01"],
        "acceptanceDateTime": ["2014-02-01T17:00:00-05:00"],
        "form": ["10-K"],
    }
    responses = {
        "https://data.sec.gov/submissions/CIK0000320193.json": submissions,
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json": companyfacts,
        f"https://data.sec.gov/submissions/{archive_name}": archive,
    }
    calls: list[str] = []

    def fake_fetch(url: str, **_: Any) -> tuple[bytes, dict[str, Any]]:
        calls.append(url)
        payload = responses[url]
        rendered = json.dumps(payload).encode("utf-8")
        return rendered, payload

    monkeypatch.setattr(module, "_fetch_json", fake_fetch)
    manifest = module.fetch_sec_b9_cache(
        "320193",
        tmp_path,
        user_agent="quant-textbook test test@example.com",
        sleep_seconds=0.0,
    )
    assert len(calls) == 3
    assert manifest["archive_count_advertised"] == 1
    assert manifest["file_count"] == 3
    assert (tmp_path / archive_name).exists()
    assert (tmp_path / "manifest.json").exists()
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])

    monkeypatch.setattr(module, "_fetch_json", lambda *_args, **_kwargs: pytest.fail("cache miss"))
    cached = module.fetch_sec_b9_cache(
        "320193",
        tmp_path,
        user_agent="quant-textbook test test@example.com",
        sleep_seconds=0.0,
    )
    assert cached["file_count"] == 3


def test_fetcher_rejects_unsafe_archive_names_and_contactless_user_agents() -> None:
    module = _load_fetcher()
    with pytest.raises(ValueError, match="unsafe"):
        module._safe_archive_name("../secret.json")
    with pytest.raises(ValueError, match="contact email"):
        module._validate_user_agent("quant-textbook")
