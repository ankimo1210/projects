"""Protocol, common-noise slots and immutable source binding for RB-F06."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
SOURCES = (
    "hullkit/src/hullkit/sabr.py",
    "hullkit/src/hullkit/_sabr_identifiability.py",
    "research/RB-F06/protocol.py",
    "research/RB-F06/reference_methods.py",
    "research/RB-F06/build_reference.py",
    "research/RB-F06/analytics.py",
)


def json_digest(value):
    """Canonical JSON identity; not a floating-point numerical acceptance test."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def arrays_digest(arrays):
    """Bind typed saved arrays for provenance, not numerical equivalence."""
    digest = hashlib.sha256()
    for name in sorted(arrays):
        value = np.asarray(arrays[name])
        if value.dtype.hasobject:
            raise ValueError("object arrays forbidden in pilot evidence")
        header = json.dumps([name, value.dtype.str, list(value.shape)], separators=(",", ":"))
        digest.update(header.encode())
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def pilot_bindings(candidate, pilot_record, pilot_arrays):
    """Identify all evidence and conditions approved by the pilot reviewer."""
    return {
        "protocol_digest": json_digest(candidate),
        "pilot_record_digest": json_digest(pilot_record),
        "pilot_arrays_digest": arrays_digest(pilot_arrays),
        "source_registry": source_registry(),
    }


def _runner():
    spec = importlib.util.spec_from_file_location(
        "rbf06_protocol_runner", Path(__file__).with_name("build_reference.py")
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _read_pilot():
    return _runner().load_result(Path(__file__).parent / "pilot")


def _check_pilot_evidence(record, arrays):
    return _runner().check_record(record, arrays, fresh=False)


def _validate_review(candidate, review, bindings):
    if (
        review.get("schema") != "RB-F06-pilot-review-v1"
        or review.get("decision") != "approved"
        or review.get("approved") is not True
    ):
        raise ValueError("typed explicitly approved pilot review required")
    required = {"protocol_digest", "pilot_record_digest", "pilot_arrays_digest", "source_registry"}
    if set(bindings) != required:
        raise ValueError("complete typed pilot review binding required")
    if bindings.get("protocol_digest") != json_digest(candidate) or any(
        review.get(key) != value for key, value in bindings.items()
    ):
        raise ValueError("approved review/pilot/conditions/source binding mismatch")
    if bindings.get("source_registry") != source_registry():
        raise ValueError("review financial source changed")


def _validate_pilot(candidate, record, arrays, review):
    if (
        candidate.get("state") != "candidate"
        or "fixture" in candidate
        or record.get("schema") != "RB-F06-study-v1"
        or record.get("phase") != "pilot"
        or record.get("complete") is not True
        or record.get("teaching_acceptance") is not False
        or record.get("protocol") != candidate
        or record.get("protocol_digest") != json_digest(candidate)
        or record.get("source_registry") != source_registry()
    ):
        raise ValueError("full candidate pilot evidence mismatch; fixture cannot freeze")
    bindings = pilot_bindings(candidate, record, arrays)
    _validate_review(candidate, review, bindings)
    checked = _check_pilot_evidence(record, arrays)
    if not isinstance(checked, dict) or checked.get("passed") is not True:
        raise ValueError("full saved numeric pilot validation required")
    return bindings, checked


def source_registry():
    """Portable project-relative financial implementation identities."""
    return {
        name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
        for name in SOURCES
        if (PROJECT / name).exists()
    }


def noise_for(protocol, phase, truth, rep):
    """Draw one reserved seven-quote master noise vector, shared by nested groups."""
    row = next(
        r
        for r in protocol["seed_ledger"]
        if (r["phase"], r["truth"], r["rep"]) == (phase, truth, rep)
    )
    return np.random.default_rng(row["seed"]).normal(
        0.0, protocol["noise_scale"], len(protocol["log_moneyness"])
    )


def validate_protocol(protocol, require_frozen=False):
    """Check original roster and, when frozen, complete contract/source binding."""
    if protocol["schema"] != "RB-F06-protocol-v1":
        raise ValueError("unknown protocol")
    seeds = [r["seed"] for r in protocol["seed_ledger"]]
    if len(seeds) != len(set(seeds)):
        raise ValueError("reserved seed collision")
    if protocol["noise_scale"] <= 0 or protocol["solver_call_cap"] != sum(
        protocol["solver_call_roster"].values()
    ):
        raise ValueError("invalid scale or cost roster")
    if require_frozen:
        frozen = protocol.get("frozen")
        content = {key: value for key, value in protocol.items() if key != "frozen"}
        if not frozen or frozen["digest"] != json_digest(content):
            raise ValueError("frozen numeric contract changed")
        registry = source_registry()
        if set(registry) != set(SOURCES) or set(frozen["source_registry"]) != set(SOURCES):
            raise ValueError("complete frozen financial source registry required")
        if frozen["source_registry"] != registry:
            raise ValueError("frozen financial source changed")
        candidate = copy.deepcopy(content)
        candidate["state"] = "candidate"
        review = frozen.get("pilot_review", {})
        _validate_review(candidate, review, frozen.get("pilot_binding", {}))
        if frozen.get("pilot_review_digest") != json_digest(review):
            raise ValueError("frozen pilot review changed")
    return protocol


def load_protocol(path=None, require_frozen=False):
    """Load candidate or reviewed frozen conditions without drawing any noise."""
    path = Path(path) if path is not None else Path(__file__).with_name("protocol.json")
    result = validate_protocol(json.loads(path.read_text()), require_frozen=require_frozen)
    if require_frozen:
        verify_frozen_evidence(result)
    return result


def freeze_protocol(protocol, review, *, pilot_record=None, pilot_arrays=None):
    """Freeze only a typed approval of the complete numerically checked pilot."""
    registry = source_registry()
    if set(registry) != set(SOURCES):
        raise ValueError("complete financial source registry required")
    if review.get("decision") != "approved" or review.get("approved") is not True:
        raise ValueError("approved independent pilot review required")
    if pilot_record is None or pilot_arrays is None:
        raise ValueError("saved pilot record and arrays required")
    validate_protocol(protocol)
    bindings, checked = _validate_pilot(protocol, pilot_record, pilot_arrays, review)
    result = copy.deepcopy(protocol)
    result["state"] = "frozen"
    result["frozen"] = {
        "digest": json_digest(result),
        "source_registry": registry,
        "pilot_binding": bindings,
        "pilot_validation": checked,
        "pilot_review": copy.deepcopy(review),
        "pilot_review_digest": json_digest(review),
    }
    validate_protocol(result, require_frozen=True)
    return result


def verify_frozen_evidence(protocol):
    """Recheck the actual saved pilot, typed approval and numeric source binding."""
    validate_protocol(protocol, require_frozen=True)
    candidate = copy.deepcopy(protocol)
    frozen = candidate.pop("frozen")
    candidate["state"] = "candidate"
    record, arrays = _read_pilot()
    bindings, checked = _validate_pilot(candidate, record, arrays, frozen["pilot_review"])
    if bindings != frozen["pilot_binding"] or checked != frozen["pilot_validation"]:
        raise ValueError("saved pilot evidence differs from frozen approval")
    return checked
