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


def black_details(forward, strike, rate, sigma, maturity):
    """Ordinary European premium with deterministic discount and lognormal F."""
    from ._index_currency import carry_option_details

    return carry_option_details(forward, strike, rate, rate, sigma, maturity)


def futures_at_option_expiry(terminal_spot, rate, yield_rate, option_maturity, futures_maturity):
    """Terminal futures/spot basis under deterministic continuous carry."""
    if not all(math.isfinite(x) for x in (terminal_spot, rate, yield_rate, option_maturity, futures_maturity)) or terminal_spot <= 0 or option_maturity < 0 or futures_maturity < option_maturity:
        raise ValueError("positive spot and futures maturity at or after option expiry required")
    return terminal_spot*math.exp((rate-yield_rate)*(futures_maturity-option_maturity))


def spot_futures_equivalence(spot, strike, rate, yield_rate, sigma, maturity, *, futures_maturity=None):
    """Hull 18.3 European equal-maturity comparison; deterministic carry only."""
    from ._index_currency import carry_option_details

    spot_values = carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)
    if futures_maturity is None:
        futures_maturity = maturity
    if not math.isfinite(futures_maturity) or not math.isclose(futures_maturity, maturity, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("spot/futures payoff equivalence requires matching maturities")
    future_values = black_details(spot_values["forward"], strike, rate, sigma, maturity)
    return {"forward": spot_values["forward"],
            "spot_call": spot_values["call"], "spot_put": spot_values["put"],
            "futures_call": future_values["call"], "futures_put": future_values["put"]}
