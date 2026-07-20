from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from .profiles import project_root


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifests() -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((project_root() / "manifests" / "sources").glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
        if not isinstance(document, dict):
            raise ValueError(f"source manifest is not a mapping: {path}")
        manifests.append((path, document))
    return manifests


def _verify_paper(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    local_path = project_root() / manifest["local_path"]
    result: dict[str, Any] = {
        "manifest": manifest_path.name,
        "kind": "paper",
        "paper_id": manifest["paper_id"],
        "path": str(local_path),
        "exists": local_path.is_file(),
    }
    if local_path.is_file():
        actual = sha256_file(local_path)
        result.update(actual_sha256=actual, expected_sha256=manifest["sha256"])
        result["hash_matches"] = actual == manifest["sha256"]
    else:
        result["hash_matches"] = None
    return result


def _verify_repository(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    root = project_root() / manifest["local_path"]
    files: list[dict[str, Any]] = []
    for evidence in manifest.get("files_used_as_evidence", []):
        path = root / evidence["path"]
        item: dict[str, Any] = {
            "path": evidence["path"],
            "exists": path.is_file(),
            "expected_sha256": evidence["sha256"],
        }
        if path.is_file():
            item["actual_sha256"] = sha256_file(path)
            item["hash_matches"] = item["actual_sha256"] == evidence["sha256"]
        else:
            item["hash_matches"] = None
        files.append(item)
    return {
        "manifest": manifest_path.name,
        "kind": "repository",
        "repository": manifest["repository"],
        "commit": manifest["commit"],
        "license_status": manifest["license_status"],
        "exists": root.is_dir(),
        "files": files,
        "hash_matches": all(item["hash_matches"] is True for item in files)
        if root.is_dir()
        else None,
    }


def verify_sources() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path, manifest in source_manifests():
        if "paper_id" in manifest:
            items.append(_verify_paper(path, manifest))
        elif "repository" in manifest:
            items.append(_verify_repository(path, manifest))
        else:
            items.append({"manifest": path.name, "kind": "unknown", "hash_matches": False})
    mismatches = [item["manifest"] for item in items if item.get("hash_matches") is False]
    missing = [item["manifest"] for item in items if not item.get("exists")]
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "missing_optional_local_sources": missing,
        "items": items,
    }


def fetch_papers(*, overwrite: bool = False) -> list[dict[str, Any]]:
    """Fetch only pinned paper PDFs. Never called at import time."""

    results: list[dict[str, Any]] = []
    for _, manifest in source_manifests():
        if "paper_id" not in manifest:
            continue
        destination = project_root() / manifest["local_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            results.append({"paper_id": manifest["paper_id"], "status": "exists"})
            continue
        temporary = destination.with_suffix(destination.suffix + ".part")
        with urllib.request.urlopen(manifest["source_url"], timeout=60) as response:
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
        actual = sha256_file(temporary)
        if actual != manifest["sha256"]:
            temporary.unlink(missing_ok=True)
            raise ValueError(
                f"hash mismatch for {manifest['paper_id']}: {actual} != {manifest['sha256']}"
            )
        temporary.replace(destination)
        results.append({"paper_id": manifest["paper_id"], "status": "downloaded"})
    return results


def fetch_repositories() -> list[dict[str, Any]]:
    """Fetch pinned repository archives into the ignored local evidence area."""

    results: list[dict[str, Any]] = []
    for _, manifest in source_manifests():
        if "repository" not in manifest:
            continue
        destination = project_root() / manifest["local_path"]
        if destination.exists():
            verification = _verify_repository(Path("existing"), manifest)
            if verification["hash_matches"] is not True:
                raise ValueError(f"existing reference tree failed evidence hashes: {destination}")
            results.append({"repository": manifest["repository"], "status": "exists"})
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="source-fetch-", dir=destination.parent
        ) as temporary_name:
            temporary = Path(temporary_name)
            archive_path = temporary / "reference.tar.gz"
            with urllib.request.urlopen(manifest["archive_url"], timeout=120) as response:
                with archive_path.open("wb") as output:
                    shutil.copyfileobj(response, output)
            archive_hash = sha256_file(archive_path)
            if archive_hash != manifest["archive_sha256"]:
                raise ValueError(
                    f"archive hash mismatch for {manifest['repository']}: "
                    f"{archive_hash} != {manifest['archive_sha256']}"
                )
            extraction_root = temporary / "extracted"
            extraction_root.mkdir()
            with tarfile.open(archive_path, mode="r:gz") as archive:
                archive.extractall(extraction_root, filter="data")
            candidates = [item for item in extraction_root.iterdir() if item.is_dir()]
            if len(candidates) != 1:
                raise ValueError(
                    f"unexpected archive layout for {manifest['repository']}: {candidates}"
                )
            extracted = candidates[0]
            for evidence in manifest.get("files_used_as_evidence", []):
                evidence_path = extracted / evidence["path"]
                if not evidence_path.is_file():
                    raise ValueError(f"archive lacks evidence file: {evidence['path']}")
                actual = sha256_file(evidence_path)
                if actual != evidence["sha256"]:
                    raise ValueError(
                        f"evidence hash mismatch for {manifest['repository']}/{evidence['path']}"
                    )
            extracted.rename(destination)
        results.append({"repository": manifest["repository"], "status": "downloaded"})
    return results


def fetch_all_sources() -> dict[str, list[dict[str, Any]]]:
    return {"papers": fetch_papers(), "repositories": fetch_repositories()}
