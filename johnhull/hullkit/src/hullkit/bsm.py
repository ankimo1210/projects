"""Black-Scholes-Merton analytic formulas (Hull 11e, Ch.15 / Ch.17).

The continuous yield ``q`` generalizes the formulas:
stock index -> q = dividend yield, currency -> q = foreign risk-free rate,
futures -> q = r (Black-76 with S = futures price).
"""

import numpy as np
from scipy.stats import norm


def _validate_price_inputs(S, K, sigma, T):
    if np.any(~np.isfinite(np.asarray(S, dtype=float))) or np.any(np.asarray(S) <= 0.0):
        raise ValueError("S must contain only finite values > 0")
    if np.any(~np.isfinite(np.asarray(K, dtype=float))) or np.any(np.asarray(K) <= 0.0):
        raise ValueError("K must contain only finite values > 0")
    sigma_array = np.asarray(sigma, dtype=float)
    if np.any(~np.isfinite(sigma_array)) or np.any(sigma_array < 0.0):
        raise ValueError("sigma must be finite and >= 0")
    time_array = np.asarray(T, dtype=float)
    if np.any(~np.isfinite(time_array)) or np.any(time_array < 0.0):
        raise ValueError("T must be finite and >= 0")


def d1(S, K, r, sigma, T, q=0.0):
    """Hull eq. (15.20) numerator term."""
    _validate_price_inputs(S, K, sigma, T)
    if np.any(np.asarray(sigma) == 0.0) or np.any(np.asarray(T) == 0.0):
        raise ValueError("d1 is undefined when sigma or T is zero")
    return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def d2(S, K, r, sigma, T, q=0.0):
    """Hull eq. (15.20): ``d1 - sigma * sqrt(T)``."""
    return d1(S, K, r, sigma, T, q) - sigma * np.sqrt(T)


def _price_mixed_boundaries(S, K, r, sigma, T, q, *, is_call):
    """Price element-wise when `T`/`sigma` mix zero and positive entries.

    Three exclusive regimes: `T == 0` -> intrinsic value; `T > 0, sigma == 0`
    -> discounted deterministic payoff; otherwise the BSM formula. `d1` is
    evaluated only on the diffusive elements, so the zero boundaries never
    reach the undefined `sigma * sqrt(T)` division.

    Reached only when a boundary and a diffusive element coexist. Uniform
    inputs keep the original whole-array expressions in `call_price`/
    `put_price`: `np.exp`/`np.log` can round differently in their SIMD and
    scalar paths, so recomputing a scalar-shaped call through the broadcast
    machinery here would shift results by ~1 ulp -- enough for a downstream
    calibration optimizer to land elsewhere and break artifact reproducibility.
    """
    broadcast = np.broadcast_arrays(
        *(np.asarray(v, dtype=float) for v in (S, K, r, sigma, T, q))
    )
    shape = broadcast[0].shape
    s, k, r_b, sigma_b, t, q_b = (np.atleast_1d(a) for a in broadcast)

    out = np.empty(s.shape, dtype=float)
    at_expiry = t == 0.0
    zero_vol = (~at_expiry) & (sigma_b == 0.0)
    diffusive = ~(at_expiry | zero_vol)

    intrinsic = s[at_expiry] - k[at_expiry]
    out[at_expiry] = np.maximum(intrinsic if is_call else -intrinsic, 0.0)

    forward = s[zero_vol] * np.exp(-q_b[zero_vol] * t[zero_vol]) - k[zero_vol] * np.exp(
        -r_b[zero_vol] * t[zero_vol]
    )
    out[zero_vol] = np.maximum(forward if is_call else -forward, 0.0)

    if np.any(diffusive):
        s_d, k_d, r_d, sigma_d, t_d, q_d = (
            a[diffusive] for a in (s, k, r_b, sigma_b, t, q_b)
        )
        vol_time = sigma_d * np.sqrt(t_d)
        d_1 = (np.log(s_d / k_d) + (r_d - q_d + 0.5 * sigma_d**2) * t_d) / vol_time
        d_2 = d_1 - vol_time
        if is_call:
            out[diffusive] = s_d * np.exp(-q_d * t_d) * norm.cdf(d_1) - k_d * np.exp(
                -r_d * t_d
            ) * norm.cdf(d_2)
        else:
            out[diffusive] = k_d * np.exp(-r_d * t_d) * norm.cdf(-d_2) - s_d * np.exp(
                -q_d * t_d
            ) * norm.cdf(-d_1)

    return out[0] if shape == () else out.reshape(shape)


def _has_mixed_boundaries(sigma, T) -> bool:
    """True when a zero-maturity/zero-vol element coexists with a diffusive one."""
    sigma_array = np.asarray(sigma, dtype=float)
    time_array = np.asarray(T, dtype=float)
    at_boundary = (time_array == 0.0) | (sigma_array == 0.0)
    return bool(np.any(at_boundary) and not np.all(at_boundary))


def call_price(S, K, r, sigma, T, q=0.0):
    """European call price, Hull eq. (15.20) / (17.4).

    Boundaries are handled per element, so `T` and `sigma` vectors may mix
    zero and positive entries: zero maturity gives the intrinsic value and
    zero volatility the discounted deterministic payoff.
    """
    _validate_price_inputs(S, K, sigma, T)
    if np.all(np.asarray(T) == 0.0):
        return np.maximum(np.asarray(S) - K, 0.0)
    if np.all(np.asarray(sigma) == 0.0):
        return np.maximum(np.asarray(S) * np.exp(-q * T) - K * np.exp(-r * T), 0.0)
    if _has_mixed_boundaries(sigma, T):
        return _price_mixed_boundaries(S, K, r, sigma, T, q, is_call=True)
    return S * np.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q)) - K * np.exp(-r * T) * norm.cdf(
        d2(S, K, r, sigma, T, q)
    )


def put_price(S, K, r, sigma, T, q=0.0):
    """European put price, Hull eq. (15.21) / (17.5).

    Same element-wise boundary handling as `call_price`.
    """
    _validate_price_inputs(S, K, sigma, T)
    if np.all(np.asarray(T) == 0.0):
        return np.maximum(K - np.asarray(S), 0.0)
    if np.all(np.asarray(sigma) == 0.0):
        return np.maximum(K * np.exp(-r * T) - np.asarray(S) * np.exp(-q * T), 0.0)
    if _has_mixed_boundaries(sigma, T):
        return _price_mixed_boundaries(S, K, r, sigma, T, q, is_call=False)
    return K * np.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q)) - S * np.exp(-q * T) * norm.cdf(
        -d1(S, K, r, sigma, T, q)
    )


def call_delta(S, K, r, sigma, T, q=0.0):
    """Analytic call delta e^{-qT} N(d1) (Hull Ch.19; needed for tree comparisons)."""
    return np.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q))


def put_delta(S, K, r, sigma, T, q=0.0):
    """Analytic put delta e^{-qT} (N(d1) - 1)."""
    return np.exp(-q * T) * (norm.cdf(d1(S, K, r, sigma, T, q)) - 1.0)


def gamma(S, K, r, sigma, T, q=0.0):
    """Gamma d2V/dS2 — identical for calls and puts (Hull Ch.19, Table 19.6)."""
    return np.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) / (S * sigma * np.sqrt(T))


def vega(S, K, r, sigma, T, q=0.0):
    """Vega dV/dsigma per 1.0 of vol (divide by 100 for per-1%); same for calls/puts."""
    return S * np.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) * np.sqrt(T)


def call_theta(S, K, r, sigma, T, q=0.0):
    """Call theta per YEAR (divide by 365 for per-calendar-day), Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return (
        -S * np.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * np.sqrt(T))
        - r * K * np.exp(-r * T) * norm.cdf(d_2)
        + q * S * np.exp(-q * T) * norm.cdf(d_1)
    )


def put_theta(S, K, r, sigma, T, q=0.0):
    """Put theta per YEAR, Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return (
        -S * np.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * np.sqrt(T))
        + r * K * np.exp(-r * T) * norm.cdf(-d_2)
        - q * S * np.exp(-q * T) * norm.cdf(-d_1)
    )


def call_rho(S, K, r, sigma, T, q=0.0):
    """Call rho dV/dr, Hull Table 19.6."""
    return K * T * np.exp(-r * T) * norm.cdf(d2(S, K, r, sigma, T, q))


def put_rho(S, K, r, sigma, T, q=0.0):
    """Put rho dV/dr (negative), Hull Table 19.6."""
    return -K * T * np.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q))


def vanna(S, K, r, sigma, T, q=0.0):
    """Vanna = d^2V/(dS dsigma) = dDelta/dsigma (Hull Ch.19, higher-order)."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return -np.exp(-q * T) * norm.pdf(d_1) * d_2 / sigma


def vomma(S, K, r, sigma, T, q=0.0):
    """Vomma (volga) = d^2V/dsigma^2 = vega * d1 d2 / sigma (Hull Ch.19)."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * np.sqrt(T)
    return vega(S, K, r, sigma, T, q) * d_1 * d_2 / sigma
