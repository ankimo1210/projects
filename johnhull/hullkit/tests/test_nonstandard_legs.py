"""Nonstandard legs: source term sheet and explicitly supplied calendars."""

import importlib
import math
from datetime import date, timedelta

import numpy as np
import pytest
from hullkit.rfr import BusinessCalendar, RFRConvention


def model():
    return importlib.import_module("hullkit._nonstandard_legs")


def test_bs34_1_source_unadjusted_contract_and_different_legs():
    m = model()
    start = date(2021, 1, 11)
    end = date(2026, 1, 11)
    cal = BusinessCalendar()
    fixed = m.leg_schedule(start, end, 6, 365, calendar=cal, adjust=False)
    floating = m.leg_schedule(start, end, 3, 360, calendar=cal, adjust=False)
    assert len(fixed) == 10 and len(floating) == 20
    assert fixed[0]["unadjusted_end"] == date(2021, 7, 11)
    assert floating[0]["unadjusted_end"] == date(2021, 4, 11)
    assert fixed[0]["accrual"] == pytest.approx(181 / 365)
    assert floating[0]["accrual"] == pytest.approx(90 / 360)

    def curve(d):
        return math.exp(-0.03 * (d - start).days / 365)

    a = m.fixed_leg(fixed, 1e8, 0.02, curve)
    b = m.projected_floating_leg(
        floating, 1.2e8, lambda d: math.exp(-0.045 * (d - start).days / 365), curve
    )
    hand_fixed = sum(1e8 * 0.02 * x["accrual"] * curve(x["payment_date"]) for x in fixed)
    hand_float = sum(
        1.2e8
        * math.expm1(0.045 * (x["accrual_end"] - x["accrual_start"]).days / 365)
        * curve(x["payment_date"])
        for x in floating
    )
    assert a["pv"] == pytest.approx(hand_fixed, abs=1e-7)
    assert b["pv"] == pytest.approx(hand_float, abs=1e-7)


def test_following_all_dates_calendar_contrast_and_anchored_month_end():
    m = model()
    start = date(2021, 1, 11)
    end = date(2026, 1, 11)
    weekend = m.leg_schedule(start, end, 3, 360, calendar=BusinessCalendar())
    holiday = m.leg_schedule(
        start, end, 3, 360, calendar=BusinessCalendar(holidays=(date(2021, 10, 11),))
    )
    assert weekend[2]["payment_date"] == date(2021, 10, 11)
    assert holiday[2]["payment_date"] == date(2021, 10, 12)
    assert holiday[3]["accrual_start"] == holiday[2]["accrual_end"]
    assert weekend[-1]["payment_date"] == date(2026, 1, 12)
    dates = m.leg_schedule(
        date(2024, 1, 31), date(2024, 4, 30), 1, 365, calendar=BusinessCalendar(), adjust=False
    )
    assert [x["unadjusted_end"] for x in dates] == [
        date(2024, 2, 29),
        date(2024, 3, 31),
        date(2024, 4, 30),
    ]


@pytest.mark.parametrize("notionals", [[100, 120, 140, 160], [100, 80, 60, 40]])
def test_scheduled_notionals_and_optional_principal_cashflows(notionals):
    m = model()
    start = date(2024, 1, 2)
    rows = m.leg_schedule(
        start, date(2025, 1, 2), 3, 365, calendar=BusinessCalendar(), adjust=False
    )

    def curve(d):
        return math.exp(-0.04 * (d - start).days / 365)

    result = m.fixed_leg(rows, notionals, 0.03, curve, initial_exchange=True, final_exchange=True)
    expected = (
        sum(
            n * 0.03 * r["accrual"] * curve(r["payment_date"])
            for n, r in zip(notionals, rows, strict=True)
        )
        - notionals[0]
        + notionals[-1] * curve(rows[-1]["payment_date"])
    )
    assert result["pv"] == pytest.approx(expected, abs=1e-12)


def test_standard_single_curve_float_telescopes_but_projection_basis_changes_value():
    m = model()
    start = date(2024, 1, 2)
    rows = m.leg_schedule(
        start, date(2026, 1, 2), 3, 360, calendar=BusinessCalendar(), adjust=False
    )

    def curve(d):
        return math.exp(-0.04 * (d - start).days / 365)

    a = m.projected_floating_leg(rows, 100, curve, curve)
    assert a["pv"] == pytest.approx(100 * (1 - curve(rows[-1]["payment_date"])), abs=1e-12)
    basis = m.projected_floating_leg(
        rows, 100, lambda d: math.exp(-0.047 * (d - start).days / 365), curve
    )
    assert basis["pv"] > a["pv"]


def test_known_daily_rfr_leg_independent_weekend_weighted_products():
    m = model()
    start = date(2024, 1, 5)
    end = date(2024, 2, 5)
    cal = BusinessCalendar()
    rows = m.leg_schedule(start, end, 1, 360, calendar=cal)

    def fixing(day):
        return 0.02 + (day - start).days * 0.0001

    row = m.compounded_rfr_leg(
        rows, 1e8, fixing, lambda d: 0.99, calendar=cal, convention=RFRConvention(), spread=0.002
    )
    product = 1.0
    day = start
    while day < end:
        next_day = day + timedelta(days=1)
        while next_day < end and next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        product *= 1 + fixing(day) * (next_day - day).days / 360
        day = next_day
    assert row["pv"] == pytest.approx(
        0.99 * 1e8 * (product - 1 + 0.002 * (end - start).days / 360), abs=1e-7
    )


def test_seasoned_fixing_and_already_settled_coupon_filter():
    m = model()
    start = date(2024, 1, 2)
    now = date(2024, 6, 1)
    rows = m.leg_schedule(
        start, date(2025, 1, 2), 3, 365, calendar=BusinessCalendar(), adjust=False
    )

    def curve(d):
        return math.exp(-0.04 * (d - now).days / 365)

    with pytest.raises(ValueError):
        m.projected_floating_leg(rows, 100, curve, curve, valuation_date=now)
    row = m.projected_floating_leg(
        rows, 100, curve, curve, valuation_date=now, known_rates=[np.nan, 0.05, np.nan, np.nan]
    )
    assert len(row["cashflows"]) == 3
    assert row["cashflows"][0] == pytest.approx(100 * 0.05 * rows[1]["accrual"])
    with pytest.raises(ValueError):
        m.leg_schedule(start, start, 3, 365, calendar=BusinessCalendar())
