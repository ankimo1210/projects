"""Stream a durable, private database backup before opening the application Store."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from health.archive import fsync_directory
from health.privacy import ensure_private_dir


def backup_database(db_path: Path) -> Path | None:
    """Checkpoint without application DDL, close, then copy in bounded chunks.

    The application must keep its writer stopped until this returns. A locked
    database or incomplete backup is an error: callers must not open Store or
    migrate after it. Existing backups are immutable and never pruned here.
    """
    db_path = Path(db_path)
    if any(path.is_symlink() for path in (db_path, *db_path.parents)):
        raise ValueError("database path must not traverse symlinks")
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CHECKPOINT")
    finally:
        con.close()
    directory = db_path.parent / "backups"
    if directory.is_symlink():
        raise ValueError("backup directory must not be a symlink")
    ensure_private_dir(directory)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"{db_path.stem}-{stamp}-{uuid4().hex}.duckdb"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".backup-", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, db_path.open("rb") as source:
            shutil.copyfileobj(source, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        fsync_directory(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    return target
