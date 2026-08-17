"""Immutable raw snapshots, deduplicated by content hash.

This layer is the entire reason Japanese vintages can exist at all. e-Stat and
the ministry CSVs publish by overwriting, so the only record of "what the value
was before the revision" is a copy we took at the time. Nothing here is ever
rewritten.

Deduplication is not just a disk optimisation. Because a stored file appears
only when the bytes changed, the set of stored dates IS the set of revision
dates -- RevisionShock detection falls out of the storage layer for free.

Every stored file's name carries the hash of its own bytes, so a path's
content is determined by its name. That is what makes the ``exists()`` guard
in ``save_snapshot`` a genuine no-op safety net rather than a data-losing
one: a file already at a content-addressed path necessarily holds that same
content, even when two different revisions land on the same calendar day.

Layout::

    {root}/{source}/{indicator}/{ingested_date}/{sha256[:12]}-{filename}
    {root}/manifest.jsonl
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SnapshotResult:
    path: Path | None  # None when the content was unchanged and not stored
    sha256: str
    changed: bool
    size: int


def manifest_path(root: Path) -> Path:
    return root / "manifest.jsonl"


def last_sha(root: Path, source: str, indicator: str) -> str | None:
    """SHA-256 of the most recent *stored* payload, or None if never stored."""
    manifest = manifest_path(root)
    if not manifest.exists():
        return None
    newest: str | None = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # The manifest is append-only; an interrupted write can leave a
            # truncated final line. Only the last line can ever be broken
            # this way, so skipping it is both safe and complete.
            continue
        if record["source"] == source and record["indicator"] == indicator:
            newest = record["sha256"]
    return newest


def save_snapshot(
    root: Path,
    source: str,
    indicator: str,
    content: bytes,
    *,
    ingested_at: datetime,
    url: str,
    http_status: int,
    filename: str = "payload",
) -> SnapshotResult:
    """Store ``content`` unless it matches the last stored payload.

    Every attempt is appended to the manifest, changed or not, so the fetch
    history stays complete even when nothing was written.
    """
    digest = hashlib.sha256(content).hexdigest()
    changed = digest != last_sha(root, source, indicator)

    target: Path | None = None
    if changed:
        directory = root / source / indicator / ingested_at.date().isoformat()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{digest[:12]}-{filename}"
        if not target.exists():
            target.write_bytes(content)

    root.mkdir(parents=True, exist_ok=True)
    record = {
        "ingested_at": ingested_at.isoformat(),
        "source": source,
        "indicator": indicator,
        "url": url,
        "sha256": digest,
        "bytes": len(content),
        "changed": changed,
        "http_status": http_status,
        "path": str(target.relative_to(root)) if target else None,
    }
    with manifest_path(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return SnapshotResult(path=target, sha256=digest, changed=changed, size=len(content))
