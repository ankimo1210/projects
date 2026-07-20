"""Closed-form exotic option pricers (Hull 11e, Ch.26)."""

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


def barrier_call(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in"):
    """Barrier call closed forms (Hull §26.9). barrier in {down-and-in,
    down-and-out, up-and-in, up-and-out}. Uses in+out=vanilla complements."""
    valid = ("down-and-in", "down-and-out", "up-and-in", "up-and-out")
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.call_price(S, K, r, sigma, T, q)
    breached = (barrier.startswith("down") and H >= S) or (barrier.startswith("up") and H <= S)
    if breached:
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
        cui = vanilla  # up-and-in with H<=K knocks in almost surely (degenerate)
    return cui if barrier == "up-and-in" else vanilla - cui


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
