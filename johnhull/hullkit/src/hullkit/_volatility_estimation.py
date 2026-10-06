"""Private Hull Ch23 estimators with explicit forecast timing and units.

Conditional variances are daily return variances. Series have n+1 entries:
entry i forecasts return i before observing it; the last is the next forecast.
These historical P-distribution forecasts are not market Q implied volatilities.
"""

import math

import numpy as np


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 1 or not np.isfinite(x).all():
        raise ValueError("finite nonempty vector required")
    return x


def price_returns(prices, *, kind="simple"):
    p = _vector(prices)
    if p.size < 2 or np.any(p <= 0):
        raise ValueError("at least two positive prices required")
    if kind == "simple":
        return p[1:] / p[:-1] - 1
    if kind == "log":
        return np.diff(np.log(p))
    raise ValueError("return kind must be simple or log")


def estimate_variance(returns, *, center=True, ddof=1):
    """Centered sample variance or zero-mean squared-return estimate."""
    u = _vector(returns)
    if ddof < 0 or int(ddof) != ddof or ddof >= u.size:
        raise ValueError("nonnegative integer ddof smaller than sample size required")
    residual = u - u.mean() if center else u
    return float(residual @ residual / (u.size - ddof))


def arch_forecast(history, weights, *, long_variance=0, long_weight=0):
    """Weighted past squared returns plus long_weight*long_variance.

    history and weights are chronological, oldest first. Only the last len(weights)
    history values are used. The caller passes observations available before the
    forecast day. All weights, including long_weight, must sum to one.
    """
    u, w = _vector(history), _vector(weights)
    if (
        u.size < w.size
        or np.any(w < 0)
        or not np.isfinite([long_variance, long_weight]).all()
        or long_variance < 0
        or long_weight < 0
        or not math.isclose(float(w.sum() + long_weight), 1, abs_tol=1e-12, rel_tol=1e-12)
    ):
        raise ValueError("nonnegative normalized weights/variance and sufficient history required")
    return float(w @ u[-w.size :] ** 2 + long_weight * long_variance)
