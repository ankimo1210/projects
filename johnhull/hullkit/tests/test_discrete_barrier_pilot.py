"""Pilot records must retain evidence, rather than trusting saved PASS flags."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest


def load_pilot():
    path = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete/pilot.py"
    spec = importlib.util.spec_from_file_location("discrete_barrier_pilot_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_contract_and_experiment_axes_are_fixed():
    config = load_pilot().pilot_config(smoke=False)
    assert config["spots"] == [80.0, 100.0, 115.0, 119.0]
    assert config["maturities"] == [0.25, 1.0, 2.0]
    assert config["monitoring"] == 12
    assert config["gl_orders"] == [32, 64, 128, 256]
    assert config["tail_sigma"] == [10.0, 12.0]
    assert config["mc_paths"] == 32768
    assert config["pilot_seed"] == 6017
    assert config["pde_space"] == [1200, 2400, 4800]
    assert config["pde_time"] == [64, 128, 256]
    assert config["pde_domain"] == [1.0, 1.5, 2.0]
    assert config["domain_dx"] == pytest.approx(0.000625)
    assert config["bump_widths"] == [0.001, 0.0005]


@pytest.fixture(scope="module")
def smoke_result():
    pilot = load_pilot()
    record, arrays = pilot.run_pilot(smoke=True)
    return pilot, record, arrays


def test_smoke_is_not_main_acceptance_and_contains_independent_evidence(smoke_result):
    pilot, record, arrays = smoke_result
    pilot.check_pilot(record, arrays, fresh=True)
    assert record["mode"] == "smoke"
    assert record["eligible_for_main_freeze"] is False
    assert record["config"]["mc_paths"] == 2048
    assert arrays["inputs"].shape == (2, 2)
    assert arrays["gl_values"].shape[-1] == 3
    assert arrays["pde_values"].shape[-1] == 4
    assert arrays["m1_cdf"].shape == (2, 3)
    assert arrays["m1_integral"].shape == (2, 6)
    assert record["summary"]["m1"]["max_price_difference"] < 1e-10
    assert record["summary"]["m1"]["max_delta_difference"] < 1e-8
    assert record["summary"]["mc"]["negative_controls"]["naive_pw"]["status"] == "biased_control"
    assert (
        record["summary"]["mc"]["negative_controls"]["last_conditional_pw"]["status"]
        == "biased_control"
    )


def test_checker_recomputes_means_sample_se_and_separate_counts(smoke_result):
    _, record, arrays = smoke_result
    row = record["summary"]["mc"]["cases"][0]
    raw = arrays["samples__main__0__raw_price"]
    assert row["methods"]["raw_price"]["mean"] == pytest.approx(raw.mean())
    assert row["methods"]["raw_price"]["se"] == pytest.approx(raw.std(ddof=1) / np.sqrt(raw.size))
    assert row["survival_count"] == np.count_nonzero(arrays["survival__main__0"])
    assert row["positive_payoff_count"] == np.count_nonzero(raw > 0)
    assert row["positive_payoff_count"] < row["survival_count"]


def test_tail_probability_price_and_delta_bounds_use_different_units(smoke_result):
    _, record, arrays = smoke_result
    inputs = arrays["inputs"]
    probability = arrays["gl_tail_bounds"][:, :, :, 0]
    cap = 20.0 * np.exp(-0.03 * inputs[:, 1])
    width = 0.2 * np.sqrt(inputs[:, 1] / 12)
    assert np.allclose(
        arrays["gl_tail_bounds"][:, :, :, 1],
        cap[:, None, None] * probability,
        rtol=1e-12,
        atol=0,
    )
    assert np.allclose(
        arrays["gl_tail_bounds"][:, :, :, 2],
        cap[:, None, None] * np.sqrt(probability) / (inputs[:, 0] * width)[:, None, None],
        rtol=1e-12,
        atol=0,
    )
    assert (
        record["summary"]["tail"]["delta_bound_method"]
        == "Cauchy-Schwarz with first-transition score"
    )


@pytest.mark.parametrize("target", ["summary", "raw", "grid", "tail", "conditioned", "oss"])
def test_tampered_numeric_evidence_is_rejected(smoke_result, target):
    pilot, record, arrays = smoke_result
    altered_record = copy.deepcopy(record)
    altered_arrays = {key: value.copy() for key, value in arrays.items()}
    if target == "summary":
        altered_record["summary"]["mc"]["cases"][0]["methods"]["raw_price"]["mean"] += 1
    elif target == "raw":
        altered_arrays["samples__main__0__raw_price"][0] += 10
    elif target == "grid":
        altered_arrays["pde_values"][0, 0, 0] += 1
    elif target == "tail":
        altered_arrays["gl_tail_bounds"][0, 0, 0, 1] += 1
    elif target == "conditioned":
        altered_arrays["samples__main__0__conditioned_delta"][0] += 1
    else:
        altered_arrays["samples__main__0__oss_delta"][0] += 1
    with pytest.raises(ValueError):
        pilot.check_pilot(altered_record, altered_arrays)


def test_saved_pass_flag_cannot_override_recalculated_gate(smoke_result):
    pilot, record, arrays = smoke_result
    altered = copy.deepcopy(record)
    altered["PASS"] = True
    assert pilot.check_pilot(altered, arrays) == pilot.check_pilot(record, arrays)


def test_nonfinite_raw_evidence_is_rejected(smoke_result):
    pilot, record, arrays = smoke_result
    altered = {key: value.copy() for key, value in arrays.items()}
    altered["samples__main__0__raw_delta"][0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        pilot.check_pilot(record, altered)


def test_standard_error_uses_hand_calculated_sample_variance():
    summary = load_pilot()._mean_se(np.array([0.0, 2.0, 4.0, 6.0]))
    assert summary["mean"] == 3.0
    assert summary["se"] == pytest.approx(np.sqrt(5.0 / 3.0))


def test_unsupported_oss_paths_are_preserved_and_not_filtered(monkeypatch):
    pilot = load_pilot()
    original = pilot.teacher.one_step_survival

    def unsupported(*args, **kwargs):
        result = original(*args, **kwargs)
        result["valid"][0] = False
        result["numerical_failure"][0] = True
        result["payoff"][0] = np.nan
        result["delta"][0] = np.nan
        return result

    monkeypatch.setattr(pilot.teacher, "one_step_survival", unsupported)
    record, arrays = pilot.run_pilot(smoke=True)
    pilot.check_pilot(record, arrays)
    case = record["summary"]["mc"]["cases"][0]
    assert case["oss_valid_count"] == 2047
    assert case["oss_failures"]["numerical_failure"] == 1
    assert case["methods"]["oss_price"]["mean"] is None
    assert case["methods"]["oss_delta"]["reference_comparison"] is None
    assert np.isnan(arrays["samples__main__0__oss_price"][0])


def test_pilot_contract_and_rng_provenance_are_checked(smoke_result):
    pilot, record, arrays = smoke_result
    for field in ("contract", "rng"):
        altered = copy.deepcopy(record)
        if field == "contract":
            altered[field]["dividend_yield"] = 0.01
        else:
            altered[field]["entropy"] = 6018
        with pytest.raises(ValueError):
            pilot.check_pilot(altered, arrays)


def test_tiny_tail_bound_cannot_be_replaced_by_zero(smoke_result):
    pilot, record, arrays = smoke_result
    altered = {key: value.copy() for key, value in arrays.items()}
    assert altered["gl_tail_bounds"][0, 0, 0, 0] > 0
    altered["gl_tail_bounds"][0, 0, 0, 0] = 0
    with pytest.raises(ValueError, match="tail"):
        pilot.check_pilot(record, altered)


def test_m1_analytic_conditioning_is_not_a_zero_variance_mc_teacher(smoke_result):
    _, record, _ = smoke_result
    case = next(c for c in record["summary"]["frequency"]["cases"] if c["monitoring"] == 1)
    for method in ("conditioned_price", "conditioned_delta", "last_conditional_pw"):
        result = case["methods"][method]
        assert result["status"] == "analytic_reference"
        assert result["sampling_status"] == "not_MC"
        assert result["se"] is None
        assert result["reference_comparison"] is None
    assert (
        record["summary"]["frequency"]["negative_controls"]["last_conditional_pw"]["case_count"]
        == 1
    )


def test_normal_draws_are_replayed_even_when_dead_path_labels_do_not_change(smoke_result):
    pilot, record, arrays = smoke_result
    altered = {key: value.copy() for key, value in arrays.items()}
    dead = np.flatnonzero(arrays["samples__main__0__conditioned_price"] == 0)[0]
    altered["normal__main__0"][dead, -1] += 0.1
    with pytest.raises(ValueError, match=r"stream|draw"):
        pilot.check_pilot(record, altered)
