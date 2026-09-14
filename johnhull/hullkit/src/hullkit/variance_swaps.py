"""Variance and volatility swaps by static replication (Hull 11e GE §26.16, pp.629-632).

The risk-neutral expected variance rate is replicated from a strip of
out-of-the-money European options (eqs. 26.6 and 26.8, including the ``S*``
boundary terms), a variance swap is valued with eq. (26.7), and a volatility
swap with the convexity approximation of eq. (26.9). Eq. (26.10) is the VIX
truncation of the log term.

Kept apart from :mod:`hullkit.exotics` (closed-form option pricers under one
set of BSM parameters): these functions consume a strike strip of option prices
(market quotes or a per-strike implied-volatility smile) and are
model-independent apart from the continuous-monitoring assumption.
"""

import math

import numpy as np

from . import bsm


def _strikes(strikes):
    k = np.asarray(strikes, dtype=float)
    if k.ndim != 1 or k.size < 2:
        raise ValueError("strikes must be a 1-D array with at least two entries")
    if not np.all(np.isfinite(k)) or np.any(k <= 0.0):
        raise ValueError("strikes must be finite and > 0")
    if np.any(np.diff(k) <= 0.0):
        raise ValueError("strikes must be strictly increasing")
    return k


def _prices(prices, n, name):
    p = np.asarray(prices, dtype=float)
    if p.shape != (n,):
        raise ValueError(f"{name} must have the same length as strikes ({n}), got shape {p.shape}")
    if not np.all(np.isfinite(p)) or np.any(p < 0.0):
        raise ValueError(f"{name} must be finite and >= 0")
    return p


def _positive(value, name):
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {value!r}")


def default_s_star(strikes, F0):
    """Hull's choice of ``S*``: the first strike at or below the forward ``F0``.

    Hull 11e GE §26.16 p.630 sets ``S*`` "equal to the first strike price below
    F0"; a strike exactly equal to ``F0`` is taken (the boundary terms of
    eq. 26.6 then vanish). Raises ``ValueError`` when every strike exceeds ``F0``.
    """
    k = _strikes(strikes)
    _positive(F0, "F0")
    below = k[k <= F0]
    if below.size == 0:
        raise ValueError(f"no strike at or below the forward F0={F0}")
    return float(below[-1])


def strike_spacing(strikes):
    """``Delta K_i`` of Hull eq. (26.8), §26.16 p.630.

    ``0.5 (K_{i+1} - K_{i-1})`` for interior strikes, ``K_2 - K_1`` for the first
    and ``K_n - K_{n-1}`` for the last.
    """
    k = _strikes(strikes)
    dk = np.empty_like(k)
    dk[1:-1] = 0.5 * (k[2:] - k[:-2])
    dk[0] = k[1] - k[0]
    dk[-1] = k[-1] - k[-2]
    return dk


def otm_option_prices(strikes, call_prices, put_prices, S_star):
    """``Q(K_i)`` of Hull eq. (26.8), §26.16 p.630.

    The put price for ``K_i < S*``, the call price for ``K_i > S*``, and the
    average of the two when ``K_i = S*``.
    """
    k = _strikes(strikes)
    c = _prices(call_prices, k.size, "call_prices")
    p = _prices(put_prices, k.size, "put_prices")
    _positive(S_star, "S_star")
    at = np.isclose(k, S_star, rtol=1e-12, atol=0.0)
    return np.where(at, 0.5 * (c + p), np.where(k < S_star, p, c))


def _strip_sum(k, q_values, r, T):
    return float(np.sum(strike_spacing(k) / k**2 * math.exp(r * T) * q_values))


def fair_variance(strikes, otm_prices, F0, r, T, S_star=None):
    """Risk-neutral expected variance rate ``E(V)`` from an OTM strip (Hull eqs. 26.6, 26.8).

    Hull 11e GE §26.16 p.630::

        E(V) = (2/T) ln(F0/S*) - (2/T)(F0/S* - 1) + (2/T) sum_i dK_i/K_i^2 e^{rT} Q(K_i)

    ``otm_prices`` are the ``Q(K_i)`` of :func:`otm_option_prices` built with the
    same ``S_star`` (default :func:`default_s_star`). This is the fair variance
    strike of a variance swap.

    Grid error (derived here, not in Hull): ``Q`` switches from the put to the
    call at ``S*``, a jump of ``e^{-rT}(F0 - K)`` whose slope the sum resolves
    only to second order. On a uniform grid of spacing ``dK`` wide enough for
    the tails to be negligible, ``E(V)_grid - E(V) ~= dK^2 (2 F0 - S*) /
    (6 T S*^3)``, i.e. about ``dK^2 / (6 T F0^2)``; a truncated strip adds a
    negative bias from the missing wings.
    """
    k = _strikes(strikes)
    q_values = _prices(otm_prices, k.size, "otm_prices")
    _positive(F0, "F0")
    _positive(T, "T")
    s_star = default_s_star(k, F0) if S_star is None else S_star
    _positive(s_star, "S_star")
    ratio = F0 / s_star
    return (2.0 / T) * (math.log(ratio) - (ratio - 1.0)) + (2.0 / T) * _strip_sum(k, q_values, r, T)


def vix_cumulative_variance(strikes, otm_prices, F0, r, T, S_star=None):
    """Expected cumulative variance ``E(V) T`` with the VIX truncation (Hull eq. 26.10, p.631).

    ``ln(F0/S*)`` in eq. (26.6) is replaced by its two-term expansion, giving
    ``-(F0/S* - 1)^2 + 2 sum_i dK_i/K_i^2 e^{rT} Q(K_i)``. Arguments as in
    :func:`fair_variance`.
    """
    k = _strikes(strikes)
    q_values = _prices(otm_prices, k.size, "otm_prices")
    _positive(F0, "F0")
    _positive(T, "T")
    s_star = default_s_star(k, F0) if S_star is None else S_star
    _positive(s_star, "S_star")
    return -((F0 / s_star - 1.0) ** 2) + 2.0 * _strip_sum(k, q_values, r, T)


def fair_variance_from_implied_vols(S, strikes, implied_vols, r, T, q=0.0, S_star=None):
    """``E(V)`` from a per-strike implied-volatility smile (Hull §26.16, Example 26.4 p.630).

    Prices the calls and puts with Black-Scholes-Merton at each strike's
    implied volatility (a scalar means a flat smile), forms ``Q(K_i)`` around
    ``S*`` (default :func:`default_s_star` with ``F0 = S e^{(r-q)T}``) and
    applies :func:`fair_variance`.
    """
    _positive(S, "S")
    _positive(T, "T")
    k = _strikes(strikes)
    vols = np.broadcast_to(np.asarray(implied_vols, dtype=float), k.shape)
    if not np.all(np.isfinite(vols)) or np.any(vols <= 0.0):
        raise ValueError("implied_vols must be finite and > 0")
    F0 = S * math.exp((r - q) * T)
    s_star = default_s_star(k, F0) if S_star is None else S_star
    calls = bsm.call_price(S, k, r, vols, T, q)
    puts = bsm.put_price(S, k, r, vols, T, q)
    q_values = otm_option_prices(k, calls, puts, s_star)
    return fair_variance(k, q_values, F0, r, T, S_star=s_star)


def variance_swap_value(expected_variance, variance_strike, r, T, notional=1.0):
    """Value of receiving realized variance and paying ``V_K`` (Hull eq. 26.7, p.630).

    ``L_var (E(V) - V_K) e^{-rT}``.
    """
    _positive(T, "T")
    return notional * (expected_variance - variance_strike) * math.exp(-r * T)


def expected_volatility(expected_variance, variance_of_variance):
    """Convexity-adjusted expected realized volatility (Hull eq. 26.9, p.631).

    ``E(sigma) ~= sqrt(E(V)) (1 - var(V) / (8 E(V)^2))``: the second-order
    expansion of ``sqrt(V)`` around ``E(V)``, so ``E(sigma) < sqrt(E(V))``.
    """
    _positive(expected_variance, "expected_variance")
    if not math.isfinite(variance_of_variance) or variance_of_variance < 0.0:
        raise ValueError(
            f"variance_of_variance must be finite and >= 0, got {variance_of_variance!r}"
        )
    return math.sqrt(expected_variance) * (
        1.0 - variance_of_variance / (8.0 * expected_variance**2)
    )


def volatility_swap_value(expected_vol, volatility_strike, r, T, notional=1.0):
    """Value of receiving realized volatility and paying ``sigma_K`` (Hull §26.16, p.631).

    ``L_vol (E(sigma) - sigma_K) e^{-rT}``; ``expected_vol`` is typically
    :func:`expected_volatility`.
    """
    _positive(T, "T")
    return notional * (expected_vol - volatility_strike) * math.exp(-r * T)
