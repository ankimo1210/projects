"""API-to-artifact contract tests for beyond-Hull volumes 21--27."""

import numpy as np
import pytest
from hullkit import frontier_reference


@pytest.fixture(scope="module")
def references() -> dict[int, frontier_reference.FrontierReference]:
    return {volume: frontier_reference.build_frontier_reference(volume) for volume in range(21, 28)}


@pytest.mark.parametrize(
    ("volume", "required_arrays", "required_metrics"),
    [
        (
            21,
            {
                "spx_target",
                "vix_target",
                "vix_option_target",
                "variance_term_target",
                "teacher_price",
                "surrogate_price",
                "teacher_delta",
                "teacher_gamma",
                "teacher_standard_error",
                "ood_flag",
                "nested_mc_ms",
                "surrogate_ms",
                "spx_model_grid",
                "vix_model_grid",
                "vix_option_model_grid",
                "variance_term_model_grid",
            },
            {"surrogate_price_rmse", "surrogate_greek_rmse", "ood_count"},
        ),
        (
            22,
            {
                "variance_clock",
                "scheduled_variance",
                "teacher_price",
                "delta",
                "gamma",
                "total_variance",
                "forward_variance",
                "event_mask",
                "event_price_rmse",
                "event_greek_rmse",
            },
            {"calendar_violations", "adjacent_expiry_violations", "session_seconds"},
        ),
        (
            23,
            {
                "discrete_accrual",
                "forward_rate",
                "normal_iv",
                "shifted_sabr_iv",
                "free_boundary_sabr_iv",
                "bachelier_price",
                "quadrature_price",
                "shifted_teacher_price",
                "hagan_price",
                "teacher_price",
                "teacher_standard_error",
                "option_price_change",
                "sticky_hedge_error",
                "bartlett_hedge_error",
                "convention_rate",
                "coupon_cashflow",
                "curve_forward_rate",
                "basis_spread_bp",
                "policy_rate_path",
                "collateral_currency_pv",
            },
            {
                "sabr_teacher_nu",
                "hagan_wing_rmse_bp",
                "bartlett_hedge_rmse",
                "multi_curve_coupon_pv",
                "zero_rate_handcheck_error",
            },
        ),
        (
            24,
            {
                "contract_pnl_long",
                "contract_pnl_short",
                "funding_settled_intervals",
                "funding_long_cashflow",
                "funding_short_cashflow",
                "funding_conservation_error",
                "initial_margin_requirement",
                "maintenance_margin_requirement",
                "bankruptcy_price",
                "liquidation_price",
                "insurance_fund",
                "adl_notional",
                "socialized_loss",
                "uncovered_loss",
                "liquidation_conservation_error",
                "liquidation_method_conservation_error",
                "liquidation_method_adl_used",
                "liquidation_method_socialized_loss",
                "oracle_shocked_mark",
                "oracle_latent_index",
                "oracle_observed_dislocation",
                "oracle_latent_dislocation",
                "cpmm_swap_identity_error",
                "concentrated_lvr",
                "fixed_fee_gross_lvr",
                "dynamic_fee_gross_lvr",
                "amm_identity_error",
            },
            {"cashflow_conservation_error", "solvency_identity_error", "solvent"},
        ),
        (
            25,
            {
                "carbon_model_price",
                "carbon_gbm_price",
                "carbon_heston_price",
                "carbon_jump_price",
                "temperature_lag1_autocorrelation",
                "premium_principle_names",
                "weather_premium",
                "basis_rmse",
                "hedge_ratio",
                "hedge_ratio_residual",
                "cash_flow_at_risk",
                "cvar95",
                "ppa_fixed",
                "ppa_pay_as_produced",
                "ppa_floor_collar",
                "ppa_fair_value",
                "hedge_residual",
                "ppa_volume_risk",
                "ppa_shape_risk",
                "ppa_profile_risk",
            },
            {"weather_premium_principle", "price_generation_correlation"},
        ),
        (
            26,
            {
                "nominal_discount_factor",
                "real_discount_factor",
                "hw_market_discount_factor",
                "hw_model_discount_factor",
                "seasonality_log_factor",
                "cpi_trend",
                "cpi_seasonal",
                "zcis_quote",
                "zcis_repriced",
                "yoy_deterministic_ratio",
                "yoy_jy_ratio",
                "jy_forward_index",
                "jy_mc_forward_index",
                "jgbi_index_ratio",
                "jgbi_coupon",
                "jgbi_unfloored_principal",
                "jgbi_floored_principal",
                "floor_analytic",
                "floor_mc",
                "breakeven_inflation",
            },
            {
                "hw_curve_fit_max_error",
                "zcis_repricing_max_error",
                "floor_decomposition_error",
                "measure_treatment",
            },
        ),
        (
            27,
            {
                "iid_exceedances",
                "clustered_exceedances",
                "kupiec_size_reject_flags",
                "traffic_light_cumulative_prob",
                "traffic_light_multiplier",
                "garch_returns",
                "conditional_sigma",
                "hs_violations",
                "fhs_violations",
                "gpd_losses",
                "mean_excess_curve",
                "evt_var_ladder",
                "empirical_var_ladder",
                "alloc_marginal_var",
                "alloc_component_var",
                "alloc_incremental_var",
                "pnl_matrix",
                "es_components",
                "taylor_component_value",
                "limit_utilization_ratio",
            },
            {
                "alloc_normal_var",
                "euler_additivity_error",
                "evt_es_identity_error",
                "fhs_violation_rate",
                "hs_violation_rate",
                "gpd_xi_hat",
                "desk_report_var",
            },
        ),
    ],
)
def test_reference_contract_is_serialization_ready(
    references: dict[int, frontier_reference.FrontierReference],
    volume: int,
    required_arrays: set[str],
    required_metrics: set[str],
) -> None:
    reference = references[volume]
    assert reference.volume == volume
    assert reference.seed == 20260718 + volume
    assert required_arrays <= reference.arrays.keys()
    assert required_metrics <= reference.metrics.keys()
    for values in reference.arrays.values():
        assert isinstance(values, np.ndarray)
        assert values.size > 0
        assert values.dtype.kind != "O"
        if values.dtype.kind in "fiu":
            assert np.all(np.isfinite(values))


def test_volume21_covers_joint_targets_teacher_greeks_timing_and_ood(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[21]
    arrays = reference.arrays
    assert arrays["spx_target"].shape[0] == arrays["maturity"].size
    assert arrays["spx_target"].shape[1] == arrays["strike"].size
    assert arrays["vix_target"].shape == arrays["vix_option_target"].shape
    assert arrays["vix_target"].shape == arrays["variance_term_target"].shape
    assert np.all(arrays["vix_option_target"] > 0.0)
    assert arrays["teacher_price"].shape == arrays["surrogate_price"].shape
    assert arrays["teacher_delta"].shape == arrays["surrogate_delta"].shape
    assert arrays["teacher_gamma"].shape == arrays["surrogate_gamma"].shape
    assert arrays["teacher_standard_error"].shape == arrays["teacher_price"].shape
    assert arrays["spx_model_grid"].shape == (4, *arrays["spx_target"].shape)
    assert arrays["vix_model_grid"].shape == (4, arrays["maturity"].size)
    assert arrays["vix_option_model_grid"].shape == arrays["vix_model_grid"].shape
    assert arrays["variance_term_model_grid"].shape == arrays["vix_model_grid"].shape
    np.testing.assert_array_equal(arrays["spx_model_grid"][0], arrays["spx_pdv"])
    np.testing.assert_array_equal(arrays["vix_model_grid"][0], arrays["vix_pdv"])
    assert np.all(arrays["nested_mc_ms"] > 0.0)
    assert np.all(arrays["surrogate_ms"] > 0.0)
    assert int(arrays["ood_flag"].sum()) == reference.metrics["ood_count"] == 4


def test_volume22_clock_event_teacher_and_expiry_identities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[22]
    arrays = reference.arrays
    assert arrays["variance_clock"][0] == pytest.approx(0.0)
    assert arrays["variance_clock"][-1] == pytest.approx(1.0)
    assert np.all(np.diff(arrays["variance_clock"]) >= 0.0)
    assert arrays["scheduled_variance"].max() > 0.0
    assert arrays["event_mask"].any() and not arrays["event_mask"].all()
    assert arrays["teacher_price"].shape == arrays["delta"].shape == arrays["gamma"].shape
    assert np.all(np.diff(arrays["total_variance"]) >= 0.0)
    assert np.all(arrays["forward_variance"] >= 0.0)
    assert reference.metrics["calendar_violations"] == 0
    assert reference.metrics["adjacent_expiry_violations"] == 0
    assert (
        reference.metrics["event_count"] + reference.metrics["non_event_count"]
        == arrays["minute"].size
    )
    assert arrays["tod_names"].tolist() == ["open", "midday", "close"]
    assert arrays["price_mae"].shape == arrays["greek_mae"].shape == (3,)


def test_volume23_uses_nonzero_nu_teacher_and_independent_option_paths(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[23]
    arrays = reference.arrays
    assert reference.metrics["sabr_teacher_nu"] > 0.0
    assert np.all(arrays["teacher_standard_error"] > 0.0)
    assert reference.metrics["hagan_long_maturity_rmse_bp"] > 0.0
    assert reference.metrics["hagan_high_vol_rmse_bp"] > 0.0
    assert reference.metrics["hagan_wing_rmse_bp"] > 0.0
    assert not np.allclose(arrays["free_boundary_sabr_iv"], arrays["shifted_sabr_iv"])
    np.testing.assert_allclose(arrays["bachelier_price"], arrays["quadrature_price"], atol=1e-12)
    assert arrays["convention_names"].tolist() == [
        "in-arrears",
        "lookback 2bd",
        "observation shift 2bd",
        "lockout 2bd",
    ]
    assert np.ptp(arrays["convention_rate"]) > 0.0
    assert arrays["coupon_names"].tolist() == ["in-arrears", "in-advance"]
    assert arrays["coupon_cashflow"][0] != pytest.approx(arrays["coupon_cashflow"][1])
    assert arrays["curve_names"].tolist() == ["SOFR", "USD collateral OIS", "TONA"]
    assert np.all(arrays["basis_spread_bp"] > 0.0)
    assert arrays["policy_rate_path"].shape == (2, 5)
    assert np.ptp(arrays["policy_rate_path"], axis=1).min() > 0.0
    assert arrays["collateral_pv"][0] > arrays["collateral_pv"][-1]
    assert arrays["shifted_teacher_standard_error"].min() > 0.0
    assert arrays["hedge_teacher_standard_error"].min() > 0.0
    assert np.std(arrays["option_price_change"]) > 0.0
    assert np.std(arrays["sticky_hedge_error"]) > 0.0
    assert np.std(arrays["bartlett_hedge_error"]) > 0.0
    assert not np.allclose(
        arrays["option_price_change"],
        arrays["forward_change"] * 0.5,
    )
    assert reference.metrics["daily_compounding_handcheck_error"] < 1e-14
    assert reference.metrics["zero_rate_handcheck_error"] == 0.0
    assert reference.metrics["quadrature_handcheck_error"] < 1e-12
    assert reference.metrics["hagan_calendar_monotone_pass"] is True
    assert reference.metrics["hedge_teacher"].startswith("shifted-SABR")


def test_volume24_unifies_cashflow_solvency_and_amm_identities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[24]
    arrays = reference.arrays
    np.testing.assert_allclose(
        arrays["contract_pnl_long"] + arrays["contract_pnl_short"],
        0.0,
        atol=1e-15,
    )
    np.testing.assert_allclose(arrays["contract_pnl_long"][:, 1], 0.0, atol=1e-15)
    np.testing.assert_array_equal(arrays["funding_settled_intervals"], np.arange(8))
    assert arrays["funding_long_cashflow"][0] == pytest.approx(0.0)
    assert np.all(np.abs(arrays["funding_rate"]) <= arrays["funding_rate_cap"])
    np.testing.assert_allclose(
        arrays["funding_long_cashflow"]
        + arrays["funding_short_cashflow"]
        + arrays["funding_venue_cashflow"],
        0.0,
        atol=1e-14,
    )
    assert np.all(arrays["initial_margin_requirement"] >= arrays["maintenance_margin_requirement"])
    assert np.all(arrays["liquidation_price"] > arrays["bankruptcy_price"])
    assert np.max(np.abs(arrays["liquidation_conservation_error"])) < 1e-12
    assert np.max(np.abs(arrays["amm_identity_error"])) < 1e-12
    assert np.max(np.abs(arrays["cpmm_swap_identity_error"])) < 1e-12
    assert np.all(arrays["cpmm_invariant_gain"] >= -1e-12)
    np.testing.assert_allclose(
        arrays["fixed_fee_gross_lvr"],
        arrays["dynamic_fee_gross_lvr"],
    )
    assert arrays["dynamic_fee_income"][-1] >= arrays["fee_income"][-1]
    assert arrays["concentrated_lvr"][-1] > 0.0
    assert arrays["liquidation_method_names"].tolist() == ["forced_sale", "auction"]
    assert arrays["liquidation_execution_price"][0] < arrays["liquidation_execution_price"][1]
    assert (
        arrays["liquidation_method_socialized_loss"][0]
        > arrays["liquidation_method_socialized_loss"][1]
    )
    assert np.all(arrays["liquidation_method_adl_used"] > 0.0)
    assert np.max(np.abs(arrays["liquidation_method_conservation_error"])) < 1e-12
    assert arrays["oracle_stale"].sum() > 0
    assert arrays["oracle_dislocated"].sum() > 0
    assert not np.allclose(
        arrays["oracle_observed_dislocation"],
        arrays["oracle_latent_dislocation"],
    )
    assert not np.allclose(arrays["oracle_shocked_mark"], arrays["oracle_latent_index"])
    assert arrays["socialized_loss"][-1] > 0.0
    assert arrays["adl_notional"][-1] > 0.0
    assert arrays["uncovered_loss"][-1] == pytest.approx(0.0)
    assert reference.metrics["cashflow_conservation_error"] < 1e-12
    assert reference.metrics["solvency_identity_error"] < 1e-12
    assert reference.metrics["solvent"] is True
    assert reference.metrics["dynamic_fee_gross_lvr_reduction"] == pytest.approx(0.0)
    assert reference.metrics["dynamic_fee_compensation"] > 0.0
    assert reference.metrics["synthetic_cascade"] is True


def test_volume25_exposes_incomplete_market_and_hedge_sensitivities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[25]
    arrays = reference.arrays
    assert arrays["carbon_model_names"].tolist() == [
        "Black-76",
        "GBM MC",
        "Heston MC",
        "SV+jump MC",
    ]
    assert arrays["carbon_model_price"].shape == (4, arrays["strike"].size)
    assert arrays["carbon_heston_standard_error"].min() > 0.0
    assert not np.array_equal(arrays["carbon_heston_price"], arrays["carbon_jump_price"])
    assert arrays["risk_premium_names"].tolist() == ["return", "variance", "jump"]
    assert arrays["temperature_model_names"].tolist() == ["OU", "fractional OU"]
    assert np.ptp(arrays["temperature_lag1_autocorrelation"]) > 0.0
    assert arrays["premium_principle_names"].tolist() == [
        "expected_value",
        "standard_deviation",
        "exponential",
    ]
    assert arrays["weather_premium"][1] > arrays["weather_premium"][0]
    assert arrays["weather_premium"][2] > arrays["weather_premium"][0]
    assert arrays["basis_rmse"][0] == pytest.approx(0.0)
    assert arrays["basis_rmse"][-1] > arrays["basis_rmse"][1]
    assert np.ptp(arrays["hedge_ratio_residual"]) > 0.0
    assert np.all(arrays["cash_flow_at_risk"] >= 0.0)
    assert np.all(arrays["cvar95"] >= arrays["cash_flow_at_risk"])
    assert np.all(arrays["ppa_volume_risk"] > 0.0)
    assert np.all(arrays["ppa_shape_risk"] > 0.0)
    assert np.all(arrays["ppa_profile_risk"] > 0.0)
    assert arrays["carbon_jump_standard_error"].min() > 0.0
    assert arrays["risk_names"].tolist() == ["fixed", "pay-as-produced", "floor-collar"]
    assert (
        arrays["ppa_fixed"].shape
        == arrays["ppa_pay_as_produced"].shape
        == arrays["ppa_floor_collar"].shape
    )
    assert arrays["ppa_fair_value"].shape == arrays["cvar95"].shape == (3,)
    assert arrays["hedge_residual"].shape == arrays["cash_flow_at_risk"].shape == (3,)
    assert reference.metrics["market_completeness"] == "incomplete"
    assert -1.0 < reference.metrics["price_generation_correlation"] < 0.0


def test_volume26_exposes_measure_consistent_inflation_and_jgbi_identities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[26]
    arrays = reference.arrays
    np.testing.assert_allclose(
        arrays["hw_market_discount_factor"], arrays["hw_model_discount_factor"], atol=1e-14
    )
    assert abs(arrays["seasonality_log_factor"].sum()) < 1e-12
    np.testing.assert_allclose(arrays["zcis_quote"], arrays["zcis_repriced"], atol=1e-12)
    assert np.max(np.abs(arrays["jy_mc_forward_index"] - arrays["jy_forward_index"])) < (
        3.0 * np.max(arrays["jy_mc_standard_error"])
    )
    assert np.all(np.diff(arrays["floor_analytic"]) >= 0.0)
    assert reference.metrics["floor_mc_zscore_max"] < 3.0
    assert arrays["jgbi_floored_principal"][-1] > arrays["jgbi_unfloored_principal"][-1]
    assert arrays["jgbi_coupon"].shape == arrays["jgbi_index_ratio"].shape
    assert arrays["breakeven_inflation"][1] != pytest.approx(arrays["breakeven_inflation"][0])
    assert reference.metrics["principal_floor_redemption_only"] is True
    assert reference.metrics["measure_treatment"] == "nominal_payment_forward"


def test_volume27_exposes_recomputable_risk_desk_identities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[27]
    arrays = reference.arrays
    metrics = reference.metrics
    # Analytic Euler additivity: component VaR sums to the normal VaR.
    np.testing.assert_allclose(
        arrays["alloc_component_var"].sum(), metrics["alloc_normal_var"], atol=1e-12
    )
    # Closed-form EVT ES identity.
    es_check = (
        metrics["evt_var"]
        + metrics["gpd_beta_hat"]
        - metrics["gpd_xi_hat"] * metrics["evt_threshold"]
    ) / (1.0 - metrics["gpd_xi_hat"])
    assert abs(metrics["evt_es"] - es_check) <= 1e-12
    # Simulation Euler ES additivity from the committed P&L matrix.
    total = arrays["pnl_matrix"].sum(axis=1)
    n = total.size
    k = max(1, int(np.ceil(0.01 * n - 1e-9)))
    tail = np.argsort(total, kind="stable")[:k]
    es_total = float((-total[tail]).mean())
    np.testing.assert_allclose(arrays["es_components"].sum(), es_total, atol=1e-12)
    # FHS coverage beats plain HS on the GARCH path.
    assert abs(metrics["fhs_violation_rate"] - 0.01) < abs(metrics["hs_violation_rate"] - 0.01)
    # Christoffersen independence detects the clustered series.
    assert metrics["christoffersen_ind_pvalue_clustered"] < 0.05
    assert metrics["christoffersen_ind_lr_clustered"] > metrics["christoffersen_ind_lr_iid"]
    # GPD parameter recovery within the acceptance tolerances.
    assert abs(metrics["gpd_xi_hat"] - metrics["gpd_xi_true"]) <= 0.1
    assert abs(metrics["gpd_beta_hat"] / metrics["gpd_beta_true"] - 1.0) <= 0.15
    # Taylor P&L-explain ordering.
    dgv_residual = abs(metrics["taylor_full_pnl"] - metrics["taylor_dgv_total"])
    delta_residual = abs(metrics["taylor_full_pnl"] - metrics["taylor_delta_only"])
    assert dgv_residual < delta_residual
    assert arrays["asset_names"].tolist() == ["equity", "rates", "credit", "fx", "commodity"]


def test_dispatcher_rejects_non_frontier_volume_and_accepts_explicit_seed() -> None:
    with pytest.raises(ValueError, match=r"\[21, 27\]"):
        frontier_reference.build_frontier_reference(20)
    assert frontier_reference.build_frontier_reference(24, seed=7).seed == 7


@pytest.mark.parametrize("volume", range(21, 28))
def test_fixed_seed_reproduces_all_non_timing_values(
    references: dict[int, frontier_reference.FrontierReference],
    volume: int,
) -> None:
    original = references[volume]
    repeated = frontier_reference.build_frontier_reference(volume, seed=original.seed)
    excluded_arrays = {"nested_mc_ms", "surrogate_ms"}
    for name in original.arrays.keys() - excluded_arrays:
        np.testing.assert_array_equal(original.arrays[name], repeated.arrays[name])
    excluded_metrics = {"surrogate_speedup_1024"}
    for name in original.metrics.keys() - excluded_metrics:
        assert original.metrics[name] == repeated.metrics[name]
