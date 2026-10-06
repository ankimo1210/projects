"""Private Hull Ch2 futures quantities, margin cash and recognition conventions."""

import numpy as np


def margin_account(entry, settlements, *, units, initial, maintenance, side="long"):
    """Replay daily variation margin with calls deposited the following day.

    balance is after today's P&L and yesterday's call, before today's new call.
    No interest/withdrawals. pending_deposit is a last-day call not yet deposited.
    """
    prices = np.asarray(settlements, dtype=float)
    if (
        prices.ndim != 1
        or not np.isfinite(prices).all()
        or not np.isfinite([entry, units, initial, maintenance]).all()
        or min(units, maintenance) < 0
        or initial < maintenance
        or side not in ("long", "short")
    ):
        raise ValueError("finite one-dimensional prices and 0<=maintenance<=initial required")
    daily = (1 if side == "long" else -1) * units * np.diff(np.r_[entry, prices])
    balances = np.empty(len(daily))
    calls = np.zeros(len(daily))
    deposits = np.zeros(len(daily))
    balance = initial
    pending = 0.0
    for i, profit in enumerate(daily):
        deposits[i] = pending
        balance += pending + profit
        balances[i] = balance
        pending = initial - balance if balance < maintenance else 0.0
        calls[i] = pending
    return {
        "daily_profit": daily,
        "cumulative_profit": np.cumsum(daily),
        "balance": balances,
        "calls": calls,
        "deposits": deposits,
        "pending_deposit": pending,
    }


def net_contracts(long_contracts, short_contracts):
    """Net same-contract exposure in contracts, before exchange margin rules."""
    if (
        not np.isfinite([long_contracts, short_contracts]).all()
        or min(long_contracts, short_contracts) < 0
    ):
        raise ValueError("nonnegative contract quantities required")
    return long_contracts - short_contracts


def quote_cash_change(previous, current, *, contracts=1, multiplier=100, price_unit=1, side="long"):
    """Quote change and cash P&L; price_unit converts quoted cents to cash units.

    multiplier is underlying units per contract, not a currency conversion.
    No fees, interest or collateral flows are part of this trading P&L.
    """
    if (
        not np.isfinite([previous, current, contracts, multiplier, price_unit]).all()
        or contracts < 0
        or min(multiplier, price_unit) <= 0
        or side not in ("long", "short")
    ):
        raise ValueError("finite prices, nonnegative contracts and positive unit scales required")
    change = current - previous
    cash = (1 if side == "long" else -1) * change * price_unit * contracts * multiplier
    return {"quote_change": change, "cash_change": cash}


def recognized_futures_profit(
    quotes, *, units, price_unit=0.01, hedge_accounting=False, side="long"
):
    """Illustrative period recognition of futures profits; cash timing stays separate.

    quotes contain entry then period-end/close prices. The historical hedge example
    defers all recognition to the final period; this is not an eligibility/tax engine.
    """
    prices = np.asarray(quotes, dtype=float)
    if (
        prices.ndim != 1
        or len(prices) < 2
        or not np.isfinite(prices).all()
        or not np.isfinite([units, price_unit]).all()
        or units < 0
        or price_unit <= 0
        or side not in ("long", "short")
    ):
        raise ValueError("at least two prices and valid quantity/unit scales required")
    cash = (1 if side == "long" else -1) * units * price_unit * np.diff(prices)
    recognized = cash.copy()
    if hedge_accounting:
        recognized[:] = 0
        recognized[-1] = cash.sum()
    return {"cash_profit": cash, "recognized": recognized}
