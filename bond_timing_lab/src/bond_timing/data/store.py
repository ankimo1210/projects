"""Where raw snapshots live, and how they are fetched and read back (design §4.5)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from macrokit.snapshot import SnapshotResult, latest_payload, save_snapshot

RAW_ROOT = Path(
    os.environ.get("BOND_TIMING_RAW", "/home/kazumasa/projects/_data/bond_timing_lab/raw")
)
MACROKIT_RAW = Path(
    os.environ.get("BOND_TIMING_MACROKIT_RAW", "/home/kazumasa/projects/macrokit/data/raw")
)
USER_AGENT = "Mozilla/5.0 (compatible; macrokit research)"


class FetchError(RuntimeError):
    """A remote file could not be fetched."""


def fetch(url: str, *, timeout: float = 300.0) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise FetchError(f"GET {url} returned {response.status_code}")
    return response.content


def store_bytes(
    root: Path, source: str, indicator: str, content: bytes, *, url: str, filename: str
) -> SnapshotResult:
    return save_snapshot(
        root,
        source,
        indicator,
        content,
        ingested_at=datetime.now(UTC),
        url=url,
        http_status=200,
        filename=filename,
    )


def read_latest(root: Path, source: str, indicator: str) -> bytes:
    path = latest_payload(root, source, indicator)
    if path is None:
        raise FileNotFoundError(
            f"no stored snapshot for {source}/{indicator} under {root}; run `bond-timing snapshot`"
        )
    return path.read_bytes()


def indicators(root: Path, source: str) -> list[str]:
    """Indicators of ``source`` with at least one stored payload."""
    manifest = root / "manifest.jsonl"
    if not manifest.exists():
        return []
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a truncated final line, as in macrokit.snapshot
        if record.get("source") == source and record.get("path"):
            seen.add(record["indicator"])
    return sorted(seen)
