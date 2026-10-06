"""Private Hull GE Ch19: Greek units, hedge cash replay and scenarios."""

import math

import numpy as np


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


def written_call_terminal(initial, terminal, strike, quantity, sale_cash, *, covered=False):
    """Terminal option payment and unfinanced stock gain, Hull 19.2 examples."""
    if (
        not all(math.isfinite(x) for x in (initial, terminal, strike, quantity, sale_cash))
        or min(initial, quantity) <= 0
        or min(terminal, strike, sale_cash) < 0
    ):
        raise ValueError(
            "positive initial/quantity and nonnegative terminal/strike/receipt required"
        )
    option_cash = quantity * max(terminal - strike, 0)
    stock_gain = quantity * (terminal - initial) if covered else 0
    return {
        "option_cash": option_cash,
        "stock_gain": stock_gain,
        "profit": sale_cash + stock_gain - option_cash,
    }


def _path_matrix(paths):
    values = np.atleast_2d(np.asarray(paths, dtype=float))
    if (
        values.ndim != 2
        or values.shape[1] < 2
        or values.shape[0] == 0
        or np.any(~np.isfinite(values))
        or np.any(values <= 0)
    ):
        raise ValueError("finite positive equity paths with at least one interval required")
    return values


def stop_loss_holdings(paths, strike):
    """Hold one share strictly above K at each pre-expiry grid observation."""
    prices = _path_matrix(paths)
    if not math.isfinite(strike) or strike < 0:
        raise ValueError("nonnegative finite strike required")
    return (prices[:, :-1] > strike).astype(float)


def hedge_cash_replay(paths, times, strike, rate, holdings, *, kind="call", quantity=1):
    """No-dividend hedge cash recurrence on caller-supplied paths and targets.

    Targets may cover pre-expiry times or the full grid. Grid trades are made
    after interest accrues. Close the final shares and pay the written option;
    no_interest_cost excludes both interest and discount as in Tables19.1/4.
    Returned debt_after_trade is before final liquidation/option settlement.
    """
    prices = _path_matrix(paths)
    times = np.asarray(times, dtype=float)
    target = np.atleast_2d(np.asarray(holdings, dtype=float))
    rows, columns = prices.shape
    if (
        times.shape != (columns,)
        or np.any(~np.isfinite(times))
        or times[0] != 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("increasing grid starting at zero and matching prices required")
    if (
        not all(math.isfinite(x) for x in (strike, rate, quantity))
        or strike < 0
        or quantity <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError("finite rate, nonnegative strike and positive quantity required")
    if target.shape not in ((rows, columns - 1), (rows, columns)) or np.any(~np.isfinite(target)):
        raise ValueError("holdings must match path rows and pre-expiry or full grid")
    if target.shape[1] == columns - 1:
        target = np.column_stack((target, target[:, -1]))
    trades = np.diff(np.column_stack((np.zeros(rows), target)), axis=1)
    trade_cash = quantity * trades * prices
    debt = np.zeros_like(prices)
    interest = np.zeros_like(prices)
    debt[:, 0] = trade_cash[:, 0]
    for i, dt in enumerate(np.diff(times), start=1):
        interest[:, i] = debt[:, i - 1] * math.expm1(rate * dt)
        debt[:, i] = debt[:, i - 1] + interest[:, i] + trade_cash[:, i]
    sign = 1 if kind == "call" else -1
    payoff = quantity * np.maximum(sign * (prices[:, -1] - strike), 0)
    close = -quantity * target[:, -1] * prices[:, -1]
    terminal = debt[:, -1] + close + payoff
    return {
        "trade_cash": trade_cash,
        "interest_cash": interest,
        "debt_after_trade": debt,
        "close_cash": close,
        "option_cash": payoff,
        "terminal_cost": terminal,
        "present_cost": terminal * math.exp(-rate * times[-1]),
        "no_interest_cost": trade_cash.sum(axis=1) + close + payoff,
    }
