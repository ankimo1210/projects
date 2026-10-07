"""Private Hull §33.3 mortgage cashflows, sequential CMO and conditional OAS.

Homogeneous fixed-coupon pool: prepayment retires proportional surviving
loans, so future scheduled payments scale with survival, not a fixed payment
on a partially prepaid single loan. Credit loss/guarantee law is excluded.
Prepayment is a supplied assumption, not fitted borrower behavior.
"""

import math

import numpy as np
from scipy.optimize import brentq


def mortgage_cashflows(
    principal, annual_coupon, monthly_rate_paths, *, prepayment=0.0, servicing_rate=0.0
):
    """SMM after scheduled principal; callback sees current/past rates only.

    Rates are annual continuous Treasury short rates, sampled per monthly
    interval; mortgage coupon is annual nominal /12. Callback signature is
    (month_index, post_scheduled_balance, history_rates). Returned SMM must
    be in [0,1]. History conditioning is distinct from an empirical model.
    """
    rates = np.asarray(monthly_rate_paths, dtype=float)
    if (
        rates.ndim != 2
        or not rates.shape[0]
        or not rates.shape[1]
        or principal <= 0
        or annual_coupon < 0
        or servicing_rate < 0
        or servicing_rate > annual_coupon
    ):
        raise ValueError(
            "monthly path matrix, positive principal and valid coupon/servicing required"
        )
    paths, months = rates.shape
    r = annual_coupon / 12
    payment = (
        principal / months if r == 0 else principal * r / (-math.expm1(-months * math.log1p(r)))
    )
    balances = np.empty((paths, months + 1))
    balances[:, 0] = principal
    interest = np.zeros_like(rates)
    scheduled = np.zeros_like(rates)
    prep = np.zeros_like(rates)
    base_balance = principal
    smm_input = (
        None
        if callable(prepayment)
        else np.broadcast_to(np.asarray(prepayment, dtype=float), rates.shape)
    )
    for i in range(months):
        begin = balances[:, i]
        interest[:, i] = begin * (annual_coupon - servicing_rate) / 12
        scheduled[:, i] = (
            begin
            if i == months - 1
            else np.minimum(begin, begin / base_balance * (payment - base_balance * r))
        )
        after = begin - scheduled[:, i]
        smm = np.asarray(
            prepayment(i, after.copy(), rates[:, : i + 1].copy())
            if callable(prepayment)
            else smm_input[:, i],
            dtype=float,
        )
        if np.any(smm < 0) or np.any(smm > 1) or not np.all(np.isfinite(smm)):
            raise ValueError("monthly prepayment probability must lie in [0,1]")
        prep[:, i] = after * smm
        balances[:, i + 1] = after - prep[:, i]
        base_balance = 0 if i == months - 1 else base_balance * (1 + r) - payment
    return dict(
        interest=interest,
        principal=scheduled + prep,
        scheduled_principal=scheduled,
        prepayment_principal=prep,
        balances=balances,
        initial_principal=principal,
        monthly_payment_per_initial_pool=payment,
        payment_times=np.arange(1, months + 1) / 12,
    )


def sequential_cmo_principal(pool_principal, initial_tranches):
    """Principal priority only; tranche interest needs separate contract rates."""
    amounts = np.asarray(pool_principal, dtype=float)
    initial = np.asarray(initial_tranches, dtype=float)
    if (
        amounts.ndim != 2
        or initial.ndim != 1
        or not initial.size
        or np.any(amounts < 0)
        or np.any(initial < 0)
        or np.any(amounts.sum(axis=1) > initial.sum() + 1e-9)
    ):
        raise ValueError("nonnegative pool principal cannot exceed tranche principal")
    paths, months = amounts.shape
    balances = np.empty((paths, months + 1, initial.size))
    balances[:, 0] = initial
    payments = np.zeros((paths, months, initial.size))
    for i in range(months):
        remain = amounts[:, i].copy()
        outstanding = balances[:, i].copy()
        for j in range(initial.size):
            paid = np.minimum(remain, outstanding[:, j])
            payments[:, i, j] = paid
            outstanding[:, j] -= paid
            remain -= paid
        balances[:, i + 1] = outstanding
    return dict(cashflows=payments, balances=balances)


def mortgage_value(cashflows, monthly_rate_paths, spread=0.0):
    """Path discount at Treasury continuous short rates plus constant OAS."""
    rates = np.asarray(monthly_rate_paths, dtype=float)
    io = np.asarray(cashflows["interest"], dtype=float)
    po = np.asarray(cashflows["principal"], dtype=float)
    if rates.shape != io.shape or rates.shape != po.shape or rates.ndim != 2 or not rates.shape[0]:
        raise ValueError("matching cashflow and monthly rate path matrices required")
    discount = np.exp(-np.cumsum(rates + spread, axis=1) / 12)
    iv = np.sum(io * discount, axis=1)
    pv = np.sum(po * discount, axis=1)
    total = iv + pv
    se = 0.0 if total.size == 1 else float(total.std(ddof=1) / math.sqrt(total.size))
    return dict(
        IO=float(iv.mean()),
        PO=float(pv.mean()),
        pass_through=float(total.mean()),
        standard_error=se,
        path_values=total,
    )


def mortgage_oas(cashflows, monthly_rate_paths, market_price):
    """Inverse price with cashflows/prepayment paths held fixed during solve.

    OAS is conditional on supplied pool, rate and repayment assumptions.
    Regenerating a different borrower model changes the inferred spread.
    """
    if market_price <= 0:
        raise ValueError("positive market price required")
    if np.sum(cashflows["interest"]) + np.sum(cashflows["principal"]) <= 0:
        raise ValueError("positive future cashflows required")

    def residual(s):
        return mortgage_value(cashflows, monthly_rate_paths, s)["pass_through"] - market_price

    lo, hi = -0.1, 0.1
    while residual(lo) < 0:
        lo *= 2
    while residual(hi) > 0:
        hi *= 2
    spread = brentq(residual, lo, hi, xtol=1e-14)
    return dict(
        spread=spread, price=mortgage_value(cashflows, monthly_rate_paths, spread)["pass_through"]
    )
