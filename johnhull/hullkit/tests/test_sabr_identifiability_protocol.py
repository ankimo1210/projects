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
    full = m.noise_for(p, "main", 0, 0)
    atm = full[p["groups"]["atm"]]
    assert np.allclose(atm, m.noise_for(p, "main", 0, 0)[[2, 3, 4]])
    assert not np.allclose(full, m.noise_for(p, "pilot", 0, 0))
    assert len({r["seed"] for r in p["seed_ledger"]}) == len(p["seed_ledger"])


def test_freeze_binds_complete_numeric_contract(monkeypatch):
    m = module()
    p = m.load_protocol()
    monkeypatch.setattr(m, "source_registry", lambda: {name: "fixture" for name in m.SOURCES})
    frozen = m.freeze_protocol(p, {"decision": "approved", "pilot_digest": "fixture"})
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
