"""Hull 20.1: European parity IV, quote rounding and identification bounds."""

import math

import pytest
from hullkit import _smile_surface as smile
from scipy.integrate import quad
from scipy.stats import norm


def density_price(spot, strike, rate, yield_rate, sigma, time, kind):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-14,
        )[0]
    )


def test_example_20_1_put_parity_and_145_percent_iv():
    result = smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, 0.0236)
    assert result["parity_put"] == pytest.approx(0.0419, abs=0.00005)
    assert result["call_iv"] == pytest.approx(0.145, abs=0.0005)
    assert result["call_iv"] == pytest.approx(0.14511006, abs=5e-9)
    assert result["put_iv"] == pytest.approx(result["call_iv"], abs=1e-11)
    assert result["parity_residual"] == pytest.approx(0, abs=1e-15)


def test_implied_vol_against_independent_payoff_quadrature_and_bisection():
    low, high = 0.05, 0.3
    for _ in range(36):
        mid = (low + high) / 2
        if density_price(0.60, 0.59, 0.05, 0.10, mid, 1, "call") > 0.0236:
            high = mid
        else:
            low = mid
    result = smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, 0.0236)
    assert result["call_iv"] == pytest.approx((low + high) / 2, abs=1e-11)


@pytest.mark.parametrize("trial_vol", [0.10, 0.22, 0.30])
def test_equation_20_2_equal_dollar_errors_when_market_prices_obey_parity(trial_vol):
    result = smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, 0.0236)
    call = density_price(0.60, 0.59, 0.05, 0.10, trial_vol, 1, "call")
    put = density_price(0.60, 0.59, 0.05, 0.10, trial_vol, 1, "put")
    assert call - 0.0236 == pytest.approx(put - result["parity_put"], abs=1e-12)


def test_rounded_printed_put_quote_does_not_force_equal_implied_vols():
    result = smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, 0.0236, put_price=0.0419)
    assert result["parity_residual"] == pytest.approx(0.0419 - result["parity_put"], abs=1e-15)
    assert abs(result["call_iv"] - result["put_iv"]) > 1e-5
    assert result["put_iv"] == pytest.approx(0.145, abs=0.0005)


def test_exact_deterministic_lower_bound_selects_zero_iv():
    result = smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, 0)
    assert result["call_iv"] == pytest.approx(0, abs=1e-15)
    assert result["put_iv"] == pytest.approx(0, abs=1e-15)


def test_tiny_positive_otm_price_is_not_erased_by_absolute_price_tolerance():
    price = density_price(100, 200, 0.03, 0.01, 0.08, 1, "call")
    assert 0 < price < 1e-10
    result = smile.parity_iv_details(100, 200, 0.03, 0.01, 1, price)
    assert result["call_iv"] == pytest.approx(0.08, abs=1e-9)


@pytest.mark.parametrize("call_price", [-0.01, 0.60 * math.exp(-0.10)])
def test_quotes_outside_finite_iv_arbitrage_bounds_are_rejected(call_price):
    with pytest.raises(ValueError):
        smile.parity_iv_details(0.60, 0.59, 0.05, 0.10, 1, call_price)
