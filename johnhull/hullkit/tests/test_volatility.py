"""Tests for hullkit.volatility against Hull 11e Ch.20/23 values."""

import numpy as np
import pytest
from hullkit import bsm, volatility


def test_implied_vol_round_trip_and_parity_equality():
    S, K, r, T, q = 100.0, 105.0, 0.04, 0.75, 0.01
    sigma_true = 0.27
    c = bsm.call_price(S, K, r, sigma_true, T, q)
    p = bsm.put_price(S, K, r, sigma_true, T, q)
    iv_c = volatility.implied_vol(c, S, K, r, T, q, kind="call")
    iv_p = volatility.implied_vol(p, S, K, r, T, q, kind="put")
    assert iv_c == pytest.approx(sigma_true, abs=1e-8)
    assert iv_p == pytest.approx(iv_c, abs=1e-8)  # parity -> identical IV


def test_implied_vol_bounds_and_kind_errors():
    with pytest.raises(ValueError):
        volatility.implied_vol(200.0, 100.0, 100.0, 0.05, 1.0)  # price > S
    with pytest.raises(ValueError):
        volatility.implied_vol(5.0, 100.0, 100.0, 0.05, 1.0, kind="cal")


def test_ewma_update_hull_example():
    # Hull GE Example 23.1 (lambda=0.90): sigma_{n-1}=1%/day, u_{n-1}=2%
    # -> 0.90*0.0001 + 0.10*0.0004 = 0.00013
    var = volatility.ewma_variance([0.02, 0.0], lam=0.90, init=0.0001)
    assert var[1] == pytest.approx(0.00013, abs=1e-12)
    assert np.sqrt(var[1]) == pytest.approx(0.011402, abs=1e-6)  # Hull 1.14%


def test_garch_update_and_long_run_hull_example():
    omega, alpha, beta = 2e-6, 0.13, 0.86
    var = volatility.garch11_variance([0.01, 0.0], omega, alpha, beta, init=0.016**2)
    assert var[1] == pytest.approx(0.00023516, abs=1e-10)
    assert np.sqrt(var[1]) == pytest.approx(0.015335, abs=1e-5)  # Hull 1.53%
    v_l = volatility.garch11_long_run(omega, alpha, beta)
    assert v_l == pytest.approx(0.0002, abs=1e-12)
    assert np.sqrt(v_l) == pytest.approx(0.014142, abs=1e-6)  # Hull 1.4%
    with pytest.raises(ValueError):
        volatility.garch11_long_run(1e-6, 0.5, 0.5)


def test_garch_forecast_hull_eq_23_13():
    omega, alpha, beta = 2e-6, 0.13, 0.86
    f10 = volatility.garch11_forecast(0.016**2, 10, omega, alpha, beta)
    assert f10 == pytest.approx(2.50645e-4, abs=2e-8)
    f_inf = volatility.garch11_forecast(0.016**2, 10_000, omega, alpha, beta)
    assert f_inf == pytest.approx(0.0002, abs=1e-9)


def test_ewma_variance_empty_raises():
    with pytest.raises(ValueError, match="non-empty"):
        volatility.ewma_variance([])


def test_garch11_variance_empty_raises():
    with pytest.raises(ValueError, match="non-empty"):
        volatility.garch11_variance([], 2e-6, 0.1, 0.85)


def test_garch11_fit_returns_python_floats():
    rng = np.random.default_rng(42)
    u = rng.standard_normal(500) * 0.01
    result = volatility.garch11_fit(u)
    assert len(result) == 3
    assert all(isinstance(x, float) for x in result), f"not all float: {[type(x) for x in result]}"


def test_garch_fit_recovers_persistence():
    rng = np.random.default_rng(0)
    omega_t, alpha_t, beta_t = 2e-6, 0.10, 0.85
    n = 4000
    u = np.empty(n)
    var = omega_t / (1.0 - alpha_t - beta_t)
    for i in range(n):
        u[i] = np.sqrt(var) * rng.standard_normal()
        var = omega_t + alpha_t * u[i] ** 2 + beta_t * var
    _omega_h, alpha_h, beta_h = volatility.garch11_fit(u)
    assert alpha_h + beta_h == pytest.approx(alpha_t + beta_t, abs=0.05)
    assert alpha_h == pytest.approx(alpha_t, abs=0.05)


def test_ewma_covariance_matches_manual_loop():
    rng = np.random.default_rng(70)
    x = 0.01 * rng.standard_normal(300)
    y = 0.01 * rng.standard_normal(300)
    cov = volatility.ewma_covariance(x, y, lam=0.94)
    # manual reference
    ref = np.empty_like(x)
    ref[0] = x[0] * y[0]
    for i in range(1, x.size):
        ref[i] = 0.94 * ref[i - 1] + 0.06 * x[i - 1] * y[i - 1]
    assert np.allclose(cov, ref)
    # correlation in [-1, 1]
    vx = volatility.ewma_variance(x, lam=0.94)
    vy = volatility.ewma_variance(y, lam=0.94)
    rho = cov[10:] / np.sqrt(vx[10:] * vy[10:])
    assert np.all(np.abs(rho) <= 1.0 + 1e-9)


def test_ewma_covariance_validation():
    with pytest.raises(ValueError):
        volatility.ewma_covariance([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        volatility.ewma_covariance([], [])


# ---------------------------------------------------------------------------
# VN-02: Breeden-Litzenberger density and the §20.4 smile axes
# ---------------------------------------------------------------------------


def _example_20a_1_density():
    """Example 20A.1 inputs, as in test_hull_pins_vol_var.py (GE p.468)."""
    S0, r, T = 10.0, 0.03, 0.25
    quoted_strikes = np.arange(6.0, 14.01, 1.0)
    quoted_vols = np.arange(0.30, 0.219, -0.01)
    grid = np.arange(6.0, 14.01, 0.5)  # delta = 0.5
    vols = np.interp(grid, quoted_strikes, quoted_vols)
    calls = bsm.call_price(S0, grid, r, vols, T)
    return grid, calls, volatility.breeden_litzenberger_density(grid, calls, r, T)


def test_breeden_litzenberger_example_20a_1_hull_ge():
    """Hull 11e GE Appendix 20A pp.468-469, Example 20A.1 via the hullkit function.

    g1..g8 at K = 6.5, 7.5, ..., 13.5 print as 0.0057, 0.0444, 0.1545, 0.2781,
    0.2813, 0.1659, 0.0573, 0.0113 (abs 5e-5); the area under the unit-width
    histogram prints as 0.9985 (computed 0.99847, abs 5e-5). The function must
    also equal eq. (20A.2) applied by hand to the three legs at K = 6.5.
    """
    grid, calls, (interior, density) = _example_20a_1_density()
    np.testing.assert_allclose(interior, grid[1:-1])
    g = density[::2]
    np.testing.assert_allclose(interior[::2], np.arange(6.5, 13.51, 1.0))
    printed = [0.0057, 0.0444, 0.1545, 0.2781, 0.2813, 0.1659, 0.0573, 0.0113]
    np.testing.assert_allclose(g, printed, rtol=0, atol=5e-5)
    assert g.sum() == pytest.approx(0.9985, abs=5e-5)

    c1, c2, c3 = calls[:3]
    assert (c1, c2, c3) == pytest.approx((4.045, 3.549, 3.055), abs=5e-4)
    by_hand = np.exp(0.03 * 0.25) * (c1 + c3 - 2.0 * c2) / 0.5**2
    assert g[0] == pytest.approx(by_hand, abs=1e-15)


def test_breeden_litzenberger_flat_vol_recovers_lognormal():
    """Constant sigma: eq. (20A.2) must return the lognormal density of S_T.

    S0 = 100, r = 3%, sigma = 22%, T = 0.5 on K = 40..180. ln S_T ~
    N(ln S0 + (r - sigma^2/2)T, sigma^2 T) (Hull §15.1). The butterfly has
    O(delta^2) truncation error, so the stated tolerance is
    max|g - lognormal pdf| <= 4e-4 x delta^2 x peak pdf (peak 0.02588) over
    the whole interior grid. Computed: 3.72e-4 x peak at delta = 1.0 and
    9.31e-5 x peak at delta = 0.5; halving delta cuts the error by 3.99
    (asserted in [3.5, 4.5]). The grid mass sums to 1 within 1e-3 (the
    lognormal mass outside [40, 180] is 8.5e-5).
    """
    from scipy.stats import lognorm

    S0, r, sigma, T = 100.0, 0.03, 0.22, 0.5
    reference = lognorm(s=sigma * np.sqrt(T), scale=S0 * np.exp((r - 0.5 * sigma**2) * T))

    errors = {}
    for delta in (1.0, 0.5):
        grid = np.arange(40.0, 180.0 + delta / 2, delta)
        calls = bsm.call_price(S0, grid, r, sigma, T)
        interior, density = volatility.breeden_litzenberger_density(grid, calls, r, T)
        exact = reference.pdf(interior)
        errors[delta] = float(np.max(np.abs(density - exact)))
        assert errors[delta] <= 4e-4 * delta**2 * exact.max()
        assert density.sum() * delta == pytest.approx(1.0, abs=1e-3)
    assert 3.5 <= errors[1.0] / errors[0.5] <= 4.5


def test_breeden_litzenberger_validation():
    grid = np.array([1.0, 2.0, 3.0, 4.0])
    calls = np.array([3.0, 2.0, 1.1, 0.4])
    with pytest.raises(ValueError, match="equal length"):
        volatility.breeden_litzenberger_density(grid, calls[:3], 0.0, 1.0)
    with pytest.raises(ValueError, match="at least 3 strikes"):
        volatility.breeden_litzenberger_density(grid[:2], calls[:2], 0.0, 1.0)
    with pytest.raises(ValueError, match="equally spaced"):
        volatility.breeden_litzenberger_density([1.0, 2.0, 3.5, 4.0], calls, 0.0, 1.0)
    with pytest.raises(ValueError, match="equally spaced"):
        volatility.breeden_litzenberger_density(grid[::-1], calls, 0.0, 1.0)
    with pytest.raises(ValueError, match="finite"):
        volatility.breeden_litzenberger_density(grid, [3.0, np.nan, 1.1, 0.4], 0.0, 1.0)
    with pytest.raises(ValueError, match="T must be a finite scalar >= 0"):
        volatility.breeden_litzenberger_density(grid, calls, 0.0, -1.0)
    # A butterfly-arbitrage strip is reported, not repaired.
    _, density = volatility.breeden_litzenberger_density(grid, [3.0, 2.0, 1.2, 0.2], 0.0, 1.0)
    assert density[1] < 0.0


def test_forward_moneyness_axis_hull_ge():
    """Hull 11e GE §20.4 p.458: K/F0 with F0 = S0 e^{(r-q)T}; K = F0 is ATM."""
    S0, r, q, T = 100.0, 0.05, 0.02, 2.0
    F0 = S0 * np.exp((r - q) * T)
    assert volatility.forward_moneyness(F0, S0, r, T, q) == pytest.approx(1.0, abs=1e-15)
    strikes = np.array([80.0, 100.0, 125.0])
    m = volatility.forward_moneyness(strikes, S0, r, T, q)
    np.testing.assert_allclose(m, strikes / F0, rtol=1e-15)
    np.testing.assert_allclose(
        volatility.strike_from_forward_moneyness(m, S0, r, T, q), strikes, rtol=1e-14
    )
    with pytest.raises(ValueError, match="moneyness must contain only finite values > 0"):
        volatility.strike_from_forward_moneyness(-1.0, S0, r, T)
    with pytest.raises(ValueError, match="K must contain only finite values > 0"):
        volatility.forward_moneyness(0.0, S0, r, T)


def test_delta_axis_round_trip_and_50_delta_hull_ge():
    """Hull 11e GE §20.4 p.458: the smile on the delta axis; 50-delta is ATM.

    Each strike carries its own implied vol. With q = 0 a 0.5 call delta means
    N(d1) = 0.5, i.e. d1 = 0 and K = F0 e^{sigma^2 T / 2}; the -0.5 put delta
    lands on the same strike.
    """
    S0, r, T = 100.0, 0.03, 0.5
    strikes = np.array([70.0, 90.0, 100.0, 110.0, 130.0])
    vols = 0.22 - 0.25 * np.log(strikes / S0) + 0.20 * np.log(strikes / S0) ** 2
    for kind in ("call", "put"):
        deltas = volatility.delta_from_strike(strikes, S0, r, vols, T, kind=kind)
        back = volatility.strike_from_delta(deltas, S0, r, vols, T, kind=kind)
        np.testing.assert_allclose(back, strikes, rtol=1e-10)
    call_deltas = volatility.delta_from_strike(strikes, S0, r, vols, T)
    np.testing.assert_allclose(call_deltas, bsm.call_delta(S0, strikes, r, vols, T), rtol=1e-15)
    assert np.all(np.diff(call_deltas) < 0.0)

    sigma = 0.22
    atm = S0 * np.exp(r * T) * np.exp(0.5 * sigma**2 * T)
    assert volatility.strike_from_delta(0.5, S0, r, sigma, T) == pytest.approx(atm, rel=1e-14)
    assert volatility.strike_from_delta(-0.5, S0, r, sigma, T, kind="put") == pytest.approx(
        atm, rel=1e-14
    )
    # With a yield the round trip still holds.
    k_q = volatility.strike_from_delta(0.25, S0, r, sigma, T, q=0.04)
    assert bsm.call_delta(S0, k_q, r, sigma, T, q=0.04) == pytest.approx(0.25, abs=1e-14)


def test_delta_axis_validation():
    with pytest.raises(ValueError, match=r"call delta must satisfy 0 < delta < e\^\{-qT\}"):
        volatility.strike_from_delta(1.0, 100.0, 0.03, 0.2, 0.5)
    with pytest.raises(ValueError, match=r"put delta must satisfy -e\^\{-qT\} < delta < 0"):
        volatility.strike_from_delta(0.3, 100.0, 0.03, 0.2, 0.5, kind="put")
    with pytest.raises(ValueError, match="sigma > 0 and T > 0"):
        volatility.strike_from_delta(0.3, 100.0, 0.03, 0.0, 0.5)
    with pytest.raises(ValueError, match="kind must be"):
        volatility.delta_from_strike(100.0, 100.0, 0.03, 0.2, 0.5, kind="straddle")
