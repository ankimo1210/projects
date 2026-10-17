"""Saved-only storage regressions; synthetic data is not a financial pilot."""

import gc
import hashlib
import sys
import weakref
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as storage  # noqa: E402
import run_pilot  # noqa: E402
import run_reference as runner  # noqa: E402
from hullkit._heston_local_surface import HestonParameters  # noqa: E402


def original_digest(value):
    arrays = {}
    tree = runner._encode_tree(value, arrays)
    bindings = {
        key: {
            "shape": list(array.shape),
            "dtype": array.dtype.str,
            "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
        }
        for key, array in arrays.items()
    }
    return runner._digest({"tree": tree, "arrays": bindings})


def row(index, *, unknown=False):
    values = np.arange(32, dtype=float).reshape(16, 2) + index
    if unknown:
        values[-1, -1] = np.nan
    return {
        "id": f"job:{index}",
        "status": "executed" if not unknown else "unclosed_source_or_solver_defect",
        "reason": None if not unknown else "original unknown retained",
        "raw": {"original_n": 16, "seed": 913, "values": values},
    }


def references(root, rows):
    result = []
    for value in rows:
        path = root / value["id"]
        run_pilot.write_pilot_artifact(path, value)
        result.append(
            {
                **{k: v for k, v in value.items() if k != "raw"},
                "artifact_path": str(path),
                "raw_job_payload_sha256": original_digest(value),
            }
        )
    return result


def tracked_reader(refs):
    def read(path):
        value, receipt = run_pilot.read_pilot_artifact(path)
        if "raw" in value:
            refs.append(weakref.ref(value["raw"]["values"]))
        elif "value" in value:
            refs.append(weakref.ref(value["value"]["values"]))
        return value, receipt

    return read


def test_streaming_digest_preserves_the_original_format_and_array_occurrences(tmp_path):
    array = np.arange(24.0).reshape(4, 6)
    value = {
        "parameters": HestonParameters(100, 0.02, 0.01, 0.04, 2, 0.04, 0.3, -0.7),
        "scalars": (np.int32(2), -0.0, np.nan, np.inf, -np.inf, "日本語", None, True),
        "arrays": [
            array,
            array,
            array[:, ::2],
            np.asfortranarray(array),
            array.astype(">f8"),
            np.array(-0.0),
            np.empty((0, 2)),
            np.array([(1, 2.0)], dtype=[("i", "<i4"), ("f", ">f8")]),
        ],
    }
    assert storage.payload_digest(value, spool_directory=tmp_path) == original_digest(value)
    assert not list(tmp_path.iterdir())
    changed = {**value, "arrays": [*value["arrays"][:-1], np.array([1.0])]}
    assert storage.payload_digest(changed) != original_digest(value)


def test_delayed_rows_preserve_full_digest_and_release_every_array(tmp_path):
    originals = [row(i, unknown=i == 2) for i in range(3)]
    refs = references(tmp_path / "original", originals)
    weak = []
    jobs = storage.ReferenceJobs(
        refs,
        artifact_context={
            "original_root": str(tmp_path / "original"),
            "restored_root": str(tmp_path / "original"),
        },
        reader=tracked_reader(weak),
    )
    delayed = storage.DeferredSequence(len(jobs), lambda i: jobs[list(jobs)[i]])
    assert storage.payload_digest({"jobs": delayed}) == original_digest({"jobs": originals})
    gc.collect()
    assert weak and all(r() is None for r in weak)
    assert list(jobs) == [r["id"] for r in originals]
    assert "job:2" in jobs
    assert len(jobs) == 3


def test_original_reference_reads_restored_copy_without_the_original(tmp_path):
    original, restored = tmp_path / "original", tmp_path / "restored"
    refs = references(original, [row(0), row(1, unknown=True)])
    original.rename(restored)
    jobs = storage.ReferenceJobs(
        refs, artifact_context={"original_root": str(original), "restored_root": str(restored)}
    )
    runner._same(jobs["job:1"], row(1, unknown=True), "restored original unknown")
    assert not original.exists()


def test_last_row_self_consistent_storage_tamper_is_rejected_by_original_reference(tmp_path):
    originals = [row(0), row(1, unknown=True)]
    refs = references(tmp_path, originals)
    jobs = storage.ReferenceJobs(
        refs, artifact_context={"original_root": str(tmp_path), "restored_root": str(tmp_path)}
    )
    changed = row(1, unknown=True)
    changed["raw"]["values"][-2, -1] += 0.125
    replacement = tmp_path / "replacement"
    run_pilot.write_pilot_artifact(replacement, changed)
    # A completely valid replacement artifact cannot inherit the original row hash.
    jobs = storage.ReferenceJobs(
        [*refs[:-1], {**refs[-1], "artifact_path": str(replacement)}],
        artifact_context=jobs.artifact_context,
    )
    with pytest.raises(ValueError, match="immutable original job payload"):
        jobs["job:1"]
    new_ref = {
        **refs[-1],
        "artifact_path": str(replacement),
        "raw_job_payload_sha256": original_digest(changed),
    }
    new_jobs = storage.ReferenceJobs([refs[0], new_ref], artifact_context=jobs.artifact_context)
    changed_sequence = storage.DeferredSequence(2, lambda i: new_jobs[list(new_jobs)[i]])
    assert storage.payload_digest({"jobs": changed_sequence}) != original_digest(
        {"jobs": originals}
    )


def test_reference_membership_and_id_iteration_do_not_decode_job_payloads(tmp_path):
    refs = references(tmp_path, [row(0), row(1)])

    def forbidden_reader(path):
        pytest.fail("metadata-only lookup decoded the original job")

    jobs = storage.ReferenceJobs(
        refs,
        artifact_context={"original_root": str(tmp_path), "restored_root": str(tmp_path)},
        reader=forbidden_reader,
    )
    assert "job:0" in jobs and "absent" not in jobs
    assert len(jobs) == 2 and list(jobs) == ["job:0", "job:1"]


def test_saved_checks_retain_full_values_unknowns_and_release_arrays(tmp_path):
    weak = []
    checks = storage.SavedChecks(tmp_path, reader=tracked_reader(weak))
    expected = {}
    for index in range(3):
        raw = row(index, unknown=index == 2)["raw"]
        value = {**raw, "sum": np.sum(raw["values"], axis=0), "financial_qualification": "unknown"}
        expected[str(index)] = value
        checks[str(index)] = value
    for identifier in checks:
        actual = checks[identifier]
        runner._same(actual, expected[identifier], "saved full arithmetic")
        del actual
    gc.collect()
    assert weak and all(r() is None for r in weak)
    assert len(checks.references) == 3
    with pytest.raises(ValueError, match="immutable"):
        checks["2"] = expected["2"]
    del checks
    restored = storage.SavedChecks(tmp_path, references=storage.read_check_manifest(tmp_path))
    runner._same(restored["2"], expected["2"], "reopened unknown arrays")
    assert storage.payload_digest(restored) == original_digest(expected)


def test_duplicate_original_reference_is_rejected(tmp_path):
    refs = references(tmp_path, [row(0)])
    with pytest.raises(ValueError, match="duplicate"):
        storage.ReferenceJobs(
            [*refs, refs[0]],
            artifact_context={"original_root": str(tmp_path), "restored_root": str(tmp_path)},
        )


def policy_checkpoint(root):
    from deep_hedge_price import _dynamic_hedging_study as study

    n = 16
    prices = np.zeros((n, 2, 2))
    prices[:, :, 0], prices[:, :, 1] = 100, 5
    dataset = {
        "model": "Heston",
        "original_n": n,
        "times": np.array([0.0, 1.0]),
        "prices": prices,
        "memory_sum": np.zeros((n, 2)),
        "memory_count": np.array([0, 12]),
        "payoff": np.linspace(0, 2, n),
        "premium": 1.0,
        "rate": 0.03,
        "cost_rates": np.array([0.0005, 0.005]),
        "path_mask": np.ones(n, dtype=bool),
    }
    rollout = study.policy_rollout(dataset, risk={}, universe="U1", policy="none")
    rows = [
        {
            "id": f"policy:{i}",
            "operation": "policy",
            "status": "executed",
            "raw": {"dataset": dataset, "rollout": rollout},
        }
        for i in range(2)
    ]
    rows.append(
        {
            "id": "policy:tail",
            "operation": "policy",
            "status": "unclosed_source_or_solver_defect",
            "reason": "original fault",
            "raw": {"dataset": dataset, "rollout": rollout},
        }
    )
    refs = references(root / "jobs", rows)
    snapshot = {
        "schema": "rb-f04-pilot-raw-v1",
        "jobs": refs,
        "artifact_directory": str(root),
        "source": {},
        "case_bindings": [],
        "attempt_bindings": [],
        "test_opened": False,
        "financial_qualification": "unknown",
    }
    run_pilot.write_pilot_artifact(root / "checkpoint0000", snapshot)
    return rows


def test_full_saved_checker_matches_eager_arithmetic_and_preserves_all_missing(tmp_path):
    import check_pilot

    root = tmp_path / "pilot"
    policy_checkpoint(root)
    eager = check_pilot.check_pilot(root, expected_plan=None)
    bounded = check_pilot.check_pilot(root, expected_plan=None, check_directory=tmp_path / "checks")
    assert bounded["closed"] is False and bounded["financial_qualification"] == "unknown"
    assert len(bounded["missing_cases"]) == 121
    assert len(bounded["missing_attempts"]) == 51
    assert bounded["issues"] == eager["issues"]
    assert list(bounded["raw_checks"]) == ["policy:0", "policy:1"]
    for identifier in bounded["raw_checks"]:
        runner._same(
            bounded["raw_checks"][identifier],
            eager["raw_checks"][identifier],
            "full saved arithmetic",
        )
    assert storage.payload_digest(bounded["raw_snapshot"]) == original_digest(eager["raw_snapshot"])
    assert storage.payload_digest(bounded["raw_checks"]) == original_digest(eager["raw_checks"])


def test_bounded_saved_checker_authenticates_the_unexecuted_tail(tmp_path):
    import check_pilot

    root = tmp_path / "pilot"
    rows = policy_checkpoint(root)
    checkpoint, _ = run_pilot.read_pilot_artifact(root / "checkpoint0000")
    # Substitute a self-consistent tail artifact while retaining its original
    # checkpoint reference: even a nonexecuted fault row must be authenticated.
    alternate = root / "alternate"
    changed = {**rows[-1], "reason": "changed original fault"}
    run_pilot.write_pilot_artifact(alternate, changed)
    checkpoint["jobs"][-1]["artifact_path"] = str(alternate)
    run_pilot.write_pilot_artifact(root / "checkpoint0001", checkpoint)
    with pytest.raises(ValueError, match="immutable original job payload"):
        check_pilot.check_pilot(root, expected_plan=None, check_directory=tmp_path / "checks")


def test_streaming_digest_releases_previous_row_before_loading_the_next():
    weak = []

    def load(index):
        gc.collect()
        assert all(r() is None for r in weak), "previous full row retained during next read"
        array = np.full((16, 2), index, dtype=float)
        weak.append(weakref.ref(array))
        return {"values": array}

    actual = storage.payload_digest(storage.DeferredSequence(3, load))
    assert actual == original_digest(
        [{"values": np.full((16, 2), i, dtype=float)} for i in range(3)]
    )


def test_saved_check_manifest_rejects_wrong_schema(tmp_path):
    import json

    (tmp_path / "manifest000001.json").write_text(
        json.dumps({"schema": "unrelated-schema", "references": []})
    )
    with pytest.raises(ValueError, match="manifest schema"):
        storage.read_check_manifest(tmp_path)


def test_original_input_identity_releases_delayed_dependency_rows():
    def old_input_identity(value):
        if isinstance(value, dict):
            value = {k: old_input_identity(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            value = [old_input_identity(v) for v in value]
        return original_digest(value)

    weak = []

    def load(index):
        gc.collect()
        assert all(r() is None for r in weak), "dependency retained between reads"
        array = np.arange(16, dtype=float) + index
        weak.append(weakref.ref(array))
        return {"id": str(index), "raw": {"values": array, "state": "unknown"}}

    sequence = storage.DeferredSequence(3, load)
    eager = [
        {"id": str(i), "raw": {"values": np.arange(16, dtype=float) + i, "state": "unknown"}}
        for i in range(3)
    ]
    assert run_pilot.input_identity(sequence) == old_input_identity(eager)


def test_bounded_report_retains_all_full_check_values_and_original_snapshot_binding(tmp_path):
    import check_pilot

    root, output = tmp_path / "pilot", tmp_path / "saved-check"
    policy_checkpoint(root)
    result = check_pilot.check_pilot(root, expected_plan=None, check_directory=output / "checks")
    receipt = check_pilot.write_bounded_report(output, result)
    authenticated = check_pilot.read_bounded_report(
        output / "report", expected_receipt=receipt, pilot_directory=root
    )
    runner._same(
        authenticated["raw_checks"]["policy:1"],
        result["raw_checks"]["policy:1"],
        "trusted full-check read",
    )
    assert authenticated["issues"] == result["issues"]
    report, _ = run_pilot.read_pilot_artifact(output / "report")
    assert report["schema"] == "rb-f04-pilot-saved-check-bounded-v1"
    assert report["closed"] is False
    assert len(report["missing_cases"]) == 121 and len(report["missing_attempts"]) == 51
    binding = report["raw_checks_reference"]
    restored = storage.SavedChecks(output / binding["directory"], references=binding["references"])
    assert list(restored) == ["policy:0", "policy:1"]
    assert storage.payload_digest(restored) == binding["logical_payload_sha256"]
    assert report["raw_snapshot_reference"]["hydrated_logical_payload_sha256"] == (
        storage.payload_digest(result["raw_snapshot"])
    )
    assert [r["id"] for r in report["raw_snapshot_reference"]["saved_snapshot"]["jobs"]] == [
        "policy:0",
        "policy:1",
        "policy:tail",
    ]


def test_indexed_delayed_stage_visits_and_releases_all_rows():
    weak = []

    def load(index):
        gc.collect()
        assert all(r() is None for r in weak), "stage indexed previous full row"
        array = np.full(16, index, dtype=float)
        weak.append(weakref.ref(array))
        return {"id": str(index), "raw": {"values": array}}

    stage = storage.IndexedRows(storage.DeferredSequence(3, load))
    gc.collect()
    assert list(stage) == ["0", "1", "2"]
    assert weak and all(r() is None for r in weak)
    last = stage["2"]
    assert np.allclose(last["raw"]["values"], np.full(16, 2.0))
    del last
    gc.collect()
    assert all(r() is None for r in weak)
    with pytest.raises(ValueError, match="duplicate delayed stage row"):
        storage.IndexedRows(storage.DeferredSequence(2, lambda i: {"id": "same"}))


def test_bounded_original_dependency_resolution_preserves_order_values_and_tail(tmp_path):
    originals = [row(0), row(1), row(2, unknown=True)]
    refs = references(tmp_path, originals)
    jobs = storage.ReferenceJobs(
        refs, artifact_context={"original_root": str(tmp_path), "restored_root": str(tmp_path)}
    )
    specification = [{"job_record": r["id"]} for r in originals]
    eager = run_pilot._resolve(specification, {}, {r["id"]: r for r in originals})
    delayed = run_pilot._resolve(specification, {}, jobs, bounded=True)
    assert isinstance(delayed, storage.DeferredSequence)
    assert run_pilot.input_identity(delayed) == run_pilot.input_identity(eager)
    assert storage.payload_digest(delayed) == original_digest(eager)
    assert delayed[-1]["status"] == "unclosed_source_or_solver_defect"


def test_bounded_embedded_gate_evidence_is_lazy_and_releases_each_row():
    reads = []
    refs = []

    class FreshJobs:
        def __getitem__(self, identifier):
            reads.append(identifier)
            values = np.full(32, int(identifier.split(":")[-1]), dtype=float)
            refs.append(weakref.ref(values))
            return {"status": "executed", "raw": {"values": values}}

    specification = [
        {
            "id": f"job:{i}",
            "operation": "call_table",
            "raw": {"job": f"job:{i}"},
            "arguments": {
                "original_values": {"job": f"job:{i}", "path": ["values"]},
                "controls": {},
            },
        }
        for i in range(4)
    ]
    # Preserve embedded arguments rather than replacing them with a locked job's
    # potentially different controls. Only the loading schedule may change.
    planned = {
        f"job:{i}": {"operation": "call_table", "arguments": {"controls": {"delta": 36}}}
        for i in range(4)
    }
    sequence = run_pilot._resolve(
        specification, {}, FreshJobs(), planned_jobs=planned, bounded=True
    )
    assert isinstance(sequence, storage.DeferredSequence)
    assert reads == [], "bounded gate hydrated evidence before iteration"
    assert len(sequence) == len(specification)
    for i in range(len(sequence)):
        gc.collect()
        assert all(ref() is None for ref in refs), "previous gate row retained"
        value = sequence[i]
        assert value["id"] == f"job:{i}"
        assert value["operation"] == "call_table"
        assert value["arguments"]["controls"] == {}
        assert np.allclose(value["raw"]["values"], np.full(32, float(i)))
        assert np.allclose(value["arguments"]["original_values"], np.full(32, float(i)))
        assert reads == [f"job:{j}" for j in range(i + 1) for _ in range(2)]
        del value
    gc.collect()
    assert all(ref() is None for ref in refs)


def test_bounded_embedded_gate_evidence_preserves_original_provenance_identity():
    original = {f"job:{i}": {"raw": {"values": np.arange(8, dtype=float) + i}} for i in range(3)}
    specification = [
        {
            "id": identifier,
            "operation": "call_table",
            "arguments": {"controls": {}, "original_n": 1024},
            "raw": {"job": identifier},
        }
        for identifier in original
    ]
    eager = run_pilot._resolve(specification, {}, original)
    delayed = run_pilot._resolve(specification, {}, original, bounded=True)
    assert isinstance(eager, list)
    assert isinstance(delayed, storage.DeferredSequence)
    assert [value["id"] for value in delayed] == list(original)
    for i, value in enumerate(delayed):
        assert np.allclose(value["raw"]["values"], np.arange(8, dtype=float) + i)
        assert value["arguments"] == {"controls": {}, "original_n": 1024}
    # These hashes bind transport/provenance; numerical values are checked above.
    assert run_pilot.input_identity(delayed) == run_pilot.input_identity(eager)
    assert storage.payload_digest(delayed) == original_digest(eager)


def test_bounded_embedded_gate_evidence_keeps_mixed_and_empty_lists_eager():
    original = {"job:0": {"raw": {"values": np.arange(8, dtype=float)}}}
    evidence = {
        "id": "job:0",
        "operation": "call_table",
        "arguments": {"controls": {}},
        "raw": {"job": "job:0"},
    }
    mixed = [evidence, {"date_index": 0, "job_id": "job:0"}]
    resolved = run_pilot._resolve(mixed, {}, original, bounded=True)
    assert isinstance(resolved, list)
    assert resolved[1] == mixed[1]
    assert np.allclose(resolved[0]["raw"]["values"], np.arange(8, dtype=float))
    assert run_pilot._resolve([], {}, original, bounded=True) == []


def test_bounded_saved_arithmetic_reads_restored_root_only(tmp_path):
    import check_pilot

    original = tmp_path / "original"
    policy_checkpoint(original)
    eager = check_pilot.check_pilot(original, expected_plan=None)
    restored = tmp_path / "restored"
    original.rename(restored)
    bounded = check_pilot.check_pilot(
        restored, expected_plan=None, check_directory=tmp_path / "checks"
    )
    assert not original.exists()
    assert bounded["issues"] == eager["issues"]
    assert storage.payload_digest(bounded["raw_checks"]) == original_digest(eager["raw_checks"])
    assert storage.payload_digest(bounded["raw_snapshot"]) == original_digest(eager["raw_snapshot"])


def test_bounded_resolution_keeps_structural_lists_and_direct_roster_comparison():
    bindings = [{"date_index": i, "job_id": f"date:{i}"} for i in range(12)]
    specification = {
        "state_bindings": bindings,
        "arguments": {"stage_plan": {"state_bindings": bindings, "grid": "coarse"}},
    }
    resolved = run_pilot._resolve(specification, {}, {}, bounded=True)
    assert isinstance(resolved["state_bindings"], list)
    assert resolved["state_bindings"] == resolved["arguments"]["stage_plan"]["state_bindings"]
    assert run_pilot.input_identity(resolved) == run_pilot.input_identity(specification)


def test_delayed_physical_guard_visits_last_original_node(tmp_path):
    import check_pilot

    nodes = []
    for i in range(3):
        path = tmp_path / str(i)
        run_pilot.write_pilot_artifact(path, {"saved": np.full(16, i, dtype=float)})
        nodes.append({"kind": "teacher_grid", "nodes": [{"path": str(path)}]})
    eager = check_pilot._teacher_physical_guard(nodes)
    delayed = storage.DeferredSequence(3, lambda i: nodes[i])
    assert check_pilot._teacher_physical_guard(delayed) == eager
    (tmp_path / "2" / "physical-change.txt").write_text("changed final physical node")
    assert check_pilot._teacher_physical_guard(delayed) != eager


def test_refinement_projection_does_not_retain_all_pair_raw_payloads():
    from collections.abc import Mapping

    import check_pilot

    from deep_hedge_price import _dynamic_hedging_execution as execution

    weak = []
    count = 8
    ids = [*(f"pair:{i}" for i in range(count)), "market"]

    class Jobs(Mapping):
        def __iter__(self):
            return iter(ids)

        def __len__(self):
            return len(ids)

        def __getitem__(self, key):
            gc.collect()
            assert sum(r() is not None for r in weak) <= 3, "all pair raw retained"
            values = np.arange(16, dtype=float)
            weak.append(weakref.ref(values))
            return {
                "id": key,
                "status": "executed",
                "operation": "market_pair" if key == "market" else "paired_pnl",
                "raw": {
                    "kind": "market_pair" if key == "market" else "paired_pnl",
                    "model": "Heston",
                    "refinement_kind": "pnl",
                    "original_n": 16,
                    "base": values,
                },
            }

    # Projection of previously checked numbers only. The last pair is unknown;
    # this small storage unit cannot stand in for an original-count CRN review.
    checks = {
        i: {
            **check_pilot.paired_pnl_metrics(
                np.arange(16.0), np.arange(16.0) + 0.01, original_n=16
            ),
            "shared_CRN_checked": True,
        }
        for i in ids
    }
    checks["pair:7"]["pnl_rms_difference"] = None
    result = check_pilot.project_attempt(
        "refinement:pnl:Heston", ids, Jobs(), checks, execution.execution_candidate(), {}
    )
    assert result["required_job_ids"] == ids
    assert result["financial_qualification"] == "unknown"


def test_bounded_report_rejects_a_check_store_outside_its_declared_directory(tmp_path):
    import check_pilot

    root, output = tmp_path / "pilot", tmp_path / "saved-check"
    policy_checkpoint(root)
    result = check_pilot.check_pilot(
        root, expected_plan=None, check_directory=tmp_path / "another-check-store"
    )
    with pytest.raises(ValueError, match="declared checks directory"):
        check_pilot.write_bounded_report(output, result)
    assert not (output / "report").exists()
