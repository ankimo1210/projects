from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from quant_textbook.sec_cache_integrity import validate_sec_b9_batch_cache


def _digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_cache(root: Path, cik: str) -> dict[str, Any]:
    cache_dir = root / f"CIK{cik}"
    cache_dir.mkdir(parents=True)
    raw_payloads = {
        "arbitrary-first.json": b'{"first": true}\n',
        "arbitrary-second.json": b'{"second": true}\n',
    }
    records: list[dict[str, Any]] = []
    for name, payload in raw_payloads.items():
        (cache_dir / name).write_bytes(payload)
        records.append(
            {
                "name": name,
                "bytes": len(payload),
                "sha256": _digest(payload),
                "url": f"https://example.invalid/{name}",
                "source": "network",
            }
        )
    child_manifest = {
        "schema_version": "b9-sec-cache-v1",
        "cik": cik,
        "archive_count_advertised": 7,
        "file_count": len(records),
        "files": records,
    }
    child_path = cache_dir / "manifest.json"
    _write_json(child_path, child_manifest)
    return {
        "cik": cik,
        "directory": cache_dir.name,
        "file_count": len(records),
        "archive_count_advertised": 7,
        "manifest_sha256": _digest(child_path.read_bytes()),
    }


def _write_batch(root: Path, caches: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    _write_json(
        root / "batch_manifest.json",
        {
            "schema_version": "b9-sec-batch-v1",
            "requested_cik_count": len(caches) + len(failures),
            "success_count": len(caches),
            "failure_count": len(failures),
            "caches": caches,
            "failures": failures,
        },
    )


def _batch_payload(root: Path) -> dict[str, Any]:
    return json.loads((root / "batch_manifest.json").read_text(encoding="utf-8"))


def _rewrite_batch(root: Path, payload: dict[str, Any]) -> None:
    _write_json(root / "batch_manifest.json", payload)


def _refresh_child_hash(root: Path, payload: dict[str, Any], *, cache_index: int = 0) -> None:
    directory = payload["caches"][cache_index]["directory"]
    payload["caches"][cache_index]["manifest_sha256"] = _digest(
        (root / directory / "manifest.json").read_bytes()
    )


def test_valid_batch_cache_returns_only_declared_success_directories(tmp_path: Path) -> None:
    first = _write_cache(tmp_path, "0000000001")
    second = _write_cache(tmp_path, "0000000002")
    _write_batch(
        tmp_path,
        [first, second],
        [
            {
                "cik": "0000000003",
                "error_type": "HTTPError",
                "message": "not found",
            }
        ],
    )
    # A failed partial cache and unrelated root file must neither be assumed nor
    # consumed: only batch-manifest entries are the trusted input set.
    (tmp_path / "CIK0000000004").mkdir()
    (tmp_path / "notes.txt").write_text("unlisted", encoding="utf-8")

    result = validate_sec_b9_batch_cache(tmp_path)

    assert result.accepted
    assert result.errors == ()
    assert result.success_cik_count == 2
    assert [path.name for path in result.success_cik_dirs] == [
        "CIK0000000001",
        "CIK0000000002",
    ]


def test_batch_shape_and_null_cache_entry_fail_closed(tmp_path: Path) -> None:
    cache = _write_cache(tmp_path, "0000000001")
    _write_batch(tmp_path, [cache], [])
    batch = _batch_payload(tmp_path)
    batch["requested_cik_count"] = 2
    batch["caches"][0]["directory"] = None
    _rewrite_batch(tmp_path, batch)

    result = validate_sec_b9_batch_cache(tmp_path)

    assert not result.accepted
    assert result.success_cik_dirs == ()
    assert result.success_cik_count == 0
    assert any("requested_cik_count" in error for error in result.errors)
    assert any("directory must not be null" in error for error in result.errors)


def test_child_manifest_hash_and_cik_mismatches_fail_closed(tmp_path: Path) -> None:
    cache = _write_cache(tmp_path, "0000000001")
    _write_batch(tmp_path, [cache], [])
    batch = _batch_payload(tmp_path)
    child_path = tmp_path / cache["directory"] / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["cik"] = "0000000009"
    _write_json(child_path, child)
    _refresh_child_hash(tmp_path, batch)
    _rewrite_batch(tmp_path, batch)

    result = validate_sec_b9_batch_cache(tmp_path)

    assert not result.accepted
    assert result.success_cik_dirs == ()
    assert result.success_cik_count == 0
    assert any("child manifest.cik does not match" in error for error in result.errors)

    batch["caches"][0]["manifest_sha256"] = "0" * 64
    _rewrite_batch(tmp_path, batch)
    hash_result = validate_sec_b9_batch_cache(tmp_path)
    assert not hash_result.accepted
    assert any("manifest_sha256 mismatch" in error for error in hash_result.errors)


def test_raw_file_safety_size_and_digest_fail_closed(tmp_path: Path) -> None:
    cache = _write_cache(tmp_path, "0000000001")
    _write_batch(tmp_path, [cache], [])
    batch = _batch_payload(tmp_path)
    child_path = tmp_path / cache["directory"] / "manifest.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))

    raw_path = tmp_path / cache["directory"] / "arbitrary-first.json"
    raw_path.write_bytes(b'{"tampered": true}\n')
    result = validate_sec_b9_batch_cache(tmp_path)

    assert not result.accepted
    assert result.success_cik_dirs == ()
    assert result.success_cik_count == 0
    assert any(".bytes mismatch" in error for error in result.errors)
    assert any(".sha256 mismatch" in error for error in result.errors)

    child["files"][0]["name"] = "../outside.json"
    _write_json(child_path, child)
    _refresh_child_hash(tmp_path, batch)
    _rewrite_batch(tmp_path, batch)
    unsafe_result = validate_sec_b9_batch_cache(tmp_path)
    assert not unsafe_result.accepted
    assert any("must be a safe JSON filename" in error for error in unsafe_result.errors)


def test_missing_manifest_listed_raw_file_fails_closed(tmp_path: Path) -> None:
    cache = _write_cache(tmp_path, "0000000001")
    _write_batch(tmp_path, [cache], [])
    (tmp_path / cache["directory"] / "arbitrary-second.json").unlink()

    result = validate_sec_b9_batch_cache(tmp_path)

    assert not result.accepted
    assert result.success_cik_dirs == ()
    assert result.success_cik_count == 0
    assert any("does not exist as a regular file" in error for error in result.errors)
