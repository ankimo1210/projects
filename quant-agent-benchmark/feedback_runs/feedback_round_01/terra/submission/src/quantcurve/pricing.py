"""Instrument pricing from a directly supplied discount function.

These functions deliberately do not depend on curve interpolation or fitting.
They provide a small, inspectable convention boundary for pricing diagnostics.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class DiscountFunction(Protocol):
    """Any object that can return discount factors at scalar or vector maturities."""

    def discount(self, maturity: float | np.ndarray) -> np.ndarray: ...


def deposit_simple_rate(discounts: DiscountFunction, maturity: float) -> float:
    """Simple annual deposit quote from a supplied discount function."""
    return float((1.0 / discounts.discount(maturity) - 1.0) / maturity)


def ois_payment_schedule(maturity: float, frequency: int) -> tuple[np.ndarray, np.ndarray]:
    """Spot-starting OIS dates and ACT/365F accruals, with a terminal stub."""
    interval = 1.0 / frequency
    dates: list[float] = []
    next_date = interval
    while next_date < maturity - 1e-10:
        dates.append(next_date)
        next_date += interval
    dates.append(maturity)
    times = np.asarray(dates, dtype=float)
    return times, np.diff(np.concatenate(([0.0], times)))


def bond_payment_schedule(maturity: float, frequency: int) -> tuple[np.ndarray, np.ndarray]:
    """Coupon dates rolled backward from maturity and annualized accruals.

    The public conventions specify coupon spacing but not an explicit irregular
    stub convention.  This interpretation keeps regular periods adjacent to
    maturity and a possible short first period.  It is documented as a
    provisional convention rather than inferred from market fit.
    """
    interval = 1.0 / frequency
    count = int(np.ceil(maturity / interval - 1e-12))
    times = maturity - interval * np.arange(count - 1, -1, -1, dtype=float)
    times = np.round(times, 12)
    return times, np.diff(np.concatenate(([0.0], times)))


def ois_par_rate(discounts: DiscountFunction, maturity: float, frequency: int) -> float:
    """Par OIS fixed rate under the published start-at-valuation-date rule."""
    times, accruals = ois_payment_schedule(maturity, frequency)
    annuity = float(np.dot(accruals, discounts.discount(times)))
    return float((1.0 - discounts.discount(maturity)) / annuity)


def bond_clean_price(discounts: DiscountFunction, maturity: float, coupon_rate: float, frequency: int) -> float:
    """Clean price per 100 face for a level-coupon bond with final principal."""
    times, accruals = bond_payment_schedule(maturity, frequency)
    cashflows = 100.0 * coupon_rate * accruals
    cashflows[-1] += 100.0
    return float(np.dot(cashflows, discounts.discount(times)))
