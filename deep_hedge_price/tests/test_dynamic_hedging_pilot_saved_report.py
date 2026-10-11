"""Trusted bounded report reads, using only tiny synthetic storage values."""

import importlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as storage  # noqa: E402
import check_pilot  # noqa: E402
import run_pilot  # noqa: E402


def reader():
    assert importlib.util.find_spec("_pilot_saved_report") is not None, (
        "trusted bounded report reader is not implemented"
    )
    return importlib.import_module("_pilot_saved_report")


@pytest.fixture
def saved_report(tmp_path, monkeypatch):
    def forbid_rng(*args, **kwargs):
        pytest.fail("saved report transport must not generate financial paths")

    monkeypatch.setattr(np.random, "default_rng", forbid_rng)
    root = tmp_path / "bundle"
    native, output = root / "native", root / "saved-check"
    rows, references = [], []
    for index in range(3):
        raw = {"original_n": 16, "values": np.array([index, np.nan])}
        value = {
            "id": f"job:{index}",
            "status": "executed" if index < 2 else "unclosed_source_or_solver_defect",
            "reason": None if index < 2 else "original failure retained",
            "raw": raw if index < 2 else None,
        }
        path = native / f"job{index:06d}"
        run_pilot.write_pilot_artifact(path, value)
        references.append(
            {
                **{key: val for key, val in value.items() if key != "raw"},
                "artifact_path": str(path),
                "raw_job_payload_sha256": storage.payload_digest(value),
            }
        )
        rows.append(value)
    snapshot = {
        "artifact_directory": str(native),
        "jobs": references,
        "source": {"synthetic_source_only": True},
        "unknown": None,
        "financial_qualification": "unknown",
    }
    receipt = run_pilot.write_pilot_artifact(native / "checkpoint000003", snapshot)
    jobs = storage.ReferenceJobs(
        references,
        artifact_context={"original_root": str(native), "restored_root": str(native)},
    )
    checks = storage.SavedChecks(output / "checks")
    for index in range(2):
        checks[f"job:{index}"] = {
            "values": np.array([index, np.nan]),
            "original_n": 16,
            "financial_qualification": "unknown",
        }
    result = {
        "closed": False,
        "financial_qualification": "unknown",
        "costs": {"closed": False, "charged_seconds": None},
        "issues": [{"id": "job:2", "status": "unclosed_source_or_solver_defect"}],
        "raw_checks": checks,
        "raw_snapshot": dict(snapshot, jobs=jobs.sequence()),
        "saved_checkpoint_reference": {
            "checkpoint_name": "checkpoint000003",
            "receipt": receipt,
            "saved_snapshot": snapshot,
            "saved_snapshot_sha256": storage.payload_digest(snapshot),
        },
        "unverified": ["financial_pilot_approval", "main_freeze"],
    }
    outer = check_pilot.write_bounded_report(output, result)
    return {
        "root": root,
        "native": native,
        "output": output,
        "receipt": outer,
        "rows": rows,
        "result": result,
    }


def load(fixture, **kwargs):
    return reader().read_bounded_report(
        fixture["output"] / "report",
        expected_receipt=fixture["receipt"],
        pilot_directory=fixture["native"],
        **kwargs,
    )


def replace_artifact(path, value):
    replacement = path.with_name(path.name + "-replacement")
    receipt = run_pilot.write_pilot_artifact(replacement, value)
    shutil.rmtree(path)
    replacement.rename(path)
    return receipt


def rewrite_report(fixture, change):
    path = fixture["output"] / "report"
    value, _ = run_pilot.read_pilot_artifact(path)
    change(value)
    fixture["receipt"] = replace_artifact(path, value)


def test_full_report_preserves_values_unknown_costs_and_original_fault_tail(saved_report):
    result = load(saved_report)
    assert result["closed"] is False
    assert result["financial_qualification"] == "unknown"
    assert result["costs"] == {"closed": False, "charged_seconds": None}
    assert result["issues"] == saved_report["result"]["issues"]
    assert list(result["raw_checks"]) == ["job:0", "job:1"]
    assert np.allclose(result["raw_checks"]["job:1"]["values"], [1, np.nan], equal_nan=True)
    rows = result["raw_snapshot"]["jobs"]
    assert [rows[index]["id"] for index in range(len(rows))] == ["job:0", "job:1", "job:2"]
    assert rows[-1]["raw"] is None
    assert rows[-1]["reason"] == "original failure retained"
    assert storage.payload_digest(result["raw_snapshot"]) == storage.payload_digest(
        saved_report["result"]["raw_snapshot"]
    )


def test_expected_outer_receipt_is_required_before_any_storage_read(saved_report, monkeypatch):
    module = reader()
    with pytest.raises(TypeError, match="expected_receipt"):
        module.read_bounded_report(
            saved_report["output"] / "report", pilot_directory=saved_report["native"]
        )
    monkeypatch.setattr(
        run_pilot, "read_pilot_artifact", lambda *args: pytest.fail("untrusted report decoded")
    )
    with pytest.raises(ValueError, match="expected report receipt"):
        module.read_bounded_report(
            saved_report["output"] / "report",
            expected_receipt=None,
            pilot_directory=saved_report["native"],
        )


def test_self_consistent_outer_replacement_cannot_inherit_expected_receipt(saved_report):
    path = saved_report["output"] / "report"
    value, _ = run_pilot.read_pilot_artifact(path)
    value["closed"] = True
    replace_artifact(path, value)
    with pytest.raises(ValueError, match="report receipt"):
        load(saved_report)


def test_last_manifest_deletion_is_rejected_against_bound_full_roster(saved_report):
    (saved_report["output"] / "checks" / "manifest000002.json").unlink()
    with pytest.raises(ValueError, match=r"manifest.*roster"):
        load(saved_report)


def test_manifest_self_consistent_reference_rewrite_is_rejected(saved_report):
    path = saved_report["output"] / "checks" / "manifest000002.json"
    value = json.loads(path.read_text())
    value["references"][0]["payload_sha256"] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match=r"manifest.*roster"):
        load(saved_report)


def test_valid_last_check_replacement_fails_bound_receipt(saved_report):
    path = saved_report["output"] / "checks" / "check000001"
    value, _ = run_pilot.read_pilot_artifact(path)
    value["value"]["values"][0] += 0.125
    replace_artifact(path, value)
    with pytest.raises(ValueError, match="saved check receipt"):
        load(saved_report)


def test_check_aggregate_hash_is_verified_even_with_trusted_outer_receipt(saved_report):
    rewrite_report(
        saved_report,
        lambda value: value["raw_checks_reference"].update(logical_payload_sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="checks logical payload"):
        load(saved_report)


@pytest.mark.parametrize("directory", ["../foreign", "/tmp/unrelated-checks"])
def test_check_root_escape_is_rejected_before_read(saved_report, directory):
    rewrite_report(
        saved_report, lambda value: value["raw_checks_reference"].update(directory=directory)
    )
    with pytest.raises(ValueError, match="check directory"):
        load(saved_report)


def test_original_checkpoint_tail_deletion_cannot_inherit_original_receipt(saved_report):
    path = saved_report["native"] / "checkpoint000003"
    value, _ = run_pilot.read_pilot_artifact(path)
    value["jobs"].pop()
    replace_artifact(path, value)
    with pytest.raises(ValueError, match="checkpoint receipt"):
        load(saved_report)


def test_original_snapshot_digest_is_not_trusted_without_recalculation(saved_report):
    rewrite_report(
        saved_report,
        lambda value: value["raw_snapshot_reference"].update(saved_snapshot_sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="original snapshot digest"):
        load(saved_report)


def test_last_original_job_replacement_fails_original_payload_hash(saved_report):
    path = saved_report["native"] / "job000002"
    value, _ = run_pilot.read_pilot_artifact(path)
    value["reason"] = "changed original fault"
    replace_artifact(path, value)
    with pytest.raises(ValueError, match="immutable original job payload"):
        load(saved_report)


def test_hydrated_aggregate_hash_is_recomputed(saved_report):
    rewrite_report(
        saved_report,
        lambda value: value["raw_snapshot_reference"].update(
            hydrated_logical_payload_sha256="0" * 64
        ),
    )
    with pytest.raises(ValueError, match="hydrated original snapshot"):
        load(saved_report)


def test_report_and_native_restore_without_original_root(saved_report):
    original = saved_report["root"]
    restored = original.with_name("restored-bundle")
    original.rename(restored)
    saved_report["root"] = restored
    saved_report["native"] = restored / "native"
    saved_report["output"] = restored / "saved-check"
    result = load(saved_report)
    assert not original.exists()
    assert result["raw_snapshot"]["artifact_directory"] == str(original / "native")
    assert result["raw_snapshot"]["jobs"][-1]["id"] == "job:2"
    assert result["raw_checks"]["job:1"]["original_n"] == 16


def rewrite_checkpoint_binding(fixture, change):
    path = fixture["native"] / "checkpoint000003"
    value, _ = run_pilot.read_pilot_artifact(path)
    change(value)
    receipt = replace_artifact(path, value)

    def bind(report):
        binding = report["raw_snapshot_reference"]
        binding["receipt"] = receipt
        binding["saved_snapshot"] = value
        binding["saved_snapshot_sha256"] = storage.payload_digest(value)

    rewrite_report(fixture, bind)


def test_self_consistent_original_job_reorder_fails_hydrated_order_hash(saved_report):
    rewrite_checkpoint_binding(saved_report, lambda value: value["jobs"].reverse())
    with pytest.raises(ValueError, match="hydrated original snapshot"):
        load(saved_report)


def test_original_job_id_is_checked_even_after_self_consistent_payload_rebind(saved_report):
    path = saved_report["native"] / "job000002"
    value, _ = run_pilot.read_pilot_artifact(path)
    value["id"] = "different-original-job"
    replace_artifact(path, value)
    rewrite_checkpoint_binding(
        saved_report,
        lambda snapshot: snapshot["jobs"][-1].update(
            raw_job_payload_sha256=storage.payload_digest(value)
        ),
    )
    with pytest.raises(ValueError, match="original job ID"):
        load(saved_report)


def test_original_job_symlink_escape_is_rejected(saved_report):
    path = saved_report["native"] / "job000002"
    outside = saved_report["root"].parent / "outside-native-job"
    path.rename(outside)
    path.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        load(saved_report)


def test_check_directory_symlink_escape_is_rejected(saved_report):
    path = saved_report["output"] / "checks"
    outside = saved_report["root"].parent / "outside-checks"
    path.rename(outside)
    path.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match=r"check directory.*escapes"):
        load(saved_report)


def test_empty_checks_partial_report_keeps_unknown_and_writes_no_manifest(saved_report):
    directory = saved_report["output"] / "checks"
    shutil.rmtree(directory)
    directory.mkdir()
    rewrite_report(
        saved_report,
        lambda report: report["raw_checks_reference"].update(
            references=[], logical_payload_sha256=storage.payload_digest({})
        ),
    )
    result = load(saved_report)
    assert list(result["raw_checks"]) == []
    assert result["closed"] is False
    assert result["financial_qualification"] == "unknown"
    assert result["costs"]["charged_seconds"] is None
    assert list(directory.iterdir()) == []
