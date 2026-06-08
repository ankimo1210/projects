"""Closed-form exotic option pricers (Hull 11e, Ch.26)."""

import math

from scipy.stats import norm

from . import bsm


def _d1d2(S, K, r, sigma, T, q):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


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
    sqt = sigma * math.sqrt(T)
    lam = (r - q + 0.5 * sigma**2) / sigma**2
    x1 = math.log(S / H) / sqt + lam * sqt
    y1 = math.log(H / S) / sqt + lam * sqt
    y = math.log(H**2 / (S * K)) / sqt + lam * sqt

    def _pow(exp_):
        return (H / S) ** exp_

    if barrier in ("down-and-in", "down-and-out"):
        if H <= K:
            cdi = (
                S * math.exp(-q * T) * _pow(2 * lam) * norm.cdf(y)
                - K * math.exp(-r * T) * _pow(2 * lam - 2) * norm.cdf(y - sqt)
            )
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


def asian_call_turnbull_wakeman(S, K, r, sigma, T, q=0.0):
    """Average-price Asian call via Turnbull-Wakeman moment matching into
    Black-76 (Hull eq. 26.3/26.4, continuous arithmetic average)."""
    b = r - q
    m1 = (math.exp(b * T) - 1.0) / (b * T) * S
    m2 = (
        2.0 * math.exp((2.0 * b + sigma**2) * T) * S**2
        / ((b + sigma**2) * (2.0 * b + sigma**2) * T**2)
        + 2.0 * S**2 / (b * T**2)
        * (1.0 / (2.0 * b + sigma**2) - math.exp(b * T) / (b + sigma**2))
    )
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
