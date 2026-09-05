"""Small, unambiguous convention helpers used by visible tests."""

from __future__ import annotations

import math


def discount_from_zero(zero_rate: float, maturity_years: float) -> float:
    """Continuously compounded discount factor exp(-z*T)."""
    if not math.isfinite(zero_rate) or not math.isfinite(maturity_years):
        raise ValueError("finite zero_rate and maturity_years required")
    if maturity_years < 0:
        raise ValueError("maturity_years must be non-negative")
    return math.exp(-zero_rate * maturity_years)


def zero_from_discount(discount_factor: float, maturity_years: float) -> float:
    """Continuously compounded zero rate -log(D)/T."""
    if not math.isfinite(discount_factor) or not math.isfinite(maturity_years):
        raise ValueError("finite discount_factor and maturity_years required")
    if discount_factor <= 0:
        raise ValueError("discount_factor must be positive")
    if maturity_years <= 0:
        raise ValueError("maturity_years must be positive")
    return -math.log(discount_factor) / maturity_years


def simple_deposit_rate(discount_factor: float, maturity_years: float) -> float:
    """Simple annual deposit rate implied by a discount factor."""
    if not math.isfinite(discount_factor) or not math.isfinite(maturity_years):
        raise ValueError("finite discount_factor and maturity_years required")
    if discount_factor <= 0 or maturity_years <= 0:
        raise ValueError("positive discount_factor and maturity_years required")
    return (1.0 / discount_factor - 1.0) / maturity_years
