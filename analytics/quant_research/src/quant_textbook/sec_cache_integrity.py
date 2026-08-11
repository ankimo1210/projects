"""Fail-closed integrity checks for a local B9 SEC batch cache.

This module validates only the cache manifest contracts written by
``tools/fetch_sec_b9_cache.py``.  It deliberately does *not* assume a
particular set of raw SEC filenames or reject extra files below the root:
those are concerns for the downstream, purpose-specific parser.  A caller
must consume ``success_cik_dirs`` only when ``accepted`` is true.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

_BATCH_SCHEMA = "b9-sec-batch-v1"
_CACHE_SCHEMA = "b9-sec-cache-v1"
_CIK_DIRECTORY_RE = re.compile(r"^CIK([0-9]{10})$")
_RAW_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.json$")
_SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_MISSING = object()


@dataclass(frozen=True)
class B9BatchCacheIntegrity:
    """Result of validating one local SEC batch cache root.

    Any validation error clears the successful directory list and count.  This
    makes accidental partial-cache consumption impossible for callers that use
    this result as the input boundary to a panel build.
    """

    cache_root: Path
    success_cik_dirs: tuple[Path, ...]
    success_cik_count: int
    errors: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        """Whether every declared successful CIK cache passed integrity checks."""

        return not self.errors and self.success_cik_count == len(self.success_cik_dirs)


def _fail(cache_root: Path, errors: list[str]) -> B9BatchCacheIntegrity:
    return B9BatchCacheIntegrity(
        cache_root=cache_root,
        success_cik_dirs=(),
        success_cik_count=0,
        errors=tuple(errors),
    )


def _required(mapping: Mapping[str, Any], field: str, *, label: str, errors: list[str]) -> Any:
    value = mapping.get(field, _MISSING)
    if value is _MISSING:
        errors.append(f"{label} is missing required field {field!r}")
    elif value is None:
        errors.append(f"{label}.{field} must not be null")
    return value


def _nonnegative_int(value: Any, *, label: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{label} must be a non-negative integer")
        return None
    return value


def _normalized_cik(value: Any, *, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.isdigit() or len(value) != 10 or value == "0" * 10:
        errors.append(f"{label} must be a nonzero, zero-padded 10-digit CIK string")
        return None
    return value


def _sha256_value(value: Any, *, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        errors.append(f"{label} must be a 64-character SHA-256 hex digest")
        return None
    return value.lower()


def _read_json_object(path: Path, *, label: str, errors: list[str]) -> Mapping[str, Any] | None:
    if path.is_symlink():
        errors.append(f"{label} must not be a symbolic link: {path}")
        return None
    if not path.is_file():
        errors.append(f"{label} does not exist as a regular file: {path}")
        return None
    try:
        decoded = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"{label} is not readable UTF-8 JSON: {path} ({error})")
        return None
    if not isinstance(decoded, Mapping):
        errors.append(f"{label} must be a JSON object: {path}")
        return None
    return decoded


def _safe_cache_dir(
    root: Path, directory: Any, *, label: str, errors: list[str]
) -> tuple[Path, str] | None:
    if not isinstance(directory, str):
        errors.append(f"{label}.directory must be a non-null string")
        return None
    match = _CIK_DIRECTORY_RE.fullmatch(directory)
    if match is None:
        errors.append(f"{label}.directory must be a safe CIK########## directory name")
        return None
    path = root / directory
    if path.is_symlink():
        errors.append(f"{label}.directory must not be a symbolic link: {path}")
        return None
    if not path.is_dir():
        errors.append(f"{label}.directory does not exist as a directory: {path}")
        return None
    try:
        if path.resolve().parent != root:
            errors.append(f"{label}.directory resolves outside cache root: {path}")
            return None
    except OSError as error:
        errors.append(f"{label}.directory cannot be resolved safely: {path} ({error})")
        return None
    return path, match.group(1)


def _validate_raw_files(
    cache_dir: Path,
    files: Any,
    *,
    label: str,
    errors: list[str],
) -> int | None:
    if not isinstance(files, list):
        errors.append(f"{label}.files must be a JSON array")
        return None

    names: set[str] = set()
    expected_root = cache_dir.resolve()
    for index, item in enumerate(files):
        item_label = f"{label}.files[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{item_label} must be a JSON object")
            continue
        name = _required(item, "name", label=item_label, errors=errors)
        expected_bytes = _nonnegative_int(
            _required(item, "bytes", label=item_label, errors=errors),
            label=f"{item_label}.bytes",
            errors=errors,
        )
        expected_digest = _sha256_value(
            _required(item, "sha256", label=item_label, errors=errors),
            label=f"{item_label}.sha256",
            errors=errors,
        )
        if not isinstance(name, str) or not _RAW_FILENAME_RE.fullmatch(name):
            errors.append(f"{item_label}.name must be a safe JSON filename")
            continue
        if name == "manifest.json":
            errors.append(f"{item_label}.name must not refer to child manifest.json")
            continue
        if name in names:
            errors.append(f"{label}.files contains duplicate raw filename {name!r}")
            continue
        names.add(name)
        if expected_bytes is None or expected_digest is None:
            continue

        raw_path = cache_dir / name
        if raw_path.is_symlink():
            errors.append(f"{item_label}.name must not be a symbolic link: {raw_path}")
            continue
        if not raw_path.is_file():
            errors.append(f"{item_label}.name does not exist as a regular file: {raw_path}")
            continue
        try:
            if raw_path.resolve().parent != expected_root:
                errors.append(f"{item_label}.name resolves outside its CIK cache: {raw_path}")
                continue
            payload = raw_path.read_bytes()
        except OSError as error:
            errors.append(f"{item_label}.name cannot be read safely: {raw_path} ({error})")
            continue
        if len(payload) != expected_bytes:
            errors.append(
                f"{item_label}.bytes mismatch for {raw_path}: "
                f"manifest={expected_bytes}, actual={len(payload)}"
            )
        actual_digest = sha256(payload).hexdigest()
        if actual_digest != expected_digest:
            errors.append(
                f"{item_label}.sha256 mismatch for {raw_path}: "
                f"manifest={expected_digest}, actual={actual_digest}"
            )
    return len(files)


def _validate_cache_entry(
    root: Path,
    entry: Any,
    *,
    index: int,
    seen_ciks: set[str],
    seen_directories: set[str],
    errors: list[str],
) -> Path | None:
    label = f"batch_manifest.caches[{index}]"
    if not isinstance(entry, Mapping):
        errors.append(f"{label} must be a JSON object")
        return None

    entry_cik = _normalized_cik(
        _required(entry, "cik", label=label, errors=errors), label=f"{label}.cik", errors=errors
    )
    safe_dir = _safe_cache_dir(
        root,
        _required(entry, "directory", label=label, errors=errors),
        label=label,
        errors=errors,
    )
    entry_file_count = _nonnegative_int(
        _required(entry, "file_count", label=label, errors=errors),
        label=f"{label}.file_count",
        errors=errors,
    )
    entry_archive_count = _nonnegative_int(
        _required(entry, "archive_count_advertised", label=label, errors=errors),
        label=f"{label}.archive_count_advertised",
        errors=errors,
    )
    expected_manifest_digest = _sha256_value(
        _required(entry, "manifest_sha256", label=label, errors=errors),
        label=f"{label}.manifest_sha256",
        errors=errors,
    )

    if entry_cik is not None:
        if entry_cik in seen_ciks:
            errors.append(f"{label}.cik duplicates another successful cache: {entry_cik}")
        seen_ciks.add(entry_cik)
    if safe_dir is None:
        return None
    cache_dir, directory_cik = safe_dir
    if cache_dir.name in seen_directories:
        errors.append(f"{label}.directory duplicates another successful cache: {cache_dir.name}")
    seen_directories.add(cache_dir.name)
    if entry_cik is None or entry_file_count is None or entry_archive_count is None:
        return None
    if expected_manifest_digest is None:
        return None
    if entry_cik != directory_cik:
        errors.append(f"{label}.cik does not match directory CIK: {entry_cik} != {directory_cik}")
        return None

    child_manifest_path = cache_dir / "manifest.json"
    if child_manifest_path.is_symlink():
        errors.append(f"{label} child manifest must not be a symbolic link: {child_manifest_path}")
        return None
    if not child_manifest_path.is_file():
        errors.append(
            f"{label} child manifest does not exist as a regular file: {child_manifest_path}"
        )
        return None
    try:
        child_manifest_payload = child_manifest_path.read_bytes()
    except OSError as error:
        errors.append(f"{label} child manifest cannot be read: {child_manifest_path} ({error})")
        return None
    actual_manifest_digest = sha256(child_manifest_payload).hexdigest()
    if actual_manifest_digest != expected_manifest_digest:
        errors.append(
            f"{label}.manifest_sha256 mismatch for {child_manifest_path}: "
            f"batch={expected_manifest_digest}, actual={actual_manifest_digest}"
        )
        return None
    child = _read_json_object(child_manifest_path, label=f"{label} child manifest", errors=errors)
    if child is None:
        return None
    schema = _required(child, "schema_version", label=f"{label} child manifest", errors=errors)
    if schema != _CACHE_SCHEMA:
        errors.append(
            f"{label} child manifest.schema_version must be {_CACHE_SCHEMA!r}, found {schema!r}"
        )
    child_cik = _normalized_cik(
        _required(child, "cik", label=f"{label} child manifest", errors=errors),
        label=f"{label} child manifest.cik",
        errors=errors,
    )
    if child_cik is not None and child_cik != entry_cik:
        errors.append(
            f"{label} child manifest.cik does not match batch/directory CIK: "
            f"{child_cik} != {entry_cik}"
        )
    child_file_count = _nonnegative_int(
        _required(child, "file_count", label=f"{label} child manifest", errors=errors),
        label=f"{label} child manifest.file_count",
        errors=errors,
    )
    child_archive_count = _nonnegative_int(
        _required(
            child, "archive_count_advertised", label=f"{label} child manifest", errors=errors
        ),
        label=f"{label} child manifest.archive_count_advertised",
        errors=errors,
    )
    raw_count = _validate_raw_files(
        cache_dir,
        _required(child, "files", label=f"{label} child manifest", errors=errors),
        label=f"{label} child manifest",
        errors=errors,
    )
    if child_file_count is not None and raw_count is not None and child_file_count != raw_count:
        errors.append(
            f"{label} child manifest.file_count does not match files length: "
            f"{child_file_count} != {raw_count}"
        )
    if child_file_count is not None and child_file_count != entry_file_count:
        errors.append(
            f"{label}.file_count does not match child manifest: "
            f"{entry_file_count} != {child_file_count}"
        )
    if child_archive_count is not None and child_archive_count != entry_archive_count:
        errors.append(
            f"{label}.archive_count_advertised does not match child manifest: "
            f"{entry_archive_count} != {child_archive_count}"
        )
    return cache_dir


def _validate_failure_entries(
    failures: list[Any], *, successful_ciks: set[str], errors: list[str]
) -> None:
    seen_failures: set[str] = set()
    for index, failure in enumerate(failures):
        label = f"batch_manifest.failures[{index}]"
        if not isinstance(failure, Mapping):
            errors.append(f"{label} must be a JSON object")
            continue
        cik = _normalized_cik(
            _required(failure, "cik", label=label, errors=errors),
            label=f"{label}.cik",
            errors=errors,
        )
        if cik is None:
            continue
        if cik in seen_failures:
            errors.append(f"{label}.cik duplicates another failed cache: {cik}")
        if cik in successful_ciks:
            errors.append(f"{label}.cik is also declared as a successful cache: {cik}")
        seen_failures.add(cik)


def validate_sec_b9_batch_cache(cache_root: Path) -> B9BatchCacheIntegrity:
    """Validate an explicit B9 SEC batch cache root without network access.

    The function reports malformed or tampered input through ``errors`` rather
    than raising, and returns no usable directory on any error.  It validates
    only the batch and child manifest contracts; downstream parsing decides
    which raw SEC files are semantically required for a specific analysis.
    """

    try:
        root = Path(cache_root).expanduser().resolve()
    except OSError as error:
        fallback = Path(cache_root).expanduser()
        return _fail(fallback, [f"cache root cannot be resolved safely: {fallback} ({error})"])
    if not root.is_dir():
        return _fail(root, [f"cache root does not exist as a directory: {root}"])

    errors: list[str] = []
    batch = _read_json_object(root / "batch_manifest.json", label="batch manifest", errors=errors)
    if batch is None:
        return _fail(root, errors)

    schema = _required(batch, "schema_version", label="batch_manifest", errors=errors)
    if schema != _BATCH_SCHEMA:
        errors.append(f"batch_manifest.schema_version must be {_BATCH_SCHEMA!r}, found {schema!r}")
    requested_count = _nonnegative_int(
        _required(batch, "requested_cik_count", label="batch_manifest", errors=errors),
        label="batch_manifest.requested_cik_count",
        errors=errors,
    )
    declared_success_count = _nonnegative_int(
        _required(batch, "success_count", label="batch_manifest", errors=errors),
        label="batch_manifest.success_count",
        errors=errors,
    )
    failure_count = _nonnegative_int(
        _required(batch, "failure_count", label="batch_manifest", errors=errors),
        label="batch_manifest.failure_count",
        errors=errors,
    )
    caches = _required(batch, "caches", label="batch_manifest", errors=errors)
    failures = _required(batch, "failures", label="batch_manifest", errors=errors)
    if not isinstance(caches, list):
        errors.append("batch_manifest.caches must be a JSON array")
    if not isinstance(failures, list):
        errors.append("batch_manifest.failures must be a JSON array")
    if errors:
        return _fail(root, errors)
    assert isinstance(caches, list)
    assert isinstance(failures, list)
    assert requested_count is not None
    assert declared_success_count is not None
    assert failure_count is not None

    if len(caches) != declared_success_count:
        errors.append(
            "batch_manifest.success_count does not match caches length: "
            f"{declared_success_count} != {len(caches)}"
        )
    if len(failures) != failure_count:
        errors.append(
            "batch_manifest.failure_count does not match failures length: "
            f"{failure_count} != {len(failures)}"
        )
    if requested_count != declared_success_count + failure_count:
        errors.append(
            "batch_manifest.requested_cik_count must equal success_count + failure_count: "
            f"{requested_count} != {declared_success_count} + {failure_count}"
        )

    seen_ciks: set[str] = set()
    seen_directories: set[str] = set()
    successful_dirs: list[Path] = []
    for index, entry in enumerate(caches):
        prior_errors = len(errors)
        cache_dir = _validate_cache_entry(
            root,
            entry,
            index=index,
            seen_ciks=seen_ciks,
            seen_directories=seen_directories,
            errors=errors,
        )
        if cache_dir is not None and len(errors) == prior_errors:
            successful_dirs.append(cache_dir)
    _validate_failure_entries(failures, successful_ciks=seen_ciks, errors=errors)

    if errors:
        return _fail(root, errors)
    return B9BatchCacheIntegrity(
        cache_root=root,
        success_cik_dirs=tuple(successful_dirs),
        success_cik_count=len(successful_dirs),
        errors=(),
    )
