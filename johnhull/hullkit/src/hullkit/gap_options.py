"""Hull GE §26.4 gap options with validated inputs and a pricing decomposition.

A gap call pays ``S_T - K1`` when ``S_T > K2``; a gap put pays ``K1 - S_T`` when
``S_T < K2``. ``K2`` triggers the payment and ``K1`` settles it, so the payoff
jumps by ``K2 - K1`` at the trigger and is negative on one side when the two
strikes are ordered against the holder. The price uses Hull's equations 26.1
and 26.2 (``hullkit.exotics.gap_call``/``gap_put``); this module adds the input
contract and splits the price into the regular option struck at ``K2`` plus a
signed cash-or-nothing adjustment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import numpy as np
from scipy.stats import norm

from hullkit import bsm, exotics

_KINDS = ("call", "put")
_LOG_MAX = math.log(np.finfo(float).max)


def _finite(name: str, value, *, minimum: float | None = None, strict: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if minimum is not None and (result <= minimum if strict else result < minimum):
        raise ValueError(f"{name} must be {'>' if strict else '>='} {minimum:g}")
    return result


@dataclass(frozen=True)
class GapOption:
    """Price and decomposition of a European gap option under BSM."""

    kind: str
    spot: float
    K1: float
    K2: float
    r: float
    sigma: float
    T: float
    q: float
    price: float
    regular_price: float
    trigger_adjustment: float
    trigger_probability: float
    forward: float

    @property
    def zero_value_settlement(self) -> float:
        """``K1`` that makes this option worth zero: the risk-neutral mean of ``S_T`` given the trigger."""
        if self.trigger_probability <= 0.0:
            raise ValueError(
                "the trigger probability is zero; no settlement strike prices it at zero"
            )
        d1 = bsm.d1(self.spot, self.K2, self.r, self.sigma, self.T, self.q)
        asset = norm.cdf(d1) if self.kind == "call" else norm.cdf(-d1)
        return float(self.forward * asset / self.trigger_probability)

    def payoff(self, spot_at_maturity):
        """Maturity payoff ``S_T - K1`` above (call) or ``K1 - S_T`` below (put) ``K2``, not floored."""
        s = np.asarray(spot_at_maturity, dtype=float)
        if self.kind == "call":
            return np.where(s > self.K2, s - self.K1, 0.0)
        return np.where(s < self.K2, self.K1 - s, 0.0)


def gap_option(
    kind: str,
    spot: float,
    K1: float,
    K2: float,
    r: float,
    sigma: float,
    T: float,
    q: float = 0.0,
) -> GapOption:
    """Price a gap call/put with settlement strike ``K1`` and trigger ``K2``.

    ``price = regular_price + trigger_adjustment``: the regular option struck at
    ``K2`` plus ``(K2 - K1) e^{-rT} N(d2)`` for a call, or
    ``(K1 - K2) e^{-rT} N(-d2)`` for a put. ``trigger_probability`` is the
    risk-neutral probability ``N(d2)`` or ``N(-d2)`` that the payment is made.
    ``K1 = 0`` gives the asset-or-nothing call, or minus the asset-or-nothing
    put. ``ValueError`` is raised for an unknown kind, inputs that are not finite
    real numbers, ``spot``, ``K2``, ``sigma`` or ``T`` not positive, ``K1``
    negative, or a discount factor, forward or price that overflows.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")
    spot = _finite("spot", spot, minimum=0.0)
    K1 = _finite("K1", K1, minimum=0.0, strict=False)
    K2 = _finite("K2", K2, minimum=0.0)
    r = _finite("r", r)
    sigma = _finite("sigma", sigma, minimum=0.0)
    T = _finite("T", T, minimum=0.0)
    q = _finite("q", q)
    for name, rate in (("r", r), ("q", q)):
        if -rate * T > _LOG_MAX:
            raise ValueError(f"exp(-{name} T) overflows")
    if math.log(spot) + (r - q) * T > _LOG_MAX:
        raise ValueError("the forward price overflows")
    discount = math.exp(-r * T)
    forward = math.exp(math.log(spot) + (r - q) * T)

    d2 = float(bsm.d2(spot, K2, r, sigma, T, q))
    if kind == "call":
        price = exotics.gap_call(spot, K1, K2, r, sigma, T, q)
        regular = bsm.call_price(spot, K2, r, sigma, T, q)
        probability = float(norm.cdf(d2))
        adjustment = (K2 - K1) * discount * probability
    else:
        price = exotics.gap_put(spot, K1, K2, r, sigma, T, q)
        regular = bsm.put_price(spot, K2, r, sigma, T, q)
        probability = float(norm.cdf(-d2))
        adjustment = (K1 - K2) * discount * probability
    if not all(math.isfinite(value) for value in (price, regular, adjustment)):
        raise ValueError("the price overflows the floating-point range")
    return GapOption(
        kind,
        spot,
        K1,
        K2,
        r,
        sigma,
        T,
        q,
        float(price),
        float(regular),
        float(adjustment),
        probability,
        forward,
    )
