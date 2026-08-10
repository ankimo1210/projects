import numpy as np
import pytest
import quant_textbook.constrained_curves as constrained_curves
from quant_textbook import (
    CouponBondUniverse,
    bond_cashflow_matrix,
    fit_constrained_bond_discount_curve,
    fit_constrained_discount_curve,
    jgb_like_zero_curve,
    leave_one_bond_out_constrained_curve,
    leave_one_bond_out_constrained_curve_rmse,
    make_synthetic_jgb_universe,
    predict_prices_from_discounts,
    second_difference_matrix,
)


def test_second_difference_operator_and_price_matrix_have_explicit_shapes() -> None:
    operator = second_difference_matrix(5)
    np.testing.assert_allclose(
        operator,
        [
            [1.0, -2.0, 1.0, 0.0, 0.0],
            [0.0, 1.0, -2.0, 1.0, 0.0],
            [0.0, 0.0, 1.0, -2.0, 1.0],
        ],
    )
    cashflows = 100.0 * np.eye(5)
    discounts = np.linspace(0.99, 0.9, 5)
    np.testing.assert_allclose(
        predict_prices_from_discounts(cashflows, discounts),
        100.0 * discounts,
    )

    irregular_nodes = np.array([1.0, 2.0, 10.0, 20.0])
    time_linear_discounts = 1.0 - 0.01 * irregular_nodes
    np.testing.assert_allclose(
        second_difference_matrix(irregular_nodes) @ time_linear_discounts,
        0.0,
        atol=1e-16,
    )


def test_coupon_bond_adapter_preserves_bond_order_and_all_contractual_cashflows() -> None:
    universe = make_synthetic_jgb_universe(seed=31)
    data = bond_cashflow_matrix(universe)
    expected_discounts = np.exp(-jgb_like_zero_curve(data.node_times) * data.node_times)

    assert data.cashflow_matrix.shape == (len(universe.bonds), data.node_times.size)
    assert data.bond_ids == tuple(universe.bonds["bond_id"].astype(str))
    assert np.all(np.diff(data.node_times) > 0.0)
    np.testing.assert_allclose(
        data.cashflow_matrix @ expected_discounts,
        data.dirty_prices,
        atol=2e-12,
    )
    np.testing.assert_allclose(data.cashflows, data.cashflow_matrix)
    assert not data.cashflow_matrix.flags.writeable


def test_exact_zero_coupon_prices_recover_node_discounts_and_qp_diagnostics() -> None:
    nodes = np.arange(1.0, 5.0)
    cashflows = 100.0 * np.eye(4)
    expected = np.array([0.99, 0.96, 0.92, 0.87])
    fit = fit_constrained_discount_curve(
        cashflows,
        cashflows @ expected,
        nodes,
        smoothness=0.0,
        monotone=True,
        compute_loo=False,
        compare_solver=True,
    )

    np.testing.assert_allclose(fit.discount_factors, expected, atol=1e-12)
    np.testing.assert_allclose(fit.fitted_prices, fit.observed_prices, atol=1e-11)
    np.testing.assert_allclose(fit.predict_prices(cashflows), fit.fitted_prices)
    assert fit.problem.n_variables == nodes.size
    assert fit.qp_solution.success
    assert fit.diagnostics.accepted
    assert fit.diagnostics.solver_comparison_passed
    assert fit.diagnostics.solver_prediction_disagreement == pytest.approx(0.0)
    assert fit.diagnostics.maximum_discount_floor_violation == 0.0
    assert fit.diagnostics.maximum_monotonicity_violation == 0.0
    assert fit.diagnostics.hard_constraints_passed
    assert fit.metadata.first_node_upper_bound == 1.0
    assert "D(0)=1" in fit.metadata.monotonicity_assumption


def test_negative_rate_fixture_is_allowed_unconstrained_but_not_called_universal_arbitrage() -> (
    None
):
    nodes = np.arange(1.0, 5.0)
    cashflows = 100.0 * np.eye(4)
    increasing_discounts = np.array([1.01, 1.02, 1.03, 1.04])
    prices = cashflows @ increasing_discounts
    negative_rate_fit = fit_constrained_discount_curve(
        cashflows,
        prices,
        nodes,
        smoothness=0.0,
        monotone=False,
        compute_loo=False,
        compare_solver=False,
    )
    restricted_fit = fit_constrained_discount_curve(
        cashflows,
        prices,
        nodes,
        smoothness=0.0,
        monotone=True,
        compute_loo=False,
        compare_solver=False,
    )

    np.testing.assert_allclose(negative_rate_fit.discount_factors, increasing_discounts)
    assert negative_rate_fit.discount_factors.max() > 1.0
    assert negative_rate_fit.metadata.monotonicity_assumption is None
    assert "negative rates" in negative_rate_fit.metadata.monotonicity_warning
    np.testing.assert_allclose(restricted_fit.discount_factors, np.ones(4), atol=1e-12)
    assert restricted_fit.metadata.monotone_discount_factors
    assert restricted_fit.metadata.first_node_upper_bound == 1.0


def test_discount_floor_has_a_separate_raw_scale_acceptance_gate() -> None:
    nodes = np.arange(1.0, 5.0)
    cashflows = 100.0 * np.eye(4)
    floor = 1e-8
    fit = fit_constrained_discount_curve(
        cashflows,
        np.full(4, 1e-10),
        nodes,
        smoothness=0.0,
        minimum_discount=floor,
        compute_loo=False,
        compare_solver=False,
    )

    np.testing.assert_allclose(fit.discount_factors, floor, rtol=0.0, atol=1e-18)
    assert fit.diagnostics.maximum_discount_floor_violation == 0.0
    assert fit.diagnostics.hard_constraint_tolerance >= 1e-4 * floor
    assert fit.diagnostics.hard_constraints_passed
    assert fit.diagnostics.accepted
    assert "numerical positivity floor" in fit.metadata.minimum_discount_rationale


def test_hard_constraint_audit_uses_local_discount_scales() -> None:
    floor = 1e-8
    (
        floor_violation,
        monotonicity_violation,
        anchor_violation,
        tolerance_summary,
        passed,
    ) = constrained_curves._hard_constraint_audit(
        np.array([-1.0, 1e20]),
        minimum_discount=floor,
        monotone=False,
    )

    assert floor_violation == pytest.approx(1.0 + floor)
    assert monotonicity_violation == 0.0
    assert anchor_violation == 0.0
    assert tolerance_summary < floor_violation
    assert not passed


def test_quote_widths_become_precision_weights_and_change_weighted_metric() -> None:
    nodes = np.arange(1.0, 5.0)
    cashflows = np.array(
        [
            [100.0, 0.0, 0.0, 0.0],
            [0.0, 100.0, 0.0, 0.0],
            [0.0, 0.0, 100.0, 0.0],
            [0.0, 0.0, 0.0, 100.0],
            [25.0, 25.0, 25.0, 25.0],
        ]
    )
    prices = cashflows @ np.array([0.99, 0.96, 0.92, 0.87])
    prices[-1] += 0.2
    widths = np.array([0.01, 0.02, 0.02, 0.04, 0.5])
    fit = fit_constrained_discount_curve(
        cashflows,
        prices,
        nodes,
        quote_widths=widths,
        smoothness=0.1,
        compute_loo=False,
        compare_solver=False,
    )

    np.testing.assert_allclose(fit.weights, 1.0 / widths**2)
    assert "quote width" in fit.metadata.weighting
    assert np.isfinite(fit.diagnostics.weighted_pricing_rmse)
    with pytest.raises(ValueError, match="not both"):
        fit_constrained_discount_curve(
            cashflows,
            prices,
            nodes,
            weights=np.ones(5),
            quote_widths=widths,
        )


def test_b1_wrapper_loo_uses_fixed_full_node_grid_and_reports_solver_agreement() -> None:
    universe = make_synthetic_jgb_universe(price_noise_std=0.01, seed=32)
    fit = fit_constrained_bond_discount_curve(
        universe,
        smoothness=1.0,
        monotone=True,
        compute_loo=True,
        compare_solver=True,
    )

    assert fit.diagnostics.accepted
    assert fit.leave_one_out is not None
    assert fit.leave_one_out.node_grid_fixed
    assert fit.leave_one_out.all_fits_accepted
    assert fit.leave_one_out.accepted_fits == len(universe.bonds)
    assert np.isfinite(fit.leave_one_out.rmse)
    assert fit.leave_one_out.rmse == pytest.approx(fit.diagnostics.leave_one_out_pricing_rmse)
    assert "only the held-out bond price" in fit.leave_one_out.contract
    assert fit.diagnostics.solver_comparison_passed
    assert fit.diagnostics.alternate_solver_kkt_passed

    data = bond_cashflow_matrix(universe)
    direct = leave_one_bond_out_constrained_curve(
        data.cashflow_matrix,
        data.dirty_prices,
        data.node_times,
        smoothness=1.0,
        monotone=True,
    )
    assert direct.rmse == pytest.approx(fit.leave_one_out.rmse)
    assert leave_one_bond_out_constrained_curve_rmse(
        data.cashflow_matrix,
        data.dirty_prices,
        data.node_times,
        smoothness=1.0,
        monotone=True,
    ) == pytest.approx(direct.rmse)


def test_rank_deficiency_is_diagnosed_without_claiming_unique_node_discounts() -> None:
    cashflows = np.ones((3, 3))
    fit = fit_constrained_discount_curve(
        cashflows,
        np.full(3, 2.7),
        [1.0, 2.0, 3.0],
        smoothness=0.0,
        compute_loo=False,
        compare_solver=False,
    )

    assert fit.diagnostics.cashflow_rank == 1
    assert fit.diagnostics.penalized_design_rank == 1
    assert not fit.diagnostics.penalized_design_full_column_rank
    assert np.isinf(fit.diagnostics.penalized_design_condition_number)
    assert any("rank deficient" in warning for warning in fit.diagnostics.warnings)
    np.testing.assert_allclose(fit.fitted_prices, fit.observed_prices)
    assert not fit.diagnostics.accepted


def test_loo_rejects_folds_whose_held_out_node_is_not_identified() -> None:
    cashflows = 100.0 * np.eye(4)
    prices = cashflows @ np.array([0.99, 0.96, 0.92, 0.87])
    result = leave_one_bond_out_constrained_curve(
        cashflows,
        prices,
        [1.0, 2.0, 3.0, 4.0],
        smoothness=0.0,
    )

    assert result.identified_fits == 0
    assert result.accepted_fits == 0
    assert not result.all_fits_accepted
    assert np.isnan(result.rmse)


def test_adapter_can_read_explicit_quote_width_column() -> None:
    universe = make_synthetic_jgb_universe(maturities=(1.0, 2.0, 3.0), seed=35)
    widths = np.array([0.01, 0.02, 0.03])
    with_widths = CouponBondUniverse(
        bonds=universe.bonds.assign(bid_ask_width=widths),
        cashflows=universe.cashflows,
    )
    data = bond_cashflow_matrix(with_widths, quote_width_column="bid_ask_width")
    np.testing.assert_allclose(data.quote_widths, widths)


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: second_difference_matrix(2), "at least three"),
        (
            lambda: fit_constrained_discount_curve(
                np.eye(3),
                np.ones(3),
                [1.0, 1.0, 2.0],
            ),
            "strictly increasing",
        ),
        (
            lambda: fit_constrained_discount_curve(
                np.eye(3),
                np.ones(3),
                [1.0, 2.0, 3.0],
                quote_widths=[1.0, 0.0, 1.0],
            ),
            "strictly positive",
        ),
        (
            lambda: fit_constrained_discount_curve(
                np.eye(3),
                np.ones(3),
                [1.0, 2.0, 3.0],
                node_time_unit="",
            ),
            "non-empty",
        ),
        (
            lambda: predict_prices_from_discounts(np.eye(3), [1.0, 0.0, 1.0]),
            "strictly positive",
        ),
        (
            lambda: leave_one_bond_out_constrained_curve(
                np.eye(3),
                np.ones(3),
                [1.0, 2.0, 3.0],
                monotone="false",
            ),
            "boolean",
        ),
    ],
)
def test_constrained_curve_contract_rejects_invalid_shapes_scales_and_units(
    operation,
    message,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        operation()
