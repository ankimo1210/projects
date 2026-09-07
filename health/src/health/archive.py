"""Lossless content-addressed response objects, independent of typed parsing."""

from __future__ import annotations

import gzip
import hashlib
import os
import re
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from health.privacy import ensure_private_dir


class ArchiveError(ValueError):
    """A stored object or its reference cannot be trusted."""


@dataclass(frozen=True)
class ObjectRef:
    sha256: str
    relative_path: str
    byte_count: int


def fsync_directory(path: Path) -> None:
    handle = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def atomic_private_write(path: Path, body: bytes) -> None:
    """Publish bytes only after the private temporary file is durable."""
    ensure_private_dir(path.parent)
    handle, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    temp = Path(name)
    try:
        try:
            remaining = memoryview(body)
            while remaining:
                written = os.write(handle, remaining)
                if written <= 0:
                    raise OSError("short archive write")
                remaining = remaining[written:]
            os.fsync(handle)
        finally:
            os.close(handle)
        os.replace(temp, path)
        fsync_directory(path.parent)
    finally:
        temp.unlink(missing_ok=True)


class Archive:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        ensure_private_dir(self.root)
        ensure_private_dir(self.root / "objects")

    def put(self, body: bytes) -> ObjectRef:
        if not isinstance(body, bytes):
            raise TypeError("archive accepts response bytes only")
        digest = hashlib.sha256(body).hexdigest()
        ref = ObjectRef(digest, f"objects/{digest}.json.gz", len(body))
        path = self.root / ref.relative_path
        if path.exists() or path.is_symlink():
            self.read(ref)
            handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(handle)
            finally:
                os.close(handle)
            fsync_directory(path.parent)
            return ref
        # One CLI writer owns the archive. Different bodies always have distinct
        # names, so later upstream updates cannot overwrite an observed version.
        atomic_private_write(path, gzip.compress(body, mtime=0))
        return ref

    def read(self, ref: ObjectRef) -> bytes:
        if not re.fullmatch(r"[0-9a-f]{64}", ref.sha256):
            raise ArchiveError("invalid object digest")
        if ref.relative_path != f"objects/{ref.sha256}.json.gz":
            raise ArchiveError("invalid object path")
        path = self.root / ref.relative_path
        if path.is_symlink():
            raise ArchiveError("object must not be a symbolic link")
        try:
            body = gzip.decompress(path.read_bytes())
        except (OSError, EOFError, zlib.error) as exc:
            raise ArchiveError("archive object is unreadable or corrupt") from exc
        if len(body) != ref.byte_count or hashlib.sha256(body).hexdigest() != ref.sha256:
            raise ArchiveError("archive object checksum mismatch")
        return body
