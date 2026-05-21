from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BackupInfo:
    backup_id: str
    path: Path
    updated_at: str
    has_manifest_db: bool
    has_manifest_plist: bool
    likely_encrypted: bool


@dataclass(frozen=True)
class FileEntry:
    file_id: str
    domain: str
    relative_path: str
    flags: int
    file_length: int


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    is_pk: bool


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    row_count: int | None = None
    sample_rows: list[tuple] = field(default_factory=list)


@dataclass
class TableCandidates:
    messages: list[str] = field(default_factory=list)
    rooms: list[str] = field(default_factory=list)
    contacts: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
