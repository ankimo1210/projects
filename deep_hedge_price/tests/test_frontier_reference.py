from __future__ import annotations

import numpy as np

from deep_hedge_price.frontier_reference import (
    benchmark_vol19_calibration,
    build_frontier_reference,
    build_vol19_reference,
    build_vol20_reference,
)


def test_vol19_reference_executes_actual_teachers_calibration_and_refits():
    metrics, arrays = build_vol19_reference(seed=1919, rbergomi_paths=512)

    assert metrics["volume"] == 19
    assert [teacher["method"] for teacher in metrics["teachers"]] == [
        "heston_cos",
        "hagan_sabr_to_bsm",
        "rbergomi_mc_antithetic",
    ]
    assert arrays["teacher_price"].shape == (3, 3, 4)
    assert arrays["teacher_implied_volatility"].shape == (3, 3, 4)
    assert np.all(arrays["teacher_standard_error"][2] > 0)
    assert np.all(arrays["teacher_standard_error"][:2] == 0)

    calibration = metrics["forward_calibration"]
    assert calibration["primary_method"] == "multi_start_forward_calibration"
    assert calibration["n_starts"] == 4
    assert calibration["all_starts_successful"] is True
    assert arrays["calibration_start_initial"].shape == (4, 4)
    assert calibration["repricing_rmse"] < 1e-7
    assert metrics["direct_inverse"]["role"] == "ablation_only"
    direct_parameter_rmse = np.sqrt(
        np.mean(
            (arrays["direct_inverse_test_prediction"] - arrays["direct_inverse_test_truth"]) ** 2
        )
    )
    assert metrics["direct_inverse"]["parameter_rmse"] == direct_parameter_rmse

    reports = metrics["surface_constraints"]["reports"]
    assert reports["raw"]["arbitrage_free"] is False
    assert reports["soft"]["arbitrage_free"] is False
    assert reports["hard"]["arbitrage_free"] is True
    for report in reports.values():
        assert {check["name"] for check in report["checks"]} == {
            "price_bounds",
            "strike_monotonicity",
            "strike_convexity",
            "calendar_monotonicity",
        }
    assert np.all(np.diff(arrays["constraint_hard_price"], axis=0) >= -1e-12)

    refits = metrics["joint_variance_refits"]
    assert refits["actual_refit_per_lambda"] is True
    assert refits["candidate_parameter_unique_count"] == 3
    assert arrays["pareto_fit_parameters"].shape == (3, 2)
    assert np.ptp(arrays["pareto_fit_parameters"], axis=0).max() > 1e-4
    assert len(refits["points"]) == 3
    assert all(point["pareto_nondominated"] for point in refits["points"])
    assert metrics["array_schema"]["teacher_price"]["shape"] == [3, 3, 4]


def test_vol19_cpu_calibration_benchmark_is_validation_only():
    benchmark = benchmark_vol19_calibration(repeats=1, warmup=0, seed=1919)

    assert benchmark["benchmark_kind"] == "wall_clock_validation_only"
    assert benchmark["unit"] == "milliseconds"
    assert benchmark["median_ms"] > 0.0
    assert benchmark["minimum_ms"] <= benchmark["median_ms"] <= benchmark["maximum_ms"]
    assert benchmark["quote_count"] == 12
    assert benchmark["n_starts"] == 4
    assert benchmark["artifact_inclusion"] == "excluded_to_preserve_byte_reproducibility"


def test_vol20_reference_proves_purge_train_only_preprocessing_and_e2e_paths():
    metrics, arrays = build_vol20_reference(seed=2020, hedge_paths=200, hedge_steps=8)

    assert metrics["volume"] == 20
    walk = metrics["walk_forward"]
    assert walk["preprocessing_fit_scope"] == "train_only_each_fold"
    assert walk["n_folds"] >= 3
    bounds = arrays["walk_forward_fold_bounds"]
    for fold, (train_start, train_end, test_start, test_end) in enumerate(bounds):
        assert train_end - 1 + walk["horizon"] + walk["embargo"] < test_start
        np.testing.assert_allclose(
            arrays["walk_forward_scaler_mean"][fold],
            arrays["dynamics_features"][train_start:train_end].mean(axis=0),
        )
        standardized_train = (
            arrays["dynamics_features"][train_start:train_end]
            - arrays["walk_forward_scaler_mean"][fold]
        ) / arrays["walk_forward_scaler_scale"][fold]
        np.testing.assert_allclose(
            arrays["walk_forward_pca_mean"][fold],
            standardized_train.mean(axis=0),
            atol=1e-12,
        )
        fold_test = arrays["walk_forward_test_row"][arrays["walk_forward_prediction_fold"] == fold]
        assert fold_test.min() == test_start
        assert fold_test.max() == test_end - 1

    assert set(walk["models"]) == {
        "persistence",
        "ewma",
        "har_ridge",
        "pca_ridge_challenger",
    }
    for model in walk["models"].values():
        ci = model["qlike_block_bootstrap_ci"]
        assert ci["lower_95"] <= ci["mean"] <= ci["upper_95"]
    assert np.all(arrays["walk_forward_actual"] > 0)
    assert np.all(arrays["walk_forward_prediction_challenger"] > 0)

    assert walk["horizons"] == [1, 5, 21]
    assert walk["target_families"] == {
        "log_realized_variance_horizons": [1, 5, 21],
        "future_realized_variance_horizons": [1, 5, 21],
        "surface_latent_horizons": [1, 5, 21],
        "surface_latent_dimension": 3,
    }
    required_models = {
        "persistence",
        "ewma",
        "garch11",
        "log_har",
        "regularized_linear",
        "pca_ridge_challenger",
        "harnet",
        "tcn",
        "lstm",
        "transformer",
    }
    for horizon in (1, 5, 21):
        horizon_report = walk["model_comparison_by_horizon"][str(horizon)]
        assert set(horizon_report["models"]) == required_models
        assert horizon_report["preprocessing_fit_scope"] == "train_only_each_fold"
        garch_parameters = arrays[f"walk_forward_h{horizon}_garch_parameters"]
        assert np.all(garch_parameters[:, 0] > 0.0)
        assert np.all(garch_parameters[:, 1] + garch_parameters[:, 2] < 1.0)
        horizon_features = arrays[f"walk_forward_h{horizon}_features"]
        horizon_sequences = arrays[f"walk_forward_h{horizon}_sequence_features"]
        for fold, (train_start, train_end, test_start, _test_end) in enumerate(
            arrays[f"walk_forward_h{horizon}_fold_bounds"]
        ):
            assert train_end - 1 + horizon + horizon_report["embargo"] < test_start
            np.testing.assert_allclose(
                arrays[f"walk_forward_h{horizon}_scaler_mean"][fold],
                horizon_features[train_start:train_end].mean(axis=0),
            )
            np.testing.assert_allclose(
                arrays[f"walk_forward_h{horizon}_sequence_scaler_mean"][fold],
                horizon_sequences[train_start:train_end].mean(axis=0),
            )
            np.testing.assert_allclose(
                arrays[f"walk_forward_h{horizon}_regime_thresholds"][fold],
                np.quantile(
                    np.exp(horizon_features[train_start:train_end, 4]),
                    [1 / 3, 2 / 3],
                ),
            )
        for report in horizon_report["models"].values():
            assert set(report["by_regime"]) == {"low", "middle", "high"}
            for scope in (report, *report["by_regime"].values()):
                assert set(scope["intervals_95"]) == {"rmse", "mae", "qlike"}
                for interval in scope["intervals_95"].values():
                    assert interval["lower_95"] <= interval["estimate"] <= interval["upper_95"]

    diagnostics = walk["attention_diagnostics"]
    assert diagnostics["attention_claim"] == "diagnostic_only"
    assert set(diagnostics["methods"]) == {
        "attention",
        "permutation",
        "occlusion",
        "integrated_gradients",
    }
    for name in (
        "attention_importance",
        "permutation_importance",
        "occlusion_importance",
        "integrated_gradients_importance",
    ):
        assert arrays[name].shape == (22,)
        assert np.all(np.isfinite(arrays[name]))

    end_to_end = metrics["end_to_end"]
    assert end_to_end["chain"] == [
        "surrogate",
        "multi_start_calibration",
        "forecast",
        "common_path_hedge",
    ]
    assert arrays["e2e_path_ids"].shape == (200,)
    assert arrays["e2e_hedge_pnl"].shape == (4, 200)
    assert metrics["phase1_deep_policy"]["status"] == "not_evaluated"
    assert "deep-policy" not in end_to_end["strategy_order"]
    assert metrics["phase1_deep_policy"]["positions_adapter_contract"]["shape"] == [200, 8]
    assert end_to_end["comparison_controls"]["pathwise_pairing"] is True
    assert end_to_end["no_trade_region"]["delta_width"] == 0.04
    assert 0.0 <= end_to_end["no_trade_region"]["observed_no_change_fraction"] <= 1.0


def test_vol20_external_positions_adapter_is_explicitly_evaluated():
    positions = np.zeros((100, 4))
    metrics, arrays = build_frontier_reference(
        20,
        seed=2021,
        hedge_paths=100,
        hedge_steps=4,
        phase1_positions=positions,
    )
    assert metrics["phase1_deep_policy"]["status"] == "evaluated_external_positions"
    assert metrics["phase1_deep_policy"]["evaluated_on_common_path_ids"] is True
    assert "deep-policy" in metrics["end_to_end"]["strategy_order"]
    assert arrays["e2e_hedge_pnl"].shape == (5, 100)
    np.testing.assert_array_equal(arrays["e2e_phase1_positions"], positions)


def test_frontier_dispatch_rejects_unknown_volume():
    try:
        build_frontier_reference(18)
    except ValueError as error:
        assert "19 or 20" in str(error)
    else:  # pragma: no cover
        raise AssertionError("unknown volume must be rejected")
