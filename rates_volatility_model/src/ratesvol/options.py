"""Black-76 and Bachelier (normal) option formulas, Greeks and implied vols.

Units: rates and vols are decimals (0.03 = 3%). ``df`` is the discount factor
to the payment date. Greeks are per unit of the underlying input unless the
function name says otherwise (``*_per_bp`` / ``*_per_vol_pt``).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _black_d1(F, K, T, sigma):
    return (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))


def black76_call(F, K, T, sigma, df=1.0):
    """Black-76 call on a forward rate: df * (F N(d1) - K N(d2))."""
    if sigma <= 0 or T <= 0:
        return df * max(F - K, 0.0)
    if F <= 0 or K <= 0:
        raise ValueError("Black-76 needs F > 0 and K > 0; use the Bachelier model instead")
    d1 = _black_d1(F, K, T, sigma)
    d2 = d1 - sigma * np.sqrt(T)
    return df * (F * norm.cdf(d1) - K * norm.cdf(d2))


def black76_put(F, K, T, sigma, df=1.0):
    """Black-76 put via put-call parity."""
    return black76_call(F, K, T, sigma, df) - df * (F - K)


def black76_delta(F, K, T, sigma, df=1.0):
    """dCall/dF (per unit move in F)."""
    if sigma <= 0 or T <= 0:
        return df * (1.0 if F > K else 0.0)
    return df * norm.cdf(_black_d1(F, K, T, sigma))


def black76_gamma(F, K, T, sigma, df=1.0):
    """d2Call/dF2 (per unit move in F, not per 1%)."""
    if sigma <= 0 or T <= 0:
        return 0.0
    return df * norm.pdf(_black_d1(F, K, T, sigma)) / (F * sigma * np.sqrt(T))


def black76_vega_per_vol_pt(F, K, T, sigma, df=1.0):
    """Price change for a 1 vol-point (0.01) move in the Black vol."""
    if sigma <= 0 or T <= 0:
        return 0.0
    return df * F * norm.pdf(_black_d1(F, K, T, sigma)) * np.sqrt(T) * 0.01


def bachelier_call(F, K, T, sigma_n, df=1.0):
    """Bachelier (normal) call: df * ((F-K) N(d) + sigma_n sqrt(T) n(d))."""
    if sigma_n <= 0 or T <= 0:
        return df * max(F - K, 0.0)
    s = sigma_n * np.sqrt(T)
    d = (F - K) / s
    return df * ((F - K) * norm.cdf(d) + s * norm.pdf(d))


def bachelier_put(F, K, T, sigma_n, df=1.0):
    """Bachelier put via put-call parity."""
    return bachelier_call(F, K, T, sigma_n, df) - df * (F - K)


def bachelier_delta(F, K, T, sigma_n, df=1.0):
    """dCall/dF."""
    if sigma_n <= 0 or T <= 0:
        return df * (1.0 if F > K else 0.0)
    return df * norm.cdf((F - K) / (sigma_n * np.sqrt(T)))


def bachelier_gamma(F, K, T, sigma_n, df=1.0):
    """d2Call/dF2."""
    if sigma_n <= 0 or T <= 0:
        return 0.0
    s = sigma_n * np.sqrt(T)
    return df * norm.pdf((F - K) / s) / s


def bachelier_vega(F, K, T, sigma_n, df=1.0):
    """dCall/dsigma_n per unit (1.0 = 10,000bp) of normal vol."""
    if sigma_n <= 0 or T <= 0:
        return 0.0
    return df * np.sqrt(T) * norm.pdf((F - K) / (sigma_n * np.sqrt(T)))


def bachelier_vega_per_bp(F, K, T, sigma_n, df=1.0):
    """Price change for a 1bp (0.0001) move in the normal vol."""
    return bachelier_vega(F, K, T, sigma_n, df) * 1e-4


def _implied(price_fn, price, F, K, T, df, option_type, lo, hi):
    intrinsic = df * (max(F - K, 0.0) if option_type == "call" else max(K - F, 0.0))
    if price <= intrinsic + 1e-14:
        return np.nan
    try:
        return brentq(lambda s: price_fn(F, K, T, s, df) - price, lo, hi, xtol=1e-12)
    except ValueError:
        return np.nan


def black76_implied_vol(price, F, K, T, df=1.0, option_type="call"):
    """Black vol that reproduces ``price``; nan if no root in [1e-6, 20]."""
    fn = black76_call if option_type == "call" else black76_put
    return _implied(fn, price, F, K, T, df, option_type, 1e-6, 20.0)


def bachelier_implied_vol(price, F, K, T, df=1.0, option_type="call"):
    """Normal vol that reproduces ``price``; nan if no root in [1e-8, 1]."""
    fn = bachelier_call if option_type == "call" else bachelier_put
    return _implied(fn, price, F, K, T, df, option_type, 1e-8, 1.0)
