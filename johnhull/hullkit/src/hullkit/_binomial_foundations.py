"""Private Hull GE Ch13: replication, direct state sums and measure changes."""

import math


def one_step_replication(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity):
    """Stock and signed present bank account replicating two terminal states.

    No dividends. A negative bank balance means borrowing. This is the GE
    4% example, with no actual-world probability needed for replication.
    """
    if not all(math.isfinite(v) for v in (spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity)) or spot <= 0 or down_stock < 0 or up_stock <= down_stock or maturity < 0:
        raise ValueError("finite inputs, positive spot and distinct ordered terminal states required")
    growth = math.exp(rate*maturity)
    probability = (spot*growth-down_stock)/(up_stock-down_stock)
    if not 0 < probability < 1:
        raise ValueError("no-arbitrage requires down stock < spot growth < up stock")
    delta = (up_payoff-down_payoff)/(up_stock-down_stock)
    terminal_bank = up_payoff-delta*up_stock
    bank = terminal_bank/growth
    return dict(delta=delta, bank=bank, terminal_bank=terminal_bank,
                price=delta*spot+bank, probability=probability)


def physical_comparison(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity, *, physical_drift):
    """Contrast actual-world expectation with the replicated, drift-free price.

    The option's inferred required return is defined only when both its price
    and actual-world payoff expectation are positive. It is not the stock's
    drift or a generally reusable discount rate for other payoffs.
    """
    if maturity <= 0 or not math.isfinite(physical_drift):
        raise ValueError("positive maturity and finite physical drift required")
    replica = one_step_replication(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity)
    physical_probability = (spot*math.exp(physical_drift*maturity)-down_stock)/(up_stock-down_stock)
    if not 0 <= physical_probability <= 1:
        raise ValueError("physical drift must fit the two stock outcomes")
    expectation = physical_probability*up_payoff+(1-physical_probability)*down_payoff
    price = replica["price"]
    required = math.log(expectation/price)/maturity if expectation > 0 and price > 0 else None
    q_probability = replica["probability"]
    return dict(physical_probability=physical_probability,
                physical_payoff_expectation=expectation,
                required_discount_rate=required, risk_neutral_probability=q_probability,
                price=price, risk_free_discounted_physical_payoff=expectation*math.exp(-rate*maturity),
                q_stock_expectation=q_probability*up_stock+(1-q_probability)*down_stock,
                p_stock_expectation=physical_probability*up_stock+(1-physical_probability)*down_stock)
