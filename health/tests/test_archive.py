import errno
import os
from dataclasses import replace

import pytest
from health.archive import Archive, ArchiveError


def test_exact_bytes_sources_and_old_versions_survive(tmp_path):
    archive = Archive(tmp_path / "archive")
    original = b'{"points":[{"source":"a","ts":1},{"source":"b","ts":1}],"x":1.00}\n'
    first = archive.put(original)
    second = archive.put(b'{"points":[]}')
    assert archive.read(first) == original
    assert archive.read(second) == b'{"points":[]}'
    assert first != second
    assert archive.put(original) == first
    assert len(list((tmp_path / "archive/objects").glob("*.json.gz"))) == 2


def test_created_objects_and_directories_are_private(tmp_path):
    archive = Archive(tmp_path / "archive")
    ref = archive.put(b"{}")
    assert (tmp_path / "archive" / ref.relative_path).stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "archive/objects").stat().st_mode & 0o777 == 0o700


def test_failed_write_never_publishes_or_removes_previous_body(tmp_path, monkeypatch):
    archive = Archive(tmp_path / "archive")
    old = archive.put(b'{"value":1}')
    with monkeypatch.context() as patch:

        def full(*args):
            raise OSError(errno.ENOSPC, "disk full")

        patch.setattr(os, "write", full)
        with pytest.raises(OSError) as error:
            archive.put(b'{"value":2}')
        assert error.value.errno == errno.ENOSPC
    assert archive.read(old) == b'{"value":1}'
    assert len(list((tmp_path / "archive/objects").iterdir())) == 1


def test_failed_fsync_never_publishes_new_object(tmp_path, monkeypatch):
    archive = Archive(tmp_path / "archive")
    old = archive.put(b"{}")
    with monkeypatch.context() as patch:

        def fail(*args):
            raise OSError(errno.EIO, "fsync failed")

        patch.setattr(os, "fsync", fail)
        with pytest.raises(OSError):
            archive.put(b'{"changed":true}')
    assert archive.read(old) == b"{}"
    assert len(list((tmp_path / "archive/objects").iterdir())) == 1


def test_corrupted_object_is_detected_without_overwriting_it(tmp_path):
    archive = Archive(tmp_path / "archive")
    ref = archive.put(b'{"keep":true}')
    path = tmp_path / "archive" / ref.relative_path
    path.write_bytes(b"corrupt")
    with pytest.raises(ArchiveError):
        archive.read(ref)
    with pytest.raises(ArchiveError):
        archive.put(b'{"keep":true}')
    assert path.read_bytes() == b"corrupt"


def test_read_cannot_escape_object_store(tmp_path):
    archive = Archive(tmp_path / "archive")
    ref = archive.put(b"{}")
    with pytest.raises(ArchiveError):
        archive.read(replace(ref, relative_path="../../tokens.json"))


def test_retry_after_directory_fsync_failure_reestablishes_durability(tmp_path, monkeypatch):
    from health import archive as module

    archive = Archive(tmp_path / "archive")
    real = module.fsync_directory
    attempts = []

    def fail_once(path):
        attempts.append(path)
        if len(attempts) == 1:
            raise OSError(errno.EIO, "directory sync failed")
        real(path)

    monkeypatch.setattr(module, "fsync_directory", fail_once)
    with pytest.raises(OSError):
        archive.put(b"{}")
    ref = archive.put(b"{}")
    assert archive.read(ref) == b"{}"
    assert len(attempts) == 2
