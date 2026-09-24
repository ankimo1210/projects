"""Tampering contract for the frontier acceptance gate.

The gate is only worth its PASS if it recomputes from the committed arrays
instead of trusting stored scalars. Each case below alters one committed
array or metric of a released volume and asserts that exactly the named
check flips to FAIL. A tamper that leaves the gate green is a check that is
reading its own answer back (the 2026-09-14 audit found that zeroing vol 28's
``cds_bootstrap_hazard`` or ``cds_survival`` and vol 27's ``gpd_losses`` all
kept 17/17 and 14/14 PASS).

"Exactly" allows the checks declared in ``DEPENDENT_FAILURES`` that read the
same input. Degenerate inputs (all zeros, a fit parameter at a pole) must
produce a failing record rather than an exception, so the gate stays
diagnosable.
"""

from __future__ import annotations

import copy
import json
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from johnhull.scripts.frontier_acceptance import evaluate_acceptance

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((ROOT / "johnhull/release_manifest.json").read_text(encoding="utf-8"))


@cache
def _load(volume: int) -> tuple[dict, dict]:
    item = next(entry for entry in MANIFEST["volumes"] if entry["number"] == volume)
    folder = ROOT / "johnhull/volumes" / item["slug"]
    json_name = next(ref for ref in item["references"] if ref.endswith(".json"))
    npz_name = next(ref for ref in item["references"] if ref.endswith(".npz"))
    metrics = json.loads((folder / json_name).read_text(encoding="utf-8"))["metrics"]
    with np.load(folder / npz_name, allow_pickle=False) as stored:
        arrays = {name: stored[name].copy() for name in stored.files}
    return metrics, arrays


def _failed(volume: int, metrics: dict, arrays: dict) -> set[str]:
    record = evaluate_acceptance(volume, metrics, arrays)
    return {check["name"] for check in record["checks"] if not check["passed"]}


def _scale_array(name: str, factor: float):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name] * factor

    return tamper


def _set_array_value(name: str, index, value: float):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = value

    return tamper


def _scale_metric(name: str, factor: float):
    def tamper(metrics, arrays):
        metrics[name] = metrics[name] * factor

    return tamper


def _flip_flag(name: str, index: int):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = 1.0 - arrays[name][index]

    return tamper


def _scale_array_value(name: str, index, factor: float):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = arrays[name][index] * factor

    return tamper


def _copy_array_value(source: str, source_index, name: str, index):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = arrays[source][source_index]

    return tamper


def _replace_array(name: str, source: str):
    def tamper(metrics, arrays):
        arrays[name] = arrays[source].copy()

    return tamper


def _set_metric(name: str, value):
    def tamper(metrics, arrays):
        metrics[name] = value

    return tamper


CASES = {
    18: [
        (
            "split_row_key_test",
            _copy_array_value("split_row_key_train", 0, "split_row_key_test", 0),
            "split_overlap_count",
        ),
        ("split_overlap_count", _set_metric("split_overlap_count", 1), "split_overlap_count"),
        (
            "test_price_abs_error",
            _scale_array("test_price_abs_error", 1.001),
            "price_mae_normalized",
        ),
        (
            "neural_price",
            _scale_array_value("neural_price", (10, 14), 1.01),
            "price_mae_normalized",
        ),
        ("test_delta_abs_error", _scale_array("test_delta_abs_error", 1.001), "delta_mae"),
        ("teacher_ci_upper", _set_array_value("teacher_ci_upper", (0, 1), -1.0), "mc_ci_coverage"),
        ("teacher_reference", _scale_array("teacher_reference", 1.5), "mc_ci_coverage"),
        # Scaling both standard-error rows cancels in the ratio; move the 40k row.
        (
            "teacher_se_4x_paths",
            _scale_array_value("teacher_se_4x_paths", (1, 0), 1.01),
            "mc_standard_error_scaling",
        ),
    ],
    19: [
        (
            "calibration_start_repricing_rmse",
            _scale_array("calibration_start_repricing_rmse", 1.001),
            "forward_repricing_rmse",
        ),
        ("calibration_truth", _scale_array("calibration_truth", 1.01), "forward_repricing_rmse"),
        (
            "constraint_hard_price",
            _scale_array_value("constraint_hard_price", (0, 4), 1.05),
            "hard_surface_report",
        ),
        (
            "constraint_raw_price",
            _replace_array("constraint_raw_price", "constraint_clean_teacher_price"),
            "raw_stress_detected",
        ),
        (
            "pareto_fit_parameters",
            _set_array_value("pareto_fit_parameters", slice(None), 0.05),
            "joint_variance_refits",
        ),
        (
            "pareto_predicted_variance",
            _scale_array_value("pareto_predicted_variance", 2, 1.5),
            "variance_pareto_improvement",
        ),
        ("pareto_losses", _scale_array("pareto_losses", 1.001), "pareto_evidence"),
        ("pareto_nondominated", _set_array_value("pareto_nondominated", 0, 0), "pareto_evidence"),
        (
            "direct_inverse_test_prediction",
            _scale_array("direct_inverse_test_prediction", 1.01),
            "direct_inverse_evidence",
        ),
    ],
    20: [
        (
            "walk_forward_prediction_ewma",
            _scale_array("walk_forward_prediction_ewma", 1.001),
            "block_bootstrap_intervals",
        ),
        (
            "walk_forward_qlike_challenger",
            _scale_array("walk_forward_qlike_challenger", 1.001),
            "block_bootstrap_intervals",
        ),
        (
            "walk_forward_h21_prediction_tcn",
            _scale_array("walk_forward_h21_prediction_tcn", 1.001),
            "horizon_regime_intervals",
        ),
        (
            "walk_forward_h5_qlike_log_har",
            _scale_array("walk_forward_h5_qlike_log_har", 1.001),
            "horizon_regime_intervals",
        ),
        (
            "walk_forward_h1_regime_code",
            _set_array_value("walk_forward_h1_regime_code", slice(None), 0),
            "horizon_regime_intervals",
        ),
        ("e2e_hedge_pnl", _scale_array("e2e_hedge_pnl", 1.001), "economic_comparison_controls"),
        (
            "e2e_hedge_turnover",
            _scale_array("e2e_hedge_turnover", 1.001),
            "economic_comparison_controls",
        ),
    ],
    21: [
        ("surrogate_ms", _scale_array("surrogate_ms", 1000.0), "surrogate_speedup"),
        ("nested_mc_ms", _scale_array("nested_mc_ms", 1.001), "surrogate_speedup"),
        ("spx_model_grid", _scale_array("spx_model_grid", 1.001), "joint_objective_components"),
        ("variance_rmse", _scale_array("variance_rmse", 1.001), "joint_objective_components"),
        ("surrogate_gamma", _scale_array("surrogate_gamma", 1.001), "in_domain_ood_diagnostics"),
        ("ood_error", _scale_array("ood_error", 1.001), "in_domain_ood_diagnostics"),
    ],
    22: [
        (
            "model_total_variance",
            _set_array_value("model_total_variance", 3, 0.0),
            "expiry_consistency",
        ),
        ("total_variance", _scale_array("total_variance", 1.001), "expiry_consistency"),
        (
            "teacher_standard_error",
            _scale_array("teacher_standard_error", 1.01),
            "event_teacher_uncertainty",
        ),
        ("price_mae", _scale_array("price_mae", 1.001), "time_of_day_diagnostics"),
        ("baseline_delta", _scale_array("baseline_delta", 1.001), "time_of_day_diagnostics"),
        ("event_price_rmse", _scale_array("event_price_rmse", 1.001), "event_non_event_split"),
        ("teacher_price", _scale_array("teacher_price", 1.001), "event_non_event_split"),
    ],
    26: [
        (
            "hw_model_discount_factor",
            _scale_array("hw_model_discount_factor", 1.001),
            "hull_white_initial_curve",
        ),
        (
            "seasonality_log_factor",
            _set_array_value("seasonality_log_factor", 0, 0.01),
            "annual_seasonality_normalization",
        ),
        ("zcis_repriced", _scale_array("zcis_repriced", 1.001), "zcis_quote_repricing"),
        ("jy_mc_forward_index", _scale_array("jy_mc_forward_index", 1.01), "jy_forward_measure_mc"),
        ("floor_mc", _scale_array("floor_mc", 1.05), "jgbi_floor_analytic_mc"),
        (
            "inflation_volatility",
            _set_array_value("inflation_volatility", slice(1, 3), [0.02, 0.01]),
            "floor_volatility_monotonicity",
        ),
        (
            "jgbi_unfloored_coupon",
            _scale_array("jgbi_unfloored_coupon", 1.001),
            "redemption_only_principal_floor",
        ),
        (
            "jgbi_coupon-floored",
            _set_array_value("jgbi_coupon", -1, 0.25),
            "redemption_only_principal_floor",
        ),
        (
            "jgbi_floored_principal-interim",
            _set_array_value("jgbi_floored_principal", 0, 100.0),
            "redemption_only_principal_floor",
        ),
        (
            "jgbi_unfloored_principal-interim",
            _set_array_value("jgbi_unfloored_principal", 0, 100.0),
            "redemption_only_principal_floor",
        ),
        ("yoy_jy_ratio", _scale_array("yoy_jy_ratio", 1.0001), "nominal_payment_forward_measure"),
        (
            "yoy_start_payment_adjustment",
            _scale_array("yoy_start_payment_adjustment", 0.0),
            "nominal_payment_forward_measure",
        ),
        (
            "yoy_log_covariance",
            _scale_array("yoy_log_covariance", 1.01),
            "nominal_payment_forward_measure",
        ),
        (
            "yoy_end_forward_cpi",
            _scale_array("yoy_end_forward_cpi", 1.001),
            "nominal_payment_forward_measure",
        ),
    ],
    23: [
        ("daily_rate", _scale_array("daily_rate", 1.001), "daily_compounding_handcheck"),
        (
            "discrete_accrual",
            _scale_array("discrete_accrual", 1.001),
            "daily_compounding_handcheck",
        ),
        (
            "convention_accumulation",
            _set_array_value("convention_accumulation", 0, 1.0),
            "daily_compounding_handcheck",
        ),
        ("continuous_accrual", _scale_array("continuous_accrual", 1.001), "continuous_limit"),
        (
            "bachelier_price",
            _scale_array("bachelier_price", 1.001),
            "bachelier_quadrature_handcheck",
        ),
        (
            "quadrature_price",
            _scale_array("quadrature_price", 1.001),
            "bachelier_quadrature_handcheck",
        ),
        (
            "bachelier_normal_vol",
            _scale_metric("bachelier_normal_vol", 1.01),
            "bachelier_quadrature_handcheck",
        ),
    ],
    24: [
        # The matched ledger nets to a zero venue leg and the underwater account
        # has zero fee/trader return and an exhausted insurance fund, so the
        # tampers below move the non-zero legs.
        (
            "funding_long_cashflow",
            _scale_array("funding_long_cashflow", 1.001),
            "funding_cap_interval",
        ),
        (
            "funding_settled_intervals",
            _set_array_value("funding_settled_intervals", -1, 9),
            "funding_cap_interval",
        ),
        (
            "liquidation_method_equity",
            _scale_array("liquidation_method_equity", 1.001),
            "liquidation_method_waterfalls",
        ),
        (
            "liquidation_method_socialized_loss",
            _scale_array("liquidation_method_socialized_loss", 1.001),
            "liquidation_method_waterfalls",
        ),
        (
            "liquidation_method_insurance_before",
            _scale_array("liquidation_method_insurance_before", 1.001),
            "insurance_identity",
        ),
        ("adl_notional", _scale_array("adl_notional", 1.001), "stress_waterfall"),
        ("rebalanced_value", _scale_array("rebalanced_value", 1.001), "amm_identity"),
        ("lvr", _scale_array("lvr", 1.001), "amm_identity"),
        ("fee_income", _scale_array("fee_income", 1.001), "amm_lvr_fee_variants"),
        ("fixed_fee_net_lvr", _scale_array("fixed_fee_net_lvr", 1.001), "amm_lvr_fee_variants"),
        (
            "dynamic_fee_compensation",
            _scale_metric("dynamic_fee_compensation", 1.001),
            "amm_lvr_fee_variants",
        ),
    ],
    25: [
        (
            "weather_premium",
            _set_array_value("weather_premium", slice(None), 1.0),
            "market_completeness",
        ),
        (
            "carbon_black76_price",
            _scale_array("carbon_black76_price", 1.001),
            "carbon_model_ladder",
        ),
        ("carbon_gbm_price", _scale_array("carbon_gbm_price", 1.1), "carbon_model_ladder"),
        (
            "carbon_black76_volatility",
            _scale_metric("carbon_black76_volatility", 1.01),
            "carbon_model_ladder",
        ),
        ("ppa_fixed", _scale_array("ppa_fixed", 1.001), "ppa_risk_decomposition"),
        (
            "hedge_ratio_residual",
            _scale_array("hedge_ratio_residual", 1.001),
            "ppa_risk_decomposition",
        ),
        (
            "ppa_merchant_cash_flow_samples",
            _scale_array("ppa_merchant_cash_flow_samples", 1.001),
            "ppa_risk_decomposition",
        ),
        (
            "ppa_hedged_cash_flow_samples",
            _scale_array("ppa_hedged_cash_flow_samples", 1.001),
            "ppa_cashflow_risk",
        ),
        ("cvar95", _scale_array("cvar95", 1.001), "ppa_cashflow_risk"),
        ("hedge_residual", _scale_array("hedge_residual", 1.001), "ppa_cashflow_risk"),
        (
            "ppa_correlation_merchant_mean",
            _scale_array_value("ppa_correlation_merchant_mean", 0, 1.001),
            "ppa_correlation_sensitivity",
        ),
        (
            "ppa_correlation_pap_fair_value",
            _scale_array_value("ppa_correlation_pap_fair_value", -1, 1.01),
            "ppa_correlation_sensitivity",
        ),
        (
            "ppa_correlation_pap_cvar95",
            _scale_array("ppa_correlation_pap_cvar95", 1.001),
            "ppa_correlation_sensitivity",
        ),
        (
            "ppa_generation_volatility",
            _scale_metric("ppa_generation_volatility", 2.0),
            "ppa_correlation_sensitivity",
        ),
    ],
    27: [
        (
            "kupiec_size_reject_flags",
            _flip_flag("kupiec_size_reject_flags", 0),
            "kupiec_size_flags_match_recomputation",
        ),
        ("garch_returns", _scale_array("garch_returns", 1.001), "fhs_coverage_improvement"),
        # FHS rescales z = r/sigma by sigma_t, so a uniform sigma scale cancels;
        # move a single day's sigma instead.
        (
            "conditional_sigma",
            _set_array_value("conditional_sigma", -1, 0.05),
            "fhs_coverage_improvement",
        ),
        ("hs_var_forecast", _scale_array("hs_var_forecast", 1.001), "fhs_coverage_improvement"),
        ("gpd_losses", _scale_array("gpd_losses", 1.01), "gpd_parameter_recovery"),
        # No exceedance or an invalid fit must fail with a record, not raise
        # (a zero-division in the EVT rebuild used to abort the whole gate).
        ("gpd_losses_zero", _scale_array("gpd_losses", 0.0), "gpd_parameter_recovery"),
        ("gpd_xi_hat_zero", _set_metric("gpd_xi_hat", 0.0), "gpd_parameter_recovery"),
        ("gpd_xi_hat_one", _set_metric("gpd_xi_hat", 1.0), "gpd_parameter_recovery"),
        ("gpd_beta_hat", _scale_metric("gpd_beta_hat", 1.02), "gpd_parameter_recovery"),
        ("evt_var", _scale_metric("evt_var", 1.001), "evt_var_es_identity"),
        ("evt_var_ladder", _scale_array("evt_var_ladder", 1.001), "evt_var_es_identity"),
        (
            "alloc_component_var",
            _scale_array("alloc_component_var", 1.001),
            "euler_additivity_normal",
        ),
        ("alloc_normal_var", _scale_metric("alloc_normal_var", 1.001), "euler_additivity_normal"),
        ("alloc_vols", _scale_array("alloc_vols", 1.001), "euler_additivity_normal"),
        ("book_delta", _scale_array("book_delta", 1.001), "cross_asset_factor_mapping"),
        (
            "position_full_pnl",
            _scale_array("position_full_pnl", 1.001),
            "cross_asset_factor_mapping",
        ),
        ("es_components", _scale_array("es_components", 1.001), "euler_es_additivity_sim"),
    ],
    28: [
        ("cds_survival", _scale_array("cds_survival", 0.999), "cds_par_spread_hull_pin"),
        ("cds_payoff_pv", _scale_array("cds_payoff_pv", 1.001), "cds_par_spread_hull_pin"),
        (
            "cds_bootstrap_hazard",
            _scale_array("cds_bootstrap_hazard", 1.01),
            "cds_bootstrap_round_trip",
        ),
        (
            "fixed_coupon_duration",
            _scale_metric("fixed_coupon_duration", 1.001),
            "fixed_coupon_price_identity",
        ),
        (
            "fixed_coupon_hazard",
            _scale_metric("fixed_coupon_hazard", 1.01),
            "fixed_coupon_price_identity",
        ),
        ("option_curve_hazard", _scale_array("option_curve_hazard", 1.01), "cds_option_parity"),
        ("payer_value", _scale_array("payer_value", 1.001), "cds_option_parity"),
        (
            "capital_structure_expected_loss",
            _scale_array("capital_structure_expected_loss", 1.001),
            "capital_structure_loss_conservation",
        ),
        (
            "portfolio_expected_loss",
            _scale_metric("portfolio_expected_loss", 1.001),
            "capital_structure_loss_conservation",
        ),
        (
            "kth_conditional_cumulative_prob",
            _scale_array("kth_conditional_cumulative_prob", 1.001),
            "kth_to_default_hull_pin_and_ordering",
        ),
        ("kth_rho", _scale_metric("kth_rho", 1.05), "kth_to_default_hull_pin_and_ordering"),
        (
            "base_correlation",
            _scale_array("base_correlation", 1.01),
            "base_correlation_curve_shape",
        ),
        ("el_curve_value", _scale_array("el_curve_value", 1.001), "base_correlation_curve_shape"),
        (
            "tranche_expected_loss",
            _scale_array("tranche_expected_loss", 1.001),
            "base_correlation_curve_shape",
        ),
        (
            "gaussian_mezz_spread",
            _scale_metric("gaussian_mezz_spread", 1.001),
            "double_t_gaussian_limit",
        ),
        (
            "cva_default_prob",
            _scale_array("cva_default_prob", 1.001),
            "netting_collateral_and_cva_special_case",
        ),
        (
            "cva_hazard",
            _scale_metric("cva_hazard", 1.01),
            "netting_collateral_and_cva_special_case",
        ),
    ],
}

# A tampered input can legitimately break more than one check when the checks
# share it (the CDS legs feed both the par spread and the MTM identity; the
# vol 24 funding and waterfall legs feed the cash-flow conservation roll-up).
DEPENDENT_FAILURES = {
    "variance_pareto_improvement": {"pareto_evidence"},
    "time_of_day_diagnostics": {"event_non_event_split"},
    "event_non_event_split": {"time_of_day_diagnostics"},
    "daily_compounding_handcheck": {"continuous_limit"},
    "funding_cap_interval": {"cashflow_conservation"},
    "liquidation_method_waterfalls": {"cashflow_conservation", "stress_waterfall"},
    "insurance_identity": {"solvency_identity", "stress_waterfall"},
    "amm_identity": {"amm_lvr_fee_variants"},
    "ppa_risk_decomposition": {"ppa_cashflow_risk", "ppa_correlation_sensitivity"},
    "ppa_cashflow_risk": {"ppa_risk_decomposition", "ppa_correlation_sensitivity"},
    "fhs_coverage_improvement": {"fhs_constant_vol_identity"},
    "gpd_parameter_recovery": {"evt_var_es_identity"},
    "euler_additivity_normal": {"marginal_fd_consistency", "desk_report_reproducible"},
    "cross_asset_factor_mapping": {"pnl_explain_taylor_ordering"},
    "euler_es_additivity_sim": {"desk_report_reproducible"},
    "cds_par_spread_hull_pin": {"cds_mtm_identity"},
    "base_correlation_curve_shape": {"implied_correlation_reprices_quotes"},
}

FLAT_CASES = [(volume, *case) for volume, cases in CASES.items() for case in cases]


@pytest.mark.parametrize("volume", sorted(CASES))
def test_committed_gate_passes(volume):
    metrics, arrays = _load(volume)
    assert _failed(volume, copy.deepcopy(metrics), dict(arrays)) == set()


# Inputs that used to abort evaluate_acceptance with an exception when zeroed
# (found by zeroing every numeric array and metric of every volume in turn).
DEGENERATE_ZEROS = [
    (23, "array", "day_count"),
    (23, "metric", "rfr_day_count_basis"),
    (27, "metric", "alpha"),
    (27, "metric", "fhs_window"),
    (27, "metric", "gpd_beta_true"),
    (27, "metric", "gpd_xi_hat"),
    (27, "array", "gpd_losses"),
    (27, "metric", "kupiec_size_observations"),
    (28, "array", "cds_market_tenor"),
    (28, "array", "factor_weight"),
    (28, "array", "kth_factor_weight"),
    (28, "array", "tranche_expected_principal"),
    (28, "array", "tranche_payment_time"),
    (28, "metric", "cds_bootstrap_freq"),
    (28, "metric", "fixed_coupon_freq"),
    (28, "metric", "fixed_coupon_maturity"),
    (28, "metric", "option_freq"),
    (28, "metric", "option_maturity"),
]


@pytest.mark.parametrize(
    ("volume", "kind", "name"),
    DEGENERATE_ZEROS,
    ids=[f"vol{volume}-{kind}-{name}" for volume, kind, name in DEGENERATE_ZEROS],
)
def test_degenerate_input_returns_a_failing_record(volume, kind, name):
    metrics, arrays = _load(volume)
    metrics, arrays = copy.deepcopy(metrics), dict(arrays)
    if kind == "array":
        arrays[name] = np.zeros_like(arrays[name])
    else:
        metrics[name] = 0
    with np.errstate(all="ignore"):
        record = evaluate_acceptance(volume, metrics, arrays)
    assert record["passed"] is False
    assert all(isinstance(check["passed"], bool) for check in record["checks"])


@pytest.mark.parametrize(
    ("volume", "label", "tamper", "check"),
    FLAT_CASES,
    ids=[f"vol{volume}-{label}" for volume, label, _, _ in FLAT_CASES],
)
def test_tamper_flips_exactly_the_recomputing_check(volume, label, tamper, check):
    metrics, arrays = _load(volume)
    metrics, arrays = copy.deepcopy(metrics), dict(arrays)
    tamper(metrics, arrays)
    failed = _failed(volume, metrics, arrays)
    assert check in failed, f"vol {volume} {label}: {check} still passes after tampering"
    assert failed <= {check, *DEPENDENT_FAILURES.get(check, set())}, (
        f"vol {volume} {label}: {failed}"
    )
