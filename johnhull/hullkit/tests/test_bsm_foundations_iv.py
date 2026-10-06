"""Hull GE 15.11: bisection, finite-IV bounds and source VIX quote units."""

import math
from fractions import Fraction

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit.trees import crr_price
from hullkit.volatility import implied_vol


def test_source_bisection_prices_and_implied_volatility():
    prices = [float(bsm.call_price(21, 20, 0.1, sigma, 0.25)) for sigma in [0.2, 0.3, 0.25]]
    assert prices[:2] == pytest.approx([1.76, 2.10], abs=0.005, rel=0)
    assert prices[2] == pytest.approx(1.926831, abs=0.000001, rel=0)
    assert prices[0] < 1.875 < prices[2] < prices[1]
    sigma = foundations.implied_vol_bisection(1.875, 21, 20, 0.1, 0.25)
    assert sigma == pytest.approx(0.235, abs=0.0005, rel=0)
    assert sigma == pytest.approx(0.23451291, abs=1e-8)
    assert float(bsm.call_price(21, 20, 0.1, sigma, 0.25)) == pytest.approx(1.875, abs=1e-10)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_inverse_against_independent_brent_solver(kind):
    pricing = bsm.call_price if kind == "call" else bsm.put_price
    price = float(pricing(42, 40, -0.02, 0.35, 0.75))
    sigma = foundations.implied_vol_bisection(price, 42, 40, -0.02, 0.75, kind=kind)
    assert sigma == pytest.approx(0.35, abs=1e-9)
    assert sigma == pytest.approx(implied_vol(price, 42, 40, -0.02, 0.75, kind=kind), abs=1e-9)


def test_source_implied_vol_reprices_in_independent_crr_tree():
    sigma = foundations.implied_vol_bisection(1.875, 21, 20, 0.1, 0.25)
    assert crr_price(21, 20, 0.1, sigma, 0.25, 1200) == pytest.approx(1.875, abs=0.002)


@pytest.mark.parametrize(
    "kind,price", [("call", 1.48), ("call", 21), ("put", -0.01), ("put", 20 * math.exp(-0.025))]
)
def test_impossible_or_infinite_volatility_quote_has_no_finite_root(kind, price):
    with pytest.raises(ValueError):
        foundations.implied_vol_bisection(price, 21, 20, 0.1, 0.25, kind=kind)


def test_zero_extrinsic_chooses_zero_volatility():
    deterministic = float(bsm.call_price(21, 20, 0.1, 0, 0.25))
    assert foundations.implied_vol_bisection(deterministic, 21, 20, 0.1, 0.25) == pytest.approx(0)


def test_expired_option_does_not_identify_volatility():
    with pytest.raises(ValueError):
        foundations.implied_vol_bisection(2, 42, 40, 0.1, 0)


def test_example_15_8_quote_units_and_independent_fraction_futures_ledger():
    pnl = foundations.quoted_futures_pnl(18.5, 19.3, 1000)
    expected = (Fraction(193, 10) - Fraction(185, 10)) * 1000
    assert pnl == pytest.approx(float(expected), abs=1e-10)
    assert pnl == pytest.approx(800, abs=1e-10)
    assert foundations.quoted_futures_pnl(18.5, 19.3, 1000, quantity=-1) == pytest.approx(
        -800, abs=1e-10
    )
    assert foundations.quoted_futures_pnl(0.185, 0.193, 100000) == pytest.approx(pnl, abs=1e-10)


@pytest.mark.parametrize("strike,sigma", [(200, 0.3), (150, 0.2)])
def test_tiny_positive_otm_price_keeps_its_volatility(strike, sigma):
    price = float(bsm.call_price(100, strike, 0.05, sigma, 0.1))
    assert 0 < price < 1e-9
    assert foundations.implied_vol_bisection(price, 100, strike, 0.05, 0.1) == pytest.approx(
        sigma, abs=1e-8
    )


@pytest.mark.parametrize(
    "kind,strike,sigma,maturity",
    [("call", 50, 0.6, 0.05), ("call", 80, 0.2, 0.05), ("put", 200, 0.6, 0.05)],
)
def test_deep_in_the_money_quote_with_small_time_value_keeps_its_volatility(
    kind, strike, sigma, maturity
):
    pricing = bsm.call_price if kind == "call" else bsm.put_price
    price = float(pricing(100, strike, 0.03, sigma, maturity))
    assert price - float(pricing(100, strike, 0.03, 0, maturity)) < 1e-6
    assert foundations.implied_vol_bisection(
        price, 100, strike, 0.03, maturity, kind=kind
    ) == pytest.approx(sigma, abs=1e-6)
