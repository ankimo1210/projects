"""Protocol tests keep candidate/frozen lifecycle fixtures explicit."""

import copy
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity/protocol.py"


def module():
    spec = importlib.util.spec_from_file_location("short_protocol_tests", PATH)
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


def test_candidate_declares_rosters_and_fresh_private_seeds():
    m = module()
    p = m.candidate_protocol()
    assert p["state"] == "candidate"
    assert p["teacher_sample_count"] is None
    assert p["splits"] == {"train": 512, "validation": 128, "test": 336}
    assert len(p["pilot"]["cases"]) == 84
    assert p["normal_draw_policy"] == "active_only"
    assert p["fit"]["paired_seeds"] == [11, 29, 47]
    rows = p["seed_ledger"]
    assert len({r["id"] for r in rows}) == len(rows)
    assert len({r["seed"] for r in rows}) == len(rows)
    assert np.allclose(m.validate_protocol(p)["clock"]["weights"], [2, 0.5, 2])
    assert m.seed_for(p, "main/init/11") == 11
    assert m.seed_for(p, "main/teacher/train/0/count") != m.seed_for(p, "main/teacher/train/0/jump")


@pytest.mark.parametrize("split", ["train", "validation", "test"])
def test_candidate_cannot_draw_main_geometry(split, monkeypatch):
    m = module()

    def forbidden(*args, **kwargs):
        raise AssertionError("main RNG used before frozen evidence")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    with pytest.raises(ValueError, match="frozen"):
        m.scenario_inputs(m.candidate_protocol(), split, phase="main")


def test_pilot_geometry_balances_contracts_and_keeps_split_seeds():
    m = module()
    p = m.candidate_protocol()
    a = m.scenario_inputs(p, "train", phase="pilot")
    b = m.scenario_inputs(p, "validation", phase="pilot")
    assert a.shape == (512, 3)
    assert b.shape == (128, 3)
    assert np.sum(a[:, 2] == 1) == 256
    assert np.min(a[:, 1]) >= 60 and np.max(a[:, 1]) <= 390 * 60
    assert not np.allclose(a[:128], b)
    assert np.allclose(a, m.scenario_inputs(p, "train", phase="pilot"))


def test_fixed_test_original_slots_include_all_time_distance_regimes():
    m = module()
    p = m.candidate_protocol()
    rows = m.scenario_inputs(p, "test", phase="pilot")
    assert rows.shape == (336, 3)
    assert set(rows[:, 1] / 60) == {1, 5, 15, 30, 60, 120, 240, 390}
    assert np.sum(rows[:, 2] == 1) == 168
    assert np.sum(np.isclose(rows[:, 0], 100)) == 16


def test_seed_or_roster_tamper_rejected_without_random_sampling():
    m = module()
    p = m.candidate_protocol()
    p["seed_ledger"][1]["seed"] = p["seed_ledger"][0]["seed"]
    with pytest.raises(ValueError, match="seed"):
        m.validate_protocol(p)
    p = m.candidate_protocol()
    p["splits"]["test"] = 335
    with pytest.raises(ValueError, match="roster"):
        m.validate_protocol(p)


def test_source_registry_never_silently_omits_a_required_source(tmp_path, monkeypatch):
    m = module()
    monkeypatch.setattr(m, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="complete"):
        m.source_registry()
    assert m.source_registry(require_complete=False) == {}


def test_unapproved_or_smoke_evidence_cannot_freeze(monkeypatch):
    m = module()
    p = m.candidate_protocol()
    monkeypatch.setattr(m, "source_registry", lambda **kwargs: {s: "fixture" for s in m.SOURCES})
    with pytest.raises(ValueError, match="approved"):
        m.freeze_protocol(p, {}, pilot_record={}, pilot_arrays={})
    review = {"schema": "RB-F05-short-pilot-review-v1", "decision": "approved", "approved": True}
    with pytest.raises(ValueError, match="full"):
        m.freeze_protocol(p, review, pilot_record={"schema": "smoke"}, pilot_arrays={})


def test_array_identity_is_provenance_and_rejects_object_payload():
    m = module()
    a = {"marks": np.asarray([1.0, 2.0])}
    assert m.arrays_digest(a) == m.arrays_digest(copy.deepcopy(a))
    with pytest.raises(ValueError, match="object"):
        m.arrays_digest({"bad": np.asarray([{}], dtype=object)})


@pytest.mark.parametrize(
    "group,key,value",
    [
        ("clock", "annual_sessions", 365),
        ("clock", "carry_days", 360),
        ("clock", "edges", [0.0, 0.2, 0.8, 1.0]),
        ("contract", "pulse_minutes", 15.0),
        ("contract", "pulse_full_mean_count", 0.04),
        ("contract", "pulse_variance", 0.0004),
        ("contract", "timezone", "UTC"),
        ("contract", "session_open", "08:00"),
        ("contract", "session_close", "15:00"),
        ("fit", "widths", [3, 16, 16, 1]),
        ("fit", "gamma_loss", True),
        ("fit", "output", "discounted_intrinsic_residual"),
    ],
)
def test_ignored_hardcoded_conditions_are_rejected(group, key, value):
    m = module()
    p = m.candidate_protocol()
    p[group][key] = value
    with pytest.raises(ValueError, match=r"fixed.*condition"):
        m.validate_protocol(p)


def test_full_original_pilot_and_fit_seed_rosters_required():
    m = module()
    p = m.candidate_protocol()
    p["pilot"]["cases"][0]["distance"] = -3.0
    with pytest.raises(ValueError, match="roster"):
        m.validate_protocol(p)
    p = m.candidate_protocol()
    p["fit"]["paired_seeds"] = [11, 29]
    p["seed_ledger"] = m.build_seed_ledger(p)
    with pytest.raises(ValueError, match="roster"):
        m.validate_protocol(p)
