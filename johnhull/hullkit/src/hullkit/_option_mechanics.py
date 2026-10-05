"""Private terminal arithmetic for Hull Ch10; premiums exclude time-value carry."""

import numpy as np

from .payoffs import leg_payoff


def _finite_values(*values):
    arrays = np.broadcast_arrays(*(np.asarray(value, dtype=float) for value in values))
    if any(np.any(~np.isfinite(value)) for value in arrays):
        raise ValueError("cashflow inputs must be finite")
    return arrays


def option_cashflows(spot, strike, premium, *, kind="call", quantity=1, multiplier=1):
    """Signed terminal payoff, initial premium cashflow and profit (Hull §10.1–10.2).

    ``quantity`` is positive for a buyer and negative for a writer;
    ``multiplier`` converts one contract to underlying units. Interest on
    the initial premium is excluded, as in Hull's terminal-profit figures.
    The exercise value is per underlying unit before the position sign.
    With zero premium, the payoff is index/futures exercise cash (§10.3).
    Inputs broadcast; signed underlying/strike values remain valid arithmetic.
    """
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    spot, strike, premium, quantity, multiplier = _finite_values(
        spot, strike, premium, quantity, multiplier
    )
    if np.any(multiplier <= 0):
        raise ValueError("contract multiplier must be positive")
    intrinsic = leg_payoff(spot, 1, kind, strike)
    units = quantity * multiplier
    payoff = units * intrinsic
    premium_cashflow = -units * premium
    return dict(
        per_unit_payoff=intrinsic,
        payoff=payoff,
        premium_cashflow=premium_cashflow,
        profit=payoff + premium_cashflow,
        unexercised_profit=premium_cashflow,
    )
