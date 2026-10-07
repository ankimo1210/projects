"""Private Hull §34.1 dated nonstandard swap legs, explicit calendar/curves.

Source U.S. calendar does not identify a concrete holiday set. A caller must
supply a calendar; date tests with weekend/holiday examples are synthetic.
Projection, discount, observation and principal exchange are separate inputs.
"""

import calendar as month_calendar
from datetime import date, timedelta
from itertools import pairwise

import numpy as np

from .rfr import compounded_rfr


def _following(day, calendar):
    while not calendar.is_business_day(day):
        day += timedelta(days=1)
    return day


def leg_schedule(start, end, months, day_count_basis, *, calendar, adjust=True, payment_lag=0):
    """Anchored month schedule, end stub, Following on all accrual dates.

    Day-of-month is anchored to the original start, retaining month end for
    an end-of-month start. payment_lag is in supplied-calendar business days.
    adjust=False preserves raw source dates and uses no holiday inference.
    """
    if end <= start or months < 1 or day_count_basis <= 0 or payment_lag < 0:
        raise ValueError("ordered dates, positive months/basis and nonnegative lag required")
    calendar.validate()
    raw = [start]
    count = 1
    eom = start.day == month_calendar.monthrange(start.year, start.month)[1]
    while raw[-1] < end:
        total = start.year * 12 + start.month - 1 + count * months
        year, month = divmod(total, 12)
        month += 1
        last = month_calendar.monthrange(year, month)[1]
        d = date(year, month, last if eom else min(start.day, last))
        raw.append(min(d, end))
        count += 1
    adjusted = [_following(d, calendar) if adjust else d for d in raw]
    if any(b <= a for a, b in pairwise(adjusted)):
        raise ValueError("date adjustment collapsed an accrual interval")
    return [
        dict(
            unadjusted_start=raw[i],
            unadjusted_end=raw[i + 1],
            accrual_start=adjusted[i],
            accrual_end=adjusted[i + 1],
            payment_date=calendar.shift(adjusted[i + 1], payment_lag)
            if payment_lag
            else adjusted[i + 1],
            accrual=(adjusted[i + 1] - adjusted[i]).days / day_count_basis,
        )
        for i in range(len(raw) - 1)
    ]


def _amounts(schedule, notionals):
    n = np.broadcast_to(np.asarray(notionals, dtype=float), (len(schedule),))
    if not schedule or np.any(n < 0):
        raise ValueError("nonempty schedule and nonnegative notionals required")
    return n


def _value(
    schedule, cash, discount_curve, valuation_date, notionals, initial_exchange, final_exchange
):
    dates = []
    values = []
    for row, c in zip(schedule, cash, strict=True):
        if valuation_date is None or row["payment_date"] > valuation_date:
            dates.append(row["payment_date"])
            values.append(float(c))
    if initial_exchange and (
        valuation_date is None or schedule[0]["accrual_start"] > valuation_date
    ):
        dates.insert(0, schedule[0]["accrual_start"])
        values.insert(0, -float(notionals[0]))
    if final_exchange and (valuation_date is None or schedule[-1]["payment_date"] > valuation_date):
        dates.append(schedule[-1]["payment_date"])
        values.append(float(notionals[-1]))
    dfs = np.array([discount_curve(d) for d in dates])
    if np.any(dfs <= 0):
        raise ValueError("positive payment discounts required")
    return dict(
        pv=float(np.asarray(values) @ dfs),
        payment_dates=tuple(dates),
        cashflows=np.array(values),
        discounts=dfs,
    )


def fixed_leg(
    schedule,
    notionals,
    coupon_rates,
    discount_curve,
    *,
    valuation_date=None,
    initial_exchange=False,
    final_exchange=False,
):
    """Scheduled notional coupons; optional initial/final principal exchange."""
    n = _amounts(schedule, notionals)
    rates = np.broadcast_to(np.asarray(coupon_rates, dtype=float), n.shape)
    cash = n * rates * np.array([r["accrual"] for r in schedule])
    return _value(
        schedule, cash, discount_curve, valuation_date, n, initial_exchange, final_exchange
    )


def projected_floating_leg(
    schedule,
    notionals,
    projection_curve,
    discount_curve,
    *,
    spread=0.0,
    known_rates=None,
    valuation_date=None,
    initial_exchange=False,
    final_exchange=False,
):
    """Single-period simple forward coupon, separate projection and OIS curve.

    A seasoned in-advance coupon needs an explicit known rate. This helper
    does not model a partly observed backward RFR coupon; supply all daily
    observed/projected fixings to compounded_rfr_leg for that contract.
    """
    n = _amounts(schedule, notionals)
    known = (
        np.full(n.shape, np.nan)
        if known_rates is None
        else np.broadcast_to(np.asarray(known_rates, dtype=float), n.shape)
    )
    cash = np.zeros(n.shape)
    for i, row in enumerate(schedule):
        if valuation_date is not None and row["payment_date"] <= valuation_date:
            continue
        if np.isfinite(known[i]):
            rate = known[i]
        elif valuation_date is not None and row["accrual_start"] < valuation_date:
            raise ValueError("seasoned in-advance coupon needs a known fixing")
        else:
            ps, pe = projection_curve(row["accrual_start"]), projection_curve(row["accrual_end"])
            if min(ps, pe) <= 0:
                raise ValueError("positive projection discounts required")
            rate = (ps / pe - 1) / row["accrual"]
        cash[i] = n[i] * (rate + spread) * row["accrual"]
    return _value(
        schedule, cash, discount_curve, valuation_date, n, initial_exchange, final_exchange
    )


def compounded_rfr_leg(
    schedule,
    notionals,
    fixings,
    discount_curve,
    *,
    calendar,
    convention,
    spread=0.0,
    valuation_date=None,
):
    """Daily factor coupon with caller-supplied observed/projected fixing source.

    Projection substitution for unknown future daily rates is a declared
    deterministic scenario, not general stochastic RFR option valuation.
    """
    n = _amounts(schedule, notionals)
    cash = np.zeros(n.shape)
    for i, row in enumerate(schedule):
        if valuation_date is not None and row["payment_date"] <= valuation_date:
            continue
        rfr = compounded_rfr(
            row["accrual_start"],
            row["accrual_end"],
            fixings,
            calendar=calendar,
            convention=convention,
        )
        cash[i] = n[i] * (rfr.accumulation_factor - 1 + spread * rfr.accrual_year_fraction)
    return _value(schedule, cash, discount_curve, valuation_date, n, False, False)
