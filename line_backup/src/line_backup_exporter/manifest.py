from __future__ import annotations

import json
import plistlib
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

from .models import FileEntry
from .utils import get_logger, write_csv

logger = get_logger(__name__)

# Keywords for LINE-related domain / relativePath filtering
_LINE_KEYWORDS = ("LINE", "Line", "line", "jp.naver.line", "naver")

# Priority keywords for scoring (higher = more interesting)
_PRIORITY_KEYWORDS = (
    "Line.sqlite",
    "line.sqlite",
    "Talk.sqlite",
    "chat",
    "message",
    "sticker",
    "image",
    "audio",
    "video",
    "Application Support",
    "Documents",
    "Library",
)


def check_encrypted(backup_dir: Path) -> bool:
    """Return True if the backup is encrypted. Raises RuntimeError if so."""
    plist_path = backup_dir / "Manifest.plist"
    if not plist_path.exists():
        return False
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        return bool(data.get("IsEncrypted", False))
    except Exception as e:
        logger.warning("Could not read Manifest.plist: %s", e)
        return False


def open_manifest(backup_dir: Path) -> sqlite3.Connection:
    db_path = backup_dir / "Manifest.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Manifest.db not found in {backup_dir}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def iter_line_files(conn: sqlite3.Connection) -> Iterator[FileEntry]:
    """Yield FileEntry rows matching LINE-related domain or relativePath."""
    like_clauses = " OR ".join(
        ["domain LIKE ?"] * len(_LINE_KEYWORDS) + ["relativePath LIKE ?"] * len(_LINE_KEYWORDS)
    )
    params = [f"%{kw}%" for kw in _LINE_KEYWORDS] * 2

    sql = f"""
        SELECT fileID, domain, relativePath, flags, COALESCE(LENGTH(file), 0) AS file_length
        FROM Files
        WHERE {like_clauses}
    """
    with closing(conn.cursor()) as cur:
        cur.execute(sql, params)
        for row in cur:
            yield FileEntry(
                file_id=row["fileID"] or "",
                domain=row["domain"] or "",
                relative_path=row["relativePath"] or "",
                flags=row["flags"] or 0,
                file_length=row["file_length"] or 0,
            )


def _priority_score(entry: FileEntry) -> int:
    score = 0
    combined = entry.domain + "/" + entry.relative_path
    for i, kw in enumerate(_PRIORITY_KEYWORDS):
        if kw.lower() in combined.lower():
            # Earlier keywords (more specific) get higher weight
            score += len(_PRIORITY_KEYWORDS) - i
    return score


def prioritize(entries: list[FileEntry]) -> list[FileEntry]:
    return sorted(entries, key=_priority_score, reverse=True)


def resolve_blob_path(backup_dir: Path, file_id: str) -> Path:
    """Resolve fileID to its actual path inside the backup directory."""
    if len(file_id) < 2:
        raise ValueError(f"Invalid fileID: {file_id!r}")
    return backup_dir / file_id[:2] / file_id


def scan_line_files(
    backup_dir: Path,
    out_dir: Path,
) -> list[FileEntry]:
    """Read Manifest.db, extract LINE files, write CSV+JSON, return prioritized list."""
    if check_encrypted(backup_dir):
        raise RuntimeError(
            "This backup is encrypted. Encrypted backups are not supported in this version.\n"
            "Please disable backup encryption in iTunes/Finder and create a new backup."
        )

    with closing(open_manifest(backup_dir)) as conn:
        entries = list(iter_line_files(conn))

    if not entries:
        logger.warning("No LINE-related files found in Manifest.db.")
        return []

    ranked = prioritize(entries)

    # Write CSV
    csv_path = out_dir / "manifest_line_files.csv"
    headers = ["file_id", "domain", "relative_path", "flags", "file_length"]
    rows = [(e.file_id, e.domain, e.relative_path, e.flags, e.file_length) for e in ranked]
    write_csv(csv_path, rows, headers)
    logger.info("Wrote %d entries to %s", len(rows), csv_path)

    # Write JSON
    json_path = out_dir / "manifest_line_files.json"
    json_data = [
        {
            "file_id": e.file_id,
            "domain": e.domain,
            "relative_path": e.relative_path,
            "flags": e.flags,
            "file_length": e.file_length,
        }
        for e in ranked
    ]
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    logger.info("Wrote JSON to %s", json_path)

    return ranked
