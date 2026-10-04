"""Private Hull §34.6 conditional swap cashflows; no historical valuation.

Commodity quantity/unit price, rate-dependent amortization and P&G quoted
payoff arithmetic. CMT rates are decimal; Treasury prices are cash per par100.
Borrower/amortization behavior is caller-supplied, not empirically inferred.
Asset/CDS/variance pricing remains in the corresponding chapter modules.
"""

import numpy as np


def commodity_fixed_unit_price(fixed_payment, quantity):
    """Currency per unit (e.g. USD/bbl), not annual total payment."""
    cash, q = np.broadcast_arrays(
        np.asarray(fixed_payment, dtype=float), np.asarray(quantity, dtype=float)
    )
    if np.any(q <= 0):
        raise ValueError("positive contracted commodity quantity required")
    return cash / q


def commodity_swap_cashflows(quantities, realized_unit_prices, fixed_unit_prices):
    """Receive floating commodity value/pay fixed; amounts in payment currency."""
    q, p, k = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (quantities, realized_unit_prices, fixed_unit_prices)]
    )
    if np.any(q < 0):
        raise ValueError("nonnegative commodity quantities required")
    return q * (p - k)


def pg_spread(cmt5_decimal, treasury_cash_price_per_100):
    """BT/P&G max(0,[98.5*(CMT5/5.78%)-TreasuryPrice]/100)."""
    c, p = np.broadcast_arrays(
        np.asarray(cmt5_decimal, dtype=float), np.asarray(treasury_cash_price_per_100, dtype=float)
    )
    return np.maximum((98.5 * (c / 0.0578) - p) / 100, 0.0)


def pg_payment_rate(mean_cp30_decimal, spread):
    """P&G pays mean 30-day CP minus 75bp plus the structured spread."""
    return np.asarray(mean_cp30_decimal) - 0.0075 + np.asarray(spread)


def pg_swap_coupons(notional, accruals, mean_cp30, cmt5, treasury_price, *, first_spread_zero=True):
    """Known/scenario coupons, P&G receives 5.30% and pays structured CP leg.

    Source uses N200M, ten semiannual periods, first spread0 and remaining9
    observed spreads. No original indicator histories/market price supplied.
    mean_cp30 is a declared period average, not an invented fixing series.
    """
    a, cp, cmt, p = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (accruals, mean_cp30, cmt5, treasury_price)]
    )
    if notional <= 0 or a.ndim != 1 or not a.size or np.any(a <= 0):
        raise ValueError("positive notional/accrual vector required")
    spread = pg_spread(cmt, p)
    if first_spread_zero:
        spread[0] = 0.0
    paid = pg_payment_rate(cp, spread)
    return dict(
        spread=spread,
        pg_paid_rate=paid,
        pg_net_cash=notional * a * (0.053 - paid),
        bt_fixed_cash=notional * a * 0.053,
    )


def index_amortizing_notionals(initial_notional, observed_rate_paths, amortization_rule):
    """State-dependent amortization fraction from known history, never future.

    Rule(i,current_balance,rate_history_through_i) gives a fraction in [0,1].
    Output includes initial balance and post-observation balances. Contract
    decides when each resulting notional applies to a coupon/reset.
    """
    r = np.asarray(observed_rate_paths, dtype=float)
    if r.ndim != 2 or initial_notional <= 0:
        raise ValueError("positive initial notional/rate path matrix required")
    values = np.empty((r.shape[0], r.shape[1] + 1))
    values[:, 0] = initial_notional
    for i in range(r.shape[1]):
        fraction = np.asarray(
            amortization_rule(i, values[:, i].copy(), r[:, : i + 1].copy()), dtype=float
        )
        if np.any(fraction < 0) or np.any(fraction > 1) or not np.all(np.isfinite(fraction)):
            raise ValueError("amortization fraction must lie in [0,1]")
        values[:, i + 1] = values[:, i] * (1 - fraction)
    return values


def asset_total_return_cash(notional, start_price, end_price, cash_income):
    """Known one-period asset capital gain plus cash income on fixed units.

    This differs from a reinvested total-return index; do not add income again
    when start/end prices already refer to that index. Credit-event/default
    settlement, funding, timing and PV are separate contract inputs.
    """
    if notional < 0 or start_price <= 0:
        raise ValueError("nonnegative notional/positive initial asset price required")
    return notional * (end_price + cash_income - start_price) / start_price
