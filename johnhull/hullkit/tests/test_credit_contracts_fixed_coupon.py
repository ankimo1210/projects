"""Hull Example25.1: unrounded 365/360 conversion and upfront cashflow direction."""

import math

import pytest
from hullkit import _credit_contracts as c


def test_source_example_25_1_all_five_values():
    result = c.fixed_coupon_quote(0.0034, 0.004, 0.4, 0.04, 5)
    assert result["annual_spread"] * 100 == pytest.approx(0.345, abs=0.0005)
    assert result["annual_coupon"] * 100 == pytest.approx(0.406, abs=0.0005)
    assert result["hazard"] * 100 == pytest.approx(0.5717, abs=0.00005)
    assert result["risky_duration"] == pytest.approx(4.447, abs=0.0005)
    assert result["price_per_100"] == pytest.approx(100.27, abs=0.005)
    assert result["buyer_upfront"] < 0


def test_upfront_plus_independent_state_cashflows_has_zero_npv():
    result = c.fixed_coupon_quote(0.0034, 0.004, 0.4, 0.04, 5, notional=125e6)
    hazard, coupon = result["hazard"], result["annual_coupon"]
    future = 0
    for period in range(1, 21):
        time = period / 4
        mid = time - 0.125
        pd = math.exp(-hazard * (time - 0.25)) - math.exp(-hazard * time)
        previous_premiums = sum(coupon * 0.25 * math.exp(-0.04 * j / 4) for j in range(1, period))
        default_cash = (0.6 - coupon * 0.125) * math.exp(-0.04 * mid) - previous_premiums
        future += pd * default_cash
    future -= math.exp(-hazard * 5) * sum(
        coupon * 0.25 * math.exp(-0.04 * j / 4) for j in range(1, 21)
    )
    assert future * 125e6 - result["buyer_upfront"] == pytest.approx(0, abs=1e-7)


def test_equal_coupon_and_spread_zero_upfront_and_direction_reversal():
    equal = c.fixed_coupon_quote(0.01, 0.01, 0.4, 0.04, 5, quote_basis="year")
    high = c.fixed_coupon_quote(0.02, 0.01, 0.4, 0.04, 5, quote_basis="year")
    low = c.fixed_coupon_quote(0.005, 0.01, 0.4, 0.04, 5, quote_basis="year")
    assert equal["price_per_100"] == pytest.approx(100)
    assert equal["buyer_upfront"] == pytest.approx(0)
    assert high["buyer_upfront"] > 0 > low["buyer_upfront"]
