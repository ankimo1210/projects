"""Black's-model interest-rate derivatives (Hull 11e, Ch.29/30)."""

import math

import numpy as np
from scipy.stats import norm


def _black(forward, strike, sigma, T, df, kind_call):
    """Black-76 forward-price option value: df * [F N(d1) - K N(d2)] (call)."""
    d1 = (math.log(forward / strike) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind_call:
        return df * (forward * norm.cdf(d1) - strike * norm.cdf(d2))
    return df * (strike * norm.cdf(-d2) - forward * norm.cdf(-d1))


def bond_option_black(P0T, F_B, K, sigma_B, T, kind="call"):
    """European bond option, Black's model (Hull eq. 29.1/29.2).

    P0T = P(0, T); F_B = forward bond price; sigma_B = forward-price vol.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    return _black(F_B, K, sigma_B, T, P0T, kind == "call")


def caplet_black(L, delta, F, R_K, sigma, t_k, P_pay, kind="caplet"):
    """Single caplet/floorlet, Black's model (Hull eq. 29.7/29.8).

    L notional, delta accrual, F forward rate, R_K cap rate, sigma the rate's
    volatility, t_k the fixing time, P_pay = P(0, t_{k+1}).
    """
    if kind not in ("caplet", "floorlet"):
        raise ValueError(f"kind must be 'caplet' or 'floorlet', got {kind!r}")
    return L * delta * _black(F, R_K, sigma, t_k, P_pay, kind == "caplet")


def cap_black(L, forwards, R_K, sigma, accruals, pay_discounts, fixing_times, kind="cap"):
    """Cap or floor = sum of caplets/floorlets (Hull eq. 29.7). sigma is the
    flat volatility applied to every caplet (or pass spot vols via a loop)."""
    if kind not in ("cap", "floor"):
        raise ValueError(f"kind must be 'cap' or 'floor', got {kind!r}")
    leg = "caplet" if kind == "cap" else "floorlet"
    sig = [sigma] * len(forwards) if np.ndim(sigma) == 0 else sigma
    return sum(
        caplet_black(L, d, f, R_K, s, t, p, kind=leg)
        for f, d, p, t, s in zip(forwards, accruals, pay_discounts, fixing_times, sig, strict=True)
    )


def swaption_black(L, annuity, s_F, s_K, sigma, T, kind="payer"):
    """European swaption, Black's model (Hull eq. 29.10/29.11).

    annuity A(0) = sum of pay-date discount factors / m; s_F forward swap rate.
    """
    if kind not in ("payer", "receiver"):
        raise ValueError(f"kind must be 'payer' or 'receiver', got {kind!r}")
    return L * annuity * _black(s_F, s_K, sigma, T, 1.0, kind == "payer")


def convexity_adjustment(y_F, sigma_y, T, g2_over_g1):
    """Convexity adjustment to a forward bond yield (Hull eq. 30.1).

    Returns the amount to ADD to y_F to get the expected yield:
    -0.5 y_F^2 sigma_y^2 T (G''/G'). For a bond G'<0, G''>0 so G''/G' < 0 and
    the adjustment is positive; pass g2_over_g1 = |G''/G'| (a positive number).
    """
    return 0.5 * y_F**2 * sigma_y**2 * T * g2_over_g1
