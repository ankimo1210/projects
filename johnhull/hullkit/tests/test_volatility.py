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
