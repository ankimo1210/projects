"""Hull 17.2: currency amounts, bounded conversion and zero-cost collar."""

import math
from fractions import Fraction

import pytest
from hullkit import _index_currency as index
from scipy.integrate import quad
from scipy.stats import norm


def test_source_currency_call_and_put_cash():
    assert index.currency_option_cash(1.15, 1.10, 1000000, kind="call") == pytest.approx(50000)
    assert index.currency_option_cash(0.67, 0.70, 10000000, kind="put") == pytest.approx(300000)


@pytest.mark.parametrize("exposure", ["receive", "pay"])
def test_three_regions_against_independent_fraction_cash_ledger(exposure):
    low, high, amount = Fraction(13, 10), Fraction(13414, 10000), 1000000
    sign = 1 if exposure == "receive" else -1
    for spot in [Fraction(12, 10), low, Fraction(132, 100), high, Fraction(15, 10)]:
        put = max(low - spot, 0) * amount
        call = max(spot - high, 0) * amount
        expected = sign * (amount * spot + put - call)
        cash = index.range_forward_cash(
            float(spot), float(low), float(high), amount, exposure=exposure
        )
        assert cash["cash"] == pytest.approx(float(expected))
        assert cash["derivatives"] == pytest.approx(float(sign * (put - call)))
        assert cash["effective_rate"] == pytest.approx(float(min(max(spot, low), high)))


def test_equal_strikes_give_source_forward_receipt_1320000():
    for spot in [0.8, 1.32, 2]:
        cash = index.range_forward_cash(spot, 1.32, 1.32, 1000000)
        assert cash["cash"] == pytest.approx(1320000)


def test_printed_rounded_range_prices_and_nonzero_residual():
    prices = index.range_forward_prices(1.32, 1.3000, 1.3414, 0.02, 0.02, 0.14, 0.25)
    assert prices["put"] == pytest.approx(0.027304826, abs=5e-10)
    assert prices["call"] == pytest.approx(0.027292496, abs=5e-10)
    assert prices["premium"] == pytest.approx(0.000012329, abs=1e-9)
    assert prices["put"] == pytest.approx(0.0273, abs=5e-5)
    assert prices["call"] == pytest.approx(0.0273, abs=5e-5)


def test_zero_cost_upper_strike_prices_against_independent_payoff_integration():
    result = index.zero_cost_range_forward(1.32, 1.3, 0.02, 0.02, 0.14, 0.25)
    assert result["upper_strike"] == pytest.approx(1.3414, abs=5e-5)
    width = 0.14 * math.sqrt(0.25)

    def payoff(z, strike, call):
        terminal = 1.32 * math.exp(-0.5 * width**2 + width * z)
        return max(terminal - strike if call else strike - terminal, 0) * norm.pdf(z)

    put = quad(
        payoff, -10, math.log(1.3 / 1.32) / width + 0.5 * width, args=(1.3, False), epsabs=1e-12
    )[0] * math.exp(-0.02 * 0.25)
    call = quad(
        payoff,
        math.log(result["upper_strike"] / 1.32) / width + 0.5 * width,
        10,
        args=(result["upper_strike"], True),
        epsabs=1e-12,
    )[0] * math.exp(-0.02 * 0.25)
    assert [result["put"], result["call"]] == pytest.approx([put, call], abs=2e-12)
    assert put == pytest.approx(call, abs=2e-12)


@pytest.mark.parametrize(
    "rate,yield_rate,time", [(0, 0, 1), (0.03, 0.01, 0.5), (0.05, 0.03, 0.8), (-0.02, 0.03, 1)]
)
def test_zero_cost_at_forward_collapses_to_single_strike(rate, yield_rate, time):
    forward = 1.32 * math.exp((rate - yield_rate) * time)
    result = index.zero_cost_range_forward(1.32, forward, rate, yield_rate, 0.2, time)
    assert result["upper_strike"] == pytest.approx(forward, abs=1e-12)


def test_mathematically_infeasible_ordered_collar_and_reversed_strikes():
    with pytest.raises(ValueError):
        index.zero_cost_range_forward(1.32, 1.4, 0.02, 0.02, 0.14, 0.25)
    with pytest.raises(ValueError):
        index.range_forward_cash(1.32, 1.4, 1.3, 1000000)


def test_zero_cost_range_forward_uses_domestic_discounting_and_foreign_carry():
    # Distinct rates: swapping r and rf moves the upper strike from 1.3691 to 1.3142.
    spot, lower, r, rf, sigma, t = 1.32, 1.30, 0.05, 0.01, 0.14, 0.25

    def gk(strike, sign):
        d1 = (math.log(spot / strike) + (r - rf + sigma**2 / 2) * t) / (sigma * math.sqrt(t))
        d2 = d1 - sigma * math.sqrt(t)
        return sign * (
            spot * math.exp(-rf * t) * norm.cdf(sign * d1)
            - strike * math.exp(-r * t) * norm.cdf(sign * d2)
        )

    from scipy.optimize import brentq

    upper = brentq(lambda k: gk(k, 1) - gk(lower, -1), lower, 3 * spot, xtol=1e-14)
    assert index.zero_cost_range_forward(spot, lower, r, rf, sigma, t)[
        "upper_strike"
    ] == pytest.approx(upper, abs=1e-10)
    assert upper == pytest.approx(1.3691, abs=5e-5)
