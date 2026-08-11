"""Fetch a reproducible, local SEC Company Facts/Submissions cache for B9.

This command is intentionally opt-in and writes only below the explicit
``--output`` directory.  It fetches every historical ``filings.files`` archive
advertised by the CIK submissions response; callers must provide a descriptive
User-Agent with contact information and may retain the resulting raw cache
outside the repository.  No ``filed`` fallback is introduced here.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SEC_BASE_URL = "https://data.sec.gov"
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+\.json$")


def _digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _cik_digest(ciks: Iterable[str]) -> str:
    """Return the canonical digest used to link a batch to its seed cohort."""

    normalized = tuple(sorted({_validate_cik(cik) for cik in ciks}))
    if not normalized:
        raise ValueError("at least one CIK is required for a digest")
    return _digest(("\n".join(normalized) + "\n").encode("ascii"))


def _validate_cik(value: str) -> str:
    digits = value.strip().lstrip("0") or "0"
    if not digits.isdigit() or len(digits) > 10 or not 1 <= int(digits) <= 9_999_999_999:
        raise ValueError("cik must be a positive numeric SEC CIK")
    return digits.zfill(10)


def _validate_user_agent(value: str) -> str:
    text = value.strip()
    if len(text) < 12 or "@" not in text:
        raise ValueError("user-agent must include a descriptive name and contact email")
    return text


def _fetch_json(
    url: str, *, user_agent: str, timeout_seconds: float
) -> tuple[bytes, dict[str, Any]]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": user_agent,
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            payload = gzip.decompress(payload)
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError(f"SEC response was not JSON: {url}") from error
    if not isinstance(decoded, dict):
        raise ValueError(f"SEC response must be a JSON object: {url}")
    return payload, decoded


def _safe_archive_name(value: Any) -> str:
    if not isinstance(value, str) or not _SAFE_FILENAME.fullmatch(value):
        raise ValueError(f"unsafe SEC archive filename: {value!r}")
    return value


def _write_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def fetch_sec_b9_cache(
    cik: str,
    output_dir: Path,
    *,
    user_agent: str,
    timeout_seconds: float = 60.0,
    sleep_seconds: float = 0.2,
    refresh: bool = False,
) -> dict[str, Any]:
    """Fetch a CIK's Company Facts, recent submissions, and all archives."""

    normalized_cik = _validate_cik(cik)
    validated_agent = _validate_user_agent(user_agent)
    if timeout_seconds <= 0.0 or sleep_seconds < 0.0:
        raise ValueError("timeout_seconds must be positive and sleep_seconds non-negative")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    urls = {
        "companyfacts": f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{normalized_cik}.json",
        "submissions": f"{SEC_BASE_URL}/submissions/CIK{normalized_cik}.json",
    }
    records: list[dict[str, Any]] = []

    def fetch_to_file(name: str, url: str) -> dict[str, Any]:
        path = output_dir / name
        if path.exists() and not refresh:
            payload = path.read_bytes()
            json.loads(payload)
            source = "cache"
        else:
            payload, _ = _fetch_json(
                url,
                user_agent=validated_agent,
                timeout_seconds=timeout_seconds,
            )
            _write_bytes(path, payload)
            source = "network"
            time.sleep(sleep_seconds)
        record = {
            "name": name,
            "url": url,
            "sha256": _digest(payload),
            "bytes": len(payload),
            "source": source,
        }
        records.append(record)
        return json.loads(payload)

    submissions = fetch_to_file(f"submissions_CIK{normalized_cik}.json", urls["submissions"])
    fetch_to_file(f"companyfacts_CIK{normalized_cik}.json", urls["companyfacts"])
    archive_metadata = submissions.get("filings", {}).get("files", [])
    if not isinstance(archive_metadata, list):
        raise ValueError("SEC submissions response has an invalid filings.files value")
    for metadata in sorted(archive_metadata, key=lambda item: str(item.get("name", ""))):
        if not isinstance(metadata, dict):
            raise ValueError("SEC filings.files entries must be objects")
        name = _safe_archive_name(metadata.get("name"))
        fetch_to_file(name, f"{SEC_BASE_URL}/submissions/{name}")

    manifest = {
        "schema_version": "b9-sec-cache-v1",
        "cik": normalized_cik,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "archive_count_advertised": len(archive_metadata),
        "file_count": len(records),
        "files": sorted(records, key=lambda item: item["name"]),
    }
    _write_bytes(
        output_dir / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def fetch_sec_b9_batch(
    ciks: Iterable[str],
    output_root: Path,
    *,
    user_agent: str,
    timeout_seconds: float = 60.0,
    sleep_seconds: float = 0.2,
    refresh: bool = False,
) -> dict[str, Any]:
    """Fetch multiple CIK caches below one explicit, auditable root.

    CIKs are normalized, deduplicated, and processed in numeric order so a
    manifest is stable with respect to the input file's ordering.  Each CIK
    retains the single-issuer manifest written by :func:`fetch_sec_b9_cache`;
    the batch manifest is only an index over those child caches.
    """

    normalized_ciks = tuple(sorted({_validate_cik(str(cik)) for cik in ciks}))
    if not normalized_ciks:
        raise ValueError("at least one CIK is required")
    validated_agent = _validate_user_agent(user_agent)
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for normalized_cik in normalized_ciks:
        try:
            manifest = fetch_sec_b9_cache(
                normalized_cik,
                output_root / f"CIK{normalized_cik}",
                user_agent=validated_agent,
                timeout_seconds=timeout_seconds,
                sleep_seconds=sleep_seconds,
                refresh=refresh,
            )
        except Exception as error:
            failures.append(
                {
                    "cik": normalized_cik,
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
            continue
        manifests.append(
            {
                "cik": normalized_cik,
                "directory": f"CIK{normalized_cik}",
                "file_count": int(manifest["file_count"]),
                "archive_count_advertised": int(manifest["archive_count_advertised"]),
                "manifest_sha256": _digest(
                    (output_root / f"CIK{normalized_cik}" / "manifest.json").read_bytes()
                ),
            }
        )
    batch_manifest = {
        "schema_version": "b9-sec-batch-v1",
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "requested_cik_count": len(normalized_ciks),
        "requested_cik_sha256": _cik_digest(normalized_ciks),
        "success_count": len(manifests),
        "failure_count": len(failures),
        "caches": manifests,
        "failures": failures,
    }
    _write_bytes(
        output_root / "batch_manifest.json",
        (json.dumps(batch_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return batch_manifest


def _read_cik_file(path: Path) -> tuple[str, ...]:
    """Read one CIK per line, ignoring blank lines and ``#`` comments."""

    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"CIK file does not exist: {path}")
    values = tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not values:
        raise ValueError("CIK file contains no CIK values")
    return values


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    cik_group = parser.add_mutually_exclusive_group(required=True)
    cik_group.add_argument("--cik", help="one SEC CIK, with or without leading zeroes")
    cik_group.add_argument(
        "--cik-file",
        type=Path,
        help="text file containing one SEC CIK per line; blank lines and # comments are ignored",
    )
    parser.add_argument("--output", required=True, type=Path, help="explicit local cache directory")
    parser.add_argument(
        "--user-agent",
        required=True,
        help="descriptive application name plus contact email, as required by SEC fair access",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--refresh", action="store_true", help="refetch existing cache files")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.cik is not None:
        manifest = fetch_sec_b9_cache(
            args.cik,
            args.output,
            user_agent=args.user_agent,
            timeout_seconds=args.timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            refresh=args.refresh,
        )
    else:
        manifest = fetch_sec_b9_batch(
            _read_cik_file(args.cik_file),
            args.output,
            user_agent=args.user_agent,
            timeout_seconds=args.timeout_seconds,
            sleep_seconds=args.sleep_seconds,
            refresh=args.refresh,
        )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
