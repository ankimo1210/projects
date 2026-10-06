"""Private Hull Ch25 contract cashflows and single/index CDS calculations.

Rates are fractions per year; payment times are simplified year fractions,
not a calendar/day-count or ISDA legal-contract engine. Values state their
notional unit explicitly. New pricing APIs remain private.
"""

import math

import numpy as np

from ._credit_risk import _recovery


def basis_points_to_rate(basis_points):
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
    if not np.isfinite([cds_spread, bond_yield, risk_free_rate]).all():
        raise ValueError("finite rates required")
    return {
        "basis": cds_spread - (bond_yield - risk_free_rate),
        "protected_yield": bond_yield - cds_spread,
    }
