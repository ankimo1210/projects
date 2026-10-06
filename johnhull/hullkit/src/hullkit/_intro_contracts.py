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


def option_contract_cashflows(
    terminal_spot, strike, premium, *, kind="call", side="long", contracts=1, multiplier=100
):
    """Signed terminal payoff and profit after entry premium, without interest/fees.

    premium is cash per underlying unit; quantity=contracts*multiplier. Contract
    fractions are allowed for mathematical portfolios; no lot-size rounding.
    """
    from .payoffs import leg_payoff

    spot = np.asarray(terminal_spot, dtype=float)
    if (
        not np.isfinite([strike, premium, contracts, multiplier]).all()
        or min(premium, contracts) < 0
        or multiplier <= 0
        or not np.isfinite(spot).all()
        or kind not in ("call", "put")
        or side not in ("long", "short")
    ):
        raise ValueError(
            "finite prices, nonnegative premium/contracts, positive multiplier and supported kind/side required"
        )
    direction = 1 if side == "long" else -1
    quantity = contracts * multiplier
    payoff = leg_payoff(spot, direction * quantity, kind, strike)
    premium_cash = -direction * quantity * premium
    return {
        "quantity": quantity,
        "premium_cash": premium_cash,
        "payoff": payoff,
        "profit": payoff + premium_cash,
    }


def fx_forward_hedge(amount, forward_quote, terminal_spot, *, obligation="pay"):
    """Foreign cash obligation plus hedge settlement, all in domestic cash currency.

    Quotes are domestic currency per foreign unit; caller chooses ask for paying
    and bid for receiving. This fixes cash amount, not a current contract valuation.
    """
    if obligation not in ("pay", "receive"):
        raise ValueError("obligation must be pay or receive")
    spot = np.asarray(terminal_spot, dtype=float)
    sign = -1 if obligation == "pay" else 1
    hedge = forward_cashflows(amount, forward_quote, spot, side="long" if sign == -1 else "short")
    cash = sign * amount * spot
    return {
        "unhedged_cash": cash,
        "hedge_payoff": hedge["payoff"],
        "net_cash": cash + hedge["payoff"],
    }


def protected_holding(units, terminal_spot, strike, premium, *, multiplier=100):
    """Stock plus covering puts: terminal holding value and value after insurance premium.

    Neither field deducts the original stock purchase price; neither is profit
    since purchase. Units can imply fractional contracts for mathematical portfolios.
    """
    if not np.isfinite([units, multiplier]).all() or units < 0 or multiplier <= 0:
        raise ValueError("nonnegative units and positive contract multiplier required")
    puts = option_contract_cashflows(
        terminal_spot,
        strike,
        premium,
        kind="put",
        contracts=units / multiplier,
        multiplier=multiplier,
    )
    value = units * np.asarray(terminal_spot, dtype=float) + puts["payoff"]
    return {
        "contracts": units / multiplier,
        "premium_per_contract": multiplier * premium,
        "premium_cost": -puts["premium_cash"],
        "terminal_value": value,
        "value_after_premium": value + puts["premium_cash"],
    }
