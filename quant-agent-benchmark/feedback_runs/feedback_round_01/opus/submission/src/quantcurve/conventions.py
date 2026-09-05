"""Small, unambiguous convention helpers.

Everything in this module is a pure function of documented market conventions
(``market_data/CONVENTIONS.md``).  The three helpers at the top are part of the
supplied starter interface and are relied upon by the visible tests; the rest
implement the schedule and quote conventions required by the benchmark.

Documented conventions implemented here
---------------------------------------
* Zero rates are continuously compounded annual decimals, ``D(T) = exp(-z T)``.
* Deposits use simple interest, ``D(T) = 1 / (1 + r T)``.
* OIS fixed legs pay annually through 2Y and semiannually thereafter; the
  accrual factor of every period is ``1 / payment_frequency``.
* Bonds pay level coupons at ``1 / payment_frequency`` year intervals, have face
  value 100, no accrued interest and repay principal at maturity.

Schedule construction
---------------------
Both swap and bond schedules are generated *backwards from maturity* in steps of
``1 / payment_frequency`` using ``n = round(T * frequency)`` periods (round half
away from zero, floored at one period).  This is the only rule consistent with
the supplied quotes: it reproduces the 1.25Y annual-pay OIS quote (one period)
and the 2.44Y semiannual bond quote (five periods) simultaneously, whereas
``ceil`` fails the former and ``floor`` fails the latter.  See
``MODEL_RISKS.md`` for the empirical evidence.
"""

from __future__ import annotations

import math

import numpy as np

__all__ = [
    "discount_from_zero",
    "zero_from_discount",
    "simple_deposit_rate",
    "period_count",
    "schedule_backward",
    "swap_schedule",
    "bond_schedule",
    "annual_frequency_for_swap",
    "PERCENT_TO_DECIMAL",
    "DECIMAL_TO_PERCENT",
    "BASIS_POINT",
]

#: One basis point expressed as a decimal rate.
BASIS_POINT = 1.0e-4
#: Multiplier converting a quote in percentage points to a decimal rate.
PERCENT_TO_DECIMAL = 0.01
#: Multiplier converting a decimal rate to percentage points.
DECIMAL_TO_PERCENT = 100.0


def discount_from_zero(zero_rate: float, maturity_years: float) -> float:
    """Continuously compounded discount factor exp(-z*T)."""
    if maturity_years < 0:
        raise ValueError("maturity_years must be non-negative")
    return math.exp(-zero_rate * maturity_years)


def zero_from_discount(discount_factor: float, maturity_years: float) -> float:
    """Continuously compounded zero rate -log(D)/T."""
    if discount_factor <= 0:
        raise ValueError("discount_factor must be positive")
    if maturity_years <= 0:
        raise ValueError("maturity_years must be positive")
    return -math.log(discount_factor) / maturity_years


def simple_deposit_rate(discount_factor: float, maturity_years: float) -> float:
    """Simple annual deposit rate implied by a discount factor."""
    if discount_factor <= 0 or maturity_years <= 0:
        raise ValueError("positive discount_factor and maturity_years required")
    return (1.0 / discount_factor - 1.0) / maturity_years


def period_count(maturity_years: float, frequency: int) -> int:
    """Number of accrual periods, ``round(T * frequency)`` with a floor of one.

    Rounding is *half away from zero* rather than Python's banker's rounding so
    that a hypothetical 2.5Y annual-pay schedule produces three periods rather
    than two.  The benchmark data contain no half-integer ``T * frequency``
    cases, so the two rules agree on the supplied dataset.
    """
    if not np.isfinite(maturity_years) or maturity_years <= 0:
        raise ValueError("maturity_years must be a positive finite number")
    if frequency <= 0:
        raise ValueError("frequency must be a positive integer")
    return max(1, int(math.floor(maturity_years * frequency + 0.5)))


def schedule_backward(maturity_years: float, frequency: int) -> np.ndarray:
    """Payment times generated backwards from maturity in ``1/frequency`` steps.

    Returns an ascending array of strictly positive payment times whose last
    element is exactly ``maturity_years``.
    """
    n = period_count(maturity_years, frequency)
    times = maturity_years - np.arange(n - 1, -1, -1, dtype=float) / float(frequency)
    # A very short stub can round to a non-positive first time; drop it and keep
    # the schedule well-formed.  ``maturity_years`` itself is always retained.
    times = times[times > 0.0]
    if times.size == 0:
        times = np.array([float(maturity_years)])
    return times


def annual_frequency_for_swap(maturity_years: float) -> int:
    """Documented OIS fixed-leg frequency: annual through 2Y, semiannual after."""
    return 1 if maturity_years <= 2.0 else 2


def swap_schedule(maturity_years: float, frequency: int) -> tuple[np.ndarray, float]:
    """Fixed-leg payment times and the (constant) accrual factor ``1/frequency``."""
    return schedule_backward(maturity_years, frequency), 1.0 / float(frequency)


def bond_schedule(maturity_years: float, frequency: int) -> np.ndarray:
    """Coupon payment times for a bullet bond maturing at ``maturity_years``."""
    return schedule_backward(maturity_years, frequency)
