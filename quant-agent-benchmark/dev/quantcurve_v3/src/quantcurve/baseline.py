"""Simple baseline: sequential bootstrap with linear zero-rate interpolation.

For each tenor cluster of deposits/OIS (in maturity order) one knot is added
and its zero rate solved so that the weighted sum of yield-equivalent
residuals of the cluster's instruments is zero. Bonds are not used - the
baseline is deliberately the textbook single-curve bootstrap. Extrapolation is
flat in the zero rate on both ends.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .curve import PiecewiseLinearZeroCurve
from .instruments import Instrument
from .pricing import rate_residual


def fit_baseline(instruments: list[Instrument], weights: np.ndarray, cluster_ids: np.ndarray) -> PiecewiseLinearZeroCurve:
    weights = np.asarray(weights, dtype=float)
    cluster_ids = np.asarray(cluster_ids)
    order = sorted(
        {cid for j, cid in enumerate(cluster_ids) if instruments[j].is_rate and weights[j] > 0},
        key=lambda cid: np.median([instruments[j].maturity for j in range(len(instruments)) if cluster_ids[j] == cid and instruments[j].is_rate]),
    )
    if not order:
        raise ValueError("baseline bootstrap needs at least one usable deposit or OIS quote")
    knots: list[float] = []
    zeros: list[float] = []
    for cid in order:
        members = [j for j in range(len(instruments)) if cluster_ids[j] == cid and instruments[j].is_rate and weights[j] > 0]
        knot = float(np.median([instruments[j].maturity for j in members]))
        if knots and knot <= knots[-1] + 1e-9:
            continue

        def objective(z: float) -> float:
            curve = PiecewiseLinearZeroCurve(np.array(knots + [knot]), np.array(zeros + [z]))
            return float(sum(weights[j] * rate_residual(instruments[j], curve) for j in members))

        lo, hi = -0.5, 1.0
        f_lo, f_hi = objective(lo), objective(hi)
        if f_lo * f_hi > 0:
            raise ValueError(f"baseline bootstrap failed to bracket the zero rate at {knot:.4f}y")
        z = brentq(objective, lo, hi, xtol=1e-12, rtol=1e-12, maxiter=200)
        knots.append(knot)
        zeros.append(float(z))
    return PiecewiseLinearZeroCurve(np.array(knots), np.array(zeros))
