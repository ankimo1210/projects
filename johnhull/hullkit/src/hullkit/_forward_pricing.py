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


def forward_value(forward_price, delivery_price, rate, remaining, *, side="long", units=1):
    """Existing forward contract PV with fixed delivery price and current forward quote.

    The input forward_price already includes any income/storage/currency carry;
    neither it nor a terminal payoff is the current contract value by itself.
    """
    if (
        not np.isfinite([forward_price, delivery_price, rate, remaining, units]).all()
        or min(remaining, units) < 0
        or side not in ("long", "short")
    ):
        raise ValueError("finite quotes/rate and nonnegative remaining time/units required")
    return (
        (1 if side == "long" else -1)
        * units
        * (forward_price - delivery_price)
        * np.exp(-rate * remaining)
    )


def offset_forward_cash(units, contract_size, entry_price, offset_price):
    """Opposite forwards lock terminal nominal cash; no missing discount rate is guessed."""
    if (
        not np.isfinite([units, contract_size, entry_price, offset_price]).all()
        or units < 0
        or contract_size <= 0
    ):
        raise ValueError("finite quotes and valid unit/contract amounts required")
    return {
        "contracts": units / contract_size,
        "locked_terminal_cash": units * (offset_price - entry_price),
    }


def index_delivery_replication(index_spot, rate, dividend_yield, maturity, *, multiplier=1):
    """Initial reinvested index units and funding for one futures delivery basket."""
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("positive multiplier required")
    forward = known_yield_forward(index_spot, rate, dividend_yield, maturity)
    initial = multiplier * np.exp(-dividend_yield * maturity)
    return {
        "forward": forward,
        "initial_units": initial,
        "delivery_units": multiplier,
        "funding_terminal": multiplier * forward,
    }


def converted_index_value(index_value, multiplier, fx_quote):
    """Basket value converted at observed FX; this is not a fixed-FX quanto price."""
    if not np.isfinite([index_value, multiplier, fx_quote]).all() or min(multiplier, fx_quote) <= 0:
        raise ValueError("finite index and positive multiplier/FX quote required")
    return multiplier * index_value * fx_quote


def currency_carry_cash(
    spot,
    domestic_rate,
    foreign_rate,
    maturity,
    delivery_quote,
    *,
    foreign_principal=1000,
    domestic_principal=1000,
):
    """Covered FX cash in both financing directions, quote domestic per foreign unit.

    All rates are continuous. Cheap/rich labels denote candidate trade directions,
    and profits can be negative when that direction is not an arbitrage opportunity.
    """
    if (
        not np.isfinite(
            [
                spot,
                domestic_rate,
                foreign_rate,
                maturity,
                delivery_quote,
                foreign_principal,
                domestic_principal,
            ]
        ).all()
        or min(spot, delivery_quote) <= 0
        or min(maturity, foreign_principal, domestic_principal) < 0
    ):
        raise ValueError("positive FX quotes and valid time/principal required")
    gd = np.exp(domestic_rate * maturity)
    gf = np.exp(foreign_rate * maturity)
    foreign_debt = foreign_principal * gf
    domestic_asset = foreign_principal * spot * gd
    foreign_bought = domestic_principal / spot
    foreign_asset = foreign_bought * gf
    domestic_debt = domestic_principal * gd
    return {
        "fair_forward": spot * gd / gf,
        "foreign_repayment": foreign_debt,
        "domestic_investment": domestic_asset,
        "cheap_forward_cost": foreign_debt * delivery_quote,
        "cheap_profit": domestic_asset - foreign_debt * delivery_quote,
        "foreign_bought": foreign_bought,
        "foreign_investment": foreign_asset,
        "domestic_repayment": domestic_debt,
        "rich_forward_receipt": foreign_asset * delivery_quote,
        "rich_profit": foreign_asset * delivery_quote - domestic_debt,
    }


def forward_rate_differential(front_quote, back_quote, maturity_gap):
    """Continuous funding-rate difference inferred from two covered-FX forward quotes."""
    if (
        not np.isfinite([front_quote, back_quote, maturity_gap]).all()
        or min(front_quote, back_quote, maturity_gap) <= 0
    ):
        raise ValueError("positive quotes and maturity gap required")
    return np.log(back_quote / front_quote) / maturity_gap


def storage_forward(
    spot, storage_dates, storage_cash, storage_zeros, rate, maturity, *, consumption=False
):
    """Known-storage investment forward equality or consumption cash-and-carry upper bound.

    Storage is cash cost, not a proportional yield. Consumption inventories can
    have nontraded convenience benefits, so the bound is not their unique price.
    """
    cash = np.asarray(storage_cash, dtype=float)
    if np.any(cash < 0):
        raise ValueError("nonnegative storage cash required")
    a = known_income_forward(spot, storage_dates, -cash, storage_zeros, rate, maturity)
    return {
        "storage_pv": -a["income_pv"],
        "carry_forward": a["forward"],
        "relation": "upper_bound" if consumption else "equality",
    }


def implied_convenience_yield(spot, forward_quote, rate, storage_yield, maturity):
    """Implied continuous convenience yield under a stated proportional storage cost."""
    if (
        not np.isfinite([spot, forward_quote, rate, storage_yield, maturity]).all()
        or min(spot, forward_quote, maturity) <= 0
    ):
        raise ValueError("positive spot/forward/time required")
    return rate + storage_yield - np.log(forward_quote / spot) / maturity


def cost_of_carry(spot, rate, maturity, *, income_yield=0, storage_yield=0, convenience_yield=0):
    """Conditional continuous carry formula; convenience yield is subtracted once.

    carry=r+storage-income excludes convenience. With a consumption asset this
    uses supplied convenience yield; setting it to zero gives the carry bound.
    """
    if not np.isfinite([income_yield, storage_yield, convenience_yield]).all():
        raise ValueError("finite proportional yield inputs required")
    carry = rate + storage_yield - income_yield
    return {"carry": carry, "forward": no_income_forward(spot, carry - convenience_yield, maturity)}


def expected_spot_forward(expected_spot, rate, required_return, maturity):
    """Nominal forward implied by a physical expectation and stated required return.

    This illustrative discounted-return relation neglects daily settlement and
    does not identify physical expectations or risk premia from quotes alone.
    """
    if not np.isfinite(required_return):
        raise ValueError("finite required return required")
    return no_income_forward(expected_spot, rate - required_return, maturity)
