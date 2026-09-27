"""Dupire local volatility from a smooth European call surface (Hull GE §27.3)."""

from __future__ import annotations

import math
from collections.abc import Callable


def dupire_local_vol(
    call_price: Callable[[float, float], float],
    strike: float,
    maturity: float,
    rate: float,
    dividend_yield: float = 0.0,
    *,
    strike_step: float,
    maturity_step: float,
) -> float:
    """Estimate ``σ_loc(K,T)`` with central differences in Hull GE eq. (27.4).

    ``call_price(K,T)`` supplies a *smooth* European call **price** in
    currency units, discounted to today (its present value). ``rate`` and
    ``dividend_yield`` are instantaneous forward rates at ``T``, not averages.
    Both finite-difference steps are explicit because the second strike
    derivative amplifies quote noise. The caller must smooth and check the
    surface before inversion; this scalar estimate is not a calibration or an
    arbitrage repair. It rejects nonpositive butterfly density or local
    variance rather than silently clipping either value.
    """
    values = (strike, maturity, rate, dividend_yield, strike_step, maturity_step)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("strike, maturity, rates and steps must be finite")
    if (
        strike <= 0
        or maturity <= 0
        or not 0 < strike_step < strike
        or not 0 < maturity_step < maturity
    ):
        raise ValueError("need K,T>0 and central-difference steps strictly inside both axes")

    def price(k: float, t: float) -> float:
        value = float(call_price(k, t))
        if not math.isfinite(value):
            raise ValueError("call surface returned a nonfinite price")
        return value

    middle = price(strike, maturity)
    low_k, high_k = price(strike - strike_step, maturity), price(strike + strike_step, maturity)
    low_t, high_t = price(strike, maturity - maturity_step), price(strike, maturity + maturity_step)
    first_k = (high_k - low_k) / (2 * strike_step)
    second_k = (high_k - 2 * middle + low_k) / strike_step**2
    first_t = (high_t - low_t) / (2 * maturity_step)
    if second_k <= 0:
        raise ValueError("call surface must be strictly convex in strike at (K,T)")
    numerator = first_t + dividend_yield * middle + strike * (rate - dividend_yield) * first_k
    if numerator <= 0:
        raise ValueError("Dupire forward-time numerator must be positive")
    return math.sqrt(2 * numerator / (strike**2 * second_k))
