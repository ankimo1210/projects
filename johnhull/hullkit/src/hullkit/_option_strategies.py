"""Private Hull GE Ch12 calculations: funding, profits and residual valuation.

Terminal profit uses Hull's nominal payoff minus initial cost convention,
without accruing financing costs. Time-dependent valuation is kept separate.
"""

import math

import numpy as np

from . import bsm, payoffs, trees, volatility


def _price(spot, strike, rate, sigma, maturity, *, q=0, kind="call"):
    values = (spot, strike, rate, sigma, maturity, q)
    if not all(math.isfinite(value) for value in values) or min(spot, strike, sigma, maturity) < 0:
        raise ValueError(
            "finite inputs and nonnegative spot, strike, volatility, maturity required"
        )
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    if spot == 0 or strike == 0 or sigma == 0 or maturity == 0:
        difference = spot * math.exp(-q * maturity) - strike * math.exp(-rate * maturity)
        return max(difference if kind == "call" else -difference, 0)
    price = bsm.call_price if kind == "call" else bsm.put_price
    return float(price(spot, strike, rate, sigma, maturity, q=q))


def principal_note(
    terminal_spot,
    spot,
    principal,
    investment,
    rate,
    sigma,
    maturity,
    *,
    strike=None,
    q=0,
    participation=1,
):
    """Example 12.1: zero-coupon principal protection plus call participation.

    ``spot`` is the option's portfolio unit; participation may differ from 1.
    Full participation can exceed the funding budget. ``None`` means no
    nonnegative participation is affordable; ``inf`` means a zero-cost call.
    No issuer default, fees or interest on the displayed nominal profit.
    """
    strike = spot if strike is None else strike
    option_price = _price(spot, strike, rate, sigma, maturity, q=q)
    if (
        not all(math.isfinite(v) for v in (principal, investment, participation))
        or min(principal, investment, participation) < 0
    ):
        raise ValueError("principal, investment and participation must be finite and nonnegative")
    terminal = np.asarray(terminal_spot, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    bond_cost = principal * math.exp(-rate * maturity)
    budget = investment - bond_cost
    affordable = None if budget < 0 else (budget / option_price if option_price > 0 else math.inf)
    cost = bond_cost + participation * option_price
    payoff = principal + payoffs.leg_payoff(terminal, participation, "call", strike)
    return dict(
        bond_cost=bond_cost,
        option_budget=budget,
        option_price=option_price,
        affordable_participation=affordable,
        cost=cost,
        cash_surplus=investment - cost,
        payoff=payoff,
        profit=payoff - investment,
    )


def principal_note_volatility_limit(
    spot, principal, investment, rate, maturity, *, strike=None, q=0, participation=1
):
    """Solve full funding equality using hullkit's IV bracket [1e-6,5].

    At a zero-volatility boundary return 0; an underfunded deterministic
    payoff or a nonunique zero-maturity problem has no volatility solution.
    """
    if maturity <= 0 or participation <= 0:
        raise ValueError("positive maturity and participation required for volatility limit")
    strike = spot if strike is None else strike
    note = principal_note(
        [],
        spot,
        principal,
        investment,
        rate,
        0,
        maturity,
        strike=strike,
        q=q,
        participation=participation,
    )
    target = note["option_budget"] / participation
    if math.isclose(target, note["option_price"], rel_tol=1e-12, abs_tol=1e-12):
        return 0.0
    return float(volatility.implied_vol(target, spot, strike, rate, maturity, q=q))


def stock_option_legs(name, strike):
    """Figure 12.1's covered/protective positions and their exact reversals."""
    if not math.isfinite(strike) or strike < 0:
        raise ValueError("strike must be finite and nonnegative")
    reverse = name.startswith("reverse_")
    base = name.removeprefix("reverse_")
    if base not in ("covered_call", "protective_put"):
        raise ValueError("unknown stock-option position")
    direction = -1 if reverse else 1
    return [(direction * qty, kind, k) for qty, kind, k in payoffs.STRATEGIES[base](strike)]


def strategy_profit(
    terminal_spot,
    legs,
    premiums,
    *,
    maturity=None,
    dividend_times=(),
    dividend_amounts=(),
    reinvest_rate=0,
):
    """Terminal payoff, signed initial cost and Hull's nominal profit.

    Premiums are per unit, in leg order; quantities supply the buy/sell sign.
    Stock dividends are separate dated cashflows; shorts owe these payments.
    A schedule requires a terminal horizon. Default reinvestment rate 0 means
    raw received cash; a supplied rate explicitly accrues dividend receipts.
    Initial financing costs are excluded from the displayed profit.
    """
    terminal = np.asarray(terminal_spot, dtype=float)
    legs = tuple(legs)
    prices = np.asarray(premiums, dtype=float)
    if (
        prices.ndim != 1
        or len(prices) != len(legs)
        or np.any(prices < 0)
        or not np.all(np.isfinite(prices))
    ):
        raise ValueError("finite nonnegative per-unit premiums must align with legs")
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    stock_quantity = 0.0
    cost = 0.0
    for (quantity, kind, strike), price in zip(legs, prices, strict=True):
        if not math.isfinite(quantity):
            raise ValueError("leg quantity must be finite")
        if kind == "stock":
            stock_quantity += quantity
        elif strike is None or not math.isfinite(strike) or strike < 0:
            raise ValueError("option strikes must be finite and nonnegative")
        cost += quantity * price
    if len(dividend_times) and maturity is None:
        raise ValueError("a dividend schedule requires the terminal maturity")
    dividends = bsm.pv_dividends(dividend_times, dividend_amounts, reinvest_rate, maturity)
    dividend_cash = stock_quantity * dividends * math.exp(reinvest_rate * (maturity or 0))
    payoff = payoffs.strategy_payoff(terminal, legs)
    total_cash = payoff + dividend_cash
    return dict(
        payoff=payoff,
        initial_cost=float(cost),
        dividend_cash=dividend_cash,
        total_cash=total_cash,
        profit=total_cash - cost,
    )


def spread_legs(name, strikes, *, reverse=False):
    """Canonical Ch12 same-maturity spreads without changing the registry."""
    k = np.asarray(strikes, dtype=float)
    butterfly = name in ("call_butterfly", "put_butterfly")
    if (
        k.ndim != 1
        or len(k) != (3 if butterfly else 2)
        or not np.all(np.isfinite(k))
        or np.any(k < 0)
        or np.any(np.diff(k) <= 0)
    ):
        raise ValueError("finite nonnegative strictly increasing spread strikes required")
    if butterfly:
        if not math.isclose(k[0] + k[2], 2 * k[1], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("canonical butterfly strikes must be equally spaced")
        kind = "call" if name == "call_butterfly" else "put"
        legs = [(1, kind, k[0]), (-2, kind, k[1]), (1, kind, k[2])]
    elif name in ("bull_call_spread", "bear_call_spread"):
        sign = 1 if name == "bull_call_spread" else -1
        legs = [(sign, "call", k[0]), (-sign, "call", k[1])]
    elif name in ("bear_put_spread", "bull_put_spread"):
        sign = 1 if name == "bear_put_spread" else -1
        legs = [(sign, "put", k[1]), (-sign, "put", k[0])]
    elif name == "box":
        legs = [(1, "call", k[0]), (-1, "call", k[1]), (1, "put", k[1]), (-1, "put", k[0])]
    else:
        raise ValueError("unknown spread")
    return [(-q if reverse else q, kind, float(strike)) for q, kind, strike in legs]


def spread_value(spot, strikes, rate, sigma, maturity, *, name, american=False, steps=1000):
    """Sum standalone no-dividend option values; American legs are not a bond.

    This does not simulate early assignment on a short American leg. Its sum
    differs from the European box's discounted fixed terminal payoff.
    """
    legs = spread_legs(name, strikes)
    prices = []
    for _, kind, strike in legs:
        price = _price(spot, strike, rate, sigma, maturity, kind=kind)
        if american:
            if steps < 1 or int(steps) != steps:
                raise ValueError("positive integer American tree steps required")
            if min(spot, strike, sigma, maturity) == 0:
                intrinsic = max(spot - strike, 0) if kind == "call" else max(strike - spot, 0)
                price = max(price, intrinsic)
            else:
                price = trees.crr_price(
                    spot, strike, rate, sigma, maturity, int(steps), kind=kind, american=True
                )
        prices.append(price)
    return dict(
        legs=legs,
        leg_prices=np.asarray(prices),
        price=sum(q * p for (q, _, _), p in zip(legs, prices, strict=True)),
    )


def short_expiry_spread(
    spots,
    short_strike,
    long_strike,
    rate,
    sigma,
    short_maturity,
    long_maturity,
    *,
    kind="call",
    short_premium=0,
    long_premium=0,
    reverse=False,
    q=0,
):
    """Calendar/diagonal value at T1: long remaining option minus short payoff.

    Caller premiums determine nominal profit; they are not inferred from the
    observed T1 spot. The residual term is T2-T1, not the original T2.
    """
    if (
        not all(
            math.isfinite(v) for v in (short_maturity, long_maturity, short_premium, long_premium)
        )
        or min(short_maturity, short_premium, long_premium) < 0
        or long_maturity < short_maturity
    ):
        raise ValueError("nonnegative premiums and 0 <= T1 <= T2 required")
    if not math.isfinite(short_strike) or short_strike < 0:
        raise ValueError("short strike must be finite and nonnegative")
    axis = np.asarray(spots, dtype=float)
    if axis.ndim != 1:
        raise ValueError("spots must be a one-dimensional short-expiry curve")
    remaining = long_maturity - short_maturity
    marks = np.array(
        [_price(float(s), long_strike, rate, sigma, remaining, q=q, kind=kind) for s in axis]
    )
    short_payoff = payoffs.leg_payoff(axis, 1, kind, short_strike)
    direction = -1 if reverse else 1
    value = direction * (marks - short_payoff)
    cost = direction * (long_premium - short_premium)
    return dict(
        remaining_long_value=marks,
        short_payoff=short_payoff,
        initial_cost=cost,
        value=value,
        profit=value - cost,
    )


def combination_profile(terminal_spot, name, strikes, premiums, *, reverse=False):
    """Section 12.4 combinations, nominal profits, tail slopes and breakevens.

    Breakeven points are restricted to nonnegative stock prices. With a free
    strangle the whole strike interval has zero profit, so its endpoints do
    not describe two isolated roots. Short downside at S=0 is finite.
    """
    if name not in ("straddle", "strip", "strap", "strangle"):
        raise ValueError("unknown combination")
    k = np.asarray(strikes, dtype=float)
    if (
        k.ndim != 1
        or len(k) != (2 if name == "strangle" else 1)
        or not np.all(np.isfinite(k))
        or np.any(k < 0)
    ):
        raise ValueError("finite nonnegative combination strikes required")
    if name == "strangle" and k[0] >= k[1]:
        raise ValueError("strangle requires put strike below call strike")
    base = payoffs.STRATEGIES[name](*k.tolist())
    direction = -1 if reverse else 1
    result = strategy_profit(
        terminal_spot, [(direction * q, kind, strike) for q, kind, strike in base], premiums
    )
    cost = direction * result["initial_cost"]
    call_weight, call_strike = next((q, strike) for q, kind, strike in base if kind == "call")
    put_weight, put_strike = next((q, strike) for q, kind, strike in base if kind == "put")
    points = sorted(
        {
            value
            for value in (put_strike - cost / put_weight, call_strike + cost / call_weight)
            if value >= 0
        }
    )
    return dict(
        **result,
        break_evens=np.asarray(points),
        zero_profit_interval=(put_strike, call_strike) if cost == 0 else None,
        left_slope=-direction * put_weight,
        right_slope=direction * call_weight,
        minimum_profit=-math.inf if reverse else -cost,
        maximum_profit=cost if reverse else math.inf,
        zero_stock_profit=direction * (put_weight * put_strike - cost),
    )


def butterfly_spike(terminal_spot, center, width, *, height=None):
    """Figure 12.13: unit butterfly height h, scaled by height/h."""
    height = width if height is None else height
    if not all(math.isfinite(v) for v in (center, width, height)) or width <= 0 or center < width:
        raise ValueError("positive width and nonnegative outer strikes required")
    legs = [
        (quantity * height / width, kind, strike)
        for quantity, kind, strike in spread_legs(
            "call_butterfly", [center - width, center, center + width]
        )
    ]
    result = strategy_profit(terminal_spot, legs, [0, 0, 0])
    return dict(legs=legs, payoff=result["payoff"])


def replicate_payoff(terminal_spot, knots, values):
    """Finite butterfly-hat interpolation, with explicit padded zero tails.

    Add a zero-valued knot one local spacing beyond each endpoint. The
    original node values interpolate exactly, including nonzero endpoints;
    the padding describes behavior outside the requested approximation range.
    Nonuniform knots use unequal wing weights. A negative computational
    padding strike is translated into stock plus terminal cash, never a
    traded negative-strike call. Cash here is payable at terminal time.
    """
    k, y = np.asarray(knots, dtype=float), np.asarray(values, dtype=float)
    if (
        k.ndim != 1
        or y.shape != k.shape
        or len(k) < 2
        or not np.all(np.isfinite(k))
        or not np.all(np.isfinite(y))
        or np.any(k < 0)
        or np.any(np.diff(k) <= 0)
    ):
        raise ValueError("finite nonnegative increasing knots and matching node values required")
    terminal = np.asarray(terminal_spot, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    padded = np.concatenate(([k[0] - (k[1] - k[0])], k, [k[-1] + (k[-1] - k[-2])]))
    weights = {}
    for i, height in enumerate(y, start=1):
        left, center, right = padded[i - 1 : i + 2]
        left_weight, right_weight = height / (center - left), height / (right - center)
        for strike, weight in (
            (left, left_weight),
            (center, -left_weight - right_weight),
            (right, right_weight),
        ):
            weights[strike] = weights.get(strike, 0.0) + weight
    cash, stock = 0.0, 0.0
    legs = []
    for strike, quantity in sorted(weights.items()):
        if strike < 0:
            stock += quantity
            cash -= quantity * strike
        elif quantity != 0:
            legs.append((float(quantity), "call", float(strike)))
    if stock != 0:
        legs.append((float(stock), "stock", None))
    payoff = payoffs.strategy_payoff(terminal, legs) + cash
    return dict(legs=legs, cash=float(cash), payoff=payoff, padded_knots=padded)
