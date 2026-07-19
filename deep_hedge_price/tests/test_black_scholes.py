from __future__ import annotations

import numpy as np

from deep_hedge_price.black_scholes import (
    call_delta,
    call_gamma,
    call_price,
    call_rho,
    call_theta,
    call_vega,
)


def test_known_reference_values():
    price = call_price(100.0, 100.0, 1.0, 0.05, 0.20)
    delta = call_delta(100.0, 100.0, 1.0, 0.05, 0.20)
    assert np.isclose(price, 10.450583572185565, atol=1e-10)
    assert np.isclose(delta, 0.6368306511756191, atol=1e-10)


def test_price_bounds_and_delta_bounds():
    spots = np.linspace(50, 150, 101)
    price = call_price(spots, 100, 0.5, 0.02, 0.3)
    delta = call_delta(spots, 100, 0.5, 0.02, 0.3)
    lower = np.maximum(spots - 100 * np.exp(-0.02 * 0.5), 0)
    assert np.all(price >= lower - 1e-12)
    assert np.all(price <= spots + 1e-12)
    assert np.all((delta >= 0) & (delta <= 1))


def test_expiry_behavior():
    spots = np.array([90.0, 100.0, 110.0])
    assert np.array_equal(call_price(spots, 100, 0.0, 0.01, 0.2), [0, 0, 10])
    assert np.array_equal(call_delta(spots, 100, 0.0, 0.01, 0.2), [0, 0.5, 1])


def test_dividend_and_greeks_match_finite_differences():
    args = (105.0, 100.0, 0.8, 0.03, 0.27, 0.02)
    spot, strike, maturity, rate, sigma, dividend = args
    h = 1e-4
    delta_fd = (
        call_price(spot + h, strike, maturity, rate, sigma, dividend)
        - call_price(spot - h, strike, maturity, rate, sigma, dividend)
    ) / (2 * h)
    gamma_fd = (
        call_price(spot + h, strike, maturity, rate, sigma, dividend)
        - 2 * call_price(*args)
        + call_price(spot - h, strike, maturity, rate, sigma, dividend)
    ) / h**2
    vega_fd = (
        call_price(spot, strike, maturity, rate, sigma + h, dividend)
        - call_price(spot, strike, maturity, rate, sigma - h, dividend)
    ) / (2 * h)
    rho_fd = (
        call_price(spot, strike, maturity, rate + h, sigma, dividend)
        - call_price(spot, strike, maturity, rate - h, sigma, dividend)
    ) / (2 * h)
    theta_fd = -(
        call_price(spot, strike, maturity + h, rate, sigma, dividend)
        - call_price(spot, strike, maturity - h, rate, sigma, dividend)
    ) / (2 * h)
    np.testing.assert_allclose(call_delta(*args), delta_fd, rtol=0, atol=1e-7)
    assert np.isclose(call_gamma(*args), gamma_fd, atol=1e-6)
    assert np.isclose(call_vega(*args), vega_fd, atol=1e-6)
    assert np.isclose(call_rho(*args), rho_fd, atol=1e-6)
    assert np.isclose(call_theta(*args), theta_fd, atol=1e-6)


def test_zero_volatility_limit_is_finite():
    price = call_price(np.array([90.0, 110.0]), 100.0, 1.0, 0.03, 0.0, 0.01)
    assert np.all(np.isfinite(price))
    assert np.all(np.isfinite(call_delta(np.array([90.0, 110.0]), 100.0, 1.0, 0.03, 0.0, 0.01)))
    assert np.array_equal(call_gamma(np.array([90.0, 110.0]), 100.0, 1.0, 0.03, 0.0, 0.01), [0, 0])
