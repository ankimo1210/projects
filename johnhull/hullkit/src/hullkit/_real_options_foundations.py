"""Private Ch36 project cashflows, risk adjustment and investment exercise states."""

import math

import numpy as np


def real_project_npv(initial, times, expected_cashflows, required_rate):
    """P expected incremental cash discounted at its stated continuous required return."""
    from .rates import bond_price

    if initial < 0:
        raise ValueError("nonnegative initial investment required")
    return float(bond_price(times, expected_cashflows, required_rate) - initial)


def two_state_required_returns(spot, up, down, strike, rate, physical_growth, maturity):
    """Two-state replicated call/put prices and their implied P continuous required returns.

    Stock P expected growth determines P probabilities. Q probabilities price the
    payoff; its own required return is inferred from that price, not imposed as r.
    A zero-price/zero-expectation payoff has no identifiable required return.
    """
    if (
        not np.isfinite([spot, up, down, strike, rate, physical_growth, maturity]).all()
        or min(spot, strike, down) < 0
        or up <= down
        or maturity <= 0
    ):
        raise ValueError("ordered nonnegative prices, positive time and finite rates required")
    q = (spot * math.exp(rate * maturity) - down) / (up - down)
    p = (spot * math.exp(physical_growth * maturity) - down) / (up - down)
    if not 0 <= q <= 1 or not 0 <= p <= 1:
        raise ValueError("P and Q means must lie within the supplied two states")
    result = {"p_physical": p, "p_risk_neutral": q}
    for kind in ["call", "put"]:
        cash = (
            np.maximum(np.array([up, down]) - strike, 0)
            if kind == "call"
            else np.maximum(strike - np.array([up, down]), 0)
        )
        price = float(math.exp(-rate * maturity) * np.dot([q, 1 - q], cash))
        expected = float(np.dot([p, 1 - p], cash))
        delta = float((cash[0] - cash[1]) / (up - down))
        result[kind] = {
            "price": price,
            "expected_payoff": expected,
            "required_return": math.log(expected / price) / maturity
            if min(expected, price) > 0
            else None,
            "delta": delta,
            "cash_bond": math.exp(-rate * maturity) * (cash[1] - delta * down),
        }
    return result
