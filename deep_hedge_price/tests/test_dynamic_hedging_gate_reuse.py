"""Saved-evidence reuse inside teacher gates: same checks, fewer recomputations."""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as saved_storage  # noqa: E402
import check_pilot as checker  # noqa: E402
import run_pilot as pilot  # noqa: E402

from deep_hedge_price import _dynamic_hedging_study as study  # noqa: E402


def test_verified_once_recomputes_only_a_changed_record():
    calls = []
    record = {"original_n": 4, "values": np.arange(4.0)}

    def verify():
        calls.append(1)
        return {"original_n": 4}

    memo = {}
    first = checker._verified_once(memo, "kind", record, verify)
    first["original_n"] = 99  # a caller's mutation never reaches the memo
    assert checker._verified_once(memo, "kind", copy.deepcopy(record), verify) == {"original_n": 4}
    assert len(calls) == 1
    changed = copy.deepcopy(record)
    changed["values"][-1] += 1e-12
    checker._verified_once(memo, "kind", changed, verify)
    assert len(calls) == 2
    checker._verified_once(memo, "other-kind", record, verify)
    assert len(calls) == 3
    checker._verified_once(None, "kind", record, verify)
    assert len(calls) == 4


def test_verified_once_never_remembers_a_failure():
    attempts = []

    def failing():
        attempts.append(1)
        raise ValueError("saved recomputation differs")

    memo = {}
    for _ in range(2):
        with pytest.raises(ValueError, match="differs"):
            checker._verified_once(memo, "kind", {"x": 1}, failing)
    assert len(attempts) == 2
    assert memo == {}


def test_verified_once_without_saved_digest_recomputes_as_before():
    calls = []
    record = {1: "non-string key has no saved-format digest"}
    memo = {}
    for _ in range(2):
        checker._verified_once(memo, "kind", record, lambda: calls.append(1))
    assert len(calls) == 2
    assert memo == {}


def test_recompute_memo_lives_only_in_its_verification_context():
    assert checker._recompute_memo(None) is not checker._recompute_memo(None)
    context = {"events": []}
    memo = checker._recompute_memo(context)
    assert checker._recompute_memo(context) is memo
    assert checker._recompute_memo({"events": []}) is not memo


def quote_risk_raw():
    value = {"original_n": 4, "targets": np.arange(8.0).reshape(2, 4)}
    arguments = pilot.pack_inputs({"dataset": {"original_n": 4}, "chunk_paths": 2})
    return {"kind": "quote_risk", "arguments": arguments, "value": value}


def test_identical_quote_risk_sources_recompute_once(monkeypatch):
    calls = []

    def recompute(**arguments):
        calls.append(arguments)
        return copy.deepcopy(quote_risk_raw()["value"])

    monkeypatch.setattr(study, "quote_risk_dataset", recompute)
    context = {"recompute_memo": {}}
    first = checker.check_wrapped_operation(quote_risk_raw(), "quote_risk", context)
    second = checker.check_wrapped_operation(quote_risk_raw(), "quote_risk", context)
    assert len(calls) == 1
    pilot.runner._same(first, second, "reused wrapped check")
    checker.check_wrapped_operation(quote_risk_raw(), "quote_risk", {})
    assert len(calls) == 2
    changed = quote_risk_raw()
    changed["value"]["targets"][0, 0] += 1.0
    with pytest.raises(ValueError, match="saved observable quote risk"):
        checker.check_wrapped_operation(changed, "quote_risk", context)
    assert len(calls) == 3


def test_market_pair_rows_share_one_replay(monkeypatch):
    calls = []

    def replay(record):
        calls.append(1)
        return {"original_n": record["original_n"], "scope": "saved_market_and_CRN_pairing"}

    monkeypatch.setattr(checker, "check_market_pair_record", replay)
    memo = {}
    job = {"id": "m", "operation": "market_pair", "raw": {"original_n": 4, "x": np.ones(3)}}
    first = checker._raw_job_check(job, {"recompute_memo": memo})
    second = checker._raw_job_check(copy.deepcopy(job), {"recompute_memo": memo})
    assert first == second
    assert len(calls) == 1
    checker._raw_job_check(job, {})
    assert len(calls) == 2


def test_bump_row_check_registers_its_full_recomputation(monkeypatch):
    calls = []

    def recompute(raw):
        calls.append(1)
        return {"original_n": raw["original_n"], "risk_variants": [1.0, 2.0, 3.0]}

    monkeypatch.setattr(checker, "check_bump_risk_record", recompute)
    memo = {}
    raw = {"kind": "bump_risk", "original_n": 4, "prices": np.ones((2, 4))}
    job = {"id": "bump", "operation": "bump_risk", "raw": raw}
    assert checker._raw_job_check(job, {"recompute_memo": memo})["risk_variants"][1] == 2.0
    assert checker._raw_job_check(job, {"recompute_memo": memo})["risk_variants"][1] == 2.0
    assert len(calls) == 2  # row checks keep their full recomputed result

    def unexpected():
        raise AssertionError("an identical paired-cell source must reuse the row check")

    checker._verified_once(memo, "bump_risk", copy.deepcopy(raw), unexpected)


def test_indexed_rows_use_planned_ids_and_still_check_decoded_ids():
    loads = []
    rows = [{"id": "a", "v": 1}, {"id": "b", "v": 2}]

    def load(index):
        loads.append(index)
        return copy.deepcopy(rows[index])

    declared = saved_storage.DeferredSequence(2, load, identifiers=["a", "b"])
    indexed = saved_storage.IndexedRows(declared)
    assert loads == []
    assert list(indexed) == ["a", "b"]
    assert indexed["b"]["v"] == 2
    assert loads == [1]
    assert declared[1:].identifiers == ("b",)
    swapped = saved_storage.IndexedRows(
        saved_storage.DeferredSequence(2, load, identifiers=["b", "a"])
    )
    with pytest.raises(ValueError, match="identity changed"):
        swapped["b"]
    with pytest.raises(ValueError, match="duplicate delayed stage row"):
        saved_storage.IndexedRows(saved_storage.DeferredSequence(2, load, identifiers=["a", "a"]))
    with pytest.raises(ValueError, match="identifier roster length"):
        saved_storage.DeferredSequence(2, load, identifiers=["a"])
    legacy = saved_storage.IndexedRows(saved_storage.DeferredSequence(2, load))
    assert list(legacy) == ["a", "b"]


def recorded_dependency(tmp_path, reads):
    def reader(path):
        reads.append(path)
        return pilot.read_pilot_artifact(path)

    results = saved_storage.RecordedJobs(
        artifact_context={"original_root": str(tmp_path), "restored_root": str(tmp_path)},
        reader=reader,
    )
    row = {
        "id": "dep",
        "operation": "market",
        "status": "executed",
        "raw": {"kind": "market", "value": np.arange(3.0)},
    }
    path = tmp_path / "jobs" / "dep"
    pilot.write_pilot_artifact(path, row)
    results.register(row, path)
    return results


def test_dependency_status_uses_in_process_reference_without_decoding(tmp_path):
    reads = []
    results = recorded_dependency(tmp_path, reads)
    assert pilot._recorded_status(results, "dep") == "executed"
    assert reads == []
    assert results["dep"]["status"] == "executed"
    assert len(reads) == 1
    with pytest.raises(KeyError):
        pilot._recorded_status(results, "missing")
    assert pilot._recorded_status({"dep": {"status": "failed_at_declared_cap"}}, "dep") == (
        "failed_at_declared_cap"
    )


def test_bounded_evidence_rows_declare_planned_ids_without_decoding(tmp_path):
    reads = []
    results = recorded_dependency(tmp_path, reads)
    planned = {"dep": {"id": "dep", "operation": "market", "arguments": {}}}
    evidence = [
        {
            "id": "dep",
            "operation": "market",
            "raw": {"job": "dep"},
            "arguments": {"job_arguments": "dep"},
        },
        {"job_record": "dep"},
    ]
    resolved = pilot._resolve(evidence, {}, results, planned_jobs=planned, bounded=True)
    assert isinstance(resolved, saved_storage.DeferredSequence)
    assert resolved.identifiers == ("dep", "dep")
    assert reads == []
    assert resolved[0]["id"] == resolved[1]["id"] == "dep"
    assert np.array_equal(resolved[0]["raw"]["value"], np.arange(3.0))
