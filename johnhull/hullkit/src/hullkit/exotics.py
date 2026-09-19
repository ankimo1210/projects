"""Closed-form exotic option pricers (Hull 11e, Ch.26).

Variance and volatility swaps (§26.16) live in :mod:`hullkit.variance_swaps`.
"""

import math

import numpy as np
from scipy.stats import norm

from . import bsm


def _d1d2(S, K, r, sigma, T, q):
    # Delegates to bsm.d1/d2 (now vectorized) to avoid formula duplication.
    return bsm.d1(S, K, r, sigma, T, q), bsm.d2(S, K, r, sigma, T, q)


def gap_call(S, K1, K2, r, sigma, T, q=0.0):
    """Gap call: pays S_T - K1 when S_T > K2 (Hull eq. 26.1)."""
    d1, d2 = _d1d2(S, K2, r, sigma, T, q)
    return S * math.exp(-q * T) * norm.cdf(d1) - K1 * math.exp(-r * T) * norm.cdf(d2)


def gap_put(S, K1, K2, r, sigma, T, q=0.0):
    """Gap put: pays K1 - S_T when S_T < K2 (Hull 11e GE §26.4 p.617, eq. 26.2).

    ``d1``/``d2`` use the trigger ``K2``; ``K1`` only sets the payoff. Because
    gap call minus gap put pays ``S_T - K1`` in every state,
    ``gap_call - gap_put = S e^{-qT} - K1 e^{-rT}``.
    """
    d1, d2 = _d1d2(S, K2, r, sigma, T, q)
    return K1 * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def cash_or_nothing(S, K, r, sigma, T, q=0.0, kind="call", payout=1.0):
    """Cash-or-nothing binary: pays `payout` if ITM at expiry (Hull §26.10)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    _, d2 = _d1d2(S, K, r, sigma, T, q)
    sign = 1.0 if kind == "call" else -1.0
    return payout * math.exp(-r * T) * norm.cdf(sign * d2)


def asset_or_nothing(S, K, r, sigma, T, q=0.0, kind="call"):
    """Asset-or-nothing binary: pays S_T if ITM at expiry (Hull §26.10)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    d1, _ = _d1d2(S, K, r, sigma, T, q)
    sign = 1.0 if kind == "call" else -1.0
    return S * math.exp(-q * T) * norm.cdf(sign * d1)


_BARRIER_TYPES = ("down-and-in", "down-and-out", "up-and-in", "up-and-out")

# Broadie-Glasserman-Kou constant beta = -zeta(1/2)/sqrt(2*pi) = 0.5826 (as printed
# in Hull 11e GE §26.9 p.622).
BGK_BETA = 0.5826


def bgk_adjusted_barrier(H, sigma, T, n_observations, barrier):
    """Broadie-Glasserman-Kou continuity correction for a discretely monitored barrier.

    Hull 11e GE §26.9 p.622: when the asset price is observed ``m`` times
    (every ``T/m`` years), price with the continuous-monitoring formulas after
    replacing ``H`` by ``H e^{0.5826 sigma sqrt(T/m)}`` for up barriers and by
    ``H e^{-0.5826 sigma sqrt(T/m)}`` for down barriers. ``barrier`` is one of
    the four barrier types (or just ``"up"``/``"down"``). The shift moves the
    barrier away from the spot, so the correction tends to 0 as ``m`` grows.
    """
    if not barrier.startswith(("up", "down")):
        raise ValueError(f"barrier must start with 'up' or 'down', got {barrier!r}")
    if isinstance(n_observations, bool) or int(n_observations) != n_observations:
        raise ValueError(f"n_observations must be a positive integer, got {n_observations!r}")
    if n_observations < 1:
        raise ValueError(f"n_observations must be a positive integer, got {n_observations!r}")
    if H <= 0.0 or sigma <= 0.0 or T <= 0.0:
        raise ValueError("H, sigma, and T must be > 0")
    sign = 1.0 if barrier.startswith("up") else -1.0
    return H * math.exp(sign * BGK_BETA * sigma * math.sqrt(T / n_observations))


def barrier_call(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in", n_observations=None):
    """Barrier call closed forms (Hull GE §26.9 pp.620–622). barrier in {down-and-in,
    down-and-out, up-and-in, up-and-out}. Uses in+out=vanilla complements.

    ``n_observations=None`` (default) is continuous monitoring. An integer
    ``m`` applies the Broadie-Glasserman-Kou shift of
    :func:`bgk_adjusted_barrier` (Hull 11e GE §26.9 p.622) to ``H`` before
    pricing; the already-breached guard still compares the spot with the
    contract barrier H. Maturity is a fixing date, so the exact zero for
    an up-and-out call with the original H <= K is preserved even when the
    shifted barrier would cross the strike."""
    valid = _BARRIER_TYPES
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.call_price(S, K, r, sigma, T, q)
    breached = (barrier.startswith("down") and H >= S) or (barrier.startswith("up") and H <= S)
    if breached:
        return vanilla if barrier.endswith("in") else 0.0
    contract_H = H
    if n_observations is not None:
        H = bgk_adjusted_barrier(H, sigma, T, n_observations, barrier)
    # T is a fixing date even for discrete monitoring. Positive intrinsic value
    # here necessarily breaches the original contract barrier at or before T.
    # Validate the BGK inputs above, but do not let its shift break an exact zero.
    if barrier.startswith("up") and contract_H <= K:
        return vanilla if barrier.endswith("in") else 0.0
    sqt = sigma * math.sqrt(T)
    lam = (r - q + 0.5 * sigma**2) / sigma**2
    x1 = math.log(S / H) / sqt + lam * sqt
    y1 = math.log(H / S) / sqt + lam * sqt
    y = math.log(H**2 / (S * K)) / sqt + lam * sqt

    def _pow(exp_):
        return (H / S) ** exp_

    if barrier in ("down-and-in", "down-and-out"):
        if H <= K:
            cdi = S * math.exp(-q * T) * _pow(2 * lam) * norm.cdf(y) - K * math.exp(-r * T) * _pow(
                2 * lam - 2
            ) * norm.cdf(y - sqt)
        else:
            cdo = (
                S * math.exp(-q * T) * norm.cdf(x1)
                - K * math.exp(-r * T) * norm.cdf(x1 - sqt)
                - S * math.exp(-q * T) * _pow(2 * lam) * norm.cdf(y1)
                + K * math.exp(-r * T) * _pow(2 * lam - 2) * norm.cdf(y1 - sqt)
            )
            cdi = vanilla - cdo
        return cdi if barrier == "down-and-in" else vanilla - cdi
    # up barriers
    if H >= K:
        cui = (
            S * math.exp(-q * T) * norm.cdf(x1)
            - K * math.exp(-r * T) * norm.cdf(x1 - sqt)
            - S * math.exp(-q * T) * _pow(2 * lam) * (norm.cdf(-y) - norm.cdf(-y1))
            + K * math.exp(-r * T) * _pow(2 * lam - 2) * (norm.cdf(-y + sqt) - norm.cdf(-y1 + sqt))
        )
    else:
        cui = vanilla  # positive call payoff requires crossing H<=K (not certain hitting)
    return cui if barrier == "up-and-in" else vanilla - cui


def barrier_put(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in", n_observations=None):
    """Barrier put closed forms (Hull 11e GE §26.9 pp.620–622).

    ``barrier`` in {down-and-in, down-and-out, up-and-in, up-and-out}; the
    signature, validation and already-breached guard mirror
    :func:`barrier_call` (a down barrier at or above the spot, or an up barrier
    at or below it, returns the vanilla put for knock-ins and 0 for
    knock-outs). Hull's branches: up barriers use the ``p_ui`` formula when
    ``H >= K`` and the ``p_uo`` formula when ``H < K``; a down barrier with
    ``H >= K`` gives ``p_do = 0`` and ``p_di = p``, otherwise the ``p_di``
    formula. The complement in each pair is ``vanilla put - value`` (in + out =
    vanilla). ``n_observations`` applies the Broadie-Glasserman-Kou discrete
    monitoring shift as in barrier_call, preserving the exact zero
    down-and-out payoff for the original H >= K when T is a fixing date.
    """
    valid = _BARRIER_TYPES
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.put_price(S, K, r, sigma, T, q)
    breached = (barrier.startswith("down") and H >= S) or (barrier.startswith("up") and H <= S)
    if breached:
        return vanilla if barrier.endswith("in") else 0.0
    contract_H = H
    if n_observations is not None:
        H = bgk_adjusted_barrier(H, sigma, T, n_observations, barrier)
    # T is a fixing date even for discrete monitoring. Positive intrinsic value
    # here necessarily breaches the original contract barrier at or before T.
    # Validate the BGK inputs above, but do not let its shift break an exact zero.
    if barrier.startswith("down") and contract_H >= K:
        return vanilla if barrier.endswith("in") else 0.0
    sqt = sigma * math.sqrt(T)
    lam = (r - q + 0.5 * sigma**2) / sigma**2
    x1 = math.log(S / H) / sqt + lam * sqt
    y1 = math.log(H / S) / sqt + lam * sqt
    y = math.log(H**2 / (S * K)) / sqt + lam * sqt
    asset = S * math.exp(-q * T)
    cash = K * math.exp(-r * T)
    pow_a = (H / S) ** (2 * lam)
    pow_c = (H / S) ** (2 * lam - 2)

    if barrier in ("up-and-in", "up-and-out"):
        if H >= K:
            pui = -asset * pow_a * norm.cdf(-y) + cash * pow_c * norm.cdf(-y + sqt)
        else:
            puo = (
                -asset * norm.cdf(-x1)
                + cash * norm.cdf(-x1 + sqt)
                + asset * pow_a * norm.cdf(-y1)
                - cash * pow_c * norm.cdf(-y1 + sqt)
            )
            pui = vanilla - puo
        return pui if barrier == "up-and-in" else vanilla - pui
    # down barriers
    if H >= K:
        pdi = vanilla  # the put pays only below K <= H, so it must have knocked in
    else:
        pdi = (
            -asset * norm.cdf(-x1)
            + cash * norm.cdf(-x1 + sqt)
            + asset * pow_a * (norm.cdf(y) - norm.cdf(y1))
            - cash * pow_c * (norm.cdf(y - sqt) - norm.cdf(y1 - sqt))
        )
    return pdi if barrier == "down-and-in" else vanilla - pdi


def lookback_floating_call(S, S_min, r, sigma, T, q=0.0):
    """Floating-strike lookback call (Hull §26.11). Pays S_T - min S."""
    if abs(r - q) < 1e-8:
        raise ValueError(
            "lookback_floating_call: the b=r-q=0 limit is not implemented; "
            "use r != q (the closed form has a removable singularity at b=0)"
        )
    sqt = sigma * math.sqrt(T)
    a1 = (math.log(S / S_min) + (r - q + 0.5 * sigma**2) * T) / sqt
    a2 = a1 - sqt
    a3 = (math.log(S / S_min) + (-r + q + 0.5 * sigma**2) * T) / sqt
    y1 = -2.0 * (r - q - 0.5 * sigma**2) * math.log(S / S_min) / sigma**2
    ratio = sigma**2 / (2.0 * (r - q))
    return (
        S * math.exp(-q * T) * norm.cdf(a1)
        - S * math.exp(-q * T) * ratio * norm.cdf(-a1)
        - S_min * math.exp(-r * T) * (norm.cdf(a2) - ratio * math.exp(y1) * norm.cdf(-a3))
    )


def lookback_floating_put(S, S_max, r, sigma, T, q=0.0):
    """Floating-strike lookback put (Hull 11e GE §26.11 p.624). Pays max S - S_T.

    ``S_max`` is the maximum asset price observed to date (``S_max = S`` for a
    newly issued option) and must be ``>= S``. Continuous monitoring. As for
    :func:`lookback_floating_call`, the ``r == q`` limit is not implemented and
    raises ``ValueError``.
    """
    if abs(r - q) < 1e-8:
        raise ValueError(
            "lookback_floating_put: the b=r-q=0 limit is not implemented; "
            "use r != q (the closed form has a removable singularity at b=0)"
        )
    if S_max < S:
        raise ValueError(f"S_max must be >= S (maximum to date), got S_max={S_max}, S={S}")
    sqt = sigma * math.sqrt(T)
    b1 = (math.log(S_max / S) + (-r + q + 0.5 * sigma**2) * T) / sqt
    b2 = b1 - sqt
    b3 = (math.log(S_max / S) + (r - q - 0.5 * sigma**2) * T) / sqt
    y2 = 2.0 * (r - q - 0.5 * sigma**2) * math.log(S_max / S) / sigma**2
    ratio = sigma**2 / (2.0 * (r - q))
    return (
        S_max * math.exp(-r * T) * (norm.cdf(b1) - ratio * math.exp(y2) * norm.cdf(-b3))
        + S * math.exp(-q * T) * ratio * norm.cdf(-b2)
        - S * math.exp(-q * T) * norm.cdf(b2)
    )


def lookback_fixed_call(S, K, S_max, r, sigma, T, q=0.0):
    """Fixed-strike lookback call (Hull 11e GE §26.11 pp.624-625). Pays max(max S - K, 0).

    Hull's put-call parity type relation: with ``S*_max = max(S_max, K)``,
    ``c_fix = p*_fl + S e^{-qT} - K e^{-rT}``, where ``p*_fl`` is
    :func:`lookback_floating_put` evaluated with ``S_max`` replaced by
    ``S*_max``. ``S_max`` is the maximum observed to date (``>= S``). The
    ``r == q`` limit raises ``ValueError`` (inherited).
    """
    if K <= 0.0:
        raise ValueError(f"K must be > 0, got {K}")
    if S_max < S:
        raise ValueError(f"S_max must be >= S (maximum to date), got S_max={S_max}, S={S}")
    p_star = lookback_floating_put(S, max(S_max, K), r, sigma, T, q)
    return p_star + S * math.exp(-q * T) - K * math.exp(-r * T)


def lookback_fixed_put(S, K, S_min, r, sigma, T, q=0.0):
    """Fixed-strike lookback put (Hull 11e GE §26.11 p.625). Pays max(K - min S, 0).

    With ``S*_min = min(S_min, K)``, ``p_fix = c*_fl + K e^{-rT} - S e^{-qT}``,
    where ``c*_fl`` is :func:`lookback_floating_call` evaluated with ``S_min``
    replaced by ``S*_min``. ``S_min`` is the minimum observed to date
    (``<= S``). The ``r == q`` limit raises ``ValueError`` (inherited).
    """
    if K <= 0.0:
        raise ValueError(f"K must be > 0, got {K}")
    if S_min > S:
        raise ValueError(f"S_min must be <= S (minimum to date), got S_min={S_min}, S={S}")
    c_star = lookback_floating_call(S, min(S_min, K), r, sigma, T, q)
    return c_star + K * math.exp(-r * T) - S * math.exp(-q * T)


def _exp_integral(rate, T):
    """Stable value of integral_0^T exp(rate*t) dt."""
    x = rate * T
    if abs(x) < 1e-7:
        return T * (1.0 + x / 2.0 + x**2 / 6.0 + x**3 / 24.0 + x**4 / 120.0)
    return math.expm1(x) / rate


def _exp_integral_derivative(rate, T):
    """Derivative of :func:`_exp_integral` with respect to ``rate``."""
    x = rate * T
    if abs(x) < 1e-5:
        return T**2 * (0.5 + x / 3.0 + x**2 / 8.0 + x**3 / 30.0 + x**4 / 144.0)
    return T**2 * (x * math.exp(x) - math.expm1(x)) / x**2


def asian_moments(S, r, sigma, T, q=0.0, times=None):
    """First two moments of the arithmetic average (Hull eq. 26.3-26.4 inputs).

    ``times=None`` averages continuously over ``[0, T]``. A sequence of
    observation times instead averages ``S`` at those dates; the discrete form
    is exact, needs no ``r != q``, and reproduces Hull's 12/52/250-observation
    prices with dates ``i*T/m`` (today excluded, maturity included).
    """
    if S <= 0.0 or sigma <= 0.0 or T <= 0.0:
        raise ValueError("S, sigma, and T must be > 0")
    b = r - q
    if times is None:
        m1 = S * _exp_integral(b, T) / T
        delta = b + sigma**2
        if abs(delta * T) < 1e-7:
            second_integral = _exp_integral_derivative(b, T)
        else:
            second_integral = (_exp_integral(2.0 * b + sigma**2, T) - _exp_integral(b, T)) / delta
        return m1, 2.0 * S**2 * second_integral / T**2
    dates = sorted(float(t) for t in times)
    if not dates or dates[0] <= 0.0 or dates[-1] > T:
        raise ValueError("observation times must be positive and at most T")
    forwards = [S * math.exp(b * t) for t in dates]
    count = len(dates)
    m1 = math.fsum(forwards) / count
    # With the dates sorted, min(t_i, t_j) = t_i for j > i, so a suffix sum of the
    # forwards turns the double sum for E[A^2] into a single pass.
    suffix = 0.0
    terms = []
    for index in range(count - 1, -1, -1):
        weight = forwards[index] * math.exp(sigma**2 * dates[index])
        terms.append(weight * (forwards[index] + 2.0 * suffix))
        suffix += forwards[index]
    return m1, math.fsum(terms) / count**2


def _moment_matched_black(m1, m2, K, r, T, kind):
    """Black-76 on the moment-matched lognormal average (Hull eq. 26.3-26.4)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    sigma_a = math.sqrt(math.log(m2 / m1**2) / T)
    d1 = (math.log(m1 / K) + 0.5 * sigma_a**2 * T) / (sigma_a * math.sqrt(T))
    d2 = d1 - sigma_a * math.sqrt(T)
    if kind == "call":
        return math.exp(-r * T) * (m1 * norm.cdf(d1) - K * norm.cdf(d2))
    return math.exp(-r * T) * (K * norm.cdf(-d2) - m1 * norm.cdf(-d1))


def asian_average_price(S, K, r, sigma, T, q=0.0, kind="call", times=None):
    """Average-price Asian call or put by Turnbull-Wakeman (Hull §26.13).

    Moment matching is an approximation: the arithmetic average is not
    lognormal. Over the 119 measured rows whose independent reference exceeds
    0.5 the error runs from +23.35% to -6.85%; the 25 rows below that price
    reach -18.29%. It has no single direction in moneyness -- both signs occur
    at the same spot-to-strike ratio in different markets -- so quote the
    measured table and its domain of use with the price
    (`docs/SECTION_26_13_REVIEW_2026-09-16.md`). Put-call parity
    ``C - P = exp(-r*T)*(M1 - K)`` holds exactly whatever the error.
    """
    if S <= 0.0 or K <= 0.0 or sigma <= 0.0 or T <= 0.0:
        raise ValueError("S, K, sigma, and T must be > 0")
    m1, m2 = asian_moments(S, r, sigma, T, q=q, times=times)
    return _moment_matched_black(m1, m2, K, r, T, kind)


def asian_call_turnbull_wakeman(S, K, r, sigma, T, q=0.0):
    """Average-price Asian call via Turnbull-Wakeman moment matching into
    Black-76 (Hull eq. 26.3/26.4, continuous arithmetic average)."""
    return asian_average_price(S, K, r, sigma, T, q=q, kind="call")


def asian_seasoned_average_price(S, K, r, sigma, elapsed, remaining, observed_average,
                                 q=0.0, kind="call"):
    """Seasoned average-price option through Hull's strike shift (Hull p.627).

    With ``t1`` of the averaging window already observed at average ``Sbar`` and
    ``t2`` left, the payoff is ``t2/(t1+t2)`` of a newly issued option struck at
    ``K* = ((t1+t2)/t2)*K - (t1/t2)*Sbar``. A non-positive ``K*`` means a call
    is certain to be exercised, so it is worth the scaled forward on the
    remaining average and the put is worthless.
    """
    if elapsed < 0.0 or remaining <= 0.0:
        raise ValueError("elapsed must be >= 0 and remaining must be > 0")
    if observed_average <= 0.0 and elapsed > 0.0:
        raise ValueError("observed_average must be > 0 once the window has started")
    window = elapsed + remaining
    weight = remaining / window
    shifted = K / weight - observed_average * elapsed / remaining
    if shifted > 0.0:
        return weight * asian_average_price(S, shifted, r, sigma, remaining, q=q, kind=kind)
    if kind == "put":
        return 0.0
    if kind != "call":
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    m1, _ = asian_moments(S, r, sigma, remaining, q=q)
    return weight * math.exp(-r * remaining) * (m1 - shifted)


def asian_average_strike(S, r, sigma, T, q=0.0, kind="call", times=None):
    """Average-strike option as an exchange option (Hull p.627).

    An average-strike call pays ``max(0, S_T - Save)``, so it exchanges the
    average for the terminal price. Hull prices it as a Margrabe exchange
    option "when Save is assumed to be lognormal" without fixing the log
    covariance; this uses the geometric-average proxy
    ``Cov(ln Save, ln S_T) = sigma^2 * mean(observation times)``, exact for the
    geometric average. Both approximations are measured in
    `docs/SECTION_26_13_REVIEW_2026-09-16.md`.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    dates = None if times is None else sorted(float(t) for t in times)
    if dates is not None and len(dates) == 1 and dates[0] == T:
        return 0.0  # a single observation at maturity makes the average the terminal price
    m1, m2 = asian_moments(S, r, sigma, T, q=q, times=dates)
    mean_time = T / 2.0 if dates is None else math.fsum(dates) / len(dates)
    sigma_a = math.sqrt(math.log(m2 / m1**2) / T)
    covariance = sigma**2 * mean_time
    # The three terms cancel to zero as the average collapses onto S_T, so read a
    # residue below the rounding scale of sigma^2*T as the exact zero it stands for.
    variance = sigma_a**2 * T + sigma**2 * T - 2.0 * covariance
    spread = math.sqrt(variance) if variance > 1e-12 * sigma**2 * T else 0.0
    terminal = S * math.exp((r - q) * T)
    if spread <= 0.0:
        payoff = max(terminal - m1, 0.0) if kind == "call" else max(m1 - terminal, 0.0)
        return math.exp(-r * T) * payoff
    d1 = (math.log(terminal / m1) + 0.5 * spread**2) / spread
    d2 = d1 - spread
    if kind == "call":
        return math.exp(-r * T) * (terminal * norm.cdf(d1) - m1 * norm.cdf(d2))
    return math.exp(-r * T) * (m1 * norm.cdf(-d2) - terminal * norm.cdf(-d1))


def exchange_spread_volatility(sigma_u, sigma_v, rho):
    """Volatility of V/U: sqrt(su^2 + sv^2 - 2 rho su sv) (Hull §26.14).

    Dropping the cross term is the usual mistake and overprices every
    correlated contract; the independent references in
    `docs/validation/section-26-14/` reject it on all 21 correlated rows.
    """
    if sigma_u < 0.0 or sigma_v < 0.0:
        raise ValueError("volatilities must be >= 0")
    if not -1.0 <= rho <= 1.0:
        raise ValueError("rho must lie in [-1, 1]")
    return math.sqrt(max(sigma_u**2 + sigma_v**2 - 2.0 * rho * sigma_u * sigma_v, 0.0))


def exchange_option(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0):
    """Margrabe option to exchange asset U for asset V (Hull eq. 26.5).

    The price does not depend on the risk-free rate, and r is not an argument:
    a higher rate raises both risk-neutral growth rates and the discount rate by
    the same amount. Measured, not assumed - the same 24 contracts priced at
    r = 0, 8% and -2% move by at most 1.8e-14
    (`docs/validation/section-26-14/numerical-check.json`).
    """
    if U0 <= 0.0 or V0 <= 0.0 or T <= 0.0:
        raise ValueError("U0, V0 and T must be > 0")
    sig = exchange_spread_volatility(sigma_u, sigma_v, rho)
    if sig <= 0.0:
        # The ratio is deterministic, so only the discounted forward spread is left.
        return max(V0 * math.exp(-q_v * T) - U0 * math.exp(-q_u * T), 0.0)
    d1 = (math.log(V0 / U0) + (q_u - q_v + 0.5 * sig**2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return V0 * math.exp(-q_v * T) * norm.cdf(d1) - U0 * math.exp(-q_u * T) * norm.cdf(d2)


def exchange_option_american(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0, steps=1024):
    """American exchange option on a CRR tree (Rubinstein 1991; Hull §26.14).

    Hull states the equivalence this uses: the contract is ``U0`` American calls
    on an asset worth ``V/U`` struck at 1.0 when the risk-free rate is ``q_u``
    and the dividend yield is ``q_v``. Early exercise is therefore worth nothing
    when ``q_v = 0``; the saved references measure a premium of 1.9e-13 there
    and up to 4.28 when ``q_v > 0``.

    The tree is a finite grid, so it carries a discretisation residual, not an
    error bound. Against the closed form where the two must agree (``q_v = 0``)
    the worst residual over the saved markets halves with each doubling:
    0.0457 at 128 steps, 0.0114 at 512, 0.0057 at the default 1024.
    """
    if U0 <= 0.0 or V0 <= 0.0 or T <= 0.0:
        raise ValueError("U0, V0 and T must be > 0")
    if steps < 1:
        raise ValueError("steps must be >= 1")
    volatility = exchange_spread_volatility(sigma_u, sigma_v, rho)
    if volatility <= 0.0:
        raise ValueError("a deterministic ratio has no tree; use exchange_option")
    dt = T / steps
    up = math.exp(volatility * math.sqrt(dt))
    growth = math.exp((q_u - q_v) * dt)
    probability = (growth - 1.0 / up) / (up - 1.0 / up)
    if not 0.0 < probability < 1.0:
        raise ValueError(f"tree probability {probability} outside (0, 1); use more steps")
    discount = math.exp(-q_u * dt)
    exponents = np.arange(-steps, steps + 1, 2, dtype=float)
    ratio = (V0 / U0) * up**exponents
    values = np.maximum(ratio - 1.0, 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * (probability * values[1:] + (1.0 - probability) * values[:-1])
        ratio = (V0 / U0) * up ** np.arange(-step, step + 1, 2, dtype=float)
        values = np.maximum(values, ratio - 1.0)
    return U0 * float(values[0])


def better_of_two_assets(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0):
    """Value of receiving max(U_T, V_T) = U_T + max(V_T - U_T, 0) (Hull §26.14)."""
    return U0 * math.exp(-q_u * T) + exchange_option(
        U0, V0, sigma_u, sigma_v, rho, T, q_u=q_u, q_v=q_v
    )


def worse_of_two_assets(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0):
    """Value of receiving min(U_T, V_T) = V_T - max(V_T - U_T, 0) (Hull §26.14)."""
    return V0 * math.exp(-q_v * T) - exchange_option(
        U0, V0, sigma_u, sigma_v, rho, T, q_u=q_u, q_v=q_v
    )


def _validated_basket_inputs(spots, weights, rate, dividends, volatilities, correlations, expiry):
    """Return validated numeric basket inputs for the public basket pricers."""
    try:
        spot_array = np.asarray(spots, dtype=float)
        weight_array = np.asarray(weights, dtype=float)
        dividend_array = np.asarray(dividends, dtype=float)
        volatility_array = np.asarray(volatilities, dtype=float)
        correlation_array = np.asarray(correlations, dtype=float)
        scalar_array = np.asarray([rate, expiry], dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("basket inputs must be numeric") from error

    arrays = (spot_array, weight_array, dividend_array, volatility_array)
    if any(array.ndim != 1 for array in arrays) or spot_array.size == 0:
        raise ValueError("spots, weights, dividends, and volatilities must be nonempty one-dimensional sequences")
    n_assets = spot_array.size
    if any(array.size != n_assets for array in arrays[1:]):
        raise ValueError("spots, weights, dividends, and volatilities must have equal lengths")
    if correlation_array.shape != (n_assets, n_assets):
        raise ValueError("correlations must be a square matrix aligned with the asset inputs")
    if not all(np.all(np.isfinite(array)) for array in (*arrays, correlation_array, scalar_array)):
        raise ValueError("basket inputs must be finite")
    if np.any(spot_array <= 0.0):
        raise ValueError("spots must be > 0")
    if np.any(weight_array < 0.0) or not np.any(weight_array > 0.0):
        raise ValueError("weights must be nonnegative with at least one positive weight")
    if np.any(volatility_array < 0.0):
        raise ValueError("volatilities must be >= 0")
    if expiry <= 0.0:
        raise ValueError("expiry must be > 0")
    if not np.allclose(correlation_array, correlation_array.T, rtol=0.0, atol=1e-12):
        raise ValueError("correlations must be symmetric")
    if not np.allclose(np.diag(correlation_array), 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("correlations must have a unit diagonal")
    try:
        eigenvalues = np.linalg.eigvalsh(correlation_array)
    except np.linalg.LinAlgError as error:
        raise ValueError("correlations must be positive semidefinite") from error
    if np.min(eigenvalues) < -1e-12:
        raise ValueError("correlations must be positive semidefinite")

    return spot_array, weight_array, float(rate), dividend_array, volatility_array, correlation_array, float(expiry)


def basket_moments(spots, weights, rate, dividends, volatilities, correlations, expiry):
    """Return exact first and second moments of a positive GBM basket (Hull §26.15).

    ``spots``, ``weights``, ``dividends`` and ``volatilities`` are aligned
    numerical sequences. Weights are nonnegative holdings with at least one
    positive value; ``correlations`` is a symmetric positive-semidefinite
    unit-diagonal matrix. Rates and dividend yields are continuously
    compounded and ``expiry`` is measured in years.
    """
    spots, weights, rate, dividends, volatilities, correlations, expiry = _validated_basket_inputs(
        spots, weights, rate, dividends, volatilities, correlations, expiry
    )
    forwards = weights * spots * np.exp((rate - dividends) * expiry)
    exponents = np.outer(volatilities, volatilities) * correlations * expiry
    with np.errstate(over="raise", invalid="raise"):
        try:
            second_moment = float(np.sum(np.outer(forwards, forwards) * np.exp(exponents)))
        except FloatingPointError as error:
            raise ValueError("basket inputs produce nonfinite moments") from error
    first_moment = float(np.sum(forwards))
    if not math.isfinite(first_moment) or not math.isfinite(second_moment):
        raise ValueError("basket inputs produce nonfinite moments")
    return first_moment, second_moment


def basket_option_price(spots, weights, strike, rate, dividends, volatilities, correlations, expiry, kind="call"):
    """Price a European positive-basket option with the §26.15 lognormal proxy.

    The first two basket moments are exact under correlated risk-neutral GBM;
    replacing the basket with their matched lognormal distribution is an
    approximation except for single-asset and proportional perfectly
    correlated baskets. ``kind`` is either ``"call"`` or ``"put"``.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    try:
        strike = float(strike)
    except (TypeError, ValueError) as error:
        raise ValueError("strike must be a finite scalar > 0") from error
    if not math.isfinite(strike) or strike <= 0.0:
        raise ValueError("strike must be a finite scalar > 0")

    first_moment, second_moment = basket_moments(
        spots, weights, rate, dividends, volatilities, correlations, expiry
    )
    log_variance = math.log(second_moment) - 2.0 * math.log(first_moment)
    if log_variance < -1e-12:
        raise ValueError("basket moments imply a negative matched variance")
    discount = math.exp(-rate * expiry)
    if log_variance <= 1e-12:
        intrinsic = first_moment - strike if kind == "call" else strike - first_moment
        return discount * max(intrinsic, 0.0)

    matched_volatility = math.sqrt(log_variance / expiry)
    volatility_time = matched_volatility * math.sqrt(expiry)
    d1 = (math.log(first_moment / strike) + 0.5 * log_variance) / volatility_time
    d2 = d1 - volatility_time
    if kind == "call":
        return discount * (first_moment * norm.cdf(d1) - strike * norm.cdf(d2))
    return discount * (strike * norm.cdf(-d2) - first_moment * norm.cdf(-d1))
