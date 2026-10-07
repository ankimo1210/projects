"""Private Hull §34.2 coupon/compound rates and one-payment swap balances.

Forward-realized inputs describe an approximation in general. Under the
single-curve floating-bank setup zero compound spread and deterministic
multiplicative compound spread admit exact PV telescoping; arbitrary
additive spread, basis, coupon conventions or exercise can break it.
"""

import numpy as np


def compound_growth(reference_rates, accruals, *, spread=0.0, mode="additive"):
    """Compound spread affects unpaid balance; it is not the coupon spread."""
    r, a = np.broadcast_arrays(
        np.asarray(reference_rates, dtype=float), np.asarray(accruals, dtype=float)
    )
    if np.any(a <= 0) or mode not in ("additive", "multiplicative"):
        raise ValueError("positive accruals and additive/multiplicative spread mode required")
    growth = 1 + (r + spread) * a if mode == "additive" else (1 + r * a) * (1 + spread * a)
    if np.any(1 + r * a <= 0) or np.any(growth <= 0):
        raise ValueError("positive reference and compound accumulation factors required")
    return growth


def compound_balances(coupon_cash, growth_factors, *, initial_balance=0.0):
    """B_i=B_(i-1)*growth_i+coupon_i, coupon added at period end.

    Last axis is time; other axes can be rate paths. Positive or negative
    balances/coupons are allowed, but growth must stay positive.
    """
    cash, g = np.broadcast_arrays(
        np.asarray(coupon_cash, dtype=float), np.asarray(growth_factors, dtype=float)
    )
    if cash.ndim < 1 or not cash.shape[-1] or np.any(g <= 0):
        raise ValueError("nonempty period cashflows and positive growth factors required")
    values = np.empty((*cash.shape[:-1], cash.shape[-1] + 1))
    values[..., 0] = initial_balance
    for i in range(cash.shape[-1]):
        values[..., i + 1] = values[..., i] * g[..., i] + cash[..., i]
    return values


def forward_realized_leg(
    coupon_rates,
    compound_rates,
    accruals,
    notionals,
    final_discount,
    *,
    compound_spread=0.0,
    spread_mode="additive",
    initial_balance=0.0,
):
    """Declared rate scenarios accumulated to one terminal payment.

    coupon_rates already include any coupon spread. compound_rates plus
    compound_spread determine only reinvestment of earlier unpaid coupons.
    Initial unpaid balance is separate from principal exchanged elsewhere.
    """
    c, r, a, n = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (coupon_rates, compound_rates, accruals, notionals)]
    )
    if final_discount <= 0 or np.any(n < 0):
        raise ValueError("positive discount/nonnegative notionals required")
    growth = compound_growth(r, a, spread=compound_spread, mode=spread_mode)
    cash = c * a * n
    balances = compound_balances(cash, growth, initial_balance=initial_balance)
    final = balances[..., -1]
    return dict(
        coupon_cash=cash,
        growth_factors=growth,
        balances=balances,
        terminal_cash=final,
        pv=final_discount * final,
        method="forward-realized scenario",
    )
