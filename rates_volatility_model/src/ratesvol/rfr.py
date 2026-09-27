"""Overnight risk-free-rate (SOFR/TONA/SONIA-style) compounding."""

from __future__ import annotations

import numpy as np


def compounded_in_arrears(daily_rates, day_weights, day_basis=360):
    """Annualised compounded rate: (prod(1 + r_i n_i / basis) - 1) * basis / sum(n_i).

    ``day_weights`` n_i is the number of calendar days each fixing applies to
    (a Friday fixing usually covers 3 days). Use basis 360 for SOFR/ESTR, 365 for TONA/SONIA.
    """
    r = np.asarray(daily_rates, dtype=float)
    n = np.asarray(day_weights, dtype=float)
    if r.shape != n.shape:
        raise ValueError("daily_rates and day_weights must have the same shape")
    growth = np.prod(1 + r * n / day_basis)
    return (growth - 1) * day_basis / n.sum()


def simple_average(daily_rates, day_weights):
    """Day-weighted arithmetic average of the fixings (no compounding)."""
    r = np.asarray(daily_rates, dtype=float)
    n = np.asarray(day_weights, dtype=float)
    return float((r * n).sum() / n.sum())
