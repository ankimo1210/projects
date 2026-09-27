"""Smile models: SABR (Hagan 2002 lognormal expansion), raw SVI, and smile metrics."""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.stats import norm


# -------------------------------------------------------------------- SABR
def sabr_black_vol(F, K, T, alpha, beta, rho, nu):
    """Hagan et al. (2002) Black implied vol for dF = a F^beta dW1, da = nu a dW2, <dW1,dW2> = rho dt.

    ``alpha`` is the initial vol level (not vol-of-vol); ``nu`` is the vol-of-vol.
    Returns nan for non-positive F, K or T.
    """
    if F <= 0 or K <= 0 or T <= 0:
        return np.nan
    one_b = 1 - beta
    fk_mid = (F * K) ** (one_b / 2)
    correction = 1 + T * (
        one_b**2 / 24 * alpha**2 / fk_mid**2
        + rho * beta * nu * alpha / (4 * fk_mid)
        + (2 - 3 * rho**2) / 24 * nu**2
    )
    log_fk = np.log(F / K)
    if abs(log_fk) < 1e-12:
        return alpha / F**one_b * correction
    z = nu / alpha * fk_mid * log_fk
    x_z = np.log((np.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
    ratio = z / x_z if abs(z) > 1e-8 else 1 - 0.5 * rho * z
    denom = 1 + one_b**2 / 24 * log_fk**2 + one_b**4 / 1920 * log_fk**4
    return alpha / (fk_mid * denom) * ratio * correction


def sabr_alpha_from_atm_vol(F, T, atm_vol, beta, rho, nu):
    """Smallest positive alpha reproducing the target ATM Black vol; nan if none exists.

    With x = alpha / F**(1-beta), the Hagan ATM approximation is a cubic in x.
    Its large-alpha branch can turn down, so a fixed outer bracket can miss a root.
    """
    if F <= 0 or T <= 0 or atm_vol <= 0:
        return np.nan
    c0 = 1 + T * (2 - 3 * rho**2) * nu**2 / 24
    c1 = T * rho * beta * nu / 4
    c2 = T * (1 - beta) ** 2 / 24
    roots = np.roots([c2, c1, c0, -atm_vol])
    positive = [z.real for z in roots if z.real > 0 and abs(z.imag) < 1e-10 * max(1, abs(z.real))]
    return min(positive) * F ** (1 - beta) if positive else np.nan


def calibrate_sabr(F, T, strikes, market_vols, beta, x0=None):
    """Least-squares (alpha, rho, nu) for fixed beta. Returns (alpha, rho, nu, rmse_bp, fitted_vols)."""
    strikes = np.asarray(strikes, dtype=float)
    market_vols = np.asarray(market_vols, dtype=float)
    if x0 is None:
        x0 = (market_vols[len(market_vols) // 2] * F ** (1 - beta), -0.3, 0.4)

    def model(p):
        return np.array([sabr_black_vol(F, K, T, p[0], beta, p[1], p[2]) for K in strikes])

    def sse(p):
        v = model(p)
        return 1e6 if np.any(~np.isfinite(v)) else np.sum((v - market_vols) ** 2)

    bounds = [(1e-6, None), (-0.999, 0.999), (1e-4, 5.0)]
    res = minimize(sse, x0, method="L-BFGS-B", bounds=bounds)
    fitted = model(res.x)
    rmse_bp = np.sqrt(np.mean((fitted - market_vols) ** 2)) * 1e4
    return res.x[0], res.x[1], res.x[2], rmse_bp, fitted


# --------------------------------------------------------------------- SVI
def svi_total_variance(k, a, b, rho, m, sig):
    """Raw SVI: w(k) = a + b (rho (k-m) + sqrt((k-m)^2 + sig^2)), k = ln(K/F), w = vol^2 T."""
    k = np.asarray(k, dtype=float)
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sig**2))


def svi_density_g(k, a, b, rho, m, sig):
    """Gatheral-Jacquier (2014) g(k); the smile is free of butterfly arbitrage iff g >= 0 and w > 0."""
    k = np.asarray(k, dtype=float)
    x = k - m
    root = np.sqrt(x**2 + sig**2)
    w = svi_total_variance(k, a, b, rho, m, sig)
    w1 = b * (rho + x / root)
    w2 = b * sig**2 / root**3
    return (1 - k * w1 / (2 * w)) ** 2 - w1**2 / 4 * (1 / w + 0.25) + w2 / 2


def calibrate_svi(F, T, strikes, market_vols, x0=(None, 0.05, -0.3, 0.0, 0.1)):
    """Fit raw SVI total variance with a penalty on g(k) < 0 over k in [-1.5, 1.5].

    Returns (params, rmse_bp, fitted_vols). Slope bound b(1+|rho|) <= 4 (Rogers-Tehranchi) is a bound.
    """
    k = np.log(np.asarray(strikes, dtype=float) / F)
    w_mkt = np.asarray(market_vols, dtype=float) ** 2 * T
    k_check = np.linspace(-1.5, 1.5, 301)
    a0 = 0.5 * w_mkt.min() if x0[0] is None else x0[0]

    def obj(p):
        b, r = p[1], p[2]
        if b * (1 + abs(r)) > 4:
            return 1e6
        w = svi_total_variance(k_check, *p)
        if np.any(w <= 0):
            return 1e6
        g = svi_density_g(k_check, *p)
        penalty = 1e3 * np.sum(np.minimum(g, 0.0) ** 2)
        return np.sum((svi_total_variance(k, *p) - w_mkt) ** 2) / w_mkt.mean() ** 2 + penalty

    bounds = [(-1.0, 1.0), (1e-6, 4.0), (-0.999, 0.999), (-1.0, 1.0), (1e-4, 2.0)]
    res = minimize(obj, (a0, *x0[1:]), method="L-BFGS-B", bounds=bounds)
    fitted = np.sqrt(svi_total_variance(k, *res.x) / T)
    rmse_bp = np.sqrt(np.mean((fitted - market_vols) ** 2)) * 1e4
    return res.x, rmse_bp, fitted


# ---------------------------------------------------------- smile metrics
def delta_strike(F, T, vol_of_strike, target_delta):
    """Strike whose smile-consistent forward Black delta equals ``target_delta``.

    Call delta = N(d1), put delta = N(d1) - 1; ``vol_of_strike(K)`` is the smile.
    Returns nan when the smile is too extreme for the delta to be bracketed.
    """
    atm = vol_of_strike(F)
    lo, hi = F * np.exp(-8 * atm * np.sqrt(T)), F * np.exp(8 * atm * np.sqrt(T))

    def f(K):
        s = vol_of_strike(K)
        d1 = (np.log(F / K) + 0.5 * s**2 * T) / (s * np.sqrt(T))
        delta = norm.cdf(d1) if target_delta > 0 else norm.cdf(d1) - 1
        return delta - target_delta

    try:
        return brentq(f, lo, hi)
    except ValueError:
        return np.nan


def smile_metrics(F, T, vol_of_strike, delta=0.25):
    """ATM vol, delta risk reversal (call - put) and butterfly ((call + put)/2 - ATM)."""
    atm = vol_of_strike(F)
    k_c = delta_strike(F, T, vol_of_strike, delta)
    k_p = delta_strike(F, T, vol_of_strike, -delta)
    if np.isnan(k_c) or np.isnan(k_p):
        return atm, np.nan, np.nan
    v_c, v_p = vol_of_strike(k_c), vol_of_strike(k_p)
    return atm, v_c - v_p, 0.5 * (v_c + v_p) - atm
