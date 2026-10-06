"""Private Hull Ch3 futures hedges and explicit cash/quantity conventions."""

import numpy as np


def asset_hedge(
    terminal_spot,
    futures_entry,
    futures_exit,
    *,
    units,
    contract_size,
    price_unit=1,
    obligation="sell",
):
    """Equal-unit futures hedge of a spot purchase/sale; net_cash is signed cash.

    Both quote types share underlying units. price_unit converts cents to cash.
    effective_price is receipt per unit for selling, cost per unit for buying.
    Daily settlement interest, fees and rounding to exchange lots are excluded.
    """
    s = np.asarray(terminal_spot, dtype=float)
    f = np.asarray(futures_exit, dtype=float)
    if (
        not np.isfinite(s).all()
        or not np.isfinite(f).all()
        or not np.isfinite([futures_entry, units, contract_size, price_unit]).all()
        or units < 0
        or min(contract_size, price_unit) <= 0
        or obligation not in ("buy", "sell")
    ):
        raise ValueError("finite quotes, valid units/scales and buy/sell obligation required")
    direction = 1 if obligation == "sell" else -1
    per_unit = direction * (futures_entry - f) * price_unit
    spot_cash = direction * units * s * price_unit
    profit = units * per_unit
    return {
        "contracts": units / contract_size,
        "per_unit_profit": per_unit,
        "futures_profit": profit,
        "spot_cash": spot_cash,
        "net_cash": spot_cash + profit,
        "effective_price": (s + futures_entry - f) * price_unit,
    }
