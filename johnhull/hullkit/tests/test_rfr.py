"""Convention, curve and scenario gates for exact RFR compounding."""

from datetime import date

import numpy as np
import pytest
from hullkit import rfr


def test_exact_daily_compounding_carries_friday_fixing_over_weekend() -> None:
    calendar = rfr.BusinessCalendar()
    start, end = date(2026, 7, 2), date(2026, 7, 7)  # Thu -> Tue
    fixings = {
        date(2026, 7, 2): 0.04,
        date(2026, 7, 3): 0.05,
        date(2026, 7, 6): 0.06,
    }
    result = rfr.compounded_rfr(start, end, fixings, calendar=calendar)
    assert [row.day_count for row in result.observations] == [1, 3, 1]
    expected = (1 + 0.04 / 360) * (1 + 0.05 * 3 / 360) * (1 + 0.06 / 360)
    assert result.accumulation_factor == pytest.approx(expected)


def test_lookback_observation_shift_and_lockout_are_distinct() -> None:
    calendar = rfr.BusinessCalendar(holidays=(date(2026, 7, 3),))
    start, end = date(2026, 7, 6), date(2026, 7, 10)
    fixing_dates = [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 6), date(2026, 7, 7)]
    fixings = {day: 0.01 * (index + 1) for index, day in enumerate(fixing_dates)}
    lookback = rfr.daily_accrual_schedule(
        start,
        end,
        fixings,
        calendar=calendar,
        convention=rfr.RFRConvention(lookback_business_days=2),
    )
    assert [row.observation_date for row in lookback] == fixing_dates
    shifted = rfr.daily_accrual_schedule(
        start,
        end,
        fixings,
        calendar=calendar,
        convention=rfr.RFRConvention(lookback_business_days=2, observation_shift=True),
    )
    assert [row.day_count for row in lookback] != [row.day_count for row in shifted]
    lockout_fixings = {date(2026, 7, 6): 0.01, date(2026, 7, 7): 0.02}
    locked = rfr.daily_accrual_schedule(
        start,
        end,
        lockout_fixings,
        calendar=calendar,
        convention=rfr.RFRConvention(lockout_business_days=2),
    )
    assert [row.observation_date for row in locked] == [
        date(2026, 7, 6),
        date(2026, 7, 7),
        date(2026, 7, 7),
        date(2026, 7, 7),
    ]


def test_zero_rate_continuous_limit_and_advance_arrears_payoffs() -> None:
    start, end = date(2026, 1, 2), date(2026, 2, 2)
    calendar = rfr.BusinessCalendar()
    dates = calendar.business_dates(start, end)
    zero = {day: 0.0 for day in dates}
    zero_result = rfr.compounded_rfr(start, end, zero)
    assert zero_result.annualized_rate == 0.0
    constant = {day: 0.05 for day in dates}
    exact = rfr.compounded_rfr(start, end, constant)
    continuous = rfr.continuous_compounding_approximation(exact.observations, 360)
    assert exact.annualized_rate == pytest.approx(continuous, rel=2e-4)

    prior_start, prior_end = date(2025, 12, 2), start
    prior_dates = calendar.business_dates(prior_start, prior_end)
    all_fixings = {**{day: 0.03 for day in prior_dates}, **{day: 0.05 for day in dates}}
    arrears = rfr.rfr_coupon(1_000_000, start, end, all_fixings, determination="in_arrears")
    advance = rfr.rfr_coupon(
        1_000_000,
        start,
        end,
        all_fixings,
        determination="in_advance",
        advance_observation_period=(prior_start, prior_end),
    )
    assert advance < arrears


def _curve(name: str, currency: str, discounts: tuple[float, float]) -> rfr.RfrCurve:
    return rfr.RfrCurve(
        name=name,
        valuation_date=date(2026, 1, 2),
        pillar_dates=(date(2026, 7, 2), date(2027, 1, 2)),
        discount_factors=discounts,
        currency=currency,
    )


def test_sofr_tona_curve_basis_convexity_policy_and_collateral_layers() -> None:
    sofr = _curve("SOFR", "USD", (0.98, 0.95))
    tona = _curve("TONA", "JPY", (0.995, 0.99))
    start, end = date(2026, 4, 2), date(2026, 10, 2)
    assert sofr.simple_forward(start, end) > tona.simple_forward(start, end)
    assert rfr.curve_basis_spread(sofr, tona, start, end) > 0.0
    futures, adjustment = rfr.futures_forward_from_covariance(0.04, -0.0002, 0.98)
    assert futures > 0.04 and adjustment > 0.0
    flat, zero_adjustment = rfr.futures_forward_from_covariance(0.04, 0.0, 0.98)
    assert flat == 0.04 and zero_adjustment == 0.0

    observations = [date(2026, 1, 20), date(2026, 1, 30), date(2026, 2, 2)]
    path = rfr.policy_jump_path(
        observations,
        0.04,
        [rfr.PolicyJump(date(2026, 1, 29), -0.0025, "FOMC")],
    )
    np.testing.assert_allclose(path, [0.04, 0.0375, 0.0375])
    scenario = rfr.MultiCurveScenario(sofr, sofr, "USD")
    pv = rfr.collateralized_present_value([100.0], [date(2027, 1, 2)], scenario)
    assert pv == pytest.approx(95.0)
    with pytest.raises(ValueError, match="collateral"):
        rfr.MultiCurveScenario(sofr, sofr, "JPY").validate()
