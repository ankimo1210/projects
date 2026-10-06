"""Private Hull GE Ch18: futures cashflows, Black pricing and exercise."""

import math


def futures_exercise_cash(current, last_settlement, strike, *, quantity=1, multiplier=1, kind="call", premium=0):
    """Exercise then close at current F; all quotes share multiplier cash units.

    The settlement cash can be negative if the last settlement was OTM.
    Futures entry costs zero; an ordinary option premium is paid separately.
    Signed futures prices are allowed in this accounting, not in Black pricing.
    """
    if not all(math.isfinite(x) for x in (current, last_settlement, strike, quantity, multiplier, premium)) or min(quantity, premium) < 0 or multiplier <= 0 or kind not in ("call", "put"):
        raise ValueError("finite quotes, nonnegative quantity/premium and positive multiplier required")
    sign = 1 if kind == "call" else -1
    exercised = sign*(current-strike) > 0
    position = sign*quantity if exercised else 0
    settlement = position*(last_settlement-strike)*multiplier
    close_cash = position*(current-last_settlement)*multiplier
    premium_cash = quantity*multiplier*premium
    return {"position": position, "settlement": settlement, "close_cash": close_cash,
            "payoff": settlement+close_cash, "premium_cash": premium_cash,
            "profit": settlement+close_cash-premium_cash}


def fractional_quote(whole, ticks, denominator):
    """Nonnegative printed fractional quote, e.g. 96-09 in 32nds."""
    if not all(math.isfinite(x) and int(x) == x for x in (whole, ticks, denominator)) or whole < 0 or denominator <= 0 or not 0 <= ticks < denominator:
        raise ValueError("nonnegative whole and integer ticks within positive denominator required")
    return whole+ticks/denominator


def rate_from_futures_quote(quote):
    """100 minus the printed percentage quote, returned as a decimal rate."""
    if not math.isfinite(quote):
        raise ValueError("finite quote required")
    return (100-quote)/100
