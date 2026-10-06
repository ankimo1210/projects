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
