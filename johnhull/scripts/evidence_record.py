"""Schema-2 recheck records: a run's decision, fingerprint and store-backed images.

A record either **redraws** (new captures stored in both artifact-store copies)
or **reuses** a baseline. A reused record points directly at a redrawn schema-2
record, carries exactly its images and must match its fingerprint digest and
the runtime facts observed in the browser. Chains of reuse are rejected so the
original captures are always one hop away. Existing schema-1 records are left
to the ledger checker's original code path.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

try:
    from . import evidence_store
except ImportError:  # executed as a script from johnhull/scripts
    import evidence_store

KIND = "johnhull-section-recheck"
DECISIONS = ("redrawn", "reused")
RUNTIME_KEYS = ("browser_version", "mathjax_version", "fonts")
REQUIRED_FIELDS = (
    "schema_version",
    "kind",
    "status",
    "run_id",
    "created_at",
    "commit",
    "dirty",
    "section_id",
    "decision",
    "reasons",
    "dependency_fingerprint",
    "baseline",
    "images",
    "checks",
    "environment",
    "storage_verification",
    "source_sha256",
    "artifact_sha256",
)
OPTIONAL_FIELDS = ("observations",)
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_problems(record: dict) -> list[str]:
    """Problems that can be judged from the record alone."""
    problems = []
    checks = record.get("checks")
    if not isinstance(checks, dict) or not checks:
        problems.append("checks: expected at least one named check")
    else:
        for name, check in checks.items():
            if not isinstance(check, dict) or check.get("status") not in ("PASS", "FAIL"):
                problems.append(f"checks.{name}: expected status PASS or FAIL")
            elif check["status"] != "PASS":
                problems.append(f"checks.{name}: status is {check['status']}")
    storage = record.get("storage_verification")
    if not isinstance(storage, dict) or storage.get("status") != "PASS":
        problems.append("storage_verification: both copies must restore and match (status PASS)")
    elif any(
        not isinstance(storage.get(role), dict) or storage[role].get("status") != "PASS"
        for role in ("primary", "mirror")
    ):
        problems.append("storage_verification: primary and mirror must each be PASS")
    images = record.get("images")
    if not isinstance(images, list) or not images:
        problems.append("images: a record needs at least one image reference")
    fingerprint = record.get("dependency_fingerprint")
    if not isinstance(fingerprint, dict):
        problems.append("dependency_fingerprint: expected an object")
    elif record.get("decision") == "reused" and fingerprint.get("unknown"):
        problems.append("dependency_fingerprint: unknown dependencies prevent reuse")
    if record.get("decision") == "reused" and not isinstance(record.get("baseline"), dict):
        problems.append("baseline: a reused record needs a direct baseline reference")
    return problems


def build_record(
    *,
    run_id: str,
    created_at: str,
    commit: str,
    dirty: bool,
    section_id: str,
    decision: str,
    reasons: list[str],
    fingerprint: dict,
    baseline: dict | None,
    images: list[dict],
    checks: dict,
    environment: dict,
    storage_verification: dict,
    source_sha256: dict,
    artifact_sha256: dict,
    observations: dict | None = None,
) -> dict:
    record = {
        "schema_version": 2,
        "kind": KIND,
        "status": "FAIL",
        "run_id": run_id,
        "created_at": created_at,
        "commit": commit,
        "dirty": dirty,
        "section_id": section_id,
        "decision": decision,
        "reasons": list(reasons),
        "dependency_fingerprint": fingerprint,
        "baseline": baseline,
        "images": images,
        "checks": checks,
        "environment": environment,
        "storage_verification": storage_verification,
        "source_sha256": source_sha256,
        "artifact_sha256": artifact_sha256,
    }
    if observations is not None:
        record["observations"] = observations
    record["status"] = "FAIL" if _local_problems(record) else "PASS"
    return record


def baseline_ref(project: Path | str, record_path: str) -> dict:
    """Direct reference to a saved record: project-relative path, digest and run id."""
    project = Path(project)
    path = project / evidence_store.validate_relative_path(record_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    return {"record": record_path, "record_sha256": _sha256_file(path), "run_id": record["run_id"]}


def _schema_problems(record: dict) -> list[str]:
    problems = []
    unknown = sorted(set(record) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    missing = sorted(set(REQUIRED_FIELDS) - set(record))
    if unknown:
        problems.append(f"record: unknown fields {unknown}")
    if missing:
        problems.append(f"record: missing fields {missing}")
    if record.get("schema_version") != 2:
        problems.append("record.schema_version: expected 2")
    if record.get("kind") != KIND:
        problems.append(f"record.kind: expected {KIND!r}")
    for name in ("run_id", "section_id"):
        if not isinstance(record.get(name), str) or not record.get(name):
            problems.append(f"record.{name}: expected a non-empty string")
    try:
        datetime.fromisoformat(str(record.get("created_at")))
    except ValueError:
        problems.append("record.created_at: expected an ISO timestamp")
    if not isinstance(record.get("commit"), str) or not _COMMIT_RE.fullmatch(record["commit"]):
        problems.append("record.commit: expected a full 40-character commit")
    if not isinstance(record.get("dirty"), bool):
        problems.append("record.dirty: expected a boolean")
    if record.get("decision") not in DECISIONS:
        problems.append(f"record.decision: expected one of {DECISIONS}")
    reasons = record.get("reasons")
    if not isinstance(reasons, list) or any(not isinstance(item, str) for item in reasons):
        problems.append("record.reasons: expected a list of strings")
    fingerprint = record.get("dependency_fingerprint")
    if isinstance(fingerprint, dict):
        digest = fingerprint.get("digest")
        if digest is not None and (not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest)):
            problems.append("dependency_fingerprint.digest: expected sha256 or null")
        if not isinstance(fingerprint.get("unknown"), list):
            problems.append("dependency_fingerprint.unknown: expected a list")
    if not isinstance(record.get("environment"), dict) or not isinstance(
        record["environment"].get("runtime"), dict
    ):
        problems.append("environment.runtime: expected an object")
    try:
        evidence_store.validate_entries(record.get("images"), "images")
    except evidence_store.StoreError as exc:
        problems.append(str(exc))
    return problems


def _baseline_problems(project: Path, record: dict) -> list[str]:
    baseline = record.get("baseline")
    if baseline is None:
        return []
    if not isinstance(baseline, dict) or set(baseline) != {"record", "record_sha256", "run_id"}:
        return ["baseline: expected {record, record_sha256, run_id}"]
    try:
        relative = evidence_store.validate_relative_path(baseline["record"])
    except evidence_store.StoreError as exc:
        return [f"baseline.record: {exc}"]
    path = project.joinpath(*relative.parts)
    if not path.resolve(strict=False).is_relative_to(project.resolve()) or not path.is_file():
        return [f"baseline.record: file does not exist in the project: {baseline['record']!r}"]
    if _sha256_file(path) != baseline["record_sha256"]:
        return ["baseline.record_sha256: digest does not match the saved baseline record"]
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return [f"baseline.record: invalid JSON: {exc}"]
    if not isinstance(saved, dict) or saved.get("schema_version") != 2:
        return ["baseline.record: must be a schema-2 record"]
    problems = []
    if saved.get("run_id") != baseline["run_id"]:
        problems.append("baseline.run_id: does not match the saved record")
    if saved.get("status") != "PASS":
        problems.append("baseline.record: status must be PASS")
    if record.get("decision") != "reused":
        return problems
    if saved.get("decision") != "redrawn":
        problems.append("baseline: reuse chain (the baseline is itself a reused record)")
    ours = record.get("dependency_fingerprint") or {}
    theirs = saved.get("dependency_fingerprint") or {}
    if ours.get("digest") is None or ours.get("digest") != theirs.get("digest"):
        problems.append("dependency_fingerprint: digest differs from the baseline")
    if record.get("images") != saved.get("images"):
        problems.append("images: reused images differ from the baseline's images")
    runtime = (record.get("environment") or {}).get("runtime") or {}
    saved_runtime = (saved.get("environment") or {}).get("runtime") or {}
    for key in RUNTIME_KEYS:
        if runtime.get(key) is None or runtime.get(key) != saved_runtime.get(key):
            problems.append(f"environment.runtime.{key}: differs from the baseline run")
    return problems


def _artifact_problems(record: dict, stores) -> list[str]:
    if stores is None:
        try:
            stores = (
                evidence_store.store_from_env("PROJECTS_ARTIFACT_STORE", role="primary"),
                evidence_store.store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror"),
            )
        except evidence_store.StoreError as exc:
            return [f"images: UNVERIFIED, artifact store not available: {exc}"]
    problems = []
    for entry in record.get("images") or []:
        digest = evidence_store.parse_ref(entry["ref"])
        for store in stores:
            try:
                store.read_verified(digest, entry["bytes"])
            except evidence_store.StoreError as exc:
                problems.append(f"images {entry['path']}: {exc}")
    return problems


def validate_record(
    project: Path | str, record: dict, *, check_artifacts: bool = False, stores=None
) -> list[str]:
    """Return every problem with a schema-2 record (empty when it is valid and PASS)."""
    project = Path(project)
    if not isinstance(record, dict):
        return ["record: top level must be an object"]
    problems = _schema_problems(record)
    local = _local_problems(record)
    problems.extend(local)
    problems.extend(_baseline_problems(project, record))
    expected = "FAIL" if local else "PASS"
    if record.get("status") != expected:
        problems.append(
            f"record.status: claims {record.get('status')!r}, evaluates to {expected!r}"
        )
    elif expected != "PASS":
        problems.append("record must have top-level status=PASS")
    if check_artifacts:
        problems.extend(_artifact_problems(record, stores))
    return problems
