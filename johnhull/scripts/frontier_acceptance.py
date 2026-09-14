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
    _add(
        checks,
        "split_overlap_count",
        metrics["split_overlap_count"],
        "== 0",
        metrics["split_overlap_count"] == 0,
    )
    _add(
        checks,
        "price_mae_normalized",
        metrics["price_mae_normalized"],
        "< 0.001",
        metrics["price_mae_normalized"] < 1e-3,
    )
    _add(checks, "delta_mae", metrics["delta_mae"], "< 0.002", metrics["delta_mae"] < 2e-3)
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
    coverage = metrics["teacher_ci_coverage_20_seeds_by_estimand"]
    coverage_ok = all(0.80 <= float(value) <= 1.0 for value in coverage.values())
    _add(
        checks,
        "mc_ci_coverage",
        min(coverage.values()),
        "each estimand in [0.80, 1.00]",
        coverage_ok,
    )
    ratios = metrics["teacher_se_ratio_4x_paths_by_estimand"]
    ratio_ok = all(0.40 <= float(value) <= 0.60 for value in ratios.values())
    _add(
        checks,
        "mc_standard_error_scaling",
        max(ratios.values()),
        "each 4x-path ratio in [0.40, 0.60]",
        ratio_ok,
    )
    negative = []
    if not metrics["soft_penalty_improved_hard_checks"]:
        negative.append("The quick soft-penalty ablation did not improve the hard-check count.")
    if metrics["break_even_batch"] is None:
        negative.append(
            "No neural CPU break-even batch was observed in the measured quick profile."
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
    _add(
        checks,
        "forward_repricing_rmse",
        calibration["repricing_rmse"],
        "< 1e-5",
        calibration["repricing_rmse"] < 1e-5,
    )
    hard_complete = (
        hard["check_set_complete"]
        and hard["arbitrage_free"]
        and all(item["passed"] for item in hard["checks"])
    )
    _add(
        checks, "hard_surface_report", hard_complete, "complete and all checks pass", hard_complete
    )
    _add(
        checks,
        "raw_stress_detected",
        reports["raw"]["arbitrage_free"],
        "is false",
        not reports["raw"]["arbitrage_free"],
    )
    distinct_refits = (
        refits["actual_refit_per_lambda"] and refits["candidate_parameter_unique_count"] >= 2
    )
    _add(
        checks,
        "joint_variance_refits",
        refits["candidate_parameter_unique_count"],
        ">= 2 distinct actual refits",
        distinct_refits,
    )
    variance_improved = points[-1]["variance_loss"] < points[0]["variance_loss"]
    _add(
        checks,
        "variance_pareto_improvement",
        points[-1]["variance_loss"],
        "< lambda=0 variance loss",
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
    )
    _add(
        checks,
        "direct_inverse_evidence",
        metrics["direct_inverse"]["test_rows"],
        "aligned parameter and repricing ablation arrays",
        inverse_ok,
    )
    pareto_ok = (
        arrays["pareto_losses"].shape == (len(points), 3)
        and arrays["pareto_fit_parameters"].shape[0] == len(points)
        and arrays["pareto_nondominated"].shape == (len(points),)
        and np.all(arrays["pareto_nondominated"] == 1)
        and np.all(np.isfinite(arrays["pareto_losses"]))
    )
    _add(
        checks,
        "pareto_evidence",
        len(points),
        "each actual refit has losses, parameters, and nondominance status",
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
    intervals_ok = all(
        model["qlike_block_bootstrap_ci"]["lower_95"]
        <= model["qlike_block_bootstrap_ci"]["mean"]
        <= model["qlike_block_bootstrap_ci"]["upper_95"]
        for model in walk["models"].values()
    )
    _add(checks, "block_bootstrap_intervals", intervals_ok, "ordered for every model", intervals_ok)
    detailed_intervals_ok = True
    for horizon in horizons:
        comparison = comparisons[str(horizon)]
        detailed_intervals_ok &= set(
            comparison["paired_qlike_difference_model_minus_log_har"]
        ) == full_models - {"log_har"}
        for model in comparison["models"].values():
            detailed_intervals_ok &= set(model["by_regime"]) == {"low", "middle", "high"}
            for scope in [model, *model["by_regime"].values()]:
                detailed_intervals_ok &= scope.get("n_observations", 1) > 0
                detailed_intervals_ok &= all(
                    interval["lower_95"] <= interval["estimate"] <= interval["upper_95"]
                    for interval in scope["intervals_95"].values()
                )
        detailed_intervals_ok &= all(
            interval["lower_95"] <= interval["mean"] <= interval["upper_95"]
            for interval in comparison["paired_qlike_difference_model_minus_log_har"].values()
        )
    _add(
        checks,
        "horizon_regime_intervals",
        len(horizons),
        "QLIKE/RMSE/MAE and paired Log-HAR comparisons have ordered block CIs",
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
    )
    _add(
        checks,
        "economic_comparison_controls",
        paths,
        "common paths/premium/costs and explicit no-trade region",
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
    _add(
        checks,
        "surrogate_speedup",
        metrics["surrogate_speedup_1024"],
        "> 1 at batch 1024",
        metrics["surrogate_speedup_1024"] > 1.0,
    )
    joint_reported = all(
        np.isfinite(metrics[name])
        for name in (
            "joint_spx_rmse",
            "joint_vix_rmse",
            "joint_vix_option_rmse",
            "joint_variance_rmse",
        )
    )
    _add(
        checks,
        "joint_objective_components",
        joint_reported,
        "all four component errors finite",
        joint_reported,
    )
    domain_diagnostics = all(
        np.isfinite(metrics[name])
        for name in (
            "in_domain_price_rmse",
            "in_domain_delta_rmse",
            "in_domain_gamma_rmse",
            "ood_price_rmse",
            "ood_delta_rmse",
            "ood_gamma_rmse",
        )
    )
    _add(
        checks,
        "in_domain_ood_diagnostics",
        domain_diagnostics,
        "price, delta and gamma RMSE finite in both domains",
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
    calendar_ok = (
        metrics["calendar_violations"] == 0
        and metrics["adjacent_expiry_violations"] == 0
        and np.all(arrays["forward_variance"] >= 0)
    )
    _add(
        checks,
        "expiry_consistency",
        metrics["adjacent_expiry_violations"],
        "zero violations and nonnegative forward variance",
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
    _add(
        checks,
        "event_teacher_uncertainty",
        metrics["event_teacher_standard_error"],
        "> 0",
        metrics["event_teacher_standard_error"] > 0,
    )
    tod_ok = len(arrays["tod_names"]) == len(arrays["price_mae"]) == len(arrays["greek_mae"])
    _add(
        checks,
        "time_of_day_diagnostics",
        len(arrays["tod_names"]),
        "open/midday/close with aligned price and Greek buckets",
        tod_ok
        and arrays["tod_names"].tolist() == ["open", "midday", "close"]
        and set(arrays["time_of_day"].tolist()) == {"open", "midday", "close"},
    )
    event_mask = arrays["event_mask"].astype(bool)
    split_ok = (
        arrays["event_split_names"].tolist() == ["event", "non-event"]
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
    _add(
        checks,
        "daily_compounding_handcheck",
        metrics["daily_compounding_handcheck_error"],
        "< 1e-12",
        metrics["daily_compounding_handcheck_error"] < 1e-12,
    )
    _add(
        checks,
        "continuous_limit",
        metrics["continuous_limit_error"],
        "< 1e-5",
        metrics["continuous_limit_error"] < 1e-5,
    )
    _add(
        checks,
        "bachelier_quadrature_handcheck",
        metrics["quadrature_handcheck_error"],
        "< 1e-12",
        metrics["quadrature_handcheck_error"] < 1e-12
        and np.allclose(arrays["bachelier_price"], arrays["quadrature_price"], atol=1e-12),
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
    _add(
        checks,
        "cashflow_conservation",
        metrics["cashflow_conservation_error"],
        "< 1e-12",
        metrics["cashflow_conservation_error"] < 1e-12,
    )
    funding_ok = (
        metrics["funding_interval_hours"] > 0
        and metrics["funding_absolute_cap"] > 0
        and np.all(
            np.abs(arrays["funding_rate"]) <= arrays["funding_rate_cap"] + np.finfo(float).eps
        )
        and np.all(np.diff(arrays["funding_settled_intervals"]) >= 0)
        and np.max(np.abs(arrays["funding_conservation_error"])) < 1e-12
    )
    _add(
        checks,
        "funding_cap_interval",
        metrics["funding_interval_hours"],
        "positive interval, absolute cap, and conserved transfers",
        funding_ok,
    )
    _add(
        checks,
        "solvency_identity",
        metrics["solvency_identity_error"],
        "< 1e-12",
        metrics["solvency_identity_error"] < 1e-12,
    )
    _add(
        checks,
        "insurance_identity",
        metrics["insurance_identity_error"],
        "< 1e-12",
        metrics["insurance_identity_error"] < 1e-12,
    )
    waterfall = (
        metrics["ending_adl_notional"] > 0
        and metrics["ending_socialized_loss"] > 0
        and metrics["ending_uncovered_loss"] == 0
        and metrics["solvent"] is True
    )
    _add(
        checks,
        "stress_waterfall",
        metrics["ending_socialized_loss"],
        "ADL/social loss tracked with zero uncovered loss",
        waterfall,
    )
    methods_ok = (
        arrays["liquidation_method_names"].tolist() == ["forced_sale", "auction"]
        and np.max(np.abs(arrays["liquidation_method_conservation_error"])) < 1e-12
        and np.all(arrays["liquidation_method_uncovered_loss"] == 0)
        and np.all(np.isfinite(arrays["liquidation_method_socialized_loss"]))
    )
    _add(
        checks,
        "liquidation_method_waterfalls",
        len(arrays["liquidation_method_names"]),
        "forced sale and auction conserve their stress waterfalls",
        methods_ok,
    )
    amm_ok = float(np.max(np.abs(arrays["amm_identity_error"]))) < 1e-12
    _add(
        checks,
        "amm_identity",
        float(np.max(np.abs(arrays["amm_identity_error"]))),
        "< 1e-12",
        amm_ok,
    )
    cpmm_ok = (
        np.max(np.abs(arrays["cpmm_swap_identity_error"])) < 1e-12
        and np.all(arrays["cpmm_invariant_gain"] >= 0)
        and np.all(np.isfinite(arrays["fixed_fee_net_lvr"]))
        and np.all(np.isfinite(arrays["dynamic_fee_net_lvr"]))
        and np.all(np.isfinite(arrays["concentrated_lvr"]))
    )
    _add(
        checks,
        "amm_lvr_fee_variants",
        float(np.max(np.abs(arrays["cpmm_swap_identity_error"]))),
        "CPMM identity plus finite fixed/dynamic/concentrated LVR",
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
    _add(
        checks,
        "market_completeness",
        metrics["market_completeness"],
        "== incomplete",
        metrics["market_completeness"] == "incomplete",
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
    carbon_se = arrays["carbon_model_standard_error"]
    carbon_ok = (
        carbon_models == ["Black-76", "GBM MC", "Heston MC", "SV+jump MC"]
        and metrics["carbon_model_ladder_complete"] is True
        and arrays["carbon_model_price"].shape == carbon_se.shape
        and np.all(np.isfinite(arrays["carbon_model_price"]))
        and np.all(carbon_se >= 0)
        and np.all(carbon_se[1:] > 0)
    )
    _add(
        checks,
        "carbon_model_ladder",
        len(carbon_models),
        "Black-76 and three MC models with aligned uncertainty",
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
    ppa = (
        np.all(np.isfinite(arrays["cvar95"]))
        and np.all(np.isfinite(arrays["hedge_residual"]))
        and np.ptp(arrays["hedge_ratio_residual"]) > 0
    )
    _add(
        checks,
        "ppa_risk_decomposition",
        len(arrays["risk_names"]),
        "finite CVaR/residual and hedge sensitivity",
        ppa,
    )
    cashflow_ok = (
        arrays["cash_flow_at_risk"].shape
        == arrays["unhedged_cash_flow_std"].shape
        == arrays["expected_hedged_cash_flow"].shape
        and np.all(np.isfinite(arrays["cash_flow_at_risk"]))
        and np.all(np.isfinite(arrays["unhedged_cash_flow_std"]))
        and np.all(np.isfinite(arrays["expected_hedged_cash_flow"]))
        and metrics["ppa_cvar95"] >= metrics["ppa_cash_flow_at_risk95"] > 0
    )
    _add(
        checks,
        "ppa_cashflow_risk",
        metrics["ppa_cash_flow_at_risk95"],
        "finite aligned CFaR diagnostics and CVaR >= CFaR > 0",
        cashflow_ok,
    )
    return checks, [
        "Weather and PPA values are premium-principle dependent because the underlying market is incomplete."
    ]


def _volume26(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    _add(
        checks,
        "hull_white_initial_curve",
        metrics["hw_curve_fit_max_error"],
        "<= 1e-12",
        metrics["hw_curve_fit_max_error"] <= 1e-12,
    )
    _add(
        checks,
        "annual_seasonality_normalization",
        metrics["seasonality_annual_log_sum"],
        "<= 1e-12",
        metrics["seasonality_annual_log_sum"] <= 1e-12,
    )
    _add(
        checks,
        "zcis_quote_repricing",
        metrics["zcis_repricing_max_error"],
        "<= 1e-10",
        metrics["zcis_repricing_max_error"] <= 1e-10,
    )
    jy_shapes = arrays["jy_forward_index"].shape == arrays["jy_mc_forward_index"].shape == arrays[
        "jy_mc_standard_error"
    ].shape and np.all(arrays["jy_mc_standard_error"] > 0.0)
    _add(
        checks,
        "jy_forward_measure_mc",
        metrics["jy_forward_mc_zscore_max"],
        "aligned arrays and maximum analytic/MC z-score < 3",
        jy_shapes and metrics["jy_forward_mc_zscore_max"] < 3.0,
    )
    floor_shapes = (
        arrays["floor_analytic"].shape
        == arrays["floor_mc"].shape
        == arrays["floor_mc_standard_error"].shape
        == arrays["inflation_volatility"].shape
    )
    _add(
        checks,
        "jgbi_floor_analytic_mc",
        metrics["floor_mc_zscore_max"],
        "aligned arrays and maximum non-degenerate z-score < 3",
        floor_shapes and metrics["floor_mc_zscore_max"] < 3.0,
    )
    _add(
        checks,
        "floor_volatility_monotonicity",
        metrics["floor_monotone_in_volatility"],
        "analytic floor is non-decreasing in inflation volatility",
        metrics["floor_monotone_in_volatility"] is True,
    )
    redemption_only = (
        metrics["principal_floor_redemption_only"] is True
        and metrics["coupon_floor_max_error"] == 0.0
        and arrays["jgbi_floored_principal"][-1] > arrays["jgbi_unfloored_principal"][-1]
    )
    _add(
        checks,
        "redemption_only_principal_floor",
        metrics["coupon_floor_max_error"],
        "coupons identical and floored final principal exceeds unfloored principal",
        redemption_only,
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
    measure_ok = (
        metrics["measure_treatment"] == "nominal_payment_forward"
        and np.ptp(arrays["yoy_jy_ratio"] - arrays["yoy_deterministic_ratio"]) > 0.0
    )
    _add(
        checks,
        "nominal_payment_forward_measure",
        metrics["measure_treatment"],
        "explicit nominal payment-forward measure with non-zero YoY convexity",
        measure_ok,
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
    binomial_se = math.sqrt(0.05 * 0.95 / n_replications)
    size_zscore = abs(rejection_rate - 0.05) / binomial_se
    _add(
        checks,
        "kupiec_size_calibration",
        size_zscore,
        "iid rejection rate within z < 3 of nominal 5% (binomial SE, 400 replications)",
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

    # 4. FHS coverage beats plain HS on the GARCH path.
    hs_rate = float(np.asarray(arrays["hs_violations"], dtype=float).mean())
    fhs_rate = float(np.asarray(arrays["fhs_violations"], dtype=float).mean())
    coverage_improved = abs(fhs_rate - p) < abs(hs_rate - p)
    _add(
        checks,
        "fhs_coverage_improvement",
        fhs_rate,
        "|FHS violation rate - (1-alpha)| < |plain-HS violation rate - (1-alpha)|",
        coverage_improved,
    )

    # 5. GPD parameter recovery.
    xi_true = float(metrics["gpd_xi_true"])
    beta_true = float(metrics["gpd_beta_true"])
    xi_hat = float(metrics["gpd_xi_hat"])
    beta_hat = float(metrics["gpd_beta_hat"])
    xi_error = abs(xi_hat - xi_true)
    beta_ratio_error = abs(beta_hat / beta_true - 1.0)
    _add(
        checks,
        "gpd_parameter_recovery",
        xi_error,
        "|xi_hat - xi| <= 0.1 and |beta_hat/beta - 1| <= 0.15",
        xi_error <= 0.1 and beta_ratio_error <= 0.15,
    )

    # 6. EVT ES closed-form identity.
    threshold = float(metrics["evt_threshold"])
    evt_var = float(metrics["evt_var"])
    evt_es = float(metrics["evt_es"])
    evt_es_check = (evt_var + beta_hat - xi_hat * threshold) / (1.0 - xi_hat)
    evt_identity_error = abs(evt_es - evt_es_check)
    _add(
        checks,
        "evt_var_es_identity",
        evt_identity_error,
        "<= 1e-12",
        evt_identity_error <= 1e-12,
    )

    # 7. Analytic Euler additivity: components sum to normal VaR.
    component_var = np.asarray(arrays["alloc_component_var"], dtype=float)
    normal_var = float(metrics["alloc_normal_var"])
    euler_error = abs(float(component_var.sum()) - normal_var)
    _add(checks, "euler_additivity_normal", euler_error, "<= 1e-12", euler_error <= 1e-12)

    # 8. Analytic marginal VaR matches a central finite difference.
    amounts = np.asarray(arrays["alloc_amounts"], dtype=float)
    vols = np.asarray(arrays["alloc_vols"], dtype=float)
    corr = np.asarray(arrays["alloc_corr"], dtype=float)
    covariance = corr * np.outer(vols, vols)
    sigma_p = math.sqrt(float(amounts @ covariance @ amounts))
    z_alpha = normal_var / sigma_p  # recover z from committed data (avoids scipy)
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
    desk_sum_error = abs(float(position_full_pnl.sum()) - full_pnl)
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
        "including parallel_zero_rate with a non-zero rate delta and zero rate vega, and the "
        "per-position full P&L sums to the desk full P&L (<= 1e-9)",
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


def _volume28(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    recovery = float(metrics.get("recovery", 0.4))

    # 1. CDS par spread re-summed from the Table 25.2–25.4 columns.
    annuity = float(np.sum(arrays["cds_payment_pv"]))
    accrual = float(np.sum(arrays["cds_accrual_pv"]))
    payoff = float(np.sum(arrays["cds_payoff_pv"]))
    spread_bp = payoff / (annuity + accrual) * 1e4
    _add(
        checks,
        "cds_par_spread_hull_pin",
        spread_bp,
        "Σpayoff/(Σpayment+Σaccrual) within 0.5 bp of Hull's 123 bp and 1e-9 bp of the stored metric",
        abs(spread_bp - 123.0) <= 0.5
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

    # 3. CDS bootstrap reprices its quotes.
    reprice_error = float(
        np.max(
            np.abs(
                np.asarray(arrays["cds_bootstrap_repriced_spread"])
                - np.asarray(arrays["cds_market_spread"])
            )
        )
    )
    _add(
        checks,
        "cds_bootstrap_round_trip",
        reprice_error,
        "max |repriced − market| <= 1e-10",
        reprice_error <= 1e-10,
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

    # 5. Fixed-coupon price identity (Example 25.1).
    price = 100.0 - 100.0 * float(metrics["fixed_coupon_duration"]) * (
        float(metrics["fixed_coupon_spread"]) - float(metrics["fixed_coupon_coupon"])
    )
    _add(
        checks,
        "fixed_coupon_price_identity",
        price,
        "100 − 100·D·(s−c) equals the stored price (1e-10) and Hull's 100.27 (0.01)",
        abs(price - float(metrics["fixed_coupon_price"])) <= 1e-10 and abs(price - 100.27) <= 0.01,
    )

    # 6. Payer/receiver parity.
    strikes = np.asarray(arrays["option_strike_grid"], dtype=float)
    parity = float(
        np.max(
            np.abs(
                np.asarray(arrays["payer_value"])
                - np.asarray(arrays["receiver_value"])
                - float(metrics["option_risky_annuity"])
                * (float(metrics["option_forward_spread"]) - strikes)
            )
        )
    )
    _add(
        checks,
        "cds_option_parity",
        parity,
        "max |payer − receiver − A(F−K)| <= 1e-10",
        parity <= 1e-10,
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

    # 9. Loss conservation across the capital structure.
    widths = np.asarray(arrays["capital_structure_detach"], dtype=float) - np.asarray(
        arrays["capital_structure_attach"], dtype=float
    )
    conservation = float(
        abs(
            widths @ np.asarray(arrays["capital_structure_expected_loss"], dtype=float)
            - float(metrics["portfolio_expected_loss"])
        )
    )
    _add(
        checks,
        "capital_structure_loss_conservation",
        conservation,
        "Σ width·C_tranche equals the 0–100% expected loss (1e-8)",
        conservation <= 1e-8,
    )

    # 10. Third-to-default re-summed from the conditional cumulative probabilities;
    #     spreads fall with k.
    kth_weights = np.asarray(arrays["kth_factor_weight"], dtype=float)
    cumulative = np.asarray(arrays["kth_conditional_cumulative_prob"], dtype=float)
    kth_times = np.arange(1.0, cumulative.shape[1])
    r_kth = float(metrics["kth_rate"])
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
        "re-summed 3rd-to-default spread within 1 bp of Hull's 153 bp and 1e-9 bp of the metric; "
        "spreads strictly decrease in k",
        abs(kth_bp - 153.0) <= 1.0
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

    # 13. Expected-loss curve shape: increasing in X with a decreasing slope ΔEL/ΔX
    #     (the X grid is uneven, so slopes rather than second differences are tested).
    curve = np.asarray(arrays["el_curve_value"], dtype=float)
    curve_x = np.asarray(arrays["el_curve_x"], dtype=float)
    slopes = np.diff(curve) / np.diff(curve_x)
    _add(
        checks,
        "base_correlation_curve_shape",
        float(np.max(np.diff(slopes))),
        "0–X% expected-loss PV increasing in X with strictly decreasing slope ΔEL/ΔX",
        bool(np.all(np.diff(curve) > 0.0)) and bool(np.all(np.diff(slopes) < 0.0)),
    )

    # 14. Double-t limit.
    gap_bp = float(
        abs(
            np.asarray(arrays["double_t_spread"], dtype=float)[-1]
            - float(metrics["gaussian_mezz_spread"])
        )
        * 1e4
    )
    _add(
        checks,
        "double_t_gaussian_limit",
        gap_bp,
        "ν→∞ double-t spread within 0.5 bp of the Gaussian spread",
        gap_bp <= 0.5,
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
    cva_special = (
        (1.0 - recovery)
        * float(metrics["cva_no_default_value"])
        * float(np.sum(arrays["cva_default_prob"]))
    )
    cva_gap = abs(cva_special - float(metrics["cva_special_case"]))
    general_gap = abs(float(metrics["cva_general_equivalent"]) - cva_special)
    _add(
        checks,
        "netting_collateral_and_cva_special_case",
        max(collateral_gap, cva_gap, general_gap),
        "netting 15 <= gross 40 (Hull 24.7); Example 24.4 exposures 5/0/0/5; (1−R)f_nd Σq_i "
        "equals the stored CVA (1e-12) and the general CVA on a 2000-step grid (1e-5)",
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
    """Return the canonical gate record; this does not approve empirical performance."""
    try:
        evaluator = _EVALUATORS[volume]
    except KeyError as exc:
        raise ValueError("acceptance volume must lie in [18, 28]") from exc
    checks, negative_results = evaluator(metrics, arrays)
    return {
        "schema_version": 1,
        "scope": "integration_and_reproducibility",
        "model_performance_approved": False,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "negative_results": negative_results,
    }
