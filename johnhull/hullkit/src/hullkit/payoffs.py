"""Terminal payoffs and option trading strategies (Hull 11e, Ch.10 / Ch.12).

A strategy is a list of legs ``(qty, kind, K)`` with kind in
{"call", "put", "stock"} (K is ignored for stock legs). Premiums/pricing are
deliberately out of scope — notebooks price legs with ``hullkit.bsm``.
"""

import math

import numpy as np

_KINDS = ("call", "put", "stock")


def leg_payoff(S, qty, kind, K=None):
    """Terminal payoff of one leg: qty x {call, put, stock}."""
    S = np.asarray(S, dtype=float)
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")
    if kind == "stock":
        return qty * S
    if K is None:
        raise ValueError("K is required for option legs")
    if kind == "call":
        return qty * np.maximum(S - K, 0.0)
    return qty * np.maximum(K - S, 0.0)


def strategy_payoff(S, legs):
    """Sum of leg payoffs; legs = iterable of (qty, kind, K)."""
    S = np.asarray(S, dtype=float)
    total = np.zeros_like(S)
    for qty, kind, K in legs:
        total = total + leg_payoff(S, qty, kind, K)
    return total


def box_spread_value(K1, K2, r, T):
    """(K2 - K1) e^{-rT} — European-only arbitrage value (Hull §12.3)."""
    return (K2 - K1) * math.exp(-r * T)


# Strategy registry: name -> legs factory (Hull Ch.12). Shared with notebooks.
STRATEGIES = {
    "bull_call_spread": lambda K1, K2: [(1, "call", K1), (-1, "call", K2)],
    "bear_put_spread": lambda K1, K2: [(1, "put", K2), (-1, "put", K1)],
    "butterfly": lambda K1, K2, K3: [
        (1, "call", K1),
        (-2, "call", K2),
        (1, "call", K3),
    ],
    "straddle": lambda K: [(1, "call", K), (1, "put", K)],
    "strangle": lambda K1, K2: [(1, "put", K1), (1, "call", K2)],
    "strip": lambda K: [(1, "call", K), (2, "put", K)],
    "strap": lambda K: [(2, "call", K), (1, "put", K)],
    "covered_call": lambda K: [(1, "stock", None), (-1, "call", K)],
    "protective_put": lambda K: [(1, "stock", None), (1, "put", K)],
}
