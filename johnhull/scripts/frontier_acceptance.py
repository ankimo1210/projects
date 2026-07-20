"""Canonical integration-gate checks for johnhull volumes 18--27."""

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
            "in_domain_greek_rmse",
            "ood_price_rmse",
            "ood_greek_rmse",
        )
    )
    _add(
        checks,
        "in_domain_ood_diagnostics",
        domain_diagnostics,
        "price and Greek RMSE finite in both domains",
        domain_diagnostics,
    )
    negative = [
        f"The polynomial surrogate Greek RMSE is {metrics['surrogate_greek_rmse']:.6g}; this is a reported negative result, not a Greek-accuracy approval.",
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
    )
    _add(
        checks,
        "event_non_event_split",
        f"{metrics['event_count']}/{metrics['non_event_count']}",
        "mask counts and two-way diagnostics agree",
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
    diagnostics = (
        metrics["hagan_static_arbitrage_pass"]
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
        "regime errors reported and static checks pass",
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
    _add(
        checks,
        "floor_payoff_decomposition",
        metrics["floor_decomposition_error"],
        "<= 1e-12",
        metrics["floor_decomposition_error"] <= 1e-12,
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
    hedge_ok = (
        arrays["hedge_risk_names"].tolist() == ["nominal duration", "CPI delta"]
        and np.all(arrays["unhedged_normalized_risk"] > 0.0)
        and np.allclose(arrays["hedged_normalized_risk"], 0.0)
    )
    _add(
        checks,
        "synthetic_hedge_decomposition",
        len(arrays["hedge_risk_names"]),
        "nominal-duration and CPI-delta residuals are reported separately",
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


def _lr_independence_np(exceedances: np.ndarray) -> float:
    """Christoffersen (1998) independence LR statistic recomputed in NumPy."""
    exc = np.asarray(exceedances, dtype=int)
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

    # 1. Kupiec size calibration recomputed from the committed rejection flags.
    reject_flags = np.asarray(arrays["kupiec_size_reject_flags"], dtype=float)
    n_replications = int(reject_flags.size)
    rejection_rate = float(reject_flags.mean())
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

    # 10. P&L-explain Taylor ordering and shrinkage.
    dgv_residual = abs(float(metrics["taylor_full_pnl"]) - float(metrics["taylor_dgv_total"]))
    delta_residual = abs(float(metrics["taylor_full_pnl"]) - float(metrics["taylor_delta_only"]))
    dgv_residual_half = abs(
        float(metrics["taylor_full_pnl_half"]) - float(metrics["taylor_dgv_total_half"])
    )
    delta_residual_half = abs(
        float(metrics["taylor_full_pnl_half"]) - float(metrics["taylor_delta_only_half"])
    )
    taylor_ordered = (
        dgv_residual < delta_residual
        and dgv_residual_half < dgv_residual
        and delta_residual_half < delta_residual
    )
    _add(
        checks,
        "pnl_explain_taylor_ordering",
        dgv_residual,
        "dgv residual < delta-only residual; both shrink when moves halve",
        taylor_ordered,
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
        raise ValueError("acceptance volume must lie in [18, 27]") from exc
    checks, negative_results = evaluator(metrics, arrays)
    return {
        "schema_version": 1,
        "scope": "integration_and_reproducibility",
        "model_performance_approved": False,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "negative_results": negative_results,
    }
