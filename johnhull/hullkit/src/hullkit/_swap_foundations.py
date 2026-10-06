"""Private Hull Ch7 swap cash, calibration and valuation with explicit sign conventions."""

import numpy as np


def interest_swap_cash(notional, fixed_rate, reference_rates, accruals, *, receive="floating"):
    """Signed interest exchange on one notional; no principal cash is exchanged.

    Reference rates are period-simple annual quotes, already known/forecast by the
    caller. OIS compounding and LIBOR fixing timing are not inferred from this table.
    """
    rates = np.atleast_1d(np.asarray(reference_rates, dtype=float))
    tau = np.broadcast_to(np.asarray(accruals, dtype=float), rates.shape)
    if (
        not np.isfinite([notional, fixed_rate]).all()
        or not np.isfinite(rates).all()
        or not np.isfinite(tau).all()
        or notional < 0
        or np.any(tau <= 0)
        or receive not in ("fixed", "floating")
    ):
        raise ValueError("valid notional/rates/accruals and receive direction required")
    sign = 1 if receive == "floating" else -1
    floating = sign * notional * tau * rates
    fixed = -sign * notional * tau * fixed_rate
    return {"floating": floating, "fixed": fixed, "net": floating + fixed}


def swap_terminal_principal(notional, fixed_rate, reference_rates, accruals, *, receive="floating"):
    """Add offsetting hypothetical final principal to both interest legs for replication."""
    a = interest_swap_cash(notional, fixed_rate, reference_rates, accruals, receive=receive)
    sign = 1 if receive == "floating" else -1
    floating = a["floating"].copy()
    fixed = a["fixed"].copy()
    floating[-1] += sign * notional
    fixed[-1] -= sign * notional
    return {"floating": floating, "fixed": fixed, "net": floating + fixed}


def ois_bootstrap(maturities, par_rates, *, frequency=4, single_exchange_until=1):
    """Hull OIS: short single exchange, long equal-period coupons, linear continuous zeros.

    Annual OIS par rates are simple over their cash accrual periods. Long maturities
    must end on the chosen coupon grid; no holiday/day-count policy is inferred.
    """
    from ._rates_foundations import bootstrap_piecewise_zero

    t = np.asarray(maturities, dtype=float)
    q = np.asarray(par_rates, dtype=float)
    if (
        t.ndim != 1
        or t.shape != q.shape
        or not len(t)
        or not np.isfinite(t).all()
        or not np.isfinite(q).all()
        or np.any(t <= 0)
        or not np.isfinite(frequency)
        or frequency <= 0
    ):
        raise ValueError("positive maturity nodes and finite paired par rates required")
    inst = []
    for maturity, quote in zip(t, q, strict=True):
        if maturity <= single_exchange_until:
            dates = np.array([maturity])
            cash = np.array([100 * (1 + quote * maturity)])
        else:
            periods = maturity * frequency
            if not np.isclose(periods, round(periods)):
                raise ValueError("long maturity must lie on coupon grid")
            dates = np.arange(1, round(periods) + 1) / frequency
            cash = np.full(len(dates), 100 * quote / frequency)
            cash[-1] += 100
        inst.append((dates, cash, 100))
    return bootstrap_piecewise_zero(inst)


def effective_rate(legs):
    """Sum signed rate legs (floating loading, fixed spread), retaining benchmark units."""
    values = np.asarray(legs, dtype=float)
    if values.ndim != 2 or values.shape[1] != 2 or not len(values) or not np.isfinite(values).all():
        raise ValueError("finite pairs of floating loading and spread required")
    return {
        "floating_loading": float(values[:, 0].sum()),
        "fixed_spread": float(values[:, 1].sum()),
    }
