"""Saved grid report source tests; small real paths are not a formal pilot."""

import copy
import dataclasses
import gc
import json
import shutil
import sys
import weakref
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import check_pilot as checker  # noqa: E402
import run_pilot as pilot  # noqa: E402
from hullkit._dynamic_hedging_conditional import primitive_labels  # noqa: E402
from hullkit._heston_local_surface import HestonParameters  # noqa: E402

SAMPLES = {
    "raw_samples",
    "conditioned_samples",
    "cv_samples",
    "f_samples",
    "f_x_samples",
    "raw_x_samples",
    "conditioned_x_samples",
    "unreplaced_cv_samples",
    "unreplaced_cv_x_samples",
    "aux_raw_samples",
    "aux_conditioned_samples",
}


@pytest.fixture(scope="module")
def saved_grid(tmp_path_factory):
    # Full original coarse roster, with a declared source-unit N/calendar.
    # The production M6 N1024/calendar768 raw is never touched by these tests.
    root = tmp_path_factory.mktemp("teacher-report")
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    times = np.arange(25) / 24
    axes = pilot.teacher_axes("coarse", "Heston")
    driver = pilot.run_teacher_driver_job(
        seed=913,
        original_n=16,
        chunk_paths=6,
        calendar_times=times,
        work_directory=root / "driver",
    )
    planned, nodes = [], []
    for date in range(12):
        for state in axes["state"]:
            coordinate = {"date_index": date, "spot": 100.0, "state": float(state)}
            raw = pilot.run_teacher_job(
                parameters,
                None,
                model="Heston",
                seed=913,
                original_n=16,
                chunk_paths=6,
                calendar_times=times,
                start_index=2 * date,
                spot=100.0,
                state=float(state),
                thresholds=axes["threshold"][date],
                driver=driver,
            )
            path = root / f"node{len(nodes):04d}"
            pilot.write_pilot_artifact(path, raw)
            nodes.append(
                coordinate
                | {"path": str(path), "raw_binding": pilot._teacher_node_binding(path, raw)}
            )
            planned.append(coordinate)

    def rows():
        for node in nodes:
            row, _ = pilot.read_pilot_artifact(node["path"])
            row["surface"] = None
            yield row

    cache = checker.replay.rebuild_asian_cache(
        rows(), parameters, axes, model="heston", evaluation_domains=None
    )["cache"]
    grid = {
        "kind": "teacher_grid",
        "teacher_reference": None,
        "driver": driver,
        "model": "Heston",
        "grid": "coarse",
        "original_n": 16,
        "seed": 913,
        "axes": axes,
        "planned_nodes": planned,
        "nodes": nodes,
        "cache": cache,
        "evaluation_domains": None,
        "status": "executed",
        "unexecuted_node_count": 0,
        "cap_evidence": None,
        "financial_qualification": "unknown",
    }
    pilot.write_pilot_artifact(root / "unit-grid", grid)
    (root / "unit-parameters.json").write_text(
        json.dumps(dataclasses.asdict(parameters), indent=2) + "\n"
    )
    return root, parameters, grid


def arrays(value):
    if isinstance(value, np.ndarray):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from arrays(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from arrays(child)


def no_rng(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("a saved checker regenerated financial RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)


def replace_last(grid, raw, path, *, legacy=False):
    # Literal storage makes numeric tampering reach the independent comparator,
    # rather than merely testing physical storage authentication.
    raw["kind"] = "source_unit_literal_teacher"
    pilot.write_pilot_artifact(path, raw)
    result = copy.deepcopy(grid)
    node = result["nodes"][-1]
    node["path"] = str(path)
    if legacy:
        node.pop("raw_binding", None)
        node["raw_sha256"] = pilot.runner.payload_digest(raw)
    else:
        node["raw_binding"] = pilot._teacher_node_binding(path, raw)
    return result


def test_bounded_grid_keeps_full_default_and_all_original_checks(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    no_rng(monkeypatch)
    full = checker.check_teacher_grid_record(grid, parameters, None)
    bounded = checker.check_teacher_grid_record(grid, parameters, None, report_mode="bounded")
    assert "status" not in full and "status" not in bounded
    assert bounded["original_n"] == 16
    assert bounded["original_node_count"] == bounded["executed_node_count"] == 108
    assert len(bounded["raw_checks"]) == 108
    pilot.runner._same(full["cache"], bounded["cache"], "same full cache")
    for index, (original, compact) in enumerate(
        zip(full["raw_checks"], bounded["raw_checks"], strict=True)
    ):
        assert "labels" in original and "report_mode" not in original
        assert "labels" not in compact and compact["report_mode"] == "bounded"
        assert compact["full_saved_driver_sde_replayed"] is True
        assert compact["financial_qualification"] == "unknown"
        reference = compact["raw_reference"]
        assert reference["node_index"] == index
        assert reference["path"] == grid["nodes"][index]["path"]
        assert reference["raw_binding"] == grid["nodes"][index]["raw_binding"]
        assert reference["node"] == grid["planned_nodes"][index]
        assert "artifact_context" not in reference
        label_ref = compact["labels_reference"]
        assert label_ref["all_original_N_label_values_compared"] is True
        assert label_ref["raw_field"] == "labels"
        assert SAMPLES <= label_ref["array_fields"].keys()
        for key in SAMPLES:
            assert label_ref["array_fields"][key]["shape"] == [16, 33]
            assert np.dtype(label_ref["array_fields"][key]["dtype"]) == np.dtype("float64")
        assert label_ref["array_fields"]["block_means"]["shape"] == [16, 33, 3]
        assert label_ref["array_fields"]["joint_block_covariance"]["shape"] == [198, 198]
        assert all(array.ndim <= 1 and array.size <= 33 for array in arrays(compact))
        summary = {
            key: value
            for key, value in compact.items()
            if key not in ("raw_reference", "labels_reference", "report_mode")
        }
        pilot.runner._same(
            summary,
            {key: value for key, value in original.items() if key != "labels"},
            "unchanged unknown/SE/failure summary",
        )
    # The bounded report itself must stay serializable without runtime context.
    pilot.runner._encode_tree(bounded, {})


@pytest.mark.parametrize(
    "field",
    [
        "f_samples",
        "block_means",
        "joint_block_covariance",
        "status_reasons",
    ],
)
def test_bounded_rejects_last_original_node_label_tamper(saved_grid, tmp_path, monkeypatch, field):
    _, parameters, grid = saved_grid
    raw, _ = pilot.read_pilot_artifact(grid["nodes"][-1]["path"])
    target = raw["labels"][field]
    if target.dtype.kind in "SU":
        target.flat[-1] = "source_unit_tamper"
    else:
        target.flat[-1] += 1
    changed = replace_last(grid, raw, tmp_path / "tampered")
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="mismatch"):
        checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")


def test_bounded_rejects_last_original_path_saved_sde_tamper(saved_grid, tmp_path, monkeypatch):
    _, parameters, grid = saved_grid
    raw, _ = pilot.read_pilot_artifact(grid["nodes"][-1]["path"])
    raw["primitives"]["last_left_spot"][-1] += 1
    changed = replace_last(grid, raw, tmp_path / "primitive-tampered", legacy=True)
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="SDE primitive replay"):
        checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")


def test_bounded_rejects_unknown_saved_cache_outside_summary(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    changed = copy.deepcopy(grid)
    # Check a late original array entry, not just top-level cache metadata.
    saved_value = changed["cache"]["f"][-1, -1, -1]
    changed["cache"]["f"][-1, -1, -1] = saved_value + 1 if np.isfinite(saved_value) else 0
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="saved_cache"):
        checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")


def test_bounded_cacheless_releases_each_raw_and_replayed_label(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    changed = copy.deepcopy(grid)
    changed["cache"] = None
    read = pilot.read_pilot_artifact
    check = checker.check_teacher_record
    raw_refs, label_refs, live_at_read = [], [], []

    def observed_read(path):
        raw, receipt = read(path)
        if str(path).startswith(str(Path(grid["nodes"][0]["path"]).parent / "node")):
            gc.collect()
            live_at_read.append(
                (
                    sum(ref() is not None for ref in raw_refs),
                    sum(ref() is not None for ref in label_refs),
                )
            )
            raw_refs.append(weakref.ref(raw["primitives"]["b"]))
        return raw, receipt

    def observed_check(*args, **kwargs):
        result = check(*args, **kwargs)
        label_refs.append(weakref.ref(result["labels"]["f_samples"]))
        label_refs.append(weakref.ref(result["labels"]["joint_block_covariance"]))
        return result

    monkeypatch.setattr(pilot, "read_pilot_artifact", observed_read)
    monkeypatch.setattr(checker, "check_teacher_record", observed_check)
    no_rng(monkeypatch)
    result = checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")
    gc.collect()
    assert len(result["raw_checks"]) == len(raw_refs) == 108
    assert max(raw for raw, _ in live_at_read) <= 2
    assert max(labels for _, labels in live_at_read) == 0
    assert all(ref() is None for ref in raw_refs + label_refs)
    assert result["status"] == "unclosed_or_declared_cap"
    assert result["financial_qualification"] == "unknown"


def test_bounded_restored_report_is_portable_without_original_root(
    saved_grid, tmp_path, monkeypatch
):
    original, parameters, grid = saved_grid
    changed = copy.deepcopy(grid)
    changed["cache"] = None
    no_rng(monkeypatch)
    expected = checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")
    restored = tmp_path / "restored"
    shutil.copytree(original, restored)
    unavailable = original.with_name(original.name + "-retained-unavailable")
    original.rename(unavailable)
    try:
        actual = checker.check_teacher_grid_record(
            changed,
            parameters,
            None,
            report_mode="bounded",
            artifact_context={"original_root": original, "restored_root": restored},
        )
        assert not original.exists()
        pilot.runner._same(expected, actual, "portable restored bounded report")
        assert all("artifact_context" not in row["raw_reference"] for row in actual["raw_checks"])
        pilot.write_pilot_artifact(tmp_path / "portable-report", actual)
        reread, _ = pilot.read_pilot_artifact(tmp_path / "portable-report")
        pilot.runner._same(actual, reread, "report serialization")
    finally:
        unavailable.rename(original)


def test_bounded_partial_cap_retains_original_denominator_and_unknown(tmp_path, monkeypatch):
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    axes = pilot.teacher_axes("coarse", "Heston")
    raw = pilot.run_teacher_job(
        parameters,
        None,
        model="Heston",
        seed=913,
        original_n=16,
        chunk_paths=6,
        calendar_times=np.arange(25) / 24,
        start_index=0,
        spot=100,
        state=1e-5,
        thresholds=axes["threshold"][0],
        wall_cap_seconds=1e-12,
    )
    path = tmp_path / "partial"
    pilot.write_pilot_artifact(path, raw)
    planned = [
        {"date_index": j, "spot": 100.0, "state": float(s)}
        for j in range(12)
        for s in axes["state"]
    ]
    grid = {
        "teacher_reference": None,
        "driver": None,
        "seed": 913,
        "original_n": 16,
        "grid": "coarse",
        "model": "Heston",
        "axes": axes,
        "planned_nodes": planned,
        "nodes": [
            planned[0] | {"path": str(path), "raw_binding": pilot._teacher_node_binding(path, raw)}
        ],
        "unexecuted_node_count": 107,
        "cache": None,
    }
    no_rng(monkeypatch)
    result = checker.check_teacher_grid_record(grid, parameters, None, report_mode="bounded")
    assert result["status"] == "unclosed_or_declared_cap"
    assert result["original_node_count"] == 108 and result["executed_node_count"] == 1
    row = result["raw_checks"][0]
    assert row["original_n"] == row["unexecuted_n"] == 16 and row["executed_n"] == 0
    assert row["financial_qualification"] == "unknown"
    assert not row.get("full_saved_driver_sde_replayed", False)
    assert "labels_reference" not in row
    assert row["raw_reference"]["raw_binding"] == grid["nodes"][0]["raw_binding"]
    assert raw["cap_evidence"]["consumed"] >= raw["cap_evidence"]["limit"]
    assert np.all(raw["path_status"] == "not_executed_at_declared_cap")


def test_bounded_keeps_invalid_nan_status_and_legacy_binding(saved_grid, tmp_path, monkeypatch):
    _, parameters, grid = saved_grid
    raw, _ = pilot.read_pilot_artifact(grid["nodes"][-1]["path"])
    raw["driver"] = None  # Explicit saved-primitive-only boundary, not a full-SDE claim.
    primitive = raw["primitives"]
    primitive["path_mask"][-1] = False
    primitive["primitive_status"][-1] = "invalid"
    primitive["failure_reasons"][-1] = "source_unit_invalid"
    for key in pilot._PATH_KEYS:
        if primitive[key].dtype.kind == "f":
            primitive[key][-1] = np.nan
    primitive["local_step_status"][-1] = 0
    raw["labels"] = primitive_labels(primitive, raw["thresholds"], blocks=16)
    raw["labels"]["shared_driver_id"] = raw["global_driver_id"]
    raw["labels"]["date_index"] = raw["date_index"]
    changed = replace_last(grid, raw, tmp_path / "invalid", legacy=True)
    changed["cache"] = None
    no_rng(monkeypatch)
    result = checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")
    last = result["raw_checks"][-1]
    assert last["invalid_path_count"] == 1
    assert last["unknown_node_count"] == 33
    assert np.isnan(last["raw_standard_errors"]).all()
    assert last["gate_standard_errors"] == [None] * 33
    assert last["financial_qualification"] == "unknown"
    assert last["full_saved_driver_sde_replayed"] is False
    assert last["labels_reference"]["all_original_N_label_values_compared"] is True
    assert last["raw_reference"]["raw_sha256"] == changed["nodes"][-1]["raw_sha256"]


@pytest.mark.parametrize("operation", ["teacher_grid", "teacher_domain_selection"])
def test_formal_teacher_checker_dispatch_uses_bounded_mode(saved_grid, monkeypatch, operation):
    _, parameters, grid = saved_grid
    no_rng(monkeypatch)
    context = {"parameters": parameters, "surface": None}
    raw = grid
    if operation == "teacher_domain_selection":
        # Binding validation is separately covered by the original pilot tests;
        # its actual returned grid still traverses the real saved checker here.
        monkeypatch.setattr(checker, "check_teacher_domain_selection_record", lambda *a, **k: None)
        context["resolved_arguments"] = {"teacher": grid, "selection_rule": {}}
    result = checker._raw_job_check({"operation": operation, "raw": raw}, context)
    assert len(result["raw_checks"]) == 108
    assert all(
        "labels" not in row and row["report_mode"] == "bounded" for row in result["raw_checks"]
    )
    assert all(row["full_saved_driver_sde_replayed"] for row in result["raw_checks"])


def test_invalid_report_mode_fails_before_any_raw_read(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    monkeypatch.setattr(
        pilot, "read_pilot_artifact", lambda *a, **k: pytest.fail("read before mode validation")
    )
    with pytest.raises(ValueError, match="report mode"):
        checker.check_teacher_grid_record(grid, parameters, None, report_mode="silent")


def test_bounded_cannot_claim_full_coverage_when_cache_consumer_stops_early(
    saved_grid, monkeypatch
):
    _, parameters, grid = saved_grid

    def unfinished_cache(rows, *args, **kwargs):
        next(iter(rows))
        return {"cache": grid["cache"]}

    monkeypatch.setattr(checker.replay, "rebuild_asian_cache", unfinished_cache)
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="validation coverage"):
        checker.check_teacher_grid_record(grid, parameters, None, report_mode="bounded")


def test_bounded_cache_cannot_hide_an_unexecuted_original_node(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    changed = copy.deepcopy(grid)
    changed["nodes"].pop()
    changed["unexecuted_node_count"] = 1
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="hide unexecuted"):
        checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")


def test_bounded_cannot_relabel_a_saved_node_coordinate(saved_grid, monkeypatch):
    _, parameters, grid = saved_grid
    changed = copy.deepcopy(grid)
    changed["nodes"][0]["state"] = 0.04
    changed["cache"] = None
    no_rng(monkeypatch)
    with pytest.raises(ValueError, match="node order"):
        checker.check_teacher_grid_record(changed, parameters, None, report_mode="bounded")
