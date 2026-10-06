"""Private Hull GE Ch17: index insurance, currency cashflows and carry pricing."""

import math
import sys

from ._option_mechanics import option_cashflows


def capm_portfolio_scenario(value, initial_index, terminal_index, beta, rate, maturity, index_yield, portfolio_yield):
    """Hull's simple-period CAPM conditional expectation, not a realized hedge.

    Rates multiply T as in Tables17.1/2; these are not exponential carry
    rates. Residual portfolio risk and premium cost are not in this scenario.
    """
    if not all(math.isfinite(x) for x in (value, initial_index, terminal_index, beta, rate, maturity, index_yield, portfolio_yield)) or min(value, initial_index) <= 0 or terminal_index < 0 or maturity < 0:
        raise ValueError("positive initial value/index and nonnegative terminal index/time required")
    price_return = terminal_index/initial_index-1
    income = index_yield*maturity
    rf = rate*maturity
    excess = price_return+income-rf
    portfolio_excess = beta*excess
    total = rf+portfolio_excess
    portfolio_price = total-portfolio_yield*maturity
    return {"index_price_return": price_return, "index_income_return": income,
            "index_total_return": price_return+income, "risk_free_return": rf,
            "index_excess_return": excess, "portfolio_excess_return": portfolio_excess,
            "portfolio_total_return": total, "portfolio_price_return": portfolio_price,
            "price_value": value*(1+portfolio_price)}


def index_put_insurance(value, initial_index, beta, rate, maturity, index_yield, portfolio_yield, floor, *, multiplier=100, include_dividends=False):
    """Fractional put count/strike for the stated CAPM scenario floor.

    This is a design under a conditional linear relation, not a guarantee
    from beta alone. Premium and portfolio residuals belong to the cash ledger.
    """
    capm_portfolio_scenario(value, initial_index, initial_index, beta, rate, maturity, index_yield, portfolio_yield)
    if not all(math.isfinite(x) for x in (floor, multiplier)) or floor < 0 or multiplier <= 0 or beta <= 0:
        raise ValueError("positive put exposure/multiplier and nonnegative floor required")
    offset = (1-beta)*rate*maturity+beta*index_yield*maturity
    if not include_dividends:
        offset -= portfolio_yield*maturity
    strike = initial_index*(1+(floor/value-1-offset)/beta)
    if strike < 0:
        raise ValueError("requested floor leads to a negative put strike")
    return {"contracts": beta*value/(multiplier*initial_index), "strike": strike}


def insurance_cash_value(portfolio_terminal, index_terminal, strike, contracts, *, multiplier=100, cash_income=0, terminal_cost=0):
    """Actual portfolio plus put, income and terminal-value cost, in currency."""
    if not all(math.isfinite(x) for x in (portfolio_terminal, cash_income, terminal_cost)):
        raise ValueError("finite portfolio, income and terminal cost required")
    payoff = float(option_cashflows(index_terminal, strike, 0, kind="put", quantity=contracts, multiplier=multiplier)["payoff"])
    return {"portfolio": portfolio_terminal, "put_payoff": payoff, "total": portfolio_terminal+payoff+cash_income-terminal_cost}


def currency_option_cash(terminal_rate, strike, foreign_notional, *, kind="call"):
    """Domestic cash payoff; rates are domestic currency per foreign unit."""
    return float(option_cashflows(terminal_rate, strike, 0, kind=kind, quantity=foreign_notional, multiplier=1)["payoff"])


def range_forward_cash(terminal_rate, lower_strike, upper_strike, foreign_notional, *, exposure="receive"):
    """Signed domestic cash: positive receipt, negative payment; no premium."""
    if not all(math.isfinite(x) for x in (terminal_rate, lower_strike, upper_strike, foreign_notional)) or min(terminal_rate, lower_strike) < 0 or upper_strike < lower_strike or foreign_notional <= 0:
        raise ValueError("nonnegative ordered rates/strikes and positive foreign notional required")
    if exposure not in ("receive", "pay"):
        raise ValueError("exposure must be receive or pay")
    sign = 1 if exposure == "receive" else -1
    conversion = sign*foreign_notional*terminal_rate
    derivatives = sign*(currency_option_cash(terminal_rate, lower_strike, foreign_notional, kind="put")-currency_option_cash(terminal_rate, upper_strike, foreign_notional))
    cash = conversion+derivatives
    return {"conversion": conversion, "derivatives": derivatives, "cash": cash,
            "effective_rate": sign*cash/foreign_notional}


def range_forward_prices(spot, lower_strike, upper_strike, domestic_rate, foreign_rate, sigma, maturity):
    """Per-foreign-unit put/call costs and receive-collar premium, Hull 17.2."""
    from .bsm import call_price, put_price

    if not all(math.isfinite(x) for x in (domestic_rate, foreign_rate, lower_strike, upper_strike)) or upper_strike < lower_strike:
        raise ValueError("finite rates and ordered strikes required")
    put = float(put_price(spot, lower_strike, domestic_rate, sigma, maturity, q=foreign_rate))
    call = float(call_price(spot, upper_strike, domestic_rate, sigma, maturity, q=foreign_rate))
    return {"put": put, "call": call, "premium": put-call}


def zero_cost_range_forward(spot, lower_strike, domestic_rate, foreign_rate, sigma, maturity):
    """Solve the unique upper strike for an ordered, diffusive zero-cost collar."""
    from scipy.optimize import brentq

    range_forward_prices(spot, lower_strike, lower_strike, domestic_rate, foreign_rate, sigma, maturity)
    if sigma <= 0 or maturity <= 0:
        raise ValueError("positive volatility/time required for a unique strike")
    forward = spot*math.exp((domestic_rate-foreign_rate)*maturity)
    if lower_strike > forward:
        raise ValueError("lower strike above forward cannot give an ordered zero-cost collar")
    if math.isclose(lower_strike, forward, rel_tol=1e-13, abs_tol=1e-14):
        # At the forward, parity gives equal call/put; tiny CDF rounding must
        # not determine the sign of a root bracket whose solution is its end.
        return {"upper_strike": lower_strike, **range_forward_prices(spot, lower_strike, lower_strike, domestic_rate, foreign_rate, sigma, maturity)}
    def residual(strike):
        return range_forward_prices(spot, lower_strike, strike, domestic_rate, foreign_rate, sigma, maturity)["premium"]
    high = max(2*spot, 2*lower_strike)
    while residual(high) < 0:
        high *= 2
    upper = brentq(residual, lower_strike, high, xtol=1e-13)
    result = range_forward_prices(spot, lower_strike, upper, domestic_rate, foreign_rate, sigma, maturity)
    return {"upper_strike": upper, **result}


def _carry_inputs(spot, strike, rate, yield_rate, maturity):
    if not all(math.isfinite(x) for x in (spot, strike, rate, yield_rate, maturity)) or spot <= 0 or strike < 0 or maturity < 0:
        raise ValueError("positive spot and nonnegative strike/time required")


def carry_option_details(spot, strike, rate, yield_rate, sigma, maturity):
    """European lognormal pricing, Hull 17.1-5; continuous deterministic carry."""
    from ._bsm_foundations import lognormal_call_moments, standard_normal_probability

    _carry_inputs(spot, strike, rate, yield_rate, maturity)
    if not math.isfinite(sigma) or sigma < 0:
        raise ValueError("nonnegative finite volatility required")
    forward = spot*math.exp((rate-yield_rate)*maturity)
    discount = math.exp(-rate*maturity)
    moments = lognormal_call_moments(forward, sigma*math.sqrt(maturity), strike)
    call = discount*moments["payoff_mean"]
    if moments["d1"] is None:
        put = discount*max(strike-forward, 0)
    else:
        # Direct lower tails avoid subtracting nearly equal ITM call/parity terms.
        put = discount*max(strike*standard_normal_probability(-moments["d2"])-forward*standard_normal_probability(-moments["d1"]), 0)
    return {"call": call, "put": put, "forward": forward, "discount": discount,
            "prepaid_spot": spot*math.exp(-yield_rate*maturity),
            "d1": moments["d1"], "d2": moments["d2"],
            "N_d1": moments["stock_weight"], "N_d2": moments["exercise_probability"]}


def carry_bounds(spot, strike, rate, yield_rate, maturity):
    """European bounds and parity; valid also for negative rates/yields."""
    _carry_inputs(spot, strike, rate, yield_rate, maturity)
    prepaid = spot*math.exp(-yield_rate*maturity)
    bond = strike*math.exp(-rate*maturity)
    return {"call_lower": max(prepaid-bond, 0), "call_upper": prepaid,
            "put_lower": max(bond-prepaid, 0), "put_upper": bond,
            "call_minus_put": prepaid-bond}


def carry_american_difference_bounds(spot, strike, rate, yield_rate, maturity):
    """Hull's American C-P interval under its nonnegative r and q assumptions."""
    _carry_inputs(spot, strike, rate, yield_rate, maturity)
    if min(rate, yield_rate) < 0:
        raise ValueError("Hull's stated American interval assumes nonnegative rate/yield")
    return spot*math.exp(-yield_rate*maturity)-strike, spot-strike*math.exp(-rate*maturity)


def carry_pde_residual(spot, rate, yield_rate, sigma, value, f_time, delta, gamma):
    """Dividend self-financing PDE; f_time means calendar-time derivative."""
    from ._bsm_foundations import bsm_pde_residual

    if not math.isfinite(yield_rate):
        raise ValueError("finite yield required")
    return bsm_pde_residual(spot, rate, sigma, value, f_time, delta, gamma)-yield_rate*spot*delta


def carry_from_option_quotes(spot, strike, rate, maturity, call, put):
    """Hull 17.8-10: forward and continuous yield from same-K/T European quotes."""
    _carry_inputs(spot, strike, rate, 0, maturity)
    if not all(math.isfinite(x) for x in (call, put)) or min(call, put) < 0 or maturity <= 0:
        raise ValueError("nonnegative option quotes and positive maturity required")
    forward = strike+(call-put)*math.exp(rate*maturity)
    if forward <= 0:
        raise ValueError("quotes imply a nonpositive lognormal forward")
    return {"forward": forward, "yield_rate": rate-math.log(forward/spot)/maturity}


def carry_implied_vol(price, spot, strike, rate, yield_rate, maturity, *, kind="call"):
    """European carry IV using Brent convergence in volatility, not price.

    Only the exact deterministic price selects sigma=0. An absolute price
    tolerance would erase the volatility in very small but positive OTM quotes.
    """
    from scipy.optimize import brentq

    from .bsm import call_price, put_price

    _carry_inputs(spot, strike, rate, yield_rate, maturity)
    if strike <= 0 or maturity <= 0 or not math.isfinite(price) or kind not in ("call", "put"):
        raise ValueError("finite price and positive strike/time required to identify IV")
    pricing = call_price if kind == "call" else put_price
    lower = float(pricing(spot, strike, rate, 0, maturity, q=yield_rate))
    upper = carry_bounds(spot, strike, rate, yield_rate, maturity)[kind+"_upper"]
    if price < lower or price >= upper:
        raise ValueError("price outside finite-IV arbitrage bounds")
    if price == lower:
        return 0.0
    def objective(sigma):
        return float(pricing(spot, strike, rate, sigma, maturity, q=yield_rate))-price
    high = .5
    while objective(high) < 0:
        high *= 2
    return brentq(objective, 0, high, xtol=1e-12)


def currency_inversion(spot, strike, domestic_rate, foreign_rate, sigma, maturity, *, kind="call"):
    """European reciprocal quote with swapped rates and opposite option.

    Per one original foreign unit, the inverse option notional is K domestic
    units. Its foreign-currency price is converted at today's S, giving S*K.
    This uses the foreign numeraire, not an inverted path under the old measure.
    """
    _carry_inputs(spot, strike, domestic_rate, foreign_rate, maturity)
    if strike <= 0 or kind not in ("call", "put"):
        raise ValueError("positive reciprocal strike and call/put kind required")
    opposite = "put" if kind == "call" else "call"
    inverse = carry_option_details(1/spot, 1/strike, foreign_rate, domestic_rate, sigma, maturity)
    unit_value = inverse[opposite]
    return {"inverse_spot": 1/spot, "inverse_strike": 1/strike,
            "inverse_kind": opposite, "inverse_notional": strike,
            "foreign_unit_value": unit_value, "domestic_value": spot*strike*unit_value}


def _strictly_better(intrinsic, continuation):
    """Immediate exercise beats continuation by more than rounding error."""
    return intrinsic > continuation+16*sys.float_info.epsilon*max(1.0, abs(intrinsic), abs(continuation))


def carry_exercise_comparison(spot, strike, rate, yield_rate, sigma, maturity, steps=500, *, kind="call"):
    """European/American carry prices and strict root exercise on a CRR grid.

    Zero volatility uses the same exercise dates on a deterministic path.
    Returned premium compares two identical trees, avoiding analytic/tree error.
    """
    from .trees import binomial_tree, crr_params, risk_neutral_p

    analytic = carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)
    if steps < 1 or int(steps) != steps or kind not in ("call", "put"):
        raise ValueError("positive integer steps and call/put kind required")
    steps = int(steps)
    sign = 1 if kind == "call" else -1
    intrinsic = max(sign*(spot-strike), 0)
    dt = maturity/steps
    growth = math.exp((rate-yield_rate)*dt)
    if maturity == 0 or sigma == 0:
        cash = [math.exp(-rate*j*dt)*max(sign*(spot*math.exp((rate-yield_rate)*j*dt)-strike), 0) for j in range(steps+1)]
        american = max(cash)
        continuation = max(cash[1:])
        return {"american": american, "european": analytic[kind], "european_tree_value": cash[-1],
                "early_exercise_premium": american-cash[-1],
                "exercise_now": maturity > 0 and _strictly_better(intrinsic, continuation),
                "root_continuation": continuation, "growth": growth, "probability": None,
                "underlying_tree": None, "american_tree": None, "european_tree": None}
    up, down = crr_params(sigma, dt)
    probability = risk_neutral_p(up, down, rate, dt, q=yield_rate)
    stock, american_tree = binomial_tree(spot, strike, rate, maturity, steps, up, down, q=yield_rate, kind=kind, american=True)
    _, european_tree = binomial_tree(spot, strike, rate, maturity, steps, up, down, q=yield_rate, kind=kind)
    american, european = float(american_tree[0][0]), float(european_tree[0][0])
    continuation = math.exp(-rate*dt)*float(probability*american_tree[1][0]+(1-probability)*american_tree[1][1])
    return {"american": american, "european": analytic[kind], "european_tree_value": european,
            "early_exercise_premium": max(american-european, 0),
            "exercise_now": _strictly_better(intrinsic, continuation),
            "root_continuation": continuation, "growth": growth, "probability": probability,
            "underlying_tree": stock, "american_tree": american_tree, "european_tree": european_tree}
