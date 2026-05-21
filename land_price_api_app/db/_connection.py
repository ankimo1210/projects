"""db/_connection.py — DuckDB 接続管理と WAL 自動回復。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb

from config import DUCKDB_PATH, get_logger

logger = get_logger(__name__)


def _wal_path_for_db(db_path: Path) -> Path:
    return db_path.parent / f"{db_path.name}.wal"


def _is_wal_replay_error(exc: Exception) -> bool:
    return "Failure while replaying WAL file" in str(exc)


def _quarantine_corrupt_wal(db_path: Path) -> Optional[Path]:
    wal_path = _wal_path_for_db(db_path)
    if not wal_path.exists():
        return None
    backup_dir = db_path.parent / "recovery_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{db_path.name}.wal.corrupt_{timestamp}"
    wal_path.replace(target)
    return target


def get_connection(
    db_path: Optional[Path] = None,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """DuckDB 接続を返す。書き込みロック取得失敗時は read_only にフォールバック。"""
    path = db_path or DUCKDB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = duckdb.connect(str(path), read_only=read_only)
    except duckdb.IOException:
        logger.warning("書き込みロック取得失敗。read_only モードで接続します: %s", path)
        conn = duckdb.connect(str(path), read_only=True)
    except Exception as exc:
        if not _is_wal_replay_error(exc):
            raise
        recovered_wal = _quarantine_corrupt_wal(path)
        if recovered_wal is None:
            raise
        logger.error(
            "WAL 再生に失敗したため退避しました: %s -> %s",
            _wal_path_for_db(path),
            recovered_wal,
        )
        conn = duckdb.connect(str(path), read_only=read_only)
    logger.debug("DuckDB 接続: %s (read_only=%s)", path, read_only)
    return conn
