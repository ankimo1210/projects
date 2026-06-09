"""Interest-rate and bond utilities (Hull 11e, Ch.4).

Continuous compounding throughout — Hull's book standard. Used by the
volume-04 notebook and by later volumes (07 swaps, 11 IR derivatives).
"""

import math

import numpy as np
from scipy.optimize import brentq


def to_continuous(rate, m):
    """Annual rate compounded m times/year -> continuous (Hull eq. 4.3)."""
    return m * math.log(1.0 + rate / m)


def from_continuous(rate, m):
    """Continuous rate -> annual rate compounded m times/year (Hull eq. 4.4)."""
    return m * (math.exp(rate / m) - 1.0)


def bond_price(times, cashflows, zero_rates):
    """PV of cashflows under continuous zero rates (scalar or per-time array)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    zero_rates = np.broadcast_to(np.asarray(zero_rates, dtype=float), times.shape)
    return float(np.sum(cashflows * np.exp(-zero_rates * times)))


def bond_yield(times, cashflows, price):
    """Continuous-compounding YTM (Hull eq. 4.7) via brentq."""
    return brentq(lambda y: bond_price(times, cashflows, y) - price, -0.5, 5.0)


def macaulay_duration(times, cashflows, y):
    """Macaulay duration with continuous yield (Hull eq. 4.8)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    pv = cashflows * np.exp(-y * times)
    return float(np.dot(times, pv) / pv.sum())


def convexity(times, cashflows, y):
    """Convexity with continuous yield (Hull eq. 4.14)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    pv = cashflows * np.exp(-y * times)
    return float(np.dot(times**2, pv) / pv.sum())


def forward_rate(r1, t1, r2, t2):
    """Forward rate for (t1, t2) from continuous zeros (Hull eq. 4.5)."""
    return (r2 * t2 - r1 * t1) / (t2 - t1)


def fra_value(notional, rate_fixed, rate_forward, t1, t2, r2):
    """FRA value to the fixed-rate receiver (continuous rates, Hull §4.9)."""
    return notional * (rate_fixed - rate_forward) * (t2 - t1) * math.exp(-r2 * t2)


def zero_interp(t, times, rates):
    """Linear interpolation on a zero curve with flat extrapolation."""
    return float(np.interp(t, times, rates))


def bootstrap_zero_curve(instruments):
    """Bootstrap continuous zero rates from bond prices (Hull §4.7, Table 4.3).

    instruments: iterable of (maturity_years, annual_coupon, price) on face
    100 with SEMIANNUAL coupons (annual_coupon=0 -> zero-coupon), processed
    in increasing maturity. Coupon dates of later bonds must be covered by
    earlier maturities (interpolated). Returns (times, zero_rates) lists.
    """
    times, zeros = [], []
    for maturity, annual_coupon, price in sorted(instruments):
        coupon = annual_coupon / 2.0
        cf_times = np.arange(maturity, 0.0, -0.5)[::-1]  # ..., maturity
        if coupon != 0.0 and cf_times[:-1].size and times and cf_times[-2] > times[-1] + 1e-9:
            raise ValueError(
                f"bootstrap_zero_curve: coupon date {cf_times[-2]:.4f} of the "
                f"{maturity}y bond is not covered by an earlier maturity"
            )
        pv_known = sum(coupon * math.exp(-zero_interp(t, times, zeros) * t) for t in cf_times[:-1])
        final_cf = 100.0 + coupon
        rate = -math.log((price - pv_known) / final_cf) / maturity
        times.append(float(maturity))
        zeros.append(rate)
    return times, zeros
