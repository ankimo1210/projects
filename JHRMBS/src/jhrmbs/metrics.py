from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
ArrayLike = float | Sequence[float] | FloatArray


def _array(value: ArrayLike) -> FloatArray:
    return np.asarray(value, dtype=np.float64)


def _scalar_or_array(original: ArrayLike, result: FloatArray) -> float | FloatArray:
    return float(result) if np.ndim(original) == 0 else result


def _validate_rate(name: str, values: FloatArray) -> None:
    finite = values[np.isfinite(values)]
    if ((finite < 0.0) | (finite > 1.0)).any():
        raise ValueError(f"{name} must be in decimal units between 0 and 1")


def cpr_to_smm(cpr: ArrayLike) -> float | FloatArray:
    """Convert annual CPR in decimal units to monthly SMM in decimal units."""
    values = _array(cpr)
    _validate_rate("CPR", values)
    result = 1.0 - np.power(1.0 - values, 1.0 / 12.0)
    return _scalar_or_array(cpr, result)


def smm_to_cpr(smm: ArrayLike) -> float | FloatArray:
    """Convert monthly SMM in decimal units to annual CPR in decimal units."""
    values = _array(smm)
    _validate_rate("SMM", values)
    result = 1.0 - np.power(1.0 - values, 12.0)
    return _scalar_or_array(smm, result)


def psj_cpr(
    wala_months: ArrayLike,
    terminal_cpr: float,
    *,
    seasoning_months: int = 60,
) -> float | FloatArray:
    """Return standard JSDA PSJ CPR for WALA and terminal CPR, both in decimal units.

    Standard PSJ starts at 0 CPR at WALA 0, increases linearly, reaches the
    terminal CPR at month 60 by default, and remains flat thereafter.
    """
    if seasoning_months <= 0:
        raise ValueError("seasoning_months must be positive")
    if not 0.0 <= terminal_cpr <= 1.0:
        raise ValueError("terminal_cpr must be in decimal units between 0 and 1")
    wala = _array(wala_months)
    finite = wala[np.isfinite(wala)]
    if (finite < 0.0).any():
        raise ValueError("WALA cannot be negative")
    ramp = np.clip(wala / float(seasoning_months), 0.0, 1.0)
    result = terminal_cpr * ramp
    return _scalar_or_array(wala_months, result)


def cpr_to_psj_terminal(
    cpr: ArrayLike,
    wala_months: ArrayLike,
    *,
    seasoning_months: int = 60,
) -> FloatArray:
    """Convert point-in-time CPR into its instantaneous standard-PSJ terminal CPR."""
    cpr_values = _array(cpr)
    wala_values = _array(wala_months)
    _validate_rate("CPR", cpr_values)
    ramp = np.clip(wala_values / float(seasoning_months), 0.0, 1.0)
    return np.divide(
        cpr_values,
        ramp,
        out=np.full(np.broadcast(cpr_values, ramp).shape, np.nan, dtype=np.float64),
        where=ramp > 0.0,
    )


def factor_implied_total_smm(
    previous_actual_factor: ArrayLike,
    actual_factor: ArrayLike,
    previous_scheduled_factor: ArrayLike,
    scheduled_factor: ArrayLike,
) -> FloatArray:
    """Infer total unscheduled monthly decrement after scheduled amortization.

    This is not the published voluntary-prepayment SMM. It can also reflect
    substitutions, cancellations, delinquency removals, rescheduling and rounding.
    """
    previous_actual = _array(previous_actual_factor)
    actual = _array(actual_factor)
    previous_scheduled = _array(previous_scheduled_factor)
    scheduled = _array(scheduled_factor)
    expected_after_schedule = np.divide(
        previous_actual * scheduled,
        previous_scheduled,
        out=np.full(np.broadcast(previous_actual, scheduled).shape, np.nan),
        where=previous_scheduled > 0.0,
    )
    implied = np.divide(
        expected_after_schedule - actual,
        expected_after_schedule,
        out=np.full(expected_after_schedule.shape, np.nan),
        where=expected_after_schedule > 0.0,
    )
    return np.asarray(np.clip(implied, -1.0, 1.0), dtype=np.float64)


def combine_competing_monthly_rates(*rates: ArrayLike) -> FloatArray:
    """Combine monthly decimal decrement rates as conditionally independent risks."""
    if not rates:
        raise ValueError("at least one rate is required")
    arrays = [_array(rate) for rate in rates]
    for index, values in enumerate(arrays):
        _validate_rate(f"rate[{index}]", values)
    survival: FloatArray = np.ones(np.broadcast_shapes(*(value.shape for value in arrays)))
    for values in arrays:
        survival = survival * (1.0 - values)
    return np.asarray(1.0 - survival, dtype=np.float64)
