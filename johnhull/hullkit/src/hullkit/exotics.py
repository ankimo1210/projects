"""Closed-form exotic option pricers (Hull 11e, Ch.26).

Variance and volatility swaps (§26.16) live in :mod:`hullkit.variance_swaps`.
"""

import math

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
    """Barrier call closed forms (Hull §26.9). barrier in {down-and-in,
    down-and-out, up-and-in, up-and-out}. Uses in+out=vanilla complements.

    ``n_observations=None`` (default) is continuous monitoring. An integer
    ``m`` applies the Broadie-Glasserman-Kou shift of
    :func:`bgk_adjusted_barrier` (Hull 11e GE §26.9 p.622) to ``H`` before
    pricing; the already-breached guard still compares the spot with the
    contract barrier ``H``."""
    valid = _BARRIER_TYPES
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.call_price(S, K, r, sigma, T, q)
    breached = (barrier.startswith("down") and H >= S) or (barrier.startswith("up") and H <= S)
    if breached:
        return vanilla if barrier.endswith("in") else 0.0
    if n_observations is not None:
        H = bgk_adjusted_barrier(H, sigma, T, n_observations, barrier)
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
        cui = vanilla  # up-and-in with H<=K knocks in almost surely (degenerate)
    return cui if barrier == "up-and-in" else vanilla - cui


def barrier_put(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in", n_observations=None):
    """Barrier put closed forms (Hull 11e GE §26.9 pp.621-622).

    ``barrier`` in {down-and-in, down-and-out, up-and-in, up-and-out}; the
    signature, validation and already-breached guard mirror
    :func:`barrier_call` (a down barrier at or above the spot, or an up barrier
    at or below it, returns the vanilla put for knock-ins and 0 for
    knock-outs). Hull's branches: up barriers use the ``p_ui`` formula when
    ``H >= K`` and the ``p_uo`` formula when ``H < K``; a down barrier with
    ``H >= K`` gives ``p_do = 0`` and ``p_di = p``, otherwise the ``p_di``
    formula. The complement in each pair is ``vanilla put - value`` (in + out =
    vanilla). ``n_observations`` applies the Broadie-Glasserman-Kou discrete
    monitoring shift exactly as in :func:`barrier_call`.
    """
    valid = _BARRIER_TYPES
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.put_price(S, K, r, sigma, T, q)
    breached = (barrier.startswith("down") and H >= S) or (barrier.startswith("up") and H <= S)
    if breached:
        return vanilla if barrier.endswith("in") else 0.0
    if n_observations is not None:
        H = bgk_adjusted_barrier(H, sigma, T, n_observations, barrier)
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


def asian_call_turnbull_wakeman(S, K, r, sigma, T, q=0.0):
    """Average-price Asian call via Turnbull-Wakeman moment matching into
    Black-76 (Hull eq. 26.3/26.4, continuous arithmetic average)."""
    if S <= 0.0 or K <= 0.0 or sigma <= 0.0 or T <= 0.0:
        raise ValueError("S, K, sigma, and T must be > 0")
    b = r - q
    m1 = S * _exp_integral(b, T) / T
    delta = b + sigma**2
    if abs(delta * T) < 1e-7:
        second_integral = _exp_integral_derivative(b, T)
    else:
        second_integral = (_exp_integral(2.0 * b + sigma**2, T) - _exp_integral(b, T)) / delta
    m2 = 2.0 * S**2 * second_integral / T**2
    f0 = m1
    sigma_a = math.sqrt(math.log(m2 / m1**2) / T)
    d1 = (math.log(f0 / K) + 0.5 * sigma_a**2 * T) / (sigma_a * math.sqrt(T))
    d2 = d1 - sigma_a * math.sqrt(T)
    return math.exp(-r * T) * (f0 * norm.cdf(d1) - K * norm.cdf(d2))


def exchange_option(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0):
    """Margrabe option to exchange asset U for asset V (Hull eq. 26.5).
    r-independent: drift and discounting cancel."""
    sig = math.sqrt(sigma_u**2 + sigma_v**2 - 2.0 * rho * sigma_u * sigma_v)
    d1 = (math.log(V0 / U0) + (q_u - q_v + 0.5 * sig**2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return V0 * math.exp(-q_v * T) * norm.cdf(d1) - U0 * math.exp(-q_u * T) * norm.cdf(d2)
