"""Tests for hullkit.sabr (Hagan implied-vol expansion).

Pins the well-known limiting behaviour: beta=1 with no vol-of-vol is a flat smile
at alpha; the ATM branch is continuous with the general formula; a negative rho
tilts the smile downward in strike.
"""

import pytest
from hullkit import sabr


def test_flat_smile_when_volvol_zero_and_beta_one():
    for K in (80.0, 100.0, 120.0):
        iv = sabr.sabr_implied_vol(100.0, K, 1.0, 0.20, 1.0, 0.0, 1e-8)
        assert abs(iv - 0.20) < 1e-4, K


def test_flat_smile_at_exactly_nu_zero():
    # regression: nu=0 made z/x(z) evaluate as 0/0 -> NaN off-ATM
    for K in (80.0, 100.0, 120.0):
        iv = sabr.sabr_implied_vol(100.0, K, 1.0, 0.20, 1.0, -0.3, 0.0)
        assert abs(iv - 0.20) < 1e-12, K


def test_atm_branch_is_continuous():
    args = (1.0, 0.20, 0.5, -0.3, 0.4)
    atm = sabr.sabr_implied_vol(100.0, 100.0, *args)
    near = sabr.sabr_implied_vol(100.0, 100.0 * (1 + 1e-6), *args)
    assert abs(atm - near) < 1e-4


def test_negative_rho_gives_downward_skew():
    lo = sabr.sabr_implied_vol(100.0, 90.0, 1.0, 0.20, 0.5, -0.5, 0.4)
    hi = sabr.sabr_implied_vol(100.0, 110.0, 1.0, 0.20, 0.5, -0.5, 0.4)
    assert lo > hi


def test_calibration_recovers_reference_params():
    import numpy as np

    ks = np.linspace(80.0, 125.0, 16)
    mkt = [sabr.sabr_implied_vol(100.0, k, 1.0, 0.30, 1.0, -0.30, 0.40) for k in ks]
    a, r_, n_ = sabr.calibrate_sabr(100.0, 1.0, ks, mkt, beta=1.0)
    assert abs(a - 0.30) < 1e-6 and abs(r_ + 0.30) < 1e-4 and abs(n_ - 0.40) < 1e-4


def test_same_smile_different_beta_gives_different_delta():
    # Hagan's model-risk point: every beta reprices the market smile, but the
    # smile-consistent deltas differ materially.
    import numpy as np

    ks = np.linspace(80.0, 125.0, 16)
    mkt = np.array([sabr.sabr_implied_vol(100.0, k, 1.0, 0.30, 1.0, -0.30, 0.40) for k in ks])
    atm_deltas = {}
    for beta in (1.0, 0.0):
        a, r_, n_ = sabr.calibrate_sabr(100.0, 1.0, ks, mkt, beta)
        fit = np.array([sabr.sabr_implied_vol(100.0, k, 1.0, a, beta, r_, n_) for k in ks])
        assert np.abs(fit - mkt).max() < 1e-3, beta  # market data fixed
        atm_deltas[beta] = sabr.sabr_smile_delta(100.0, 100.0, 1.0, a, beta, r_, n_)
    assert abs(atm_deltas[1.0] - atm_deltas[0.0]) > 0.05  # ~12 delta points apart


def test_sabr_greeks_flat_limit_matches_black():
    # beta=1, nu=0: flat smile, so every smile-consistent Greek must equal the
    # r=q=0 Black-Scholes Greek (vega is per ATM-vol unit by construction).
    from hullkit import bsm

    F, K, T, sig = 100.0, 110.0, 1.0, 0.20
    g = sabr.sabr_greeks(F, K, T, sig, 1.0, 0.0, 0.0)
    assert abs(g["delta"] - bsm.call_delta(F, K, 0.0, sig, T)) < 1e-6
    assert abs(g["gamma"] - bsm.gamma(F, K, 0.0, sig, T)) < 1e-6
    assert abs(g["vega"] - bsm.vega(F, K, 0.0, sig, T)) < 1e-3
    assert abs(g["theta"] - bsm.call_theta(F, K, 0.0, sig, T)) < 1e-3


def test_smile_delta_flat_limit_equals_sticky_strike():
    # nu=0, beta=1: the smile is flat, so backbone and sticky-strike deltas agree.
    d_smile = sabr.sabr_smile_delta(100.0, 110.0, 1.0, 0.20, 1.0, 0.0, 0.0)
    d_sticky = sabr.sticky_strike_delta(100.0, 110.0, 1.0, 0.20)
    assert abs(d_smile - d_sticky) < 1e-6


def test_validates_inputs():
    with pytest.raises(ValueError):
        sabr.sabr_implied_vol(100.0, 100.0, 1.0, -0.1, 0.5, 0.0, 0.4)  # alpha <= 0
    with pytest.raises(ValueError):
        sabr.sabr_implied_vol(100.0, 100.0, 1.0, 0.2, 0.5, 1.5, 0.4)  # rho out of range
