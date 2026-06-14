"""Tests for hullkit.aad (pathwise / likelihood-ratio / bump Greeks).

All three estimators must agree with the closed-form BSM delta and vega — the
point of the chapter (the pathwise estimator is the adjoint result for this payoff).
"""

import numpy as np
from hullkit import aad, bsm


def test_delta_estimators_agree_with_closed_form():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    true = bsm.call_delta(S0, K, r, sigma, T)
    pd, _ = aad.pathwise_greeks(S0, K, r, sigma, T, rng=np.random.default_rng(2))
    ld, _ = aad.likelihood_ratio_greeks(S0, K, r, sigma, T, rng=np.random.default_rng(2))
    bd, _ = aad.bump_greeks(S0, K, r, sigma, T)
    assert abs(pd - true) < 5e-3  # pathwise (MC)
    assert abs(ld - true) < 1e-2  # likelihood ratio (noisier)
    assert abs(bd - true) < 1e-4  # bump-and-revalue (deterministic)


def test_vega_estimators_agree_with_closed_form():
    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    true = bsm.vega(S0, K, r, sigma, T)
    _, pv = aad.pathwise_greeks(S0, K, r, sigma, T, rng=np.random.default_rng(2))
    _, bv = aad.bump_greeks(S0, K, r, sigma, T)
    assert abs(pv - true) < 0.5  # pathwise (MC)
    assert abs(bv - true) < 1e-2  # bump-and-revalue
