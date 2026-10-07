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


def option_trade_costs(bid, ask, *, contracts=1, multiplier=100, fixed_fee=0, fee_per_contract=0):
    """Bid/ask half-spread cost and order cashflows (Hull §10.6).

    Fees are caller inputs, not current broker rates. The fixed commission
    is charged once for a nonempty order; fee_per_contract scales with count.
    """
    bid, ask, contracts, multiplier, fixed_fee, fee_per_contract = _finite_values(
        bid, ask, contracts, multiplier, fixed_fee, fee_per_contract
    )
    if np.any(ask < bid) or np.any(contracts < 0) or np.any(multiplier <= 0):
        raise ValueError("quotes must be ordered, contracts nonnegative and multiplier positive")
    midpoint = (bid + ask) / 2
    half_spread = (ask - bid) / 2
    units = contracts * multiplier
    commission = np.where(contracts > 0, fixed_fee, 0) + contracts * fee_per_contract
    return dict(
        midpoint=midpoint,
        half_spread=half_spread,
        cost_per_contract=half_spread * multiplier,
        commission=commission,
        buy_cashflow=-units * ask - commission,
        sell_cashflow=units * bid - commission,
        total_cost=units * half_spread + commission,
    )


def option_exit_cashflows(intrinsic, bid, *, units=100, sale_fee=0, exercise_fee=0):
    """Long holder's sale/exercise cash after caller-supplied total fees.

    These are alternative exit cashflows; the sunk initial premium is common
    to both, and a future stock position after physical exercise is separate.
    """
    intrinsic, bid, units, sale_fee, exercise_fee = _finite_values(
        intrinsic, bid, units, sale_fee, exercise_fee
    )
    if np.any(intrinsic < 0) or np.any(units < 0):
        raise ValueError("intrinsic value and holder units must be nonnegative")
    sale = units * bid - np.where(units > 0, sale_fee, 0)
    exercise = units * intrinsic - np.where(units > 0, exercise_fee, 0)
    return dict(sale=sale, exercise=exercise, sale_minus_exercise=sale - exercise)


def legacy_short_option_margin(
    spot,
    strike,
    option_mark,
    *,
    kind="call",
    contracts=1,
    multiplier=100,
    risk_rate=0.20,
    floor_rate=0.10,
):
    """Hull §10.7 historical naked-option collateral formula, in currency units.

    option_mark is the opening premium or the current mark on later dates.
    risk_rate=0.15 is the book's index example. Broker-specific/current rules
    are caller inputs rather than assertions made by this educational helper.
    """
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    spot, strike, option_mark, contracts, multiplier, risk_rate, floor_rate = _finite_values(
        spot, strike, option_mark, contracts, multiplier, risk_rate, floor_rate
    )
    if any(np.any(v < 0) for v in (spot, strike, option_mark, contracts, risk_rate, floor_rate)):
        raise ValueError("stock margin inputs must be nonnegative")
    if np.any(multiplier <= 0):
        raise ValueError("contract multiplier must be positive")
    otm = np.maximum(strike - spot if kind == "call" else spot - strike, 0)
    units = contracts * multiplier
    primary = units * (option_mark + risk_rate * spot - otm)
    floor = units * (option_mark + floor_rate * (spot if kind == "call" else strike))
    return dict(
        primary=primary,
        floor=floor,
        required=np.maximum(primary, floor),
        mark_value=units * option_mark,
    )


def legacy_margin_cashflows(
    spot,
    strike,
    option_mark,
    *,
    initial_cash,
    withdraw_excess=True,
    **margin_parameters,
):
    """Recompute historical margin along one path and adjust cash collateral.

    initial_cash includes credited sale proceeds. Positive top_up is an
    additional deposit; withdrawal releases excess collateral. The account
    has no interest, fees or position-closing cashflows in this calculation.
    """
    required = np.atleast_1d(
        legacy_short_option_margin(spot, strike, option_mark, **margin_parameters)["required"]
    )
    if required.ndim != 1:
        raise ValueError("cash account requires one time path")
    cash = float(initial_cash)
    if not np.isfinite(cash):
        raise ValueError("initial cash must be finite")
    top_up, withdrawal, balance = (np.zeros_like(required) for _ in range(3))
    for i, target in enumerate(required):
        top_up[i] = max(float(target) - cash, 0)
        cash += top_up[i]
        if withdraw_excess:
            withdrawal[i] = max(cash - float(target), 0)
            cash -= withdrawal[i]
        balance[i] = cash
    return dict(required=required, top_up=top_up, withdrawal=withdrawal, balance=balance)


def legacy_covered_call_loan_limit(spot, strike, *, units=100):
    """Book's covered-call stock borrowing limit: units × 0.5 × min(S,K)."""
    spot, strike, units = _finite_values(spot, strike, units)
    if any(np.any(v < 0) for v in (spot, strike, units)):
        raise ValueError("stock values and covered units must be nonnegative")
    return units * 0.5 * np.minimum(spot, strike)


def legacy_long_option_loan_limit(option_mark, expiry_months, *, units=100):
    """Book's 25% borrowing limit only for more than nine months to expiry.

    Exactly nine months follows the fully paid side of this explicitly
    historical convention; this is not a current regulation lookup.
    """
    option_mark, expiry_months, units = _finite_values(option_mark, expiry_months, units)
    if any(np.any(v < 0) for v in (option_mark, expiry_months, units)):
        raise ValueError("option mark, expiry and units must be nonnegative")
    return np.where(expiry_months > 9, 0.25 * units * option_mark, 0)
