"""Where raw snapshots live, and how they are fetched and read back (design §4)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from macrokit.snapshot import SnapshotResult, latest_payload, save_snapshot

RAW_ROOT = Path(
    os.environ.get("SECTOR_LEADLAG_RAW", "/home/kazumasa/projects/_data/sector_leadlag_lab/raw")
)
USER_AGENT = "Mozilla/5.0 (compatible; macrokit research)"


class FetchError(RuntimeError):
    """A remote file could not be fetched."""


def fetch(url: str, *, timeout: float = 120.0) -> bytes:
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
            f"no stored snapshot for {source}/{indicator} under {root}; run `sector-leadlag snapshot`"
        )
    return path.read_bytes()


def manifest_records(root: Path) -> dict[str, dict]:
    """The newest stored record of every indicator, keyed ``source/indicator``."""
    manifest = root / "manifest.jsonl"
    records: dict[str, dict] = {}
    if not manifest.exists():
        return records
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a blank or truncated line, as in macrokit.snapshot
        if record.get("path"):
            records[f"{record['source']}/{record['indicator']}"] = {
                name: record.get(name) for name in ("sha256", "ingested_at", "url", "path")
            }
    return dict(sorted(records.items()))


def indicators(root: Path, source: str) -> list[str]:
    """Indicators of ``source`` with at least one stored payload."""
    prefix = f"{source}/"
    return [key[len(prefix) :] for key in manifest_records(root) if key.startswith(prefix)]
