"""Share exact immutable artifact files without changing their receipt-bound bytes.

Run on a quiescent artifact tree whose writer never updates published files
in place. Audit is the default. This does not compress/rewrite any payload,
change numerical checks, or reclaim Windows VHDX allocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import time
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path

LEAVES = {"metadata.json": "metadata_sha256", "arrays.npz": "arrays_sha256"}
IDENTITY_FIELDS = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_uid", "st_gid", "st_mode")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def safe_path(path):
    """Reject symlinks in both the target and all existing ancestors."""
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        if part.is_symlink():
            raise ValueError(f"symlink rejected: {part}")
    return path


def snapshot(path):
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"not a regular file: {path}")
    return value


def stable(before, after):
    return all(getattr(before, name) == getattr(after, name) for name in IDENTITY_FIELDS)


def sync_directory(path):
    descriptor = os.open(safe_path(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class BudgetedReader:
    """Charge ZIP-directory reads to the same budget as byte verification."""

    def __init__(self, handle, engine):
        self.handle, self.engine = handle, engine

    def read(self, count=-1):
        if count < 0:
            count = os.fstat(self.handle.fileno()).st_size - self.handle.tell()
        return self.engine.read(self.handle, count)

    def seek(self, *args):
        return self.handle.seek(*args)

    def tell(self):
        return self.handle.tell()

    def seekable(self):
        return True


class LimitReachedError(Exception):
    """A resource limit stops administrative work, never certifies a dataset."""


class RollbackFailedError(RuntimeError):
    """Keep the original backup when its restoration fails."""


class CommittedCleanupError(RuntimeError):
    """Verified sharing happened, but final cleanup durability is unconfirmed."""


class SharingRun:
    """One bounded audit/apply run; logs live outside the artifact inventory."""

    def __init__(
        self,
        root,
        journal,
        *,
        apply=False,
        min_age_seconds=3600,
        min_bytes=1048576,
        max_read_gib=128,
        max_seconds=900,
        max_links=30000,
    ):
        values = (min_age_seconds, min_bytes, max_read_gib, max_seconds, max_links)
        if not all(math.isfinite(v) for v in values) or min(values) < 0 or min(values[2:]) <= 0:
            raise ValueError("invalid age/size/read/time/link limits")
        self.root, self.journal = safe_path(root), safe_path(journal)
        if self.journal.is_relative_to(self.root):
            raise ValueError("journal must be outside the artifact root")
        self.apply, self.min_bytes = apply, min_bytes
        self.cutoff_ns = time.time_ns() - int(min_age_seconds * 1e9)
        self.max_read_bytes = int(max_read_gib * 2**30)
        self.max_seconds, self.max_links = max_seconds, max_links
        self.start = time.monotonic()
        self.read_bytes = 0
        self.log = None
        self.staging = self.journal.parent / ("sharing-staging-" + uuid.uuid4().hex)
        self.report = {
            "root": str(self.root),
            "apply": apply,
            "candidate_files": 0,
            "candidate_allocated_bytes": 0,
            "linked": 0,
            "replacement_attempts": 0,
            "committed_unconfirmed": 0,
            "rejected": 0,
            "released_allocated_bytes": 0,
            "termination": "completed",
        }
        self.last_progress = self.start

    def check(self):
        if time.monotonic() - self.start >= self.max_seconds:
            raise LimitReachedError("max_seconds")

    def prepare(self):
        if not self.root.is_dir():
            raise ValueError("artifact root missing")
        if not self.journal.parent.is_dir():
            raise ValueError("journal parent must already exist")
        if self.journal.parent.stat().st_dev != self.root.stat().st_dev:
            raise ValueError("journal/staging must be on the artifact filesystem")
        self.log = self.journal.open("x", encoding="utf-8")
        self.staging.mkdir()
        sync_directory(self.journal.parent)
        self.event("start", root=str(self.root), apply=self.apply)

    def event(self, event, **data):
        self.log.write(canonical({"event": event, **data}).decode() + "\n")
        self.log.flush()
        os.fsync(self.log.fileno())

    def read(self, handle, count):
        self.check()
        if self.read_bytes + count > self.max_read_bytes:
            raise LimitReachedError("max_read_bytes")
        data = handle.read(count)
        self.read_bytes += len(data)
        return data

    def receipt(self, directory):
        path = safe_path(directory / "receipt.json")
        before = snapshot(path)
        if before.st_size > 65536:
            raise ValueError("receipt exceeds 64 KiB")
        with path.open("rb") as handle:
            data = self.read(handle, before.st_size)
        if not stable(before, snapshot(path)) or before.st_mtime_ns > self.cutoff_ns:
            raise ValueError("receipt changed or is recent")
        receipt = json.loads(data)
        if not isinstance(receipt, dict):
            raise ValueError("invalid receipt")
        identity = {k: v for k, v in receipt.items() if k != "artifact_sha256"}
        if (
            data != canonical(receipt)
            or receipt.get("schema") != "rb-f04-array-receipt-v1"
            or receipt.get("artifact_sha256") != hashlib.sha256(canonical(identity)).hexdigest()
        ):
            raise ValueError("receipt schema/canonical/hash mismatch")
        for key in LEAVES.values():
            if not isinstance(receipt.get(key), str) or not re.fullmatch(
                r"[0-9a-f]{64}", receipt[key]
            ):
                raise ValueError("invalid receipt digest")
        return receipt, before, hashlib.sha256(data).hexdigest()

    def inspect(self, path):
        path = safe_path(path)
        if not path.is_relative_to(self.root) or path.name not in LEAVES:
            raise ValueError("file outside approved artifact scope")
        info = snapshot(path)
        if info.st_mtime_ns > self.cutoff_ns:
            raise ValueError("recent artifact")
        receipt, receipt_stat, receipt_sha = self.receipt(path.parent)
        for name in LEAVES:
            sibling = snapshot(safe_path(path.with_name(name)))
            if sibling.st_mtime_ns > self.cutoff_ns:
                raise ValueError("recent sibling")
        return {
            "path": path,
            "stat": info,
            "sha": receipt[LEAVES[path.name]],
            "receipt": receipt,
            "receipt_stat": receipt_stat,
            "receipt_sha": receipt_sha,
        }

    def digest(self, path):
        path = safe_path(path)
        before = snapshot(path)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            if not stable(before, os.fstat(handle.fileno())):
                raise ValueError("file changed before hashing")
            remaining = before.st_size
            while remaining:
                data = self.read(handle, min(1048576, remaining))
                if not data:
                    raise ValueError("file truncated while hashing")
                digest.update(data)
                remaining -= len(data)
            if not stable(before, os.fstat(handle.fileno())):
                raise ValueError("file changed while hashing")
        if not stable(before, snapshot(path)):
            raise ValueError("path changed while hashing")
        return digest.hexdigest()

    def verify(self, record):
        current = self.inspect(record["path"])
        if (
            not stable(record["stat"], current["stat"])
            or not stable(record["receipt_stat"], current["receipt_stat"])
            or record["receipt_sha"] != current["receipt_sha"]
        ):
            raise ValueError("artifact identity/receipt changed")
        for name, key in LEAVES.items():
            if self.digest(record["path"].with_name(name)) != record["receipt"][key]:
                raise ValueError("artifact bytes disagree with receipt")
        if record["path"].name == "arrays.npz":
            # Read only the central directory; do not decode or allocate arrays.
            with record["path"].open("rb") as handle:
                with zipfile.ZipFile(BudgetedReader(handle, self)) as archive:
                    expanded = sum(item.file_size for item in archive.infolist())
            if expanded != record["receipt"].get("uncompressed_bytes") or expanded > 256 * 2**20:
                raise ValueError("NPZ expanded size disagrees with receipt/limit")

    def verify_replacement(self, source, target):
        new = snapshot(target["path"])
        if not stable(source["stat"], new) or self.digest(target["path"]) != target["sha"]:
            raise ValueError("replacement inode/bytes mismatch")
        receipt, info, sha = self.receipt(target["path"].parent)
        if (
            receipt != target["receipt"]
            or sha != target["receipt_sha"]
            or not stable(info, target["receipt_stat"])
        ):
            raise ValueError("target receipt changed")

    def link(self, source, target):
        self.verify(source)
        self.verify(target)
        for name in ("st_dev", "st_uid", "st_gid", "st_mode", "st_size"):
            if getattr(source["stat"], name) != getattr(target["stat"], name):
                raise ValueError("filesystem/owner/permissions/size mismatch")
        if source["sha"] != target["sha"]:
            raise ValueError("different bytes")
        self.check()
        if self.report["replacement_attempts"] >= self.max_links:
            raise LimitReachedError("max_links")
        staged, backup = self.staging / uuid.uuid4().hex, self.staging / uuid.uuid4().hex
        rollback_staged = self.staging / uuid.uuid4().hex
        values = {
            "source": str(source["path"].relative_to(self.root)),
            "target": str(target["path"].relative_to(self.root)),
            "sha256": target["sha"],
            "receipt_sha256": target["receipt_sha"],
            "original_mtime_ns": target["stat"].st_mtime_ns,
        }
        self.event("intent", **values, backup=str(backup))
        replaced = False
        retain_backup = False
        try:
            os.link(target["path"], backup, follow_symlinks=False)
            os.link(source["path"], staged, follow_symlinks=False)
            sync_directory(self.staging)
            for record, temporary in ((source, staged), (target, backup)):
                if not stable(record["stat"], snapshot(temporary)) or not stable(
                    record["stat"], snapshot(record["path"])
                ):
                    raise ValueError("file changed before replacement")
            self.check()
            self.report["replacement_attempts"] += 1
            # A signal may arrive after rename succeeds but before Python resumes.
            # Restoring an unmodified target after a failed attempt is harmless.
            replaced = True
            os.replace(staged, target["path"])
            sync_directory(target["path"].parent)
            sync_directory(self.staging)
            self.verify_replacement(source, target)
            released = backup.stat().st_blocks * 512 if backup.stat().st_nlink == 1 else 0
            self.event("verified", **values, released_allocated_bytes=released)
            backup.unlink()
            sync_directory(self.staging)
            self.report["released_allocated_bytes"] += released
            self.report["linked"] += 1
        except BaseException as failure:
            if replaced and backup.exists():
                try:
                    os.link(backup, rollback_staged, follow_symlinks=False)
                    sync_directory(self.staging)
                    os.replace(rollback_staged, target["path"])
                    sync_directory(target["path"].parent)
                    sync_directory(self.staging)
                    self.event("rolled_back", **values)
                except BaseException as error:
                    retain_backup = True
                    raise RollbackFailedError(
                        f"rollback/durability unconfirmed; original backup retained at {backup}"
                    ) from error
            elif replaced:
                self.report["committed_unconfirmed"] += 1
                raise CommittedCleanupError(
                    f"replacement committed; cleanup durability unconfirmed: {target['path']}"
                ) from failure
            raise
        finally:
            pending = sys.exception()
            try:
                for temporary in (staged, rollback_staged, backup):
                    if temporary.exists() and not (retain_backup and temporary == backup):
                        temporary.unlink()
                sync_directory(self.staging)
            except BaseException as error:
                if isinstance(pending, (RollbackFailedError, CommittedCleanupError)):
                    pending.add_note(f"staging cleanup/durability failed: {error!r}")
                else:
                    raise RollbackFailedError(
                        f"staging cleanup/durability failed; inspect {self.staging}"
                    ) from error

    def scan(self):
        groups = defaultdict(list)
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            self.check()
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            if "receipt.json" not in files:
                continue
            for name in LEAVES:
                path = Path(directory) / name
                try:
                    record = self.inspect(path)
                    info = record["stat"]
                    if info.st_size < self.min_bytes:
                        continue
                    key = (
                        name,
                        record["sha"],
                        info.st_size,
                        info.st_dev,
                        info.st_uid,
                        info.st_gid,
                        info.st_mode,
                    )
                    groups[key].append(record)
                except (OSError, ValueError, TypeError) as error:
                    self.report["rejected"] += 1
                    self.event("rejected", path=str(path.relative_to(self.root)), reason=str(error))
        return groups

    def close(self):
        self.report.update(
            read_bytes=self.read_bytes, elapsed_seconds=time.monotonic() - self.start
        )
        if self.log is not None:
            self.event("finished", **self.report)
            self.log.close()
            self.log = None
        if self.staging.exists() and not any(self.staging.iterdir()):
            self.staging.rmdir()

    def run(self):
        self.prepare()
        try:
            for records in self.scan().values():
                identities = {}
                for record in records:
                    identities.setdefault(record["stat"].st_ino, record)
                if len(identities) < 2:
                    continue
                source = max(identities.values(), key=lambda r: r["stat"].st_nlink)
                self.report["candidate_files"] += len(identities) - 1
                self.report["candidate_allocated_bytes"] += sum(
                    r["stat"].st_blocks * 512 for r in identities.values() if r is not source
                )
                if not self.apply:
                    continue
                # Include all path aliases: an inode is released only when its
                # last original link disappears, never just its first pathname.
                for target in records:
                    current = snapshot(target["path"])
                    if current.st_ino == source["stat"].st_ino:
                        continue
                    target = dict(target, stat=current)
                    try:
                        self.link(source, target)
                    except (OSError, ValueError, zipfile.BadZipFile) as error:
                        self.report["rejected"] += 1
                        self.event(
                            "rejected",
                            path=str(target["path"].relative_to(self.root)),
                            reason=str(error),
                        )
                    if time.monotonic() - self.last_progress >= 20:
                        print(json.dumps({"progress": self.report}), flush=True)
                        self.last_progress = time.monotonic()
        except LimitReachedError as error:
            self.report.update(termination="administrative_limit", limit=str(error))
        except BaseException as error:
            termination = (
                "interrupted"
                if isinstance(error, (KeyboardInterrupt, SystemExit))
                else "tool_exception"
            )
            self.report.update(termination=termination, error=repr(error))
            raise
        finally:
            self.close()
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-age-seconds", type=float, default=3600)
    parser.add_argument("--min-bytes", type=int, default=1048576)
    parser.add_argument("--max-read-gib", type=float, default=128)
    parser.add_argument("--max-seconds", type=float, default=900)
    parser.add_argument("--max-links", type=int, default=30000)
    args = parser.parse_args()
    report = SharingRun(**vars(args)).run()
    print(json.dumps(report), flush=True)
    return 0 if report["termination"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
