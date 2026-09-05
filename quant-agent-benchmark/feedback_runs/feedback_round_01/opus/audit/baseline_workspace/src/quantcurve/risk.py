"""DV01 and key-rate sensitivities, with analytic finite-difference verification.

Definitions follow ``CONVENTIONS.md`` exactly:

* **DV01** is the *central* finite difference of the receiver / fixed-instrument
  PV for a parallel one-basis-point move of the continuously compounded zero
  curve: ``(PV[-1bp] - PV[+1bp]) / 2``.  Deposits and swaps use notional
  1,000,000; bonds use face 100.  A receiver position gains when rates fall, so
  a positive DV01 means "value per basis point of rate fall".
* **Key-rate sensitivities** use the same central difference with a *local* bump
  shape centred on 2Y, 5Y, 10Y and 30Y.  The shape is a **triangular tent** that
  peaks at its own key tenor and decays linearly to zero at the neighbouring key
  tenors, flat at 1 below the first tenor and above the last.  The four tents sum
  to exactly one at every maturity, so the key rates add back to the parallel
  DV01 up to the second-order term that the central difference already removes.

``verify_dv01`` re-derives the same number analytically, cash flow by cash flow,
which is what the "finite-difference verification" requirement asks for.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .conventions import BASIS_POINT
from .curve import DiscountCurve
from .instruments import BOND, DEPOSIT, OIS_SWAP, Instrument
from .pricing import bond_cashflows, instrument_pv

__all__ = [
    "KEY_TENORS",
    "tent_bump",
    "parallel_bump",
    "dv01",
    "key_rate_sensitivities",
    "analytic_dv01",
    "verify_dv01",
    "InstrumentRisk",
    "instrument_risk",
]

#: Key-rate tenors mandated by the benchmark.
KEY_TENORS: tuple[float, ...] = (2.0, 5.0, 10.0, 30.0)


def parallel_bump(size: float):
    """Additive parallel shift of the continuously compounded zero rate."""

    def bump(t):
        return np.full(np.asarray(t, dtype=float).shape, size)

    return bump


def tent_bump(index: int, size: float, tenors: tuple[float, ...] = KEY_TENORS):
    """Triangular key-rate bump shape; the family sums to one everywhere."""
    if not 0 <= index < len(tenors):
        raise IndexError("key-rate index out of range")
    centre = tenors[index]
    left = tenors[index - 1] if index > 0 else None
    right = tenors[index + 1] if index + 1 < len(tenors) else None

    def bump(t):
        t = np.asarray(t, dtype=float)
        shape = np.zeros(t.shape, dtype=float)
        if left is None:
            shape = np.where(t <= centre, 1.0, shape)
        else:
            rising = (t > left) & (t <= centre)
            shape = np.where(rising, (t - left) / (centre - left), shape)
        if right is None:
            shape = np.where(t > centre, 1.0, shape)
        else:
            falling = (t > centre) & (t < right)
            shape = np.where(falling, (right - t) / (right - centre), shape)
        return shape * size

    return bump


def dv01(curve: DiscountCurve, inst: Instrument, bump_size: float = BASIS_POINT) -> float:
    """Central-difference parallel DV01 in the instrument's own notional units."""
    down = instrument_pv(curve.bumped(parallel_bump(-bump_size)), inst)
    up = instrument_pv(curve.bumped(parallel_bump(+bump_size)), inst)
    return 0.5 * (down - up)


def key_rate_sensitivities(
    curve: DiscountCurve,
    inst: Instrument,
    bump_size: float = BASIS_POINT,
    tenors: tuple[float, ...] = KEY_TENORS,
) -> dict[str, float]:
    """Central-difference key-rate sensitivities for the documented tent shapes."""
    out: dict[str, float] = {}
    for index, tenor in enumerate(tenors):
        down = instrument_pv(curve.bumped(tent_bump(index, -bump_size, tenors)), inst)
        up = instrument_pv(curve.bumped(tent_bump(index, +bump_size, tenors)), inst)
        label = f"key_{tenor:g}y".replace(".", "_")
        out[label] = 0.5 * (down - up)
    return out


def analytic_dv01(
    curve: DiscountCurve, inst: Instrument, bump_size: float = BASIS_POINT
) -> float:
    """Closed-form parallel DV01, used to verify the finite-difference result.

    A parallel zero shift ``eps`` maps ``D(t) -> D(t) exp(-eps t)``, so for any
    fixed cash-flow schedule ``dPV/d eps = -sum_i t_i C_i D(t_i)``.  The OIS float
    leg ``1 - D(T)`` is handled explicitly.
    """
    times = inst.schedule()
    discounts = np.asarray(curve.discount(times), dtype=float)
    if inst.instrument_type == DEPOSIT:
        amount = inst.notional() * (1.0 + inst.quote / 100.0 * inst.maturity_years)
        derivative = -inst.maturity_years * amount * float(discounts[-1])
    elif inst.instrument_type == OIS_SWAP:
        accrual = 1.0 / float(inst.fixed_frequency)
        fixed = inst.quote / 100.0 * accrual * float(np.sum(-times * discounts))
        # d/d(eps) of the float leg -(1 - D(T)) is -T D(T): the float leg loses
        # value when rates rise, exactly like the fixed leg.
        floating = -float(times[-1] * discounts[-1])
        derivative = inst.notional() * (fixed + floating)
    elif inst.instrument_type == BOND:
        flows = bond_cashflows(times, float(inst.coupon_rate), inst.fixed_frequency)
        derivative = float(np.sum(-times * flows * discounts))
    else:  # pragma: no cover - guarded upstream
        raise ValueError(f"unsupported instrument type: {inst.instrument_type}")
    return -derivative * bump_size


def verify_dv01(
    curve: DiscountCurve, inst: Instrument, bump_size: float = BASIS_POINT
) -> dict[str, float]:
    """Compare the reported finite-difference DV01 with the analytic derivative."""
    numeric = dv01(curve, inst, bump_size)
    analytic = analytic_dv01(curve, inst, bump_size)
    denominator = max(abs(analytic), 1.0e-12)
    return {
        "dv01_finite_difference": numeric,
        "dv01_analytic": analytic,
        "absolute_difference": numeric - analytic,
        "relative_difference": (numeric - analytic) / denominator,
    }


@dataclass(frozen=True)
class InstrumentRisk:
    instrument_id: str
    instrument_type: str
    maturity_years: float
    dv01: float
    key_rates: dict[str, float]
    key_rate_sum: float
    analytic_dv01: float
    key_sum_error: float
    analytic_error: float


def instrument_risk(
    curve: DiscountCurve,
    inst: Instrument,
    bump_size: float = BASIS_POINT,
    tenors: tuple[float, ...] = KEY_TENORS,
) -> InstrumentRisk:
    """Full risk record for one instrument, including both consistency checks."""
    parallel = dv01(curve, inst, bump_size)
    keys = key_rate_sensitivities(curve, inst, bump_size, tenors)
    key_sum = float(sum(keys.values()))
    analytic = analytic_dv01(curve, inst, bump_size)
    denominator = max(abs(parallel), 1.0e-9)
    return InstrumentRisk(
        instrument_id=inst.instrument_id,
        instrument_type=inst.instrument_type,
        maturity_years=inst.maturity_years,
        dv01=parallel,
        key_rates=keys,
        key_rate_sum=key_sum,
        analytic_dv01=analytic,
        key_sum_error=(key_sum - parallel) / denominator,
        analytic_error=(parallel - analytic) / denominator,
    )
