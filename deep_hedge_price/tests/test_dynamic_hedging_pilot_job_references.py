"""Runtime job references over tiny synthetic saved rows; no finance or RNG."""

import copy
import gc
import shutil
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


def _row(index, status="executed"):
    values = np.arange(32, dtype=float).reshape(16, 2) + index
    if status != "executed":
        values[-1, -1] = np.nan
    return {
        "id": f"job:{index}",
        "operation": "synthetic_only",
        "status": status,
        "reason": None if status == "executed" else "original failure retained",
        "financial_qualification": "unknown",
        "expense": {"id": f"expense:{index}", "timing": {"wall_seconds": None}},
        "size": {"path_steps": 16, "expanded_bytes": values.nbytes},
        "argument_manifest": {"seed": 913, "calendar_times": np.array([0.0, 1.0])},
        "raw": {"original_n": 16, "seed": 913, "values": values},
    }


def _context(root):
    return {"original_root": str(root), "restored_root": str(root)}


def test_runtime_registration_matches_checkpoint_and_releases_raw(tmp_path):
    jobs = storage.RecordedJobs(artifact_context=_context(tmp_path))
    row = _row(0)
    path = tmp_path / row["id"]
    run_pilot.write_pilot_artifact(path, row)
    row["artifact_path"] = str(path)
    original = copy.deepcopy(row)
    weak = weakref.ref(row["raw"]["values"])
    reference = jobs.register(row, path)
    expected = {k: v for k, v in row.items() if k != "raw"}
    expected["raw_job_payload_sha256"] = runner.payload_digest(
        {k: v for k, v in row.items() if k != "artifact_path"}
    )
    runner._same(reference, expected, "same original checkpoint reference")
    runner._same(row, original, "register preserves original runtime row")
    assert "raw" not in jobs.references[row["id"]]
    identifier = row["id"]
    del row
    gc.collect()
    assert weak() is None
    loaded = jobs[identifier]
    runner._same(loaded, original, "full runtime result restored")
    assert loaded["artifact_path"] == str(path.resolve())
    loaded_weak = weakref.ref(loaded["raw"]["values"])
    del loaded
    gc.collect()
    assert loaded_weak() is None
    # A later mutation to the caller-owned metadata cannot alter the stored ref.
    original["expense"]["timing"]["wall_seconds"] = 99.0
    assert jobs.references[identifier]["expense"]["timing"]["wall_seconds"] is None


@pytest.mark.parametrize(
    "status",
    [
        "executed",
        "failed_at_declared_cap",
        "unexecuted_dependency_cap",
        "unclosed_source_or_solver_defect",
        "not_required_after_qualified_prefix",
    ],
)
def test_runtime_original_status_unknown_and_order_are_preserved(tmp_path, status):
    jobs = storage.RecordedJobs(artifact_context=_context(tmp_path))
    rows = [_row(0), _row(1, status)]
    for row in rows:
        path = tmp_path / row["id"]
        run_pilot.write_pilot_artifact(path, row)
        jobs.register(row, path)
    assert list(jobs) == [r["id"] for r in rows]
    loaded = jobs["job:1"]
    runner._same(
        {k: v for k, v in loaded.items() if k != "artifact_path"},
        rows[-1],
        "all original unknown/fault values preserved",
    )
    assert loaded["raw"]["original_n"] == 16
    assert loaded["raw"]["seed"] == 913
    assert loaded["financial_qualification"] == "unknown"
    with pytest.raises(KeyError):
        jobs["missing"]
    with pytest.raises(ValueError, match="duplicate"):
        jobs.register(rows[-1], tmp_path / "job:1")


def test_runtime_requires_saved_path_and_authenticates_full_original_row(tmp_path):
    jobs = storage.RecordedJobs(artifact_context=_context(tmp_path))
    row = _row(0)
    path = tmp_path / "job:0"
    with pytest.raises(ValueError, match="saved"):
        jobs.register(row, path)
    run_pilot.write_pilot_artifact(path, row)
    jobs.register(row, path)
    replacement = tmp_path / "replacement"
    changed = copy.deepcopy(row)
    changed["raw"]["values"][-1, -1] += 0.1
    run_pilot.write_pilot_artifact(replacement, changed)
    shutil.rmtree(path)
    replacement.rename(path)
    with pytest.raises(ValueError, match="payload"):
        jobs["job:0"]


def test_runtime_restored_path_and_standard_reader_behavior_are_distinct(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    row = _row(0)
    path = original / row["id"]
    run_pilot.write_pilot_artifact(path, row)
    runtime = storage.RecordedJobs(artifact_context=_context(original))
    runtime.register(row, path)
    refs = list(runtime.references.values())
    restored = tmp_path / "restored"
    shutil.copytree(original, restored)
    shutil.rmtree(original)
    context = {"original_root": str(original), "restored_root": str(restored)}
    standard = storage.ReferenceJobs(refs, artifact_context=context)
    loaded = standard["job:0"]
    assert "artifact_path" not in loaded
    runner._same(loaded, row, "legacy standard saved reader")
    restored_runtime = storage.RecordedJobs(refs, artifact_context=context)
    current = restored_runtime["job:0"]
    assert current["artifact_path"] == str((restored / row["id"]).resolve())
    runner._same(
        {k: v for k, v in current.items() if k != "artifact_path"}, row, "restored full row"
    )


def test_runtime_reference_does_not_follow_external_metadata_mutation(tmp_path):
    jobs = storage.RecordedJobs(artifact_context=_context(tmp_path))
    row = _row(0)
    path = tmp_path / row["id"]
    run_pilot.write_pilot_artifact(path, row)
    jobs.register(row, path)
    row["expense"]["timing"]["wall_seconds"] = 3.0
    row["argument_manifest"]["calendar_times"][-1] = 9.0
    assert jobs.references["job:0"]["expense"]["timing"]["wall_seconds"] is None
    np.testing.assert_allclose(
        jobs.references["job:0"]["argument_manifest"]["calendar_times"], [0.0, 1.0]
    )
    assert "raw" not in jobs.references["job:0"]
