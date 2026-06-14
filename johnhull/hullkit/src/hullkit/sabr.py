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
    x_z = np.log((np.sqrt(1.0 - 2.0 * rho * z + z * z) + z - rho) / (1.0 - rho))
    denom = fk_pow * (1.0 + (one_b**2 / 24.0) * log_fk**2 + (one_b**4 / 1920.0) * log_fk**4)
    return (alpha / denom) * (z / x_z) * time_corr
