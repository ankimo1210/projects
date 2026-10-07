"""Hull22.4 covariance risk, bond exposures and variance-preserving mapping."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _market_risk as market
from hullkit import bsm
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import brentq

COV = np.array(
    [
        [0.000275, 0.000094, 0.000177, 0.000080],
        [0.000094, 0.000187, 0.000138, 0.000102],
        [0.000177, 0.000138, 0.000237, 0.000097],
        [0.000080, 0.000102, 0.000097, 0.000173],
    ]
)


def test_table_22_8_and_independent_multivariate_normal_quadrature():
    amount = np.array([4000, 3000, 1000, 2000])
    result = market.covariance_risk(amount, COV)
    assert result["daily_sigma"] ** 2 == pytest.approx(14404, abs=1e-8)
    assert result["daily_sigma"] ** 2 == pytest.approx(14406.193, rel=2e-4)
    assert result["var"] == pytest.approx(279.222, rel=2e-4)
    assert result["es"] == pytest.approx(319.894, rel=2e-4)
    nodes, weights = hermgauss(4)
    factor = np.linalg.cholesky(COV)
    second = 0.0
    for ids in product(range(4), repeat=4):
        changes = factor @ (math.sqrt(2) * nodes[list(ids)])
        pnl = amount @ changes
        second += pnl**2 * np.prod(weights[list(ids)]) / math.pi**2
    assert result["daily_sigma"] ** 2 == pytest.approx(second, abs=1e-8)


def test_example_22_1_delta_positions_and_bsm_repricing_second_order_error():
    exposure = market.delta_exposures([120, 30], [1000, 20000])
    assert exposure == pytest.approx([120_000, 600_000], abs=1e-10)
    risk = market.normal_portfolio_risk(exposure, [0.02, 0.01], [[1, 0.3], [0.3, 1]])
    assert risk["daily_sigma"] / 1000 == pytest.approx(7.099, abs=0.0005)
    spot, strike, rate, vol, maturity = 100, 100, 0.04, 0.25, 1
    delta = bsm.call_delta(spot, strike, rate, vol, maturity)
    linear = market.delta_exposures([spot], [delta])[0]
    base = bsm.call_price(spot, strike, rate, vol, maturity)
    errors = []
    for change in [0.01, 0.005]:
        full = bsm.call_price(spot * (1 + change), strike, rate, vol, maturity) - base
        errors.append(abs(full - linear * change))
    assert errors[0] / errors[1] == pytest.approx(4, rel=0.03)


def test_source_1_2_year_bond_has_three_coupon_cashflows():
    result = market.bond_cashflows(1_000_000, 0.06, 1.2, frequency=2)
    assert result["times"] == pytest.approx([0.2, 0.7, 1.2], abs=1e-12)
    assert result["cashflows"] == pytest.approx([30000, 30000, 1030000], abs=1e-8)


@pytest.mark.parametrize("compounding", ["continuous", "periodic"])
def test_modified_duration_money_risk_and_independent_bond_repricing(compounding):
    times = np.array([0.2, 0.7, 1.2])
    cash = np.array([30000, 30000, 1030000])
    rate = 0.06
    result = market.bond_parallel_risk(
        times, cash, rate, 0.0001, compounding=compounding, frequency=2
    )

    def price(y):
        discount = (
            np.exp(-y * times) if compounding == "continuous" else (1 + y / 2) ** (-2 * times)
        )
        return cash @ discount

    h = 1e-5
    derivative = (price(rate + h) - price(rate - h)) / (2 * h)
    assert result["value"] == pytest.approx(price(rate), abs=1e-8)
    assert result["dollar_duration"] == pytest.approx(-derivative, rel=1e-9)
    assert result["daily_sigma"] == pytest.approx(abs(derivative) * 0.0001, rel=1e-9)


def test_cashflow_mapping_preserves_pv_and_individual_variance_with_independent_root():
    grid = [0.25, 0.5, 1]
    rates = [0.055, 0.06, 0.07]
    vols = np.array([0.0006, 0.001, 0.002])
    corr = np.array([[1, 0.9, 0.6], [0.9, 1, 0.7], [0.6, 0.7, 1]])
    mapped = market.cashflow_map(1_050_000, 0.8, grid, rates, vols, corr, compounding="annual")
    pv = 1_050_000 / (1.066**0.8)
    expected_weight = brentq(
        lambda w: (
            (w * 0.001) ** 2
            + ((1 - w) * 0.002) ** 2
            + 2 * 0.7 * w * (1 - w) * 0.001 * 0.002
            - 0.0016**2
        ),
        0,
        1,
    )
    assert mapped["value"] == pytest.approx(997662, abs=0.5)
    assert mapped["present_values"].sum() == pytest.approx(pv, abs=1e-8)
    assert mapped["present_values"][1] / pv == pytest.approx(expected_weight, abs=1e-12)
    cov = np.outer(vols, vols) * corr
    assert mapped["present_values"] @ cov @ mapped["present_values"] == pytest.approx(
        pv**2 * 0.0016**2, rel=1e-12
    )
    assert np.sum(mapped["principals"] / (1 + np.array(rates)) ** np.array(grid)) == pytest.approx(
        pv, abs=1e-8
    )


def test_exact_pillar_and_zero_volatility_cashflow_mapping():
    corr = np.eye(3)
    exact = market.cashflow_map(
        -500, 0.5, [0.25, 0.5, 1], [0.02, 0.03, 0.04], [0.001, 0.002, 0.003], corr
    )
    assert exact["principals"] == pytest.approx([0, -500, 0], abs=1e-10)
    flat = market.cashflow_map(100, 0.75, [0.25, 0.5, 1], [0.02, 0.03, 0.04], [0, 0, 0], corr)
    assert flat["present_values"] @ np.zeros((3, 3)) @ flat["present_values"] == pytest.approx(
        0, abs=1e-12
    )
    assert flat["weights"] == pytest.approx([0, 0.5, 0.5], abs=1e-12)


def test_fx_forward_and_ois_bond_decompositions_match_independent_cashflows():
    r, rf, maturity, spot, strike, notional = 0.04, 0.02, 1.5, 1.2, 1.21, 100
    domestic, foreign = math.exp(-r * maturity), math.exp(-rf * maturity)
    fx = market.fx_forward_bond_legs(spot, notional, strike, domestic, foreign)
    forward = spot * math.exp((r - rf) * maturity)
    assert fx["value"] == pytest.approx(notional * (forward - strike) * domestic, abs=1e-12)
    times = np.array([0.5, 1, 1.5])
    dfs = np.exp(-r * times)
    fixed_cash = np.array([2, 2, 102])
    swap = market.ois_bond_legs(fixed_cash, dfs, 100)
    forwards = (np.r_[1, dfs[:-1]] / dfs - 1) / 0.5
    floating_coupon = np.sum(100 * forwards * 0.5 * dfs)
    fixed_coupon = np.sum(2 * dfs)
    assert swap["value"] == pytest.approx(fixed_coupon - floating_coupon, abs=1e-12)
