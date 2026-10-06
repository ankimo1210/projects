"""Private Hull Ch4 rate conventions and cashflow-based foundational calculations."""

import numpy as np


def compounded_reference_rate(rates, days, *, basis=360):
    """Daily simple-interest factors compounded over caller-supplied day weights.

    A Friday fixing can carry days=3. Annualization uses basis/sum(days), not the
    number of observed fixings. This contains no calendar or fixing-date policy.
    """
    rates = np.asarray(rates, dtype=float)
    days = np.asarray(days, dtype=float)
    if (
        rates.ndim != 1
        or rates.shape != days.shape
        or not len(rates)
        or not np.isfinite(rates).all()
        or not np.isfinite(days).all()
        or not np.isfinite(basis)
        or basis <= 0
        or np.any(days <= 0)
    ):
        raise ValueError("paired fixings/day weights and positive basis required")
    factors = 1 + rates * days / basis
    if np.any(factors <= 0):
        raise ValueError("positive daily growth factors required")
    growth = float(np.prod(factors))
    return {
        "growth": growth,
        "days": float(days.sum()),
        "annualized_rate": (growth - 1) * basis / days.sum(),
    }
