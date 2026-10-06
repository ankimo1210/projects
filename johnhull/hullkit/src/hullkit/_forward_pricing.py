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


def known_income_forward(spot, income_dates, income_amounts, income_zeros, rate, maturity):
    """Known cash-income forward; each income uses its own continuous zero quote.

    Income at 0<=date<=maturity is deducted. Cash after maturity is excluded.
    Positive amounts denote received income; negative cash denotes a known cost.
    """
    dates = np.asarray(income_dates, dtype=float)
    cash = np.asarray(income_amounts, dtype=float)
    zeros = np.broadcast_to(np.asarray(income_zeros, dtype=float), dates.shape)
    if (
        dates.ndim != 1
        or dates.shape != cash.shape
        or not np.isfinite(dates).all()
        or not np.isfinite(cash).all()
        or not np.isfinite(zeros).all()
        or np.any(dates < 0)
        or not np.isfinite([spot, rate, maturity]).all()
        or min(spot, maturity) < 0
    ):
        raise ValueError(
            "aligned finite income cash/dates/rates and nonnegative spot/time required"
        )
    use = dates <= maturity
    pv = float(np.dot(cash[use], np.exp(-zeros[use] * dates[use])))
    return {
        "income_pv": pv,
        "net_spot": spot - pv,
        "forward": (spot - pv) * np.exp(rate * maturity),
    }


def known_yield_forward(spot, rate, income_yield, maturity):
    """Forward price for deterministic continuously compounded reinvested income yield."""
    if not np.isfinite(income_yield):
        raise ValueError("finite yield required")
    return no_income_forward(spot, rate - income_yield, maturity)
