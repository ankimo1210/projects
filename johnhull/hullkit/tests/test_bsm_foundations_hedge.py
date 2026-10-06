"""Hull GE 15.5: local cancellation and self-financing hedge rebalancing."""

from fractions import Fraction

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm


def test_hull_local_hedge_and_ten_share_rebalance():
    result = foundations.delta_hedge_cash(-100, .4, .10, .04, 50, .5)
    assert [result["stock_units"], result["option_pnl"], result["stock_pnl"], result["pnl"]] == pytest.approx([40, -4, 4, 0])
    assert result["rebalance_units"] == pytest.approx(10)


def test_hedge_cashflow_against_independent_fraction_ledger():
    # The source does not specify the rebalance price; 50 is synthetic.
    option_units = Fraction(-100)
    delta_before, delta_after = Fraction(2, 5), Fraction(1, 2)
    stock_units = -option_units*delta_before
    trade = -option_units*delta_after-stock_units
    bank_before = Fraction(700)
    bank_after = bank_before-trade*50
    before = bank_before+stock_units*50
    after = bank_after+(stock_units+trade)*50
    result = foundations.delta_hedge_cash(-100, .4, .10, .04, 50, .5)
    assert result["rebalance_cash"] == pytest.approx(float(bank_after-bank_before))
    assert float(after-before) == pytest.approx(0)
    assert result["rebalance_units"]*50+result["rebalance_cash"] == pytest.approx(0)


def test_finite_stock_move_has_gamma_residual_not_riskless_profit():
    s, k, r, sigma, t = 42, 40, .1, .2, .5
    delta = float(bsm.call_delta(s, k, r, sigma, t))
    gamma = float(bsm.gamma(s, k, r, sigma, t))
    for ds in [.1, .01]:
        dc = float(bsm.call_price(s+ds, k, r, sigma, t)-bsm.call_price(s, k, r, sigma, t))
        result = foundations.delta_hedge_cash(-100, delta, ds, dc, s+ds, delta)
        assert result["pnl"] < 0
        assert result["pnl"]/ds**2 == pytest.approx(-50*gamma, rel=.02)


def test_rebalance_price_must_be_positive():
    with pytest.raises(ValueError):
        foundations.delta_hedge_cash(-100, .4, .1, .04, 0, .5)
