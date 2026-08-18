from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from macrokit import expectations

JST = ZoneInfo("Asia/Tokyo")


def test_random_walk_takes_the_prior_quarter_as_it_stood_before_the_release(
    con, insert_obs, insert_rates, make_event
):
    may = datetime(2026, 5, 18, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    insert_obs(date(2026, 1, 1), may, 2.1, 1)       # superseded in June
    insert_obs(date(2026, 1, 1), june, 1.8, 2)      # the value knowable on 8/14
    insert_obs(date(2026, 1, 1), august, 1.9, 1)    # revised ON the release day
    insert_obs(date(2026, 4, 1), august, 1.1, 1)
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    result = expectations.random_walk(con, make_event(date(2026, 4, 1), "1st_prelim", august))

    # Not 1.9 (same-day) and not 2.1 (stale) -- the two failure directions.
    assert result.expected == 1.8
    assert result.as_of == date(2026, 8, 14)


def test_random_walk_has_no_expectation_for_the_oldest_release(
    con, insert_obs, insert_rates, make_event
):
    first = datetime(2009, 2, 16, 8, 50, tzinfo=JST)
    insert_obs(date(2008, 10, 1), first, 1.0, 1)
    insert_rates(date(2009, 2, 13), date(2009, 2, 16))

    event = make_event(date(2008, 10, 1), "1st_prelim", first)
    assert expectations.random_walk(con, event) is None


def test_prior_vintage_anchors_the_second_preliminary_on_the_first(
    con, insert_obs, insert_rates, make_event
):
    may = datetime(2026, 5, 18, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    insert_obs(date(2026, 1, 1), may, 2.1, 1)   # 1st preliminary
    insert_obs(date(2026, 1, 1), june, 1.8, 2)  # 2nd preliminary revised it down
    insert_rates(date(2026, 6, 5), date(2026, 6, 8))

    result = expectations.prior_vintage(con, make_event(date(2026, 1, 1), "2nd_prelim", june))

    assert result.expected == 2.1
    assert result.method == "prior_vintage"


def test_prior_vintage_does_not_apply_to_a_first_preliminary(
    con, insert_obs, insert_rates, make_event
):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    insert_obs(date(2026, 4, 1), august, 1.1, 1)
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    event = make_event(date(2026, 4, 1), "1st_prelim", august)
    assert expectations.prior_vintage(con, event) is None


def test_previous_business_day_uses_market_rates_not_a_holiday_calendar(con, insert_rates):
    insert_rates(date(2026, 8, 13), date(2026, 8, 14), date(2026, 8, 17))
    assert expectations.previous_business_day(con, date(2026, 8, 17)) == date(2026, 8, 14)


def test_random_walk_crosses_the_year_boundary_into_the_prior_q4(
    con, insert_obs, insert_rates, make_event
):
    # 2025 Q4's own 1st preliminary, published well before the 2026 Q1 event
    # this test forecasts -- exercises _previous_quarter's month-underflow
    # branch (period_start.month - 3 < 1), which every real Q1 release hits
    # and which no other test in this module reaches.
    q4_release = datetime(2026, 2, 16, 8, 50, tzinfo=JST)
    insert_obs(date(2025, 10, 1), q4_release, 0.9, 1)

    q1_release = datetime(2026, 5, 18, 8, 50, tzinfo=JST)
    insert_rates(date(2026, 5, 15), date(2026, 5, 18))

    event = make_event(date(2026, 1, 1), "1st_prelim", q1_release)
    result = expectations.random_walk(con, event)

    assert result.expected == 0.9
    assert result.as_of == date(2026, 5, 15)


def test_no_expectation_reads_a_vintage_released_at_or_after_its_event(
    con, insert_obs, insert_rates, make_event
):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    insert_obs(date(2026, 1, 1), june, 1.8, 2)
    insert_obs(date(2026, 1, 1), august, 1.9, 1)
    insert_obs(date(2026, 4, 1), august, 1.1, 1)
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    event = make_event(date(2026, 4, 1), "1st_prelim", august)
    for row in expectations.compute(con, [event]):
        assert row.as_of < august.date()
        assert row.expected != 1.9  # the value that release itself published


def test_ar_model_forecasts_a_constant_series_as_that_constant(
    con, insert_obs, insert_rates, make_event
):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    earlier = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    start = date(2010, 1, 1)
    for i in range(20):
        month = (i % 4) * 3 + 1
        insert_obs(date(start.year + i // 4, month, 1), earlier, 2.0, 2)
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    result = expectations.ar_model(con, make_event(date(2026, 4, 1), "1st_prelim", august))

    assert result is not None
    assert result.expected == pytest.approx(2.0, abs=1e-6)
    assert result.as_of == date(2026, 8, 14)


def test_ar_model_declines_when_the_history_is_shorter_than_p_plus_eight(
    con, insert_obs, insert_rates, make_event
):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    earlier = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    for i in range(11):
        month = (i % 4) * 3 + 1
        insert_obs(date(2020 + i // 4, month, 1), earlier, float(i), 2)
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    event = make_event(date(2026, 4, 1), "1st_prelim", august)
    assert expectations.ar_model(con, event) is None


def test_ar_order_is_pinned_at_four():
    assert expectations.AR_ORDER == 4
    assert expectations.AR_MIN_OBSERVATIONS == 12


def test_compute_includes_ar_model_alongside_random_walk_when_history_allows(
    con, insert_obs, insert_rates, make_event
):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    earlier = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    start = date(2010, 1, 1)
    for i in range(20):
        month = (i % 4) * 3 + 1
        insert_obs(date(start.year + i // 4, month, 1), earlier, 2.0, 2)
    insert_obs(date(2026, 1, 1), earlier, 1.9, 1)  # prior quarter, for random_walk
    insert_rates(date(2026, 8, 14), date(2026, 8, 17))

    event = make_event(date(2026, 4, 1), "1st_prelim", august)
    rows = expectations.compute(con, [event])

    methods = {row.method for row in rows}
    assert methods == {"random_walk", "ar_model"}
