"""Static call ladders for barrier hedging (Hull 11e GE §26.17, pp.632–634)."""

import math
from dataclasses import dataclass

from . import bsm


@dataclass(frozen=True)
class StaticCallHedge:
    """Vanilla call portfolio matched to an up-and-out call at barrier-time nodes.

    The first leg is a call struck at the exotic strike; subsequent legs are
    calls struck at the barrier. ``value`` is the *raw* portfolio value before
    unwinding. It need not vanish between matched barrier nodes and must not be
    treated as the value of an already knocked-out claim.
    """

    strikes: tuple[float, ...]
    maturities: tuple[float, ...]
    positions: tuple[float, ...]
    expiry: float
    rate: float
    volatility: float
    dividend_yield: float

    def value(self, spot: float, time: float) -> float:
        """Mark the surviving call legs at ``time``; expired barrier calls are zero."""
        if not math.isfinite(spot) or spot <= 0.0:
            raise ValueError("spot must be finite and > 0")
        if not math.isfinite(time) or not 0.0 <= time <= self.expiry:
            raise ValueError("time must be finite and within [0, expiry]")
        return math.fsum(
            position
            * float(
                bsm.call_price(
                    spot, strike, self.rate, self.volatility, maturity - time, self.dividend_yield
                )
            )
            for strike, maturity, position in zip(
                self.strikes, self.maturities, self.positions, strict=True
            )
            if maturity >= time
        )


def up_and_out_call_hedge(
    spot: float,
    strike: float,
    barrier: float,
    rate: float,
    volatility: float,
    expiry: float,
    *,
    steps: int,
    dividend_yield: float = 0.0,
) -> StaticCallHedge:
    """Build Hull's §26.17 sequential static hedge for a continuous up-and-out call.

    ``steps`` barrier nodes are spaced by ``expiry / steps`` from time zero to
    the penultimate node. One strike-``strike`` call expiring at ``expiry``
    matches the terminal payoff below ``barrier``. Barrier-struck calls with
    decreasing maturities are then chosen backward to make the portfolio zero
    at each node. The hedge is valid while the barrier has not been reached;
    unwind it on a hit. Assumes constant BSM parameters, ``spot < barrier`` and
    ``strike < barrier``. All rates and volatility are annualized decimals.
    """
    values = (spot, strike, barrier, rate, volatility, expiry, dividend_yield)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("all market inputs must be finite")
    if spot <= 0.0 or strike <= 0.0 or barrier <= max(spot, strike):
        raise ValueError("require positive spot and strike below the barrier")
    if volatility <= 0.0 or expiry <= 0.0:
        raise ValueError("volatility and expiry must be > 0")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")

    strikes = (strike,) + (barrier,) * steps
    maturities = (expiry, *(expiry * (steps - index) / steps for index in range(steps)))
    positions = [1.0]
    for index in range(steps):
        node_time = expiry * (steps - index - 1) / steps
        basis = float(
            bsm.call_price(
                barrier,
                barrier,
                rate,
                volatility,
                maturities[index + 1] - node_time,
                dividend_yield,
            )
        )
        current = math.fsum(
            position
            * float(
                bsm.call_price(
                    barrier,
                    strikes[leg],
                    rate,
                    volatility,
                    maturities[leg] - node_time,
                    dividend_yield,
                )
            )
            for leg, position in enumerate(positions)
        )
        positions.append(-current / basis)
    return StaticCallHedge(
        strikes,
        maturities,
        tuple(positions),
        expiry,
        rate,
        volatility,
        dividend_yield,
    )
