"""Advanced Monte-Carlo: variance reduction and quasi-MC (A3 deep-dive).

Builds on :mod:`hullkit.mc` (which already has antithetic sampling and the
Longstaff-Schwartz LSM American pricer). Adds control variates, importance
sampling for deep-OTM options, and Sobol quasi-Monte-Carlo, plus a convergence
helper used by the figures. Reference: Glasserman, *Monte Carlo Methods in
Financial Engineering* (Ch.4 variance reduction, Ch.5 QMC).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, qmc

from . import bsm, mc


def _terminal(S0, r, sigma, T, z):
    return S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * z)


def plain_price(S0, K, r, sigma, T, n_paths, rng):
    """Plain risk-neutral MC call price (price, standard_error)."""
    z = rng.standard_normal(n_paths)
    disc = np.exp(-r * T) * np.maximum(_terminal(S0, r, sigma, T, z) - K, 0.0)
    return float(disc.mean()), float(disc.std(ddof=1) / np.sqrt(n_paths))


def control_variate_price(S0, K, r, sigma, T, n_paths, rng):
    """Call price with the discounted underlying as control (E[e^{-rT}S_T]=S0).

    The optimal coefficient beta is estimated from the sample covariance; the
    standard error collapses because payoff and S_T are strongly correlated.
    """
    z = rng.standard_normal(n_paths)
    s_t = _terminal(S0, r, sigma, T, z)
    payoff = np.exp(-r * T) * np.maximum(s_t - K, 0.0)
    control = np.exp(-r * T) * s_t  # E[control] = S0
    cov = np.cov(payoff, control)
    beta = cov[0, 1] / cov[1, 1]
    adjusted = payoff - beta * (control - S0)
    return float(adjusted.mean()), float(adjusted.std(ddof=1) / np.sqrt(n_paths))


def importance_sampling_price(S0, K, r, sigma, T, n_paths, rng, shift=None):
    """Deep-OTM call via drift-shift importance sampling (Glasserman §4.6).

    Sample z ~ N(shift, 1) so paths land in-the-money, then reweight by the
    likelihood ratio dP/dQ = exp(-shift*z + ½ shift²). ``shift`` defaults to the
    z that puts S_T at the strike.
    """
    if shift is None:
        shift = (np.log(K / S0) - (r - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    z = rng.standard_normal(n_paths) + shift
    s_t = _terminal(S0, r, sigma, T, z)
    lr = np.exp(-shift * z + 0.5 * shift**2)
    disc = np.exp(-r * T) * np.maximum(s_t - K, 0.0) * lr
    return float(disc.mean()), float(disc.std(ddof=1) / np.sqrt(n_paths))


def qmc_price(S0, K, r, sigma, T, m, kind="call", seed=0):
    """Sobol quasi-MC price using N=2^m low-discrepancy points."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    u = qmc.Sobol(d=1, scramble=True, seed=seed).random_base2(m).ravel()
    u = np.clip(u, 1e-10, 1.0 - 1e-10)
    s_t = _terminal(S0, r, sigma, T, norm.ppf(u))
    payoff = np.maximum(s_t - K, 0.0) if kind == "call" else np.maximum(K - s_t, 0.0)
    return float(np.exp(-r * T) * payoff.mean())


def error_vs_n(S0, K, r, sigma, T, ms=range(6, 16), seed=0):
    """|price - BSM| vs N=2^m for plain MC, antithetic, control variate, Sobol QMC."""
    true = bsm.call_price(S0, K, r, sigma, T)
    out = {"N": [], "plain": [], "antithetic": [], "control_variate": [], "qmc": []}
    for m in ms:
        n = 2**m
        out["N"].append(n)
        out["plain"].append(
            abs(plain_price(S0, K, r, sigma, T, n, np.random.default_rng(seed))[0] - true)
        )
        anti = mc.price_european_mc(
            S0, K, r, sigma, T, n_paths=n, antithetic=True, rng=np.random.default_rng(seed)
        )[0]
        out["antithetic"].append(abs(anti - true))
        out["control_variate"].append(
            abs(control_variate_price(S0, K, r, sigma, T, n, np.random.default_rng(seed))[0] - true)
        )
        out["qmc"].append(abs(qmc_price(S0, K, r, sigma, T, m, seed=seed) - true))
    return out
