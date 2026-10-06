"""Private Hull GE Ch17: index insurance, currency cashflows and carry pricing."""

import math

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
