"""Private Hull GE Ch16: equity awards and employee-option stopping rules."""

import math


def equity_award_payoffs(terminal_stock, grant_spot, grant_strike, terminal_index, grant_index):
    """One RSU/MSU and an index-linked option, without caps or averaging."""
    if not all(math.isfinite(x) for x in (terminal_stock, grant_spot, grant_strike, terminal_index, grant_index)) or min(terminal_stock, grant_strike, terminal_index) < 0 or min(grant_spot, grant_index) <= 0:
        raise ValueError("positive grant stock/index and nonnegative terminal values/strike required")
    indexed_strike = grant_strike*terminal_index/grant_index
    shares = terminal_stock/grant_spot
    return {"rsu_value": terminal_stock, "msu_shares": shares, "msu_value": shares*terminal_stock, "indexed_strike": indexed_strike, "indexed_option_payoff": max(terminal_stock-indexed_strike, 0)}
