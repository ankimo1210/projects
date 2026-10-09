"""Independent accounting, calendar and positivity checks for dynamic research core."""

from dataclasses import replace

import numpy as np
import pytest
from hullkit._dynamic_hedging_core import (
    asian_memory,
    cash_account,
    cir_implicit_step,
    heston_records,
    local_records,
    moment_certificate,
)
from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid


@pytest.fixture
def parameters():
    return HestonParameters(100.0, 0.03, 0.0, 0.04, 2.0, 0.04, 0.3, -0.7)


def test_constant_variance_is_exact_gbm_with_supplied_normals(parameters):
    p = replace(parameters, xi=0.0)
    times = np.array([0.4, 0.5, 0.8])
    normals = np.array([[[0.2, 99.0], [-0.7, 99.0]], [[-0.4, -99.0], [0.8, -99.0]]])
    out = heston_records(p, normals, times, np.arange(3), spot=np.array([90.0, 110.0]))
    logs = (p.rate - 0.5 * 0.04) * np.diff(times) + 0.2 * np.sqrt(np.diff(times)) * normals[:, :, 0]
    expected = np.array([90.0, 110.0])[:, None] * np.exp(
        np.c_[np.zeros(2), np.cumsum(logs, axis=1)]
    )
    np.testing.assert_allclose(out["spot"], expected, rtol=1e-14)
    np.testing.assert_allclose(out["variance"], 0.04)
    assert out["path_mask"].all()


def test_xi_zero_cir_transition_is_exact_for_nonconstant_variance(parameters):
    p = replace(parameters, xi=0.0)
    out = cir_implicit_step(np.array([0.0, 0.09]), np.array([-1e9, 1e9]), 0.3, p)
    np.testing.assert_allclose(out, 0.04 + (np.array([0.0, 0.09]) - 0.04) * np.exp(-0.6))


def test_positive_cir_satisfies_quadratic_even_for_large_negative_normal(parameters):
    v = np.array([0.0, 0.04, 0.09])
    z = np.array([-1e5, -3.0, 4.0])
    dt = 0.1
    result = cir_implicit_step(v, z, dt, parameters)
    assert np.all(np.isfinite(result) & (result > 0))
    y = np.sqrt(result)
    u = np.sqrt(v) + 0.15 * np.sqrt(dt) * z
    a = (4 * 2 * 0.04 - 0.3**2) / 8
    np.testing.assert_allclose(1.1 * y**2 - u * y, a * dt, rtol=1e-12, atol=1e-16)


def test_heston_stock_uses_old_variance_and_correlated_variance_shock(parameters):
    normals = np.array([[[0.8, -0.2]]])
    out = heston_records(parameters, normals, np.array([0.0, 0.25]), np.array([0, 1]))
    assert out["spot"][0, 1] == pytest.approx(100 * np.exp((0.03 - 0.02) * 0.25 + 0.2 * 0.5 * 0.8))
    zv = -0.7 * 0.8 + np.sqrt(1 - 0.7**2) * -0.2
    assert out["variance"][0, 1] == pytest.approx(
        cir_implicit_step(np.array([0.04]), np.array([zv]), 0.25, parameters)[0]
    )


def test_moment_certificate_contains_independent_fixed_grid_evidence(parameters):
    c = moment_certificate(parameters, 1.25)
    assert c["qualified"]
    assert c["gaussian_quadratic_coefficient"] == pytest.approx(0.99421875)
    assert c["scope"] == "fixed_finite_grid_sufficient_bound"
    for row in c["backward_mgf"]:
        n = row["steps"]
        dt = 1.25 / n
        eta = 0.0
        denominators = []
        for _ in range(n):
            denominator = (1 + dt) ** 2 - 2 * 0.15**2 * dt * eta
            denominators.append(denominator)
            eta = 28 * dt + eta / denominator
        assert row["min_denominator"] == pytest.approx(min(denominators))
        assert row["eta"] == pytest.approx(eta)
        assert row["qualified"]
    assert not moment_certificate(parameters, 2.0)["qualified"]


def test_local_restart_uses_absolute_calendar_midpoint(parameters):
    surface = LocalVarianceGrid(
        np.array([0.1, 0.5, 1.0]),
        np.array([-10.0, 10.0]),
        np.array([[0.01, 0.01], [0.05, 0.05], [0.10, 0.10]]),
        parameters,
    )
    times = np.array([0.5, 0.7, 0.9])
    normals = np.zeros((2, 2, 2))
    out = local_records(
        parameters,
        surface,
        normals,
        times,
        np.arange(3),
        spot=np.array([90.0, 110.0]),
        multiplier=2.0,
    )
    variance = np.array([0.12, 0.16])
    expected = np.array([90.0, 110.0]) * np.exp(np.sum((0.03 - variance / 2) * 0.2))
    np.testing.assert_allclose(out["spot"][:, -1], expected)
    np.testing.assert_allclose(out["variance"][:, :2], np.tile(variance, (2, 1)))
    assert out["diagnostics"]["original_path_count"] == 2


def test_local_preserves_unsupported_path_and_original_count(parameters):
    surface = LocalVarianceGrid(
        np.array([0.1, 0.5]), np.array([-2.0, 2.0]), np.full((2, 2), 0.04), parameters
    )
    out = local_records(
        parameters, surface, np.zeros((2, 1, 2)), np.array([0.5, 0.7]), np.arange(2)
    )
    assert out["spot"].shape == (2, 2)
    assert not out["path_mask"].any()
    assert np.isnan(out["spot"][:, -1]).all()
    assert list(out["reasons"]) == ["unsupported_time", "unsupported_time"]
    assert out["diagnostics"]["original_path_count"] == 2
    assert out["diagnostics"]["unsupported_count"] == 2


def test_local_preserves_wing_and_early_proxy_status(parameters):
    surface = LocalVarianceGrid(
        np.array([0.1, 0.5]), np.array([-1.0, 1.0]), np.full((2, 2), 0.04), parameters
    )
    out = local_records(
        parameters,
        surface,
        np.zeros((2, 1, 2)),
        np.array([0.0, 0.1]),
        np.arange(2),
        spot=np.array([100.0, 200.0]),
    )
    assert out["path_mask"].all()
    assert out["diagnostics"]["wing_count"] == 1
    assert out["diagnostics"]["early_proxy_count"] == 2


def test_nonfinite_heston_path_is_retained_without_repair(parameters):
    normals = np.zeros((2, 2, 2))
    normals[1, 0, 0] = np.nan
    out = heston_records(parameters, normals, np.array([0.0, 0.1, 0.2]), np.arange(3))
    assert out["path_mask"].tolist() == [True, False]
    assert np.isnan(out["spot"][1, 1:]).all()
    assert out["diagnostics"]["original_path_count"] == 2


def test_asian_memory_adds_fixing_before_rebalance_and_excludes_initial_spot():
    times = np.array([0.0, 1 / 24, 1 / 12, 2 / 12])
    spots = np.array([[100.0, 999.0, 110.0, 90.0], [100.0, 999.0, 80.0, 120.0]])
    fixings = np.arange(1, 13) / 12
    out = asian_memory(spots, times, fixings)
    np.testing.assert_array_equal(out["A"], [[0.0, 0.0, 110.0, 200.0], [0.0, 0.0, 80.0, 200.0]])
    np.testing.assert_array_equal(out["n"], [0, 0, 1, 2])
    np.testing.assert_array_equal(out["m"], [12, 12, 11, 10])


def test_asian_memory_rejects_missing_observation():
    with pytest.raises(ValueError, match="fixing"):
        asian_memory(np.array([[100.0, 120.0]]), np.array([0.0, 1.0]), np.array([0.5, 1.0]))


def independent_gain(times, prices, holdings, payoff, premium, rate, cf, fees):
    discount = np.exp(-rate * (times - times[0]))
    costs = np.sum(
        fees
        * prices
        * np.abs(
            np.diff(
                np.concatenate(
                    [np.zeros_like(holdings[:, :1]), holdings, np.zeros_like(holdings[:, :1])],
                    axis=1,
                ),
                axis=1,
            )
        ),
        axis=2,
    )
    gains = np.sum(
        holdings
        * (
            discount[None, 1:, None] * (prices[:, 1:] + cf[:, 1:])
            - discount[None, :-1, None] * prices[:, :-1]
        ),
        axis=(1, 2),
    )
    return premium + gains - np.sum(discount * costs, axis=1) - discount[-1] * payoff


def test_two_asset_cash_matches_independent_discounted_gain():
    times = np.array([0.0, 0.5, 1.0])
    prices = np.array([[[100.0, 6.0], [104.0, 8.0], [102.0, 5.0]]])
    holdings = np.array([[[0.4, 0.5], [0.6, 0.2]]])
    out = cash_account(
        times,
        prices,
        holdings,
        np.array([3.0]),
        premium=7.0,
        rate=0.05,
        cost_rates=np.array([0.001, 0.005]),
    )
    assert out["discounted_pnl"][0] == pytest.approx(2.2171179961044647, abs=1e-12)
    np.testing.assert_allclose(out["costs"][0], [0.055, 0.0328, 0.0662], atol=1e-12)
    expected = independent_gain(
        times,
        prices,
        holdings,
        np.array([3.0]),
        7.0,
        0.05,
        np.zeros_like(prices),
        np.array([0.001, 0.005]),
    )
    np.testing.assert_allclose(out["discounted_pnl"], expected, atol=1e-12)
    np.testing.assert_allclose(out["discounted_gain_pnl"], expected, atol=1e-12)


def test_cashflow_received_by_previous_holdings_at_event_and_terminal_once():
    times = np.array([0.2, 0.5, 1.0])
    prices = np.array([[[100.0, 6.0], [98.0, 8.0], [99.0, 5.0]]])
    holdings = np.array([[[2.0, 1.0], [-1.0, 0.5]]])
    cf = np.array([[[999.0, 999.0], [2.0, 0.3], [1.0, 0.2]]])
    out = cash_account(
        times,
        prices,
        holdings,
        np.array([4.0]),
        premium=10.0,
        rate=0.0,
        cashflows=cf,
        cost_rates=np.array([0.01, 0.02]),
    )
    # Cash: 10-206-2.12=-198.12; receive4.3, trade receipts=298-3.02;
    # terminal CF=-.9, liquidation=-96.5; terminal fee=1.04; claim4.
    assert out["cash"][0, 0] == pytest.approx(-198.12)
    assert out["cash"][0, 1] == pytest.approx(101.16)
    assert out["cash"][0, 2] == pytest.approx(-1.28)
    expected = independent_gain(
        times, prices, holdings, np.array([4.0]), 10.0, 0.0, cf, np.array([0.01, 0.02])
    )
    np.testing.assert_allclose(out["discounted_pnl"], expected)


def test_dividend_event_preserves_discounted_total_return():
    times = np.array([0.0, 0.4, 1.0])
    rate = 0.03
    dividend = 2.0
    p0 = 100.0
    p1 = p0 * np.exp(rate * 0.4) - dividend
    p2 = p1 * np.exp(rate * 0.6)
    prices = np.array([[[p0], [p1], [p2]]])
    cf = np.array([[[0.0], [dividend], [0.0]]])
    out = cash_account(
        times, prices, np.ones((1, 2, 1)), np.zeros(1), premium=0.0, rate=rate, cashflows=cf
    )
    assert out["discounted_pnl"][0] == pytest.approx(0.0, abs=3e-14)


def test_cash_failure_retains_original_path_and_nan_after_failed_event():
    prices = np.full((2, 3, 1), 100.0)
    prices[1, 1, 0] = np.nan
    out = cash_account(
        np.array([0.0, 0.5, 1.0]), prices, np.ones((2, 2, 1)), np.zeros(2), premium=0.0, rate=0.03
    )
    assert out["path_mask"].tolist() == [True, False]
    assert np.isfinite(out["cash"][1, 0])
    assert np.isnan(out["cash"][1, 1:]).all()
    assert np.isnan(out["discounted_pnl"][1])
    assert out["diagnostics"]["original_path_count"] == 2


@pytest.mark.parametrize(
    "times", [np.array([0.0, 0.0]), np.array([0.5, 0.0]), np.array([0.0, np.nan])]
)
def test_recorder_rejects_invalid_calendar(parameters, times):
    with pytest.raises(ValueError, match="times"):
        heston_records(parameters, np.zeros((1, 1, 2)), times, np.arange(2))


def test_zero_variance_underflow_is_a_heston_transition_failure(parameters):
    normals = np.array([[[0.0, -1e200]]])
    out = heston_records(parameters, normals, np.array([0.0, 0.1]), np.arange(2))
    assert not out["path_mask"][0]
    assert np.isnan(out["variance"][0, -1])


def test_discount_overflow_retains_failure_status_in_cash():
    out = cash_account(
        np.array([0.0, 1.0]),
        np.ones((1, 2, 1)),
        np.zeros((1, 1, 1)),
        np.zeros(1),
        premium=0.0,
        rate=-1000.0,
    )
    assert not out["path_mask"][0]
    assert out["reasons"][0] == "nonfinite_discounted_account"
    assert np.isnan(out["discounted_pnl"][0])


def test_asian_memory_accepts_a_single_recorded_state():
    out = asian_memory(np.array([[100.0]]), np.array([0.0]), np.arange(1, 13) / 12)
    np.testing.assert_array_equal(out["A"], [[0.0]])
    np.testing.assert_array_equal(out["n"], [0])


def test_integer_initial_spot_is_a_valid_mathematical_state(parameters):
    p = replace(parameters, spot=100)
    out = heston_records(p, np.zeros((1, 1, 2)), np.array([0.0, 0.1]), np.arange(2))
    assert out["path_mask"][0]
    assert out["spot"][0, 1] > 0


@pytest.mark.parametrize("moment", [2, 3, 4])
@pytest.mark.parametrize("horizon", [1.0, 1.25])
def test_protocol_moment_cells_have_positive_backward_denominators(parameters, moment, horizon):
    certificate = moment_certificate(parameters, horizon, p=moment)
    assert certificate["qualified"]
    for row in certificate["backward_mgf"]:
        assert row["qualified"]
        assert np.all(row["denominators"] > 0)
        assert np.isfinite(row["log_bound_at_v0"])
    assert not certificate["continuous_model_or_uniform_convergence_certified"]


def test_excluded_cm2_lognormal_has_divergent_positive_exponential_moment(parameters):
    # Conditional second stock moment contains exp(dt*v1). If v1 is a
    # nondegenerate lognormal, its Gaussian-integral log integrand tends to
    # +infinity: dt*exp(mu+sigma*z) - z**2/2. The quadratic Gaussian tail
    # cannot dominate the exponential-of-exponential payoff.
    z = np.array([40.0, 80.0, 160.0])
    log_integrand = 0.1 * np.exp(-3.0 + 0.3 * z) - z**2 / 2
    assert np.all(np.diff(log_integrand) > 0)
    assert log_integrand[-1] > 1e15
    assert "diverge" in moment_certificate(parameters, 1.0)["excluded_cm2_lognormal"]
