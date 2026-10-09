"""Raw-evidence checking of frozen RB-F04 comparisons and tiny test fixtures."""

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F04"


def _runner():
    path = HERE / "build_reference.py"
    assert path.is_file(), "RB-F04 main runner is not implemented"
    spec = importlib.util.spec_from_file_location("rbf04_research_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_protocol():
    p = json.loads((HERE / "protocol.json").read_text())
    p["state"] = "test"
    p["numerical_precision"] = None
    p.pop("freeze", None)
    # This deterministic-volatility fixture exercises real surface and path
    # code without purporting to satisfy the reviewed Heston research gate.
    p["parameters"]["xi"] = 0.0
    p["main"] = {
        "paths": 128,
        "seeds": [9017, 9029, 9047],
        "steps": [12, 24, 48],
        "block_size": 32,
        "surface": {
            "time_nodes": 5,
            "z_nodes": 9,
            "z_width": 4,
            "times_min": 1 / 4096,
            "order": 256,
            "frequency_scale": 32,
            "density_floor": 1e-10,
            "allow_row_wings": True,
        },
    }
    p["two_date"]["minimum_count"] = 1
    return p


@pytest.fixture(scope="module")
def evidence():
    runner = _runner()
    return runner, *runner._compute_reference(_fixture_protocol())


def test_production_run_requires_frozen_protocol_before_any_paths(tmp_path):
    runner = _runner()
    for state in ("candidate", "test"):
        p = _fixture_protocol()
        p["state"] = state
        with pytest.raises(ValueError, match="frozen"):
            runner.run_reference(tmp_path, protocol=p)
    assert not (tmp_path / "reference.npz").exists()


def test_frozen_without_full_pilot_review_cannot_start(tmp_path):
    p = _fixture_protocol()
    p["state"] = "frozen"
    with pytest.raises(ValueError, match=r"review|pilot"):
        _runner().run_reference(tmp_path, protocol=p)


def test_fixture_keeps_all_seeds_and_fixed_monthly_contract(evidence):
    runner, record, arrays = evidence
    assert record["mode"] == "test_fixture"
    assert record["research_acceptance"] is False
    assert record["decision"]["status"] == "pending_precision_budget"
    assert len(record["seeds"]) == 3
    assert record["combined"]["levels"][-1]["asian"]["difference"]["samples"] == 384
    assert runner.check_record(record, arrays)["passed"]
    for seed in [9017, 9029, 9047]:
        for level in [12, 24, 48]:
            for model in ["heston", "local"]:
                obs = arrays[f"seed.{seed}.{level}.{model}.observations"]
                assert obs.shape == (128, 13)
                assert obs[:, 0] == pytest.approx(np.full(128, 100))
    # GBM with the same Brownian driver is exact across levels and models.
    final = record["combined"]["levels"][-1]
    assert final["asian"]["difference"]["mean"] == pytest.approx(0, abs=1e-11)
    assert final["asian"]["difference"]["standard_error"] == pytest.approx(0, abs=1e-11)
    assert sum(map(sum, final["two_date"]["joint_counts_heston"])) == 384
    assert len(final["two_date"]["joint_counts_heston"]) == 6


def test_combined_mean_and_paired_se_come_from_all_independent_paths(evidence):
    _, record, arrays = evidence
    payoff = []
    for seed in [9017, 9029, 9047]:
        obs = arrays[f"seed.{seed}.48.heston.observations"]
        payoff.extend(np.exp(-0.03) * np.maximum(obs[:, 1:].mean(axis=1) - 100, 0))
    stats = record["combined"]["levels"][-1]["asian"]["heston"]
    assert stats["mean"] == pytest.approx(np.mean(payoff))
    assert stats["standard_error"] == pytest.approx(np.std(payoff, ddof=1) / np.sqrt(384))


@pytest.mark.parametrize("kind", ["path", "failure", "status", "count", "protocol", "decision"])
def test_checker_detects_saved_numeric_and_status_tamper(evidence, kind):
    runner, source, raw = evidence
    record, arrays = copy.deepcopy(source), {key: value.copy() for key, value in raw.items()}
    if kind == "path":
        arrays["seed.9017.48.local.observations"][0, 12] += 5
    elif kind == "failure":
        arrays["seed.9017.48.local.failures"][0] = True
    elif kind == "status":
        key = next(k for k in arrays if k.startswith("seed.9017.48.local.status."))
        arrays[key][0] += 1
    elif kind == "count":
        record["combined"]["levels"][-1]["two_date"]["joint_counts_heston"][0][0] += 1
    elif kind == "protocol":
        record["protocol"]["contract"]["asian_strike"] += 1
    else:
        record["decision"]["status"] = "difference_identified"
    result = runner.check_record(record, arrays)
    assert not result["passed"], kind
    assert result["failures"], kind


def test_failed_path_is_kept_and_invalidates_statistics(evidence):
    runner, source, raw = evidence
    record, arrays = copy.deepcopy(source), {key: value.copy() for key, value in raw.items()}
    prefix = "seed.9017.48.local."
    arrays[prefix + "observations"][0, 12] = np.nan
    arrays[prefix + "failures"][0] = True
    arrays[prefix + "failure_reasons"] = arrays[prefix + "failure_reasons"].astype("U64")
    arrays[prefix + "failure_reasons"][0] = "nonfinite_stock"
    # Recompute from raw evidence; never delete the failed path to get a mean.
    record.update(runner._summarize(arrays, record["protocol"]))
    final = record["combined"]["levels"][-1]
    assert final["asian"]["difference"]["samples"] == 384
    assert final["asian"]["difference"]["supported"] is False
    assert final["asian"]["difference"]["mean"] is None
    assert final["two_date"]["failed_pairs"] == 1
    assert runner.check_record(record, arrays)["passed"]
    # Removing even one path violates the frozen input dimensions.
    arrays[prefix + "observations"] = arrays[prefix + "observations"][1:]
    assert not runner.check_record(record, arrays)["passed"]


def test_saved_round_trip_and_fresh_use_numeric_tolerance(evidence, tmp_path):
    runner, record, arrays = evidence
    runner.save_result(tmp_path, record, arrays)
    assert runner.check(tmp_path)["passed"]
    assert runner.check(tmp_path, fresh=True)["passed"]


def test_surface_grid_tamper_is_checked_against_frozen_dimensions(evidence):
    runner, record, raw = evidence
    arrays = {key: value.copy() for key, value in raw.items()}
    arrays["surface.times"][1] *= 1.01
    result = runner.check_record(record, arrays)
    assert not result["passed"]


def test_existing_saved_run_rejects_changed_protocol_refreeze(evidence, tmp_path):
    runner, record, arrays = evidence
    runner.save_result(tmp_path, record, arrays)
    p = copy.deepcopy(record["protocol"])
    p["state"] = "frozen"
    p["main"]["paths"] *= 2
    with pytest.raises(ValueError, match=r"existing|refreeze|protocol"):
        runner.run_reference(tmp_path, protocol=p)


def test_real_heston_fixture_separates_sampling_from_time_refinement():
    runner, p = _runner(), _fixture_protocol()
    p["parameters"]["xi"] = 0.3
    p["main"]["surface"].update(time_nodes=9, z_nodes=41, order=512, frequency_scale=256)
    record, arrays = runner._compute_reference(p)
    checked = runner.check_record(record, arrays)
    assert checked["passed"], checked["failures"]
    assert record["research_acceptance"] is False
    heston, local = [], []
    for seed in p["main"]["seeds"]:
        for destination, model in ((heston, "heston"), (local, "local")):
            observations = arrays[f"seed.{seed}.48.{model}.observations"]
            destination.extend(
                np.exp(-0.03) * np.maximum(observations[:, 1:].mean(axis=1) - 100, 0)
            )
    difference = np.asarray(local) - heston
    stats = record["combined"]["levels"][-1]["asian"]["difference"]
    assert stats["mean"] == pytest.approx(np.mean(difference))
    assert stats["standard_error"] == pytest.approx(np.std(difference, ddof=1) / np.sqrt(384))
    assert record["combined"]["step_changes"][-1]["heston_asian"]["samples"] == 384


@pytest.mark.parametrize("change", ["unapproved", "different_pilot", "different_surface"])
def test_full_pilot_review_requires_approved_matching_evidence(change):
    p = _fixture_protocol()
    p["state"] = "frozen"
    p["freeze"] = {
        "reviewed": True,
        "pilot_mode": "full",
        "reviewed_by": "independent-review",
        "pilot_sha256": "reviewed-pilot",
        "selected_surface": "baseline",
    }
    review = {
        "status": "approved",
        "pilot_sha256": "reviewed-pilot",
        "selected_surface": "baseline",
    }
    if change == "unapproved":
        review["status"] = "pending"
    elif change == "different_pilot":
        review["pilot_sha256"] = "other-pilot"
    else:
        review["selected_surface"] = "wing4"
    with pytest.raises(ValueError, match="review"):
        _runner()._review_evidence(p, {}, {}, review)


def test_checker_checks_review_blob_against_the_original_provenance():
    runner = _runner()
    import hashlib

    p = _fixture_protocol()
    pilot_text, review_text = '{"mode":"full"}\n', '{"status":"approved"}\n'
    p["freeze"] = {
        "pilot_sha256": hashlib.sha256(pilot_text.encode()).hexdigest(),
        "review_sha256": hashlib.sha256(review_text.encode()).hexdigest(),
    }
    arrays = {
        "metadata.pilot_blob": np.asarray(pilot_text),
        "metadata.review_blob": np.asarray(review_text),
        "metadata.pilot_record": runner._snapshot(json.loads(pilot_text)),
        "metadata.review_record": runner._snapshot(json.loads(review_text)),
    }
    runner._check_review_provenance(arrays, p)
    arrays["metadata.review_blob"] = np.asarray('{"status":"approved","fabricated":true}\n')
    with pytest.raises(ValueError, match="provenance"):
        runner._check_review_provenance(arrays, p)


def test_vanilla_guard_uses_each_model_se_and_frozen_allowances(evidence):
    runner, record, _ = evidence
    p = copy.deepcopy(record["protocol"])
    p["numerical_precision"] = {
        "vanilla_mc_sampling_multiplier": 6.0,
        "vanilla_mc_empirical_step_allowance": 0.125,
    }
    guard = runner._vanilla_guard(record["combined"], p, pde_residual=0.025)
    for model in ("heston", "local"):
        row = guard["quotes"][model]
        raw = record["combined"]["levels"][-1]["vanilla"][model]
        assert row["tolerance"] == pytest.approx(6 * np.array(raw["standard_error"]) + 0.15)
        assert np.asarray(row["passed"]).all()
        assert np.asarray(guard["holdouts"][model]["passed"]).all()
    changed = copy.deepcopy(record["combined"])
    changed["levels"][-1]["vanilla_residuals"]["local"][0][0] = 100.0
    guard = runner._vanilla_guard(changed, p, pde_residual=0.025)
    assert guard["quotes"]["local"]["passed"][0][0] is False
    assert guard["quotes"]["heston"]["passed"][0][0] is True


def test_invalid_precision_contract_is_rejected_before_simulation():
    p = _fixture_protocol()
    p["numerical_precision"] = {"sampling_95_half_width": 0.1}
    with pytest.raises(ValueError, match="numerical_precision"):
        _runner()._validate_protocol(p)


@pytest.mark.parametrize("kind", ["unsupported_visit", "initial_visit"])
def test_rewritten_statistics_cannot_hide_inconsistent_surface_status(evidence, kind):
    runner, source, raw = evidence
    record, arrays = copy.deepcopy(source), {key: value.copy() for key, value in raw.items()}
    prefix = "seed.9017.48.local.status."
    interior = next(key for key in arrays if key.startswith(prefix) and key.endswith("interior"))
    if kind == "unsupported_visit":
        arrays[interior][0] -= 1
        arrays[prefix + "unsupported_surface"] = np.zeros(128, dtype=np.int64)
        arrays[prefix + "unsupported_surface"][0] = 1
    else:
        arrays[interior] += arrays.pop(prefix + "initial_state")
    record.update(runner._summarize(arrays, record["protocol"]))
    result = runner.check_record(record, arrays)
    assert not result["passed"], result


def _approved_contract():
    """Only a review-gate input fixture; it contains no accepted production pilot."""
    p = _fixture_protocol()
    p["numerical_precision"] = {
        "sampling_95_half_width": 0.01,
        "heston_step_empirical_refinement": 0.006,
        "local_step_empirical_refinement": 0.003,
        "pilot_surface_empirical_refinement": 0.0005,
        "pde_vanilla_residual": 0.001,
        "fourier_vanilla_residual": 1e-9,
        "vanilla_mc_sampling_multiplier": 6.0,
        "vanilla_mc_empirical_step_allowance": 0.015,
    }
    p["freeze"] = {
        "reviewed": True,
        "pilot_mode": "full",
        "reviewed_by": "independent-review",
        "pilot_sha256": "reviewed-pilot",
        "selected_surface": "baseline",
    }
    review = {
        "status": "approved",
        "pilot_sha256": "reviewed-pilot",
        "selected_surface": "baseline",
        "main": copy.deepcopy(p["main"]),
        "numerical_precision": copy.deepcopy(p["numerical_precision"]),
    }
    return p, review


@pytest.mark.parametrize(
    "key",
    [
        "sampling_95_half_width",
        "heston_step_empirical_refinement",
        "local_step_empirical_refinement",
        "pilot_surface_empirical_refinement",
        "pde_vanilla_residual",
        "fourier_vanilla_residual",
        "vanilla_mc_sampling_multiplier",
        "vanilla_mc_empirical_step_allowance",
    ],
)
def test_main_rejects_unreviewed_precision_even_after_rewriting_summary(key):
    p, review = _approved_contract()
    p["numerical_precision"][key] = float(np.nextafter(p["numerical_precision"][key], np.inf))
    # Even a one-ULP cap change is an unreviewed protocol change. Numeric
    # replay tolerance is appropriate for outputs, never for approved caps.
    rewritten = {"summary": {"precision_checks": {key: True}, "research_acceptance": True}}
    with pytest.raises(ValueError, match=r"reviewed numerical_precision"):
        _runner()._review_evidence(p, rewritten, {}, review)


@pytest.mark.parametrize("key", ["paths", "seeds", "steps", "block_size", "surface"])
def test_main_rejects_unreviewed_dimensions_even_after_rewriting_summary(key):
    p, review = _approved_contract()
    if key == "seeds":
        p["main"][key][0] += 1
    elif key == "steps":
        p["main"][key][-1] *= 2
    elif key == "surface":
        p["main"][key]["frequency_scale"] *= 2
    else:
        p["main"][key] += 1
    rewritten = {"summary": {"main": copy.deepcopy(p["main"]), "research_acceptance": True}}
    with pytest.raises(ValueError, match=r"reviewed main"):
        _runner()._review_evidence(p, rewritten, {}, review)


@pytest.mark.parametrize("key", ["main", "numerical_precision"])
def test_approval_must_explicitly_record_the_main_contract(key):
    p, review = _approved_contract()
    review.pop(key)
    with pytest.raises(ValueError, match="reviewed " + key):
        _runner()._review_evidence(p, {}, {}, review)


def test_review_snapshot_cannot_drift_from_the_hashed_blob_by_one_ulp():
    import hashlib

    runner = _runner()
    p, review = _approved_contract()
    pilot_text = '{"mode":"full"}\n'
    review_text = json.dumps(review) + "\n"
    p["freeze"].update(
        pilot_sha256=hashlib.sha256(pilot_text.encode()).hexdigest(),
        review_sha256=hashlib.sha256(review_text.encode()).hexdigest(),
    )
    altered = copy.deepcopy(review)
    cap = altered["numerical_precision"]["fourier_vanilla_residual"]
    altered["numerical_precision"]["fourier_vanilla_residual"] = float(np.nextafter(cap, np.inf))
    arrays = {
        "metadata.pilot_blob": np.asarray(pilot_text),
        "metadata.review_blob": np.asarray(review_text),
        "metadata.pilot_record": runner._snapshot(json.loads(pilot_text)),
        "metadata.review_record": runner._snapshot(altered),
    }
    with pytest.raises(ValueError, match="review original JSON evidence"):
        runner._check_review_provenance(arrays, p)
