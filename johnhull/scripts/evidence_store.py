"""Immutable content-addressed store for johnhull evidence (D1, ADR 0004).

Blobs live at ``<root>/sha256/<first two hex>/<sha256>`` and are never
overwritten. A store root is only usable when it already exists and carries
the marker written by ``init``; nothing here creates a store implicitly, so an
unmounted drive or an unset variable is an explicit error instead of a fresh
empty folder. Public manifests refer to blobs as ``artifact:sha256:<digest>``
and hold project-relative paths only.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

MARKER_NAME = ".projects-artifact-store.json"
LAYOUT = "sha256/<2>/<sha256>"
ROLES = ("primary", "mirror")
REF_PREFIX = "artifact:sha256:"
MANIFEST_KIND = "johnhull-evidence-manifest"
ENTRY_KEYS = {"path", "ref", "bytes", "mime"}
MIME_TYPES = {
    ".png": "image/png",
    ".json": "application/json",
    ".html": "text/html",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".svg": "image/svg+xml",
}
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_REF_RE = re.compile(r"artifact:sha256:([0-9a-f]{64})")


class StoreError(Exception):
    """A store, manifest or restore operation cannot be completed safely."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_ref(digest: str) -> str:
    if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
        raise StoreError(f"reference: invalid sha256 digest {digest!r}")
    return REF_PREFIX + digest


def parse_ref(ref: object) -> str:
    match = _REF_RE.fullmatch(ref) if isinstance(ref, str) else None
    if match is None:
        raise StoreError(f"reference: expected artifact:sha256:<64 lowercase hex>, got {ref!r}")
    return match.group(1)


def validate_relative_path(value: object) -> PurePosixPath:
    """Return a safe project-relative POSIX path or raise ``StoreError``."""
    if not isinstance(value, str) or not value:
        raise StoreError(f"path must be a non-empty relative path: {value!r}")
    if "\0" in value or "\\" in value:
        raise StoreError(f"path must use forward slashes only: {value!r}")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise StoreError(f"path must be relative, not absolute or drive-qualified: {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise StoreError(f"path must not contain empty, '.' or '..' components: {value!r}")
    return PurePosixPath(value)


def mime_for(path: str) -> str:
    return MIME_TYPES.get(PurePosixPath(path).suffix.lower(), "application/octet-stream")


def manifest_entry(path: str, data: bytes) -> dict:
    validate_relative_path(path)
    return {
        "path": path,
        "ref": make_ref(_sha256(data)),
        "bytes": len(data),
        "mime": mime_for(path),
    }


def validate_entries(entries: object, label: str = "entries") -> list[dict]:
    """Validate manifest entries: known fields, safe paths, consistent digests."""
    if not isinstance(entries, list):
        raise StoreError(f"{label}: expected a list")
    seen_paths: set[str] = set()
    by_digest: dict[str, tuple[int, str]] = {}
    for index, entry in enumerate(entries):
        where = f"{label}[{index}]"
        if not isinstance(entry, dict):
            raise StoreError(f"{where}: expected an object")
        unknown = sorted(set(entry) - ENTRY_KEYS)
        missing = sorted(ENTRY_KEYS - set(entry))
        if unknown:
            raise StoreError(f"{where}: unknown fields {unknown}")
        if missing:
            raise StoreError(f"{where}: missing fields {missing}")
        validate_relative_path(entry["path"])
        digest = parse_ref(entry["ref"])
        size = entry["bytes"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise StoreError(f"{where}.bytes: expected a non-negative integer")
        if not isinstance(entry["mime"], str) or not entry["mime"]:
            raise StoreError(f"{where}.mime: expected a non-empty string")
        if entry["path"] in seen_paths:
            raise StoreError(f"{where}: duplicate path {entry['path']!r}")
        seen_paths.add(entry["path"])
        facts = (size, entry["mime"])
        if by_digest.setdefault(digest, facts) != facts:
            raise StoreError(f"{where}: conflicting size or MIME for {digest}")
    return entries


def load_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict):
        raise StoreError("manifest: expected an object")
    unknown = sorted(set(manifest) - {"schema_version", "kind", "entries"})
    if unknown:
        raise StoreError(f"manifest: unknown fields {unknown}")
    if manifest.get("schema_version") != 1:
        raise StoreError("manifest.schema_version: expected 1")
    if manifest.get("kind") != MANIFEST_KIND:
        raise StoreError(f"manifest.kind: expected {MANIFEST_KIND!r}")
    validate_entries(manifest.get("entries"), "manifest.entries")
    return manifest


class Store:
    """An initialized store root. Construct with ``Store.open`` or ``init_store``."""

    def __init__(self, root: Path, role: str):
        self.root = root
        self.role = role

    def __repr__(self) -> str:
        return f"Store(role={self.role!r})"

    @classmethod
    def open(cls, root: Path | str, role: str | None = None) -> Store:
        root = Path(root)
        if not root.is_dir():
            raise StoreError(f"store root does not exist or is not mounted: {root}")
        marker = root / MARKER_NAME
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise StoreError(f"store marker {MARKER_NAME} is missing or invalid: {exc}") from exc
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or data.get("layout") != LAYOUT
            or data.get("role") not in ROLES
        ):
            raise StoreError(f"store marker {MARKER_NAME} has an unexpected format")
        if role is not None and data["role"] != role:
            raise StoreError(f"store role is {data['role']!r}, expected {role!r}")
        return cls(root, data["role"])

    def blob_path(self, digest: str) -> Path:
        make_ref(digest)
        return self.root / "sha256" / digest[:2] / digest

    def has(self, digest: str) -> bool:
        return self.blob_path(digest).is_file()

    def read_verified(self, digest: str, size: int | None = None) -> bytes:
        path = self.blob_path(digest)
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise StoreError(f"{self.role}: blob {digest} is missing") from exc
        if size is not None and len(data) != size:
            raise StoreError(
                f"{self.role}: blob {digest} size mismatch ({len(data)} bytes, expected {size})"
            )
        if _sha256(data) != digest:
            raise StoreError(f"{self.role}: blob {digest} digest mismatch")
        return data

    def put_bytes(self, data: bytes) -> dict:
        digest = _sha256(data)
        final = self.blob_path(digest)
        if final.exists():
            try:
                self.read_verified(digest, len(data))
            except StoreError as exc:
                raise StoreError(
                    f"existing blob is not intact, refusing to replace it: {exc}"
                ) from exc
            return {"sha256": digest, "bytes": len(data)}
        final.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(dir=final.parent, prefix=".tmp-", delete=False)
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if _sha256(temporary.read_bytes()) != digest:
                raise StoreError(f"{self.role}: write verification failed for {digest}")
            _publish_without_overwrite(temporary, final)
        finally:
            temporary.unlink(missing_ok=True)
        self.read_verified(digest, len(data))
        try:
            os.chmod(final, 0o444)
        except OSError:
            pass
        return {"sha256": digest, "bytes": len(data)}

    def put_file(self, path: Path) -> dict:
        return self.put_bytes(Path(path).read_bytes())


def _copy_exclusive(source: Path, target: Path) -> None:
    """Copy on filesystems without hardlinks without replacing a racing writer."""
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _publish_without_overwrite(temporary: Path, final: Path) -> None:
    """Publish complete bytes once, serializing writers on filesystems without links."""
    lock_path = final.with_name(f".lock-{final.name}")
    # Keep the lock file: unlinking it would let another process lock a new inode.
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        if final.exists() or final.is_symlink():
            return
        try:
            os.link(temporary, final)
        except FileExistsError:
            return
        except OSError:
            # DrvFS disallows hardlinks. Both paths are in one directory, so
            # rename exposes only the already fsynced, verified temporary file.
            if final.exists() or final.is_symlink():
                return
            os.rename(temporary, final)


def init_store(root: Path | str, role: str) -> Store:
    """Create (or reopen) a store root explicitly. Never adopts a used folder."""
    if role not in ROLES:
        raise StoreError(f"role must be one of {ROLES}, got {role!r}")
    root = Path(root)
    marker = root / MARKER_NAME
    if marker.exists():
        return Store.open(root, role=role)
    if root.exists() and any(root.iterdir()):
        raise StoreError(f"store root is not empty and has no marker: {root}")
    root.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"schema_version": 1, "role": role, "layout": LAYOUT}, indent=2) + "\n",
        encoding="utf-8",
    )
    return Store.open(root, role=role)


def store_from_env(variable: str, role: str) -> Store:
    value = os.environ.get(variable, "")
    if not value:
        raise StoreError(f"{variable} is not set")
    if not Path(value).is_absolute():
        raise StoreError(f"{variable} must be an absolute path")
    return Store.open(value, role=role)


def _destination(dest_root: Path, relative: str) -> Path:
    parts = validate_relative_path(relative).parts
    root = dest_root.resolve()
    target = root.joinpath(*parts)
    if target.is_symlink():
        raise StoreError(f"restore target is a symlink: {relative!r}")
    if not target.parent.resolve(strict=False).is_relative_to(root):
        raise StoreError(f"restore path escapes the destination: {relative!r}")
    return target


def _write_restored(target: Path, data: bytes, relative: str) -> str:
    if target.exists():
        if target.is_file() and _sha256(target.read_bytes()) == _sha256(data):
            return "present"
        raise StoreError(f"restore target exists with different content: {relative!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=target.parent, prefix=".restore-", delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(data)
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise StoreError(f"restore target appeared during restore: {relative!r}") from exc
        except OSError:
            try:
                _copy_exclusive(temporary, target)
            except FileExistsError as exc:
                raise StoreError(f"restore target appeared during restore: {relative!r}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return "written"


def restore(stores: Sequence[Store], manifest: dict, dest_root: Path | str) -> dict:
    """Restore every manifest entry under ``dest_root`` from the first intact store.

    A store that is missing or corrupt for an entry is recorded in ``failures``
    and the result becomes ``RECOVERED`` rather than ``PASS``. No verified copy
    at all, an unsafe path or a conflicting existing file raises ``StoreError``.
    """
    load_manifest(manifest)
    dest_root = Path(dest_root)
    dest_root.mkdir(parents=True, exist_ok=True)
    report_entries = []
    recovered = False
    for entry in manifest["entries"]:
        digest = parse_ref(entry["ref"])
        target = _destination(dest_root, entry["path"])
        failures = []
        data = served_by = None
        for store in stores:
            try:
                data = store.read_verified(digest, entry["bytes"])
                served_by = store.role
                break
            except StoreError as exc:
                failures.append({"store": store.role, "error": str(exc)})
        if data is None:
            raise StoreError(f"no verified copy of {entry['path']!r} ({digest}): {failures}")
        action = _write_restored(target, data, entry["path"])
        if _sha256(target.read_bytes()) != digest:
            raise StoreError(f"restored bytes do not match the manifest: {entry['path']!r}")
        recovered = recovered or bool(failures)
        report_entries.append(
            {
                "path": entry["path"],
                "sha256": digest,
                "served_by": served_by,
                "action": action,
                "failures": failures,
            }
        )
    return {"status": "RECOVERED" if recovered else "PASS", "entries": report_entries}


def replicate(source: Store, target: Store, digests: Iterable[str]) -> list[dict]:
    """Copy verified blobs from ``source`` into ``target`` (write-once on both sides)."""
    copied = []
    for digest in digests:
        data = source.read_verified(digest)
        copied.append(target.put_bytes(data))
    return copied


def verify_copies(primary: Store, mirror: Store, manifest: dict, workdir: Path | str) -> dict:
    """Restore each copy on its own into a fresh directory and compare three ways."""
    load_manifest(manifest)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    result: dict = {"status": "PASS"}
    for store in (primary, mirror):
        destination = Path(tempfile.mkdtemp(prefix=f"{store.role}-", dir=workdir))
        try:
            report = restore([store], manifest, destination)
            for entry in manifest["entries"]:
                restored = destination.joinpath(*PurePosixPath(entry["path"]).parts).read_bytes()
                if _sha256(restored) != parse_ref(entry["ref"]) or len(restored) != entry["bytes"]:
                    raise StoreError(f"restored file differs from manifest: {entry['path']!r}")
            result[store.role] = {
                "status": "PASS",
                "entries": len(report["entries"]),
                "bytes": sum(entry["bytes"] for entry in manifest["entries"]),
            }
        except StoreError as exc:
            result[store.role] = {"status": "FAIL", "error": str(exc)}
            result["status"] = "FAIL"
    return result


def _stores_from_env() -> tuple[Store, Store]:
    return (
        store_from_env("PROJECTS_ARTIFACT_STORE", role="primary"),
        store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a store root with its marker")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--role", choices=ROLES, required=True)
    put = commands.add_parser("put", help="store files in both copies and write a manifest")
    put.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    put.add_argument("--manifest-out", type=Path, required=True)
    put.add_argument("files", nargs="+")
    verify = commands.add_parser("verify", help="restore both copies independently and compare")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--work", type=Path, required=True)
    restore_cmd = commands.add_parser("restore", help="restore a manifest into a directory")
    restore_cmd.add_argument("manifest", type=Path)
    restore_cmd.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            store = init_store(args.root, args.role)
            print(json.dumps({"status": "PASS", "role": store.role}))
            return 0
        primary, mirror = _stores_from_env()
        if args.command == "put":
            project = args.project_root.resolve()
            entries = []
            for name in args.files:
                validate_relative_path(name)
                data = (project / name).read_bytes()
                info = primary.put_bytes(data)
                replicate(primary, mirror, [info["sha256"]])
                entries.append(manifest_entry(name, data))
            manifest = {"schema_version": 1, "kind": MANIFEST_KIND, "entries": entries}
            load_manifest(manifest)
            args.manifest_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "PASS", "entries": len(entries)}))
            return 0
        manifest = load_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
        if args.command == "verify":
            report = verify_copies(primary, mirror, manifest, args.work)
        else:
            report = restore([primary, mirror], manifest, args.dest)
        print(json.dumps(report, indent=2))
        return 0 if report["status"] in ("PASS", "RECOVERED") else 1
    except StoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
