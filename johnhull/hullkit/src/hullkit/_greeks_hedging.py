"""Private Hull GE Ch19: Greek units, hedge cash replay and scenarios."""

import math


def sold_option_valuation(
    spot, strike, rate, sigma, maturity, quantity, sale_cash, *, yield_rate=0, kind="call"
):
    """Time-zero European value vs total sale receipt, not guaranteed future P&L."""
    from ._index_currency import carry_option_details

    if (
        not all(math.isfinite(x) for x in (quantity, sale_cash))
        or quantity <= 0
        or sale_cash < 0
        or kind not in ("call", "put")
    ):
        raise ValueError("positive underlying units and nonnegative total sale cash required")
    unit = carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)[kind]
    return {
        "unit_value": unit,
        "theoretical_value": quantity * unit,
        "sale_cash": sale_cash,
        "sale_difference": sale_cash - quantity * unit,
    }
