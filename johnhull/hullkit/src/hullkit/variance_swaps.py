"""Variance and volatility swaps by static replication (Hull 11e GE §26.16, pp.629-632).

The contract side is the zero-mean realized volatility of p.629
(:func:`realized_variance`, :func:`realized_volatility`) and the notional link
``L_var = L_vol / (2 sigma_K)`` (:func:`variance_notional`). The risk-neutral
expected variance rate is replicated from a strip of out-of-the-money European
options (eqs. 26.6 and 26.8, including the ``S*`` boundary terms), a variance
swap is valued with eq. (26.7), and a volatility swap with the convexity
approximation of eq. (26.9). Eq. (26.10) is the VIX truncation of the log term,
and :func:`vix_index` applies the 30-day interpolation Hull describes on p.632.

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


def realized_variance(prices, periods_per_year=252.0, denominator="n-2"):
    """Realized variance rate ``V = sigma^2`` of a volatility swap (Hull §26.16, p.629).

    ``sigma^2 = periods_per_year / (n - 2) * sum_{i=1}^{n-1} ln(S_{i+1}/S_i)^2`` for
    ``n`` observations, with the mean daily return taken as zero. Hull notes that
    ``n - 1`` sometimes replaces ``n - 2`` (``denominator="n-1"``). With ``n - 1``
    squared returns in the sum, the ``n - 2`` convention overstates a zero-drift
    variance by the factor ``(n - 1)/(n - 2)`` in expectation.
    """
    s = np.asarray(prices, dtype=float)
    if s.ndim != 1:
        raise ValueError("prices must be a 1-D array of observations")
    if denominator == "n-2":
        minimum, divisor = 3, s.size - 2
    elif denominator == "n-1":
        minimum, divisor = 2, s.size - 1
    else:
        raise ValueError(f"denominator must be 'n-2' or 'n-1', got {denominator!r}")
    if s.size < minimum:
        raise ValueError(f"{denominator} needs at least {minimum} observations, got {s.size}")
    if not np.all(np.isfinite(s)) or np.any(s <= 0.0):
        raise ValueError("prices must be finite and > 0")
    if not math.isfinite(periods_per_year) or periods_per_year <= 0.0:
        raise ValueError(f"periods_per_year must be finite and > 0, got {periods_per_year!r}")
    log_returns = np.diff(np.log(s))
    return float(periods_per_year * math.fsum(log_returns * log_returns) / divisor)


def realized_volatility(prices, periods_per_year=252.0, denominator="n-2"):
    """Realized volatility ``sigma`` of Hull §26.16 p.629; see :func:`realized_variance`."""
    return math.sqrt(realized_variance(prices, periods_per_year, denominator))


def variance_notional(volatility_notional, volatility_strike):
    """``L_var = L_vol / (2 sigma_K)`` (Hull §26.16, p.629).

    With the variance strike ``V_K = sigma_K^2``, the variance payoff
    ``L_var (sigma^2 - sigma_K^2)`` then has the same slope ``L_vol`` as the volatility
    payoff at ``sigma = sigma_K``, and differs from it by
    ``L_vol (sigma - sigma_K)^2 / (2 sigma_K)``, which is non-negative for ``L_vol >= 0``.
    """
    if not math.isfinite(volatility_notional):
        raise ValueError(f"volatility_notional must be finite, got {volatility_notional!r}")
    _positive(volatility_strike, "volatility_strike")
    return volatility_notional / (2.0 * volatility_strike)


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


def vix_index(
    near_term,
    near_cumulative_variance,
    next_term,
    next_cumulative_variance,
    target_term=30.0 / 365.0,
):
    """Hull's 30-day VIX from two cumulative variances ``E(V)T`` (§26.16, p.632).

    The cumulative variances of the maturities just below and above 30 days
    (typically from :func:`vix_cumulative_variance`) are interpolated linearly in
    time to ``target_term``, multiplied by ``1/target_term`` (365/30 for terms in
    years of 365 days) and square-rooted. Returns a decimal volatility; the
    published index quotes 100 times this. This is Hull's description, not the
    full CBOE rulebook (strike selection, minute-level terms, forward determination).
    """
    for value, name in (
        (near_term, "near_term"),
        (next_term, "next_term"),
        (target_term, "target_term"),
    ):
        _positive(value, name)
    if not near_term < next_term:
        raise ValueError(f"need near_term < next_term, got {near_term!r} and {next_term!r}")
    if not near_term <= target_term <= next_term:
        raise ValueError("near_term and next_term must bracket target_term")
    for value in (near_cumulative_variance, next_cumulative_variance):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("cumulative variances must be finite and >= 0")
    weight = (next_term - target_term) / (next_term - near_term)
    cumulative = weight * near_cumulative_variance + (1.0 - weight) * next_cumulative_variance
    return math.sqrt(cumulative / target_term)


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
