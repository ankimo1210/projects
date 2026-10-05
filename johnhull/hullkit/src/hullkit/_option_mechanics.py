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


def adjust_stock_option(strike, units, new_shares, old_shares=1):
    """Scale strike/deliverable for an n-for-m split (Hull §10.4).

    The stock price and an existing per-unit premium scale by price_scale;
    total exercise cash and total premium are then invariant.
    """
    strike, units, new_shares, old_shares = _finite_values(strike, units, new_shares, old_shares)
    if np.any(units <= 0) or np.any(new_shares <= 0) or np.any(old_shares <= 0):
        raise ValueError("deliverable and split share counts must be positive")
    price_scale = old_shares / new_shares
    return dict(strike=strike * price_scale, units=units / price_scale, price_scale=price_scale)


def stock_dividend_adjustment(strike, units, dividend_fraction):
    """A stock dividend d is the (1+d)-for-1 adjustment; cash dividends are separate."""
    (dividend_fraction,) = _finite_values(dividend_fraction)
    if np.any(dividend_fraction < 0):
        raise ValueError("stock dividend fraction must be nonnegative")
    return adjust_stock_option(strike, units, 1 + dividend_fraction)


def legacy_option_expiries(year, month, cycle, *, after_current_expiry=False):
    """Hull's historical four-month listing rule, not a current exchange schedule.

    ``cycle`` is 1 (Jan/Apr/Jul/Oct), 2 or 3. Return two near months and
    two cycle months strictly after them. This explicit convention resolves
    overlapping near/cycle months beyond the three printed examples.
    """
    if any(not np.isfinite(v) or int(v) != v for v in (year, month, cycle)):
        raise ValueError("year, month and cycle must be finite integers")
    year, month, cycle = int(year), int(month), int(cycle)
    if year < 1 or not 1 <= month <= 12 or cycle not in (1, 2, 3):
        raise ValueError("invalid year, month or cycle")
    first = 12 * year + month - 1 + (1 if after_current_expiry else 0)
    listed = [first, first + 1]
    cursor = first + 2
    while len(listed) < 4:
        if (cursor % 12 + 1 - cycle) % 3 == 0:
            listed.append(cursor)
        cursor += 1
    return [(v // 12, v % 12 + 1) for v in listed]


def option_value_components(spot, strike, option_value, *, kind="call"):
    """Spot intrinsic/time value and moneyness; negative time value stays visible.

    The decomposition alone does not assert an American no-arbitrage bound.
    Forward moneyness and the alternative definition in §20.4 are separate.
    """
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    spot, strike, option_value = _finite_values(spot, strike, option_value)
    intrinsic = leg_payoff(spot, 1, kind, strike)
    difference = spot - strike if kind == "call" else strike - spot
    moneyness = np.where(difference > 0, "ITM", np.where(difference < 0, "OTM", "ATM"))
    return dict(intrinsic=intrinsic, time_value=option_value - intrinsic, moneyness=moneyness)
