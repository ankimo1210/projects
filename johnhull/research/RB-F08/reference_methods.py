"""Independent scalar references for RB-F08, without importing hullkit."""

from __future__ import annotations

import math

import numpy as np
from scipy.special import ndtri


def _parameters(parameters):
    p = dict(parameters)
    p.setdefault("yield_rate", 0.0)
    names = ("spot", "strike", "rate", "sigma", "maturity", "yield_rate")
    if any(name not in p for name in names):
        raise ValueError("complete GBM contract required")
    if not all(math.isfinite(p[name]) for name in names):
        raise ValueError("finite GBM contract required")
    if min(p["spot"], p["strike"], p["maturity"]) <= 0 or p["sigma"] < 0:
        raise ValueError("positive spot, strike, maturity and nonnegative sigma required")
    return p


def _cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _mass(lower, upper):
    if lower >= upper:
        return 0.0
    if lower >= 0:
        return 0.5 * (math.erfc(lower / math.sqrt(2.0)) - math.erfc(upper / math.sqrt(2.0)))
    return _cdf(upper) - _cdf(lower)


def black_call(parameters: dict) -> float:
    """Discount a lognormal terminal call using own erfc normal probabilities."""
    p = _parameters(parameters)
    s, k, r, sigma, time, q = (
        p[name] for name in ("spot", "strike", "rate", "sigma", "maturity", "yield_rate")
    )
    if sigma == 0:
        return max(s * math.exp(-q * time) - k * math.exp(-r * time), 0.0)
    width = sigma * math.sqrt(time)
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * time) / width
    d2 = d1 - width
    return s * math.exp(-q * time) * _cdf(d1) - k * math.exp(-r * time) * _cdf(d2)


def one_step_euler_call(parameters: dict) -> float:
    """Exact Gaussian positive-part expectation of a single ordinary Euler step."""
    p = _parameters(parameters)
    time = p["maturity"]
    a = p["spot"] * (1 + (p["rate"] - p["yield_rate"]) * time) - p["strike"]
    b = p["spot"] * p["sigma"] * math.sqrt(time)
    if b == 0:
        return math.exp(-p["rate"] * time) * max(a, 0.0)
    d = a / b
    value = a * _cdf(d) + b * math.exp(-0.5 * d * d) / math.sqrt(2 * math.pi)
    return math.exp(-p["rate"] * time) * value


def scalar_euler_payoffs(parameters: dict, normals: np.ndarray) -> np.ndarray:
    """Replay each Euler recurrence in a scalar loop, retaining all original paths."""
    p = _parameters(parameters)
    z = np.asarray(normals, dtype=float)
    if z.ndim != 2 or min(z.shape) < 1 or not np.isfinite(z).all():
        raise ValueError("finite nonempty path-by-step shocks required")
    dt = p["maturity"] / z.shape[1]
    drift = (p["rate"] - p["yield_rate"]) * dt
    diffusion = p["sigma"] * math.sqrt(dt)
    discount = math.exp(-p["rate"] * p["maturity"])
    out = []
    for row in z:
        stock = p["spot"]
        for shock in row:
            stock = stock * (1 + drift + diffusion * float(shock))
            if not math.isfinite(stock):
                raise ValueError("nonfinite Euler state invalidates the run")
        out.append(discount * max(stock - p["strike"], 0.0))
    values = np.asarray(out)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite payoff invalidates the run")
    return values


def clipped_black_call(parameters: dict, clip: tuple[float, float]) -> float:
    """Integrate a clipped uniform transform, including both endpoint masses.

    Uses the lognormal partial expectation and tail-stable erfc differences.
    The clipping changes the mathematical integrand; its value is separate from
    the economic Black price even when the difference is numerically very small.
    """
    p = _parameters(parameters)
    if len(clip) != 2 or not all(math.isfinite(x) for x in clip) or not 0 < clip[0] < clip[1] < 1:
        raise ValueError("clip must satisfy 0 < lower < upper < 1")
    if p["sigma"] == 0:
        return black_call(p)
    time = p["maturity"]
    lower, upper = clip
    z_lower, z_upper = float(ndtri(lower)), float(ndtri(upper))
    width = p["sigma"] * math.sqrt(time)
    stock_scale = p["spot"] * math.exp((p["rate"] - p["yield_rate"] - 0.5 * p["sigma"] ** 2) * time)
    discount = math.exp(-p["rate"] * time)

    def terminal_payoff(z):
        return max(stock_scale * math.exp(width * z) - p["strike"], 0.0)

    endpoints = lower * terminal_payoff(z_lower) + (1 - upper) * terminal_payoff(z_upper)
    lower_payoff = max(z_lower, math.log(p["strike"] / stock_scale) / width)
    interior = 0.0
    if lower_payoff < z_upper:
        interior = stock_scale * math.exp(0.5 * width * width) * _mass(
            lower_payoff - width, z_upper - width
        ) - p["strike"] * _mass(lower_payoff, z_upper)
    return discount * (endpoints + interior)
