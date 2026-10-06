"""Private Hull GE Ch1 introductory contracts, explicit quantities and cash units.

These are terminal cashflows/profits, not option or seasoned-forward valuations.
Historical bid/ask inputs are examples, not current market quotes.
"""

import numpy as np


def forward_cashflows(quantity, delivery_price, terminal_spot, *, side="long"):
    """Cash/asset value at maturity and net payoff; quantity in underlying units.

    Delivery/spot prices share the cash currency per underlying unit. Linear
    forward prices need not be nonnegative; the caller sets the asset domain.
    """
    spot = np.asarray(terminal_spot, dtype=float)
    if (
        not np.isfinite([quantity, delivery_price]).all()
        or quantity < 0
        or not np.isfinite(spot).all()
        or side not in ("long", "short")
    ):
        raise ValueError("finite prices, nonnegative quantity and long/short side required")
    direction = 1 if side == "long" else -1
    cash = -direction * quantity * delivery_price
    received = direction * quantity * spot
    return {"delivery_cash": cash, "asset_value": received, "payoff": received + cash}


def simple_carry_comparison(spot, delivery_price, rate, maturity, *, quantity=1):
    """Single-period simple-rate carry and relative gain versus holding the stock.

    No dividends, fees or funding asymmetry. Reverse carry presumes existing
    inventory or permitted shorting; interest is not continuously compounded.
    """
    if (
        not np.isfinite([spot, delivery_price, rate, maturity, quantity]).all()
        or min(spot, maturity, quantity) < 0
        or 1 + rate * maturity <= 0
    ):
        raise ValueError(
            "finite inputs, nonnegative spot/time/quantity and positive growth required"
        )
    future = spot * (1 + rate * maturity)
    difference = delivery_price - future
    return {
        "financed_spot": future,
        "interest": quantity * spot * rate * maturity,
        "relative_gain": quantity * abs(difference),
        "direction": "cash_and_carry" if difference >= 0 else "reverse_carry",
    }
