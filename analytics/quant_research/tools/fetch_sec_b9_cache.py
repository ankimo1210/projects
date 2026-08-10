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
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SEC_BASE_URL = "https://data.sec.gov"
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+\.json$")


def _digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cik", required=True, help="SEC CIK, with or without leading zeroes")
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
    manifest = fetch_sec_b9_cache(
        args.cik,
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
