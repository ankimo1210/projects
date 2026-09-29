"""Hull GE §26.2 perpetual American calls and puts under constant-parameter GBM.

The contract has no expiry. For a positive risk-free rate and a nonnegative
continuous dividend yield, the optimal exercise policy is a first passage
through a constant stock-price boundary. A zero-dividend call has no finite
optimal exercise time; its value is the stock price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PerpetualOption:
    """Value and optimal exercise policy at one positive spot price."""

    kind: str
    spot: float
    strike: float
    r: float
    sigma: float
    q: float
    exponent: float
    boundary: float
    price: float
    delta: float
    exercise_now: bool


def _positive_finite(name: str, value: float) -> None:
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{name} must be finite and > 0")


def _log_ratio(numerator: float, denominator: float) -> float:
    """Keep a positive ratio's logarithm when division underflows or overflows."""
    ratio = numerator / denominator
    if 0.5 < ratio < 2.0:
        return math.log1p((numerator - denominator) / denominator)
    if 0.0 < ratio < math.inf:
        return math.log(ratio)
    return math.log(numerator) - math.log(denominator)


def perpetual_option(
    kind: str, spot: float, strike: float, r: float, sigma: float, q: float = 0.0
) -> PerpetualOption:
    """Price a perpetual American call or put and return its exercise boundary.

    Inputs are positive spot and strike, annualized continuous rate r > 0,
    annualized volatility sigma > 0, and continuous dividend yield q >= 0.
    The rate and yield are constant. The boundary is infinity for a
    zero-dividend call: no finite exercise level is optimal. Delta is the
    derivative of option value with respect to the current spot. A finite
    exercise boundary must be distinguishable from the strike at float
    precision; otherwise a ValueError is raised rather than returning an
    incorrect exercise decision. Very small positive q can make the returned
    call exponent round to 1 even while its finite boundary remains valid.
    """
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")
    _positive_finite("spot", spot)
    _positive_finite("strike", strike)
    _positive_finite("r", r)
    _positive_finite("sigma", sigma)
    if not (math.isfinite(q) and q >= 0.0):
        raise ValueError("q must be finite and >= 0")

    if kind == "call" and q == 0.0:
        return PerpetualOption(kind, spot, strike, r, sigma, q, 1.0, math.inf, spot, 1.0, False)

    sigma2 = sigma * sigma
    if not (math.isfinite(sigma2) and sigma2 > 0.0):
        raise ValueError("sigma squared is outside floating-point range")

    # For the call, compute a1-1 directly to avoid cancellation as q -> 0.
    # Inserting a=1+e into the characteristic polynomial gives
    # (sigma^2/2)e^2 + (r-q+sigma^2/2)e - q = 0.
    shifted_drift = r - q + sigma2 / 2.0
    shifted_disc = math.hypot(shifted_drift, sigma * math.sqrt(2.0 * q))
    if shifted_drift >= 0.0:
        excess = 2.0 * q / (shifted_disc + shifted_drift)
    else:
        excess = (shifted_disc - shifted_drift) / sigma2
    a1 = 1.0 + excess

    # The positive put exponent a2 corresponds to the negative power -a2.
    w = r - q - sigma2 / 2.0
    disc = math.hypot(w, sigma * math.sqrt(2.0 * r))
    a2 = (disc + w) / sigma2 if w >= 0.0 else 2.0 * r / (disc - w)

    if kind == "call":
        if not (math.isfinite(excess) and excess > 0.0):
            raise ValueError("call exponent is not representable for these inputs")
        boundary = strike + strike / excess
        if not math.isfinite(boundary):
            raise ValueError("call boundary overflows for these inputs")
        if boundary <= strike:
            raise ValueError("call boundary cannot be distinguished from strike")
        if spot >= boundary:
            price, delta, exercise_now = spot - strike, 1.0, True
        else:
            price = spot * math.exp(-math.log1p(excess) + excess * _log_ratio(spot, boundary))
            delta, exercise_now = a1 * price / spot, False
        exponent = a1
    else:
        if not (math.isfinite(a2) and a2 > 0.0):
            raise ValueError("put exponent is not representable for these inputs")
        boundary = strike * (a2 / (a2 + 1.0))
        if not 0.0 < boundary < strike:
            raise ValueError("put boundary cannot be represented between zero and strike")
        if spot <= boundary:
            price, delta, exercise_now = strike - spot, -1.0, True
        else:
            price = (strike / (a2 + 1.0)) * math.exp(-a2 * _log_ratio(spot, boundary))
            delta, exercise_now = -a2 * price / spot, False
        exponent = a2

    if not (math.isfinite(price) and math.isfinite(delta)):
        raise ValueError("option value or delta overflows for these inputs")
    return PerpetualOption(
        kind, spot, strike, r, sigma, q, exponent, boundary, price, delta, exercise_now
    )
