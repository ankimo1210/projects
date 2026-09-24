"""Canonical integration-gate checks for johnhull volumes 18--28."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _scalar(value: Any) -> bool | int | float | str | None:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


def _add(
    checks: list[dict[str, Any]],
    name: str,
    observed: Any,
    criterion: str,
    passed: bool,
) -> None:
    checks.append(
        {
            "name": name,
            "observed": _scalar(observed),
            "criterion": criterion,
            "passed": bool(passed),
        }
    )


def _close(stored: Any, recomputed: float, *, rel: float = 1e-12, abs_tol: float = 1e-15) -> bool:
    """A stored scalar agrees with its recomputation from the committed arrays."""
    return math.isclose(float(stored), float(recomputed), rel_tol=rel, abs_tol=abs_tol)


def _rmse_np(error: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(error))))


def _qlike_np(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    ratio = np.asarray(actual, dtype=float) / np.asarray(predicted, dtype=float)
    return ratio - np.log(ratio) - 1.0


def _split_overlap_np(keys: list[np.ndarray]) -> int:
    """Rows shared with any earlier split, counted as the vol-18 manifest does."""
    seen: set[int] = set()
    overlap = 0
    for split in keys:
        current = {int(value) for value in np.asarray(split).tolist()}
        overlap += len(seen & current)
        seen |= current
    return overlap


def _unit_spot_surface_violations(
    prices: np.ndarray, strikes: np.ndarray, maturities: np.ndarray, tolerance: float = 1e-7
) -> dict[str, int]:
    """Vol-19 hard report on a (maturity, strike) call grid with S=1 and r=q=0."""
    values = np.asarray(prices, dtype=float)
    lower = np.maximum(1.0 - np.asarray(strikes, dtype=float), 0.0)
    slopes = np.diff(values, axis=1) / np.diff(strikes)
    ordered = bool(np.all(np.diff(strikes) > 0) and np.all(np.diff(maturities) > 0))
    return {
        "price_bounds": int(np.sum(np.maximum(lower - values, values - 1.0) > tolerance)),
        "strike_monotonicity": int(np.sum(np.diff(values, axis=1) > tolerance)),
        "strike_convexity": int(np.sum(-np.diff(slopes, axis=1) > tolerance)),
        "calendar_monotonicity": int(np.sum(-np.diff(values, axis=0) > tolerance))
        + (0 if ordered else 1),
    }


def _volume18(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    expected = {
        "price_bounds",
        "put_call_parity",
        "strike_monotonicity",
        "strike_convexity",
        "calendar_monotonicity",
        "spot_monotonicity",
        "nonnegative_gamma",
        "greek_consistency",
    }
    names = {str(value) for value in arrays["check_names"].tolist()}
    violations = int(np.sum(arrays["violations_constrained"]))
    overlap = _split_overlap_np(
        [arrays[f"split_row_key_{split}"] for split in ("train", "validation", "test", "ood")]
    )
    _add(
        checks,
        "split_overlap_count",
        overlap,
        "== 0 recomputed from per-split row digests",
        overlap == 0 and metrics["split_overlap_count"] == overlap,
    )
    test_price_mae = float(np.mean(arrays["test_price_abs_error"]))
    slice_consistent = arrays["price_error"].shape == arrays["neural_price"].shape and np.allclose(
        arrays["price_error"],
        np.abs(arrays["neural_price"] - arrays["truth_price"]),
        rtol=0.0,
        atol=1e-15,
    )
    _add(
        checks,
        "price_mae_normalized",
        test_price_mae,
        "< 0.001 as the mean of the test-split per-row errors",
        test_price_mae < 1e-3
        and _close(metrics["price_mae_normalized"], test_price_mae)
        and slice_consistent,
    )
    test_delta_mae = float(np.mean(arrays["test_delta_abs_error"]))
    _add(
        checks,
        "delta_mae",
        test_delta_mae,
        "< 0.002 as the mean of the test-split per-row errors",
        test_delta_mae < 2e-3 and _close(metrics["delta_mae"], test_delta_mae),
    )
    _add(checks, "hard_check_set", len(names), "exact documented 8-check set", names == expected)
    _add(
        checks,
        "hard_check_violations",
        violations,
        "== 0",
        violations == 0 and metrics["hard_violation_rate"] == 0.0,
    )
    residual_better = metrics["heston_bsm_residual_mae"] < metrics["heston_raw_price_mae"]
    _add(
        checks,
        "residual_baseline",
        metrics["heston_bsm_residual_mae"],
        "< raw-price MAE",
        residual_better,
    )
    estimands = [str(value) for value in arrays["teacher_estimand_names"].tolist()]
    reference = arrays["teacher_reference"]
    inside = (arrays["teacher_ci_lower"] <= reference) & (reference <= arrays["teacher_ci_upper"])
    coverage = dict(zip(estimands, np.mean(inside, axis=0).tolist(), strict=True))
    stored_coverage = metrics["teacher_ci_coverage_20_seeds_by_estimand"]
    coverage_ok = (
        arrays["teacher_ci_lower"].shape == arrays["teacher_ci_upper"].shape == (20, len(estimands))
        and set(coverage) == set(stored_coverage)
        and all(0.80 <= value <= 1.0 for value in coverage.values())
        and all(_close(stored_coverage[name], value) for name, value in coverage.items())
    )
    _add(
        checks,
        "mc_ci_coverage",
        min(coverage.values()),
        "each estimand in [0.80, 1.00], recomputed from the 20 seeded intervals",
        coverage_ok,
    )
    small, large = arrays["teacher_se_4x_paths"]
    ratios = dict(zip(estimands, (large / small).tolist(), strict=True))
    stored_ratios = metrics["teacher_se_ratio_4x_paths_by_estimand"]
    ratio_ok = (
        set(ratios) == set(stored_ratios)
        and all(0.40 <= value <= 0.60 for value in ratios.values())
        and all(_close(stored_ratios[name], value) for name, value in ratios.items())
    )
    _add(
        checks,
        "mc_standard_error_scaling",
        max(ratios.values()),
        "each 4x-path ratio in [0.40, 0.60], recomputed from the paired standard errors",
        ratio_ok,
    )
    negative = []
    if not metrics["soft_penalty_improved_hard_checks"]:
        negative.append("The quick soft-penalty ablation did not improve the hard-check count.")
    if metrics["break_even_batch"] is None:
        negative.append(
            "No neural CPU break-even batch was observed in the measured quick profile."
        )
    ood_price_mae = float(np.mean(arrays["ood_price_abs_error"]))
    ood_delta_mae = float(np.mean(arrays["ood_delta_abs_error"]))
    negative.append(
        f"The OOD shell is a stress diagnostic outside the gate: price MAE {ood_price_mae:.4g} "
        f"(median {float(np.median(arrays['ood_price_abs_error'])):.4g}, worst "
        f"{float(np.max(arrays['ood_price_abs_error'])):.4g}, "
        f"{float(np.mean(arrays['ood_price_abs_error'] > 0.01)):.1%} of rows above 0.01) and "
        f"delta MAE {ood_delta_mae:.4g}, against {test_price_mae:.4g} and {test_delta_mae:.4g} "
        "on the test split."
    )
    price = arrays["neural_price"]
    slice_slopes = np.diff(price, axis=1) / np.diff(arrays["moneyness"])
    negative.append(
        "On the exported 21x29 teaching slice (r=2%, q=1%, vol=20%, maturities down to 0.03y) "
        f"the network price breaks spot monotonicity at {int(np.sum(-np.diff(price, axis=1) > 1e-5))}, "
        f"spot convexity at {int(np.sum(-np.diff(slice_slopes, axis=1) > 1e-5))} and calendar "
        f"monotonicity at {int(np.sum(-np.diff(price, axis=0) > 1e-5))} grid steps beyond 1e-5, "
        f"and its mean delta error is {float(np.mean(arrays['delta_error'])):.4g}; the "
        "zero-violation hard report above is a narrower one-year, 25%-vol probe."
    )
    return checks, negative


def _volume19(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    calibration = metrics["forward_calibration"]
    reports = metrics["surface_constraints"]["reports"]
    hard = reports["hard"]
    refits = metrics["joint_variance_refits"]
    points = refits["points"]
    teacher_names = [item["model"] for item in metrics["teachers"]]
    teacher_methods = [item["method"] for item in metrics["teachers"]]
    teacher_se = arrays["teacher_standard_error"]
    teacher_ok = (
        teacher_names == ["heston", "sabr", "rbergomi"]
        and teacher_methods == ["heston_cos", "hagan_sabr_to_bsm", "rbergomi_mc_antithetic"]
        and arrays["teacher_model_code"].tolist() == [0, 1, 2]
        and arrays["teacher_price"].shape
        == arrays["teacher_implied_volatility"].shape
        == teacher_se.shape
        and np.all(np.isfinite(arrays["teacher_price"]))
        and np.all(np.isfinite(arrays["teacher_implied_volatility"]))
        and np.all(teacher_se >= 0)
        and np.all(teacher_se[2] > 0)
        and metrics["common_teacher_schema"]["same_grid_for_all_models"] is True
    )
    _add(
        checks,
        "numerical_teacher_ladder",
        len(teacher_names),
        "Heston/COS, SABR/Hagan, and rBergomi MC on one uncertainty schema",
        teacher_ok,
    )
    _add(
        checks,
        "multi_start_calibration",
        calibration["all_starts_successful"],
        "all starts successful",
        calibration["all_starts_successful"],
    )
    starts_ok = (
        arrays["calibration_start_initial"].shape == arrays["calibration_start_parameters"].shape
        and arrays["calibration_start_repricing_rmse"].shape == (calibration["n_starts"],)
        and len(calibration["evaluations"]) == calibration["n_starts"]
        and np.all(np.isfinite(arrays["calibration_parameter_dispersion"]))
    )
    _add(
        checks,
        "calibration_start_evidence",
        calibration["n_starts"],
        "initial/fitted parameters, errors, evaluations, and dispersion align",
        starts_ok,
    )
    start_rmse = arrays["calibration_start_repricing_rmse"]
    best_start = int(np.argmin(start_rmse))
    best_rmse = float(start_rmse[best_start])
    repricing_ok = (
        best_rmse < 1e-5
        and _close(calibration["repricing_rmse"], best_rmse)
        and np.array_equal(
            arrays["calibration_parameters"], arrays["calibration_start_parameters"][best_start]
        )
        and _close(
            calibration["parameter_rmse"],
            _rmse_np(arrays["calibration_parameters"] - arrays["calibration_truth"]),
        )
    )
    _add(
        checks,
        "forward_repricing_rmse",
        best_rmse,
        "< 1e-5 for the best start, whose parameters are the reported fit",
        repricing_ok,
    )
    strikes = arrays["constraint_strikes"]
    maturities = arrays["constraint_maturities"]

    def _stored_counts(report: dict[str, Any]) -> dict[str, int]:
        return {item["name"]: int(item["n_violations"]) for item in report["checks"]}

    hard_counts = _unit_spot_surface_violations(
        arrays["constraint_hard_price"], strikes, maturities
    )
    hard_complete = (
        hard["check_set_complete"]
        and hard["arbitrage_free"]
        and all(item["passed"] for item in hard["checks"])
        and _stored_counts(hard) == hard_counts
        and sum(hard_counts.values()) == 0
    )
    _add(
        checks,
        "hard_surface_report",
        sum(hard_counts.values()),
        "bounds, strike monotonicity, butterfly and calendar recomputed with zero violations",
        hard_complete,
    )
    raw_counts = _unit_spot_surface_violations(arrays["constraint_raw_price"], strikes, maturities)
    _add(
        checks,
        "raw_stress_detected",
        sum(raw_counts.values()),
        "> 0 recomputed violations on the contaminated surface",
        sum(raw_counts.values()) > 0
        and not reports["raw"]["arbitrage_free"]
        and _stored_counts(reports["raw"]) == raw_counts,
    )
    unique_refits = len(np.unique(np.round(arrays["pareto_fit_parameters"], 10), axis=0))
    distinct_refits = (
        refits["actual_refit_per_lambda"]
        and unique_refits >= 2
        and unique_refits == refits["candidate_parameter_unique_count"]
    )
    _add(
        checks,
        "joint_variance_refits",
        unique_refits,
        ">= 2 distinct actual refits",
        distinct_refits,
    )
    iv_loss = np.mean(
        (arrays["pareto_predicted_iv"] - arrays["pareto_target_iv"][None]) ** 2, axis=(1, 2)
    )
    variance_loss = np.mean(
        (arrays["pareto_predicted_variance"] - arrays["pareto_target_variance"][None]) ** 2,
        axis=1,
    )
    recomputed_losses = np.column_stack(
        (iv_loss + arrays["pareto_lambdas"] * variance_loss, iv_loss, variance_loss)
    )
    variance_improved = (
        len(points) == variance_loss.size
        and variance_loss[-1] < variance_loss[0]
        and all(
            _close(point["variance_loss"], value)
            for point, value in zip(points, variance_loss.tolist(), strict=True)
        )
    )
    _add(
        checks,
        "variance_pareto_improvement",
        float(variance_loss[-1]),
        "< lambda=0 variance loss, recomputed from refitted and target variances",
        variance_improved,
    )
    _add(
        checks,
        "direct_inverse_role",
        metrics["direct_inverse"]["role"],
        "== ablation_only",
        metrics["direct_inverse"]["role"] == "ablation_only",
    )
    inverse_ok = (
        arrays["direct_inverse_test_truth"].shape == arrays["direct_inverse_test_prediction"].shape
        and arrays["direct_inverse_test_quote"].shape
        == arrays["direct_inverse_test_repricing"].shape
        and arrays["direct_inverse_test_truth"].shape[0]
        == arrays["direct_inverse_test_quote"].shape[0]
        == metrics["direct_inverse"]["test_rows"]
        and all(
            np.all(np.isfinite(arrays[name]))
            for name in (
                "direct_inverse_test_truth",
                "direct_inverse_test_prediction",
                "direct_inverse_test_quote",
                "direct_inverse_test_repricing",
            )
        )
        and _close(
            metrics["direct_inverse"]["parameter_rmse"],
            _rmse_np(
                arrays["direct_inverse_test_prediction"] - arrays["direct_inverse_test_truth"]
            ),
        )
        and _close(
            metrics["direct_inverse"]["repricing_rmse"],
            _rmse_np(arrays["direct_inverse_test_repricing"] - arrays["direct_inverse_test_quote"]),
        )
    )
    _add(
        checks,
        "direct_inverse_evidence",
        metrics["direct_inverse"]["test_rows"],
        "aligned ablation arrays reproduce the parameter and repricing RMSE",
        inverse_ok,
    )
    nondominated = np.array(
        [
            not any(
                other[1] <= row[1]
                and other[2] <= row[2]
                and (other[1] < row[1] or other[2] < row[2])
                for other in recomputed_losses
            )
            for row in recomputed_losses
        ],
        dtype=np.int8,
    )
    pareto_ok = (
        arrays["pareto_losses"].shape == (len(points), 3)
        and arrays["pareto_fit_parameters"].shape[0] == len(points)
        and arrays["pareto_nondominated"].shape == (len(points),)
        and np.all(np.isfinite(arrays["pareto_losses"]))
        and np.allclose(arrays["pareto_losses"], recomputed_losses, rtol=1e-12, atol=0.0)
        and np.array_equal(arrays["pareto_nondominated"], nondominated)
        and np.all(nondominated == 1)
    )
    _add(
        checks,
        "pareto_evidence",
        len(points),
        "losses and nondominance recomputed from each refit's predictions",
        pareto_ok,
    )
    negative = [
        "The soft-constrained stress surface still fails at least one hard arbitrage check.",
        "The hard repair is a feasible cumulative projection, not a joint-L2 optimum.",
        "The rough-Bergomi teacher uses a small antithetic Monte Carlo sample for the CPU quick profile.",
    ]
    return checks, negative


def _volume20(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    walk = metrics["walk_forward"]
    bounds = arrays["walk_forward_fold_bounds"]
    purge_ok = bool(np.all(bounds[:, 1] - 1 + walk["horizon"] + walk["embargo"] < bounds[:, 2]))
    _add(
        checks,
        "purged_walk_forward",
        walk["minimum_observed_purge_gap"],
        "> horizon + embargo",
        purge_ok,
    )
    _add(
        checks,
        "train_only_preprocessing",
        walk["preprocessing_fit_scope"],
        "== train_only_each_fold",
        walk["preprocessing_fit_scope"] == "train_only_each_fold",
    )
    targets = walk["target_families"]
    horizons = [1, 5, 21]
    targets_ok = (
        walk["horizons"] == horizons
        and targets["log_realized_variance_horizons"] == horizons
        and targets["future_realized_variance_horizons"] == horizons
        and targets["surface_latent_horizons"] == horizons
        and targets["surface_latent_dimension"] == 3
    )
    _add(
        checks,
        "forecast_target_families",
        len(horizons),
        "1/5/21-day log-RV, future-RV, and 3D surface-latent targets",
        targets_ok,
    )
    required_models = {"persistence", "ewma", "har_ridge", "pca_ridge_challenger"}
    _add(
        checks,
        "forecast_model_ladder",
        len(walk["models"]),
        "contains four required models",
        set(walk["models"]) == required_models,
    )
    full_models = {
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
    comparisons = walk["model_comparison_by_horizon"]
    horizon_ladders_ok = set(comparisons) == {"1", "5", "21"} and all(
        set(comparisons[str(horizon)]["models"]) == full_models
        and comparisons[str(horizon)]["preprocessing_fit_scope"] == "train_only_each_fold"
        and comparisons[str(horizon)]["minimum_observed_purge_gap"]
        > horizon + comparisons[str(horizon)]["embargo"]
        for horizon in horizons
    )
    _add(
        checks,
        "horizon_model_ladders",
        len(full_models),
        "all ten models share purged train-only folds at 1/5/21 days",
        horizon_ladders_ok,
    )
    preprocessing_evidence_ok = True
    for horizon in horizons:
        prefix = f"walk_forward_h{horizon}_"
        folds = arrays[prefix + "fold_bounds"]
        preprocessing_evidence_ok &= (
            folds.shape == (3, 4)
            and arrays[prefix + "scaler_mean"].shape[0] == 3
            and arrays[prefix + "scaler_scale"].shape[0] == 3
            and arrays[prefix + "pca_mean"].shape[0] == 3
            and arrays[prefix + "pca_components"].shape[0] == 3
            and arrays[prefix + "sequence_scaler_mean"].shape[0] == 3
            and arrays[prefix + "sequence_scaler_scale"].shape[0] == 3
            and np.all(
                folds[:, 1] - 1 + horizon + comparisons[str(horizon)]["embargo"] < folds[:, 2]
            )
        )
    _add(
        checks,
        "fold_preprocessing_evidence",
        len(horizons),
        "stored scaler/PCA/sequence fits and purge bounds for every horizon",
        preprocessing_evidence_ok,
    )
    compatibility_arrays = {
        "persistence": "persistence",
        "ewma": "ewma",
        "har_ridge": "har_ridge",
        "pca_ridge_challenger": "challenger",
    }
    intervals_ok = set(walk["models"]) == set(compatibility_arrays)
    for model_name, suffix in compatibility_arrays.items():
        if model_name not in walk["models"]:
            continue
        model = walk["models"][model_name]
        loss = _qlike_np(arrays["walk_forward_actual"], arrays[f"walk_forward_prediction_{suffix}"])
        mean_loss = float(np.mean(loss))
        interval = model["qlike_block_bootstrap_ci"]
        intervals_ok &= bool(
            np.allclose(arrays[f"walk_forward_qlike_{suffix}"], loss, rtol=1e-12, atol=1e-15)
            and _close(model["qlike"], mean_loss)
            and _close(interval["mean"], mean_loss)
            and interval["lower_95"] <= mean_loss <= interval["upper_95"]
        )
    _add(
        checks,
        "block_bootstrap_intervals",
        intervals_ok,
        "ordered for every model around the QLIKE mean recomputed from forecasts",
        intervals_ok,
    )
    regime_names = ("low", "middle", "high")
    detailed_intervals_ok = True
    for horizon in horizons:
        comparison = comparisons[str(horizon)]
        prefix = f"walk_forward_h{horizon}_"
        actual = arrays[prefix + "actual"]
        regime = arrays[prefix + "regime_code"]
        detailed_intervals_ok &= set(
            comparison["paired_qlike_difference_model_minus_log_har"]
        ) == full_models - {"log_har"}
        losses: dict[str, np.ndarray] = {}
        for name, model in comparison["models"].items():
            prediction = arrays[prefix + f"prediction_{name}"]
            loss = _qlike_np(actual, prediction)
            losses[name] = loss
            detailed_intervals_ok &= set(model["by_regime"]) == set(regime_names)
            detailed_intervals_ok &= bool(
                np.allclose(arrays[prefix + f"qlike_{name}"], loss, rtol=1e-12, atol=1e-15)
            )
            scopes = [(model, np.ones(actual.shape, dtype=bool))] + [
                (model["by_regime"][regime_name], regime == code)
                for code, regime_name in enumerate(regime_names)
                if regime_name in model["by_regime"]
            ]
            for scope, selected in scopes:
                count = int(np.sum(selected))
                detailed_intervals_ok &= scope.get("n_observations", count) == count > 0
                if count == 0:
                    continue
                error = prediction[selected] - actual[selected]
                recomputed = {
                    "qlike": float(np.mean(loss[selected])),
                    "rmse": _rmse_np(error),
                    "mae": float(np.mean(np.abs(error))),
                }
                detailed_intervals_ok &= all(
                    _close(scope[key], value)
                    and _close(scope["intervals_95"][key]["estimate"], value)
                    for key, value in recomputed.items()
                )
                detailed_intervals_ok &= all(
                    interval["lower_95"] <= interval["estimate"] <= interval["upper_95"]
                    for interval in scope["intervals_95"].values()
                )
        for name, interval in comparison["paired_qlike_difference_model_minus_log_har"].items():
            detailed_intervals_ok &= bool(
                name in losses
                and "log_har" in losses
                and _close(interval["mean"], float(np.mean(losses[name] - losses["log_har"])))
                and interval["lower_95"] <= interval["mean"] <= interval["upper_95"]
            )
    _add(
        checks,
        "horizon_regime_intervals",
        len(horizons),
        "QLIKE/RMSE/MAE by regime and paired Log-HAR means recomputed from forecasts; CIs ordered",
        detailed_intervals_ok,
    )
    diagnostics = walk["attention_diagnostics"]
    importance_names = (
        "attention_importance",
        "permutation_importance",
        "occlusion_importance",
        "integrated_gradients_importance",
    )
    explainability_ok = (
        diagnostics["role"] == "non_causal_diagnostic_not_feature_explanation"
        and diagnostics["methods"]
        == ["attention", "permutation", "occlusion", "integrated_gradients"]
        and diagnostics["attention_claim"] == "diagnostic_only"
        and all(arrays[name].shape == arrays["attention_lag"].shape for name in importance_names)
        and all(np.all(np.isfinite(arrays[name])) for name in importance_names)
        and np.isfinite(diagnostics["minimum_pairwise_rank_correlation"])
        and np.isfinite(diagnostics["permutation_seed_rank_stability"])
    )
    _add(
        checks,
        "explainability_diagnostics",
        len(diagnostics["methods"]),
        "four finite diagnostics explicitly marked non-causal",
        explainability_ok,
    )
    paths = arrays["e2e_path_ids"].size
    common_paths = (
        arrays["e2e_hedge_pnl"].shape[1] == paths == arrays["e2e_hedge_turnover"].shape[1]
    )
    _add(checks, "common_path_hedge", paths, "P&L and turnover share all path ids", common_paths)
    end_to_end = metrics["end_to_end"]
    controls = end_to_end["comparison_controls"]
    controls_ok = (
        end_to_end["common_path_count"] == paths
        and controls["paths"] == "common"
        and controls["pathwise_pairing"] is True
        and controls["premium"].startswith("common_")
        and controls["transaction_cost_rate"] >= 0
        and end_to_end["strategy_order"] == ["delta", "delta-gamma", "no hedge", "no-trade"]
        and 0 < end_to_end["no_trade_region"]["observed_no_change_fraction"] <= 1
        and end_to_end["no_trade_region"]["observed_no_change_fraction"]
        == end_to_end["strategy_metrics"]["no-trade"]["no_change_fraction"]
    )
    hedge_pnl = arrays["e2e_hedge_pnl"]
    hedge_turnover = arrays["e2e_hedge_turnover"]
    controls_ok &= (
        hedge_pnl.shape[0] == len(end_to_end["strategy_order"]) == hedge_turnover.shape[0]
    )
    for index, name in enumerate(end_to_end["strategy_order"]):
        if not controls_ok:
            break
        loss = -hedge_pnl[index]
        var95 = float(np.quantile(loss, 0.95))
        recomputed = {
            "mean_pnl": float(np.mean(hedge_pnl[index])),
            "hedging_rmse": _rmse_np(hedge_pnl[index]),
            "var95": var95,
            "cvar95": float(np.mean(loss[loss >= var95])),
            "turnover": float(np.mean(hedge_turnover[index])),
        }
        stored = end_to_end["strategy_metrics"][name]
        controls_ok &= all(_close(stored[key], value) for key, value in recomputed.items())
    _add(
        checks,
        "economic_comparison_controls",
        paths,
        "common paths/premium/costs, explicit no-trade region, strategy risk recomputed from P&L",
        controls_ok,
    )
    phase1 = metrics["phase1_deep_policy"]
    phase1_explicit = (
        phase1["status"] in {"not_evaluated", "evaluated_external_positions"}
        and bool(phase1["reason"])
        and (
            (
                phase1["status"] == "not_evaluated"
                and "e2e_phase1_positions" not in arrays
                and phase1["evaluated_on_common_path_ids"] is False
                and phase1["common_premium_and_cost_convention"] is False
            )
            or (
                phase1["status"] == "evaluated_external_positions"
                and arrays["e2e_phase1_positions"].shape
                == tuple(phase1["positions_adapter_contract"]["shape"])
                and phase1["evaluated_on_common_path_ids"] is True
                and phase1["common_premium_and_cost_convention"] is True
            )
        )
    )
    _add(
        checks,
        "phase1_policy_status",
        phase1["status"],
        "explicit evaluated/not_evaluated state",
        phase1_explicit,
    )
    challenger = walk["models"]["pca_ridge_challenger"]["qlike"]
    ewma = walk["models"]["ewma"]["qlike"]
    negative = []
    if challenger >= ewma:
        negative.append(
            f"The PCA-ridge challenger QLIKE ({challenger:.6g}) does not beat EWMA ({ewma:.6g})."
        )
    if phase1["status"] == "not_evaluated":
        negative.append(
            "No real Phase-1 checkpoint positions were supplied to the core reference run."
        )
    negative.extend(
        [
            "Forecast inputs and returns are synthetic; the reported ranking is not market evidence.",
            "Attention, permutation, occlusion, and integrated gradients are diagnostics, not causal explanations.",
        ]
    )
    return checks, negative


def _volume21(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    expected_models = ["PDV", "AFV", "rough-Heston kernel", "quintic OU"]
    model_names = arrays["model_names"].tolist()
    component_arrays = (
        arrays["spx_model_grid"],
        arrays["vix_model_grid"],
        arrays["vix_option_model_grid"],
        arrays["variance_term_model_grid"],
    )
    component_errors = (
        arrays["spx_rmse"],
        arrays["vix_rmse"],
        arrays["vix_option_rmse"],
        arrays["variance_rmse"],
        arrays["joint_loss"],
    )
    ladder_ok = (
        model_names == expected_models
        and all(value.shape[0] == len(expected_models) for value in component_arrays)
        and all(
            value.shape == (len(expected_models),) and np.all(np.isfinite(value))
            for value in component_errors
        )
    )
    _add(
        checks,
        "joint_model_ladder",
        len(model_names),
        "exact four-model ladder with all joint components",
        ladder_ok,
    )
    paired = (
        arrays["teacher_price"].shape == arrays["surrogate_price"].shape
        and arrays["teacher_delta"].shape == arrays["surrogate_delta"].shape
        and arrays["teacher_gamma"].shape == arrays["surrogate_gamma"].shape
    )
    _add(checks, "teacher_surrogate_pairing", paired, "price/delta/gamma shapes match", paired)
    discount = metrics["teacher_discount_factor"]
    future = arrays["teacher_future"]
    strike = 20.0 * arrays["surrogate_features"][:, 2]
    lower = discount * np.maximum(future - strike, 0.0)
    upper = discount * future

    def _bound_violations(price: np.ndarray) -> int:
        return int(np.sum((price < lower - 1e-10) | (price > upper + 1e-10)))

    def _monotonicity_violations(curves: np.ndarray) -> int:
        return int(np.sum(np.diff(curves, axis=1) < -1e-10))

    scale_grid = arrays["monotonicity_scale"]
    hard_ok = (
        future.shape == arrays["teacher_price"].shape
        and np.allclose(arrays["price_lower_bound"], lower, rtol=0.0, atol=1e-12)
        and np.allclose(arrays["price_upper_bound"], upper, rtol=0.0, atol=1e-12)
        and scale_grid.ndim == 1
        and np.all(np.diff(scale_grid) > 0.0)
        and arrays["teacher_scale_price"].shape
        == arrays["surrogate_scale_price"].shape
        == (int((~arrays["ood_flag"].astype(bool)).sum()), scale_grid.size)
        and metrics["teacher_bound_violations"] == _bound_violations(arrays["teacher_price"]) == 0
        and metrics["surrogate_bound_violations"] == _bound_violations(arrays["surrogate_price"])
        and metrics["teacher_spot_monotonicity_violations"]
        == _monotonicity_violations(arrays["teacher_scale_price"])
        == 0
        and metrics["surrogate_spot_monotonicity_violations"]
        == _monotonicity_violations(arrays["surrogate_scale_price"])
    )
    _add(
        checks,
        "surrogate_hard_checks",
        f"{metrics['surrogate_bound_violations']}/{metrics['surrogate_spot_monotonicity_violations']}",
        "futures-option bounds and scale monotonicity recomputed; teacher has zero violations",
        hard_ok,
    )
    teacher_se = arrays["teacher_standard_error"]
    uncertainty_ok = (
        teacher_se.shape == arrays["teacher_price"].shape
        and np.all(np.isfinite(teacher_se))
        and np.all(teacher_se >= 0)
        and np.any(teacher_se > 0)
    )
    _add(
        checks,
        "teacher_uncertainty",
        int(np.count_nonzero(teacher_se > 0)),
        "aligned, nonnegative, and nontrivial standard errors",
        uncertainty_ok,
    )
    _add(
        checks,
        "ood_shell",
        metrics["ood_count"],
        "> 0 flagged observations",
        metrics["ood_count"] > 0 and int(arrays["ood_flag"].sum()) == metrics["ood_count"],
    )
    timings = bool(np.all(arrays["nested_mc_ms"] > 0) and np.all(arrays["surrogate_ms"] > 0))
    _add(
        checks,
        "measured_cpu_timing",
        metrics["timing_method"],
        "positive measured samples",
        timings and metrics["timing_nondeterministic"] is True,
    )
    at_1024 = np.flatnonzero(arrays["batch_size"] == 1024)
    speedup = (
        float(arrays["nested_mc_ms"][at_1024[0]] / arrays["surrogate_ms"][at_1024[0]])
        if at_1024.size == 1
        else float("nan")
    )
    _add(
        checks,
        "surrogate_speedup",
        speedup,
        "> 1 at batch 1024, recomputed from the timing samples",
        speedup > 1.0 and _close(metrics["surrogate_speedup_1024"], speedup),
    )
    joint_components = (
        ("spx_model_grid", "spx_target", "spx_rmse", "joint_spx_rmse"),
        ("vix_model_grid", "vix_target", "vix_rmse", "joint_vix_rmse"),
        ("vix_option_model_grid", "vix_option_target", "vix_option_rmse", "joint_vix_option_rmse"),
        (
            "variance_term_model_grid",
            "variance_term_target",
            "variance_rmse",
            "joint_variance_rmse",
        ),
    )
    joint_reported = True
    for grid_name, target_name, rmse_name, metric_name in joint_components:
        grid = arrays[grid_name]
        target = arrays[target_name]
        rmse = np.sqrt(np.mean((grid - target[None]) ** 2, axis=tuple(range(1, grid.ndim))))
        joint_reported &= bool(
            grid.shape[1:] == target.shape
            and arrays[rmse_name].shape == rmse.shape
            and np.all(np.isfinite(rmse))
            and np.allclose(arrays[rmse_name], rmse, rtol=1e-12, atol=0.0)
            and _close(metrics[metric_name], float(rmse[0]))
        )
    _add(
        checks,
        "joint_objective_components",
        joint_reported,
        "all four component errors finite and recomputed from the model grids and targets",
        joint_reported,
    )
    ood = arrays["ood_flag"].astype(bool)
    greek_errors = {
        "price": arrays["teacher_price"] - arrays["surrogate_price"],
        "delta": arrays["teacher_delta"] - arrays["surrogate_delta"],
        "gamma": arrays["teacher_gamma"] - arrays["surrogate_gamma"],
    }
    domain_diagnostics = bool(
        ood.any()
        and (~ood).any()
        and np.allclose(arrays["ood_error"], np.abs(greek_errors["price"]), rtol=1e-12, atol=0.0)
        and _close(metrics["surrogate_price_rmse"], _rmse_np(greek_errors["price"]))
    )
    for name, error in greek_errors.items():
        if not domain_diagnostics:
            break
        if name != "price":
            domain_diagnostics &= _close(metrics[f"surrogate_{name}_rmse"], _rmse_np(error))
        for scope, mask in (("in_domain", ~ood), ("ood", ood)):
            value = _rmse_np(error[mask])
            domain_diagnostics &= bool(np.isfinite(value)) and _close(
                metrics[f"{scope}_{name}_rmse"], value
            )
    _add(
        checks,
        "in_domain_ood_diagnostics",
        domain_diagnostics,
        "price, delta and gamma RMSE finite in both domains and recomputed from the pairs",
        domain_diagnostics,
    )
    negative = [
        f"The polynomial surrogate delta RMSE is {metrics['surrogate_delta_rmse']:.6g} and gamma RMSE is {metrics['surrogate_gamma_rmse']:.6g}; the nested teacher's bump gamma is ~0 because its payoff is piecewise linear in the index scale, so the gamma error is the surrogate's constant curvature. This is a reported negative result, not a Greek-accuracy approval.",
        f"The surrogate breaks the futures-option price bounds on {metrics['surrogate_bound_violations']} of {len(arrays['surrogate_price'])} evaluation rows and scale monotonicity on {metrics['surrogate_spot_monotonicity_violations']} grid steps; the teacher breaks neither.",
        f"The manufactured joint target has SPX RMSE {metrics['joint_spx_rmse']:.6g} and VIX RMSE {metrics['joint_vix_rmse']:.6g}.",
    ]
    return checks, negative


def _volume22(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    session_ok = (
        metrics["timezone"] == "America/New_York"
        and metrics["session_seconds"] == 23_400.0
        and arrays["seconds_to_settlement"].shape == arrays["minute"].shape
        and np.all(arrays["seconds_to_settlement"] >= 0)
    )
    _add(
        checks,
        "session_convention",
        metrics["timezone"],
        "New York 6.5-hour session with nonnegative settlement clock",
        session_ok,
    )
    clock_ok = (
        arrays["variance_clock"][0] == 0.0
        and arrays["variance_clock"][-1] == 1.0
        and np.all(np.diff(arrays["variance_clock"]) >= 0)
    )
    _add(checks, "variance_clock", arrays["variance_clock"][-1], "monotone from 0 to 1", clock_ok)
    expiry_years = arrays["adjacent_expiry_minutes"] / (252.0 * 390.0)
    forward_variance = np.diff(arrays["total_variance"]) / np.diff(expiry_years)
    model_forward = np.diff(arrays["model_total_variance"]) / np.diff(expiry_years)
    expiry_violations = int(np.sum(model_forward < -1e-12))
    calendar_ok = bool(
        metrics["calendar_violations"] == 0
        and np.all(np.diff(expiry_years) > 0)
        and expiry_violations == 0 == metrics["adjacent_expiry_violations"]
        and arrays["forward_variance"].shape == forward_variance.shape
        and np.allclose(arrays["forward_variance"], forward_variance, rtol=1e-12, atol=0.0)
        and np.all(forward_variance >= 0)
    )
    _add(
        checks,
        "expiry_consistency",
        expiry_violations,
        "zero violations and nonnegative forward variance, recomputed from total variance",
        calendar_ok,
    )
    injected = arrays["event_jump_variance"]
    scheduled = arrays["scheduled_variance"]
    injection_error = float(np.max(np.abs(injected - scheduled)))
    _add(
        checks,
        "event_variance_injection",
        injection_error,
        "jump variance added to the teacher equals the scheduled event variance",
        injected.shape == scheduled.shape
        and bool(np.any(scheduled > 0.0))
        and injection_error <= 1e-12 * float(np.max(scheduled)),
    )
    event_mask = arrays["event_mask"].astype(bool)
    teacher_se = arrays["teacher_standard_error"]
    event_se = float(np.mean(teacher_se[event_mask])) if event_mask.any() else float("nan")
    _add(
        checks,
        "event_teacher_uncertainty",
        event_se,
        "> 0 as the mean event-row standard error",
        teacher_se.shape == arrays["teacher_price"].shape
        and bool(np.all(teacher_se >= 0))
        and event_se > 0
        and _close(metrics["event_teacher_standard_error"], event_se),
    )
    price_error = np.abs(arrays["teacher_price"] - arrays["baseline_price"])
    greek_error = np.abs(arrays["delta"] - arrays["baseline_delta"])
    buckets = arrays["time_of_day"]
    tod_names = arrays["tod_names"].tolist()
    tod_ok = (
        len(tod_names) == len(arrays["price_mae"]) == len(arrays["greek_mae"])
        and tod_names == ["open", "midday", "close"]
        and set(buckets.tolist()) == set(tod_names)
    )
    if tod_ok:
        tod_ok = bool(
            np.allclose(
                arrays["price_mae"],
                [np.mean(price_error[buckets == name]) for name in tod_names],
                rtol=1e-12,
                atol=1e-15,
            )
            and np.allclose(
                arrays["greek_mae"],
                [np.mean(greek_error[buckets == name]) for name in tod_names],
                rtol=1e-12,
                atol=1e-15,
            )
        )
    _add(
        checks,
        "time_of_day_diagnostics",
        len(tod_names),
        "open/midday/close price and Greek MAE recomputed from teacher/baseline pairs",
        tod_ok,
    )
    event_rmse = {
        "price": [_rmse_np(price_error[event_mask]), _rmse_np(price_error[~event_mask])],
        "greek": [_rmse_np(greek_error[event_mask]), _rmse_np(greek_error[~event_mask])],
    }
    split_ok = (
        np.array_equal(event_mask, arrays["scheduled_variance"] > 0.0)
        and bool(event_mask.any())
        and bool((~event_mask).any())
        and np.allclose(arrays["event_price_rmse"], event_rmse["price"], rtol=1e-12, atol=1e-15)
        and np.allclose(arrays["event_greek_rmse"], event_rmse["greek"], rtol=1e-12, atol=1e-15)
        and _close(metrics["event_price_rmse"], event_rmse["price"][0])
        and _close(metrics["non_event_price_rmse"], event_rmse["price"][1])
        and _close(metrics["event_greek_rmse"], event_rmse["greek"][0])
        and _close(metrics["non_event_greek_rmse"], event_rmse["greek"][1])
        and _close(metrics["event_price_mae"], float(np.mean(price_error[event_mask])))
        and _close(metrics["event_greek_mae"], float(np.mean(greek_error[event_mask])))
        and arrays["event_split_names"].tolist() == ["event", "non-event"]
        and int(event_mask.sum()) == metrics["event_count"]
        and int((~event_mask).sum()) == metrics["non_event_count"]
        and arrays["event_price_rmse"].shape == (2,)
        and arrays["event_greek_rmse"].shape == (2,)
        and np.all(np.isfinite(arrays["event_price_rmse"]))
        and np.all(np.isfinite(arrays["event_greek_rmse"]))
        # The announcement ramp enters event rows only: non-event rows run on
        # the baseline schedule.
        and np.array_equal(
            arrays["event_jump_intensity"][~event_mask],
            arrays["non_event_jump_intensity"][~event_mask],
        )
        and bool(
            np.all(
                arrays["event_jump_intensity"][event_mask]
                >= arrays["non_event_jump_intensity"][event_mask]
            )
        )
        and bool(
            np.any(
                arrays["event_jump_intensity"][event_mask]
                > arrays["non_event_jump_intensity"][event_mask]
            )
        )
    )
    _add(
        checks,
        "event_non_event_split",
        f"{metrics['event_count']}/{metrics['non_event_count']}",
        "mask counts and two-way diagnostics agree; the announcement ramp enters event rows only",
        split_ok,
    )
    return checks, [
        "The intraday teacher and event schedule are synthetic fixtures, not causal dealer-flow evidence."
    ]


def _volume23(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    conventions_ok = (
        arrays["convention_names"].tolist()
        == ["in-arrears", "lookback 2bd", "observation shift 2bd", "lockout 2bd"]
        and arrays["coupon_names"].tolist() == ["in-arrears", "in-advance"]
        and arrays["convention_rate"].shape == arrays["convention_accumulation"].shape == (4,)
        and arrays["convention_day_count"].shape[0] == 4
        and arrays["convention_observation_ordinal"].shape == arrays["convention_day_count"].shape
        and np.all(np.isfinite(arrays["coupon_cashflow"]))
    )
    _add(
        checks,
        "rfr_conventions",
        len(arrays["convention_names"]),
        "four observation conventions and both coupon timings",
        conventions_ok,
    )
    # Daily compounding rebuilt from the committed fixings and day counts:
    # prod(1 + r_i d_i / basis) must reproduce the accrual path and the
    # in-arrears accumulation factor, not just the stored hand-check scalar.
    basis = float(metrics["rfr_day_count_basis"])
    daily_rate = np.asarray(arrays["daily_rate"], dtype=float)
    day_count = np.asarray(arrays["day_count"], dtype=float)
    factors = 1.0 + daily_rate * day_count / basis
    accrual_rebuilt = np.cumprod(factors) - 1.0
    accrual_gap = float(np.max(np.abs(accrual_rebuilt - arrays["discrete_accrual"])))
    in_arrears_gap = abs(float(np.prod(factors)) - float(arrays["convention_accumulation"][0]))
    handcheck_error = float(metrics["daily_compounding_handcheck_error"])
    _add(
        checks,
        "daily_compounding_handcheck",
        max(accrual_gap, in_arrears_gap, handcheck_error),
        "prod(1 + r_i d_i / basis) rebuilt from daily_rate and day_count matches the accrual "
        "path and the in-arrears accumulation factor (1e-12); stored hand-check error < 1e-12",
        accrual_gap < 1e-12 and in_arrears_gap < 1e-12 and handcheck_error < 1e-12,
    )
    year_fraction = float(day_count.sum()) / basis
    continuous_rebuilt = np.expm1(np.cumsum(daily_rate * day_count / basis))
    continuous_gap = float(np.max(np.abs(continuous_rebuilt - arrays["continuous_accrual"])))
    limit_error = abs(float(accrual_rebuilt[-1] - continuous_rebuilt[-1])) / year_fraction
    limit_metric_gap = abs(limit_error - float(metrics["continuous_limit_error"]))
    _add(
        checks,
        "continuous_limit",
        limit_error,
        "expm1(sum r_i d_i / basis) rebuilt from the fixings matches continuous_accrual "
        "(1e-12); annualized discrete-minus-continuous rate gap < 1e-5 and equals the "
        "stored error (1e-10)",
        continuous_gap < 1e-12 and limit_error < 1e-5 and limit_metric_gap < 1e-10,
    )
    bachelier_forward = float(metrics["bachelier_forward"])
    bachelier_std = float(metrics["bachelier_normal_vol"]) * math.sqrt(
        float(metrics["bachelier_expiry"])
    )
    option_strike = np.asarray(arrays["strike"], dtype=float)
    bachelier_d = (bachelier_forward - option_strike) / bachelier_std
    bachelier_rebuilt = (bachelier_forward - option_strike) * _norm_cdf_np(
        bachelier_d
    ) + bachelier_std * np.exp(-0.5 * bachelier_d**2) / math.sqrt(2.0 * math.pi)
    closed_form_gap = float(np.max(np.abs(bachelier_rebuilt - arrays["bachelier_price"])))
    quadrature_gap = float(np.max(np.abs(bachelier_rebuilt - arrays["quadrature_price"])))
    _add(
        checks,
        "bachelier_quadrature_handcheck",
        max(closed_form_gap, quadrature_gap),
        "Bachelier call rebuilt from (F, sigma_N, T) on the strike grid matches both the "
        "committed closed-form and quadrature prices (1e-12); stored hand-check error < 1e-12",
        closed_form_gap < 1e-12
        and quadrature_gap < 1e-12
        and float(metrics["quadrature_handcheck_error"]) < 1e-12,
    )
    curve_ok = (
        arrays["curve_names"].tolist() == ["SOFR", "USD collateral OIS", "TONA"]
        and arrays["curve_discount_factor"].shape[0] == 3
        and arrays["curve_forward_rate"].shape == arrays["curve_discount_factor"].shape
        and np.all(np.isfinite(arrays["basis_spread_bp"]))
        and np.ptp(arrays["basis_spread_bp"]) > 0
        and arrays["policy_scenario_names"].tolist() == ["SOFR/FOMC", "EURSTR/ECB"]
        and arrays["collateral_currency_names"].tolist() == ["USD", "JPY"]
    )
    _add(
        checks,
        "multi_curve_policy_collateral",
        len(arrays["curve_names"]),
        "SOFR/OIS/TONA curves plus policy and collateral scenarios",
        curve_ok,
    )
    teacher_ok = metrics["sabr_teacher_nu"] > 0 and np.all(arrays["teacher_standard_error"] > 0)
    _add(
        checks, "nonzero_nu_teacher", metrics["sabr_teacher_nu"], "> 0 with positive SE", teacher_ok
    )
    hagan_error = arrays["hagan_price"] - arrays["teacher_price"]
    grid_shape = (
        arrays["teacher_alpha"].size,
        arrays["teacher_maturity"].size,
        arrays["strike"].size,
    )
    long_cells = np.broadcast_to(
        (arrays["teacher_maturity"] >= np.median(arrays["teacher_maturity"]))[None, :, None],
        grid_shape,
    )
    high_cells = np.broadcast_to(
        (arrays["teacher_alpha"] >= np.median(arrays["teacher_alpha"]))[:, None, None],
        grid_shape,
    )

    def _region_rmse_bp(mask: np.ndarray) -> float:
        return float(1e4 * np.sqrt(np.mean(hagan_error[mask] ** 2)))

    regions_ok = (
        hagan_error.shape == grid_shape
        and arrays["teacher_standard_error"].shape == grid_shape
        and not np.array_equal(long_cells, high_cells)
        and math.isclose(
            _region_rmse_bp(long_cells), metrics["hagan_long_maturity_rmse_bp"], rel_tol=1e-9
        )
        and math.isclose(
            _region_rmse_bp(high_cells), metrics["hagan_high_vol_rmse_bp"], rel_tol=1e-9
        )
        and math.isclose(
            float(1e4 * np.max(np.abs(hagan_error))), metrics["hagan_worst_error_bp"], rel_tol=1e-9
        )
    )
    diagnostics = (
        regions_ok
        and metrics["hagan_static_arbitrage_pass"]
        and metrics["hagan_nonnegative_pass"]
        and metrics["hagan_strike_monotone_pass"]
        and metrics["hagan_strike_convex_pass"]
        and metrics["hagan_calendar_monotone_pass"]
        and all(
            metrics[name] > 0
            for name in (
                "hagan_long_maturity_rmse_bp",
                "hagan_high_vol_rmse_bp",
                "hagan_wing_rmse_bp",
            )
        )
    )
    _add(
        checks,
        "hagan_diagnostics",
        metrics["hagan_worst_error_bp"],
        "alpha x maturity grid; region RMSEs recomputed from arrays; static checks pass",
        diagnostics,
    )
    independent = not np.allclose(arrays["sticky_hedge_error"], arrays["bartlett_hedge_error"])
    _add(
        checks,
        "independent_hedge_paths",
        independent,
        "sticky and Bartlett errors differ",
        independent,
    )
    ladder_ok = (
        np.all(arrays["shifted_teacher_standard_error"] > 0)
        and np.all(arrays["hedge_teacher_standard_error"] > 0)
        and arrays["shifted_sabr_price"].shape
        == arrays["free_boundary_sabr_price"].shape
        == arrays["shifted_teacher_price"].shape
    )
    _add(
        checks,
        "sabr_model_ladder",
        len(arrays["shifted_teacher_price"]),
        "shifted/free-boundary approximations and MC teacher with positive SE",
        ladder_ok,
    )
    return checks, [
        f"Hagan's quick-grid worst error is {metrics['hagan_worst_error_bp']:.6g} bp.",
        "The free-boundary SABR fixture uses an explicit shift boundary rather than an endogenous boundary solve.",
        "Monte Carlo standard errors do not include time-discretization bias.",
    ]


def _volume24(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    contract_ok = (
        arrays["contract_names"].tolist() == ["linear", "inverse", "quanto"]
        and arrays["contract_pnl_long"].shape == arrays["contract_pnl_short"].shape
        and np.allclose(arrays["contract_pnl_long"] + arrays["contract_pnl_short"], 0.0)
        and metrics["contract_long_short_sign_error"] == 0.0
        and metrics["contract_zero_move_error"] == 0.0
    )
    _add(
        checks,
        "perpetual_contract_identities",
        len(arrays["contract_names"]),
        "linear/inverse/quanto long-short and zero-move identities",
        contract_ok,
    )
    # Funding ledger rebuilt per step: long + short + venue transfers net to
    # zero, the cumulative path is the running long cash flow, and settled
    # intervals are the completed multiples of the funding interval.
    funding_long = np.asarray(arrays["funding_long_cashflow"], dtype=float)
    funding_short = np.asarray(arrays["funding_short_cashflow"], dtype=float)
    funding_venue = np.asarray(arrays["funding_venue_cashflow"], dtype=float)
    funding_residual = float(np.max(np.abs(funding_long + funding_short + funding_venue)))
    cumulative_gap = float(np.max(np.abs(np.cumsum(funding_long) - arrays["funding_cashflow"])))
    interval_hours = float(metrics["funding_interval_hours"])
    settled_rebuilt = np.floor(
        np.asarray(arrays["elapsed_hours"], dtype=float) / interval_hours + 1e-9
    )
    settled_gap = float(np.max(np.abs(settled_rebuilt - arrays["funding_settled_intervals"])))

    # Liquidation waterfalls rebuilt leg by leg from the committed method
    # arrays (Hull-style ledger: equity + loss absorbers = trader return + fee).
    method_names = [str(name) for name in arrays["liquidation_method_names"]]
    w_equity = np.asarray(arrays["liquidation_method_equity"], dtype=float)
    w_fee = np.asarray(arrays["liquidation_method_fee"], dtype=float)
    w_trader = np.asarray(arrays["liquidation_method_trader_return"], dtype=float)
    w_auction = np.asarray(arrays["liquidation_method_auction_recovery"], dtype=float)
    w_insurance_used = np.asarray(arrays["liquidation_method_insurance_used"], dtype=float)
    w_adl = np.asarray(arrays["liquidation_method_adl_used"], dtype=float)
    w_social = np.asarray(arrays["liquidation_method_socialized_loss"], dtype=float)
    w_uncovered = np.asarray(arrays["liquidation_method_uncovered_loss"], dtype=float)
    w_before = np.asarray(arrays["liquidation_method_insurance_before"], dtype=float)
    w_after = np.asarray(arrays["liquidation_method_insurance_after"], dtype=float)
    w_sources = w_auction + w_insurance_used + w_adl + w_social + w_uncovered
    conservation_rebuilt = w_equity + w_sources - w_trader - w_fee
    shortfall_gap = float(np.max(np.abs(w_sources - np.maximum(-w_equity, 0.0))))
    trader_gap = float(np.max(np.abs(w_trader - np.maximum(w_equity - w_fee, 0.0))))
    insurance_rebuilt = w_after - w_before - w_fee + w_insurance_used
    conservation_error = float(np.max(np.abs(conservation_rebuilt)))
    conservation_metric_gap = float(
        np.max(np.abs(conservation_rebuilt - arrays["liquidation_method_conservation_error"]))
    )
    cashflow_error = max(
        funding_residual,
        conservation_error,
        float(np.max(np.abs(arrays["amm_identity_error"]))),
        float(np.max(np.abs(arrays["cpmm_swap_identity_error"]))),
    )
    _add(
        checks,
        "cashflow_conservation",
        cashflow_error,
        "funding long+short+venue, waterfall equity+absorbers-trader-fee (both rebuilt from the "
        "committed legs), AMM and CPMM identities all < 1e-12; stored error < 1e-12",
        cashflow_error < 1e-12 and float(metrics["cashflow_conservation_error"]) < 1e-12,
    )
    funding_ok = (
        interval_hours > 0
        and metrics["funding_absolute_cap"] > 0
        and np.all(
            np.abs(arrays["funding_rate"]) <= arrays["funding_rate_cap"] + np.finfo(float).eps
        )
        and np.all(np.diff(arrays["funding_settled_intervals"]) >= 0)
        and settled_gap == 0.0
        and funding_residual < 1e-12
        and cumulative_gap < 1e-12
    )
    _add(
        checks,
        "funding_cap_interval",
        interval_hours,
        "positive interval and absolute cap; settled intervals == floor(elapsed / interval); "
        "long+short+venue == 0 and cumulative funding == cumsum(long) rebuilt from the arrays",
        funding_ok,
    )
    auction = method_names.index("auction") if "auction" in method_names else 0
    solvency_error = max(abs(float(insurance_rebuilt[auction])), float(w_uncovered[auction]))
    solvency_metric_gap = abs(solvency_error - float(metrics["solvency_identity_error"]))
    _add(
        checks,
        "solvency_identity",
        solvency_error,
        "auction insurance identity (after - before - fee + used) rebuilt from the legs and "
        "uncovered loss both < 1e-12; equals the stored error (1e-12)",
        solvency_error < 1e-12 and solvency_metric_gap < 1e-12,
    )
    insurance_error = float(np.max(np.abs(insurance_rebuilt)))
    insurance_metric_gap = abs(
        abs(float(insurance_rebuilt[auction])) - float(metrics["insurance_identity_error"])
    )
    _add(
        checks,
        "insurance_identity",
        insurance_error,
        "insurance_after == insurance_before + fee - insurance_used for every liquidation "
        "method (1e-12); stored auction error matches (1e-12)",
        insurance_error < 1e-12 and insurance_metric_gap < 1e-12,
    )
    ending_ok = (
        float(arrays["adl_notional"][-1]) == float(w_adl[auction]) == metrics["ending_adl_notional"]
        and float(arrays["socialized_loss"][-1])
        == float(w_social[auction])
        == metrics["ending_socialized_loss"]
        and float(arrays["uncovered_loss"][-1])
        == float(w_uncovered[auction])
        == metrics["ending_uncovered_loss"]
        and float(arrays["insurance_used"][-1]) == float(w_insurance_used[auction])
        and float(arrays["insurance_fund"][-1])
        == float(w_after[auction])
        == metrics["ending_insurance_fund"]
        and bool(np.all(arrays["insurance_fund"][:-1] == w_before[auction]))
    )
    waterfall = (
        ending_ok
        and float(w_adl[auction]) > 0
        and float(w_social[auction]) > 0
        and float(w_uncovered[auction]) == 0
        and metrics["solvent"] is True
    )
    _add(
        checks,
        "stress_waterfall",
        float(w_social[auction]),
        "ending ADL/social/uncovered/insurance path equals the auction waterfall legs and the "
        "stored metrics; ADL and social loss > 0 with zero uncovered loss",
        waterfall,
    )
    forced = method_names.index("forced_sale") if "forced_sale" in method_names else 0
    methods_ok = (
        method_names == ["forced_sale", "auction"]
        and conservation_error < 1e-12
        and conservation_metric_gap < 1e-12
        and shortfall_gap < 1e-12
        and trader_gap < 1e-12
        and bool(np.all(w_fee <= np.maximum(w_equity, 0.0) + 1e-12))
        and bool(np.all(w_uncovered == 0))
        and float(w_social[auction]) < float(w_social[forced])
        and float(metrics["forced_sale_socialized_loss"]) == float(w_social[forced])
        and float(metrics["auction_socialized_loss"]) == float(w_social[auction])
    )
    _add(
        checks,
        "liquidation_method_waterfalls",
        max(conservation_error, shortfall_gap, trader_gap),
        "forced sale and auction: equity + absorbers - trader return - fee == 0, absorbers == "
        "max(-equity, 0), trader return == max(equity - fee, 0), fee <= max(equity, 0) (all "
        "rebuilt from the legs, 1e-12); auction socialized loss < forced sale; metrics match",
        methods_ok,
    )
    gross_rebuilt = np.maximum(
        0.0,
        np.asarray(arrays["rebalanced_value"], dtype=float)
        - np.asarray(arrays["lp_value"], dtype=float),
    )
    lvr_gap = max(
        float(np.max(np.abs(gross_rebuilt - arrays["lvr"]))),
        float(np.max(np.abs(arrays["dynamic_fee_gross_lvr"] - arrays["lvr"]))),
        float(np.max(np.abs(arrays["fixed_fee_gross_lvr"] - arrays["lvr"]))),
    )
    amm_identity_rebuilt = (
        np.asarray(arrays["dynamic_fee_gross_lvr"], dtype=float)
        - np.asarray(arrays["dynamic_fee_income"], dtype=float)
        - np.asarray(arrays["dynamic_fee_net_lvr"], dtype=float)
    )
    amm_error = max(lvr_gap, float(np.max(np.abs(amm_identity_rebuilt))))
    _add(
        checks,
        "amm_identity",
        amm_error,
        "gross LVR == max(0, rebalanced - LP value) for the fixed and dynamic fee ledgers and "
        "gross - dynamic fee - net == 0, all rebuilt from the committed arrays (1e-12)",
        amm_error < 1e-12
        and float(np.max(np.abs(amm_identity_rebuilt - arrays["amm_identity_error"]))) < 1e-12,
    )
    fixed_net_gap = float(
        np.max(
            np.abs(
                arrays["fixed_fee_net_lvr"] - (arrays["fixed_fee_gross_lvr"] - arrays["fee_income"])
            )
        )
    )
    dynamic_net_gap = float(
        np.max(
            np.abs(
                arrays["dynamic_fee_net_lvr"]
                - (arrays["dynamic_fee_gross_lvr"] - arrays["dynamic_fee_income"])
            )
        )
    )
    reduction_gap = abs(
        float(np.max(np.abs(arrays["fixed_fee_gross_lvr"] - arrays["dynamic_fee_gross_lvr"])))
        - float(metrics["dynamic_fee_gross_lvr_reduction"])
    )
    cpmm_ok = (
        np.max(np.abs(arrays["cpmm_swap_identity_error"])) < 1e-12
        and np.all(arrays["cpmm_invariant_gain"] >= 0)
        and fixed_net_gap < 1e-12
        and dynamic_net_gap < 1e-12
        and reduction_gap < 1e-12
        and bool(np.all(np.diff(arrays["fee_income"]) >= 0))
        and bool(np.all(np.diff(arrays["dynamic_fee_income"]) >= 0))
        and float(arrays["dynamic_fee_income"][-1]) == float(metrics["dynamic_fee_compensation"])
        and np.all(np.isfinite(arrays["concentrated_lvr"]))
    )
    _add(
        checks,
        "amm_lvr_fee_variants",
        max(fixed_net_gap, dynamic_net_gap),
        "CPMM identity; net LVR == gross - cumulative fee for the fixed and dynamic ledgers "
        "(1e-12); fee income non-decreasing; gross-LVR reduction and fee compensation metrics "
        "match the arrays; finite concentrated LVR",
        cpmm_ok,
    )
    oracle_ok = (
        int(np.count_nonzero(arrays["oracle_stale"])) == metrics["oracle_stale_count"] > 0
        and int(np.count_nonzero(arrays["oracle_dislocated"]))
        == metrics["oracle_dislocated_count"]
        > 0
    )
    _add(
        checks,
        "oracle_staleness_dislocation",
        f"{metrics['oracle_stale_count']}/{metrics['oracle_dislocated_count']}",
        "both explicit flags agree with their counts",
        oracle_ok,
    )
    negative = [
        "The liquidation cascade is deliberately synthetic and is not a reconstruction of a market event."
    ]
    if metrics["dynamic_fee_gross_lvr_reduction"] <= 0:
        negative.append(
            "The dynamic fee does not reduce gross LVR in this fixture; fee compensation is reported separately."
        )
    return checks, negative


def _volume25(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    # Incompleteness is evidenced, not declared: the three premium principles
    # price the same payoff differently and every off-site station hedge
    # leaves residual variance.
    premium_spread = float(np.ptp(arrays["weather_premium"]))
    variance_reduction = np.asarray(arrays["basis_variance_reduction"], dtype=float)
    incomplete = (
        metrics["market_completeness"] == "incomplete"
        and premium_spread > 0.0
        and bool(np.all(variance_reduction[1:] < 1.0))
    )
    _add(
        checks,
        "market_completeness",
        premium_spread,
        "label == incomplete; premium principles disagree (ptp > 0) and off-site basis hedges "
        "leave residual variance (variance reduction < 1)",
        incomplete,
    )
    principles = arrays["premium_principle_names"].tolist()
    expected = ["expected_value", "standard_deviation", "exponential"]
    _add(
        checks,
        "premium_principles",
        len(principles),
        "three explicit non-traded-index principles",
        principles == expected,
    )
    sensitivity = (
        np.all(np.isfinite(arrays["premium_sensitivity"]))
        and np.ptp(arrays["premium_sensitivity"]) > 0
    )
    _add(
        checks,
        "carbon_premium_sensitivity",
        float(np.ptp(arrays["premium_sensitivity"])),
        "> 0",
        sensitivity,
    )
    carbon_models = arrays["carbon_model_names"].tolist()
    carbon_se = np.asarray(arrays["carbon_model_standard_error"], dtype=float)
    carbon_price = np.asarray(arrays["carbon_model_price"], dtype=float)
    # Black-76 rebuilt from (F, r, T, sigma) on the strike grid; the constant-
    # variance GBM teacher must agree with it inside Monte Carlo noise.
    carbon_forward = float(metrics["carbon_forward"])
    carbon_rate = float(metrics["carbon_rate"])
    carbon_maturity = float(metrics["carbon_maturity"])
    carbon_sigma = float(metrics["carbon_black76_volatility"])
    carbon_strike = np.asarray(arrays["strike"], dtype=float)
    vol_sqrt_t = carbon_sigma * math.sqrt(carbon_maturity)
    d1 = np.log(carbon_forward / carbon_strike) / vol_sqrt_t + 0.5 * vol_sqrt_t
    black76_rebuilt = math.exp(-carbon_rate * carbon_maturity) * (
        carbon_forward * _norm_cdf_np(d1) - carbon_strike * _norm_cdf_np(d1 - vol_sqrt_t)
    )
    black76_gap = float(np.max(np.abs(black76_rebuilt - arrays["carbon_black76_price"])))
    ladder_gap = float(
        np.max(
            np.abs(
                carbon_price
                - np.stack(
                    [
                        arrays["carbon_black76_price"],
                        arrays["carbon_gbm_price"],
                        arrays["carbon_heston_price"],
                        arrays["carbon_jump_price"],
                    ]
                )
            )
        )
    )
    gbm_zscore = float(
        np.max(
            np.abs(np.asarray(arrays["carbon_gbm_price"], dtype=float) - black76_rebuilt)
            / carbon_se[1]
        )
    )
    carbon_ok = (
        carbon_models == ["Black-76", "GBM MC", "Heston MC", "SV+jump MC"]
        and metrics["carbon_model_ladder_complete"] is True
        and carbon_price.shape == carbon_se.shape
        and np.all(np.isfinite(carbon_price))
        and black76_gap < 1e-10
        and ladder_gap == 0.0
        and gbm_zscore <= 4.0
        and np.all(carbon_se[0] == 0)
        and np.all(carbon_se[1:] > 0)
        and float(metrics["carbon_atm_black76_price"])
        == float(arrays["carbon_black76_price"][carbon_strike.size // 2])
    )
    _add(
        checks,
        "carbon_model_ladder",
        gbm_zscore,
        "Black-76 rebuilt from (F, r, T, sigma) matches the committed row (1e-10); the ladder "
        "stacks the four committed price rows; constant-variance GBM MC within 4 SE of "
        "Black-76 at every strike; zero SE for Black-76, positive for the MC rows",
        carbon_ok,
    )
    weather_ok = (
        arrays["temperature_model_names"].tolist() == ["OU", "fractional OU"]
        and arrays["temperature_lag1_autocorrelation"].shape == (2,)
        and arrays["temperature_lag1_autocorrelation"][1]
        > arrays["temperature_lag1_autocorrelation"][0]
        and np.all(np.isfinite(arrays["degree_day_mean"]))
        and np.all(np.isfinite(arrays["degree_day_std"]))
    )
    _add(
        checks,
        "weather_long_memory",
        metrics["weather_fou_lag1_autocorrelation"],
        "fractional OU lag-1 correlation exceeds OU with finite degree-day moments",
        weather_ok,
    )
    basis = arrays["basis_rmse"][-1] > arrays["basis_rmse"][1] and arrays["basis_rmse"][0] == 0
    _add(
        checks,
        "weather_basis_risk",
        arrays["basis_rmse"][-1],
        "increases from zero-distance baseline",
        basis,
    )
    hedge_ok = (
        arrays["basis_hedge_ratio"].shape == arrays["basis_variance_reduction"].shape
        and np.all(np.isfinite(arrays["basis_hedge_ratio"]))
        and np.all(arrays["basis_variance_reduction"] >= 0)
        and np.all(arrays["basis_variance_reduction"] <= 1)
    )
    _add(
        checks,
        "basis_hedge_diagnostics",
        float(arrays["basis_variance_reduction"][-1]),
        "finite hedge ratios and variance reduction in [0, 1]",
        hedge_ok,
    )
    # PPA cash-flow statistics rebuilt from the committed per-scenario samples
    # (hedge ratio 1, unit discount): fair value is the mean settlement, the
    # unhedged std is the merchant std, and the hedge-ratio ladder ends at the
    # hedged residual and starts at the unhedged one.
    merchant = np.asarray(arrays["ppa_merchant_cash_flow_samples"], dtype=float)
    hedged = np.asarray(arrays["ppa_hedged_cash_flow_samples"], dtype=float)
    ppa_alpha = float(metrics["ppa_alpha"])
    settlement_samples = hedged - merchant[None, :]
    fair_value_gap = max(
        float(np.max(np.abs(settlement_samples.mean(axis=1) - arrays["ppa_fair_value"]))),
        float(
            np.max(
                np.abs(
                    np.asarray(
                        [
                            arrays["ppa_fixed"].sum(),
                            arrays["ppa_pay_as_produced"].sum(),
                            arrays["ppa_floor_collar"].sum(),
                        ]
                    )
                    - arrays["ppa_fair_value"]
                )
            )
        ),
    )
    unhedged_gap = float(np.max(np.abs(merchant.std(ddof=0) - arrays["unhedged_cash_flow_std"])))
    hedge_ratio = np.asarray(arrays["hedge_ratio"], dtype=float)
    ladder = np.asarray(arrays["hedge_ratio_residual"], dtype=float)
    pap = arrays["risk_names"].tolist().index("pay-as-produced")
    ladder_gap = max(
        abs(float(ladder[-1] - arrays["hedge_residual"][pap])),
        abs(float(ladder[0] - arrays["unhedged_cash_flow_std"][pap])),
    )
    ppa = (
        hedged.shape == (arrays["risk_names"].size, merchant.size)
        and merchant.size >= 2
        and np.all(np.isfinite(hedged))
        and float(hedge_ratio[0]) == 0.0
        and float(hedge_ratio[-1]) == 1.0
        and fair_value_gap < 1e-9
        and unhedged_gap < 1e-9
        and ladder_gap < 1e-9
        and np.ptp(ladder) > 0
    )
    _add(
        checks,
        "ppa_risk_decomposition",
        max(fair_value_gap, unhedged_gap, ladder_gap),
        "fair value == mean(hedged - merchant) == sum of period settlement means; unhedged std "
        "== merchant std; hedge-ratio ladder spans unhedged std (h=0) to hedged residual (h=1) "
        "(all rebuilt from the samples, 1e-9)",
        ppa,
    )
    expected_rebuilt = hedged.mean(axis=1)
    quantile = np.quantile(hedged, 1.0 - ppa_alpha, axis=1)
    cfar_rebuilt = expected_rebuilt - quantile
    cvar_rebuilt = np.asarray(
        [
            expected_rebuilt[row] - hedged[row][hedged[row] <= quantile[row]].mean()
            for row in range(hedged.shape[0])
        ]
    )
    residual_rebuilt = hedged.std(axis=1, ddof=0)
    cashflow_gap = max(
        float(np.max(np.abs(expected_rebuilt - arrays["expected_hedged_cash_flow"]))),
        float(np.max(np.abs(cfar_rebuilt - arrays["cash_flow_at_risk"]))),
        float(np.max(np.abs(cvar_rebuilt - arrays["cvar95"]))),
        float(np.max(np.abs(residual_rebuilt - arrays["hedge_residual"]))),
    )
    cashflow_ok = (
        cashflow_gap < 1e-9
        and bool(np.all(cvar_rebuilt >= cfar_rebuilt))
        and bool(np.all(cfar_rebuilt > 0))
        and float(metrics["ppa_cvar95"]) == float(arrays["cvar95"][pap])
        and float(metrics["ppa_cash_flow_at_risk95"]) == float(arrays["cash_flow_at_risk"][pap])
        and float(metrics["ppa_hedge_residual"]) == float(arrays["hedge_residual"][pap])
    )
    _add(
        checks,
        "ppa_cashflow_risk",
        cashflow_gap,
        "expected cash flow, CFaR = mean - q(1-alpha), CVaR = mean - mean(tail <= q) and "
        "residual std rebuilt from the hedged samples match the committed arrays (1e-9); "
        "CVaR >= CFaR > 0; pay-as-produced metrics match",
        cashflow_ok,
    )
    grid = arrays["ppa_correlation_grid"]
    merchant_mean = arrays["ppa_correlation_merchant_mean"]
    merchant_se = arrays["ppa_correlation_merchant_se"]
    fair_value = arrays["ppa_correlation_pap_fair_value"]
    periods = arrays["ppa_pay_as_produced"].size
    # Unfloored generation g(1 + sigma_G z_G) with z_G = rho z_S + ...: per period
    # E[S G] = P g (1 + rho sigma_S sigma_G), so revenue is linear in rho.
    analytic_mean = (
        periods
        * float(metrics["ppa_base_price"])
        * float(metrics["ppa_base_generation"])
        * (
            1.0
            + grid
            * float(metrics["ppa_price_volatility"])
            * float(metrics["ppa_generation_volatility"])
        )
    )
    base_rows = np.flatnonzero(np.isclose(grid, float(metrics["ppa_scenario_correlation"])))
    correlation_z = float(np.max(np.abs(merchant_mean - analytic_mean) / merchant_se))
    correlation_ok = bool(
        grid.ndim == 1
        and np.all(np.diff(grid) > 0.0)
        and merchant_mean.shape == merchant_se.shape == fair_value.shape == grid.shape
        and np.all(merchant_se > 0.0)
        and base_rows.size == 1
        and correlation_z < 3.0
        and np.allclose(
            fair_value,
            float(metrics["ppa_fixed_price"]) * arrays["ppa_correlation_generation_mean"]
            - merchant_mean,
            rtol=0.0,
            atol=1e-9,
        )
    )
    if correlation_ok:
        base = int(base_rows[0])
        correlation_ok = (
            _close(merchant_mean[base], float(np.mean(merchant)), rel=1e-12)
            and _close(fair_value[base], float(arrays["ppa_fair_value"][pap]), rel=1e-12)
            and _close(
                arrays["ppa_correlation_pap_cvar95"][base], float(arrays["cvar95"][pap]), rel=1e-12
            )
        )
    _add(
        checks,
        "ppa_correlation_sensitivity",
        correlation_z,
        "merchant revenue within 3 SE of N P g (1 + rho sigma_S sigma_G) on every grid rho; "
        "pay-as-produced fair value = K * generation - revenue; base rho row equals the samples",
        correlation_ok,
    )
    cvar_grid = arrays["ppa_correlation_pap_cvar95"]
    return checks, [
        "Weather and PPA values are premium-principle dependent because the underlying market is incomplete.",
        "Across price-generation correlation "
        f"{float(grid[0]):+.1f}..{float(grid[-1]):+.1f} the pay-as-produced fair value moves "
        f"{float(fair_value[0]):.4g} -> {float(fair_value[-1]):.4g}, but its hedged cash flow is "
        "the fixed price times generation, whose distribution does not depend on rho; the CVaR "
        f"spread {float(np.min(cvar_grid)):.4g}..{float(np.max(cvar_grid)):.4g} is sampling noise.",
    ]


def _volume26(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    hw_error = float(
        np.max(np.abs(arrays["hw_market_discount_factor"] - arrays["hw_model_discount_factor"]))
    )
    _add(
        checks,
        "hull_white_initial_curve",
        hw_error,
        "<= 1e-12 against the nominal discount curve",
        hw_error <= 1e-12
        and np.array_equal(arrays["hw_market_discount_factor"], arrays["nominal_discount_factor"])
        and _close(metrics["hw_curve_fit_max_error"], hw_error),
    )
    seasonality_sum = float(abs(np.sum(arrays["seasonality_log_factor"])))
    _add(
        checks,
        "annual_seasonality_normalization",
        seasonality_sum,
        "<= 1e-12 over the twelve monthly log factors",
        arrays["seasonality_log_factor"].shape == (12,)
        and seasonality_sum <= 1e-12
        and _close(metrics["seasonality_annual_log_sum"], seasonality_sum, abs_tol=1e-18),
    )
    zcis_error = float(np.max(np.abs(arrays["zcis_quote"] - arrays["zcis_repriced"])))
    _add(
        checks,
        "zcis_quote_repricing",
        zcis_error,
        "<= 1e-10",
        zcis_error <= 1e-10 and _close(metrics["zcis_repricing_max_error"], zcis_error),
    )
    jy_se = arrays["jy_mc_standard_error"]
    jy_shapes = bool(
        arrays["jy_forward_index"].shape == arrays["jy_mc_forward_index"].shape == jy_se.shape
        and np.all(jy_se > 0.0)
    )
    jy_z = (
        float(np.max(np.abs(arrays["jy_mc_forward_index"] - arrays["jy_forward_index"]) / jy_se))
        if jy_shapes
        else float("nan")
    )
    _add(
        checks,
        "jy_forward_measure_mc",
        jy_z,
        "aligned arrays and maximum analytic/MC z-score < 3",
        jy_shapes and jy_z < 3.0 and _close(metrics["jy_forward_mc_zscore_max"], jy_z),
    )
    floor_analytic = arrays["floor_analytic"]
    floor_mc = arrays["floor_mc"]
    floor_se = arrays["floor_mc_standard_error"]
    floor_shapes = (
        floor_analytic.shape
        == floor_mc.shape
        == floor_se.shape
        == arrays["inflation_volatility"].shape
    )
    floor_z = float("nan")
    degenerate_ok = False
    if floor_shapes:
        live = floor_se > 0.0
        floor_z = float(
            np.max(np.abs(floor_mc[live] - floor_analytic[live]) / floor_se[live], initial=0.0)
        )
        degenerate_ok = bool(np.all(np.abs(floor_mc[~live] - floor_analytic[~live]) <= 1e-12))
    _add(
        checks,
        "jgbi_floor_analytic_mc",
        floor_z,
        "aligned arrays, maximum non-degenerate z-score < 3, zero-SE rows equal analytic",
        floor_shapes
        and degenerate_ok
        and floor_z < 3.0
        and _close(metrics["floor_mc_zscore_max"], floor_z),
    )
    volatility = arrays["inflation_volatility"]
    floor_monotone = bool(
        floor_shapes
        and np.all(np.diff(volatility) > 0.0)
        and np.all(np.diff(floor_analytic) >= 0.0)
    )
    _add(
        checks,
        "floor_volatility_monotonicity",
        floor_monotone,
        "analytic floor is non-decreasing along the increasing inflation-volatility grid",
        floor_monotone and metrics["floor_monotone_in_volatility"] is True,
    )
    # The floor may touch the redemption only: both schedules pay identical
    # coupons proportional to the unfloored index ratio (a floored coupon would
    # break the proportionality on the R < 1 dates), no principal before
    # maturity, and a final principal of face * max(R, 1) against face * R.
    index_ratio = arrays["jgbi_index_ratio"]
    coupon = arrays["jgbi_coupon"]
    unfloored_coupon = arrays["jgbi_unfloored_coupon"]
    floored_principal = arrays["jgbi_floored_principal"]
    unfloored_principal = arrays["jgbi_unfloored_principal"]
    face = float(metrics["jgbi_face_value"])
    schedule_shapes = bool(
        index_ratio.ndim == 1
        and index_ratio.size >= 2
        and coupon.shape == unfloored_coupon.shape == index_ratio.shape
        and floored_principal.shape == unfloored_principal.shape == index_ratio.shape
        and np.all(index_ratio > 0.0)
    )
    coupon_error = float("nan")
    redemption_only = False
    if schedule_shapes:
        coupon_error = float(np.max(np.abs(coupon - unfloored_coupon)))
        coupon_per_ratio = coupon / index_ratio
        ratio = float(index_ratio[-1])
        redemption_only = bool(
            coupon_error == 0.0
            and np.all(
                np.abs(coupon_per_ratio - coupon_per_ratio[0]) <= 1e-12 * coupon_per_ratio[0]
            )
            and np.all(floored_principal[:-1] == 0.0)
            and np.all(unfloored_principal[:-1] == 0.0)
            and math.isclose(float(unfloored_principal[-1]), face * ratio, rel_tol=1e-12)
            and math.isclose(float(floored_principal[-1]), face * max(ratio, 1.0), rel_tol=1e-12)
            and floored_principal[-1] > unfloored_principal[-1]
        )
    _add(
        checks,
        "redemption_only_principal_floor",
        coupon_error,
        "coupons identical and proportional to the index ratio, no interim principal, "
        "final principal face * max(R, 1) against face * R",
        schedule_shapes
        and redemption_only
        and metrics["principal_floor_redemption_only"] is True
        and _close(metrics["coupon_floor_max_error"], coupon_error),
    )
    final_ratio = float(arrays["jgbi_index_ratio"][-1])
    decomposition_error = abs(
        float(arrays["jgbi_floored_principal"][-1])
        - (
            float(arrays["jgbi_unfloored_principal"][-1])
            + metrics["jgbi_face_value"] * max(1.0 - final_ratio, 0.0)
        )
    )
    _add(
        checks,
        "floor_payoff_decomposition",
        decomposition_error,
        "binding floor: floored = unfloored + face * max(1 - R, 0) within 1e-12",
        final_ratio < 1.0
        and decomposition_error <= 1e-12
        and math.isclose(decomposition_error, metrics["floor_decomposition_error"], abs_tol=1e-15),
    )
    # Rebuild E[I(e)/I(s)] under the nominal payment-forward measure from its
    # committed components: F_pay(o) = F(o) exp(a(o)), with a(e) = 0 because the
    # end observation is the payment date, times exp(Var_s - Cov_{s,e}).
    start_forward = arrays["yoy_start_forward_cpi"]
    end_forward = arrays["yoy_end_forward_cpi"]
    start_adjustment = arrays["yoy_start_payment_adjustment"]
    end_adjustment = arrays["yoy_end_payment_adjustment"]
    start_variance = arrays["yoy_start_log_variance"]
    log_covariance = arrays["yoy_log_covariance"]
    jy_ratio = arrays["yoy_jy_ratio"]
    deterministic_ratio = arrays["yoy_deterministic_ratio"]
    yoy_shapes = bool(
        jy_ratio.ndim == 1
        and jy_ratio.shape
        == deterministic_ratio.shape
        == start_forward.shape
        == end_forward.shape
        == start_adjustment.shape
        == end_adjustment.shape
        == start_variance.shape
        == log_covariance.shape
        == arrays["yoy_payment"].shape
        and np.all(start_forward > 0.0)
        and np.all(jy_ratio > 0.0)
    )
    measure_error = float("nan")
    measure_ok = False
    if yoy_shapes:
        rebuilt = (
            end_forward
            * np.exp(end_adjustment)
            / (start_forward * np.exp(start_adjustment))
            * np.exp(start_variance - log_covariance)
        )
        measure_error = float(np.max(np.abs(rebuilt / jy_ratio - 1.0)))
        deterministic_error = float(
            np.max(np.abs(end_forward / start_forward / deterministic_ratio - 1.0))
        )
        measure_ok = bool(
            measure_error <= 1e-12
            and deterministic_error <= 1e-12
            and np.all(end_adjustment == 0.0)
            and np.any(start_adjustment != 0.0)
            and np.ptp(jy_ratio - deterministic_ratio) > 0.0
        )
    _add(
        checks,
        "nominal_payment_forward_measure",
        measure_error,
        "YoY ratio rebuilt from payment-forward CPI and log covariances within 1e-12 relative, "
        "measure adjustment applied, non-zero YoY convexity",
        yoy_shapes and measure_ok and metrics["measure_treatment"] == "nominal_payment_forward",
    )
    bei_ok = (
        arrays["bei_names"].tolist() == ["raw", "floor-adjusted"]
        and arrays["breakeven_inflation"][0] != arrays["breakeven_inflation"][1]
    )
    _add(
        checks,
        "raw_and_floor_adjusted_breakeven",
        float(arrays["breakeven_inflation"][1] - arrays["breakeven_inflation"][0]),
        "two explicitly different BEI measures",
        bei_ok,
    )
    unhedged = arrays["unhedged_risk"]
    instrument = arrays["hedge_instrument_risk"]
    notional = arrays["hedge_notional"]
    linear_residual = unhedged + instrument @ notional
    unhedged_scenario = np.abs(arrays["unhedged_scenario_pnl"])
    hedged_scenario = np.abs(arrays["hedged_scenario_pnl"])
    hedge_ok = (
        arrays["hedge_risk_names"].tolist() == ["nominal duration", "CPI delta"]
        and unhedged.shape == notional.shape == arrays["hedged_risk"].shape == (2,)
        and instrument.shape == (2, 2)
        and bool(np.all(np.abs(unhedged) > 0.0))
        and bool(np.all(np.abs(linear_residual) <= 1e-9 * np.abs(unhedged)))
        and bool(np.all(np.abs(arrays["hedged_risk"] - linear_residual) <= 1e-9 * np.abs(unhedged)))
        and abs(metrics["unhedged_real_pv01"]) > 0.0
        and abs(metrics["hedged_real_pv01"]) <= 1e-4 * abs(metrics["unhedged_real_pv01"])
        and unhedged_scenario.shape == hedged_scenario.shape == arrays["hedge_scenario_names"].shape
        and bool(np.all(hedged_scenario < unhedged_scenario))
    )
    _add(
        checks,
        "synthetic_hedge_decomposition",
        float(np.max(hedged_scenario / unhedged_scenario)),
        "revalued nominal-PV01/CPI-delta residuals vanish, real PV01 follows, scenario P&L shrinks",
        hedge_ok,
    )
    return checks, [
        "All curves, CPI fixings, option quotes, and hedge ratios are synthetic rather than market calibrated.",
        "The v1 model uses deterministic seasonality and one-factor nominal/real Gaussian rates.",
        "Production ISDA disruption fallbacks and live JGBi settlement operations are out of scope.",
    ]


def _hist_var_es_np(pnl: np.ndarray, alpha: float) -> tuple[float, float]:
    """Vol-08 historical VaR/ES recomputation (k worst losses) in pure NumPy."""
    losses = -np.asarray(pnl, dtype=float)
    n = losses.size
    k = max(1, math.ceil((1.0 - alpha) * n - 1e-9))
    worst = np.sort(losses)[::-1][:k]
    return float(worst[-1]), float(worst.mean())


def _xlogy_np(a: float, b: float) -> float:
    """`a * ln(b)` with the convention `0 * ln(0) = 0` (NumPy-only)."""
    return 0.0 if a <= 0.0 else float(a * math.log(b))


def _chi2_sf_df1(statistic: float) -> float:
    """`scipy.stats.chi2.sf(statistic, df=1)` without importing scipy.

    For one degree of freedom the survival function is exactly
    `erfc(sqrt(x/2))`, so the gate can recompute its own p-value from the
    committed arrays instead of reading one out of the JSON metrics.
    """
    if statistic <= 0.0:
        return 1.0
    return float(math.erfc(math.sqrt(statistic / 2.0)))


def _binary_exceedances_np(exceedances: np.ndarray) -> np.ndarray:
    """Return `exceedances` as a 0/1 int array, raising ValueError otherwise.

    Mirrors `hullkit.var_backtest._validate_binary_exceedances`. Without it an
    `astype(int)` cast would truncate a probability series to all-zeros or a
    count series to arbitrary states, and the independence statistic would come
    back 0.0 -- a silent pass in the direction of acceptance.
    """
    exc = np.asarray(exceedances, dtype=float)
    if exc.ndim != 1:
        raise ValueError(f"exceedances must be one-dimensional, got shape {exc.shape}")
    if not np.all(np.isfinite(exc)):
        raise ValueError("exceedances must be a binary 0/1 series, got non-finite values")
    bad = ~np.isin(exc, (0.0, 1.0))
    if np.any(bad):
        raise ValueError(
            "exceedances must be a binary 0/1 series, got non-binary values "
            f"{np.unique(exc[bad]).tolist()}"
        )
    return exc.astype(int)


def _kupiec_pvalue_np(n_exceedances: int, n_obs: int, p: float) -> float:
    """Kupiec (1995) proportion-of-failures p-value recomputed without scipy.

    `LR_pof = -2 ln[ (1-p)^(n-x) p^x / (1-pi)^(n-x) pi^x ]`, pi = x/n, compared
    against chi2(1). Mirrors `hullkit.var_backtest.kupiec_pof` so the gate can
    re-derive each replication's verdict from its committed exceedance count.
    """
    n = float(n_obs)
    x = float(n_exceedances)
    pi_hat = x / n
    log_num = _xlogy_np(n - x, 1.0 - p) + _xlogy_np(x, p)
    log_den = _xlogy_np(n - x, 1.0 - pi_hat) + _xlogy_np(x, pi_hat)
    return _chi2_sf_df1(-2.0 * (log_num - log_den))


def _lr_independence_np(exceedances: np.ndarray) -> float:
    """Christoffersen (1998) independence LR statistic recomputed in NumPy."""
    exc = _binary_exceedances_np(exceedances)
    if exc.size < 2 or np.unique(exc).size == 1:
        return 0.0
    prev, curr = exc[:-1], exc[1:]
    n00 = float(np.sum((prev == 0) & (curr == 0)))
    n01 = float(np.sum((prev == 0) & (curr == 1)))
    n10 = float(np.sum((prev == 1) & (curr == 0)))
    n11 = float(np.sum((prev == 1) & (curr == 1)))
    n_trans = n00 + n01 + n10 + n11
    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi_bar = (n01 + n11) / n_trans
    log_num = _xlogy_np(n00 + n10, 1.0 - pi_bar) + _xlogy_np(n01 + n11, pi_bar)
    log_den = (
        _xlogy_np(n00, 1.0 - pi01)
        + _xlogy_np(n01, pi01)
        + _xlogy_np(n10, 1.0 - pi11)
        + _xlogy_np(n11, pi11)
    )
    return float(-2.0 * (log_num - log_den))


def _volume27(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    alpha = float(metrics.get("alpha", 0.99))
    p = 1.0 - alpha

    # 1. Kupiec size calibration recomputed from the committed exceedance counts.
    #    The stored reject flags are `kupiec_pof`'s output, so they are re-derived
    #    here from their input rather than trusted; a mismatch fails the gate.
    reject_flags = np.asarray(arrays["kupiec_size_reject_flags"], dtype=float)
    exceedance_counts = np.asarray(arrays["kupiec_size_exceedance_counts"], dtype=float)
    kupiec_observations = int(metrics["kupiec_size_observations"])
    if exceedance_counts.shape != reject_flags.shape:
        raise ValueError("kupiec size counts and reject flags must have equal length")
    recomputed_flags = np.array(
        [
            1.0 if _kupiec_pvalue_np(int(count), kupiec_observations, p) < 0.05 else 0.0
            for count in exceedance_counts
        ]
    )
    flag_mismatch = float(np.max(np.abs(recomputed_flags - reject_flags)))
    _add(
        checks,
        "kupiec_size_flags_match_recomputation",
        flag_mismatch,
        "every stored reject flag equals Kupiec's own verdict recomputed from the "
        "committed per-replication exceedance count",
        flag_mismatch == 0.0,
    )
    n_replications = int(reject_flags.size)
    rejection_rate = float(recomputed_flags.mean())
    # The exceedance count is discrete, so the 5% nominal level is not the
    # test's actual size: sum the binomial mass over the rejection region.
    count_grid = np.arange(kupiec_observations + 1)
    rejects = np.array(
        [
            1.0 if _kupiec_pvalue_np(int(x), kupiec_observations, p) < 0.05 else 0.0
            for x in count_grid
        ]
    )
    exact_size = float(np.sum(_binomial_pmf_np(kupiec_observations, np.array(p)) * rejects))
    binomial_se = math.sqrt(exact_size * (1.0 - exact_size) / n_replications)
    size_zscore = abs(rejection_rate - exact_size) / binomial_se
    _add(
        checks,
        "kupiec_size_calibration",
        size_zscore,
        f"iid rejection rate within z < 3 of the exact Kupiec size {exact_size:.4f} at "
        f"n={kupiec_observations} (binomial SE, {n_replications} replications)",
        size_zscore < 3.0,
    )

    # 2. Christoffersen independence detects clustering (LR recomputed from arrays).
    lr_iid = _lr_independence_np(arrays["iid_exceedances"])
    lr_clustered = _lr_independence_np(arrays["clustered_exceedances"])
    pvalue_clustered = _chi2_sf_df1(lr_clustered)
    detects_clustering = pvalue_clustered < 0.05 and lr_clustered > lr_iid
    _add(
        checks,
        "christoffersen_detects_clustering",
        pvalue_clustered,
        "clustered LR_ind p-value (recomputed from the arrays) < 0.05 and LR_ind "
        "statistic exceeds the iid series",
        detects_clustering,
    )

    # 2b. The stored p-value must agree with the recomputation (metric integrity).
    stored_pvalue = float(metrics["christoffersen_ind_pvalue_clustered"])
    pvalue_consistency = abs(stored_pvalue - pvalue_clustered)
    _add(
        checks,
        "christoffersen_pvalue_matches_recomputation",
        pvalue_consistency,
        "stored christoffersen_ind_pvalue_clustered matches erfc(sqrt(LR/2)) recomputed "
        "from the committed exceedance series (<= 1e-12)",
        pvalue_consistency <= 1e-12,
    )

    # 3. Constant-sigma FHS equals plain historical simulation.
    hs_var, _ = _hist_var_es_np(arrays["garch_returns"], alpha)
    fhs_constant_error = abs(float(metrics["fhs_var_constant"]) - hs_var)
    _add(
        checks,
        "fhs_constant_vol_identity",
        fhs_constant_error,
        "<= 1e-12",
        fhs_constant_error <= 1e-12,
    )

    # 4. FHS coverage beats plain HS on the GARCH path. The rolling HS and FHS
    #    forecasts and the violation series are rebuilt from the committed
    #    return and conditional-volatility paths before the rates are compared.
    returns = np.asarray(arrays["garch_returns"], dtype=float)
    sigma_path = np.asarray(arrays["conditional_sigma"], dtype=float)
    window = int(metrics["fhs_window"])
    hs_forecast = np.empty(returns.size - window)
    fhs_forecast = np.empty(returns.size - window)
    for offset, t in enumerate(range(window, returns.size)):
        window_returns = returns[t - window : t]
        window_sigma = sigma_path[t - window : t]
        hs_forecast[offset], _ = _hist_var_es_np(window_returns, alpha)
        fhs_forecast[offset], _ = _hist_var_es_np(
            window_returns / window_sigma * sigma_path[t], alpha
        )
    realized_loss = -returns[window:]
    hs_violations = (realized_loss > hs_forecast).astype(float)
    fhs_violations = (realized_loss > fhs_forecast).astype(float)
    fhs_rebuild_gap = max(
        float(np.max(np.abs(hs_forecast - arrays["hs_var_forecast"]))),
        float(np.max(np.abs(fhs_forecast - arrays["fhs_var_forecast"]))),
        float(np.max(np.abs(hs_violations - arrays["hs_violations"]))),
        float(np.max(np.abs(fhs_violations - arrays["fhs_violations"]))),
    )
    hs_rate = float(hs_violations.mean())
    fhs_rate = float(fhs_violations.mean())
    coverage_improved = abs(fhs_rate - p) < abs(hs_rate - p)
    _add(
        checks,
        "fhs_coverage_improvement",
        fhs_rate,
        "rolling HS/FHS forecasts and violations rebuilt from the return and sigma paths match "
        "the committed series (1e-12); |FHS violation rate - (1-alpha)| < |plain-HS rate - "
        "(1-alpha)|",
        fhs_rebuild_gap <= 1e-12 and coverage_improved,
    )

    # 5. GPD parameter recovery. The committed (xi, beta) must be a local
    #    maximum of the GPD likelihood on the committed exceedances (1% moves
    #    in either parameter lower the likelihood), and the exceedance count
    #    must match the losses above the threshold.
    xi_true = float(metrics["gpd_xi_true"])
    beta_true = float(metrics["gpd_beta_true"])
    xi_hat = float(metrics["gpd_xi_hat"])
    beta_hat = float(metrics["gpd_beta_hat"])
    threshold = float(metrics["evt_threshold"])
    gpd_losses = np.asarray(arrays["gpd_losses"], dtype=float)
    exceedances = gpd_losses[gpd_losses > threshold] - threshold
    n_exceedances = int(exceedances.size)
    n_total = int(gpd_losses.size)

    def _gpd_nll(xi: float, beta: float) -> float:
        if beta <= 0.0:
            return math.inf
        z = xi * exceedances / beta
        if np.any(z <= -1.0):
            return math.inf
        return float(n_exceedances * math.log(beta) + (1.0 + 1.0 / xi) * np.sum(np.log1p(z)))

    # A fit needs at least one exceedance and a finite (xi, beta) with beta > 0
    # and 0 < |xi| < 1 (the EVT VaR divides by xi and the ES by 1 - xi). Anything
    # else fails the GPD and EVT checks with a reason instead of raising.
    fit_inputs_valid = (
        n_exceedances > 0
        and math.isfinite(xi_hat)
        and math.isfinite(beta_hat)
        and beta_hat > 0.0
        and xi_hat != 0.0
        and xi_hat < 1.0
    )
    mle_local_max = False
    if fit_inputs_valid:
        fit_nll = _gpd_nll(xi_hat, beta_hat)
        neighbour_nll = [
            _gpd_nll(xi_hat * 1.01, beta_hat),
            _gpd_nll(xi_hat * 0.99, beta_hat),
            _gpd_nll(xi_hat, beta_hat * 1.01),
            _gpd_nll(xi_hat, beta_hat * 0.99),
        ]
        mle_local_max = math.isfinite(fit_nll) and all(fit_nll < value for value in neighbour_nll)
    xi_error = abs(xi_hat - xi_true)
    beta_ratio_error = abs(beta_hat / beta_true - 1.0)
    _add(
        checks,
        "gpd_parameter_recovery",
        xi_error,
        "(xi_hat, beta_hat) is a local maximum of the GPD likelihood on the committed "
        "exceedances (1% perturbations), the exceedance count matches the metric, and "
        "|xi_hat - xi| <= 0.1 and |beta_hat/beta - 1| <= 0.15",
        fit_inputs_valid
        and mle_local_max
        and n_exceedances == int(metrics["gpd_n_exceedances"])
        and xi_error <= 0.1
        and beta_ratio_error <= 0.15,
    )

    # 6. EVT VaR rebuilt from the fit and the committed sample; ES closed form.
    evt_alpha = float(metrics["evt_alpha"])
    evt_var = float(metrics["evt_var"])
    evt_es = float(metrics["evt_es"])

    def _evt_var(level: float) -> float:
        if not 0.0 < level < 1.0:
            return math.nan
        ratio = (n_total / n_exceedances) * (1.0 - level)
        return threshold + (beta_hat / xi_hat) * (ratio ** (-xi_hat) - 1.0)

    if fit_inputs_valid:
        var_rebuild_gap = abs(_evt_var(evt_alpha) - evt_var)
        ladder_gap = float(
            np.max(
                np.abs(
                    np.array([_evt_var(float(a)) for a in arrays["evt_quantile_alpha"]])
                    - arrays["evt_var_ladder"]
                )
            )
        )
        evt_es_check = (evt_var + beta_hat - xi_hat * threshold) / (1.0 - xi_hat)
        evt_identity_error = abs(evt_es - evt_es_check)
    else:
        var_rebuild_gap = ladder_gap = evt_identity_error = math.inf
    _add(
        checks,
        "evt_var_es_identity",
        evt_identity_error,
        "EVT VaR rebuilt from (xi, beta, u, n, N_u) matches the metric and the committed "
        "quantile ladder (1e-10); ES identity <= 1e-12",
        var_rebuild_gap <= 1e-10 and ladder_gap <= 1e-10 and evt_identity_error <= 1e-12,
    )

    # 7. Analytic Euler additivity: normal VaR and its components are rebuilt
    #    from amounts, vols, correlations and z_alpha (numpy bisection quantile)
    #    before the additivity identity is tested.
    component_var = np.asarray(arrays["alloc_component_var"], dtype=float)
    normal_var = float(metrics["alloc_normal_var"])
    amounts = np.asarray(arrays["alloc_amounts"], dtype=float)
    vols = np.asarray(arrays["alloc_vols"], dtype=float)
    corr = np.asarray(arrays["alloc_corr"], dtype=float)
    covariance = corr * np.outer(vols, vols)
    sigma_p = math.sqrt(float(amounts @ covariance @ amounts))
    z_alpha = _norm_ppf_np(alpha)
    normal_var_rebuilt = z_alpha * sigma_p
    component_rebuilt = z_alpha * amounts * (covariance @ amounts) / sigma_p
    euler_rebuild_gap = max(
        abs(normal_var_rebuilt - normal_var),
        float(np.max(np.abs(component_rebuilt - component_var))),
    )
    euler_error = abs(float(component_var.sum()) - normal_var)
    _add(
        checks,
        "euler_additivity_normal",
        euler_error,
        "normal VaR and component VaR rebuilt from amounts/vols/corr and z_alpha match the "
        "committed values (1e-9); Σ components − VaR <= 1e-12",
        euler_rebuild_gap <= 1e-9 and euler_error <= 1e-12,
    )

    # 8. Analytic marginal VaR matches a central finite difference (z from the
    #    quantile, not from the stored VaR).
    marginal = np.asarray(arrays["alloc_marginal_var"], dtype=float)
    step = 1e-6 * np.maximum(np.abs(amounts), 1.0)
    finite_difference = np.empty_like(amounts)
    for i in range(amounts.size):
        forward = amounts.copy()
        backward = amounts.copy()
        forward[i] += step[i]
        backward[i] -= step[i]
        sigma_fwd = math.sqrt(float(forward @ covariance @ forward))
        sigma_bwd = math.sqrt(float(backward @ covariance @ backward))
        finite_difference[i] = z_alpha * (sigma_fwd - sigma_bwd) / (2.0 * step[i])
    relative_error = float(
        np.max(np.abs(marginal - finite_difference) / np.maximum(np.abs(marginal), 1e-12))
    )
    _add(
        checks,
        "marginal_fd_consistency",
        relative_error,
        "analytic vs central-difference marginals, relative error <= 1e-6",
        relative_error <= 1e-6,
    )

    # 9. Simulation Euler ES additivity recomputed from the P&L matrix.
    pnl_matrix = np.asarray(arrays["pnl_matrix"], dtype=float)
    total = pnl_matrix.sum(axis=1)
    n = total.size
    k = max(1, math.ceil((1.0 - alpha) * n - 1e-9))
    tail = np.argsort(total, kind="stable")[:k]
    es_total = float((-total[tail]).mean())
    es_components_recomputed = -pnl_matrix[tail].mean(axis=0)
    stored_es_components = np.asarray(arrays["es_components"], dtype=float)
    additivity_error = abs(float(es_components_recomputed.sum()) - es_total)
    component_match = float(np.max(np.abs(es_components_recomputed - stored_es_components)))
    _add(
        checks,
        "euler_es_additivity_sim",
        max(additivity_error, component_match),
        "sum(ES components) == total historical ES and matches committed array, <= 1e-12",
        additivity_error <= 1e-12 and component_match <= 1e-12,
    )

    # 10. P&L-explain Taylor ordering and shrinkage, recomputed from the arrays.
    book_delta = np.asarray(arrays["book_delta"], dtype=float)
    book_gamma = np.asarray(arrays["book_gamma"], dtype=float)
    book_vega = np.asarray(arrays["book_vega"], dtype=float)
    factor_moves = np.asarray(arrays["factor_moves"], dtype=float)
    vol_moves = np.asarray(arrays["vol_moves"], dtype=float)

    def _taylor(scale: float) -> tuple[float, float]:
        """(delta-only, delta-gamma-vega) Taylor P&L for a scaled factor move."""
        moves = scale * factor_moves
        delta_only = float(book_delta @ moves)
        dgv = (
            delta_only + 0.5 * float(book_gamma @ moves**2) + float(book_vega @ (scale * vol_moves))
        )
        return delta_only, dgv

    # Full revaluation is the sum of the committed per-position P&L, not a stored scalar.
    full_pnl = float(np.asarray(arrays["position_full_pnl"], dtype=float).sum())
    full_pnl_half = float(np.asarray(arrays["position_full_pnl_half"], dtype=float).sum())
    delta_only, dgv_total = _taylor(1.0)
    delta_only_half, dgv_total_half = _taylor(0.5)
    dgv_residual = abs(full_pnl - dgv_total)
    delta_residual = abs(full_pnl - delta_only)
    dgv_residual_half = abs(full_pnl_half - dgv_total_half)
    delta_residual_half = abs(full_pnl_half - delta_only_half)
    taylor_ordered = (
        dgv_residual < delta_residual
        and dgv_residual_half < dgv_residual
        and delta_residual_half < delta_residual
    )
    _add(
        checks,
        "pnl_explain_taylor_ordering",
        dgv_residual,
        "dgv residual < delta-only residual; both shrink when moves halve "
        "(all four recomputed from the committed exposure and P&L arrays)",
        taylor_ordered,
    )

    # 10b. Cross-asset factor mapping: equities and rates in one book.
    factor_names = [str(name) for name in arrays["factor_names"]]
    position_full_pnl = np.asarray(arrays["position_full_pnl"], dtype=float)
    mapping_delta = np.asarray(arrays["position_factor_delta"], dtype=float)
    mapping_vega = np.asarray(arrays["position_factor_vega"], dtype=float)
    n_positions = int(np.asarray(arrays["position_names"]).size)
    n_factors = len(factor_names)
    position_weights = np.asarray(arrays["position_weights"], dtype=float)
    mapping_gamma = np.asarray(arrays["position_factor_gamma"], dtype=float)
    # Book exposures must be the weighted aggregation of the committed
    # position x factor matrices, and the per-position full P&L must equal the
    # committed shocked-minus-base values (the desk total is their sum, so a
    # Σ−Σ comparison would be identically zero).
    book_gap = max(
        float(np.max(np.abs(position_weights @ mapping_delta - book_delta))),
        float(np.max(np.abs(position_weights @ mapping_gamma - book_gamma))),
        float(np.max(np.abs(position_weights @ mapping_vega - book_vega))),
    )
    revaluation_gap = float(
        np.max(
            np.abs(
                np.asarray(arrays["position_shocked_value"], dtype=float)
                - np.asarray(arrays["position_base_value"], dtype=float)
                - position_full_pnl
            )
        )
    )
    desk_sum_error = max(book_gap, revaluation_gap)
    rate_factor = "parallel_zero_rate"
    has_rate_factor = rate_factor in factor_names
    rate_column = factor_names.index(rate_factor) if has_rate_factor else 0
    rate_delta_nonzero = has_rate_factor and bool(
        np.any(np.abs(mapping_delta[:, rate_column]) > 0.0)
    )
    # The rate leg is a swap revalued off a deterministic curve: no vega.
    rate_vega_zero = has_rate_factor and bool(np.all(mapping_vega[:, rate_column] == 0.0))
    shapes_match = mapping_delta.shape == (n_positions, n_factors) and mapping_vega.shape == (
        n_positions,
        n_factors,
    )
    _add(
        checks,
        "cross_asset_factor_mapping",
        desk_sum_error,
        "position x factor mapping is (n_positions, n_factors) over explicit factor labels "
        "including parallel_zero_rate with a non-zero rate delta and zero rate vega; book "
        "delta/gamma/vega equal weights @ mapping and per-position P&L equals shocked − base "
        "value (<= 1e-9)",
        shapes_match
        and has_rate_factor
        and rate_delta_nonzero
        and rate_vega_zero
        and desk_sum_error <= 1e-9,
    )

    # 11. Desk-report scalars reproduce the recomputed VaR/ES exactly.
    desk_var_error = abs(float(metrics["desk_report_var"]) - float(component_var.sum()))
    desk_es_error = abs(float(metrics["desk_report_es"]) - es_total)
    _add(
        checks,
        "desk_report_reproducible",
        max(desk_var_error, desk_es_error),
        "desk-report VaR equals Euler component sum and ES equals total historical ES",
        desk_var_error <= 1e-12 and desk_es_error <= 1e-12,
    )

    return checks, [
        "All P&L, exceedance, and tail samples are synthetic fixed-seed draws, not market data.",
        "FHS uses the committed EWMA conditional-volatility path; no live model calibration is performed.",
        "The Basel multiplier schedule is the 250-day BCBS table and is only documented, not re-derived, elsewhere.",
        "Cross-gamma, vanna, and vomma P&L-explain terms are out of scope (see hullkit.pnl_explain).",
    ]


# --- vol 28 helpers: numpy-only normal CDF/quantile and the standard market model ---


def _norm_cdf_np(x: np.ndarray) -> np.ndarray:
    return 0.5 * np.vectorize(math.erfc)(-np.asarray(x, dtype=float) / math.sqrt(2.0))


def _norm_ppf_np(p: float) -> float:
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(_norm_cdf_np(np.array(mid))) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _binomial_pmf_np(n: int, p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-300, 1.0 - 1e-16)[..., None]
    k = np.arange(n + 1, dtype=float)
    log_choose = np.array(
        [math.lgamma(n + 1.0) - math.lgamma(i + 1.0) - math.lgamma(n - i + 1.0) for i in k]
    )
    return np.exp(log_choose + k * np.log(p) + (n - k) * np.log1p(-p))


def _tranche_legs_np(
    hazard: float,
    recovery: float,
    r: float,
    maturity: float,
    attach: float,
    detach: float,
    n: int,
    rho: float,
    freq: int = 4,
    m: int = 60,
) -> tuple[float, float, float]:
    """Hull eqs. 25.5–25.12 without hullkit: returns (A, B, C)."""
    x, w = np.polynomial.hermite.hermgauss(m)
    nodes, weights = math.sqrt(2.0) * x, w / math.sqrt(math.pi)
    times = np.arange(1, round(maturity * freq) + 1) / freq
    previous = times - 1.0 / freq
    n_low, n_high = attach * n / (1.0 - recovery), detach * n / (1.0 - recovery)
    m_low, m_high = math.floor(n_low) + 1, math.floor(n_high) + 1
    k = np.arange(n + 1)
    principal = np.where(
        k < m_low,
        1.0,
        np.where(k >= m_high, 0.0, (detach - k * (1.0 - recovery) / n) / (detach - attach)),
    )
    expected = np.ones((m, times.size + 1))
    for j, t in enumerate(times, start=1):
        q = 1.0 - math.exp(-hazard * t)
        conditional = _norm_cdf_np(
            (_norm_ppf_np(q) - math.sqrt(rho) * nodes) / math.sqrt(1.0 - rho)
        )
        expected[:, j] = _binomial_pmf_np(n, conditional) @ principal
    dt = times - previous
    discount, discount_mid = np.exp(-r * times), np.exp(-r * 0.5 * (times + previous))
    loss = expected[:, :-1] - expected[:, 1:]
    annuity = weights @ (dt * expected[:, 1:] * discount).sum(axis=1)
    accrual = weights @ (0.5 * dt * loss * discount_mid).sum(axis=1)
    protection = weights @ (loss * discount_mid).sum(axis=1)
    return float(annuity), float(accrual), float(protection)


def _survival_np(knots: np.ndarray, hazards: np.ndarray, t: np.ndarray) -> np.ndarray:
    """S(t) for piecewise-constant forward hazards on (0,k_1], (k_1,k_2], ... (flat beyond)."""
    knots = np.asarray(knots, dtype=float)
    hazards = np.asarray(hazards, dtype=float)
    t = np.asarray(t, dtype=float)
    lower = np.concatenate([[0.0], knots[:-1]])
    total = np.zeros_like(t)
    for lo, hi, lam in zip(lower, knots, hazards, strict=True):
        total = total + lam * np.clip(np.minimum(t, hi) - lo, 0.0, None)
    total = total + hazards[-1] * np.clip(t - knots[-1], 0.0, None)
    return np.exp(-total)


def _cds_legs_np(
    knots: np.ndarray,
    hazards: np.ndarray,
    recovery: float,
    r: float,
    maturity: float,
    freq: int,
    start: float = 0.0,
) -> tuple[float, float, float]:
    """Hull §25.2 legs (annuity, accrual, protection) without hullkit.

    Defaults at period midpoints, half-period accrual, unconditional survival
    weights (so ``start > 0`` values a forward-start CDS that knocks out).
    """
    n = round((maturity - start) * freq)
    times = start + np.arange(1, n + 1) / freq
    dt = 1.0 / freq
    survival = _survival_np(knots, hazards, times)
    default_in_period = _survival_np(knots, hazards, times - dt) - survival
    annuity = float(np.sum(survival * dt * np.exp(-r * times)))
    accrual = float(np.sum(0.5 * dt * default_in_period * np.exp(-r * (times - 0.5 * dt))))
    protection = float(
        np.sum((1.0 - recovery) * default_in_period * np.exp(-r * (times - 0.5 * dt)))
    )
    return annuity, accrual, protection


def _black_cds_option_np(
    forward: float, strike: np.ndarray, sigma: float, expiry: float, annuity: float, payer: bool
) -> np.ndarray:
    vol = sigma * math.sqrt(expiry)
    d1 = (np.log(forward / strike) + 0.5 * vol * vol) / vol
    d2 = d1 - vol
    if payer:
        return annuity * (forward * _norm_cdf_np(d1) - strike * _norm_cdf_np(d2))
    return annuity * (strike * _norm_cdf_np(-d2) - forward * _norm_cdf_np(-d1))


def _volume28(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    recovery = float(metrics.get("recovery", 0.4))

    # 1. CDS legs recomputed from the hazard, discount rate and recovery (Table
    #    25.2–25.4), then compared with the committed columns before re-summing.
    cds_year = np.asarray(arrays["cds_year"], dtype=float)
    cds_hazard, cds_rate = float(metrics["cds_hazard"]), float(metrics["cds_rate"])
    survival = np.exp(-cds_hazard * cds_year)
    default_prob = -np.diff(np.concatenate([[1.0], survival]))
    discount_end, discount_mid = np.exp(-cds_rate * cds_year), np.exp(-cds_rate * (cds_year - 0.5))
    payment_pv = survival * discount_end
    accrual_pv = 0.5 * default_prob * discount_mid
    payoff_pv = (1.0 - recovery) * default_prob * discount_mid
    column_gap = max(
        float(np.max(np.abs(survival - arrays["cds_survival"]))),
        float(np.max(np.abs(default_prob - arrays["cds_default_prob"]))),
        float(np.max(np.abs(payment_pv - arrays["cds_payment_pv"]))),
        float(np.max(np.abs(accrual_pv - arrays["cds_accrual_pv"]))),
        float(np.max(np.abs(payoff_pv - arrays["cds_payoff_pv"]))),
    )
    annuity = float(np.sum(payment_pv))
    accrual = float(np.sum(accrual_pv))
    payoff = float(np.sum(payoff_pv))
    spread_bp = payoff / (annuity + accrual) * 1e4
    _add(
        checks,
        "cds_par_spread_hull_pin",
        spread_bp,
        "survival/DF/PV columns recomputed from λ, r, R match the committed columns (1e-12); "
        "Σpayoff/(Σpayment+Σaccrual) within 0.5 bp of Hull's 123 bp and 1e-9 bp of the metric",
        column_gap <= 1e-12
        and abs(spread_bp - 123.0) <= 0.5
        and abs(spread_bp - float(metrics["cds_par_spread_bp"])) <= 1e-9,
    )

    # 2. Mark-to-market identity at 150 bp.
    mtm = (annuity + accrual) * 0.015 - payoff
    grid = np.asarray(arrays["cds_contract_spread_grid"], dtype=float)
    at_150 = float(np.asarray(arrays["cds_mtm_seller"])[np.argmin(np.abs(grid - 0.015))])
    _add(
        checks,
        "cds_mtm_identity",
        mtm,
        "D·0.015 − protection equals the stored metric and the grid value (1e-10) and Hull's 0.0111 (1e-4)",
        abs(mtm - float(metrics["cds_mtm_seller_150bp"])) <= 1e-10
        and abs(mtm - at_150) <= 1e-10
        and abs(mtm - 0.0111) <= 1e-4,
    )

    # 3. CDS bootstrap: the committed piecewise-constant hazards reprice the
    #    market quotes when the legs are rebuilt here from hazard, tenor, r, R.
    market_tenor = np.asarray(arrays["cds_market_tenor"], dtype=float)
    market_spread = np.asarray(arrays["cds_market_spread"], dtype=float)
    bootstrap_hazard = np.asarray(arrays["cds_bootstrap_hazard"], dtype=float)
    bootstrap_freq = int(metrics["cds_bootstrap_freq"])
    repriced = np.empty(market_tenor.size)
    for i, tenor in enumerate(market_tenor):
        a_i, b_i, c_i = _cds_legs_np(
            market_tenor, bootstrap_hazard, recovery, cds_rate, float(tenor), bootstrap_freq
        )
        repriced[i] = c_i / (a_i + b_i)
    reprice_error = float(np.max(np.abs(repriced - market_spread)))
    stored_gap = float(np.max(np.abs(repriced - arrays["cds_bootstrap_repriced_spread"])))
    _add(
        checks,
        "cds_bootstrap_round_trip",
        reprice_error,
        "par spreads rebuilt from the committed hazards reprice the quotes (1e-10) and match "
        "the stored repricing (1e-12)",
        reprice_error <= 1e-10 and stored_gap <= 1e-12,
    )

    # 4. Bond bootstrap vs Hull Example 24.2.
    hazard_error = float(
        np.max(
            np.abs(
                np.asarray(arrays["bond_bootstrap_hazard"])
                - np.asarray(arrays["hull_bond_bootstrap_hazard"])
            )
        )
    )
    loss_error = float(
        np.max(np.abs(np.asarray(arrays["bond_expected_loss_pv"]) - np.array([1.50, 3.53, 5.61])))
    )
    _add(
        checks,
        "bond_bootstrap_hull_pin",
        max(hazard_error, loss_error),
        "hazards within 0.0002 of 2.46/3.48/3.74% and loss PVs within 0.01 of 1.50/3.53/5.61",
        hazard_error <= 2e-4 and loss_error <= 0.01,
    )

    # 5. Fixed-coupon price identity (Example 25.1): the risky duration D is
    #    rebuilt from the implied hazard, which must itself reprice the quote.
    fixed_hazard = float(metrics["fixed_coupon_hazard"])
    fixed_maturity = float(metrics["fixed_coupon_maturity"])
    a_f, b_f, c_f = _cds_legs_np(
        np.array([fixed_maturity]),
        np.array([fixed_hazard]),
        recovery,
        float(metrics["fixed_coupon_rate"]),
        fixed_maturity,
        int(metrics["fixed_coupon_freq"]),
    )
    duration = a_f + b_f
    duration_gap = abs(duration - float(metrics["fixed_coupon_duration"]))
    quote_gap = abs(c_f / duration - float(metrics["fixed_coupon_spread"]))
    price = 100.0 - 100.0 * duration * (
        float(metrics["fixed_coupon_spread"]) - float(metrics["fixed_coupon_coupon"])
    )
    _add(
        checks,
        "fixed_coupon_price_identity",
        price,
        "D rebuilt from the implied hazard matches the metric (1e-12) and reprices the quote "
        "(1e-10); 100 − 100·D·(s−c) equals the stored price (1e-10) and Hull's 100.27 (0.01)",
        duration_gap <= 1e-12
        and quote_gap <= 1e-10
        and abs(price - float(metrics["fixed_coupon_price"])) <= 1e-10
        and abs(price - 100.27) <= 0.01,
    )

    # 6. Forward spread, forward risky duration and Black-type values are
    #    rebuilt from the committed hazard curve; then payer/receiver parity.
    strikes = np.asarray(arrays["option_strike_grid"], dtype=float)
    a_o, b_o, c_o = _cds_legs_np(
        np.asarray(arrays["option_curve_tenor"], dtype=float),
        np.asarray(arrays["option_curve_hazard"], dtype=float),
        recovery,
        cds_rate,
        float(metrics["option_maturity"]),
        int(metrics["option_freq"]),
        start=float(metrics["option_start"]),
    )
    option_annuity = a_o + b_o
    option_forward = c_o / option_annuity
    option_inputs_gap = max(
        abs(option_annuity - float(metrics["option_risky_annuity"])),
        abs(option_forward - float(metrics["option_forward_spread"])),
    )
    sigma_o, expiry_o = float(metrics["option_sigma"]), float(metrics["option_expiry"])
    payer = _black_cds_option_np(option_forward, strikes, sigma_o, expiry_o, option_annuity, True)
    receiver = _black_cds_option_np(
        option_forward, strikes, sigma_o, expiry_o, option_annuity, False
    )
    option_value_gap = max(
        float(np.max(np.abs(payer - arrays["payer_value"]))),
        float(np.max(np.abs(receiver - arrays["receiver_value"]))),
    )
    parity = float(np.max(np.abs(payer - receiver - option_annuity * (option_forward - strikes))))
    _add(
        checks,
        "cds_option_parity",
        parity,
        "F and A rebuilt from the hazard curve match the metrics (1e-12), Black values match the "
        "committed grids (1e-10), and max |payer − receiver − A(F−K)| <= 1e-10",
        option_inputs_gap <= 1e-12 and option_value_gap <= 1e-10 and parity <= 1e-10,
    )

    # 7. Mezzanine tranche: re-integrate A, B, C from the committed E_j(F_k) and reprice
    #    independently with the numpy-only standard market model above.
    times = np.asarray(arrays["tranche_payment_time"], dtype=float)
    weights = np.asarray(arrays["factor_weight"], dtype=float)
    expected = np.asarray(arrays["tranche_expected_principal"], dtype=float)
    previous = np.concatenate([[0.0], times[:-1]])
    r_cdo = float(metrics["cdo_rate"])
    dt = times - previous
    loss = expected[:, :-1] - expected[:, 1:]
    a_val = float(weights @ (dt * expected[:, 1:] * np.exp(-r_cdo * times)).sum(axis=1))
    b_val = float(
        weights @ (0.5 * dt * loss * np.exp(-r_cdo * 0.5 * (times + previous))).sum(axis=1)
    )
    c_val = float(weights @ (loss * np.exp(-r_cdo * 0.5 * (times + previous))).sum(axis=1))
    mezz_bp = c_val / (a_val + b_val) * 1e4
    a_ind, b_ind, c_ind = _tranche_legs_np(
        float(metrics["cdo_index_hazard"]),
        recovery,
        r_cdo,
        5.0,
        0.03,
        0.06,
        125,
        float(metrics["cdo_rho"]),
    )
    independent_bp = c_ind / (a_ind + b_ind) * 1e4
    _add(
        checks,
        "cdo_mezz_spread_hull_pin",
        mezz_bp,
        "re-integrated C/(A+B) within 1 bp of Hull's 348 bp, 1e-9 bp of the stored metric, and "
        "1e-6 bp of an independent numpy repricing; A/B/C within 0.002 of 4.2846/0.0187/0.1496",
        abs(mezz_bp - 348.0) <= 1.0
        and abs(mezz_bp - float(metrics["cdo_mezz_spread_bp"])) <= 1e-9
        and abs(mezz_bp - independent_bp) <= 1e-6
        and abs(a_val - 4.2846) <= 2e-3
        and abs(b_val - 0.0187) <= 2e-3
        and abs(c_val - 0.1496) <= 2e-3,
    )

    # 8. Expected principal is monotone in time and in the factor.
    nodes = np.asarray(arrays["factor_node"], dtype=float)
    order = np.argsort(nodes)
    time_monotone = float(np.max(np.diff(expected, axis=1)))
    factor_monotone = float(np.min(np.diff(expected[order, -1])))
    _add(
        checks,
        "expected_principal_monotone",
        max(time_monotone, -factor_monotone),
        "E_j(F) non-increasing in j and non-decreasing in F (1e-12)",
        time_monotone <= 1e-12 and factor_monotone >= -1e-12,
    )

    # 9. Loss conservation across the capital structure, with every tranche's
    #    expected loss and the 0–100% total repriced by the numpy model.
    cs_attach = np.asarray(arrays["capital_structure_attach"], dtype=float)
    cs_detach = np.asarray(arrays["capital_structure_detach"], dtype=float)
    cdo_hazard, cdo_rho = float(metrics["cdo_index_hazard"]), float(metrics["cdo_rho"])
    cdo_maturity, cdo_names = float(metrics["cdo_maturity"]), int(metrics["cdo_names"])
    tranche_loss = np.array(
        [
            _tranche_legs_np(
                cdo_hazard, recovery, r_cdo, cdo_maturity, float(lo), float(hi), cdo_names, cdo_rho
            )[2]
            for lo, hi in zip(cs_attach, cs_detach, strict=True)
        ]
    )
    portfolio_loss = _tranche_legs_np(
        cdo_hazard, recovery, r_cdo, cdo_maturity, 0.0, 1.0, cdo_names, cdo_rho
    )[2]
    tranche_gap = max(
        float(np.max(np.abs(tranche_loss - arrays["capital_structure_expected_loss"]))),
        abs(portfolio_loss - float(metrics["portfolio_expected_loss"])),
    )
    widths = cs_detach - cs_attach
    conservation = float(abs(widths @ tranche_loss - portfolio_loss))
    _add(
        checks,
        "capital_structure_loss_conservation",
        conservation,
        "tranche and 0–100% expected losses repriced independently match the committed values "
        "(1e-9); Σ width·C_tranche equals the 0–100% expected loss (1e-8)",
        tranche_gap <= 1e-9 and conservation <= 1e-8,
    )

    # 10. Third-to-default: the conditional P(≥k defaults by t | F) grid is rebuilt
    #     from the one-factor copula on the committed nodes, then re-summed;
    #     spreads fall with k.
    kth_weights = np.asarray(arrays["kth_factor_weight"], dtype=float)
    kth_nodes = np.asarray(arrays["kth_factor_node"], dtype=float)
    cumulative = np.asarray(arrays["kth_conditional_cumulative_prob"], dtype=float)
    kth_times = np.arange(1.0, cumulative.shape[1])
    r_kth = float(metrics["kth_rate"])
    kth_n, kth_k = int(metrics["kth_names"]), int(metrics["kth_pinned_order"])
    kth_lambda, kth_rho = float(metrics["kth_hazard"]), float(metrics["kth_rho"])
    rebuilt = np.zeros_like(cumulative)
    for j, t in enumerate(kth_times, start=1):
        q_t = 1.0 - math.exp(-kth_lambda * t)
        conditional = _norm_cdf_np(
            (_norm_ppf_np(q_t) - math.sqrt(kth_rho) * kth_nodes) / math.sqrt(1.0 - kth_rho)
        )
        rebuilt[:, j] = _binomial_pmf_np(kth_n, conditional)[:, kth_k:].sum(axis=1)
    kth_grid_gap = float(np.max(np.abs(rebuilt - cumulative)))
    kth_maturity_ok = cumulative.shape[1] == round(float(metrics["kth_maturity"])) + 1
    trigger = cumulative[:, 1:] - cumulative[:, :-1]
    disc_mid = np.exp(-r_kth * (kth_times - 0.5))
    kth_payoff = float(kth_weights @ ((1.0 - recovery) * trigger * disc_mid).sum(axis=1))
    kth_annuity = float(
        kth_weights @ ((1.0 - cumulative[:, 1:]) * np.exp(-r_kth * kth_times)).sum(axis=1)
    )
    kth_accrual = float(kth_weights @ (0.5 * trigger * disc_mid).sum(axis=1))
    kth_bp = kth_payoff / (kth_annuity + kth_accrual) * 1e4
    kth_spreads = np.asarray(arrays["kth_spread"], dtype=float)
    _add(
        checks,
        "kth_to_default_hull_pin_and_ordering",
        kth_bp,
        "conditional cumulative probabilities rebuilt from the copula match the committed grid "
        "(1e-10); re-summed 3rd-to-default spread within 1 bp of Hull's 153 bp and 1e-9 bp of "
        "the metric; spreads strictly decrease in k",
        kth_grid_gap <= 1e-10
        and kth_maturity_ok
        and abs(kth_bp - 153.0) <= 1.0
        and abs(kth_bp - float(metrics["kth3_spread_bp"])) <= 1e-9
        and bool(np.all(np.diff(kth_spreads) < 0.0)),
    )

    # 11. Compound correlations reprice Table 25.6 (independent numpy pricer).
    attach = np.asarray(arrays["market_tranche_attach"], dtype=float)
    detach = np.asarray(arrays["market_tranche_detach"], dtype=float)
    quotes = np.asarray(arrays["market_tranche_quote"], dtype=float)
    compound = np.asarray(arrays["compound_correlation"], dtype=float)
    hazard_itx, r_itx = float(metrics["itraxx_hazard"]), float(metrics["itraxx_rate"])
    reprice = np.empty(quotes.size)
    for i in range(quotes.size):
        a_i, b_i, c_i = _tranche_legs_np(
            hazard_itx,
            recovery,
            r_itx,
            5.0,
            float(attach[i]),
            float(detach[i]),
            125,
            float(compound[i]),
        )
        reprice[i] = c_i - 0.05 * (a_i + b_i) if i == 0 else c_i / (a_i + b_i)
    reprice_gap = float(np.max(np.abs(reprice - quotes)))
    _add(
        checks,
        "implied_correlation_reprices_quotes",
        reprice_gap,
        "independent repricing at the committed compound correlations within 1e-6 of the quotes "
        "(0.01 bp / 1e-4 upfront points)",
        reprice_gap <= 1e-6,
    )

    # 12. Table 25.8 pins.
    compound_gap = float(
        np.max(np.abs(compound - np.asarray(arrays["hull_compound_correlation"], dtype=float)))
    )
    base_gap = float(
        np.max(
            np.abs(
                np.asarray(arrays["base_correlation"], dtype=float)
                - np.asarray(arrays["hull_base_correlation"], dtype=float)
            )
        )
    )
    _add(
        checks,
        "implied_correlation_hull_pin",
        max(compound_gap, base_gap),
        "compound and base correlations within 1.0 point of Table 25.8",
        compound_gap <= 0.01 and base_gap <= 0.01,
    )

    # 13. Base correlations and the expected-loss curve are repriced: the 0–X_q
    #     tranche at the committed base correlation must carry the cumulative
    #     expected loss of the compound-priced tranches (Hull's step 3/4), and
    #     the curve is increasing in X with a decreasing slope ΔEL/ΔX (the X
    #     grid is uneven, so slopes rather than second differences are tested).
    curve = np.asarray(arrays["el_curve_value"], dtype=float)
    curve_x = np.asarray(arrays["el_curve_x"], dtype=float)
    base = np.asarray(arrays["base_correlation"], dtype=float)
    itraxx_maturity, itraxx_names = float(metrics["itraxx_maturity"]), int(metrics["cdo_names"])
    compound_loss = np.array(
        [
            _tranche_legs_np(
                hazard_itx,
                recovery,
                r_itx,
                itraxx_maturity,
                float(attach[i]),
                float(detach[i]),
                itraxx_names,
                float(compound[i]),
            )[2]
            for i in range(quotes.size)
        ]
    )
    cumulative_loss = np.cumsum(compound_loss * (detach - attach))
    base_loss = np.array(
        [
            _tranche_legs_np(
                hazard_itx,
                recovery,
                r_itx,
                itraxx_maturity,
                0.0,
                float(x),
                itraxx_names,
                float(rho),
            )[2]
            for x, rho in zip(curve_x, base, strict=True)
        ]
    )
    base_gap = float(np.max(np.abs(base_loss * curve_x - cumulative_loss)))
    curve_gap = float(np.max(np.abs(base_loss * curve_x - curve)))
    tranche_loss_gap = float(np.max(np.abs(compound_loss - arrays["tranche_expected_loss"])))
    slopes = np.diff(curve) / np.diff(curve_x)
    _add(
        checks,
        "base_correlation_curve_shape",
        float(np.max(np.diff(slopes))),
        "0–X% tranches repriced at the committed base correlations carry the cumulative "
        "compound-priced expected loss (1e-8) and equal the committed curve (1e-10); the curve "
        "is increasing in X with strictly decreasing slope ΔEL/ΔX",
        base_gap <= 1e-8
        and curve_gap <= 1e-10
        and tranche_loss_gap <= 1e-9
        and bool(np.all(np.diff(curve) > 0.0))
        and bool(np.all(np.diff(slopes) < 0.0)),
    )

    # 14. Double-t limit against a Gaussian spread repriced here (the stored
    #     Gaussian metric is checked, not trusted).
    gaussian_bp = independent_bp
    gaussian_gap_bp = abs(gaussian_bp - float(metrics["gaussian_mezz_spread"]) * 1e4)
    gap_bp = float(abs(np.asarray(arrays["double_t_spread"], dtype=float)[-1] * 1e4 - gaussian_bp))
    _add(
        checks,
        "double_t_gaussian_limit",
        gap_bp,
        "stored Gaussian mezzanine spread matches the independent repricing (1e-6 bp); ν→∞ "
        "double-t spread within 0.5 bp of it",
        gaussian_gap_bp <= 1e-6 and gap_bp <= 0.5,
    )

    # 15. ASB recursion equals the binomial pmf (both recomputed here).
    probe = np.asarray(arrays["asb_probe_prob"], dtype=float)
    recursion = np.zeros(probe.size + 1)
    recursion[0] = 1.0
    for p_i in probe:
        recursion = recursion * (1.0 - p_i) + np.concatenate([[0.0], recursion[:-1]]) * p_i
    binomial = _binomial_pmf_np(probe.size, np.array(probe[0]))
    asb_gap = float(
        max(
            np.max(np.abs(recursion - binomial)),
            np.max(np.abs(recursion - np.asarray(arrays["asb_probe_pmf"], dtype=float))),
        )
    )
    _add(
        checks,
        "heterogeneous_equals_binomial",
        asb_gap,
        "recursion pmf equals the binomial pmf and the committed pmf (1e-12)",
        asb_gap <= 1e-12,
    )

    # 16. CreditMetrics thresholds from the committed matrix; correlation fattens the tail.
    #     The default boundary is N⁻¹(1 − p_default) (Hull 2.9290 for BBB), not the
    #     cumulative sum, because the printed rows carry a 0.01-point rounding residual.
    matrix = np.asarray(arrays["transition_matrix"], dtype=float)
    aaa = np.array([_norm_ppf_np(float(p)) for p in np.cumsum(matrix[0])[:3]])
    bbb = np.array([_norm_ppf_np(float(p)) for p in np.cumsum(matrix[3])[:3]])
    bbb_default = _norm_ppf_np(1.0 - float(matrix[3][-1]))
    stored_gap = max(
        float(np.max(np.abs(np.asarray(arrays["threshold_aaa"], dtype=float)[:3] - aaa))),
        float(np.max(np.abs(np.asarray(arrays["threshold_bbb"], dtype=float)[:3] - bbb))),
        abs(bbb_default - float(metrics["creditmetrics_bbb_default_threshold"])),
    )
    threshold_gap = float(
        max(
            np.max(np.abs(aaa - np.asarray(arrays["hull_threshold_aaa"]))),
            np.max(np.abs(bbb - np.asarray(arrays["hull_threshold_bbb"]))),
            abs(bbb_default - 2.9290),
        )
    )
    losses = np.asarray(arrays["credit_loss_by_case"], dtype=float)
    var_independent = float(np.quantile(losses[0], 0.999))
    var_correlated = float(np.quantile(losses[1], 0.999))
    _add(
        checks,
        "creditmetrics_thresholds_hull_pin",
        threshold_gap,
        "thresholds recomputed from Table 24.4 within 0.0002 of Hull and 1e-9 of the stored "
        "values; 99.9% credit VaR larger with ρ=0.2 than independent",
        threshold_gap <= 2e-4 and stored_gap <= 1e-9 and var_correlated > var_independent,
    )

    # 17. Netting, collateral rule, and eq. 24.5.
    trades = np.asarray(arrays["netting_trade_value"], dtype=float)
    netted, gross = max(float(trades.sum()), 0.0), float(np.maximum(trades, 0.0).sum())
    value = np.asarray(arrays["collateral_case_value"], dtype=float)
    lagged = np.asarray(arrays["collateral_case_lagged"], dtype=float)
    exposure = np.maximum(value - np.maximum(lagged, 0.0), 0.0) + np.maximum(
        np.maximum(-lagged, 0.0) - np.maximum(-value, 0.0), 0.0
    )
    collateral_gap = float(
        np.max(np.abs(exposure - np.asarray(arrays["hull_collateral_case_exposure"], dtype=float)))
    )
    cva_hazard, cva_horizon = float(metrics["cva_hazard"]), float(metrics["cva_horizon"])
    cva_grid = np.asarray(arrays["cva_grid_time"], dtype=float)
    q_rebuilt = -np.diff(np.exp(-cva_hazard * cva_grid))
    q_gap = float(np.max(np.abs(q_rebuilt - arrays["cva_default_prob"])))
    f_nd = float(metrics["cva_no_default_value"])
    # Constant hazard: Σq_i telescopes to 1 − e^{−λT}, and with the exposure
    # growing at the discount rate the general integral has the same value.
    cva_closed = (1.0 - recovery) * f_nd * (1.0 - math.exp(-cva_hazard * cva_horizon))
    cva_special = (1.0 - recovery) * f_nd * float(np.sum(q_rebuilt))
    cva_gap = max(
        abs(cva_special - float(metrics["cva_special_case"])),
        abs(cva_closed - cva_special),
        abs(float(cva_grid[-1]) - cva_horizon),
        q_gap,
    )
    general_gap = abs(float(metrics["cva_general_equivalent"]) - cva_closed)
    _add(
        checks,
        "netting_collateral_and_cva_special_case",
        max(collateral_gap, cva_gap, general_gap),
        "netting 15 <= gross 40 (Hull 24.7); Example 24.4 exposures 5/0/0/5; q_i rebuilt from "
        "the hazard match the grid (1e-12), (1−R)f_nd Σq_i equals the stored CVA and the closed "
        "form (1−R)f_nd(1−e^{−λT}) (1e-12), and the general CVA on a 2000-step grid (1e-5)",
        netted == 15.0
        and gross == 40.0
        and netted <= gross
        and collateral_gap <= 1e-12
        and cva_gap <= 1e-12
        and general_gap <= 1e-5,
    )

    return checks, [
        "Hull Table 24.4 (S&P 1981–2019) and Table 25.6 (Creditex iTraxx quotes, 2007-01-31) are transcribed textbook constants, not downloaded market data.",
        "The Table 25.8 implied correlations match Hull to one decimal place; residual differences reflect DerivaGem's integration grid, not calibration quality.",
        "The double-t copula and ASB recursion are validated only by limits (ν→∞, homogeneous); Hull prints no numeric example for §25.11.",
        "Random recovery / random factor loadings, the implied copula, dynamic models and KMV EDF mappings have no code; the notebook section 本巻で実装しない節 summarizes Hull's description of each and how it differs from the constant-rho, constant-R quadrature implemented here.",
        "CDS options use the Black-type formula on the survival-weighted forward risky duration, so pre-expiry default knocks the option out. The spread volatility is an input assumption (0.6) rather than derived from a stochastic hazard-rate model, the lognormal-spread assumption is not tested, and no non-knock-out (front-end protection) variant is implemented; Hull defers these to Hull and White (2003).",
    ]


_EVALUATORS = {
    18: _volume18,
    19: _volume19,
    20: _volume20,
    21: _volume21,
    22: _volume22,
    23: _volume23,
    24: _volume24,
    25: _volume25,
    26: _volume26,
    27: _volume27,
    28: _volume28,
}


def evaluate_acceptance(
    volume: int,
    metrics: dict[str, Any],
    arrays: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Return the canonical gate record; this does not approve empirical performance.

    A numerical failure inside an evaluator (a zero division, a math domain
    error, an empty slice) on tampered or degenerate inputs yields a failing
    record with a single ``gate_evaluation`` check naming the exception, so the
    caller still gets a diagnosable FAIL instead of an aborted run. Missing keys
    and wrong types are schema errors and still raise.
    """
    try:
        evaluator = _EVALUATORS[volume]
    except KeyError as exc:
        raise ValueError("acceptance volume must lie in [18, 28]") from exc
    try:
        checks, negative_results = evaluator(metrics, arrays)
    except (ArithmeticError, IndexError, ValueError) as exc:
        checks = []
        _add(
            checks,
            "gate_evaluation",
            f"{type(exc).__name__}: {exc}",
            "the volume evaluator completes on the committed inputs",
            False,
        )
        negative_results = []
    return {
        "schema_version": 1,
        "scope": "integration_and_reproducibility",
        "model_performance_approved": False,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "negative_results": negative_results,
    }
