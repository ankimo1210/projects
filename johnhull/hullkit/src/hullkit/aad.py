"""Pathwise, likelihood-ratio and bump Greeks (A3 deep-dive — toward AAD).

For a European call under GBM the *pathwise* estimator is exactly the adjoint
(reverse-mode) result: d payoff / dS0 = e^{-rT} (S_T/S0) 1{S_T>K}. We provide the
pathwise and likelihood-ratio (score) estimators and a central bump-and-revalue,
and the tests confirm they all match the closed-form Greeks. Real AAD generalizes
the pathwise idea to compute *all* sensitivities in one reverse sweep at O(1) cost.

References: Glasserman, *Monte Carlo Methods* Ch.7; Giles & Glasserman (2006),
"Smoking adjoints: fast Monte Carlo Greeks".
"""

from __future__ import annotations

import numpy as np

from . import bsm


def _terminal(S0, r, sigma, T, z):
    return S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)


def pathwise_greeks(S0, K, r, sigma, T, n_paths=200_000, rng=None):
    """(delta, vega) of a European call by pathwise differentiation."""
    if rng is None:
        rng = np.random.default_rng(0)
    z = rng.standard_normal(n_paths)
    s_t = _terminal(S0, r, sigma, T, z)
    itm = (s_t > K).astype(float)
    disc = np.exp(-r * T)
    delta = disc * float(np.mean(itm * s_t / S0))
    ds_dsigma = s_t * (-sigma * T + np.sqrt(T) * z)  # dS_T/dsigma
    vega = disc * float(np.mean(itm * ds_dsigma))
    return delta, vega


def likelihood_ratio_greeks(S0, K, r, sigma, T, n_paths=200_000, rng=None):
    """(delta, vega) of a European call by the likelihood-ratio (score) method."""
    if rng is None:
        rng = np.random.default_rng(0)
    z = rng.standard_normal(n_paths)
    s_t = _terminal(S0, r, sigma, T, z)
    payoff = np.exp(-r * T) * np.maximum(s_t - K, 0.0)
    sq_t = sigma * np.sqrt(T)
    delta = float(np.mean(payoff * z / (S0 * sq_t)))
    vega = float(np.mean(payoff * ((z**2 - 1.0) / sigma - z * np.sqrt(T))))
    return delta, vega


def bump_greeks(S0, K, r, sigma, T, h_s=1e-2, h_v=1e-4):
    """(delta, vega) by central bump-and-revalue of the closed-form price."""
    delta = (
        bsm.call_price(S0 + h_s, K, r, sigma, T) - bsm.call_price(S0 - h_s, K, r, sigma, T)
    ) / (2.0 * h_s)
    vega = (bsm.call_price(S0, K, r, sigma + h_v, T) - bsm.call_price(S0, K, r, sigma - h_v, T)) / (
        2.0 * h_v
    )
    return float(delta), float(vega)
