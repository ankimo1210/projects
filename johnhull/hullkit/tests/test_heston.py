"""Tests for hullkit.heston (characteristic function + Monte-Carlo).

Pins: CF(0)=1; the Heston price via COS reduces to BSM as vol-of-vol -> 0; the
COS price agrees with an independent full-truncation Euler MC; and a negative
spot-vol correlation produces a downward-skewed implied-vol smile.
"""

import numpy as np
from hullkit import bsm, fourier, heston, volatility


def test_cf_at_zero_is_one():
    val = heston.heston_cf(np.array([0.0]), 0.05, 1.0, 0.04, 1.5, 0.04, 0.5, -0.7)[0]
    assert abs(val - 1.0) < 1e-12


def test_heston_reduces_to_bsm_as_volvol_vanishes():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0

    # xi -> 0 with v0 = theta = sigma^2 freezes variance at sigma^2 (=> GBM)
    def cf(u):
        return heston.heston_cf(u, r, T, sigma**2, 1.5, sigma**2, 1e-3, -0.7)

    price = fourier.cos_price(cf, S0, K, r, T)
    assert abs(price - bsm.call_price(S0, K, r, sigma, T)) < 2e-3


def test_heston_cos_matches_monte_carlo():
    S0, K, r, T = 100.0, 100.0, 0.05, 1.0
    v0, kappa, theta, xi, rho = 0.04, 1.5, 0.04, 0.5, -0.7

    def cf(u):
        return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)

    p_cos = fourier.cos_price(cf, S0, K, r, T)
    p_mc, se = heston.heston_mc_price(
        S0,
        K,
        r,
        T,
        v0,
        kappa,
        theta,
        xi,
        rho,
        n_steps=200,
        n_paths=200_000,
        rng=np.random.default_rng(0),
    )
    assert abs(p_cos - p_mc) < 4 * se + 0.03  # within ~4 MC standard errors + small Euler bias


def test_negative_correlation_gives_downward_skew():
    S0, r, T = 100.0, 0.05, 1.0
    v0, kappa, theta, xi, rho = 0.04, 1.5, 0.04, 0.5, -0.7

    def cf(u):
        return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)

    ivs = [
        volatility.implied_vol(fourier.cos_price(cf, S0, K, r, T), S0, K, r, T)
        for K in (90.0, 100.0, 110.0)
    ]
    assert ivs[0] > ivs[1] > ivs[2]  # rho < 0 => skew down in strike
