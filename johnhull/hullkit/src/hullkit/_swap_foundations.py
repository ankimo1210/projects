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


def dealer_swap_quotes(bids, asks):
    """Dealer pays fixed at bid, receives fixed at ask; mid and spread in rate bp."""
    b = np.asarray(bids, dtype=float)
    a = np.asarray(asks, dtype=float)
    if b.shape != a.shape or not np.isfinite(b).all() or not np.isfinite(a).all() or np.any(a < b):
        raise ValueError("finite paired bid<=ask quotes required")
    return {"mid": (b + a) / 2, "spread_bp": (a - b) * 1e4}


def dated_interest(notional, annual_rate, start, end, *, basis=360):
    """Simple interest using actual calendar days on a caller-supplied annual basis."""
    from ._rate_futures import day_count

    if not np.isfinite([notional, annual_rate, basis]).all() or notional < 0 or basis <= 0:
        raise ValueError("finite rate, nonnegative notional and positive basis required")
    return notional * annual_rate * day_count(start, end) / basis


def comparative_irs(
    fixed_a, fixed_b, floating_spread_a, floating_spread_b, fixed_paid_to_a, fixed_received_from_b
):
    """Illustrative gains: A borrows fixed then pays float; B does the opposite.

    Dealer receives B's fixed and pays A's fixed. Credit-spread rollover and
    counterparty risk prevent interpreting the static gains as riskless arbitrage.
    """
    if not np.isfinite(
        [
            fixed_a,
            fixed_b,
            floating_spread_a,
            floating_spread_b,
            fixed_paid_to_a,
            fixed_received_from_b,
        ]
    ).all():
        raise ValueError("finite rate quotes required")
    aa = fixed_a - fixed_paid_to_a
    bb = floating_spread_b + fixed_received_from_b
    gap = fixed_b - fixed_a
    float_gap = floating_spread_b - floating_spread_a
    return {
        "fixed_gap": gap,
        "floating_gap": float_gap,
        "joint_gain": gap - float_gap,
        "a_effective_spread": aa,
        "b_effective_fixed": bb,
        "a_gain": floating_spread_a - aa,
        "b_gain": fixed_b - bb,
        "dealer_gain": fixed_received_from_b - fixed_paid_to_a,
    }


def ois_swap_value(
    notional, fixed_rate, pay_times, zero_rates, *, observed_rate, elapsed, receive="floating"
):
    """Seasoned single-curve OIS value using observed plus forward log-growth.

    elapsed is already observed portion of the first full accrual. Later floating
    payments telescope using the curve; fixed coupons use full period accruals.
    This is an OIS conditional forecast, not a LIBOR preset fixing assumption.
    """
    t = np.asarray(pay_times, dtype=float)
    z = np.asarray(zero_rates, dtype=float)
    if (
        t.ndim != 1
        or t.shape != z.shape
        or not len(t)
        or not np.isfinite(t).all()
        or not np.isfinite(z).all()
        or np.any(np.diff(np.r_[0, t]) <= 0)
        or not np.isfinite([notional, fixed_rate, observed_rate, elapsed]).all()
        or min(notional, elapsed) < 0
        or receive not in ("fixed", "floating")
    ):
        raise ValueError("ordered payment dates, finite rates and valid observed accrual required")
    tau = np.diff(np.r_[0, t])
    tau[0] += elapsed
    logs = np.diff(np.r_[0, z * t])
    logs[0] += observed_rate * elapsed
    continuous = logs / tau
    simple = np.expm1(logs) / tau
    cash = interest_swap_cash(notional, fixed_rate, simple, tau, receive=receive)
    df = np.exp(-t * z)
    pv = cash["net"] * df
    return {
        "continuous_rates": continuous,
        "simple_rates": simple,
        "fixed_cash": cash["fixed"],
        "floating_cash": cash["floating"],
        "net_cash": cash["net"],
        "discounts": df,
        "present_values": pv,
        "value": float(pv.sum()),
    }


def swap_roll_schedule(notional, pay_times, curve, *, fixed_rate=None, receive="fixed"):
    """PV of remaining exchanges rolled along the initial deterministic discount curve.

    Value at a payment time excludes that just-settled payment. Forward rates are
    those implied initially; this is not a claim about real stochastic expected PV.
    """
    from .rates import discount_factor
    from .swaps import swap_rate

    t = np.asarray(pay_times, dtype=float)
    if t.ndim != 1 or not len(t) or np.any(np.diff(np.r_[0, t]) <= 0):
        raise ValueError("ordered positive payment times required")
    df = np.array([discount_factor(float(time), curve) for time in t])
    tau = np.diff(np.r_[0, t])
    simple = (np.r_[1, df[:-1]] / df - 1) / tau
    fixed = swap_rate(t, curve) if fixed_rate is None else fixed_rate
    cash = interest_swap_cash(notional, fixed, simple, tau, receive=receive)["net"]
    pv = cash * df
    initial = float(pv.sum())
    rolls = np.r_[initial, (initial - np.cumsum(pv)) / df]
    return {"fixed_rate": fixed, "net_cash": cash, "initial_value": initial, "roll_values": rolls}


def currency_swap_cash(
    domestic_notional, foreign_notional, domestic_rate, foreign_rate, accruals, *, receive="foreign"
):
    """Two-currency fixed swap including inception/final principal, retaining currencies."""
    tau = np.atleast_1d(np.asarray(accruals, dtype=float))
    if (
        not np.isfinite([domestic_notional, foreign_notional, domestic_rate, foreign_rate]).all()
        or min(domestic_notional, foreign_notional) < 0
        or not len(tau)
        or not np.isfinite(tau).all()
        or np.any(tau <= 0)
        or receive not in ("domestic", "foreign")
    ):
        raise ValueError("valid notionals, accruals and receive currency required")
    sign = 1 if receive == "foreign" else -1
    domestic = np.r_[sign * domestic_notional, -sign * domestic_notional * domestic_rate * tau]
    foreign = np.r_[-sign * foreign_notional, sign * foreign_notional * foreign_rate * tau]
    domestic[-1] -= sign * domestic_notional
    foreign[-1] += sign * foreign_notional
    return {"domestic": domestic, "foreign": foreign}


def currency_comparative_cash(
    a_domestic,
    b_domestic,
    a_foreign,
    b_foreign,
    a_effective_foreign,
    b_effective_domestic,
    domestic_notional,
    foreign_notional,
):
    """Illustrative borrowing gains and unhedged dealer cash in each currency.

    Dealer domestic positive/foreign negative interest cannot be subtracted as a
    guaranteed cash profit without a supplied FX-forward curve and date schedule.
    """
    if (
        not np.isfinite(
            [
                a_domestic,
                b_domestic,
                a_foreign,
                b_foreign,
                a_effective_foreign,
                b_effective_domestic,
                domestic_notional,
                foreign_notional,
            ]
        ).all()
        or min(domestic_notional, foreign_notional) < 0
    ):
        raise ValueError("finite rates and nonnegative notionals required")
    d = b_effective_domestic - a_domestic
    f = a_effective_foreign - b_foreign
    gd = b_domestic - a_domestic
    gf = b_foreign - a_foreign
    return {
        "domestic_gap": gd,
        "foreign_gap": gf,
        "joint_gain": gd - gf,
        "a_gain": a_foreign - a_effective_foreign,
        "b_gain": b_domestic - b_effective_domestic,
        "dealer_domestic_rate": d,
        "dealer_foreign_rate": f,
        "naive_rate_difference": d + f,
        "dealer_domestic_cash": domestic_notional * d,
        "dealer_foreign_cash": foreign_notional * f,
    }


def currency_swap_value_details(
    times, domestic_cash, foreign_cash, domestic_zeros, foreign_zeros, spot, *, receive="foreign"
):
    """Same-date fixed currency legs via FX forwards, with independent bond PV fields.

    Cash inputs are positive payments/principal of each currency leg. Default
    receives foreign/pays domestic; spot is domestic cash per foreign unit.
    Exact Hull7.2/7.3 value .9627879765M rounds .9628M, not printed .9629M.
    """
    t = np.asarray(times, dtype=float)
    d = np.asarray(domestic_cash, dtype=float)
    f = np.asarray(foreign_cash, dtype=float)
    zd = np.broadcast_to(np.asarray(domestic_zeros, dtype=float), t.shape)
    zf = np.broadcast_to(np.asarray(foreign_zeros, dtype=float), t.shape)
    if (
        t.ndim != 1
        or d.shape != t.shape
        or f.shape != t.shape
        or not np.isfinite(t).all()
        or not np.isfinite(d).all()
        or not np.isfinite(f).all()
        or not np.isfinite(zd).all()
        or not np.isfinite(zf).all()
        or np.any(t < 0)
        or not np.isfinite(spot)
        or spot <= 0
        or receive not in ("domestic", "foreign")
    ):
        raise ValueError("aligned finite currency payments/rates and positive FX required")
    sign = 1 if receive == "foreign" else -1
    dd = np.exp(-zd * t)
    df = np.exp(-zf * t)
    forwards = spot * df / dd
    converted = sign * f * forwards
    net = converted - sign * d
    pv = net * dd
    return {
        "domestic_cash": -sign * d,
        "foreign_cash": sign * f,
        "fx_forwards": forwards,
        "foreign_converted": converted,
        "net_domestic_cash": net,
        "present_values": pv,
        "domestic_bond_pvs": d * dd,
        "foreign_bond_pvs": f * df,
        "value": float(pv.sum()),
    }


def currency_coupon_leg(notional, pay_times, curve, *, fixed_rate=None, first_fixing=None):
    """Positive currency bond-equivalent coupon/principal leg on reset-date accruals.

    None fixed rate means period-simple forwards. A supplied first fixing replaces
    only the first forward; inception principal is excluded from a seasoned value.
    """
    from .rates import discount_factor

    t = np.asarray(pay_times, dtype=float)
    if (
        t.ndim != 1
        or not len(t)
        or np.any(np.diff(np.r_[0, t]) <= 0)
        or not np.isfinite(notional)
        or notional < 0
    ):
        raise ValueError("ordered positive payments and nonnegative notional required")
    tau = np.diff(np.r_[0, t])
    df = np.array([discount_factor(float(time), curve) for time in t])
    rates = (
        (np.r_[1, df[:-1]] / df - 1) / tau if fixed_rate is None else np.full(len(t), fixed_rate)
    )
    if fixed_rate is None and first_fixing is not None:
        rates[0] = first_fixing
    if not np.isfinite(rates).all():
        raise ValueError("finite coupon/fixing rates required")
    cash = notional * rates * tau
    cash[-1] += notional
    return cash


def mixed_currency_value(
    pay_times,
    domestic_notional,
    foreign_notional,
    domestic_curve,
    foreign_curve,
    spot,
    *,
    dom_fixed=None,
    for_fixed=None,
    first_dom=None,
    first_for=None,
    receive="domestic",
):
    """Fixed/float currency swap valued by currency-specific forwards and discount curves.

    This reset-date single-curve-per-currency foundation has no cross-currency basis
    or inception principal. A later model may supply basis-adjusted forecasts.
    """
    from .rates import zero_interp

    t = np.asarray(pay_times, dtype=float)
    d = currency_coupon_leg(
        domestic_notional, t, domestic_curve, fixed_rate=dom_fixed, first_fixing=first_dom
    )
    f = currency_coupon_leg(
        foreign_notional, t, foreign_curve, fixed_rate=for_fixed, first_fixing=first_for
    )
    zd = np.array([zero_interp(float(time), *domestic_curve) for time in t])
    zf = np.array([zero_interp(float(time), *foreign_curve) for time in t])
    return currency_swap_value_details(t, d, f, zd, zf, spot, receive=receive)
