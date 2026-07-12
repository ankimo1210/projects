from __future__ import annotations

import numpy as np

from deep_hedge_price.black_scholes import call_delta, call_price


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
