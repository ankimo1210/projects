"""Black's-model interest-rate derivatives (Hull 11e, Ch.29/30)."""

import math

import numpy as np
from scipy.stats import norm


def _black(forward, strike, sigma, T, df, kind_call):
    """Black-76 forward-price option value: df * [F N(d1) - K N(d2)] (call).

    Black's model is lognormal in the forward, so both the forward and the
    strike must be strictly positive. Post-LIBOR curves do quote negative
    forward rates; price those with a normal (Bachelier) model instead --
    `hullkit.rfr_options` has one.
    """
    if not (forward > 0.0 and strike > 0.0):
        raise ValueError(
            "Black's model needs a positive forward and strike (it is lognormal), "
            f"got forward={forward}, strike={strike}; use a normal/Bachelier model "
            "for negative rates"
        )
    if sigma <= 0.0 or T <= 0.0:
        raise ValueError(f"Black's model needs sigma > 0 and T > 0, got sigma={sigma}, T={T}")
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


def bond_yield_convexity(y_F, coupon, n_years, freq=1, face=1.0):
    """G'(y_F) and G''(y_F) of a standard coupon bond's price-yield function (Hull §30.1).

    G(y) = sum_k (face*coupon/freq) (1 + y/freq)^-k + face (1 + y/freq)^-(freq*n_years),
    k = 1..freq*n_years, so y and coupon are annual rates compounded ``freq``
    times a year (Hull Example 30.1 uses annual compounding, freq=1). Returns
    ``(g1, g2)`` with g1 < 0 < g2 for a positive-yield bond; feed
    ``g2_over_g1 = -g2 / g1`` to :func:`convexity_adjustment` for eq. 30.1.
    Hull Example 30.1 (3-year 6% bond, y_F = 6%): G' = -2.6730, G'' = 9.8910.
    """
    if freq <= 0:
        raise ValueError(f"freq must be positive, got {freq}")
    n_periods = n_years * freq
    if n_periods < 1 or abs(n_periods - round(n_periods)) > 1e-9:
        raise ValueError(
            f"n_years * freq must be a positive whole number of periods, got {n_periods}"
        )
    base = 1.0 + y_F / freq
    if base <= 0.0:
        raise ValueError(f"1 + y_F/freq must be positive, got {base}")
    k = np.arange(1, round(float(n_periods)) + 1, dtype=float)
    cashflows = np.full(k.size, face * coupon / freq)
    cashflows[-1] += face
    g1 = -np.sum(k * cashflows * base ** (-k - 1.0)) / freq
    g2 = np.sum(k * (k + 1.0) * cashflows * base ** (-k - 2.0)) / freq**2
    return float(g1), float(g2)
