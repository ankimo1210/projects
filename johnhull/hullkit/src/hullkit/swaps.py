"""Interest-rate and currency swap valuation (Hull 11e, Ch.7).

A curve is a (times, zero_rates) tuple with continuous compounding,
interpolated via rates.zero_interp; P(0, t) = exp(-z(t) * t).
"""

import math

import numpy as np

from . import rates


def discount(t, curve):
    """Discount factor P(0, t) from a (times, zeros) curve tuple."""
    times, zeros = curve
    return math.exp(-rates.zero_interp(t, times, zeros) * t)


def swap_rate(pay_times, curve):
    """Par swap rate s = (1 - P(0,t_n)) / sum(tau_i * P(0,t_i)) (Hull Ch.7)."""
    pay_times = np.asarray(pay_times, dtype=float)
    taus = np.diff(np.concatenate([[0.0], pay_times]))
    annuity = float(
        sum(tau * discount(float(t), curve) for tau, t in zip(taus, pay_times, strict=True))
    )
    return (1.0 - discount(float(pay_times[-1]), curve)) / annuity


def irs_value_bonds(notional, s_fixed, pay_times, curve, next_float_rate, accrual_to_next=None):
    """Receive-fixed IRS value via the bond decomposition V = B_fix - B_fl.

    next_float_rate is the simple rate already set for the next floating
    payment; the floating bond is worth par immediately after that payment
    (Hull Ch.7), so B_fl = (L + L * r * tau1) * P(0, t1).
    """
    pay_times = np.asarray(pay_times, dtype=float)
    taus = np.diff(np.concatenate([[0.0], pay_times]))
    b_fix = sum(
        notional * s_fixed * tau * discount(float(t), curve)
        for tau, t in zip(taus, pay_times, strict=True)
    )
    b_fix += notional * discount(float(pay_times[-1]), curve)
    tau1 = float(taus[0]) if accrual_to_next is None else accrual_to_next
    b_fl = (notional + notional * next_float_rate * tau1) * discount(float(pay_times[0]), curve)
    return b_fix - b_fl


def irs_value_fras(notional, s_fixed, pay_times, curve, next_float_rate=None):
    """Receive-fixed IRS value via the FRA decomposition (Hull's preferred).

    Each floating payment is assumed to realize the curve's forward rate
    (simple, over its accrual period); the preset first rate can be given.
    """
    pay_times = np.asarray(pay_times, dtype=float)
    times_aug = np.concatenate([[0.0], pay_times])
    value = 0.0
    for i in range(len(pay_times)):
        t0, t1 = float(times_aug[i]), float(times_aug[i + 1])
        tau = t1 - t0
        if i == 0 and next_float_rate is not None:
            f_simple = next_float_rate
        else:
            z0 = rates.zero_interp(t0, *curve) if t0 > 0.0 else 0.0
            z1 = rates.zero_interp(t1, *curve)
            f_cont = (z1 * t1 - z0 * t0) / tau
            f_simple = (math.exp(f_cont * tau) - 1.0) / tau
        value += notional * (s_fixed - f_simple) * tau * discount(t1, curve)
    return value


def currency_swap_value(
    domestic_times,
    domestic_cfs,
    domestic_curve,
    foreign_times,
    foreign_cfs,
    foreign_curve,
    spot,
):
    """Receive-domestic / pay-foreign swap value in domestic units: B_D - S0 * B_F."""
    b_d = sum(
        cf * discount(float(t), domestic_curve)
        for t, cf in zip(domestic_times, domestic_cfs, strict=True)
    )
    b_f = sum(
        cf * discount(float(t), foreign_curve)
        for t, cf in zip(foreign_times, foreign_cfs, strict=True)
    )
    return b_d - spot * b_f
