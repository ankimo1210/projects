"""Private Hull Ch6 calendar/quotation and interest-rate futures calculations."""

from datetime import date

import numpy as np


def _date(value):
    """Accept a date or ISO date string for the explicit historical examples."""
    return date.fromisoformat(value) if isinstance(value, str) else value


def day_count(start, end, *, convention="actual"):
    """Actual days or 30/360 bond-basis days, without February end-of-month adjustment.

    Bond basis caps start day at 30 and caps end day 31 only when start is 30.
    It reproduces Hull's Feb28-Mar1 three-day illustration, unlike US EOM rules.
    """
    a, b = _date(start), _date(end)
    if b < a:
        raise ValueError("ordered dates required")
    if convention == "actual":
        return (b - a).days
    if convention != "30/360-bond":
        raise ValueError("supported day-count convention required")
    d1 = min(a.day, 30)
    d2 = 30 if b.day == 31 and d1 == 30 else b.day
    return 360 * (b.year - a.year) + 30 * (b.month - a.month) + d2 - d1


def accrued_coupon(period_coupon, previous_coupon, settlement, next_coupon, *, convention="actual"):
    """Coupon-period accrued interest, act/act(in period) or named bond basis."""
    previous, now, next_date = map(_date, [previous_coupon, settlement, next_coupon])
    if not previous <= now <= next_date or next_date <= previous or not np.isfinite(period_coupon):
        raise ValueError("settlement inside a positive coupon period required")
    return (
        period_coupon
        * day_count(previous, now, convention=convention)
        / day_count(previous, next_date, convention=convention)
    )


def bill_price(discount_percent, days):
    """T-bill price per 100 face from annual discount percent on actual/360."""
    if not np.isfinite([discount_percent, days]).all() or days <= 0:
        raise ValueError("finite discount and positive days required")
    discount = discount_percent * days / 360
    price = 100 - discount
    if price <= 0:
        raise ValueError("positive bill price required")
    return {"price": price, "discount_amount": discount, "period_return": discount / price}


def bill_discount_quote(price, days):
    """Annual actual/360 discount quote in percent, distinct from investment yield."""
    if not np.isfinite([price, days]).all() or min(price, days) <= 0:
        raise ValueError("positive bill price/days required")
    return (100 - price) * 360 / days


def parse_32nds(quote):
    """Parse points-32nds with optional 2/5/7 suffix for quarter/half/three-quarter.

    A plus suffix denotes half a 32nd. Examples include 139-025 and 110-127.
    This is the printed quotation convention, not a live contract tick registry.
    """
    whole, fraction = quote.split("-")
    extra = 0.0
    if fraction.endswith("+"):
        extra = 0.5
        fraction = fraction[:-1]
    elif len(fraction) == 3:
        suffix = fraction[-1]
        fraction = fraction[:-1]
        if suffix not in "0257":
            raise ValueError("fractional 32nd suffix must be 0/2/5/7")
        extra = {"0": 0, "2": 0.25, "5": 0.5, "7": 0.75}[suffix]
    thirty_seconds = int(fraction)
    if len(fraction) != 2 or not 0 <= thirty_seconds < 32:
        raise ValueError("two digits for 0..31 thirty-seconds required")
    return int(whole) + (thirty_seconds + extra) / 32


def clean_dirty(clean_price, accrued_interest, *, face=100000):
    """Dirty price per 100 face and cash price, retaining unrounded accrued interest."""
    if not np.isfinite([clean_price, accrued_interest, face]).all() or face <= 0:
        raise ValueError("finite prices and positive face required")
    dirty = clean_price + accrued_interest
    return {"dirty_price": dirty, "cash_price": dirty * face / 100}
