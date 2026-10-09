"""Frozen F08 conditions, stream collision audit and typed ledger contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research/RB-F08"


@pytest.fixture(scope="module")
def protocol():
    spec = importlib.util.spec_from_file_location("rbf08_protocol_test", HERE / "protocol.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_candidate_cannot_run_main(protocol):
    candidate = protocol.candidate_protocol()
    protocol.validate_protocol(candidate)
    with pytest.raises(ValueError, match="frozen"):
        protocol.validate_protocol(candidate, require_frozen=True)
    candidate["state"] = "frozen"
    with pytest.raises(ValueError, match=r"pilot|review|fingerprint"):
        protocol.validate_protocol(candidate, require_frozen=True)


def test_forced_uint32_collision_is_resolved_and_audited(protocol):
    logical = [
        {"logical_id": "a", "phase": "pilot", "entropy": [83101], "logical_spawn_key": [0]},
        {"logical_id": "b", "phase": "coverage", "entropy": [83301], "logical_spawn_key": [0]},
    ]
    rows = protocol.resolve_seed_roster(
        logical, candidate_seed_fn=lambda row, retry: 100 if retry == 0 else 101
    )
    assert [row["raw_seed"] for row in rows] == [100, 100]
    assert [row["seed"] for row in rows] == [100, 101]
    assert [row["retry_count"] for row in rows] == [0, 1]
    assert rows[1]["candidate_seeds"] == [100, 101]
    assert rows[1]["spawn_key"] == [0, 1]


def test_duplicate_logical_child_is_rejected(protocol):
    row = {"logical_id": "a", "phase": "pilot", "entropy": [83101], "logical_spawn_key": [0]}
    with pytest.raises(ValueError, match="duplicate"):
        protocol.resolve_seed_roster([row, copy.deepcopy(row)])
    other = {**row, "logical_id": "b"}
    with pytest.raises(ValueError, match="duplicate"):
        protocol.resolve_seed_roster([row, other])


def test_seed_roster_reads_stored_rows_without_generating(protocol, monkeypatch):
    rows = protocol.resolve_seed_roster(
        [
            {
                "logical_id": "pilot.l0",
                "phase": "pilot",
                "entropy": [83101],
                "logical_spawn_key": [0, 0],
            },
            {
                "logical_id": "main.l0",
                "phase": "main",
                "entropy": [83201],
                "logical_spawn_key": [0, 0],
            },
        ]
    )
    monkeypatch.setattr(protocol, "_candidate_seed", lambda *_: pytest.fail("seed generation"))
    assert protocol.seed_roster({"seed_ledger": rows}, "pilot") == rows[:1]


def test_candidate_json_has_all_fixed_numbers(protocol):
    candidate = protocol.candidate_protocol()
    assert candidate["schema"] == "RB-F08-mlmc-rqmc-v1"
    assert candidate["epsilon"] == [0.4, 0.2, 0.1]
    assert candidate["main"]["outer_runs"] == 256
    assert candidate["rqmc"]["outer_runs"] == 512
    assert candidate["pilot"]["levels"] == list(range(9))
    assert candidate["pilot"]["paths_per_stream"] == 16384
    assert candidate["pilot"]["streams"] == 3
    assert candidate["phase_roots"] == dict(
        zip(
            ["pilot", "main", "coverage", "fresh_review", "timing", "method_order", "bootstrap"],
            range(83101, 83702, 100),
            strict=True,
        )
    )
    assert candidate["caps"] == {"paths_per_run": 2000000, "steps_per_run": 100000000}
    assert candidate["bootstrap"]["resamples"] == 2000
    assert candidate["threads"] == {
        "OPENBLAS_NUM_THREADS": 1,
        "OMP_NUM_THREADS": 1,
        "MKL_NUM_THREADS": 1,
    }


def test_saved_protocol_conditions_match_declared_candidates(protocol):
    saved = json.loads((HERE / "protocol.json").read_text())
    expected = protocol.protocol_for_json(protocol.candidate_protocol())
    assert saved["state"] in {"candidate", "frozen"}
    # Publication adds evidence and the ledger registry after the full pilot.
    for key, value in expected.items():
        if key not in {"state", "seed_ledger_meta"}:
            assert saved[key] == value


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("maturity", 0),
        ("sigma", -0.1),
        ("rate", float("nan")),
    ],
)
def test_invalid_product_is_rejected(protocol, key, value):
    candidate = protocol.candidate_protocol()
    candidate["parameters"][key] = value
    with pytest.raises(ValueError):
        protocol.validate_protocol(candidate)


def test_zero_sigma_and_nonzero_yield_are_valid(protocol):
    candidate = protocol.candidate_protocol()
    candidate["parameters"].update(sigma=0, yield_rate=0.02)
    protocol.validate_protocol(candidate)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("main", "outer_runs", True),
        ("rqmc", "outer_runs", 0),
        ("rqmc", "powers", [8, 8]),
        ("rqmc", "scrambles", [1, 16, 32]),
        ("timing", "measured_repetitions", 0),
        ("caps", "paths_per_run", -1),
    ],
)
def test_invalid_integer_roster_is_rejected(protocol, section, key, value):
    candidate = protocol.candidate_protocol()
    candidate[section][key] = value
    with pytest.raises(ValueError):
        protocol.validate_protocol(candidate)


def test_duplicate_phase_root_and_bad_clip_are_rejected(protocol):
    candidate = protocol.candidate_protocol()
    candidate["phase_roots"]["main"] = candidate["phase_roots"]["pilot"]
    with pytest.raises(ValueError, match="phase"):
        protocol.validate_protocol(candidate)
    candidate = protocol.candidate_protocol()
    candidate["rqmc"]["clip"]["lower"] = 0.1
    with pytest.raises(ValueError, match="clip"):
        protocol.validate_protocol(candidate)


def test_missing_cost_definition_is_rejected(protocol):
    candidate = protocol.candidate_protocol()
    candidate["cost_definition"].pop("level_positive")
    with pytest.raises(ValueError, match="cost"):
        protocol.validate_protocol(candidate)


def test_candidate_cannot_enable_torch_or_change_public_apis(protocol):
    candidate = protocol.candidate_protocol()
    candidate["constraints"]["torch"] = True
    with pytest.raises(ValueError, match="constraint"):
        protocol.validate_protocol(candidate)
    candidate = protocol.candidate_protocol()
    candidate["constraints"]["public_api_changes"] = True
    with pytest.raises(ValueError, match="constraint"):
        protocol.validate_protocol(candidate)


def test_typed_small_ledger_roundtrip_without_pickle(protocol, tmp_path):
    rows = protocol.resolve_seed_roster(
        [
            {
                "logical_id": "pilot.l0",
                "phase": "pilot",
                "entropy": [83101],
                "logical_spawn_key": [0, 0],
            },
            {
                "logical_id": "main.l0",
                "phase": "main",
                "entropy": [83201],
                "logical_spawn_key": [0, 0],
            },
        ]
    )
    arrays = protocol.pack_seed_ledger(rows)
    assert all(array.dtype.kind != "O" for array in arrays.values())
    path = tmp_path / "ledger.npz"
    np.savez_compressed(path, **arrays)
    with np.load(path, allow_pickle=False) as stored:
        assert protocol.unpack_seed_ledger(dict(stored)) == rows


@pytest.fixture(scope="module")
def full_candidate(protocol):
    candidate = protocol.candidate_protocol()
    rows = protocol.build_seed_ledger(candidate)
    return protocol.attach_seed_ledger(candidate, rows)


def test_real_ledger_covers_all_slots_and_resolves_collisions(protocol, full_candidate):
    rows = full_candidate["seed_ledger"]
    assert len(protocol.seed_roster(full_candidate, "coverage")) == 172032
    assert len(protocol.seed_roster(full_candidate, "main")) == 9216
    assert len(protocol.seed_roster(full_candidate, "fresh_review")) == 372
    assert len({row["seed"] for row in rows}) == len(rows)
    assert len({row["logical_id"] for row in rows}) == len(rows)
    assert any(row["retry_count"] > 0 for row in rows)
    for budget in range(3):
        found = {
            row["level"]
            for row in protocol.seed_roster(full_candidate, "main")
            if row["budget"] == budget and row["method"] == "mlmc"
        }
        assert found == set(range(9))
    protocol.validate_protocol(full_candidate)


def test_json_hydrate_is_digest_bound(protocol, full_candidate):
    arrays = protocol.pack_seed_ledger(full_candidate["seed_ledger"])
    saved = protocol.protocol_for_json(full_candidate)
    assert "seed_ledger" not in saved
    restored = protocol.hydrate_protocol(saved, arrays)
    assert restored["seed_ledger_meta"] == full_candidate["seed_ledger_meta"]
    changed = {name: value.copy() for name, value in arrays.items()}
    changed["seed_ledger_seed"][0] ^= np.uint32(1)
    with pytest.raises(ValueError, match=r"digest|ledger"):
        protocol.hydrate_protocol(saved, changed)


def _source(protocol):
    source = {
        "files": {name: "a" * 64 for name in protocol.SOURCE_FILES},
        "dependencies": {"python": "3.12.3", "numpy": np.__version__, "scipy": "1.17.1"},
    }
    source["digest"] = protocol.json_digest(source)
    return source


def _freeze_evidence(protocol, candidate, monkeypatch):
    conditions = protocol.protocol_conditions(candidate)
    arrays = {
        "observations": np.array([1.0, 2.0, 3.0]),
        **protocol.pack_seed_ledger(candidate["seed_ledger"]),
    }
    source = _source(protocol)
    allocations = {
        "0.4": {"status": "ready", "level": 2, "paths": [32, 32, 32]},
        "0.2": {"status": "ready", "level": 3, "paths": [64] * 4},
        "0.1": {"status": "bias_unresolved", "reason": "pilot upper envelope"},
    }
    record = {
        "schema": "RB-F08-pilot-v1",
        "mode": "full",
        "protocol_digest": protocol.json_digest(conditions),
        "seed_ledger_digest": candidate["seed_ledger_meta"]["digest"],
        "source_fingerprint": source["digest"],
        "allocations": allocations,
        "cv_beta": 0.7,
    }
    review = {
        "decision": "approved",
        "pilot_record_digest": protocol.json_digest(record),
        "pilot_arrays_digest": protocol.arrays_digest(arrays),
        "protocol_digest": record["protocol_digest"],
        "seed_ledger_digest": record["seed_ledger_digest"],
        "source_fingerprint": source["digest"],
        "approved_conditions": conditions,
        "approved_allocations": allocations,
        "approved_cv_beta": 0.7,
    }
    monkeypatch.setattr(protocol, "validate_pilot_evidence", lambda *_: {"passed": True})
    return record, arrays, review, source


def test_full_approved_pilot_can_freeze(protocol, freeze_candidate, monkeypatch):
    record, arrays, review, source = _freeze_evidence(protocol, freeze_candidate, monkeypatch)
    frozen = protocol.freeze_protocol(freeze_candidate, record, arrays, review, source=source)
    assert frozen["state"] == "frozen"
    assert freeze_candidate["state"] == "candidate"
    assert frozen["frozen"]["allocations"] == record["allocations"]
    assert frozen["frozen"]["cv_beta"] == pytest.approx(0.7)
    protocol.validate_protocol(frozen, require_frozen=True)
    protocol.verify_frozen_source(frozen, source)


@pytest.mark.parametrize("field", ["seed", "coverage", "main", "cap", "clip", "cost"])
def test_mutating_any_frozen_condition_is_rejected(
    protocol,
    freeze_candidate,
    monkeypatch,
    field,
):
    record, arrays, review, source = _freeze_evidence(protocol, freeze_candidate, monkeypatch)
    frozen = protocol.freeze_protocol(freeze_candidate, record, arrays, review, source=source)
    if field == "seed":
        frozen["seed_ledger"][0]["seed"] ^= 1
    elif field == "coverage":
        frozen["rqmc"]["outer_runs"] -= 1
    elif field == "main":
        frozen["main"]["outer_runs"] -= 1
    elif field == "cap":
        frozen["caps"]["paths_per_run"] += 1
    elif field == "clip":
        frozen["rqmc"]["clip"]["upper"] = 1.0
    else:
        frozen["cost_definition"]["level_positive"]["normals"] = "2*M_l*N"
    with pytest.raises(ValueError):
        protocol.validate_protocol(frozen, require_frozen=True)


@pytest.mark.parametrize(
    "field",
    ["smoke", "record", "arrays", "review", "conditions", "allocations", "source", "pilot_fail"],
)
def test_freeze_requires_full_verified_matching_pilot(
    protocol,
    freeze_candidate,
    monkeypatch,
    field,
):
    record, arrays, review, source = _freeze_evidence(protocol, freeze_candidate, monkeypatch)
    if field == "smoke":
        record["mode"] = "smoke"
    elif field == "record":
        review["pilot_record_digest"] = "b" * 64
    elif field == "arrays":
        arrays["observations"][0] += 1
    elif field == "review":
        review["decision"] = "rejected"
    elif field == "conditions":
        review["approved_conditions"]["main"]["outer_runs"] -= 1
    elif field == "allocations":
        review["approved_allocations"] = {}
    elif field == "source":
        source["dependencies"]["scipy"] = "bad"
    else:
        monkeypatch.setattr(protocol, "validate_pilot_evidence", lambda *_: {"passed": False})
    with pytest.raises(ValueError):
        protocol.freeze_protocol(freeze_candidate, record, arrays, review, source=source)


def test_fixed_source_registry_and_actual_file_fingerprint(protocol, tmp_path):
    file = tmp_path / "source.py"
    file.write_text("value = 1\n")
    first = protocol.source_fingerprint([file])
    file.write_text("value = 2\n")
    second = protocol.source_fingerprint([file])
    assert first["digest"] != second["digest"]
    assert set(first["dependencies"]) == {"python", "numpy", "scipy"}


@pytest.fixture(scope="module")
def freeze_candidate(protocol):
    candidate = protocol.candidate_protocol()
    candidate["pilot"]["levels"] = [0, 1, 2]
    candidate["main"].update(outer_runs=4, levels_reserved=[0, 1, 2])
    candidate["rqmc"].update(outer_runs=4, powers=[3], scrambles=[4])
    candidate["fresh_review"]["coverage_replay_runs"] = [0, 1, 3]
    return protocol.attach_seed_ledger(candidate, protocol.build_seed_ledger(candidate))


def test_saved_pilot_and_review_recheck_frozen_evidence(
    protocol,
    freeze_candidate,
    monkeypatch,
):
    record, arrays, review, source = _freeze_evidence(protocol, freeze_candidate, monkeypatch)
    frozen = protocol.freeze_protocol(freeze_candidate, record, arrays, review, source=source)
    protocol.verify_frozen_evidence(frozen, record, arrays, review, source=source)
    arrays["observations"][0] += 0.01
    with pytest.raises(ValueError):
        protocol.verify_frozen_evidence(frozen, record, arrays, review, source=source)


def test_typed_ledger_rejects_floating_seed_columns(protocol):
    rows = protocol.resolve_seed_roster(
        [
            {
                "logical_id": "pilot.a",
                "phase": "pilot",
                "entropy": [83101],
                "logical_spawn_key": [0],
            },
        ]
    )
    arrays = protocol.pack_seed_ledger(rows)
    arrays["seed_ledger_seed"] = arrays["seed_ledger_seed"].astype(float) + 0.25
    with pytest.raises(ValueError, match=r"dtype|typed"):
        protocol.unpack_seed_ledger(arrays)


def test_frozen_source_change_rejected(protocol, freeze_candidate, monkeypatch):
    record, arrays, review, source = _freeze_evidence(protocol, freeze_candidate, monkeypatch)
    frozen = protocol.freeze_protocol(freeze_candidate, record, arrays, review, source=source)
    source["files"][protocol.SOURCE_FILES[0]] = "b" * 64
    source["digest"] = protocol.json_digest({k: v for k, v in source.items() if k != "digest"})
    with pytest.raises(ValueError, match="source"):
        protocol.verify_frozen_source(frozen, source)


def test_nonzero_yield_control_and_fresh_replay_bounds_are_validated(protocol):
    candidate = protocol.candidate_protocol()
    candidate["parameters"]["yield_rate"] = 0.02
    candidate["main"]["cv_expectation"] = "S0"
    with pytest.raises(ValueError, match=r"dividend|expectation"):
        protocol.validate_protocol(candidate)
    candidate = protocol.candidate_protocol()
    candidate["fresh_review"]["coverage_replay_runs"] = [512]
    with pytest.raises(ValueError, match=r"fresh|replay"):
        protocol.validate_protocol(candidate)


def test_phase_root_and_rqmc_axis_audit_match_fixed_roster(protocol, freeze_candidate):
    candidate = copy.deepcopy(freeze_candidate)
    candidate["seed_ledger"][0]["budget"] = 8
    candidate["seed_ledger_meta"] = protocol.attach_seed_ledger(
        protocol.candidate_protocol(), candidate["seed_ledger"]
    )["seed_ledger_meta"]
    with pytest.raises(ValueError, match=r"roster|reservation"):
        protocol.validate_protocol(candidate)


@pytest.mark.parametrize("field", ["raw_seed", "retry_count", "spawn_key", "candidate_seeds"])
def test_seed_collision_audit_tampering_is_rejected(protocol, field):
    rows = protocol.resolve_seed_roster(
        [
            {
                "logical_id": "pilot.a",
                "phase": "pilot",
                "entropy": [83101],
                "logical_spawn_key": [0],
            },
        ]
    )
    if field == "raw_seed":
        rows[0][field] ^= 1
    elif field == "retry_count":
        rows[0][field] += 1
    else:
        rows[0][field][0] ^= 1
    with pytest.raises(ValueError, match=r"audit|seed|spawn|retry"):
        protocol.validate_seed_ledger(rows)


def test_clip_comparison_has_reserved_pilot_stream_and_frozen_conditions(protocol):
    p = protocol.candidate_protocol()
    rows = protocol.build_seed_ledger(p)
    selected = [
        row for row in rows if row["phase"] == "pilot" and row["method"] == "clip_diagnostic"
    ]
    assert len(selected) == 1
    assert p["clip_diagnostic"]["power"] == 10
    assert p["clip_diagnostic"]["public_clip"] == pytest.approx([1e-10, 1 - 1e-10])
    assert len(rows) == 181729
