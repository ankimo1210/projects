from __future__ import annotations

from pathlib import Path

import httpx
from jhrmbs.config import AppConfig, SourceConfig
from jhrmbs.ingest import RawDownloader, _carried_forward_records
from jhrmbs.util import atomic_write_json


def test_downloader_records_hash_and_reuses_conditional_cache(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304, request=request)
        return httpx.Response(
            200,
            content=b"public data",
            headers={"content-type": "text/csv", "etag": '"v1"'},
            request=request,
        )

    source = SourceConfig(
        id="test",
        kind="file",
        url="https://example.com/data.csv",
        allowed_hosts=("example.com",),
        data_definition="test data",
        coverage="test period",
    )
    config = AppConfig(data_root=tmp_path)
    with RawDownloader(config, transport=httpx.MockTransport(handler)) as downloader:
        first = downloader.fetch(source, source.url, role="data")
        second = downloader.fetch(source, source.url, role="data")
    assert calls == 2
    assert first.sha256 == second.sha256
    assert second.cache_status == "not_modified"
    assert (tmp_path / first.object_path).read_bytes() == b"public data"


def test_partial_ingest_carries_unselected_sources_from_latest_snapshot(tmp_path: Path) -> None:
    manifest = tmp_path / "raw" / "manifests" / "old.json"
    atomic_write_json(
        manifest,
        {
            "snapshot_id": "old",
            "records": [
                {"source_id": "jhf_monthly", "role": "data", "sha256": "jhf"},
                {"source_id": "mof_jgb", "role": "data", "sha256": "jgb"},
                {"source_id": "removed", "role": "data", "sha256": "old"},
            ],
        },
    )
    atomic_write_json(
        tmp_path / "raw" / "latest_manifest.json",
        {"snapshot_id": "old", "manifest_path": "raw/manifests/old.json"},
    )
    carried, snapshot = _carried_forward_records(
        tmp_path,
        {"mof_jgb"},
        {"jhf_monthly", "mof_jgb"},
    )
    assert snapshot == "old"
    assert [record["source_id"] for record in carried] == ["jhf_monthly"]
