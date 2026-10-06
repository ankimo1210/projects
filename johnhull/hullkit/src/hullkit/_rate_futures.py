"""Private Hull Ch6 calendar/quotation and interest-rate futures calculations."""

from datetime import date, timedelta

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


def conversion_factor(annual_coupon, remaining_months, *, rounding_months=3):
    """Hull's 6%-semiannual conversion-factor illustration, per 100 face.

    Three-month rule floors remaining months; Note month rule uses nearest month
    (half up). Stub accrued interest is deducted from discounted coupon/principal.
    Exchange-specific eligibility/day rules beyond Hull are not inferred.
    """
    if (
        not np.isfinite([annual_coupon, remaining_months]).all()
        or annual_coupon < 0
        or remaining_months <= 0
        or rounding_months not in (1, 3)
    ):
        raise ValueError("valid coupon/maturity and Hull one/three-month rule required")
    months = (
        np.floor(remaining_months / 3) * 3
        if rounding_months == 3
        else np.floor(remaining_months + 0.5)
    )
    if months <= 0:
        raise ValueError("positive rounded maturity required")
    stub = months % 6
    first = stub / 12 if stub else 0.5
    times = np.arange(first, months / 12 + 1e-9, 0.5)
    coupon = 50 * annual_coupon
    cash = np.full(len(times), coupon)
    cash[-1] += 100
    dirty = float(np.dot(cash, 1.03 ** (-2 * times)))
    accrued = coupon * (0.5 - first) / 0.5
    clean = dirty - accrued
    return {
        "factor": clean / 100,
        "dirty_price": dirty,
        "clean_price": clean,
        "accrued": accrued,
        "first_coupon_value": dirty * 1.03 ** (2 * first),
        "rounded_months": months,
    }


def treasury_invoice(settlement_quote, factor, accrued, *, face=100000):
    """Treasury futures invoice per 100 face and total delivery cash."""
    if not np.isfinite([settlement_quote, factor, accrued, face]).all() or min(factor, face) <= 0:
        raise ValueError("finite quote/accrual and positive factor/face required")
    price = settlement_quote * factor + accrued
    return {"price": price, "cash": price * face / 100}


def cheapest_delivery(clean_prices, factors, settlement_quote):
    """Choose smallest clean-price minus futures-invoice component, ties first."""
    prices = np.asarray(clean_prices, dtype=float)
    cf = np.asarray(factors, dtype=float)
    if (
        prices.ndim != 1
        or prices.shape != cf.shape
        or not len(prices)
        or not np.isfinite(prices).all()
        or not np.isfinite(cf).all()
        or np.any(cf <= 0)
        or not np.isfinite(settlement_quote)
    ):
        raise ValueError("paired bond prices/positive factors required")
    costs = prices - settlement_quote * cf
    return {"costs": costs, "index": int(np.argmin(costs))}


def bond_futures_quote(
    clean_spot,
    coupon_cash,
    elapsed_days,
    next_coupon_days,
    delivery_days,
    delivery_elapsed_days,
    delivery_remaining_days,
    rate,
    factor,
    *,
    basis=365,
):
    """Known CTD/date bond future with one coupon before delivery, Hull Example6.2.

    Day fractions for accrued coupons and the continuous rate's year basis differ.
    Caller supplies actual interval counts; no contract delivery option is valued.
    """
    if (
        not np.isfinite(
            [
                clean_spot,
                coupon_cash,
                elapsed_days,
                next_coupon_days,
                delivery_days,
                delivery_elapsed_days,
                delivery_remaining_days,
                rate,
                factor,
                basis,
            ]
        ).all()
        or min(elapsed_days, delivery_elapsed_days) < 0
        or min(next_coupon_days, delivery_remaining_days, factor, basis) <= 0
        or delivery_days < next_coupon_days
    ):
        raise ValueError("valid coupon interval/delivery days and positive factor/basis required")
    cash_spot = clean_spot + coupon_cash * elapsed_days / (elapsed_days + next_coupon_days)
    coupon_time = next_coupon_days / basis
    delivery_time = delivery_days / basis
    pv = coupon_cash * np.exp(-rate * coupon_time)
    dirty = (cash_spot - pv) * np.exp(rate * delivery_time)
    clean = dirty - coupon_cash * delivery_elapsed_days / (
        delivery_elapsed_days + delivery_remaining_days
    )
    return {
        "cash_spot": cash_spot,
        "coupon_time": coupon_time,
        "income_pv": pv,
        "delivery_time": delivery_time,
        "cash_forward": dirty,
        "clean_forward": clean,
        "futures_quote": clean / factor,
    }


def rate_futures_quote(rate):
    """100 minus annual interest percent, with rate supplied as a decimal fraction."""
    if not np.isfinite(rate):
        raise ValueError("finite annual rate required")
    return 100 - 100 * rate


def rate_futures_cash(
    entry_quote, settlement_quote, *, notional=1e6, accrual=0.25, contracts=1, side="long"
):
    """Linear futures settlement P&L and cash per rate bp, excluding timing corrections."""
    if (
        not np.isfinite([entry_quote, settlement_quote, notional, accrual, contracts]).all()
        or min(notional, accrual) <= 0
        or contracts < 0
        or side not in ("long", "short")
    ):
        raise ValueError("finite quotes and valid notional/accrual/count required")
    bp = notional * accrual * 1e-4
    profit = (
        (1 if side == "long" else -1)
        * contracts
        * notional
        * accrual
        * (settlement_quote - entry_quote)
        / 100
    )
    return {"bp_value": bp, "profit": profit, "implied_rate": (100 - settlement_quote) / 100}


def rate_futures_borrow_hedge(
    notional, spread, accrual, entry_quote, settlement_quote, *, contracts, contract_notional=1e6
):
    """Short rate-futures borrow hedge; negative-rate case still fixes Example6.3 cost.

    Source 197000/102250/502250 are arithmetic typos; exact ledger gives
    197500/102500/502500. Daily reinvestment/convexity is outside this approximation.
    """
    a = rate_futures_cash(
        entry_quote,
        settlement_quote,
        notional=contract_notional,
        accrual=accrual,
        contracts=contracts,
        side="short",
    )
    if not np.isfinite([notional, spread]).all() or notional < 0:
        raise ValueError("nonnegative borrow amount and finite spread required")
    interest = notional * accrual * (a["implied_rate"] + spread)
    return {
        "change_bp": 100 * (entry_quote - settlement_quote),
        "futures_profit": a["profit"],
        "interest_cash": interest,
        "net_interest": interest - a["profit"],
    }


def extend_zero(start, current_zero, forward_rate, end):
    """Extend continuous zero via a forward over start..end in any consistent time unit."""
    if not np.isfinite([start, current_zero, forward_rate, end]).all() or start < 0 or end <= start:
        raise ValueError("0<=start<end and finite rates required")
    return (current_zero * start + forward_rate * (end - start)) / end


def remaining_zero(full_zero, full_period, observed_zero, observed_period):
    """Residual continuous rate after removing observed log-growth, as in Example6.5."""
    if (
        not np.isfinite([full_zero, full_period, observed_zero, observed_period]).all()
        or not 0 <= observed_period < full_period
    ):
        raise ValueError("0<=observed period<full period required")
    return (full_zero * full_period - observed_zero * observed_period) / (
        full_period - observed_period
    )


def adjust_forward_rate(futures_rate, convexity_adjustment):
    """Forward=futures-c with supplied nonnegative c; no absent model parameters guessed."""
    if not np.isfinite([futures_rate, convexity_adjustment]).all() or convexity_adjustment < 0:
        raise ValueError("finite rates and nonnegative convexity adjustment required")
    return futures_rate - convexity_adjustment


def sofr_fixing_window(start, end, fixings, *, basis=360):
    """Arithmetic/compounded rates on [start,end), carrying the latest supplied fixing.

    Caller provides business-day fixings/holidays; each carried calendar day is
    counted once. A carried fixing uses one simple factor 1+r*days/basis before
    reinvestment at the next fixing, including across weekends and holidays.
    Equal rates on distinct fixing dates still create separate factors.
    End-date observations are excluded, not charged for another day.
    """
    from ._rates_foundations import compounded_reference_rate

    start, end = _date(start), _date(end)
    observations = sorted((_date(key), float(value)) for key, value in fixings.items())
    if end <= start or not observations or observations[0][0] > start:
        raise ValueError("positive window and an opening/prior fixing required")
    daily = []
    fixing_rates, fixing_days = [], []
    index = 0
    previous_index = None
    day = start
    while day < end:
        while index + 1 < len(observations) and observations[index + 1][0] <= day:
            index += 1
        rate = observations[index][1]
        daily.append(rate)
        if index == previous_index:
            fixing_days[-1] += 1
        else:
            fixing_rates.append(rate)
            fixing_days.append(1)
            previous_index = index
        day += timedelta(days=1)
    rates = np.array(daily)
    a = compounded_reference_rate(fixing_rates, fixing_days, basis=basis)
    return {
        "daily_rates": rates,
        "growth": a["growth"],
        "compounded": a["annualized_rate"],
        "arithmetic": float(rates.mean()),
    }


def duration_futures_hedge(portfolio_value, portfolio_duration, contract_value, contract_duration):
    """Short count cancelling first-order parallel-yield risk in matching duration units.

    contract_value is quoted futures notional value, not CTD spot value. Durations
    refer to hedge maturity, and a CTD switch can require rebalancing.
    """
    if (
        not np.isfinite(
            [portfolio_value, portfolio_duration, contract_value, contract_duration]
        ).all()
        or portfolio_value < 0
        or min(contract_value, contract_duration) <= 0
    ):
        raise ValueError("valid portfolio value and positive contract risk scale required")
    count = portfolio_value * portfolio_duration / (contract_value * contract_duration)
    return {"short_contracts": count, "rounded": np.rint(count)}
