"""Saved pilot evidence, complete IID denominators and no fresh checker draws."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity/pilot.py"


def module():
    spec = importlib.util.spec_from_file_location("short_pilot_tests", PATH)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    m = module()
    p = m.protocol.candidate_protocol()
    path = tmp_path_factory.mktemp("short_pilot") / "smoke"
    record, arrays = m.run_pilot(p, path, mode="smoke")
    return m, path, record, arrays


def test_smoke_saved_typed_roster_cannot_support_freeze(saved):
    m, path, record, arrays = saved
    loaded, bundle = m.load_result(path)
    assert loaded == record
    assert set(bundle) == set(arrays)
    assert all(not a.dtype.hasobject for a in bundle.values())
    assert record["smoke"] and record["phase"] == "pilot"
    assert len(record["cases"]) == 2
    result = m.check_record(loaded, bundle)
    assert not result["passed"] and result["selected_sample_count"] is None
    assert "smoke_not_freezable" in result["reasons"]


def test_saved_checker_never_samples_or_calls_an_optimizer(saved, monkeypatch):
    m, _, record, arrays = saved

    def forbidden(*args, **kwargs):
        raise AssertionError("saved pilot checker generated RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    assert m.check_record(record, arrays)["numerical_replay_passed"]


def test_selection_compact_original_prefix_denominator_covariance_and_se(saved):
    _, _, record, arrays = saved
    event = next(c for c in record["cases"] if c["event"] == 1)
    stream = event["streams"][0]
    compact = stream["selection"]
    indices = arrays[compact["active_indices_key"]]
    zero = arrays[compact["zero_values_key"]]
    active = arrays[compact["active_values_key"]]
    full = np.repeat(zero[None, :], compact["sample_count"], axis=0)
    full[indices] = active
    for prefix in stream["prefixes"]:
        n = prefix["sample_count"]
        assert prefix["count"] == n
        assert arrays[prefix["mean_key"]] == pytest.approx(full[:n].mean(0), rel=1e-11, abs=1e-13)
        assert arrays[prefix["covariance_key"]] == pytest.approx(
            np.cov(full[:n], rowvar=False), rel=1e-11, abs=1e-13
        )
        assert arrays[prefix["se_key"]] == pytest.approx(
            full[:n].std(0, ddof=1) / np.sqrt(n), rel=1e-11, abs=1e-13
        )
        assert prefix["actual_random_draws"] == compact["actual_random_draws"]


@pytest.mark.parametrize("field", ["zero_values_key", "active_values_key"])
def test_modified_conditioned_labels_are_rejected(saved, field):
    m, _, record, arrays = saved
    corrupt = {k: v.copy() for k, v in arrays.items()}
    event = next(c for c in record["cases"] if c["event"] == 1)
    key = event["streams"][0]["selection"][field]
    corrupt[key].flat[0] += 0.01
    with pytest.raises(ValueError, match=r"conditioned|zero|active"):
        m.check_record(record, corrupt)


@pytest.mark.parametrize("field", ["mean_key", "m2_matrix_key", "covariance_key", "se_key"])
def test_modified_original_joint_moments_are_rejected(saved, field):
    m, _, record, arrays = saved
    corrupt = {k: v.copy() for k, v in arrays.items()}
    key = record["cases"][1]["streams"][0]["prefixes"][-1][field]
    corrupt[key].flat[0] += 0.01
    with pytest.raises(ValueError, match=r"moment|covariance|se|mean"):
        m.check_record(record, corrupt)


def test_raw_and_crn_save_primitive_draws_not_duplicated_path_values(saved):
    m, _, record, arrays = saved
    raw = record["cases"][1]["streams"][0]["raw"]
    for field in ["counts_key", "z_brown_key", "z_jump_key"]:
        assert arrays[raw[field]].shape == (record["execution"]["raw_sample_count"],)
    assert not any("path_values" in key for key in arrays)
    assert set(raw["methods"]) == {
        "price",
        "pw_delta",
        "lr_delta",
        "lrpw_gamma",
        "lr2_gamma",
        "naive_gamma",
    }
    assert len(raw["crn"]) == 3
    assert m.check_record(record, arrays)["raw_replay_count"] == 2


def test_altered_raw_mean_or_finite_h_target_is_rejected(saved):
    m, _, record, arrays = saved
    for key in [
        record["cases"][1]["streams"][0]["raw"]["joint_mean_key"],
        record["cases"][1]["streams"][0]["raw"]["crn"][0]["target_key"],
    ]:
        corrupt = {k: v.copy() for k, v in arrays.items()}
        corrupt[key].flat[0] += 0.01
        with pytest.raises(ValueError, match=r"raw|CRN|finite.h"):
            m.check_record(record, corrupt)


def test_wrong_roster_or_reserved_seed_not_hidden_by_ready_flags(saved):
    m, _, record, arrays = saved
    bad = copy.deepcopy(record)
    bad["cases"][0]["id"] = "invented"
    with pytest.raises(ValueError, match="roster"):
        m.check_record(bad, arrays)
    bad = copy.deepcopy(record)
    bad["cases"][0]["streams"][0]["selection"]["count_seed"] += 1
    with pytest.raises(ValueError, match="seed"):
        m.check_record(bad, arrays)


def test_forged_full_smoke_roster_is_rejected(saved):
    m, _, record, arrays = saved
    bad = copy.deepcopy(record)
    bad["smoke"] = False
    bad["execution"]["mode"] = "full"
    with pytest.raises(ValueError, match=r"execution|roster"):
        m.check_record(bad, arrays)


def test_full_requires_complete_registry_before_any_randomness(tmp_path, monkeypatch):
    m = module()

    def absent(*, require_complete=True):
        if require_complete:
            raise ValueError("complete source registry required fixture")
        return {}

    def forbidden(*args, **kwargs):
        raise AssertionError("full sampling occurred before registry gate")

    monkeypatch.setattr(m.protocol, "source_registry", absent)
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    with pytest.raises(ValueError, match="complete"):
        m.run_pilot(m.protocol.candidate_protocol(), tmp_path / "full")
    assert not (tmp_path / "full" / "pilot.json").exists()


def test_original_saved_evidence_is_not_overwritten(saved):
    m, path, record, _ = saved
    before = (path / "pilot.json").read_text()
    with pytest.raises(FileExistsError):
        m.run_pilot(record["protocol"], path, mode="smoke")
    assert (path / "pilot.json").read_text() == before


def test_no_event_reports_zero_observed_mc_not_reserved_n(saved):
    _, _, record, arrays = saved
    c = next(c for c in record["cases"] if c["event"] == 0)
    stream = c["streams"][0]
    assert stream["selection"]["actual_random_draws"] == 0
    for prefix in stream["prefixes"]:
        assert prefix["count"] == 0 and prefix["active_count"] == 0
        assert prefix["status"] == "analytic_deterministic"
        assert arrays[prefix["se_key"]] == pytest.approx(np.zeros(3))


def test_cli_check_uses_saved_smoke_and_succeeds_as_numerical_check(saved):
    _, path, _, _ = saved
    result = subprocess.run(
        [sys.executable, str(PATH), "--check", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    checked = json.loads(result.stdout)
    assert checked["numerical_replay_passed"] and not checked["passed"]


def test_reference_math_failure_keeps_every_reserved_case_stream(tmp_path, monkeypatch):
    m = module()

    def failure(*args, **kwargs):
        raise ValueError("fixture mathematical reference failure")

    monkeypatch.setattr(m.reference, "independent_mixture", failure)
    p = m.protocol.candidate_protocol()
    record, _arrays = m.run_pilot(p, tmp_path / "failed", mode="smoke")
    assert not record["complete"]
    assert len(record["cases"]) == 2
    for row in record["cases"]:
        assert row["reference_failure"]["type"] == "ValueError"
        assert [r["replica"] for r in row["streams"]] == [0]
        assert row["streams"][0]["status"] == "not_run"
    checked = m.check_record(*m.load_result(tmp_path / "failed"))
    assert not checked["passed"] and checked["reference_failure_count"] == 2


def test_raw_math_failure_retains_original_draws_and_unknown_slot(tmp_path, monkeypatch):
    m = module()

    def failure(*args, **kwargs):
        raise ValueError("fixture mathematical raw failure")

    monkeypatch.setattr(m.core, "path_values", failure)
    record, arrays = m.run_pilot(
        m.protocol.candidate_protocol(), tmp_path / "raw_failed", mode="smoke"
    )
    assert not record["complete"]
    raw = record["cases"][0]["streams"][0]["raw"]
    assert raw["status"] == "mathematical_failure"
    assert arrays[raw["counts_key"]].shape == (512,)
    assert raw["actual_random_draws"] == 1536
    checked = m.check_record(*m.load_result(tmp_path / "raw_failed"))
    assert checked["raw_failure_count"] == 2


def test_individual_expense_or_actual_count_cost_cannot_be_silently_changed(saved):
    m, _, record, arrays = saved
    wrong = copy.deepcopy(record)
    wrong["expenses"][0]["seconds"] += 1.0
    with pytest.raises(ValueError, match=r"expense|timing"):
        m.check_record(wrong, arrays)
    wrong = copy.deepcopy(record)
    wrong["cases"][1]["streams"][0]["selection"]["count_draws"] += 1
    with pytest.raises(ValueError, match=r"draw|cost"):
        m.check_record(wrong, arrays)


def test_mathematically_valid_float_moment_rounding_uses_tolerance(saved):
    m, _, record, arrays = saved
    slight = copy.deepcopy(record)
    slight["cases"][0]["streams"][0]["raw"]["methods"]["price"]["mean"] += 1e-13
    assert m.check_record(slight, arrays)["numerical_replay_passed"]
