"""Backups preserve an existing database before application migrations run."""

import os
import stat
from pathlib import Path

import duckdb
import pytest
from health.backup import backup_database


def legacy_database(path):
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE legacy_only (value VARCHAR)")
    con.execute("INSERT INTO legacy_only VALUES ('synthetic original')")
    con.close()


def test_backup_is_readable_private_and_streamed(tmp_path, monkeypatch):
    db = tmp_path / "legacy.duckdb"
    legacy_database(db)

    def no_whole_file_read(*args, **kwargs):
        raise AssertionError("backup must stream the database")

    monkeypatch.setattr(Path, "read_bytes", no_whole_file_read)
    backup = backup_database(db)
    assert backup != db
    con = duckdb.connect(str(backup), read_only=True)
    assert con.execute("SHOW TABLES").fetchall() == [("legacy_only",)]
    assert con.execute("SELECT * FROM legacy_only").fetchall() == [("synthetic original",)]
    con.close()
    if os.name == "posix":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert stat.S_IMODE(backup.parent.stat().st_mode) == 0o700
    second = backup_database(db)
    assert second != backup and backup.exists()


def test_missing_database_is_not_created_by_backup(tmp_path):
    db = tmp_path / "missing.duckdb"
    assert backup_database(db) is None
    assert not db.exists()
    assert not (tmp_path / "backups").exists()


def test_backup_failure_keeps_source_and_previous_backups(tmp_path, monkeypatch):
    db = tmp_path / "legacy.duckdb"
    legacy_database(db)
    previous = backup_database(db)

    def fail(*args):
        raise OSError("synthetic disk full")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="synthetic disk full"):
        backup_database(db)
    assert list(previous.parent.iterdir()) == [previous]
    con = duckdb.connect(str(db))
    assert con.execute("SELECT * FROM legacy_only").fetchall() == [("synthetic original",)]
    con.close()


def test_checkpoint_connection_closes_before_copy(tmp_path, monkeypatch):
    import health.backup as module

    db = tmp_path / "legacy.duckdb"
    legacy_database(db)
    events = []
    real_connect = duckdb.connect
    real_copy = module.shutil.copyfileobj

    class CheckpointConnection:
        def __init__(self, *args, **kwargs):
            self.con = real_connect(*args, **kwargs)

        def execute(self, sql):
            assert sql == "CHECKPOINT"
            events.append("checkpoint")
            return self.con.execute(sql)

        def close(self):
            self.con.close()
            events.append("closed")

    def copy(source, target, length):
        assert events == ["checkpoint", "closed"]
        assert 0 < length <= 1024 * 1024
        events.append("copy")
        return real_copy(source, target, length)

    monkeypatch.setattr(module.duckdb, "connect", CheckpointConnection)
    monkeypatch.setattr(module.shutil, "copyfileobj", copy)
    backup_database(db)
    assert events == ["checkpoint", "closed", "copy"]


def test_symlink_database_is_rejected(tmp_path):
    original = tmp_path / "original.duckdb"
    legacy_database(original)
    link = tmp_path / "link.duckdb"
    link.symlink_to(original)
    with pytest.raises(ValueError):
        backup_database(link)
    assert not (tmp_path / "backups").exists()
