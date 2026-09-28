"""Hull GE §26.1 packages: zero-cost range forwards and deferred-payment options.

A package is a portfolio of European options, forwards, cash and the underlying.
``range_forward`` chooses the call strike ``K2`` that makes a long call worth as
much as a short put at ``K1 < F``, so the package costs nothing (Hull §17.2 and
§26.1). ``deferred_option`` moves the premium from today to maturity, growing it
at the risk-free rate; ``break_forward`` is the deferred call struck at the
forward price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from hullkit import bsm

_SIDES = {"long": 1.0, "short": -1.0}
_KINDS = ("call", "put")
_AT_FORWARD_RTOL = 1e-12
_MAX_BRACKET_DOUBLINGS = 200


def _check_market(spot: float, sigma: float, T: float) -> None:
    if not (math.isfinite(spot) and spot > 0.0):
        raise ValueError("spot must be finite and > 0")
    if not (math.isfinite(sigma) and sigma > 0.0):
        raise ValueError("sigma must be finite and > 0")
    if not (math.isfinite(T) and T > 0.0):
        raise ValueError("T must be finite and > 0")


def _sign(side: str) -> float:
    if side not in _SIDES:
        raise ValueError(f"side must be one of {tuple(_SIDES)}, got {side!r}")
    return _SIDES[side]


@dataclass(frozen=True)
class RangeForward:
    """A long call at ``call_strike`` and a short put at ``put_strike``, same maturity."""

    spot: float
    r: float
    sigma: float
    T: float
    q: float
    put_strike: float
    call_strike: float
    forward: float

    @property
    def premium(self) -> float:
        """Value of the short put, which the long call must equal."""
        return float(bsm.put_price(self.spot, self.put_strike, self.r, self.sigma, self.T, self.q))

    @property
    def cost(self) -> float:
        """Call value less put value at today's price; zero by construction."""
        call = bsm.call_price(self.spot, self.call_strike, self.r, self.sigma, self.T, self.q)
        return float(call) - self.premium

    def payoff(self, spot_at_maturity, side: str = "long"):
        """Maturity payoff of the long (or, with ``side="short"``, the short) package."""
        s = np.asarray(spot_at_maturity, dtype=float)
        long_payoff = np.maximum(s - self.call_strike, 0.0) - np.maximum(self.put_strike - s, 0.0)
        return _sign(side) * long_payoff


def range_forward(
    put_strike: float, spot: float, r: float, sigma: float, T: float, q: float = 0.0
) -> RangeForward:
    """Zero-cost range forward: the call strike ``K2`` with ``c(K2) = p(put_strike)``.

    ``put_strike`` must lie in ``(0, F]`` with ``F = spot * exp((r - q) * T)``.
    ``c`` falls and ``p`` rises in the strike and ``c(F) = p(F)``, so the root is
    unique and satisfies ``put_strike < F < K2``. ``put_strike == F`` gives the
    forward contract itself.
    """
    _check_market(spot, sigma, T)
    forward = spot * math.exp((r - q) * T)
    if not (math.isfinite(put_strike) and put_strike > 0.0):
        raise ValueError("put_strike must be finite and > 0")
    if put_strike > forward * (1.0 + _AT_FORWARD_RTOL):
        raise ValueError(f"put_strike must not exceed the forward price {forward:.10g}")
    if put_strike >= forward * (1.0 - _AT_FORWARD_RTOL):
        return RangeForward(spot, r, sigma, T, q, put_strike, forward, forward)

    target = float(bsm.put_price(spot, put_strike, r, sigma, T, q))

    def excess(strike: float) -> float:
        return float(bsm.call_price(spot, strike, r, sigma, T, q)) - target

    upper = forward * 1.5
    for _ in range(_MAX_BRACKET_DOUBLINGS):
        if excess(upper) < 0.0:
            break
        upper *= 2.0
    else:
        raise ArithmeticError("no call strike with the required premium was found")
    call_strike = brentq(excess, forward, upper, xtol=1e-15 * forward, rtol=4 * np.finfo(float).eps)
    return RangeForward(spot, r, sigma, T, q, put_strike, float(call_strike), forward)


def deferred_amount(premium: float, r: float, T: float) -> float:
    """Amount ``A = premium * exp(r T)`` paid at maturity in place of ``premium`` today."""
    if not (math.isfinite(premium) and premium >= 0.0):
        raise ValueError("premium must be finite and >= 0")
    return premium * math.exp(r * T)


@dataclass(frozen=True)
class DeferredOption:
    """A European option whose premium is paid at maturity as ``amount``."""

    kind: str
    strike: float
    spot: float
    r: float
    sigma: float
    T: float
    q: float
    premium: float
    amount: float

    @property
    def max_loss(self) -> float:
        """Largest possible net loss: the deferred payment, reached when the option expires worthless."""
        return self.amount

    @property
    def breakeven(self) -> float:
        """Maturity price at which the net payoff is zero."""
        return self.strike + self.amount if self.kind == "call" else self.strike - self.amount

    def payoff(self, spot_at_maturity):
        """Net payoff at maturity: option payoff less the deferred amount."""
        s = np.asarray(spot_at_maturity, dtype=float)
        leg = (
            np.maximum(s - self.strike, 0.0)
            if self.kind == "call"
            else np.maximum(self.strike - s, 0.0)
        )
        return leg - self.amount


def deferred_option(
    kind: str, strike: float, spot: float, r: float, sigma: float, T: float, q: float = 0.0
) -> DeferredOption:
    """Option bought for the deferred amount ``A = c exp(r T)``, worth nothing today."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")
    _check_market(spot, sigma, T)
    if not (math.isfinite(strike) and strike > 0.0):
        raise ValueError("strike must be finite and > 0")
    price = bsm.call_price if kind == "call" else bsm.put_price
    premium = float(price(spot, strike, r, sigma, T, q))
    return DeferredOption(
        kind, strike, spot, r, sigma, T, q, premium, deferred_amount(premium, r, T)
    )


def break_forward(spot: float, r: float, sigma: float, T: float, q: float = 0.0) -> DeferredOption:
    """Deferred call struck at the forward price (Boston option, cancelable forward)."""
    _check_market(spot, sigma, T)
    return deferred_option("call", spot * math.exp((r - q) * T), spot, r, sigma, T, q)
