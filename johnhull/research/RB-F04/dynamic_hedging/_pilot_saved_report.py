"""Authenticate full saved reports by trusted receipt, without financial solves.

The reader returns lazy full checks and original jobs after streaming every
bound value through the original-format digest. It neither recalculates financial
qualification nor changes unknown, failed, or unclosed cost values. Whole returned
payload memory and execution capacity are separate, unproved properties.
"""

import json
from pathlib import Path

import _pilot_saved_storage as storage

_SCHEMA = "rb-f04-pilot-saved-check-bounded-v1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read_authenticated(directory, expected_receipt, label):
    from run_pilot import read_pilot_artifact

    _require(
        isinstance(expected_receipt, dict) and bool(expected_receipt),
        f"expected {label} receipt required",
    )
    try:
        stored_receipt = json.loads((directory / "receipt.json").read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} receipt is missing or invalid") from error
    _require(stored_receipt == expected_receipt, f"{label} receipt differs from expected")
    value, actual_receipt = read_pilot_artifact(directory)
    _require(actual_receipt == expected_receipt, f"{label} receipt changed during read")
    return value


def _bound_path(root, relative, label):
    _require(isinstance(relative, str) and bool(relative), f"{label} missing")
    path = Path(relative)
    _require(
        not path.is_absolute() and ".." not in path.parts and path != Path("."),
        f"{label} must belong to this restored root",
    )
    result = (root / path).resolve()
    _require(result.is_relative_to(root.resolve()), f"{label} escapes restored root")
    _require(result.is_dir(), f"{label} is missing")
    return result


def read_bounded_report(directory, *, expected_receipt, pilot_directory):
    """Read all original values after matching a caller's trusted outer receipt.

    directory is the report artifact (the writer's output/report).
    pilot_directory is the original or restored native root, explicitly
    supplied by the caller. References retain their original path provenance.
    Passing a receipt copied from an untrusted report does not supply authority.
    No financial qualification, capacity guarantee, or cost closure is inferred.
    """
    _require(
        isinstance(expected_receipt, dict) and bool(expected_receipt),
        "expected report receipt required",
    )
    directory = Path(directory).resolve()
    report = _read_authenticated(directory, expected_receipt, "report")
    _require(report.get("schema") == _SCHEMA, "bounded report schema mismatch")

    check_binding = report["raw_checks_reference"]
    references = check_binding["references"]
    _require(isinstance(references, list), "saved check reference roster missing")
    checks_directory = _bound_path(directory.parent, check_binding["directory"], "check directory")
    if references:
        manifests = storage.read_check_manifest(checks_directory)
    else:
        _require(
            not list(checks_directory.glob("manifest*.json")),
            "saved check manifest roster differs from trusted report",
        )
        manifests = []
    _require(manifests == references, "saved check manifest roster differs from trusted report")
    checks = storage.SavedChecks(checks_directory, references=references)
    _require(
        storage.payload_digest(checks) == check_binding["logical_payload_sha256"],
        "saved checks logical payload differs from trusted report",
    )

    snapshot_binding = report["raw_snapshot_reference"]
    saved_snapshot = snapshot_binding["saved_snapshot"]
    original_digest = snapshot_binding["saved_snapshot_sha256"]
    _require(
        storage.payload_digest(saved_snapshot) == original_digest,
        "original snapshot digest differs from trusted report",
    )
    checkpoint_name = snapshot_binding["checkpoint_name"]
    _require(
        isinstance(checkpoint_name, str) and Path(checkpoint_name).name == checkpoint_name,
        "original checkpoint name must belong to restored root",
    )
    pilot_directory = Path(pilot_directory).resolve()
    checkpoint = _bound_path(pilot_directory, checkpoint_name, "checkpoint directory")
    actual_snapshot = _read_authenticated(checkpoint, snapshot_binding["receipt"], "checkpoint")
    _require(
        storage.payload_digest(actual_snapshot) == original_digest,
        "original snapshot digest differs from checkpoint",
    )

    artifact_context = {
        "original_root": actual_snapshot["artifact_directory"],
        "restored_root": str(pilot_directory),
    }
    jobs = storage.ReferenceJobs(actual_snapshot["jobs"], artifact_context=artifact_context)
    hydrated = dict(actual_snapshot, jobs=jobs.sequence())
    _require(
        storage.payload_digest(hydrated) == snapshot_binding["hydrated_logical_payload_sha256"],
        "hydrated original snapshot differs from trusted report",
    )
    result = {
        key: value
        for key, value in report.items()
        if key not in ("raw_checks_reference", "raw_snapshot_reference")
    }
    result.update(
        raw_checks=checks,
        raw_snapshot=hydrated,
        saved_checkpoint_reference={
            key: value
            for key, value in snapshot_binding.items()
            if key != "hydrated_logical_payload_sha256"
        },
    )
    return result
