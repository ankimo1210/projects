"""Tiny, non-acceptance F08 execution evidence and saved-result tamper checks."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F08"


@pytest.fixture
def builder():
    path = HERE / "build_reference.py"
    spec = importlib.util.spec_from_file_location("rbf08_execution_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def protocol_file(builder, tmp_path):
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(builder.fixture_protocol(), allow_nan=False))
    return path


@pytest.fixture
def bundle(builder, tmp_path):
    output = tmp_path / "result"
    record = builder.run_reference(
        output, protocol_path=protocol_file(builder, tmp_path), mode="fixture"
    )
    loaded, arrays = builder.load_result(output)
    assert loaded["mode"] == record["mode"] == "fixture"
    return record, arrays, output


def test_tiny_fixture_keeps_all_original_runs_and_sampling_units(builder, bundle):
    record, arrays, _ = bundle
    checked = builder.check_record(record, arrays, fresh=True)
    assert checked["passed"] is True
    assert checked["fixture"] is True
    assert record["main_repetitions"] == 4
    assert record["coverage_repetitions"] == 4
    assert record["teaching_acceptance"] is False
    assert len(record["coverage_cells"]) == 3
    assert record["allocations"][0]["mlmc_paths"] == [16, 8, 4]
    cell = record["budget_cells"][0]
    method = cell["methods"]["mlmc"]
    assert arrays[method["prices_key"]].shape == (4,)
    for run in method["runs"]:
        assert run["summary"]["level_counts"] == [16, 8, 4]
    for coverage in record["coverage_cells"]:
        assert arrays[coverage["estimates_key"]].shape == (4, 4)
        assert coverage["coverage_BSM"]["trials"] == 4


@pytest.mark.parametrize(
    "field", ["price", "standard_error", "coverage", "decision", "allocation", "clip", "review"]
)
def test_json_claims_are_recomputed_from_observations(builder, bundle, field):
    original, arrays, _ = bundle
    record = copy.deepcopy(original)
    if field in {"price", "standard_error"}:
        record["budget_cells"][0]["methods"]["mlmc"]["runs"][0]["summary"][field] += 1
    elif field == "coverage":
        record["coverage_cells"][0]["coverage_BSM"]["coverage"] += 0.1
    elif field == "decision":
        record["decision"]["speedup_supported_vs_euler"] = not record["decision"][
            "speedup_supported_vs_euler"
        ]
    elif field == "allocation":
        record["allocations"][0]["mlmc_paths"][0] += 1
    elif field == "clip":
        record["protocol"]["rqmc"]["clip"]["upper"] = 0.99
    else:
        record["review_digest"] = "f" * 64
    with pytest.raises(ValueError):
        builder.check_record(record, arrays)


@pytest.mark.parametrize("field", ["level_m2", "seed", "coupling", "registry", "negative"])
def test_raw_evidence_and_integer_registry_are_checked(builder, bundle, field):
    original, saved, _ = bundle
    record = copy.deepcopy(original)
    arrays = {key: value.copy() for key, value in saved.items()}
    run = record["budget_cells"][0]["methods"]["mlmc"]["runs"][0]
    if field == "level_m2":
        arrays[run["levels"][0]["moments_key"]][0, 1] += 1
    elif field == "seed":
        arrays[record["coverage_cells"][0]["child_seeds_key"]][0, 0] += 1
    elif field == "coupling":
        arrays[record["coupling_diagnostic"]["coarse_normals_key"]][0, 0] += 1
    elif field == "registry":
        arrays[run["levels"][0]["counts_key"]] = arrays[run["levels"][0]["counts_key"]].astype(
            float
        )
    else:
        arrays[run["levels"][0]["negatives_key"]][0, 2] = 1000
    with pytest.raises(ValueError):
        builder.check_record(record, arrays)


def test_execution_reads_stored_seeds_without_legacy_spawn_or_resolution(
    builder, tmp_path, monkeypatch
):
    path = protocol_file(builder, tmp_path)
    protocol = builder.module("protocol")
    from hullkit import _rqmc_ci

    def forbidden(*args, **kwargs):
        raise AssertionError("seed generation/legacy wrapper must not run after input ledger")

    monkeypatch.setattr(protocol, "build_seed_ledger", forbidden)
    monkeypatch.setattr(protocol, "resolve_seed_roster", forbidden)
    monkeypatch.setattr(_rqmc_ci, "rqmc_gbm_call", forbidden)
    original_sequence = np.random.SeedSequence

    class NoSpawn:
        def __init__(self, *args, **kwargs):
            self.sequence = original_sequence(*args, **kwargs)

        def generate_state(self, *args, **kwargs):
            return self.sequence.generate_state(*args, **kwargs)

        spawn = forbidden

    monkeypatch.setattr(np.random, "SeedSequence", NoSpawn)
    record = builder.run_reference(tmp_path / "stored", protocol_path=path, mode="fixture")
    assert record["main_repetitions"] == 4


def test_fixture_cannot_be_promoted_to_main(builder, tmp_path):
    with pytest.raises(ValueError, match="fixture"):
        builder.run_reference(
            tmp_path / "main", protocol_path=protocol_file(builder, tmp_path), mode="main"
        )
    assert not (tmp_path / "main" / "reference.json").exists()


def test_existing_reference_is_never_overwritten(builder, bundle, tmp_path):
    _, _, output = bundle
    original = (output / "reference.json").read_bytes()
    with pytest.raises(FileExistsError):
        builder.run_reference(
            output, protocol_path=protocol_file(builder, tmp_path), mode="fixture"
        )
    assert (output / "reference.json").read_bytes() == original


def test_failed_original_run_is_saved_without_replacement(builder, tmp_path, monkeypatch):
    from hullkit import _multilevel_mc

    original = _multilevel_mc.gbm_level_samples
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("deliberate nonfinite path")
        return original(*args, **kwargs)

    monkeypatch.setattr(_multilevel_mc, "gbm_level_samples", fail_once)
    output = tmp_path / "failed"
    record = builder.run_reference(
        output, protocol_path=protocol_file(builder, tmp_path), mode="fixture"
    )
    loaded, arrays = builder.load_result(output)
    assert builder.check_record(loaded, arrays)["passed"] is True
    assert record["budget_cells"][0]["status"] == "failed"
    failures = [
        run
        for method in record["budget_cells"][0]["methods"].values()
        for run in method["runs"]
        if run["status"] == "failed"
    ]
    assert len(failures) == 1
    assert (
        sum(len(method["runs"]) for method in record["budget_cells"][0]["methods"].values()) == 16
    )
    assert failures[0]["run"] in range(4)


def test_cli_checks_small_saved_bundle(builder, bundle):
    _, _, output = bundle
    result = subprocess.run(
        [sys.executable, str(HERE / "build_reference.py"), "--check", str(output), "--fresh"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout.lower()


def test_protocol_input_float_changes_are_metadata_not_numerical_tolerance(builder, bundle):
    original, arrays, _ = bundle
    record = copy.deepcopy(original)
    record["cv_beta"] = np.nextafter(record["cv_beta"], np.inf)
    with pytest.raises(ValueError):
        builder.check_record(record, arrays)


@pytest.mark.parametrize(
    "count,size,expected", [(2049, 2048, [2047, 2]), (4097, 2048, [2048, 2047, 2]), (3, 2, [3])]
)
def test_singleton_tail_keeps_every_original_path_in_valid_blocks(builder, count, size, expected):
    assert builder._block_lengths(count, size) == expected


def test_unsupported_euler_keeps_exact_comparators_and_failure_cell(builder, tmp_path):
    p = builder.fixture_protocol()
    allocation = p["fixture"]["allocations"][0]
    allocation.update(
        status="bias_unresolved",
        reason="fixture unresolved bias",
        level=None,
        mlmc_paths=[],
        bias_bound=None,
    )
    allocation["method_status"].update(mlmc="bias_unresolved", plain_euler="bias_unresolved")
    path = tmp_path / "unresolved.json"
    path.write_text(json.dumps(p))
    output = tmp_path / "unresolved"
    record = builder.run_reference(output, protocol_path=path, mode="fixture")
    _, arrays = builder.load_result(output)
    assert record["budget_cells"][0]["status"] == "failed"
    assert record["budget_cells"][0]["methods"]["exact_plain"]["status"] == "valid"
    assert record["budget_cells"][0]["methods"]["exact_cv"]["status"] == "valid"
    assert builder.check_record(record, arrays, fresh=True)["passed"] is True


def test_fresh_receipt_binds_reference_and_keeps_original_cost_pending(builder, bundle):
    record, _, output = bundle
    original = (output / "reference.json").read_bytes()
    result = subprocess.run(
        [sys.executable, str(HERE / "build_reference.py"), "--check", str(output), "--fresh"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((output / "fresh_check.json").read_text())
    assert receipt["schema"] == "RB-F08-fresh-check-v1"
    assert receipt["reference_record_digest"] == builder.module("protocol").json_digest(record)
    assert receipt["seconds"] > 0
    assert receipt["checks"]["passed"] is True
    assert record["fresh_review_pending"] is True
    assert (output / "reference.json").read_bytes() == original


def test_complete_research_cost_includes_rqmc_and_diagnostics(builder, bundle):
    record, _, _ = bundle
    costs = record["costs"]
    assert costs["full_experiment_s"] == pytest.approx(
        costs["total"]["experiment_s"]
        + costs["coverage_main_s"]
        + record["diagnostic_s"]
        + costs["analytic_reference_s"]
    )
    assert costs["full_research_s_before_fresh"] == pytest.approx(
        costs["full_experiment_s"] + record["serialization_s"]
    )


@pytest.mark.parametrize("field", ["method_reason", "budget_reason", "coverage_reason"])
def test_failure_reason_fields_follow_original_roster(builder, bundle, field):
    original, arrays, _ = bundle
    record = copy.deepcopy(original)
    if field == "method_reason":
        record["budget_cells"][0]["methods"]["mlmc"]["reason"] = "unsupported"
    elif field == "budget_reason":
        record["budget_cells"][0]["reason"] = "unsupported"
    else:
        record["coverage_cells"][0]["reason"] = "unsupported"
    with pytest.raises(ValueError):
        builder.check_record(record, arrays)


def test_candidate_without_fixture_still_cannot_execute_main(builder, tmp_path):
    p = builder.fixture_protocol()
    p.pop("fixture")
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="frozen"):
        builder.run_reference(tmp_path / "unreviewed", protocol_path=path, mode="main")


def test_nondefault_reviewed_rqmc_confidence_is_used_by_execution(builder, tmp_path):
    p = builder.fixture_protocol()
    p["rqmc"]["confidence"] = 0.9
    path = tmp_path / "confidence.json"
    path.write_text(json.dumps(p))
    record = builder.run_reference(tmp_path / "confidence", protocol_path=path, mode="fixture")
    assert all(
        row["summary"]["confidence_level"] == pytest.approx(0.9)
        for cell in record["coverage_cells"]
        for row in cell["runs"]
    )


def test_saved_checker_never_generates_bootstrap_or_method_order_randomness(
    builder, bundle, monkeypatch
):
    record, arrays, _ = bundle

    def forbidden(*args, **kwargs):
        raise AssertionError("artifact-only saved checker must not create a RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    assert builder.check_record(record, arrays)["passed"] is True


def test_bootstrap_indices_are_saved_and_original_run_bounds_are_checked(builder, bundle):
    record, saved, _ = bundle
    cell = record["budget_cells"][0]
    key = cell["bootstrap_indices_key"]
    assert saved[key].shape == (32, 4)
    assert np.issubdtype(saved[key].dtype, np.integer)
    arrays = {name: value.copy() for name, value in saved.items()}
    arrays[key][0, 0] = 4
    with pytest.raises(ValueError):
        builder.check_record(record, arrays)


def test_analytic_black_comparator_keeps_one_evaluation_and_actual_time(builder, bundle):
    record, _, _ = bundle
    analytic = record["analytic_reference"]
    assert analytic["method"] == "independent_BSM"
    assert analytic["evaluations"] == 1
    assert analytic["price"] == pytest.approx(
        builder.module("reference_methods").black_call(record["protocol"]["parameters"])
    )
    assert np.isfinite(analytic["seconds"]) and analytic["seconds"] >= 0
    assert record["costs"]["analytic_reference_s"] == analytic["seconds"]


@pytest.mark.parametrize("field", ["price", "seconds"])
def test_analytic_comparator_rejects_false_price_or_invalid_time(builder, bundle, field):
    record, arrays, _ = bundle
    changed = copy.deepcopy(record)
    changed["analytic_reference"][field] = (
        changed["analytic_reference"]["price"] + 1 if field == "price" else -1
    )
    with pytest.raises(ValueError, match="analytic"):
        builder.check_record(changed, arrays)
