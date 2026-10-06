"""Private loss-risk calculations for Hull Ch22.

Losses and loss_mean are positive for a loss. Existing public risk functions
use positive profits for mu; wrappers below explicitly reverse that sign.
"""

import math

import numpy as np
from scipy.stats import t

from . import risk


def _risk_inputs(scale, confidence, mean=0, horizon=1):
    if not np.isfinite([scale, confidence, mean, horizon]).all():
        raise ValueError("risk parameters must be finite")
    if scale < 0 or horizon < 0 or not 0 < confidence < 1:
        raise ValueError("nonnegative scale/horizon and 0 < confidence < 1 required")


def normal_loss_risk(sigma, confidence=0.99, *, loss_mean=0, horizon=1):
    """Normal daily losses aggregated over independent days, including mean."""
    _risk_inputs(sigma, confidence, loss_mean, horizon)
    return {
        "var": risk.normal_var(sigma, confidence, horizon, -loss_mean),
        "es": risk.normal_es(sigma, confidence, horizon, -loss_mean),
        "sigma": float(sigma * math.sqrt(horizon)),
        "mean": float(loss_mean * horizon),
    }


def student_loss_risk(scale, degrees, confidence=0.99, *, loss_mean=0):
    """Student-t loss location/scale risk; ES needs degrees > 1.

    scale is the distribution's scale, not its standard deviation. No
    square-root-time aggregation of a Student distribution is assumed.
    """
    _risk_inputs(scale, confidence, loss_mean)
    if not np.isfinite(degrees) or degrees <= 1:
        raise ValueError("Student ES requires degrees > 1")
    z = t.ppf(confidence, degrees)
    tail_mean = (degrees + z * z) / (degrees - 1) * t.pdf(z, degrees) / (1 - confidence)
    return {"var": float(loss_mean + scale * z), "es": float(loss_mean + scale * tail_mean)}


def ar1_horizon_risk(daily_sigma, phi, days, confidence=0.99, *, daily_loss_mean=0):
    """Exact normal risk for stationary AR(1) losses with marginal daily SD."""
    _risk_inputs(daily_sigma, confidence, daily_loss_mean)
    if not np.isfinite(phi) or abs(phi) >= 1 or days < 1 or int(days) != days:
        raise ValueError("stationary |phi| < 1 and positive integer days required")
    days = int(days)
    k = np.arange(1, days)
    variance_multiplier = float(days + 2 * np.sum((days - k) * phi**k))
    sigma = daily_sigma * math.sqrt(max(variance_multiplier, 0))
    result = normal_loss_risk(sigma, confidence, loss_mean=daily_loss_mean * days)
    result.update(
        variance_multiplier=variance_multiplier,
        sqrt_time_ratio=math.sqrt(max(variance_multiplier, 0) / days),
    )
    return result
