"""Private Hull GE Ch12 calculations: funding, profits and residual valuation.

Terminal profit uses Hull's nominal payoff minus initial cost convention,
without accruing financing costs. Time-dependent valuation is kept separate.
"""

import math

import numpy as np

from . import bsm, payoffs, volatility


def _price(spot, strike, rate, sigma, maturity, *, q=0, kind="call"):
    values = (spot, strike, rate, sigma, maturity, q)
    if not all(math.isfinite(value) for value in values) or min(spot, strike, sigma, maturity) < 0:
        raise ValueError("finite inputs and nonnegative spot, strike, volatility, maturity required")
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    if spot == 0 or strike == 0 or sigma == 0 or maturity == 0:
        difference = spot*math.exp(-q*maturity)-strike*math.exp(-rate*maturity)
        return max(difference if kind == "call" else -difference, 0)
    price = bsm.call_price if kind == "call" else bsm.put_price
    return float(price(spot, strike, rate, sigma, maturity, q=q))


def principal_note(terminal_spot, spot, principal, investment, rate, sigma, maturity,
                   *, strike=None, q=0, participation=1):
    """Example 12.1: zero-coupon principal protection plus call participation.

    ``spot`` is the option's portfolio unit; participation may differ from 1.
    Full participation can exceed the funding budget. ``None`` means no
    nonnegative participation is affordable; ``inf`` means a zero-cost call.
    No issuer default, fees or interest on the displayed nominal profit.
    """
    strike = spot if strike is None else strike
    option_price = _price(spot, strike, rate, sigma, maturity, q=q)
    if not all(math.isfinite(v) for v in (principal, investment, participation)) or min(principal, investment, participation) < 0:
        raise ValueError("principal, investment and participation must be finite and nonnegative")
    terminal = np.asarray(terminal_spot, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    bond_cost = principal*math.exp(-rate*maturity)
    budget = investment-bond_cost
    affordable = None if budget < 0 else (budget/option_price if option_price > 0 else math.inf)
    cost = bond_cost+participation*option_price
    payoff = principal+payoffs.leg_payoff(terminal, participation, "call", strike)
    return dict(bond_cost=bond_cost, option_budget=budget, option_price=option_price,
                affordable_participation=affordable, cost=cost, cash_surplus=investment-cost,
                payoff=payoff, profit=payoff-investment)


def principal_note_volatility_limit(spot, principal, investment, rate, maturity,
                                    *, strike=None, q=0, participation=1):
    """Solve full funding equality using hullkit's IV bracket [1e-6,5].

    At a zero-volatility boundary return 0; an underfunded deterministic
    payoff or a nonunique zero-maturity problem has no volatility solution.
    """
    if maturity <= 0 or participation <= 0:
        raise ValueError("positive maturity and participation required for volatility limit")
    strike = spot if strike is None else strike
    note = principal_note([], spot, principal, investment, rate, 0, maturity,
                          strike=strike, q=q, participation=participation)
    target = note["option_budget"]/participation
    if math.isclose(target, note["option_price"], rel_tol=1e-12, abs_tol=1e-12):
        return 0.
    return float(volatility.implied_vol(target, spot, strike, rate, maturity, q=q))
