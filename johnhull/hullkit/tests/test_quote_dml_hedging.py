"""Frozen-contract quote hedges against independently bootstrapped cashflows."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_dml_teachers as teacher

Q = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])


@pytest.fixture(scope="module")
def hedge():
    def load():
        name = "hullkit._quote_dml_hedging"
        assert importlib.util.find_spec(name) is not None, "frozen quote hedge module is missing"
        return importlib.import_module(name)

    return load


@pytest.fixture(scope="module")
def reference():
    path = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml/reference_methods.py"
    spec = importlib.util.spec_from_file_location("quote_hedge_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("q", [Q, Q - 0.04, Q + np.array([0.001, -0.001, 0.002, -0.002, 0.001])])
def test_held_cashflows_and_quote_risk_match_independent_reference(hedge, reference, q):
    hedge = hedge()
    market = teacher.prepare_market(q)
    # Off-market coupons exercise nonzero cross-bucket sensitivities.
    coupons = Q + np.array([0.002, -0.002, 0.001, 0.004, -0.003])
    np.testing.assert_allclose(
        hedge.held_prices(market, 110.0, coupons),
        reference.held_prices(q, 110.0, coupons),
        atol=1e-6,
        rtol=1e-10,
    )
    np.testing.assert_allclose(
        hedge.held_risk(market, 110.0, coupons),
        reference.held_risk(q, 110.0, coupons),
        atol=1e-6,
        rtol=1e-10,
    )


def test_shocked_swap_keeps_original_coupon(hedge):
    hedge = hedge()
    shifted = Q.copy()
    shifted[4] += 1e-4
    market = teacher.prepare_market(shifted)
    held = hedge.held_prices(market, 100.0, Q)[-1]
    reset = hedge.held_prices(market, 100.0, shifted)[-1]
    assert held == pytest.approx(-451.6857813536834, abs=1e-6, rel=1e-9)
    assert reset == pytest.approx(0.0, abs=1e-6)
    assert abs(held - reset) > 450


def test_each_center_uses_its_own_par_coupon_and_diagonal_quote_risk(hedge, reference):
    hedge = hedge()
    for q in (Q, Q + np.array([0.003, -0.002, 0.001, -0.001, 0.002])):
        market = teacher.prepare_market(q)
        prices = hedge.held_prices(market, 100.0, market.quotes)
        np.testing.assert_allclose(prices, np.r_[100.0, np.zeros(5)], atol=1e-6)
        expected = np.diag(
            np.r_[
                1.0,
                -1e6 * 0.5 * reference.discount(q, 0.5),
                -1e6 * 0.5 * reference.discount(q, 1.0),
                [
                    -1e6 * sum(reference.discount(q, t) for t in ts)
                    for ts in reference.SCHEDULES[2:]
                ],
            ]
        )
        np.testing.assert_allclose(
            hedge.held_risk(market, 100.0, market.quotes), expected, atol=1e-6, rtol=1e-10
        )


def test_quantities_cancel_independent_spot_and_quote_risk(hedge, reference):
    hedge = hedge()
    market = teacher.prepare_market(Q)
    B = reference.held_risk(Q, 110.0, Q)
    target = reference.digital_moments(Q, 110.0, 4.5)["g_quote"]
    h = hedge.solve_hedge(B, target)
    np.testing.assert_allclose(B @ h + target, np.zeros(6), atol=1e-12)
    assert h[0] < 0  # Positive digital delta requires short stock.
    expected_rates = -target[1:] / np.diag(B)[1:]
    np.testing.assert_allclose(h[1:], expected_rates, atol=1e-14, rtol=1e-10)
    np.testing.assert_allclose(
        hedge.held_risk(market, 110.0, Q) @ h + target, np.zeros(6), atol=1e-10
    )


def test_notional_change_preserves_held_cashflows_and_shock_pnl(hedge, reference):
    hedge = hedge()
    market = teacher.prepare_market(Q)
    target = reference.digital_moments(Q, 110.0, 4.5)["g_quote"]
    B1 = hedge.held_risk(market, 110.0, Q, notional=1e6)
    B2 = hedge.held_risk(market, 110.0, Q, notional=2e6)
    h1, h2 = hedge.solve_hedge(B1, target), hedge.solve_hedge(B2, target)
    assert h2[0] == pytest.approx(h1[0], abs=1e-14)
    np.testing.assert_allclose(h2[1:] * 2, h1[1:], atol=1e-14, rtol=1e-10)
    shocked = teacher.prepare_market(Q + np.array([1, -1, 0, 1, -1]) * 1e-4)
    pv1 = hedge.held_prices(shocked, 111.0, Q, notional=1e6)
    pv2 = hedge.held_prices(shocked, 111.0, Q, notional=2e6)
    np.testing.assert_allclose(h1 * pv1, h2 * pv2, atol=1e-12, rtol=1e-10)
    assert h1 @ pv1 == pytest.approx(h2 @ pv2, abs=1e-12, rel=1e-10)


def test_zero_shock_gives_zero_revaluation(hedge, reference):
    hedge = hedge()
    B = reference.held_risk(Q, 110.0, Q)
    exact = reference.digital_moments(Q, 110.0, 4.5)
    h = hedge.solve_hedge(B, exact["g_quote"])
    initial = reference.held_prices(Q, 110.0, Q)
    final = reference.held_prices(Q.copy(), 110.0, Q.copy())
    residual = (
        reference.digital_price(Q.copy(), 110.0, 4.5) - exact["price"] + h @ (final - initial)
    )
    assert residual == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("kind", ["spot", "rate"])
def test_reference_hedge_leaves_second_order_small_shock_residual(hedge, reference, kind):
    hedge = hedge()
    spot, maturity = 110.0, 4.5
    exact = reference.digital_moments(Q, spot, maturity)
    h = hedge.solve_hedge(reference.held_risk(Q, spot, Q), exact["g_quote"])
    initial = reference.held_prices(Q, spot, Q)

    def residual(width, quantities):
        q, shifted_spot = Q.copy(), spot
        if kind == "spot":
            shifted_spot += width
        else:
            q[4] += width
        return (
            reference.digital_price(q, shifted_spot, maturity)
            - exact["price"]
            + quantities @ (reference.held_prices(q, shifted_spot, Q) - initial)
        )

    width = 0.2 if kind == "spot" else 1e-4
    big, small = residual(width, h), residual(width / 2, h)
    assert abs(small) < abs(big)
    assert abs(big / small) == pytest.approx(4.0, rel=0.03)
    # Both reversed and doubled positions leave an uncancelled first-order term.
    assert abs(residual(width / 2, -h)) > 100 * abs(small)
    assert abs(residual(width / 2, 2 * h)) > 50 * abs(small)


def test_entry_cost_uses_per_bp_rates_and_absolute_quantities(hedge, reference):
    hedge = hedge()
    B = reference.held_risk(Q, 100.0, Q)
    h = np.array([-0.1, 0.2, -0.3, 0.4, -0.5, 0.6])
    expected_stock = abs(h[0]) * 100 * 5e-4
    expected_rate = np.sum(np.abs(h[1:]) * np.abs(np.diag(B)[1:]) * 1e-4 * 0.5)
    got = hedge.entry_cost(h, B, 100.0, rate_halfspread_bp=0.5, stock_halfspread_bp=5.0)
    assert got == pytest.approx(expected_stock + expected_rate, abs=1e-10, rel=1e-12)
    assert hedge.entry_cost(
        h, B, 100.0, rate_halfspread_bp=0.0, stock_halfspread_bp=0.0
    ) == pytest.approx(0.0, abs=1e-14)
    assert hedge.entry_cost(
        -h, B, 100.0, rate_halfspread_bp=0.5, stock_halfspread_bp=5.0
    ) == pytest.approx(got, abs=1e-10)


def test_entry_cost_preserves_economics_when_notional_changes(hedge, reference):
    hedge = hedge()
    B1 = reference.held_risk(Q, 100.0, Q, notional=1e6)
    B2 = reference.held_risk(Q, 100.0, Q, notional=2e6)
    target = reference.digital_moments(Q, 100.0, 1.5)["g_quote"]
    cost1 = hedge.entry_cost(
        hedge.solve_hedge(B1, target), B1, 100.0, rate_halfspread_bp=1.0, stock_halfspread_bp=1.0
    )
    cost2 = hedge.entry_cost(
        hedge.solve_hedge(B2, target), B2, 100.0, rate_halfspread_bp=1.0, stock_halfspread_bp=1.0
    )
    assert cost1 == pytest.approx(cost2, abs=1e-14, rel=1e-10)


@pytest.mark.parametrize("B", [np.zeros((6, 6)), np.ones((6, 6)), np.zeros((5, 5))])
def test_rank_deficient_or_wrong_shape_hedge_is_rejected(hedge, B):
    hedge = hedge()
    with pytest.raises(ValueError):
        hedge.solve_hedge(B, np.ones(6))


def test_quote_unit_scaling_does_not_reject_well_spanned_problem(hedge):
    hedge = hedge()
    # Raw condition number is one million, but spot/bp normalized rank is full.
    B = np.diag(np.r_[1.0, np.full(5, -1e6)])
    g = np.r_[0.01, np.arange(1.0, 6.0)]
    np.testing.assert_allclose(B @ hedge.solve_hedge(B, g), -g, atol=1e-12)


@pytest.mark.parametrize("field", ["matrix", "gradient"])
def test_nonfinite_hedge_inputs_fail_explicitly(hedge, field):
    hedge = hedge()
    B, g = np.eye(6), np.ones(6)
    if field == "matrix":
        B[0, 0] = np.nan
    else:
        g[0] = np.inf
    with pytest.raises(ValueError):
        hedge.solve_hedge(B, g)


@pytest.mark.parametrize("notional", [0, -1, np.inf])
def test_invalid_notional_rejected(hedge, notional):
    hedge = hedge()
    market = teacher.prepare_market(Q)
    with pytest.raises(ValueError):
        hedge.held_prices(market, 100.0, Q, notional=notional)


@pytest.mark.parametrize("field", ["rate_halfspread_bp", "stock_halfspread_bp"])
def test_negative_spread_cost_rejected(hedge, field):
    hedge = hedge()
    kwargs = {"rate_halfspread_bp": 0.5, "stock_halfspread_bp": 1.0, field: -1.0}
    with pytest.raises(ValueError):
        hedge.entry_cost(np.ones(6), np.eye(6), 100.0, **kwargs)
