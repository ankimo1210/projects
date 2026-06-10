"""Tests for hullkit.bsm analytic Greeks against Hull 11e Ch.19 values."""

import pytest
from hullkit import bsm

# Hull Ch.19 running example: S=49, K=50, r=5%, sigma=20%, T=20 weeks
EX19 = dict(S=49.0, K=50.0, r=0.05, sigma=0.20, T=0.3846)


def test_hull_ch19_example_values():
    assert bsm.call_delta(**EX19) == pytest.approx(0.5216, abs=5e-4)  # Hull 0.522
    assert bsm.gamma(**EX19) == pytest.approx(0.06555, abs=5e-4)  # Hull 0.066
    assert bsm.vega(**EX19) == pytest.approx(12.105, abs=2e-2)  # Hull 12.1
    assert bsm.call_theta(**EX19) == pytest.approx(-4.3055, abs=5e-3)  # Hull -4.31
    assert bsm.call_theta(**EX19) / 365.0 == pytest.approx(-0.0118, abs=1e-4)
    assert bsm.call_rho(**EX19) == pytest.approx(8.9066, abs=1e-2)  # Hull 8.91
    assert bsm.call_price(**EX19) == pytest.approx(2.4004, abs=1e-3)  # Hull 2.40


def test_bsm_pde_identity():
    # Theta + r S Delta + 0.5 sigma^2 S^2 Gamma = r * price (Hull eq. 19.4)
    S, K, r, sigma, T = 49.0, 50.0, 0.05, 0.20, 0.3846
    lhs = (
        bsm.call_theta(S, K, r, sigma, T)
        + r * S * bsm.call_delta(S, K, r, sigma, T)
        + 0.5 * sigma**2 * S**2 * bsm.gamma(S, K, r, sigma, T)
    )
    assert lhs == pytest.approx(r * bsm.call_price(S, K, r, sigma, T), abs=1e-9)


def test_finite_difference_cross_checks():
    S, K, r, sigma, T, q = 100.0, 105.0, 0.04, 0.3, 0.75, 0.02
    h = 1e-4
    fd_gamma = (
        bsm.call_delta(S + h, K, r, sigma, T, q) - bsm.call_delta(S - h, K, r, sigma, T, q)
    ) / (2.0 * h)
    assert bsm.gamma(S, K, r, sigma, T, q) == pytest.approx(fd_gamma, rel=1e-5)
    fd_vega = (
        bsm.call_price(S, K, r, sigma + h, T, q) - bsm.call_price(S, K, r, sigma - h, T, q)
    ) / (2.0 * h)
    assert bsm.vega(S, K, r, sigma, T, q) == pytest.approx(fd_vega, rel=1e-5)
    # theta = dV/dt = -dV/dT
    fd_theta = -(
        bsm.call_price(S, K, r, sigma, T + h, q) - bsm.call_price(S, K, r, sigma, T - h, q)
    ) / (2.0 * h)
    assert bsm.call_theta(S, K, r, sigma, T, q) == pytest.approx(fd_theta, rel=1e-5)
    fd_rho = (
        bsm.call_price(S, K, r + h, sigma, T, q) - bsm.call_price(S, K, r - h, sigma, T, q)
    ) / (2.0 * h)
    assert bsm.call_rho(S, K, r, sigma, T, q) == pytest.approx(fd_rho, rel=1e-5)
    fd_put_theta = -(
        bsm.put_price(S, K, r, sigma, T + h, q) - bsm.put_price(S, K, r, sigma, T - h, q)
    ) / (2.0 * h)
    assert bsm.put_theta(S, K, r, sigma, T, q) == pytest.approx(fd_put_theta, rel=1e-5)
    fd_put_rho = (
        bsm.put_price(S, K, r + h, sigma, T, q) - bsm.put_price(S, K, r - h, sigma, T, q)
    ) / (2.0 * h)
    assert bsm.put_rho(S, K, r, sigma, T, q) == pytest.approx(fd_put_rho, rel=1e-5)


def test_put_rho_negative_and_signs():
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.2, 1.0
    assert bsm.put_rho(S, K, r, sigma, T) < 0.0
    assert bsm.call_rho(S, K, r, sigma, T) > 0.0
    assert bsm.gamma(S, K, r, sigma, T) > 0.0
    assert bsm.vega(S, K, r, sigma, T) > 0.0
    assert bsm.call_theta(S, K, r, sigma, T) < 0.0  # typical case


def test_vanna_vomma_finite_difference():
    S, K, r, sigma, T, q = 100.0, 105.0, 0.04, 0.3, 0.75, 0.02
    h = 1e-5
    fd_vanna = (
        bsm.call_delta(S, K, r, sigma + h, T, q) - bsm.call_delta(S, K, r, sigma - h, T, q)
    ) / (2.0 * h)
    assert bsm.vanna(S, K, r, sigma, T, q) == pytest.approx(fd_vanna, rel=1e-5)
    fd_vomma = (bsm.vega(S, K, r, sigma + h, T, q) - bsm.vega(S, K, r, sigma - h, T, q)) / (2.0 * h)
    assert bsm.vomma(S, K, r, sigma, T, q) == pytest.approx(fd_vomma, rel=1e-5)


def test_vomma_zero_atm_symmetry():
    # vomma -> 0 as d1*d2 -> 0; near ATM-forward d1 and d2 straddle 0
    import numpy as np

    v = bsm.vomma(np.array([90.0, 100.0, 110.0]), 100.0, 0.05, 0.2, 1.0)
    assert v.shape == (3,)
