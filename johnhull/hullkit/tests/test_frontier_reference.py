"""API-to-artifact contract tests for beyond-Hull volumes 21--28."""

import numpy as np
import pytest
from hullkit import frontier_reference, var_backtest


@pytest.fixture(scope="module")
def references() -> dict[int, frontier_reference.FrontierReference]:
    return {volume: frontier_reference.build_frontier_reference(volume) for volume in range(21, 29)}


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
            {
                "surrogate_price_rmse",
                "surrogate_delta_rmse",
                "surrogate_gamma_rmse",
                "surrogate_bound_violations",
                "surrogate_spot_monotonicity_violations",
                "ood_count",
            },
        ),
        (
            22,
            {
                "variance_clock",
                "scheduled_variance",
                "event_jump_variance",
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
        (
            28,
            {
                "bond_bootstrap_hazard",
                "hull_bond_bootstrap_hazard",
                "cds_payment_pv",
                "cds_accrual_pv",
                "cds_payoff_pv",
                "cds_mtm_seller",
                "tranche_expected_principal",
                "tranche_spread_vs_rho",
                "kth_spread",
                "kth_conditional_cumulative_prob",
                "compound_correlation",
                "base_correlation",
                "el_curve_value",
                "double_t_spread",
                "transition_matrix",
                "threshold_bbb",
                "credit_loss_by_case",
                "collateral_case_exposure",
                "cva_default_prob",
            },
            {
                "cds_par_spread_bp",
                "cds_mtm_seller_150bp",
                "fixed_coupon_price",
                "cdo_mezz_spread_bp",
                "kth3_spread_bp",
                "base_correlation_max_reprice_error",
                "double_t_limit_gap_bp",
                "heterogeneous_binomial_gap",
                "cva_special_case",
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


def test_volume21_reports_delta_and_gamma_separately_with_surrogate_hard_checks(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """Delta and gamma errors live on different scales, so one pooled RMSE hides delta.

    The nested teacher is piecewise linear in the index scale, so its bump gamma
    is ~0 while the quadratic surrogate has a constant gamma; a pooled RMSE was
    therefore a gamma-only number.  The surrogate also gets the hard checks that
    the teacher passes by construction: Black futures-option bounds and
    monotonicity in the index scale.
    """
    reference = references[21]
    arrays = reference.arrays
    metrics = reference.metrics
    for pooled in ("surrogate_greek_rmse", "in_domain_greek_rmse", "ood_greek_rmse"):
        assert pooled not in metrics
    in_domain = ~arrays["ood_flag"]
    for greek in ("delta", "gamma"):
        error = arrays[f"teacher_{greek}"] - arrays[f"surrogate_{greek}"]
        assert metrics[f"surrogate_{greek}_rmse"] == pytest.approx(
            float(np.sqrt(np.mean(error**2))), rel=1e-12
        )
        assert metrics[f"in_domain_{greek}_rmse"] == pytest.approx(
            float(np.sqrt(np.mean(error[in_domain] ** 2))), rel=1e-12
        )
        assert metrics[f"ood_{greek}_rmse"] == pytest.approx(
            float(np.sqrt(np.mean(error[~in_domain] ** 2))), rel=1e-12
        )
    assert metrics["surrogate_delta_rmse"] != pytest.approx(metrics["surrogate_gamma_rmse"])

    discount = metrics["teacher_discount_factor"]
    strike = 20.0 * arrays["surrogate_features"][:, 2]
    lower = discount * np.maximum(arrays["teacher_future"] - strike, 0.0)
    upper = discount * arrays["teacher_future"]
    np.testing.assert_allclose(arrays["price_lower_bound"], lower, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(arrays["price_upper_bound"], upper, rtol=0.0, atol=1e-12)

    def bound_violations(price: np.ndarray) -> int:
        return int(np.sum((price < lower - 1e-10) | (price > upper + 1e-10)))

    assert metrics["teacher_bound_violations"] == bound_violations(arrays["teacher_price"]) == 0
    assert metrics["surrogate_bound_violations"] == bound_violations(arrays["surrogate_price"])
    assert metrics["surrogate_bound_violations"] > 0

    scale_grid = arrays["monotonicity_scale"]
    assert np.all(np.diff(scale_grid) > 0.0)
    teacher_curves = arrays["teacher_scale_price"]
    surrogate_curves = arrays["surrogate_scale_price"]
    assert teacher_curves.shape == surrogate_curves.shape == (int(in_domain.sum()), scale_grid.size)
    assert metrics["teacher_spot_monotonicity_violations"] == int(
        np.sum(np.diff(teacher_curves, axis=1) < -1e-10)
    )
    assert metrics["teacher_spot_monotonicity_violations"] == 0
    assert metrics["surrogate_spot_monotonicity_violations"] == int(
        np.sum(np.diff(surrogate_curves, axis=1) < -1e-10)
    )


def test_volume22_clock_event_teacher_and_expiry_identities(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[22]
    arrays = reference.arrays
    assert arrays["variance_clock"][0] == pytest.approx(0.0)
    assert arrays["variance_clock"][-1] == pytest.approx(1.0)
    assert np.all(np.diff(arrays["variance_clock"]) >= 0.0)
    assert arrays["scheduled_variance"].max() > 0.0
    # The injected jump variance equals the scheduled event variance row by row.
    np.testing.assert_allclose(
        arrays["event_jump_variance"], arrays["scheduled_variance"], rtol=1e-12, atol=0.0
    )
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
    # The Hagan grid is a full alpha x maturity x strike cube, so the long-maturity
    # and high-vol regions select different cells instead of the same zipped rows.
    grid_shape = (
        arrays["teacher_alpha"].size,
        arrays["teacher_maturity"].size,
        arrays["strike"].size,
    )
    assert grid_shape == (3, 3, 9)
    assert arrays["hagan_price"].shape == arrays["teacher_price"].shape == grid_shape
    assert arrays["teacher_standard_error"].shape == grid_shape
    assert reference.metrics["hagan_long_maturity_rmse_bp"] != pytest.approx(
        reference.metrics["hagan_high_vol_rmse_bp"], rel=1e-6
    )
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


def test_volume26_hedge_is_revalued_and_floor_identity_is_independent(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """The hedge residuals come from bump revaluation, not literal [1, 1] / [0, 0] arrays.

    A 5y real zero linker plus its JY deflation floor is hedged with a 5y nominal
    zero bond and a 5y receive-inflation ZCIS on nominal PV01 and CPI delta.  The
    floor identity is checked against the cash-flow schedule rather than against
    the same ``raw + floor`` expression that built the adjusted price.
    """
    reference = references[26]
    arrays = reference.arrays
    metrics = reference.metrics
    assert "unhedged_normalized_risk" not in arrays
    assert "hedged_normalized_risk" not in arrays
    assert arrays["hedge_risk_names"].tolist() == ["nominal duration", "CPI delta"]
    unhedged = arrays["unhedged_risk"]
    instrument = arrays["hedge_instrument_risk"]
    notional = arrays["hedge_notional"]
    assert instrument.shape == (2, 2) and notional.shape == (2,)
    assert np.all(np.abs(unhedged) > 0.0)
    scale = np.abs(unhedged)
    linear_residual = unhedged + instrument @ notional
    assert np.all(np.abs(linear_residual) <= 1e-9 * scale)
    np.testing.assert_allclose(
        arrays["hedged_risk"], linear_residual, rtol=0.0, atol=1e-9 * scale.max()
    )
    # Real-rate PV01 is not a hedge target; it vanishes because every instrument
    # depends on the 5y nominal discount factor and CPI forward only.
    assert abs(metrics["unhedged_real_pv01"]) > 0.0
    assert abs(metrics["hedged_real_pv01"]) <= 1e-4 * abs(metrics["unhedged_real_pv01"])
    assert arrays["hedge_scenario_names"].size == 3
    assert np.all(np.abs(arrays["hedged_scenario_pnl"]) < np.abs(arrays["unhedged_scenario_pnl"]))
    assert np.any(np.abs(arrays["hedged_scenario_pnl"]) > 0.0)

    face = metrics["jgbi_face_value"]
    final_ratio = arrays["jgbi_index_ratio"][-1]
    assert final_ratio < 1.0
    expected_floored = arrays["jgbi_unfloored_principal"][-1] + face * max(1.0 - final_ratio, 0.0)
    assert metrics["floor_decomposition_error"] == abs(
        arrays["jgbi_floored_principal"][-1] - expected_floored
    )
    assert metrics["floor_decomposition_error"] <= 1e-12


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
    with pytest.raises(ValueError, match=r"\[21, 28\]"):
        frontier_reference.build_frontier_reference(20)
    assert frontier_reference.build_frontier_reference(24, seed=7).seed == 7


@pytest.mark.parametrize("volume", range(21, 29))
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


# --- vol 27 acceptance gate independence -------------------------------


def _frontier_acceptance():
    """Import the acceptance script (it lives outside the installed packages)."""
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import frontier_acceptance

    return frontier_acceptance


def _volume27_checks(metrics: dict, arrays: dict) -> dict[str, dict]:
    checks, _ = _frontier_acceptance()._volume27(metrics, arrays)
    return {check["name"]: check for check in checks}


def test_volume27_christoffersen_gate_ignores_the_stored_pvalue(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """Tampering with the JSON p-value must not be able to flip the gate to PASS."""
    reference = references[27]
    arrays = dict(reference.arrays)
    honest = _volume27_checks(dict(reference.metrics), arrays)
    assert honest["christoffersen_detects_clustering"]["passed"] is True
    assert honest["christoffersen_pvalue_matches_recomputation"]["passed"] is True

    tampered_metrics = dict(reference.metrics)
    tampered_metrics["christoffersen_ind_pvalue_clustered"] = 0.0
    tampered = _volume27_checks(tampered_metrics, arrays)

    # The detection gate is decided by the arrays, so the tamper cannot reach it ...
    assert tampered["christoffersen_detects_clustering"]["passed"] is True
    assert tampered["christoffersen_detects_clustering"]["observed"] == pytest.approx(
        honest["christoffersen_detects_clustering"]["observed"]
    )
    # ... and the tampered metric is caught by the consistency check instead.
    assert tampered["christoffersen_pvalue_matches_recomputation"]["passed"] is False


def test_volume27_christoffersen_gate_fails_when_clustering_is_absent(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """With an iid series in place of the clustered one the gate must FAIL."""
    reference = references[27]
    arrays = dict(reference.arrays)
    arrays["clustered_exceedances"] = arrays["iid_exceedances"]
    metrics = dict(reference.metrics)
    acceptance = _frontier_acceptance()
    lr = acceptance._lr_independence_np(arrays["clustered_exceedances"])
    metrics["christoffersen_ind_pvalue_clustered"] = acceptance._chi2_sf_df1(lr)

    checks = _volume27_checks(metrics, arrays)
    assert checks["christoffersen_detects_clustering"]["passed"] is False


def test_volume27_christoffersen_pvalue_matches_scipy(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """The scipy-free erfc recomputation must agree with chi2.sf(LR, df=1)."""
    from scipy.stats import chi2

    acceptance = _frontier_acceptance()
    arrays = references[27].arrays
    for name in ("iid_exceedances", "clustered_exceedances"):
        lr = acceptance._lr_independence_np(arrays[name])
        assert acceptance._chi2_sf_df1(lr) == pytest.approx(float(chi2.sf(lr, df=1)), abs=1e-12)


# --- vol 27 cross-asset capstone ---------------------------------------


def test_volume27_capstone_maps_equity_and_rate_positions(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """The capstone book must span equities and rates through explicit factors."""
    arrays = references[27].arrays
    positions = arrays["position_names"].tolist()
    factors = arrays["factor_names"].tolist()
    assert positions == ["index call", "single-name put", "receive-fixed IRS"]
    assert factors == ["index_spot", "single_name_spot", "parallel_zero_rate"]

    shape = (len(positions), len(factors))
    for name in ("position_factor_delta", "position_factor_gamma", "position_factor_vega"):
        assert arrays[name].shape == shape

    rate_column = factors.index("parallel_zero_rate")
    swap_row = positions.index("receive-fixed IRS")
    assert arrays["position_factor_delta"][swap_row, rate_column] != 0.0
    # A swap revalued off a deterministic curve carries no vega.
    assert np.all(arrays["position_factor_vega"][:, rate_column] == 0.0)
    assert arrays["position_factor_vega"][swap_row, :].tolist() == [0.0, 0.0, 0.0]


def test_volume27_swap_sensitivities_match_an_independent_bump(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """Re-derive the IRS rate delta/gamma from scratch with the same curve bump."""
    from hullkit import swaps

    reference = references[27]
    metrics = reference.metrics
    arrays = reference.arrays

    notional = metrics["swap_notional"]
    fixed_rate = metrics["swap_fixed_rate"]
    bump = metrics["swap_rate_bump"]
    pay_times = np.asarray([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    curve_times = np.asarray([0.25, 0.5, 1.0, 2.0, 3.0, 5.0])
    curve_zeros = np.asarray([0.018, 0.019, 0.021, 0.023, 0.024, 0.026])

    def value(shift: float) -> float:
        return float(
            swaps.irs_value_fras(
                notional, fixed_rate, pay_times, (curve_times, curve_zeros + shift)
            )
        )

    base, up, down = value(0.0), value(bump), value(-bump)
    expected_delta = (up - down) / (2.0 * bump)
    expected_gamma = (up - 2.0 * base + down) / bump**2

    assert metrics["swap_base_value"] == pytest.approx(base, rel=1e-12)
    assert metrics["swap_rate_delta"] == pytest.approx(expected_delta, rel=1e-12)
    assert metrics["swap_rate_gamma"] == pytest.approx(expected_gamma, rel=1e-9)

    factors = arrays["factor_names"].tolist()
    swap_row = arrays["position_names"].tolist().index("receive-fixed IRS")
    rate_column = factors.index("parallel_zero_rate")
    assert arrays["position_factor_delta"][swap_row, rate_column] == pytest.approx(
        expected_delta, rel=1e-12
    )


def test_volume27_full_revaluation_sums_across_positions(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[27]
    arrays = reference.arrays
    metrics = reference.metrics
    np.testing.assert_allclose(
        arrays["position_full_pnl"].sum(), metrics["taylor_full_pnl"], atol=1e-9
    )
    np.testing.assert_allclose(
        arrays["position_full_pnl_half"].sum(), metrics["taylor_full_pnl_half"], atol=1e-9
    )
    np.testing.assert_allclose(
        arrays["position_shocked_value"] - arrays["position_base_value"],
        arrays["position_full_pnl"],
        atol=1e-9,
    )


def test_volume27_taylor_residual_shrinks_faster_than_delta_only(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """dgv beats delta-only, and halving the move shrinks both residuals."""
    metrics = references[27].metrics
    assert metrics["taylor_dgv_residual"] < metrics["taylor_delta_residual"]
    assert metrics["taylor_dgv_residual_half"] < metrics["taylor_dgv_residual"]
    assert metrics["taylor_delta_residual_half"] < metrics["taylor_delta_residual"]


def test_volume27_reference_is_deterministic() -> None:
    """The capstone must regenerate identically for the same seed."""
    first = frontier_reference.volume27_reference()
    second = frontier_reference.volume27_reference()
    assert first.metrics == second.metrics
    assert set(first.arrays) == set(second.arrays)
    for name, values in first.arrays.items():
        np.testing.assert_array_equal(values, second.arrays[name])


def test_volume27_diversifying_position_does_not_consume_limit(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """A risk-reducing sleeve must show negative component VaR and negative utilization.

    Component VaR carries a sign: it is the position's Euler contribution to
    total VaR, so a hedge that lowers portfolio risk contributes a negative
    amount and the components still sum to the total. Feeding the *absolute*
    component into limit utilization erases that sign, and a position that
    reduces desk risk would report the same limit usage as one that adds the
    same amount -- a diversifier could then breach its limit.
    """
    arrays = references[27].arrays
    component_var = arrays["alloc_component_var"]
    limit_measure = arrays["limit_measure"]

    assert np.any(component_var < 0.0), (
        "the capstone book must contain a genuine diversifier, otherwise the "
        "signed-limit convention is never exercised"
    )
    np.testing.assert_allclose(limit_measure, component_var, atol=0.0, rtol=0.0)

    hedge = int(np.argmin(component_var))
    assert arrays["limit_utilization_ratio"][hedge] < 0.0
    assert limit_measure[hedge] <= arrays["limit_value"][hedge]

    # The Euler identity must survive the sign convention.
    assert float(component_var.sum()) == pytest.approx(
        references[27].metrics["alloc_normal_var"], abs=1e-12
    )


def test_volume27_kupiec_size_study_is_recomputable_from_committed_counts(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    """The size study must commit its inputs, not just its verdicts.

    The gate's rule is that acceptance is recomputed from committed arrays
    rather than trusted as a stored flag. Committing only the per-replication
    reject flags broke that rule structurally: the flags are the *output* of
    `kupiec_pof`, so nothing downstream could check the test was applied
    correctly. Committing each replication's exceedance count makes the whole
    study reproducible.
    """
    arrays = references[27].arrays
    counts = arrays["kupiec_size_exceedance_counts"]
    flags = arrays["kupiec_size_reject_flags"]
    observations = int(references[27].metrics["kupiec_size_observations"])

    assert counts.shape == flags.shape
    assert np.all(counts >= 0.0) and np.all(counts <= observations)

    alpha = float(references[27].metrics["alpha"])
    recomputed = np.array(
        [
            1.0 if var_backtest.kupiec_pof(int(count), observations, alpha=alpha)[1] < 0.05 else 0.0
            for count in counts
        ]
    )
    np.testing.assert_array_equal(recomputed, flags)


# --- vol 28 credit desk -------------------------------------------------


def test_volume28_reproduces_hull_pins(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[28]
    m, a = reference.metrics, reference.arrays
    assert m["cds_par_spread_bp"] == pytest.approx(123.0, abs=0.5)
    assert m["cds_mtm_seller_150bp"] == pytest.approx(0.0111, abs=1e-4)
    assert m["fixed_coupon_price"] == pytest.approx(100.27, abs=0.01)
    assert m["cdo_mezz_spread_bp"] == pytest.approx(348.0, abs=1.0)
    assert m["kth3_spread_bp"] == pytest.approx(153.0, abs=1.0)
    np.testing.assert_allclose(
        a["bond_bootstrap_hazard"], a["hull_bond_bootstrap_hazard"], atol=2e-4
    )
    np.testing.assert_allclose(a["compound_correlation"], a["hull_compound_correlation"], atol=0.01)
    np.testing.assert_allclose(a["base_correlation"], a["hull_base_correlation"], atol=0.01)
    np.testing.assert_allclose(
        a["collateral_case_exposure"], a["hull_collateral_case_exposure"], atol=1e-12
    )
    assert m["base_correlation_max_reprice_error"] < 1e-6
    assert m["double_t_limit_gap_bp"] < 0.5
    assert m["heterogeneous_binomial_gap"] < 1e-12


def test_volume28_identities_are_recomputable(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[28]
    m, a = reference.metrics, reference.arrays
    spread = a["cds_payoff_pv"].sum() / (a["cds_payment_pv"].sum() + a["cds_accrual_pv"].sum())
    assert spread * 1e4 == pytest.approx(m["cds_par_spread_bp"], abs=1e-9)
    weights = a["factor_weight"]
    assert weights @ a["tranche_protection_by_factor"] == pytest.approx(
        m["cdo_mezz_protection"], abs=1e-12
    )
    widths = a["capital_structure_detach"] - a["capital_structure_attach"]
    assert widths @ a["capital_structure_expected_loss"] == pytest.approx(
        m["portfolio_expected_loss"], abs=1e-10
    )
    assert np.all(np.diff(a["kth_spread"]) < 0.0)
    slopes = np.diff(a["el_curve_value"]) / np.diff(a["el_curve_x"])
    assert np.all(np.diff(a["el_curve_value"]) > 0.0) and np.all(np.diff(slopes) < 0.0)
    assert m["netting_exposure"] == pytest.approx(15.0)
    assert m["gross_exposure"] == pytest.approx(40.0)
    assert m["credit_var_correlated"] > m["credit_var_independent"]


def test_volume28_reference_is_deterministic() -> None:
    first = frontier_reference.volume28_reference()
    second = frontier_reference.volume28_reference()
    for name in first.arrays:
        np.testing.assert_array_equal(first.arrays[name], second.arrays[name])
    assert first.metrics == second.metrics


# --- vol 28 acceptance gate independence -------------------------------


def _volume28_checks(metrics: dict, arrays: dict) -> dict[str, dict]:
    checks, _ = _frontier_acceptance()._volume28(metrics, arrays)
    return {check["name"]: check for check in checks}


def test_volume28_acceptance_passes_and_recomputes_from_arrays(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[28]
    arrays = {name: np.asarray(value) for name, value in reference.arrays.items()}
    checks = _volume28_checks(dict(reference.metrics), arrays)
    assert len(checks) == 17
    assert all(check["passed"] for check in checks.values()), [
        name for name, check in checks.items() if not check["passed"]
    ]
    # tampering with the stored CDO metric is caught because A, B, C are re-integrated
    tampered = dict(reference.metrics)
    tampered["cdo_mezz_spread_bp"] = 300.0
    assert not _volume28_checks(tampered, arrays)["cdo_mezz_spread_hull_pin"]["passed"]
    # tampering with the committed implied correlations is caught by independent repricing
    broken = dict(arrays)
    broken["compound_correlation"] = arrays["compound_correlation"] + 0.05
    assert not _volume28_checks(dict(reference.metrics), broken)[
        "implied_correlation_reprices_quotes"
    ]["passed"]
