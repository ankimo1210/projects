"""Hull 17.3 carry equations; independent density, cash and PDE checks."""

import math

import pytest
from hullkit import _index_currency as index
from hullkit.bsm import call_price, put_price
from hullkit.trees import crr_price
from scipy.integrate import quad
from scipy.stats import norm


@pytest.mark.parametrize("rate,yield_rate", [(0.05, 0.03), (0.02, 0.12), (-0.01, -0.03)])
def test_prices_against_independent_lognormal_density_and_spot_transform(rate, yield_rate):
    spot, strike, sigma, time = 103, 100, 0.27, 0.8
    values = index.carry_option_details(spot, strike, rate, yield_rate, sigma, time)
    width = sigma * math.sqrt(time)
    log_mean = math.log(spot) + (rate - yield_rate - 0.5 * sigma**2) * time
    cutoff = (math.log(strike) - log_mean) / width
    for kind, a, b in [("call", cutoff, 10), ("put", -10, cutoff)]:
        sign = 1 if kind == "call" else -1
        price = (
            math.exp(-rate * time)
            * quad(
                lambda z, sign=sign: (
                    max(sign * (math.exp(log_mean + width * z) - strike), 0) * norm.pdf(z)
                ),
                a,
                b,
                epsabs=1e-10,
            )[0]
        )
        assert values[kind] == pytest.approx(price, abs=1e-10)
        function = call_price if kind == "call" else put_price
        assert values[kind] == pytest.approx(
            function(spot * math.exp(-yield_rate * time), strike, rate, sigma, time), abs=1e-10
        )
    assert values["call"] - values["put"] == pytest.approx(
        values["prepaid_spot"] - strike * values["discount"], abs=1e-11
    )


@pytest.mark.parametrize("sigma,time", [(0, 0.8), (0.27, 0)])
def test_deterministic_and_expiry_boundaries(sigma, time):
    result = index.carry_option_details(103, 100, 0.05, 0.03, sigma, time)
    forward = 103 * math.exp((0.05 - 0.03) * time)
    assert [result["call"], result["put"]] == pytest.approx(
        [
            math.exp(-0.05 * time) * max(forward - 100, 0),
            math.exp(-0.05 * time) * max(100 - forward, 0),
        ]
    )
    assert result["d1"] is None


def test_source_european_lower_upper_bounds_with_zero_strike():
    values = index.carry_option_details(103, 0, 0.05, 0.03, 0.27, 0.8)
    bounds = index.carry_bounds(103, 0, 0.05, 0.03, 0.8)
    assert values["call"] == pytest.approx(103 * math.exp(-0.03 * 0.8))
    assert [
        bounds["call_lower"],
        bounds["call_upper"],
        bounds["put_lower"],
        bounds["put_upper"],
    ] == pytest.approx([values["call"], values["call"], 0, 0])


def test_reinvested_dividend_shares_replicate_one_terminal_share():
    shares = math.exp(-0.03 * 0.8)
    # Independently compound share counts on 16 successive ex-dividend intervals.
    for _ in range(16):
        shares += shares * math.expm1(0.03 * 0.8 / 16)
    assert shares == pytest.approx(1, abs=1e-14)
    values = index.carry_option_details(103, 100, 0.05, 0.03, 0.27, 0.8)
    assert values["prepaid_spot"] == pytest.approx(103 * math.exp(-0.03 * 0.8))


@pytest.mark.parametrize("kind", ["call", "put"])
def test_source_carry_pde_against_independent_price_finite_differences(kind):
    spot, strike, rate, yield_rate, sigma, time = 103, 100, 0.05, 0.03, 0.27, 0.8

    def price(s, t):
        return index.carry_option_details(s, strike, rate, yield_rate, sigma, t)[kind]

    hs, ht = 0.01, 1e-5
    value = price(spot, time)
    delta = (price(spot + hs, time) - price(spot - hs, time)) / (2 * hs)
    gamma = (price(spot + hs, time) - 2 * value + price(spot - hs, time)) / hs**2
    calendar_theta = -(price(spot, time + ht) - price(spot, time - ht)) / (2 * ht)
    assert index.carry_pde_residual(
        spot, rate, yield_rate, sigma, value, calendar_theta, delta, gamma
    ) == pytest.approx(0, abs=2e-6)


def test_source_american_difference_interval_with_actual_tree_prices():
    for spot, yield_rate in [(80, 0.03), (120, 0.12)]:
        call = crr_price(spot, 100, 0.05, 0.27, 0.8, 500, q=yield_rate, american=True)
        put = crr_price(spot, 100, 0.05, 0.27, 0.8, 500, q=yield_rate, kind="put", american=True)
        lower, upper = index.carry_american_difference_bounds(spot, 100, 0.05, yield_rate, 0.8)
        assert lower <= call - put + 1e-10
        assert call - put <= upper + 1e-10


def test_american_source_bounds_require_nonnegative_rates_and_time_is_nonnegative():
    with pytest.raises(ValueError):
        index.carry_american_difference_bounds(100, 100, -0.01, 0.03, 1)
    with pytest.raises(ValueError):
        index.carry_option_details(100, 100, 0.05, 0.03, 0.2, -1)
