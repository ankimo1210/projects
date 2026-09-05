"""Small, unambiguous convention helpers used by visible tests."""

from __future__ import annotations

import math

import numpy as np


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


def discount_array_from_zero(zero_rate: np.ndarray, maturity_years: np.ndarray) -> np.ndarray:
    """Vectorized continuously compounded discount factors."""
    z = np.asarray(zero_rate, dtype=float)
    t = np.asarray(maturity_years, dtype=float)
    if np.any(t < 0) or not np.all(np.isfinite(z)) or not np.all(np.isfinite(t)):
        raise ValueError("finite zero rates and non-negative maturities required")
    return np.exp(np.clip(-z * t, -700.0, 700.0))


def forward_from_zero_grid(maturity_years: np.ndarray, zero_rate: np.ndarray) -> np.ndarray:
    """Instantaneous forward rate d(T*z(T))/dT on an ordered grid."""
    t = np.asarray(maturity_years, dtype=float)
    z = np.asarray(zero_rate, dtype=float)
    if t.ndim != 1 or z.shape != t.shape or len(t) < 3 or np.any(np.diff(t) <= 0):
        raise ValueError("ordered one-dimensional grids of at least three points required")
    return np.gradient(t * z, t, edge_order=2)
