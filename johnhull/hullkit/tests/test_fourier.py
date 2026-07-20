"""Tests for hullkit.fourier (COS method).

Pins the COS machinery against the closed-form Black-Scholes price (exact for the
GBM characteristic function) and checks the recovered density integrates to 1.
"""

import numpy as np
from hullkit import bsm, fourier


def test_cos_matches_bsm_for_gbm_call_and_put():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    cf = fourier.lognormal_cf(r, T, sigma)
    call = fourier.cos_price(cf, S0, K, r, T, kind="call")
    put = fourier.cos_price(cf, S0, K, r, T, kind="put")
    assert abs(call - bsm.call_price(S0, K, r, sigma, T)) < 1e-3
    assert abs(put - bsm.put_price(S0, K, r, sigma, T)) < 1e-3


def test_cos_matches_bsm_across_strikes():
    S0, r, sigma, T = 100.0, 0.03, 0.25, 0.5
    cf = fourier.lognormal_cf(r, T, sigma)
    for K in (70.0, 90.0, 100.0, 110.0, 130.0):
        got = fourier.cos_price(cf, S0, K, r, T, kind="call")
        assert abs(got - bsm.call_price(S0, K, r, sigma, T)) < 1e-3, K


def test_cos_density_integrates_to_one():
    cf = fourier.lognormal_cf(0.05, 1.0, 0.2)
    y, f = fourier.cos_density(cf, N=256, L=12.0, n_grid=4000)
    assert abs(float(np.trapezoid(f, y)) - 1.0) < 1e-3
    assert f.min() > -1e-6  # essentially non-negative


def test_cos_deep_otm_outside_truncation_interval_is_zero():
    cf = fourier.lognormal_cf(0.05, 1.0, 0.2)
    call = fourier.cos_price(cf, 100.0, 1_000_000.0, 0.05, 1.0, kind="call")
    put = fourier.cos_price(cf, 100.0, 0.001, 0.05, 1.0, kind="put")
    assert call == 0.0
    assert put == 0.0
