"""Tests for Black--Scholes prices, vega and implied volatility."""

import numpy as np
import pytest
from rough_volatility.black_scholes import (
    call_price,
    implied_vol,
    put_price,
    vega,
)


def test_reference_prices_and_vega() -> None:
    assert call_price(100.0, 100.0, 1.0, 0.2, 0.05) == pytest.approx(10.450583572185565, abs=1e-10)
    assert put_price(100.0, 100.0, 1.0, 0.2, 0.05) == pytest.approx(5.573526022256971, abs=1e-10)
    assert vega(100.0, 100.0, 1.0, 0.2, 0.05) == pytest.approx(37.52403469169379, abs=1e-10)


@pytest.mark.parametrize("sigma", [0.05, 0.2, 0.6, 1.0])
@pytest.mark.parametrize("log_moneyness", [-0.3, 0.0, 0.3])
def test_implied_vol_round_trip(sigma: float, log_moneyness: float) -> None:
    s, t, r = 100.0, 0.7, 0.03
    forward = s * np.exp(r * t)
    strike = forward * np.exp(log_moneyness)
    price = call_price(s, strike, t, sigma, r)
    # A 5-vol deep-ITM call has only ~2e-13 of time value in float64; the
    # inversion is necessarily ill-conditioned at that one corner.
    tolerance = 2e-5 if sigma == 0.05 and log_moneyness == -0.3 else 1e-8
    assert implied_vol(price, s, strike, t, r) == pytest.approx(sigma, abs=tolerance)


def test_invalid_no_arbitrage_bounds_return_nan() -> None:
    assert np.isnan(implied_vol(-0.1, 100.0, 100.0, 1.0))
    assert np.isnan(implied_vol(100.0, 100.0, 100.0, 1.0))
    assert np.isnan(implied_vol(19.9, 100.0, 80.0, 1.0))
    assert implied_vol(20.0, 100.0, 80.0, 1.0) == 0.0


def test_expiry_and_zero_volatility_limits() -> None:
    assert call_price(100.0, 90.0, 0.0, 0.2) == 10.0
    assert put_price(100.0, 110.0, 0.0, 0.2) == 10.0
    assert vega(100.0, 100.0, 0.0, 0.2) == 0.0
    assert call_price(100.0, 110.0, 1.0, 0.0) == 0.0
    assert implied_vol(10.0, 100.0, 90.0, 0.0) == 0.0


def test_prices_vectorize_and_satisfy_put_call_parity() -> None:
    strikes = np.array([80.0, 100.0, 120.0])
    calls = call_price(100.0, strikes, 0.5, 0.25, 0.02)
    puts = put_price(100.0, strikes, 0.5, 0.25, 0.02)
    np.testing.assert_allclose(calls - puts, 100.0 - strikes * np.exp(-0.02 * 0.5), atol=1e-12)
