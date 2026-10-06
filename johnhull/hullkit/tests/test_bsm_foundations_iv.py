"""Hull GE 15.11: bisection, finite-IV bounds and source VIX quote units."""

import math
from fractions import Fraction

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit.trees import crr_price
from hullkit.volatility import implied_vol


def test_source_bisection_prices_and_implied_volatility():
    prices = [float(bsm.call_price(21, 20, .1, sigma, .25)) for sigma in [.2, .3, .25]]
    assert prices[:2] == pytest.approx([1.76, 2.10], abs=.005, rel=0)
    assert prices[2] == pytest.approx(1.926831, abs=.000001, rel=0)
    assert prices[0] < 1.875 < prices[2] < prices[1]
    sigma = foundations.implied_vol_bisection(1.875, 21, 20, .1, .25)
    assert sigma == pytest.approx(.235, abs=.0005, rel=0)
    assert sigma == pytest.approx(.23451291, abs=1e-8)
    assert float(bsm.call_price(21, 20, .1, sigma, .25)) == pytest.approx(1.875, abs=1e-10)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_inverse_against_independent_brent_solver(kind):
    pricing = bsm.call_price if kind == "call" else bsm.put_price
    price = float(pricing(42, 40, -.02, .35, .75))
    sigma = foundations.implied_vol_bisection(price, 42, 40, -.02, .75, kind=kind)
    assert sigma == pytest.approx(.35, abs=1e-9)
    assert sigma == pytest.approx(implied_vol(price, 42, 40, -.02, .75, kind=kind), abs=1e-9)


def test_source_implied_vol_reprices_in_independent_crr_tree():
    sigma = foundations.implied_vol_bisection(1.875, 21, 20, .1, .25)
    assert crr_price(21, 20, .1, sigma, .25, 1200) == pytest.approx(1.875, abs=.002)


@pytest.mark.parametrize("kind,price", [("call", 1.48), ("call", 21), ("put", -.01), ("put", 20*math.exp(-.025))])
def test_impossible_or_infinite_volatility_quote_has_no_finite_root(kind, price):
    with pytest.raises(ValueError):
        foundations.implied_vol_bisection(price, 21, 20, .1, .25, kind=kind)


def test_zero_extrinsic_chooses_zero_volatility():
    deterministic = float(bsm.call_price(21, 20, .1, 0, .25))
    assert foundations.implied_vol_bisection(deterministic, 21, 20, .1, .25) == pytest.approx(0)


def test_expired_option_does_not_identify_volatility():
    with pytest.raises(ValueError):
        foundations.implied_vol_bisection(2, 42, 40, .1, 0)


def test_example_15_8_quote_units_and_independent_fraction_futures_ledger():
    pnl = foundations.quoted_futures_pnl(18.5, 19.3, 1000)
    expected = (Fraction(193, 10)-Fraction(185, 10))*1000
    assert pnl == pytest.approx(float(expected), abs=1e-10)
    assert pnl == pytest.approx(800, abs=1e-10)
    assert foundations.quoted_futures_pnl(18.5, 19.3, 1000, quantity=-1) == pytest.approx(-800, abs=1e-10)
    assert 15/100 == pytest.approx(.15)
    assert foundations.quoted_futures_pnl(.185, .193, 100000) == pytest.approx(pnl, abs=1e-10)
