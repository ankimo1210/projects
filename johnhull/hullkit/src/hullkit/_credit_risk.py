"""Private Hull Ch24 credit calculations. Probabilities are fractions, times years.

P denotes real-world/historical probabilities, Q pricing probabilities. Numerical
transformations do not convert between these measures; the caller supplies the
appropriate inputs. Exposure amounts inherit the supplied contract's money unit.
"""

import math

import numpy as np

from . import credit_curve


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 1 or not np.isfinite(x).all():
        raise ValueError("finite nonempty vector required")
    return x


def _recovery(recovery):
    if not np.isfinite(recovery) or not 0 <= recovery <= 1:
        raise ValueError("recovery fraction in [0,1] required")


def constant_pd(hazard, maturity):
    if not np.isfinite([hazard, maturity]).all() or min(hazard, maturity) < 0:
        raise ValueError("nonnegative finite hazard/maturity required")
    return {"survival": math.exp(-hazard * maturity), "pd": -math.expm1(-hazard * maturity)}


def historical_pd(times, cumulative_pd, *, measure="P"):
    """Interval PDs and annual piecewise hazards from cumulative probabilities."""
    t, q = _vector(times), _vector(cumulative_pd)
    if (
        t.shape != q.shape
        or t[0] <= 0
        or np.any(np.diff(t) <= 0)
        or np.any(q < 0)
        or np.any(q >= 1)
        or np.any(np.diff(q) < 0)
        or measure not in ("P", "Q")
    ):
        raise ValueError(
            "increasing positive times, increasing finite PD in [0,1), and P/Q label required"
        )
    survival = 1 - q
    previous = np.r_[1, survival[:-1]]
    interval = previous - survival
    cumulative_hazard = -np.log1p(-q)
    forward = np.diff(np.r_[0, cumulative_hazard]) / np.diff(np.r_[0, t])
    curve = credit_curve.HazardCurve(tuple(t), tuple(forward))
    return {
        "survival": survival,
        "interval_pd": interval,
        "conditional_pd": interval / previous,
        "average_hazard": cumulative_hazard / t,
        "forward_hazard": forward,
        "curve": curve,
        "measure": measure,
    }
