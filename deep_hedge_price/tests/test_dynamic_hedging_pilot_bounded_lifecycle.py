"""Isolated lifecycle storage tests; no formal financial pilot qualification."""

import copy
import gc
import sys
import weakref
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as storage  # noqa: E402
import check_pilot  # noqa: E402
import run_pilot  # noqa: E402
from test_dynamic_hedging_pilot import _lifecycle_source_plan  # noqa: E402


def isolated_plan(monkeypatch, count=8):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    # The existing source-unit plan preserves the declared original roster.
    # These source diagnostics have no financial sampling denominator.
    template = plan["jobs"][-1]
    plan["jobs"] = []
    for index in range(count):
        job = copy.deepcopy(template)
        job.update(
            id=f"diagnostic:{index}",
            expense_id=f"diagnostic:{index}:actual",
            arguments={"index": index},
        )
        plan["jobs"].append(job)
    return inputs, plan


def test_bounded_lifecycle_releases_previous_raw_and_preserves_all_checkpoint_refs(
    tmp_path, monkeypatch
):
    inputs, plan = isolated_plan(monkeypatch)
    weak = []

    def diagnostic_dispatch(operation, arguments):
        gc.collect()
        assert all(value() is None for value in weak), "previous full raw retained"
        array = np.arange(16.0) + arguments["index"]
        if arguments["index"] == 7:
            array[-1] = np.nan
        weak.append(weakref.ref(array))
        return {"kind": "source_diagnostic", "values": array, "financial_qualification": "unknown"}

    monkeypatch.setattr(run_pilot, "_dispatch", diagnostic_dispatch)
    monkeypatch.setattr(np.random, "default_rng", lambda *a, **k: pytest.fail("unit RNG"))
    root = tmp_path / "pilot"
    snapshot = run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, bounded=True)
    assert isinstance(snapshot["jobs"], storage.DeferredSequence)
    assert len(snapshot["jobs"]) == len(plan["jobs"]) == 8
    gc.collect()
    assert all(value() is None for value in weak)
    checkpoint, _ = run_pilot.read_pilot_artifact(root / "checkpoint0000")
    assert [r["id"] for r in checkpoint["jobs"]] == [r["id"] for r in plan["jobs"]]
    for index, reference in enumerate(checkpoint["jobs"]):
        assert "raw" not in reference
        saved, _ = run_pilot.read_pilot_artifact(Path(reference["artifact_path"]))
        assert storage.payload_digest(saved) == reference["raw_job_payload_sha256"]
        actual = snapshot["jobs"][index]
        np.testing.assert_allclose(
            actual["raw"]["values"],
            np.arange(16.0) + index if index != 7 else np.r_[np.arange(15.0) + 7, np.nan],
            equal_nan=True,
        )
        assert actual["financial_qualification"] == "unknown"
    assert snapshot["test_opened"] is False


def test_bounded_cap_dependency_and_resume_keep_original_costs_and_raw(tmp_path, monkeypatch):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    root = tmp_path / "pilot"
    first = run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, bounded=True)
    assert [row["status"] for row in first["jobs"]] == [
        "failed_at_declared_cap",
        "unexecuted_dependency_cap",
        "executed",
    ]
    parent, _ = run_pilot.read_pilot_artifact(root / "jobs/teacher-cap")
    expected_parent = storage.payload_digest(parent)
    monkeypatch.setattr(run_pilot, "run_teacher_job", lambda *a, **k: pytest.fail("cap rerun"))
    resumed = run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, resume=True, bounded=True)
    unchanged, _ = run_pilot.read_pilot_artifact(root / "jobs/teacher-cap")
    assert storage.payload_digest(unchanged) == expected_parent
    assert resumed["execution_phases"][0] == first["execution_phases"][0]
    assert resumed["execution_phases"][1]["covered_job_ids"] == []
    checked = check_pilot.check_dependency_cap_job(
        resumed["jobs"][1], plan["jobs"][1], plan, storage.IndexedRows(resumed["jobs"])
    )
    assert checked["executed_n"] == 0
    assert checked["cap_scope_parent_ids"] == ["teacher-cap"]
    costs = check_pilot.check_raw_costs(resumed, plan)
    assert costs["closed"] is True  # Source-unit plan has no required external clocks.
    assert costs["financial_speedup_supported"] is False


def test_bounded_lifecycle_keeps_original_source_fault_tail(tmp_path, monkeypatch):
    inputs, plan = _lifecycle_source_plan(monkeypatch)
    plan["jobs"][0]["operation"] = "invalid-source-operation"
    plan["jobs"][0]["prediction"]["path_steps"] = 0
    root = tmp_path / "pilot"
    snapshot = run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, bounded=True)
    assert len(snapshot["jobs"]) == 1
    fault = snapshot["jobs"][0]
    assert fault["status"] == "unclosed_source_or_solver_defect"
    assert fault["cap_evidence"] is None
    assert fault["financial_qualification"] == "unknown"
    assert "unsupported actual pilot operation" in fault["reason"]
    checkpoint, _ = run_pilot.read_pilot_artifact(root / "checkpoint0000")
    assert checkpoint["jobs"][0]["raw_job_payload_sha256"] == storage.payload_digest(
        {key: value for key, value in fault.items() if key != "artifact_path"}
    )


def test_bounded_resume_refuses_resealed_raw_that_differs_from_previous_checkpoint(
    tmp_path, monkeypatch
):
    inputs, plan = isolated_plan(monkeypatch, count=2)
    monkeypatch.setattr(
        run_pilot,
        "_dispatch",
        lambda operation, arguments: {"values": np.arange(16.0) + arguments["index"]},
    )
    root = tmp_path / "pilot"
    run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, bounded=True)
    path = root / "jobs/diagnostic:1"
    original, _ = run_pilot.read_pilot_artifact(path)
    replacement = root / "replacement"
    changed = copy.deepcopy(original)
    changed["raw"]["values"][-1] += 0.125
    run_pilot.write_pilot_artifact(replacement, changed)
    path.rename(root / "preserved-original")
    replacement.rename(path)
    with pytest.raises(ValueError, match="resume original job payload differs"):
        run_pilot.run_pilot(root, inputs=inputs, locked_plan=plan, resume=True, bounded=True)
    assert not (root / "checkpoint0001").exists()
