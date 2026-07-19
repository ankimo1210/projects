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


def _validated_curve(curve):
    """Return finite, strictly ordered curve arrays for new curve helpers."""
    try:
        times, zeros = curve
    except (TypeError, ValueError) as exc:
        raise ValueError("curve must be a (times, zero_rates) pair") from exc
    times = np.asarray(times, dtype=float)
    zeros = np.asarray(zeros, dtype=float)
    if times.ndim != 1 or zeros.ndim != 1 or times.size != zeros.size or not times.size:
        raise ValueError("curve times and zero rates must be non-empty one-dimensional arrays")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(zeros)):
        raise ValueError("curve times and zero rates must be finite")
    if np.any(times < 0.0) or np.any(np.diff(times) <= 0.0):
        raise ValueError("curve times must be non-negative and strictly increasing")
    return times, zeros


def discount_factor(t, curve):
    """Continuous-compounding discount factor ``P(0,t)`` from a zero curve."""
    t = float(t)
    if not math.isfinite(t) or t < 0.0:
        raise ValueError("discount time must be finite and non-negative")
    if t == 0.0:
        return 1.0
    times, zeros = _validated_curve(curve)
    return math.exp(-zero_interp(t, times, zeros) * t)


def forward_discount(start, end, curve):
    """Forward discount factor ``P(0,end) / P(0,start)`` for ``end >= start``."""
    start = float(start)
    end = float(end)
    if not math.isfinite(start) or not math.isfinite(end) or start < 0.0 or end < start:
        raise ValueError("forward-discount times must satisfy 0 <= start <= end")
    return discount_factor(end, curve) / discount_factor(start, curve)


def instantaneous_forward(t, curve, *, bump=1e-5):
    r"""Numerical instantaneous forward ``f(0,t)=-d log P(0,t)/dt``.

    A central difference is used away from zero and a forward difference at the
    origin.  The helper deliberately follows the interpolation convention of the
    supplied zero curve instead of fitting an additional smoothing model.
    """
    t = float(t)
    bump = float(bump)
    if not math.isfinite(t) or t < 0.0:
        raise ValueError("forward time must be finite and non-negative")
    if not math.isfinite(bump) or bump <= 0.0:
        raise ValueError("bump must be finite and positive")

    def log_discount(time):
        return math.log(discount_factor(time, curve))

    if t < bump:
        return -(log_discount(t + bump) - log_discount(t)) / bump
    return -(log_discount(t + bump) - log_discount(t - bump)) / (2.0 * bump)


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
