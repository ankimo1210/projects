"""Tests for hullkit.bsm against Hull 11e textbook values."""

import math

import numpy as np
import pytest
from hullkit import bsm

# Hull Example 15.6: S=42, K=40, r=10%, sigma=20%, T=0.5
EX156 = dict(S=42.0, K=40.0, r=0.10, sigma=0.20, T=0.5)


def test_d1_d2_example_15_6():
    assert bsm.d1(**EX156) == pytest.approx(0.7693, abs=1e-4)
    assert bsm.d2(**EX156) == pytest.approx(0.6278, abs=1e-4)


def test_call_put_example_15_6():
    assert bsm.call_price(**EX156) == pytest.approx(4.76, abs=1e-2)
    assert bsm.put_price(**EX156) == pytest.approx(0.81, abs=1e-2)


def test_atm_call_reference():
    # Convergence target used by the notebook: ATM 1y call = 10.4506
    assert bsm.call_price(100, 100, 0.05, 0.20, 1.0) == pytest.approx(10.4506, abs=1e-4)


def test_put_call_parity_with_yield():
    # c - p = S e^{-qT} - K e^{-rT}  (Hull eq. 17.3)
    S, K, r, sigma, T, q = 105.0, 100.0, 0.04, 0.3, 0.75, 0.02
    c = bsm.call_price(S, K, r, sigma, T, q)
    p = bsm.put_price(S, K, r, sigma, T, q)
    lhs = c - p
    rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    assert lhs == pytest.approx(rhs, abs=1e-10)


def test_deltas():
    # Call delta in (0,1), put delta in (-1,0), call - put = e^{-qT}
    S, K, r, sigma, T, q = 100.0, 100.0, 0.05, 0.2, 1.0, 0.03
    dc = bsm.call_delta(S, K, r, sigma, T, q)
    dp = bsm.put_delta(S, K, r, sigma, T, q)
    assert 0.0 < dc < 1.0
    assert -1.0 < dp < 0.0
    assert dc - dp == pytest.approx(math.exp(-q * T), abs=1e-12)
    # Hull Ex 19.1: S=49, K=50, r=5%, sigma=20%, T=0.3846 -> delta = 0.522
    assert bsm.call_delta(49.0, 50.0, 0.05, 0.20, 0.3846) == pytest.approx(0.522, abs=1e-3)


def test_vectorized_over_spot_array():
    import numpy as np

    S = np.array([80.0, 100.0, 120.0])
    K, r, sigma, T = 100.0, 0.05, 0.2, 1.0
    vec = bsm.call_price(S, K, r, sigma, T)
    assert vec.shape == (3,)
    scal = np.array([bsm.call_price(float(s), K, r, sigma, T) for s in S])
    assert np.allclose(vec, scal, atol=1e-12)
    # a Greek too
    g = bsm.gamma(S, K, r, sigma, T)
    assert g.shape == (3,) and np.all(g > 0.0)


def test_expiry_returns_intrinsic_value_including_atm():
    import numpy as np

    spots = np.array([80.0, 100.0, 120.0])
    assert np.array_equal(bsm.call_price(spots, 100.0, 0.05, 0.2, 0.0), [0.0, 0.0, 20.0])
    assert np.array_equal(bsm.put_price(spots, 100.0, 0.05, 0.2, 0.0), [20.0, 0.0, 0.0])


def test_zero_volatility_uses_deterministic_terminal_value():
    call = bsm.call_price(100.0, 100.0, 0.05, 0.0, 1.0)
    put = bsm.put_price(100.0, 100.0, 0.05, 0.0, 1.0)
    assert call == pytest.approx(100.0 - 100.0 * math.exp(-0.05), abs=1e-12)
    assert put == 0.0


@pytest.mark.parametrize(("sigma", "T"), [(0.2, 0.0), (0.0, 1.0), (-0.2, 1.0), (0.2, -1.0)])
def test_d1_rejects_undefined_or_invalid_domain(sigma, T):
    with pytest.raises(ValueError):
        bsm.d1(100.0, 100.0, 0.05, sigma, T)


# --- mixed boundary vectors --------------------------------------------


def test_call_price_mixed_maturity_vector():
    """T=[0, 1] must price element-wise: intrinsic at expiry, BSM elsewhere."""
    prices = bsm.call_price(100.0, 95.0, 0.05, 0.2, np.array([0.0, 1.0]))
    assert prices[0] == pytest.approx(5.0)
    assert prices[1] == pytest.approx(bsm.call_price(100.0, 95.0, 0.05, 0.2, 1.0))


def test_put_price_mixed_maturity_vector():
    prices = bsm.put_price(100.0, 105.0, 0.05, 0.2, np.array([0.0, 1.0]))
    assert prices[0] == pytest.approx(5.0)
    assert prices[1] == pytest.approx(bsm.put_price(100.0, 105.0, 0.05, 0.2, 1.0))


def test_call_price_mixed_volatility_vector():
    """sigma=[0, 0.2] must use the discounted deterministic payoff at sigma=0."""
    prices = bsm.call_price(100.0, 90.0, 0.05, np.array([0.0, 0.2]), 1.0)
    expected_zero_vol = max(100.0 - 90.0 * math.exp(-0.05), 0.0)
    assert prices[0] == pytest.approx(expected_zero_vol)
    assert prices[1] == pytest.approx(bsm.call_price(100.0, 90.0, 0.05, 0.2, 1.0))


def test_put_price_mixed_volatility_vector():
    prices = bsm.put_price(100.0, 110.0, 0.05, np.array([0.0, 0.2]), 1.0)
    expected_zero_vol = max(110.0 * math.exp(-0.05) - 100.0, 0.0)
    assert prices[0] == pytest.approx(expected_zero_vol)
    assert prices[1] == pytest.approx(bsm.put_price(100.0, 110.0, 0.05, 0.2, 1.0))


def test_price_broadcasts_spot_strike_and_maturity():
    """A surface built by broadcasting S, K and T must match element-wise pricing."""
    spots = np.array([[90.0], [110.0]])
    maturities = np.array([0.0, 0.5, 1.0])
    surface = bsm.call_price(spots, 100.0, 0.03, 0.25, maturities)
    assert surface.shape == (2, 3)
    for i, spot in enumerate([90.0, 110.0]):
        for j, maturity in enumerate(maturities):
            assert surface[i, j] == pytest.approx(
                bsm.call_price(spot, 100.0, 0.03, 0.25, maturity)
            )


def test_mixed_boundary_put_call_parity_in_diffusive_region():
    spots = np.array([95.0, 100.0, 105.0])
    maturities = np.array([0.25, 0.5, 1.0])
    call = bsm.call_price(spots, 100.0, 0.04, 0.2, maturities, q=0.01)
    put = bsm.put_price(spots, 100.0, 0.04, 0.2, maturities, q=0.01)
    parity = spots * np.exp(-0.01 * maturities) - 100.0 * np.exp(-0.04 * maturities)
    np.testing.assert_allclose(call - put, parity, rtol=1e-12, atol=1e-12)


def test_scalar_price_still_returns_scalar():
    price = bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)
    assert np.ndim(price) == 0
    assert float(price) == pytest.approx(10.450583572185565, rel=1e-12)
