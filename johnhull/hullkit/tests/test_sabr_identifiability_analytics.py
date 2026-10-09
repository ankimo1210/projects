"""Outcome separation and numerical direction uncertainty in RB-F06."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "research/RB-F06/analytics.py"
    assert path.exists(), "RB-F06 analytics implementation missing"
    spec = importlib.util.spec_from_file_location("rbf06_analytics_test", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_failed_lower_cost_does_not_replace_converged_result():
    best = module().best_records([{"q": 1.0, "success": True}, {"q": 0.1, "success": False}])
    assert best["converged"]["q"] == pytest.approx(1)
    assert best["finite"]["q"] == pytest.approx(0.1)


def test_profile_below_baseline_invalidates_whole_dataset():
    support = module().dataset_support(10.0, [{"q": 9.0, "success": True}], [10.0, 11.0, 12.0])
    assert support["status"] == "unsupported"
    assert support["truth_outcomes"] == ["unknown"] * 3


def test_profile_cannot_be_higher_than_feasible_slice():
    support = module().dataset_support(
        1.0, [{"q": 5.0, "slice_q": 2.0, "success": True}], [1.0, 2.0, 3.0]
    )
    assert support["status"] == "unsupported"


def test_unknown_is_separate_from_excluded_and_original_denominator():
    value = module().inclusion_summary(["included"] * 8 + ["excluded"] * 4 + ["unknown"] * 4)
    assert value["denominator"] == 16
    assert value["included"] == 8 and value["excluded"] == 4 and value["unknown"] == 4
    assert value["known_rate"] == pytest.approx(2 / 3)
    assert value["original_rate_bounds"] == pytest.approx([0.5, 0.75])


def test_nonconnected_profile_crossings_are_all_preserved():
    points = [{"value": float(i), "q": q, "success": True} for i, q in enumerate([0, 5, 0, 5, 0])]
    result = module().profile_segments(points, baseline_q=0.0, threshold=3.84, bounds=[0.0, 4.0])
    assert len(result["crossing_brackets"]) == 4
    assert len(result["observed_components"]) == 3
    assert result["lower_censored"] and result["upper_censored"]
    assert result["guaranteed_full_support"] is False


def test_jacobian_global_relative_error_does_not_certify_small_direction():
    js = [np.diag([1000.0, 1e-3, 0.0]), np.diag([1000.0, 4e-3, 0.0]), np.diag([1000.0, 2e-3, 0.0])]
    result = module().jacobian_stability(js)
    assert result["relative_matrix_change"] < 1e-5
    assert result["status"] == "numerical_unresolved"


def test_exact_rectangular_nullspace_has_stable_rank_two():
    j = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
    result = module().jacobian_stability([j, j, j])
    assert result["status"] == "stable_estimate"
    assert result["ranks"] == [2, 2, 2]


def test_summary_invalidates_all_truth_axes_on_failed_better_fit():
    record = {
        "phase": "fixture",
        "protocol": {
            "truths": [{"name": "test", "theta": [0.2, -0.3, 0.4]}],
            "parameter_scale": [0.2, 0.5, 0.5],
            "profile_threshold": 3.841458820694124,
            "baseline_improvement_tolerance": 1e-6,
            "noiseless_delta_q": 1e-6,
            "noiseless_max_iv_error": 1e-9,
        },
        "datasets": [
            {
                "dataset_id": "toy",
                "truth_index": 0,
                "group": "full",
                "rep": 0,
                "fits": [
                    {
                        "fit_id": "good",
                        "q": 10.0,
                        "success": True,
                        "kind": "unrestricted",
                        "array_keys": {"theta": "good_theta", "raw_residual": "good_residual"},
                    },
                    {
                        "fit_id": "failed",
                        "q": 1.0,
                        "success": False,
                        "kind": "unrestricted",
                        "array_keys": {},
                    },
                ],
                "profile_points": [],
                "truth_points": [],
            }
        ],
    }
    arrays = {"good_theta": np.array([0.2, -0.3, 0.4]), "good_residual": np.array([0.001])}
    result = module().summarize(record, arrays)
    assert result["per_dataset"][0]["support"]["status"] == "unsupported"
    assert result["cells"][0]["pointwise_inclusion"][0]["unknown"] == 1


def test_truth_fixed_feasible_improvement_invalidates_dataset():
    result = module().dataset_support(
        10.0, [], [{"q": 1.0, "success": False}, {"q": 10.0, "success": True}]
    )
    assert result["status"] == "unsupported"
    assert result["truth_outcomes"] == ["unknown", "unknown"]


def test_truth_slice_feasible_improvement_invalidates_dataset():
    result = module().dataset_support(10.0, [], [{"q": 11.0, "success": False, "slice_q": 1.0}])
    assert result["status"] == "unsupported"


def test_exception_costs_are_unknown_not_measured_zero():
    record = {
        "phase": "fixture",
        "protocol": {
            "truths": [{"name": "toy"}],
            "profile_threshold": 3.84,
            "baseline_improvement_tolerance": 1e-6,
        },
        "datasets": [
            {
                "dataset_id": "bad",
                "truth_index": 0,
                "group": "sparse",
                "rep": 0,
                "fits": [
                    {
                        "fit_id": "exception",
                        "kind": "unrestricted",
                        "q": None,
                        "success": False,
                        "array_keys": {},
                        "residual_calls": None,
                        "diagnostic_calls": None,
                        "scalar_iv_evaluations": None,
                        "seconds": None,
                    }
                ],
                "profile_points": [],
                "truth_points": [],
            }
        ],
    }
    result = module().summarize(record, {})
    assert result["cost_totals"]["evaluation_count_unknown_attempts"] == 1
    assert result["cost_totals"]["fit_seconds_unknown_attempts"] == 1
    assert (
        result["cost_totals"]["cost_scope"]
        == "known measured amounts; incomplete if unknown_attempts>0"
    )


def test_failed_finite_profile_attempt_invalidates_pointwise_support():
    points = [
        {"point_id": f"p{i}", "axis": i, "value": 0.2, "q": 10.0, "success": True} for i in range(3)
    ]
    record = {
        "phase": "fixture",
        "protocol": {
            "truths": [{"name": "toy", "theta": [0.2, -0.3, 0.4]}],
            "parameter_scale": [0.2, 0.5, 0.5],
            "profile_threshold": 3.84,
            "baseline_improvement_tolerance": 1e-6,
        },
        "datasets": [
            {
                "dataset_id": "toy",
                "truth_index": 0,
                "group": "full",
                "rep": 0,
                "fits": [
                    {
                        "fit_id": "base",
                        "kind": "unrestricted",
                        "q": 10.0,
                        "success": True,
                        "array_keys": {"theta": "theta", "raw_residual": "residual"},
                    },
                    {
                        "fit_id": "failed_profile",
                        "kind": "profile",
                        "q": 1.0,
                        "success": False,
                        "array_keys": {},
                    },
                ],
                "profile_points": points,
                "truth_points": ["p0", "p1", "p2"],
            }
        ],
    }
    result = module().summarize(
        record, {"theta": np.array([0.2, -0.3, 0.4]), "residual": np.array([0.001])}
    )
    assert result["per_dataset"][0]["support"]["status"] == "unsupported"
