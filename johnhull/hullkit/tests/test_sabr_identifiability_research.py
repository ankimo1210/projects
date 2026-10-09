"""Saved numerical audit and phase separation of the SABR research runner."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F06"


def builder():
    spec = importlib.util.spec_from_file_location("rbf06_test_builder", HERE / "build_reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    m = builder()
    p = m.fixture_protocol()
    directory = tmp_path_factory.mktemp("rbf06_fixture")
    record, arrays = m.run_study(p, "fixture", directory)
    return m, p, directory, record, arrays


def test_small_fixture_is_explicit_and_retains_original_slots(saved):
    m, _, directory, record, arrays = saved
    assert record["phase"] == "fixture"
    assert record["teaching_acceptance"] is False
    assert record["complete"]
    assert len(record["datasets"]) == 4
    assert len({d["dataset_id"] for d in record["datasets"]}) == 4
    for dataset in record["datasets"]:
        unrestricted = [f for f in dataset["fits"] if f["kind"] == "unrestricted"]
        assert len(unrestricted) == 2
        for fit in unrestricted:
            hydrated = m.unpack_fit(fit, arrays)
            assert hydrated["theta"].shape == (3,)
            assert hydrated["scaled_jacobian"].shape[1] == 3
            assert hydrated["holdout_prices"].shape == (6,)
    loaded, values = m.load_result(directory)
    assert m.check_record(loaded, values)["passed"]
    assert all(value.dtype != object for value in values.values())


def test_master_quote_noise_is_shared_by_nested_groups(saved):
    _, _, _, record, arrays = saved
    full = next(d for d in record["datasets"] if d["group"] == "full" and d["rep"] == 0)
    sparse = next(d for d in record["datasets"] if d["group"] == "sparse" and d["rep"] == 0)
    assert full["master_id"] == sparse["master_id"]
    assert arrays[sparse["quotes_key"]] == pytest.approx(
        arrays[full["quotes_key"]][sparse["indices"]]
    )
    assert arrays[full["master_noise_key"]].shape == (7,)


def test_saved_check_has_no_rng_or_optimizer(saved, monkeypatch):
    m, _, _, record, arrays = saved

    def forbidden(*args, **kwargs):
        raise AssertionError("saved checker performed new random experiment")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(m.core, "fit_smile", forbidden)
    assert m.check_record(record, arrays, fresh=False)["passed"]


def test_numerical_noise_roundoff_is_not_a_sha_acceptance_gate(saved):
    m, _, _, record, arrays = saved
    values = {key: value.copy() for key, value in arrays.items()}
    noisy = next(ds for ds in record["datasets"] if ds["rep"] == 0)
    values[noisy["master_noise_key"]][0] += 1e-16
    assert m.check_record(record, values)["passed"]


def test_svd_right_direction_signs_do_not_change_saved_acceptance(saved):
    m, _, _, record, arrays = saved
    values = {key: value.copy() for key, value in arrays.items()}
    fit = record["datasets"][0]["fits"][0]
    values[fit["array_keys"]["right_vectors"]][0] *= -1
    assert m.check_record(record, values)["passed"]


def test_final_serialization_cost_has_separate_original_binding(saved):
    m, _, directory, record, _ = saved
    receipt = m.serialization_receipt(directory, record)
    assert receipt["pending"] is False
    assert receipt["seconds"] >= 0
    assert receipt["protocol_digest"] == record["protocol_digest"]
    assert receipt["reference_record_digest"] == m._digest(record)


@pytest.mark.parametrize(
    "field", ["theta", "q", "raw_residual", "scaled_jacobian", "holdout_prices"]
)
def test_saved_financial_evidence_tamper_is_rejected(saved, field):
    m, _, _, record, arrays = saved
    altered = copy.deepcopy(record)
    values = {key: value.copy() for key, value in arrays.items()}
    fit = altered["datasets"][0]["fits"][0]
    if field == "q":
        fit["q"] += 1
    else:
        values[fit["array_keys"][field]].flat[0] += 0.01
    with pytest.raises(ValueError):
        m.check_record(altered, values)


def test_profile_audits_include_slice_and_all_four_attempts(saved):
    m, p, _, record, arrays = saved
    for dataset in record["datasets"]:
        baseline = next(f for f in dataset["fits"] if f["fit_id"] == dataset["best_converged"])
        theta = m.unpack_fit(baseline, arrays)["theta"]
        for point in dataset["profile_points"]:
            assert len(point["attempts"]) == 4
            literal = theta.copy()
            literal[point["axis"]] = point["value"]
            iv = m.core.sabr_vols(
                p["forward"], p["maturity"], p["beta"], literal, arrays[dataset["strikes_key"]]
            )
            q = np.sum(((iv - arrays[dataset["quotes_key"]]) / p["noise_scale"]) ** 2)
            assert point["slice_q"] == pytest.approx(q)
            assert point["best_finite"] in point["attempts"]
        assert len({(p["axis"], p["value"]) for p in dataset["profile_points"]}) == len(
            dataset["profile_points"]
        )
    assert record["costs"]["solver_calls"] <= p["solver_call_cap"]


def test_failed_optimizer_original_slot_survives(tmp_path, monkeypatch):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"]["profiles"] = False
    original = m.core.fit_smile

    def budget_one(*args, **kwargs):
        kwargs["max_nfev"] = 1
        return original(*args, **kwargs)

    monkeypatch.setattr(m.core, "fit_smile", budget_one)
    record, arrays = m.run_study(p, "fixture", tmp_path)
    fits = [fit for ds in record["datasets"] for fit in ds["fits"]]
    assert len(fits) == 8
    assert all(not fit["success"] and fit["status"] == 0 for fit in fits)
    assert all(ds["best_converged"] is None for ds in record["datasets"])
    assert all(ds["best_finite"] is not None for ds in record["datasets"])
    assert m.check_record(record, arrays)["passed"]


def test_candidate_cannot_draw_main_noise(tmp_path, monkeypatch):
    m = builder()
    p = m.module("protocol").load_protocol()

    def forbidden(*args, **kwargs):
        raise AssertionError("main noise drawn before review/freeze")

    monkeypatch.setattr(m.module("protocol"), "noise_for", forbidden)
    with pytest.raises(ValueError, match="frozen"):
        m.run_study(p, "main", tmp_path)


def test_main_boundary_preserves_frozen_pilot_evidence_rejection(monkeypatch):
    m = builder()
    p = m.fixture_protocol()
    p["state"] = "frozen"
    p["frozen"] = {"pilot_review": {"decision": "approved"}}
    protocol = m.module("protocol")

    # The protocol owns saved-pilot I/O. Isolate this runner's guard contract
    # while its frozen-evidence validator is implemented independently.
    monkeypatch.setattr(protocol, "validate_protocol", lambda value, require_frozen=False: value)

    def reject_unbound(value):
        raise ValueError("frozen pilot evidence is not bound")

    monkeypatch.setattr(protocol, "verify_frozen_evidence", reject_unbound, raising=False)
    with pytest.raises(ValueError, match="pilot evidence"):
        m._binding(p, "main")


def test_completed_study_resume_does_not_refit(saved, monkeypatch):
    m, p, directory, record, arrays = saved

    def forbidden(*args, **kwargs):
        raise AssertionError("completed original slot refitted")

    monkeypatch.setattr(m.core, "fit_smile", forbidden)
    resumed, _ = m.run_study(p, "fixture", directory)
    assert resumed["costs"]["solver_calls"] == record["costs"]["solver_calls"]
    assert m.check_record(resumed, arrays)["passed"]


def test_interrupted_dataset_resumes_original_completed_fit(tmp_path, monkeypatch):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"]["profiles"] = False
    original = m.core.fit_smile
    calls = []

    def interrupt(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise KeyboardInterrupt
        return original(*args, **kwargs)

    monkeypatch.setattr(m.core, "fit_smile", interrupt)
    with pytest.raises(KeyboardInterrupt):
        m.run_study(p, "fixture", tmp_path)
    remaining = []

    def count(*args, **kwargs):
        remaining.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(m.core, "fit_smile", count)
    record, arrays = m.run_study(p, "fixture", tmp_path)
    assert len(remaining) == 6
    assert record["costs"]["solver_calls"] == 8
    assert m.check_record(record, arrays)["passed"]


def test_saved_profile_roster_cannot_drop_a_curve(saved):
    m, _, _, record, arrays = saved
    altered = copy.deepcopy(record)
    altered["datasets"][0]["curves"] = []
    with pytest.raises(ValueError, match="curve"):
        m.check_record(altered, arrays)


def test_saved_curve_cannot_hide_an_initial_crossing_bracket(saved):
    m, _, _, record, arrays = saved
    altered = copy.deepcopy(record)
    curve = next(c for ds in altered["datasets"] for c in ds["curves"] if c["refinement_brackets"])
    curve["refinement_brackets"] = []
    with pytest.raises(ValueError, match="bracket"):
        m.check_record(altered, arrays)


def test_saved_profile_truth_roster_cannot_disappear(saved):
    m, _, _, record, arrays = saved
    altered = copy.deepcopy(record)
    noisy = next(ds for ds in altered["datasets"] if ds["rep"] == 0)
    noisy["truth_points"] = []
    with pytest.raises(ValueError, match="truth"):
        m.check_record(altered, arrays)


def test_invalid_master_quotes_retain_all_original_start_slots(tmp_path, monkeypatch):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"]["profiles"] = False

    def invalid(*args, **kwargs):
        return np.full(7, -1.0)

    monkeypatch.setattr(m.module("protocol"), "noise_for", invalid)
    record, arrays = m.run_study(p, "fixture", tmp_path)
    noisy = [ds for ds in record["datasets"] if ds["rep"] == 0]
    assert len(noisy) == 2
    assert all(ds["invalid_data"] for ds in noisy)
    assert all(len(ds["fits"]) == 2 for ds in noisy)
    assert all(not f["solver_called"] for ds in noisy for f in ds["fits"])
    assert record["costs"]["solver_calls"] == 4
    assert record["costs"]["original_attempt_slots"] == 8
    assert m.check_record(record, arrays)["passed"]


@pytest.fixture(scope="module")
def nonfinite_saved(tmp_path_factory):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"].update(groups=["full", "atm", "sparse"], profiles=False)
    monkeypatch = pytest.MonkeyPatch()

    def invalid(*args, **kwargs):
        result = np.zeros(7)
        result[:3] = [np.nan, np.inf, -np.inf]
        return result

    monkeypatch.setattr(m.module("protocol"), "noise_for", invalid)
    try:
        directory = tmp_path_factory.mktemp("rbf06_nonfinite")
        record, arrays = m.run_study(p, "fixture", directory)
    finally:
        monkeypatch.undo()
    return m, directory, record, arrays


def test_nonfinite_invalid_master_survives_generation_storage_and_saved_check(nonfinite_saved):
    m, directory, _, _ = nonfinite_saved
    record, arrays = m.load_result(directory)
    noisy = [ds for ds in record["datasets"] if ds["rep"] == 0]
    assert len(noisy) == 3
    assert all(ds["invalid_data"] and len(ds["fits"]) == 2 for ds in noisy)
    assert all(f["status"] == -998 and not f["solver_called"] for ds in noisy for f in ds["fits"])
    noise = arrays[noisy[0]["master_noise_key"]]
    assert np.isnan(noise[0]) and np.isposinf(noise[1]) and np.isneginf(noise[2])
    assert m.check_record(record, arrays, fresh=False)["passed"]


@pytest.mark.parametrize(
    "field,index,value",
    [
        ("master_quotes_key", 0, np.inf),
        ("master_quotes_key", 1, -np.inf),
        ("master_quotes_key", 2, np.nan),
        ("quotes_key", 0, 0.20),
        ("quotes_key", 5, 0.30),
    ],
)
def test_nonfinite_invalid_classification_or_finite_component_tamper_is_rejected(
    nonfinite_saved, field, index, value
):
    m, _, record, arrays = nonfinite_saved
    values = {key: array.copy() for key, array in arrays.items()}
    full = next(ds for ds in record["datasets"] if ds["rep"] == 0 and ds["group"] == "full")
    values[full[field]][index] = value
    with pytest.raises(ValueError):
        m.check_record(record, values, fresh=False)


def test_positive_finite_master_cannot_be_hidden_as_invalid_slots(tmp_path):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"]["profiles"] = False
    record, arrays = m.run_study(p, "fixture", tmp_path)
    altered = copy.deepcopy(record)
    ds = next(d for d in altered["datasets"] if d["rep"] == 0)
    assert np.isfinite(arrays[ds["master_quotes_key"]]).all()
    assert np.all(arrays[ds["master_quotes_key"]] > 0)
    ds.update(
        invalid_data=True,
        invalid_reason="nonpositive_or_nonfinite_master_quote",
        best_finite=None,
        best_converged=None,
    )
    for fit in ds["fits"]:
        fit.update(
            invalid_data=True,
            success=False,
            status=-998,
            q=None,
            solver_called=False,
            residual_calls=0,
            diagnostic_calls=0,
            scalar_iv_evaluations=0,
        )
    altered["costs"] = m._costs(altered["datasets"])
    altered["summary"] = m.module("analytics").summarize(altered, arrays)
    with pytest.raises(ValueError, match="invalid"):
        m.check_record(altered, arrays)


def test_half_published_final_pair_resumes_without_refitting(saved, tmp_path, monkeypatch):
    m, p, directory, _, _ = saved
    import shutil

    shutil.copytree(directory, tmp_path, dirs_exist_ok=True)
    (tmp_path / "reference.json").rename(tmp_path / "reference.json.tmp")

    def forbidden(*args, **kwargs):
        raise AssertionError("final pair recovery refitted original experiment")

    monkeypatch.setattr(m.core, "fit_smile", forbidden)
    record, arrays = m.run_study(p, "fixture", tmp_path)
    assert m.check_record(record, arrays)["passed"]


def test_tiny_positive_nu_keeps_numerical_uncertainty_in_study(tmp_path):
    m = builder()
    p = m.fixture_protocol()
    p["truths"][0]["theta"] = [0.20, 0, 1e-10]
    p["starts"][0] = [0.20, 0, 1e-10]
    p["fixture"].update(groups=["full"], reps=0, start_indices=[0], profiles=False)
    record, arrays = m.run_study(p, "fixture", tmp_path)
    fit = record["datasets"][0]["fits"][0]
    assert fit["numerical_stability"]["status"] == "numerical_unresolved"
    hydrated = m.unpack_fit(fit, arrays)
    assert hydrated["theta"][2] > 0
    assert "analytic_nu_zero" not in hydrated["jacobian_scheme"]
    assert hydrated["stability_scalar_iv_evaluations"] > 0
    assert m.check_record(record, arrays)["passed"]


def test_cli_generation_check_and_fresh_use_toy_contract(tmp_path, capsys):
    m = builder()
    p = m.fixture_protocol()
    p["fixture"]["profiles"] = False
    import json

    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(p))
    directory = tmp_path / "bundle"
    assert m.main(["--phase", "fixture", "--protocol", str(path), "--output", str(directory)]) == 0
    assert m.main(["--check", str(directory)]) == 0
    before = (directory / "reference.json").read_bytes()
    assert m.main(["--check", str(directory), "--fresh"]) == 0
    assert (directory / "reference.json").read_bytes() == before
    assert (directory / "fresh_check.json").exists()
    assert '"passed": true' in capsys.readouterr().out


def test_master_generation_cost_is_counted_once_per_shared_vector(saved):
    _, _, _, record, _ = saved
    assert record["costs"]["master_truth_iv_evaluations"] == 14
    assert record["costs"]["noise_draws"] == 7
    assert record["costs"]["master_generation_seconds"] >= 0
    assert record["costs"]["checkpoint_seconds"] > 0


def test_toy_pilot_never_accesses_holdout_or_main_noise(tmp_path, monkeypatch):
    m = builder()
    p = m.fixture_protocol()
    p["truths"] = p["truths"][:1]
    p["groups"] = {"full": p["groups"]["full"]}
    p["pilot_reps"] = 1
    p["starts"] = [p["starts"][0]]
    p["profile_grids"][2] = [0, 0.30]
    p["profile_refinement_per_curve"] = 0
    original_noise = m.module("protocol").noise_for

    def pilot_noise(protocol, phase, truth, rep):
        assert phase == "pilot"
        return original_noise(protocol, phase, truth, rep)

    def forbidden(*args, **kwargs):
        raise AssertionError("pilot accessed holdout Black prices")

    monkeypatch.setattr(m.module("protocol"), "noise_for", pilot_noise)
    monkeypatch.setattr(m.module("reference_methods"), "black_calls", forbidden)
    record, arrays = m.run_study(p, "pilot", tmp_path)
    assert not any("holdout" in key for key in arrays)
    assert record["costs"]["holdout_iv_evaluations"] == 0
    assert record["costs"]["holdout_truth_iv_evaluations"] == 0
    assert m.check_record(record, arrays)["passed"]


def test_three_group_pilot_roster_survives_sorted_json_roundtrip(tmp_path):
    m = builder()
    p = m.fixture_protocol()
    p["truths"] = p["truths"][:1]
    p["groups"] = {name: p["groups"][name] for name in ("full", "atm", "sparse")}
    p["pilot_reps"] = 1
    p["starts"] = [p["starts"][0]]
    p["profile_grids"][2] = [0, 0.30]
    p["profile_refinement_per_curve"] = 0
    record, arrays = m.run_study(p, "pilot", tmp_path)
    assert len(record["datasets"]) == 6
    assert set(record["protocol"]["groups"]) == {"full", "atm", "sparse"}
    assert m.check_record(record, arrays, fresh=True)["passed"]
