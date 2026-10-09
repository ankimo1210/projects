"""Frozen study roster and common-noise semantics for RB-F06."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2] / "research" / "RB-F06"


def module():
    path = ROOT / "protocol.py"
    assert path.exists(), "RB-F06 protocol implementation missing"
    spec = importlib.util.spec_from_file_location("rbf06_protocol_test", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_main_roster_preserves_original_denominators():
    p = module().load_protocol()
    assert len(p["truths"]) * len(p["groups"]) * (p["main_reps"] + 1) * len(p["starts"]) == 918
    assert p["solver_call_cap"] == 4830
    assert p["noise_scale"] == pytest.approx(5e-4)
    assert set(p["groups"]["sparse"]) == {1, 5}


def test_common_master_noise_and_phase_independence():
    m = module()
    p = m.load_protocol()
    p = copy.deepcopy(p)
    for row in p["seed_ledger"]:
        row["seed"] = (row["seed"] + 101) % (2**32)
    full = m.noise_for(p, "main", 0, 0)
    atm = full[p["groups"]["atm"]]
    assert np.allclose(atm, m.noise_for(p, "main", 0, 0)[[2, 3, 4]])
    assert not np.allclose(full, m.noise_for(p, "pilot", 0, 0))
    assert len({r["seed"] for r in p["seed_ledger"]}) == len(p["seed_ledger"])


def test_freeze_binds_complete_numeric_contract(monkeypatch):
    m = module()
    p = m.load_protocol()
    p.pop("frozen", None)
    p["state"] = "candidate"
    monkeypatch.setattr(m, "source_registry", lambda: {name: "fixture" for name in m.SOURCES})
    monkeypatch.setattr(m, "_check_pilot_evidence", lambda r, a: {"passed": True})
    record, arrays, review = reviewed(m, p)
    frozen = m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)
    m.validate_protocol(frozen, require_frozen=True)
    changed = copy.deepcopy(frozen)
    changed["noise_scale"] *= 2
    with pytest.raises(ValueError, match="frozen"):
        m.validate_protocol(changed, require_frozen=True)


def test_unreviewed_pilot_cannot_freeze():
    m = module()
    with pytest.raises(ValueError, match="approved"):
        m.freeze_protocol(m.load_protocol(), {"decision": "pending"})


def test_incomplete_financial_registry_cannot_freeze(monkeypatch):
    m = module()
    monkeypatch.setattr(m, "source_registry", lambda: {name: "fixture" for name in m.SOURCES[1:]})
    with pytest.raises(ValueError, match="complete"):
        m.freeze_protocol(m.load_protocol(), {"decision": "approved"})


def test_frozen_load_rejects_self_consistent_incomplete_registry(monkeypatch):
    m = module()
    partial = {name: "fixture" for name in m.SOURCES[1:]}
    monkeypatch.setattr(m, "source_registry", lambda: partial)
    p = m.load_protocol()
    p["state"] = "frozen"
    p["frozen"] = {"digest": m.json_digest(p), "source_registry": partial}
    with pytest.raises(ValueError, match="complete"):
        m.validate_protocol(p, require_frozen=True)


def reviewed(m, p):
    """Typed unit metadata; caller stubs numeric auditing separately."""
    arrays = {"toy": np.array([0.2, -0.3, 0.4])}
    record = {
        "schema": "RB-F06-study-v1",
        "phase": "pilot",
        "complete": True,
        "teaching_acceptance": False,
        "protocol": copy.deepcopy(p),
        "protocol_digest": m.json_digest(p),
        "source_registry": m.source_registry(),
    }
    review = {
        "schema": "RB-F06-pilot-review-v1",
        "decision": "approved",
        "approved": True,
        **m.pilot_bindings(p, record, arrays),
    }
    return record, arrays, review


@pytest.fixture
def evidence(monkeypatch):
    m = module()
    p = m.load_protocol()
    p.pop("frozen", None)
    p["state"] = "candidate"
    monkeypatch.setattr(m, "_check_pilot_evidence", lambda r, a: {"passed": True})
    record, arrays, review = reviewed(m, p)
    return m, p, record, arrays, review


@pytest.mark.parametrize(
    "field", ["protocol_digest", "pilot_record_digest", "pilot_arrays_digest", "source_registry"]
)
def test_wrong_typed_review_binding_cannot_freeze(evidence, field):
    m, p, record, arrays, review = evidence
    review[field] = {} if field == "source_registry" else "wrong"
    with pytest.raises(ValueError, match="review"):
        m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)


@pytest.mark.parametrize(
    "patch", [{"approved": False}, {"schema": "generic-review"}, {"decision": "pending"}]
)
def test_explicit_typed_approval_is_required(evidence, patch):
    m, p, record, arrays, review = evidence
    review.update(patch)
    with pytest.raises(ValueError, match="approved"):
        m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)


def test_changed_candidate_rejects_old_pilot_approval(evidence):
    m, p, record, arrays, review = evidence
    p["noise_scale"] *= 2
    with pytest.raises(ValueError, match=r"pilot|review"):
        m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)


@pytest.mark.parametrize(
    "patch",
    [
        {"phase": "fixture"},
        {"complete": False},
        {"protocol": {"fixture": {"explicit": True}}},
    ],
)
def test_nonpilot_or_incomplete_evidence_cannot_freeze(evidence, patch):
    m, p, record, arrays, review = evidence
    record.update(patch)
    review.update(m.pilot_bindings(p, record, arrays))
    with pytest.raises(ValueError, match="pilot"):
        m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)


def test_full_saved_numeric_audit_is_required(evidence, monkeypatch):
    m, p, record, arrays, review = evidence
    monkeypatch.setattr(m, "_check_pilot_evidence", lambda r, a: {"passed": False})
    with pytest.raises(ValueError, match="numeric"):
        m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)


def test_frozen_load_rechecks_review_binding(evidence):
    m, p, record, arrays, review = evidence
    frozen = m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)
    m.validate_protocol(frozen, require_frozen=True)
    frozen["frozen"]["pilot_review"]["approved"] = False
    with pytest.raises(ValueError, match=r"review|approved"):
        m.validate_protocol(frozen, require_frozen=True)


def test_frozen_evidence_checks_actual_saved_pilot(evidence, monkeypatch):
    m, p, record, arrays, review = evidence
    frozen = m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)
    monkeypatch.setattr(m, "_read_pilot", lambda: (record, arrays))
    m.verify_frozen_evidence(frozen)
    changed = copy.deepcopy(record)
    changed["complete"] = False
    monkeypatch.setattr(m, "_read_pilot", lambda: (changed, arrays))
    with pytest.raises(ValueError, match=r"pilot|review"):
        m.verify_frozen_evidence(frozen)


def test_freeze_refuses_missing_saved_pilot(evidence):
    m, p, _, _, review = evidence
    with pytest.raises(ValueError, match="pilot"):
        m.freeze_protocol(p, review)


def test_frozen_metadata_requires_all_pilot_binding_fields(evidence):
    m, p, record, arrays, review = evidence
    frozen = m.freeze_protocol(p, review, pilot_record=record, pilot_arrays=arrays)
    del frozen["frozen"]["pilot_binding"]["pilot_record_digest"]
    with pytest.raises(ValueError, match="complete"):
        m.validate_protocol(frozen, require_frozen=True)
