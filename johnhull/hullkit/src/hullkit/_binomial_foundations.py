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
