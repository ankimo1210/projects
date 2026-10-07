"""Private Hull §34.4 total-return swaps and TN19 intermediate replication.

Receive equity/pay funding. A standalone equity coupon PV is L*(ratio-P),
not L*(ratio-1). Funding growth inputs are conditional payment-measure
expected accumulation factors; an arbitrary projection curve alone need
not specify these in a stochastic multicurve or lagged contract.
"""

import numpy as np


def equity_rfr_period(
    notional,
    index_ratio,
    known_accumulation,
    payment_discount,
    remaining_growth,
    *,
    discounted_equity_ratio=None,
):
    """Separate equity/funding PV and net for the next reset period.

    Same-date frictionless total-return index gives discounted ratio equal
    to current index/reset index. For observation/payment lag supply the
    discounted terminal ratio explicitly from the required timing model.
    Known overnight product multiplies unknown remaining product, retaining
    the cross term. Same-curve bank growth has remaining_growth=1/P.
    """
    if min(notional, index_ratio, known_accumulation, payment_discount, remaining_growth) <= 0:
        raise ValueError("positive notional/index ratio/accumulation/discount/growth required")
    ratio = index_ratio if discounted_equity_ratio is None else discounted_equity_ratio
    equity = notional * (ratio - payment_discount)
    funding = notional * payment_discount * (known_accumulation * remaining_growth - 1)
    return dict(equity_pv=equity, funding_pv=funding, net_pv=equity - funding)


def tn19_equity_swap(
    notional,
    index_ratio,
    reset_simple_rate,
    original_accrual,
    current_simple_rate,
    remaining_accrual,
):
    """TN19 (1)/(2), simple coupon fixed at previous reset, not overnight RFR."""
    if original_accrual < 0 or remaining_accrual < 0 or remaining_accrual > original_accrual:
        raise ValueError("ordered original/remaining accrual fractions required")
    known = 1 + reset_simple_rate * original_accrual
    base = 1 + current_simple_rate * remaining_accrual
    if min(known, base) <= 0:
        raise ValueError("positive simple accrual factors required")
    return equity_rfr_period(notional, index_ratio, known, 1 / base, 1.0)


def future_reset_periods(notional, start_discounts, end_discounts, projected_growth):
    """Future par equity reset cashflows minus declared floating-growth PVs.

    Growth here is a supplied end-payment measure expectation. Each future
    equity ratio has discounted expectation P(start) under the frictionless
    same-observation/payment total-return replication. Same-curve periods
    cancel; a deterministic basis scenario need not cancel.
    """
    ps, pe, g = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (start_discounts, end_discounts, projected_growth)]
    )
    if notional <= 0 or np.any(ps <= 0) or np.any(pe <= 0) or np.any(g <= 0):
        raise ValueError("positive notional and discount/growth arrays required")
    return notional * (ps - pe * g)


def total_return_index(prices, dividends):
    """Cash dividends per old share reinvested at each supplied ex-div price."""
    p, d = np.asarray(prices, dtype=float), np.asarray(dividends, dtype=float)
    if (
        p.ndim != 1
        or not p.size
        or p.shape != d.shape
        or np.any(p <= 0)
        or np.any(d < 0)
        or d[0] != 0
    ):
        raise ValueError("positive price series and matching dividends (first zero) required")
    shares = np.ones(p.size)
    for i in range(1, p.size):
        shares[i] = shares[i - 1] * (1 + d[i] / p[i])
    return dict(indices=shares * p, shares=shares)


def equity_reset(
    notional, previous_reset_index, observation_index, realized_rfr_accumulation, *, settled
):
    """Advance reset state while preserving any observed but unpaid old cash."""
    if min(notional, previous_reset_index, observation_index, realized_rfr_accumulation) <= 0:
        raise ValueError("positive reset index/notional/funding accumulation required")
    eq = notional * (observation_index / previous_reset_index - 1)
    funding = notional * (realized_rfr_accumulation - 1)
    net = eq - funding
    return dict(
        equity_cash=eq,
        funding_cash=funding,
        net_cash=net,
        pending_net_cash=0.0 if settled else net,
        new_reset_index=observation_index,
        new_index_units=notional / observation_index,
        new_known_accumulation=1.0,
    )
