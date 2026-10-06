"""Private Hull Ch25 contract cashflows and single/index CDS calculations.

Rates are fractions per year; payment times are simplified year fractions,
not a calendar/day-count or ISDA legal-contract engine. Values state their
notional unit explicitly. New pricing APIs remain private.
"""

import math

import numpy as np

from ._credit_risk import _recovery


def basis_points_to_rate(basis_points):
    """Convert signed basis points to a rate fraction; one bp equals 0.0001."""
    if not np.isfinite(basis_points):
        raise ValueError("finite basis points required")
    return basis_points / 10000


def cds_contract_cashflows(
    notional, spread, maturity, *, frequency=4, default_time=None, recovery=0.4
):
    """Surviving coupons, last accrual and loss-of-par protection.

    Default at a scheduled date replaces that coupon with full-period accrual;
    no coupon is paid twice. A final shortened coupon period is supported.
    default_time beyond maturity leaves the contract alive through maturity.
    """
    _recovery(recovery)
    if (
        not np.isfinite([notional, spread, maturity]).all()
        or min(notional, spread) < 0
        or maturity <= 0
        or frequency < 1
        or int(frequency) != frequency
        or (default_time is not None and (not np.isfinite(default_time) or default_time < 0))
    ):
        raise ValueError(
            "nonnegative notional/spread/default time and positive maturity/frequency required"
        )
    times = np.arange(1, math.floor(maturity * frequency) + 1) / frequency
    if times.size == 0 or times[-1] < maturity:
        times = np.r_[times, maturity]
    active_default = default_time is not None and default_time <= maturity
    if active_default:
        times = np.r_[times[times < default_time], default_time]
    accrual = np.diff(np.r_[0, times])
    premium = notional * spread * accrual
    protection = np.zeros(times.size)
    if active_default:
        protection[-1] = notional * (1 - recovery)
    buyer = protection - premium
    return {
        "times": times,
        "premium": premium,
        "protection": protection,
        "buyer_cashflows": buyer,
        "seller_cashflows": -buyer,
        "regular_premium_rate": spread / frequency,
        "regular_premium": notional * spread / frequency,
    }


def cds_bond_basis(cds_spread, bond_yield, risk_free_rate):
    """CDS minus bond-yield spread, and yield after buying protection; all rates fractions."""
    if not np.isfinite([cds_spread, bond_yield, risk_free_rate]).all():
        raise ValueError("finite rates required")
    return {
        "basis": cds_spread - (bond_yield - risk_free_rate),
        "protected_yield": bond_yield - cds_spread,
    }


def cds_leg_table(curve, recovery, rate, maturity, *, frequency=1, start=0):
    """All row coefficients in Hull Tables25.1–5, per unit notional/spread."""
    from . import cds

    _recovery(recovery)
    if not np.isfinite([rate, maturity, start]).all() or start < 0:
        raise ValueError("finite rate/times and nonnegative start required")
    hazard = cds._as_curve(curve)
    times = cds._grid(start, maturity, frequency)
    dt = 1 / frequency
    mid = times - dt / 2
    survival = hazard.survival(times)
    pd = hazard.survival(times - dt) - survival
    end_df, mid_df = np.exp(-rate * times), np.exp(-rate * mid)
    annuity = dt * survival * end_df
    accrual_expected = dt / 2 * pd
    accrual = accrual_expected * mid_df
    protection_expected = (1 - recovery) * pd
    protection = protection_expected * mid_df
    binary = pd * mid_df
    duration = float(annuity.sum() + accrual.sum())
    return {
        "times": times,
        "mid_times": mid,
        "survival": survival,
        "interval_pd": pd,
        "end_discount": end_df,
        "mid_discount": mid_df,
        "annuity_rows": annuity,
        "accrual_expected": accrual_expected,
        "accrual_rows": accrual,
        "protection_expected": protection_expected,
        "protection_rows": protection,
        "binary_rows": binary,
        "annuity": float(annuity.sum()),
        "accrual": float(accrual.sum()),
        "protection": float(protection.sum()),
        "binary_protection": float(binary.sum()),
        "risky_duration": duration,
        "par_spread": float(protection.sum() / duration),
    }


def calibrated_cds(spread, recovery, rate, maturity, *, frequency=1):
    """Existing implied-hazard calibration with explicit row/leg output."""
    from . import cds

    if not np.isfinite(spread) or spread < 0:
        raise ValueError("nonnegative finite par spread required")
    _recovery(recovery)
    if recovery == 1:
        raise ValueError("spread-to-hazard calibration requires recovery below one")
    hazard = 0.0 if spread == 0 else cds.implied_hazard(spread, recovery, rate, maturity, frequency)
    result = cds_leg_table(hazard, recovery, rate, maturity, frequency=frequency)
    result["hazard"] = hazard
    return result


def recovery_recalibration(
    spread, recoveries, rate, maturity, *, frequency=1, contract_spread=None
):
    """Recalibrate hazard for each R at fixed market quote before comparing MTM."""
    from ._credit_risk import _vector

    recovery = _vector(recoveries)
    coupon = spread if contract_spread is None else contract_spread
    if not np.isfinite(coupon) or coupon < 0:
        raise ValueError("nonnegative contract premium required")
    tables = [
        calibrated_cds(spread, float(r), rate, maturity, frequency=frequency) for r in recovery
    ]
    return {
        "hazards": np.array([t["hazard"] for t in tables]),
        "par_spreads": np.array([t["par_spread"] for t in tables]),
        "binary_spreads": np.array([t["binary_protection"] / t["risky_duration"] for t in tables]),
        "buyer_values": np.array([t["protection"] - coupon * t["risky_duration"] for t in tables]),
    }
