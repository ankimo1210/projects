"""Cash-flow schedules, market-quote repricing, and fixed-receiver PVs."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from .curve import ZeroCurve


def payment_times(maturity_years: float, frequency: int) -> np.ndarray:
    """Regular coupon times from valuation, excluding a terminal stub.

    The input has no issue/effective dates. The documented benchmark maturity
    year fraction is authoritative, so regular coupons occur at integer coupon
    intervals from valuation and principal is separately repaid at maturity.
    """
    if maturity_years <= 0 or frequency <= 0:
        raise ValueError("positive maturity and frequency required")
    step = 1.0 / frequency
    count = int(np.floor(maturity_years * frequency + 1e-10))
    return step * np.arange(1, count + 1, dtype=float)


def swap_payment_times(maturity_years: float) -> tuple[np.ndarray, np.ndarray]:
    """Annual fixed payments through 2Y and semiannual thereafter."""
    frequency = 1 if maturity_years <= 2.0 + 1e-12 else 2
    times = payment_times(maturity_years, frequency)
    if len(times) == 0 or maturity_years - times[-1] > 1e-10:
        times = np.r_[times, maturity_years]
    previous = np.r_[0.0, times[:-1]]
    accruals = times - previous
    return times, accruals


def bond_cashflows(maturity_years: float, frequency: int, coupon_rate: float) -> tuple[np.ndarray, np.ndarray]:
    """Level coupons on regular dates and principal at authoritative maturity."""
    coupon_times = payment_times(maturity_years, frequency)
    coupon_amount = 100.0 * coupon_rate / frequency
    if len(coupon_times) and abs(coupon_times[-1] - maturity_years) <= 1e-10:
        cashflows = np.full(len(coupon_times), coupon_amount)
        cashflows[-1] += 100.0
        return coupon_times, cashflows
    times = np.r_[coupon_times, maturity_years]
    cashflows = np.r_[np.full(len(coupon_times), coupon_amount), 100.0]
    return times, cashflows


def model_quote_from_discount(
    row: pd.Series,
    discount: Callable[[float | np.ndarray], float | np.ndarray],
) -> float:
    """Price directly from ``D(T)`` without curve interpolation.

    This interface is intentionally small so pricing conventions and units can
    be tested independently from curve fitting.  Rate results are decimals and
    bond results are points per 100 face value.
    """
    maturity = float(row["maturity_years"])
    instrument_type = str(row["instrument_type"])
    if instrument_type == "deposit":
        discount_at_maturity = float(discount(maturity))
        return (1.0 / discount_at_maturity - 1.0) / maturity
    if instrument_type == "ois_swap":
        times, accruals = swap_payment_times(maturity)
        discounts = np.asarray(discount(times), dtype=float)
        annuity = float(np.dot(accruals, discounts))
        if annuity <= 0:
            raise FloatingPointError("non-positive swap annuity")
        return (1.0 - float(discount(maturity))) / annuity
    if instrument_type == "bond":
        frequency = int(row["payment_frequency"])
        coupon = float(row["coupon_rate"])
        times, cashflows = bond_cashflows(maturity, frequency, coupon)
        return float(np.dot(cashflows, np.asarray(discount(times), dtype=float)))
    raise ValueError(f"unsupported instrument type: {instrument_type}")


def model_quote(row: pd.Series, curve: ZeroCurve) -> float:
    """Model quote in normalized units (rate decimal or price points)."""
    return model_quote_from_discount(row, curve.discount)


def fixed_receiver_pv(
    row: pd.Series,
    curve: ZeroCurve,
    zero_bump: Callable[[np.ndarray], np.ndarray] | None = None,
) -> float:
    """PV of contractual fixed cash flows under a bumped zero curve.

    Deposits and swaps use USD 1mm notional; bonds use face 100. For swaps,
    PV is fixed leg less floating leg. For deposits, the initial principal is
    included but is insensitive to the curve.
    """
    maturity = float(row["maturity_years"])
    quote = float(row["normalized_quote"])
    instrument_type = str(row["instrument_type"])
    if instrument_type == "deposit":
        notional = 1_000_000.0
        redemption = notional * (1.0 + quote * maturity)
        return redemption * float(curve.discount(maturity, zero_bump)) - notional
    if instrument_type == "ois_swap":
        notional = 1_000_000.0
        times, accruals = swap_payment_times(maturity)
        discounts = np.asarray(curve.discount(times, zero_bump))
        fixed_leg = quote * float(np.dot(accruals, discounts))
        floating_leg = 1.0 - float(curve.discount(maturity, zero_bump))
        return notional * (fixed_leg - floating_leg)
    if instrument_type == "bond":
        frequency = int(row["payment_frequency"])
        coupon = float(row["coupon_rate"])
        times, cashflows = bond_cashflows(maturity, frequency, coupon)
        return float(np.dot(cashflows, np.asarray(curve.discount(times, zero_bump))))
    raise ValueError(f"unsupported instrument type: {instrument_type}")
