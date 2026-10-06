"""Private Hull Ch5 forward prices versus values and explicit cash/carry assumptions."""

import numpy as np


def stock_trade_cash(units, entry, exit_price, income_per_unit, *, side="long", borrow_fee=0):
    """Stock round-trip cash including income or short-sale compensation.

    borrow_fee is total cash paid, not an annual rate. No reinvestment, funding or
    dividend timing is inferred for the introductory nominal-profit comparison.
    """
    if (
        not np.isfinite([units, entry, exit_price, income_per_unit, borrow_fee]).all()
        or min(units, borrow_fee) < 0
        or side not in ("long", "short")
    ):
        raise ValueError("finite amounts and nonnegative units/fees required")
    sign = 1 if side == "long" else -1
    initial = -sign * units * entry
    income = sign * units * income_per_unit
    final = sign * units * exit_price
    return {
        "entry_cash": initial,
        "income_cash": income,
        "exit_cash": final,
        "profit": initial + income + final - borrow_fee,
    }


def no_income_forward(spot, rate, maturity):
    """No-income/no-storage investment-asset forward price with continuous zero rate."""
    from ._rates_foundations import compound_amount

    return compound_amount(spot, rate, maturity)


def carry_cash(spot, rate, maturity, delivery_quote):
    """Nominal terminal profits of ideal cash/reverse carry with zero entry cash.

    Reverse carry assumes borrowing stock or substituting existing inventory;
    symmetric funding, no income/storage/fees and feasible simultaneous trades.
    """
    if not np.isfinite(delivery_quote):
        raise ValueError("finite delivery quote required")
    financed = no_income_forward(spot, rate, maturity)
    return {
        "fair_forward": financed,
        "entry_cash": spot - spot,
        "carry_profit": delivery_quote - financed,
        "reverse_profit": financed - delivery_quote,
    }
