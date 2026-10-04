"""Private Hull §29.1 cash-price bond options and yield-volatility conventions."""

import numpy as np
from scipy.optimize import brentq

from ._forward_black import forward_black_price


def _value(x):
    if not np.all(np.isfinite(x)):
        raise ValueError("finite bond result required")
    return float(x) if np.ndim(x) == 0 else x


def bond_clean_price(cash_price, accrued_interest):
    return _value(np.asarray(cash_price, dtype=float) - np.asarray(accrued_interest, dtype=float))


def cash_bond_strike(quoted_strike, expiry_accrued_interest):
    return _value(
        np.asarray(quoted_strike, dtype=float) + np.asarray(expiry_accrued_interest, dtype=float)
    )


def cash_bond_forward(cash_price, coupon_present_values, option_discount):
    """(dirty spot - PV of coupons before exercise)/P(0,T), Hull 29.3.

    The caller declares coupon ownership at an exercise/payment coincidence;
    accrued interest is not subtracted from the dirty spot in this formula.
    """
    p = float(option_discount)
    cash = float(cash_price)
    coupon = np.asarray(coupon_present_values, dtype=float)
    if p <= 0 or not np.all(np.isfinite(coupon)):
        raise ValueError("positive discount and finite coupon present values required")
    forward = (cash - float(np.sum(coupon))) / p
    if forward <= 0:
        raise ValueError("positive cash forward required by lognormal model")
    return _value(forward)


def forward_yield_duration(forward_cash_price, remaining_times, remaining_cashflows, frequency=2):
    """Yield and modified duration of remaining cashflows, in declared compounding.

    In Example 29.2 times are measured from exercise, including a quarter-year
    first coupon. The semiannual forward cash yield is solved before using
    modified (not Macaulay) duration in the relative volatility conversion.
    """
    t, c = np.asarray(remaining_times, dtype=float), np.asarray(remaining_cashflows, dtype=float)
    price, m = float(forward_cash_price), float(frequency)
    if (
        t.ndim != 1
        or c.shape != t.shape
        or len(t) == 0
        or np.any(t <= 0)
        or np.any(c < 0)
        or not np.any(c > 0)
        or price <= 0
        or m <= 0
        or not np.all(np.isfinite(t))
        or not np.all(np.isfinite(c))
    ):
        raise ValueError("positive price/frequency/times and nonnegative cashflows required")

    def pv(y):
        with np.errstate(over="ignore"):
            return float(np.sum(c * np.power(1 + y / m, -m * t)))

    upper = 0.1
    for _ in range(64):
        if pv(upper) < price:
            break
        upper = 2 * upper + 0.1
    else:
        raise ValueError("yield root could not be bracketed")
    y = brentq(lambda yy: pv(yy) - price, -m + 1e-12, upper, xtol=1e-14)
    discounted = c * np.power(1 + y / m, -m * t)
    macaulay = float(np.dot(t, discounted) / price)
    return dict(
        forward_yield=y, macaulay_duration=macaulay, modified_duration=macaulay / (1 + y / m)
    )


def bond_price_volatility(modified_duration, forward_yield, yield_volatility):
    """D_mod*y*relative_yield_vol, Hull 29.4 (positive lognormal yield)."""
    d, y, s = [
        np.asarray(x, dtype=float) for x in (modified_duration, forward_yield, yield_volatility)
    ]
    if np.any(d < 0) or np.any(y < 0) or np.any(s < 0):
        raise ValueError("nonnegative duration/yield/relative volatility required")
    return _value(d * y * s)


def cash_bond_option(discount, cash_forward, cash_strike, bond_volatility, expiry, kind="call"):
    return forward_black_price(discount, cash_forward, cash_strike, bond_volatility, expiry, kind)


def gaussian_bond_volatility(option_expiry, bond_maturity, mean_reversion, rate_volatility):
    """Schematic Figs29.1/29.2 in a declared constant Gaussian short-rate model.

    log-bond sd=B(t,M)*sigma*sqrt((1-exp(-2*a*t))/(2*a)); the forward
    effective volatility is sd/sqrt(t), including its continuous t=0 limit.
    This reproduces the shape, not unprinted prices or a unique book model.
    """
    t, M, a, sigma = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (option_expiry, bond_maturity, mean_reversion, rate_volatility)
        ]
    )
    if np.any(t < 0) or np.any(M < t) or np.any(a < 0) or np.any(sigma < 0):
        raise ValueError("0<=expiry<=maturity and nonnegative mean reversion/volatility required")
    safe = np.where(a == 0, 1.0, a)
    B = np.where(a == 0, M - t, -np.expm1(-a * (M - t)) / safe)
    var = np.where(a == 0, t, -np.expm1(-2 * a * t) / (2 * safe)) * sigma * sigma
    sd = B * np.sqrt(var)
    effective = np.divide(sd, np.sqrt(t), out=np.array(sigma * B), where=t > 0)
    return dict(log_price_sd=_value(sd), forward_price_volatility=_value(effective))
