"""Capacity cleanup must preserve receipt-bound bytes and fail safely."""

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/share_closed_artifacts.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def artifact(root, name, payload=b"a" * 8192):
    directory = root / name
    directory.mkdir(parents=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo("value.npy", date_time=(2020, 1, 1, 0, 0, 0)), payload)
    arrays = buffer.getvalue()
    metadata = canonical({"schema": "rb-f04-array-chunk-v1", "metadata": {"label": "same"}})
    receipt = {
        "schema": "rb-f04-array-receipt-v1",
        "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
        "arrays_sha256": hashlib.sha256(arrays).hexdigest(),
        "uncompressed_bytes": len(payload),
    }
    receipt["artifact_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    for filename, data in (
        ("metadata.json", metadata),
        ("arrays.npz", arrays),
        ("receipt.json", canonical(receipt)),
    ):
        (directory / filename).write_bytes(data)
    return directory


def run_tool(root, journal, *extra):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--journal",
            str(journal),
            "--min-age-seconds",
            "0",
            "--min-bytes",
            "1",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout.splitlines()[-1])


def test_audit_leaves_all_bytes_and_inodes_unchanged(tmp_path):
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    before = {p: (p.read_bytes(), p.stat().st_ino) for d in (a, b) for p in d.iterdir()}
    report = run_tool(root, tmp_path / "audit.jsonl")
    assert report["candidate_files"] == 2
    assert report["linked"] == 0
    assert before == {p: (p.read_bytes(), p.stat().st_ino) for p in before}


def test_apply_shares_bytes_without_changing_receipts_or_paths(tmp_path):
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    before = {p: p.read_bytes() for d in (a, b) for p in d.iterdir()}
    report = run_tool(root, tmp_path / "apply.jsonl", "--apply")
    assert report["linked"] == 2
    assert report["released_allocated_bytes"] > 0
    assert {p: p.read_bytes() for p in before} == before
    for name in ("metadata.json", "arrays.npz"):
        assert (a / name).stat().st_ino == (b / name).stat().st_ino
    assert (a / "receipt.json").stat().st_ino != (b / "receipt.json").stat().st_ino


def test_corrupt_payload_is_not_replaced(tmp_path):
    root = tmp_path / "native"
    artifact(root, "a")
    b = artifact(root, "b")
    target = b / "arrays.npz"
    original = target.read_bytes()
    target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    changed = target.read_bytes()
    report = run_tool(root, tmp_path / "corrupt.jsonl", "--apply")
    assert report["linked"] == 0
    assert report["rejected"] >= 1
    assert target.read_bytes() == changed


def test_recent_artifacts_are_skipped(tmp_path):
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    report = run_tool(root, tmp_path / "recent.jsonl", "--apply", "--min-age-seconds", "3600")
    assert report["linked"] == 0
    assert (a / "arrays.npz").stat().st_ino != (b / "arrays.npz").stat().st_ino


def test_symlink_directory_is_not_followed(tmp_path):
    root = tmp_path / "native"
    artifact(root, "a")
    outside = artifact(tmp_path / "outside", "b")
    (root / "b").symlink_to(outside, target_is_directory=True)
    before = (outside / "arrays.npz").stat().st_ino
    report = run_tool(root, tmp_path / "symlink.jsonl", "--apply")
    assert report["linked"] == 0
    assert (outside / "arrays.npz").stat().st_ino == before


def test_existing_external_hardlink_is_not_counted_as_freed(tmp_path):
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    for directory in (a, b):
        for name in ("metadata.json", "arrays.npz"):
            os.link(directory / name, tmp_path / (directory.name + "-" + name))
    report = run_tool(root, tmp_path / "external.jsonl", "--apply")
    assert report["linked"] == 2
    assert report["released_allocated_bytes"] == 0
    assert (a / "arrays.npz").stat().st_ino == (b / "arrays.npz").stat().st_ino


def load_tool():
    spec = importlib.util.spec_from_file_location("share_closed_artifacts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_postcheck_failure_restores_original_target(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(
        root, tmp_path / "failure.jsonl", apply=True, min_age_seconds=0, min_bytes=1
    )
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    original_inode = (b / "arrays.npz").stat().st_ino
    monkeypatch.setattr(
        engine,
        "verify_replacement",
        lambda *args: (_ for _ in ()).throw(OSError("injected read failure")),
    )
    with pytest.raises(OSError, match="injected"):
        engine.link(source, target)
    assert (b / "arrays.npz").stat().st_ino == original_inode
    assert (a / "arrays.npz").read_bytes() == (b / "arrays.npz").read_bytes()
    engine.close()


def test_rollback_failure_keeps_original_backup(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(
        root, tmp_path / "rollback.jsonl", apply=True, min_age_seconds=0, min_bytes=1
    )
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    original_inode = target["stat"].st_ino
    replace = os.replace
    calls = 0

    def injected_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected rollback failure")
        return replace(src, dst)

    monkeypatch.setattr(os, "replace", injected_replace)
    monkeypatch.setattr(
        engine, "verify_replacement", lambda *args: (_ for _ in ()).throw(OSError("postcheck"))
    )
    with pytest.raises(module.RollbackFailedError, match="backup retained"):
        engine.link(source, target)
    backups = list(engine.staging.iterdir())
    assert len(backups) == 1
    assert backups[0].stat().st_ino == original_inode
    assert backups[0].read_bytes() == (a / "arrays.npz").read_bytes()
    engine.close()
    assert backups[0].exists()


def test_changed_target_is_rejected_before_replacement(tmp_path):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(
        root, tmp_path / "changed.jsonl", apply=True, min_age_seconds=0, min_bytes=1
    )
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    (b / "arrays.npz").write_bytes(b"changed")
    with pytest.raises(ValueError):
        engine.link(source, target)
    assert (b / "arrays.npz").read_bytes() == b"changed"
    assert (a / "arrays.npz").stat().st_ino != (b / "arrays.npz").stat().st_ino
    engine.close()


def test_invalid_receipt_is_not_trusted(tmp_path):
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    path = b / "receipt.json"
    receipt = json.loads(path.read_bytes())
    receipt["artifact_sha256"] = "0" * 64
    path.write_bytes(canonical(receipt))
    report = run_tool(root, tmp_path / "invalid.jsonl", "--apply")
    assert report["linked"] == 0
    assert report["rejected"] == 2
    assert (a / "arrays.npz").stat().st_ino != (b / "arrays.npz").stat().st_ino


def test_keyboard_interrupt_restores_original_target(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(
        root, tmp_path / "interrupt.jsonl", apply=True, min_age_seconds=0, min_bytes=1
    )
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    original_inode = target["stat"].st_ino
    monkeypatch.setattr(
        engine, "verify_replacement", lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        engine.link(source, target)
    assert (b / "arrays.npz").stat().st_ino == original_inode
    engine.close()


def test_rollback_attempts_consume_mutation_budget(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    artifact(root, "a")
    artifact(root, "b")
    artifact(root, "c")
    engine = module.SharingRun(
        root, tmp_path / "attempts.jsonl", apply=True, min_age_seconds=0, min_bytes=1, max_links=1
    )
    monkeypatch.setattr(
        engine, "verify_replacement", lambda *args: (_ for _ in ()).throw(OSError("postcheck"))
    )
    report = engine.run()
    assert report["termination"] == "administrative_limit"
    assert report["replacement_attempts"] == 1
    assert report["linked"] == 0


def test_interrupt_immediately_after_replace_restores_target(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(root, tmp_path / "replace-interrupt.jsonl", min_age_seconds=0)
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    original_inode = target["stat"].st_ino
    replace = os.replace
    calls = 0

    def interrupted_replace(src, dst):
        nonlocal calls
        calls += 1
        replace(src, dst)
        if calls == 1:
            raise KeyboardInterrupt()

    monkeypatch.setattr(os, "replace", interrupted_replace)
    with pytest.raises(KeyboardInterrupt):
        engine.link(source, target)
    assert (b / "arrays.npz").stat().st_ino == original_inode
    engine.close()


def test_commit_cleanup_failure_stops_with_explicit_state(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(root, tmp_path / "commit-failure.jsonl", min_age_seconds=0)
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    sync = module.sync_directory

    def failed_cleanup_sync(path):
        if path == engine.staging and not any(path.iterdir()):
            raise OSError("injected commit durability failure")
        sync(path)

    monkeypatch.setattr(module, "sync_directory", failed_cleanup_sync)
    with pytest.raises(RuntimeError, match="committed"):
        engine.link(source, target)
    assert (b / "arrays.npz").stat().st_ino == source["stat"].st_ino
    assert (b / "arrays.npz").read_bytes() == (a / "arrays.npz").read_bytes()
    assert engine.report["committed_unconfirmed"] == 1
    engine.close()


def test_rollback_durability_failure_keeps_original_backup(tmp_path, monkeypatch):
    module = load_tool()
    root = tmp_path / "native"
    a, b = artifact(root, "a"), artifact(root, "b")
    engine = module.SharingRun(root, tmp_path / "rollback-sync.jsonl", min_age_seconds=0)
    engine.prepare()
    source, target = engine.inspect(a / "arrays.npz"), engine.inspect(b / "arrays.npz")
    original_inode = target["stat"].st_ino
    sync = module.sync_directory
    rollback = False

    def failed_postcheck(*args):
        nonlocal rollback
        rollback = True
        raise OSError("postcheck")

    def failed_rollback_sync(path):
        if rollback and path == b:
            raise OSError("injected rollback durability failure")
        sync(path)

    monkeypatch.setattr(engine, "verify_replacement", failed_postcheck)
    monkeypatch.setattr(module, "sync_directory", failed_rollback_sync)
    with pytest.raises(module.RollbackFailedError, match="backup retained"):
        engine.link(source, target)
    backups = list(engine.staging.iterdir())
    assert len(backups) == 1
    assert backups[0].stat().st_ino == original_inode
    assert (b / "arrays.npz").stat().st_ino == original_inode
    engine.close()
    assert backups[0].exists()
