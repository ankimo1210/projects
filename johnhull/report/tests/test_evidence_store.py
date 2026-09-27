"""Contract tests for the immutable evidence store (D1-preflight stage 1)."""

from __future__ import annotations

import errno
import hashlib
import json
import os

import pytest

from johnhull.scripts.evidence_store import (
    MARKER_NAME,
    Store,
    StoreError,
    init_store,
    load_manifest,
    make_ref,
    manifest_entry,
    parse_ref,
    replicate,
    restore,
    store_from_env,
    validate_relative_path,
    verify_copies,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"evidence-bytes" * 8


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def primary(tmp_path):
    return init_store(tmp_path / "primary", role="primary")


@pytest.fixture
def mirror(tmp_path):
    return init_store(tmp_path / "mirror", role="mirror")


def _manifest(entries):
    return {"schema_version": 1, "kind": "johnhull-evidence-manifest", "entries": entries}


# --- references -----------------------------------------------------------------


def test_reference_round_trip_uses_the_logical_artifact_prefix():
    digest = _digest(PNG)
    assert make_ref(digest) == f"artifact:sha256:{digest}"
    assert parse_ref(make_ref(digest)) == digest


@pytest.mark.parametrize(
    "value",
    ["sha256:" + "a" * 64, "artifact:sha256:" + "A" * 64, "artifact:sha256:" + "a" * 63, ""],
)
def test_malformed_reference_is_rejected(value):
    with pytest.raises(StoreError, match="reference"):
        parse_ref(value)


# --- store roots ------------------------------------------------------------------


def test_init_writes_a_marker_with_the_role_and_layout(tmp_path):
    store = init_store(tmp_path / "root", role="primary")
    marker = json.loads((tmp_path / "root" / MARKER_NAME).read_text(encoding="utf-8"))
    assert marker == {"schema_version": 1, "role": "primary", "layout": "sha256/<2>/<sha256>"}
    assert store.role == "primary"


def test_init_refuses_a_non_empty_directory_without_marker(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StoreError, match="not empty"):
        init_store(root, role="primary")


def test_init_refuses_to_change_the_role_of_an_existing_store(primary):
    with pytest.raises(StoreError, match="role"):
        init_store(primary.root, role="mirror")


def test_open_requires_the_marker(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(StoreError, match="marker"):
        Store.open(tmp_path / "empty")


def test_open_never_creates_a_missing_root(tmp_path):
    missing = tmp_path / "not-mounted"
    with pytest.raises(StoreError, match="does not exist"):
        Store.open(missing)
    assert not missing.exists()


def test_open_checks_the_expected_role(primary):
    with pytest.raises(StoreError, match="role"):
        Store.open(primary.root, role="mirror")


def test_unset_environment_variable_is_an_explicit_error(monkeypatch):
    monkeypatch.delenv("PROJECTS_ARTIFACT_STORE", raising=False)
    with pytest.raises(StoreError, match="PROJECTS_ARTIFACT_STORE is not set"):
        store_from_env("PROJECTS_ARTIFACT_STORE", role="primary")


def test_relative_environment_path_is_rejected(monkeypatch):
    monkeypatch.setenv("PROJECTS_ARTIFACT_MIRROR", "relative/store")
    with pytest.raises(StoreError, match="absolute"):
        store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror")


def test_environment_path_opens_the_store(monkeypatch, mirror):
    monkeypatch.setenv("PROJECTS_ARTIFACT_MIRROR", str(mirror.root))
    assert store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror").root == mirror.root


# --- put / read -----------------------------------------------------------------


def test_put_stores_bytes_under_the_content_address(primary):
    info = primary.put_bytes(PNG)
    digest = _digest(PNG)
    assert info == {"sha256": digest, "bytes": len(PNG)}
    assert (primary.root / "sha256" / digest[:2] / digest).read_bytes() == PNG
    assert primary.read_verified(digest, len(PNG)) == PNG


def test_put_is_idempotent_and_leaves_no_temporary_files(primary):
    primary.put_bytes(PNG)
    primary.put_bytes(PNG)
    shard = primary.root / "sha256" / _digest(PNG)[:2]
    assert [path.name for path in shard.iterdir()] == [_digest(PNG)]


def test_put_refuses_to_replace_a_corrupted_existing_blob(primary):
    info = primary.put_bytes(PNG)
    blob = primary.blob_path(info["sha256"])
    os.chmod(blob, 0o644)
    blob.write_bytes(PNG[:-1] + b"X")
    with pytest.raises(StoreError, match="existing blob"):
        primary.put_bytes(PNG)
    assert blob.read_bytes() == PNG[:-1] + b"X"


def test_missing_blob_is_reported(primary):
    with pytest.raises(StoreError, match="missing"):
        primary.read_verified(_digest(PNG), len(PNG))


def test_one_byte_corruption_is_detected(primary):
    info = primary.put_bytes(PNG)
    blob = primary.blob_path(info["sha256"])
    os.chmod(blob, 0o644)
    blob.write_bytes(PNG[:10] + bytes([PNG[10] ^ 1]) + PNG[11:])
    with pytest.raises(StoreError, match="digest mismatch"):
        primary.read_verified(info["sha256"], info["bytes"])


def test_truncated_blob_is_detected(primary):
    info = primary.put_bytes(PNG)
    blob = primary.blob_path(info["sha256"])
    os.chmod(blob, 0o644)
    blob.write_bytes(PNG[:-4])
    with pytest.raises(StoreError, match="size mismatch"):
        primary.read_verified(info["sha256"], info["bytes"])


def test_put_fallback_never_overwrites_a_file_that_appears_during_publish(
    primary, monkeypatch
):
    digest = _digest(PNG)
    final = primary.blob_path(digest)
    original_open = os.open
    appeared = False

    def unsupported_link(_source, _target):
        raise OSError(errno.EPERM, "hardlinks unsupported")

    def competing_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal appeared
        if str(path) == str(final) and flags & os.O_EXCL:
            appeared = True
            final.write_bytes(b"competing writer")
        if dir_fd is None:
            return original_open(path, flags, mode)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "link", unsupported_link)
    monkeypatch.setattr(os, "open", competing_open)
    with pytest.raises(StoreError, match=r"existing blob|size mismatch|digest mismatch"):
        primary.put_bytes(PNG)
    assert appeared
    assert final.read_bytes() == b"competing writer"


# --- paths and manifests --------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "../outside.png",
        "docs/../../outside.png",
        "C:/Users/x.png",
        "c:relative.png",
        "\\\\server\\share\\x.png",
        "//server/share/x.png",
        "docs\\validation\\x.png",
        "",
        "docs/./x.png",
        "docs//x.png",
    ],
)
def test_unsafe_relative_paths_are_rejected(value):
    with pytest.raises(StoreError, match="path"):
        validate_relative_path(value)


def test_manifest_entry_records_reference_size_and_mime():
    entry = manifest_entry("docs/validation/section-27-3/book-ivf_smile-1440.png", PNG)
    assert entry == {
        "path": "docs/validation/section-27-3/book-ivf_smile-1440.png",
        "ref": make_ref(_digest(PNG)),
        "bytes": len(PNG),
        "mime": "image/png",
    }


def test_manifest_rejects_an_unknown_schema_version():
    manifest = _manifest([])
    manifest["schema_version"] = 2
    with pytest.raises(StoreError, match="schema_version"):
        load_manifest(manifest)


def test_manifest_rejects_unknown_entry_fields():
    entry = manifest_entry("a.png", PNG) | {"extra": 1}
    with pytest.raises(StoreError, match="unknown"):
        load_manifest(_manifest([entry]))


def test_manifest_rejects_duplicate_paths():
    entry = manifest_entry("a.png", PNG)
    with pytest.raises(StoreError, match="duplicate path"):
        load_manifest(_manifest([entry, dict(entry)]))


def test_manifest_rejects_conflicting_size_for_one_digest():
    first = manifest_entry("a.png", PNG)
    second = manifest_entry("b.png", PNG) | {"bytes": len(PNG) + 1}
    with pytest.raises(StoreError, match="conflicting"):
        load_manifest(_manifest([first, second]))


def test_manifest_rejects_conflicting_mime_for_one_digest():
    first = manifest_entry("a.png", PNG)
    second = manifest_entry("b.json", PNG)
    with pytest.raises(StoreError, match="conflicting"):
        load_manifest(_manifest([first, second]))


# --- restore ---------------------------------------------------------------------


def test_restore_writes_verified_bytes_to_the_relative_path(primary, tmp_path):
    primary.put_bytes(PNG)
    manifest = load_manifest(_manifest([manifest_entry("docs/v/a.png", PNG)]))
    report = restore([primary], manifest, tmp_path / "dest")
    assert (tmp_path / "dest/docs/v/a.png").read_bytes() == PNG
    assert report["status"] == "PASS"
    assert report["entries"][0]["served_by"] == "primary"


def test_restore_refuses_to_overwrite_a_different_existing_file(primary, tmp_path):
    primary.put_bytes(PNG)
    target = tmp_path / "dest/a.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"other")
    manifest = load_manifest(_manifest([manifest_entry("a.png", PNG)]))
    with pytest.raises(StoreError, match="different content"):
        restore([primary], manifest, tmp_path / "dest")
    assert target.read_bytes() == b"other"


def test_restore_accepts_an_identical_existing_file(primary, tmp_path):
    primary.put_bytes(PNG)
    target = tmp_path / "dest/a.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(PNG)
    manifest = load_manifest(_manifest([manifest_entry("a.png", PNG)]))
    assert restore([primary], manifest, tmp_path / "dest")["status"] == "PASS"


def test_restore_refuses_a_symlink_that_escapes_the_destination(primary, tmp_path):
    primary.put_bytes(PNG)
    dest = tmp_path / "dest"
    dest.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (dest / "docs").symlink_to(outside, target_is_directory=True)
    manifest = load_manifest(_manifest([manifest_entry("docs/a.png", PNG)]))
    with pytest.raises(StoreError, match="escapes"):
        restore([primary], manifest, dest)
    assert not (outside / "a.png").exists()


def test_restore_falls_back_to_the_mirror_and_records_the_primary_failure(
    primary, mirror, tmp_path
):
    mirror.put_bytes(PNG)
    manifest = load_manifest(_manifest([manifest_entry("a.png", PNG)]))
    report = restore([primary, mirror], manifest, tmp_path / "dest")
    entry = report["entries"][0]
    assert entry["served_by"] == "mirror"
    assert entry["failures"] == [{"store": "primary", "error": entry["failures"][0]["error"]}]
    assert "missing" in entry["failures"][0]["error"]
    assert report["status"] == "RECOVERED"


def test_restore_fails_when_no_store_has_a_verified_copy(primary, mirror, tmp_path):
    manifest = load_manifest(_manifest([manifest_entry("a.png", PNG)]))
    with pytest.raises(StoreError, match="no verified copy"):
        restore([primary, mirror], manifest, tmp_path / "dest")


def test_restore_fallback_never_overwrites_a_file_that_appears_during_restore(
    primary, tmp_path, monkeypatch
):
    primary.put_bytes(PNG)
    target = tmp_path / "dest" / "a.png"
    original_open = os.open
    appeared = False

    def unsupported_link(_source, _target):
        raise OSError(errno.EPERM, "hardlinks unsupported")

    def competing_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal appeared
        if str(path) == str(target) and flags & os.O_EXCL:
            appeared = True
            target.write_bytes(b"competing writer")
        if dir_fd is None:
            return original_open(path, flags, mode)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "link", unsupported_link)
    monkeypatch.setattr(os, "open", competing_open)
    manifest = load_manifest(_manifest([manifest_entry("a.png", PNG)]))
    with pytest.raises(StoreError, match="appeared during restore"):
        restore([primary], manifest, tmp_path / "dest")
    assert appeared
    assert target.read_bytes() == b"competing writer"


# --- two copies -----------------------------------------------------------------


def test_replicate_copies_verified_blobs_to_the_mirror(primary, mirror):
    info = primary.put_bytes(PNG)
    replicate(primary, mirror, [info["sha256"]])
    assert mirror.read_verified(info["sha256"], info["bytes"]) == PNG


def test_replicate_refuses_a_corrupted_primary_blob(primary, mirror):
    info = primary.put_bytes(PNG)
    blob = primary.blob_path(info["sha256"])
    os.chmod(blob, 0o644)
    blob.write_bytes(b"broken")
    with pytest.raises(StoreError, match=r"size mismatch|digest mismatch"):
        replicate(primary, mirror, [info["sha256"]])
    assert not mirror.blob_path(info["sha256"]).exists()


def test_verify_copies_restores_each_store_independently(primary, mirror, tmp_path):
    for store in (primary, mirror):
        store.put_bytes(PNG)
    manifest = load_manifest(_manifest([manifest_entry("docs/a.png", PNG)]))
    report = verify_copies(primary, mirror, manifest, tmp_path / "work")
    assert report["status"] == "PASS"
    assert {name: report[name]["status"] for name in ("primary", "mirror")} == {
        "primary": "PASS",
        "mirror": "PASS",
    }


def test_verify_copies_fails_when_the_mirror_is_corrupted(primary, mirror, tmp_path):
    for store in (primary, mirror):
        store.put_bytes(PNG)
    blob = mirror.blob_path(_digest(PNG))
    os.chmod(blob, 0o644)
    blob.write_bytes(PNG[:-1] + b"Y")
    manifest = load_manifest(_manifest([manifest_entry("docs/a.png", PNG)]))
    report = verify_copies(primary, mirror, manifest, tmp_path / "work")
    assert report["status"] == "FAIL"
    assert report["primary"]["status"] == "PASS"
    assert report["mirror"]["status"] == "FAIL"
    assert "digest mismatch" in report["mirror"]["error"]
