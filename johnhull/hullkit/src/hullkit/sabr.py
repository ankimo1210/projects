"""SABR model — Hagan's implied-volatility expansion (A2 deep-dive).

    dF = alpha F^beta dW1,   d(alpha) = nu alpha dW2,   d<W1,W2> = rho dt.

:func:`sabr_implied_vol` returns the lognormal (Black) implied volatility from
Hagan's 2002 singular-perturbation formula — the market-standard smile
interpolation. References: Hagan, Kumar, Lesniewski & Woodward (2002),
"Managing smile risk", *Wilmott*.
"""

from __future__ import annotations

import numpy as np


def sabr_implied_vol(F, K, T, alpha, beta, rho, nu):
    """Hagan (2002) lognormal/Black implied vol of a SABR option.

    ``alpha`` initial vol, ``beta`` in [0,1] (skew/backbone), ``rho`` correlation,
    ``nu`` vol-of-vol. ATM (F≈K) uses the dedicated limit; otherwise the general
    z/x(z) expansion. ``nu -> 0`` with ``beta=1`` gives a flat smile at ``alpha``.
    """
    if alpha <= 0.0 or nu < 0.0:
        raise ValueError("alpha>0 and nu>=0 required")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must be in (-1, 1)")
    one_b = 1.0 - beta
    # time-correction factor (common to ATM and non-ATM)
    a_fac = (one_b**2 / 24.0) * alpha**2 / (F * K) ** one_b
    b_fac = 0.25 * rho * beta * nu * alpha / (F * K) ** (one_b / 2.0)
    c_fac = (2.0 - 3.0 * rho**2) / 24.0 * nu**2
    time_corr = 1.0 + (a_fac + b_fac + c_fac) * T

    if abs(F - K) < 1e-12 * F:  # ATM limit (z/x(z) -> 1, log(F/K) -> 0)
        return alpha / F**one_b * time_corr

    log_fk = np.log(F / K)
    fk_pow = (F * K) ** (one_b / 2.0)
    z = (nu / alpha) * fk_pow * log_fk
    if abs(z) < 1e-6:  # nu=0 or K~F: x(z)=z+rho z^2/2+O(z^3), so z/x(z) -> 0/0
        z_over_x = 1.0 - 0.5 * rho * z
    else:
        x_z = np.log((np.sqrt(1.0 - 2.0 * rho * z + z * z) + z - rho) / (1.0 - rho))
        z_over_x = z / x_z
    denom = fk_pow * (1.0 + (one_b**2 / 24.0) * log_fk**2 + (one_b**4 / 1920.0) * log_fk**4)
    return (alpha / denom) * z_over_x * time_corr


def _black_call(F, K, T, sigma):
    """Undiscounted Black-76 call F N(d1) - K N(d2) (forward measure)."""
    from scipy.stats import norm

    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return F * norm.cdf(d1) - K * norm.cdf(d2)


def sticky_strike_delta(F, K, T, sigma):
    """Black delta N(d1) with the strike's implied vol held FIXED as F moves.

    The naive BSM view of the smile ("sticky strike"): each strike keeps its
    own vol, so delta ignores how the smile shifts with the underlying.
    """
    from scipy.stats import norm

    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1))


def sabr_smile_delta(F, K, T, alpha, beta, rho, nu, h=None):
    """Smile-consistent SABR delta of an undiscounted call (Hagan 2002, delta risk).

    Central difference of Black(F, sigma_H(F, K)) in F with (alpha, beta, rho,
    nu) held fixed — the smile *moves with F along the CEV backbone*, so the
    delta picks up a vega·(d sigma/d F) correction that sticky-strike misses.
    """
    h = 1e-4 * F if h is None else h
    up = _black_call(F + h, K, T, sabr_implied_vol(F + h, K, T, alpha, beta, rho, nu))
    dn = _black_call(F - h, K, T, sabr_implied_vol(F - h, K, T, alpha, beta, rho, nu))
    return float((up - dn) / (2.0 * h))


def sabr_greeks(F, K, T, alpha, beta, rho, nu, h=None):
    """Smile-consistent SABR Greeks {delta, gamma, vega, theta} of an undiscounted call.

    Every bump holds the model parameters fixed so the smile moves with the
    bumped input along the SABR dynamics:

    - ``delta``/``gamma`` — central first/second difference in F (backbone move);
    - ``vega``  — dV/d(ATM vol): the alpha bump is rescaled by the ATM implied
      vol it produces, so vega is quoted per 1.0 of ATM lognormal vol and is
      directly comparable across beta (whose alpha units differ);
    - ``theta`` — calendar decay -dV/dT, per year.

    In the flat-smile limit (beta=1, nu=0) all four agree with the r=q=0
    Black-Scholes Greeks (pinned by tests).
    """
    h = 1e-3 * F if h is None else h

    def price(f=F, a=alpha, t=T):
        return _black_call(f, K, t, sabr_implied_vol(f, K, t, a, beta, rho, nu))

    base = price()
    up, dn = price(f=F + h), price(f=F - h)
    delta = (up - dn) / (2.0 * h)
    gamma = (up - 2.0 * base + dn) / h**2
    da = 1e-4 * alpha
    atm_up = sabr_implied_vol(F, F, T, alpha + da, beta, rho, nu)
    atm_dn = sabr_implied_vol(F, F, T, alpha - da, beta, rho, nu)
    vega = (price(a=alpha + da) - price(a=alpha - da)) / (atm_up - atm_dn)
    dt_ = min(1e-4, 0.5 * T)
    theta = -(price(t=T + dt_) - price(t=T - dt_)) / (2.0 * dt_)
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "vega": float(vega),
        "theta": float(theta),
    }


def calibrate_sabr(F, T, strikes, market_ivs, beta, x0=None):
    """Least-squares (alpha, rho, nu) fit to market implied vols for a fixed beta.

    The market-side workflow behind the broker screen: beta is chosen a priori
    (0, 0.5 or 1), the other three parameters are fitted to the quoted smile.
    Returns (alpha, rho, nu).
    """
    from scipy.optimize import least_squares

    strikes = np.asarray(strikes, dtype=float)
    market_ivs = np.asarray(market_ivs, dtype=float)
    if strikes.shape != market_ivs.shape or strikes.size < 3:
        raise ValueError("need >= 3 strikes with matching market_ivs")
    if x0 is None:
        atm_iv = float(market_ivs[np.argmin(np.abs(strikes - F))])
        x0 = (atm_iv * F ** (1.0 - beta), 0.0, 0.5)

    def resid(p):
        a, r_, n_ = p
        return [
            sabr_implied_vol(F, float(k), T, a, beta, r_, n_) - iv
            for k, iv in zip(strikes, market_ivs, strict=True)
        ]

    res = least_squares(
        resid, x0, bounds=([1e-6, -0.999, 1e-9], [np.inf, 0.999, 10.0]), xtol=1e-14, ftol=1e-14
    )
    return tuple(float(v) for v in res.x)
