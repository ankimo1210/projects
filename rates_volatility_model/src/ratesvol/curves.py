"""Zero-curve helpers (continuous compounding)."""

from __future__ import annotations

import numpy as np


def discount_factor(zero_rate, T):
    """P(0,T) = exp(-z(T) T)."""
    return np.exp(-np.asarray(zero_rate) * np.asarray(T))


def instantaneous_forward(zero_rates, T):
    """f(0,T) = z(T) + T dz/dT, derivative by finite differences on the grid."""
    zero_rates = np.asarray(zero_rates, dtype=float)
    T = np.asarray(T, dtype=float)
    return zero_rates + T * np.gradient(zero_rates, T)


def simple_forward(zero_rates, T_grid, T1, T2):
    """Continuously compounded forward between T1 < T2 from a linearly interpolated zero curve."""
    if T2 <= T1:
        raise ValueError("T2 must be greater than T1")
    z1 = np.interp(T1, T_grid, zero_rates)
    z2 = np.interp(T2, T_grid, zero_rates)
    return (z2 * T2 - z1 * T1) / (T2 - T1)
