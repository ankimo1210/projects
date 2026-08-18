from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from macrokit.catalog import ReleaseRule
from macrokit.holidays import load_holidays, parse_holiday_csv
from macrokit.release import nth_business_day, resolve_release

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_the_cabinet_office_csv_which_is_cp932_not_utf8():
    raw = (FIXTURES / "syukujitsu_sample.csv").read_bytes()
    # Guard the premise: if this ever decodes as UTF-8 the fixture is wrong.
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")

    holidays = parse_holiday_csv(raw)
    assert date(2026, 1, 1) in holidays
    assert date(2026, 5, 6) in holidays  # 振替休日 also appears, named 休日
    assert date(2026, 1, 2) not in holidays


def test_load_holidays_reads_the_cache_without_network(tmp_path):
    # tmp_path, not the fixtures directory: a test must never leave a cache
    # behind in the repo.
    (tmp_path / "syukujitsu.csv").write_bytes((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    holidays = load_holidays(tmp_path, fetch=False)
    assert date(2026, 5, 5) in holidays


def test_load_holidays_refuses_to_fetch_when_told_not_to(tmp_path):
    with pytest.raises(FileNotFoundError, match="fetch=False"):
        load_holidays(tmp_path, fetch=False)


def test_nth_business_day_skips_weekends_and_holidays():
    # CAVEAT (see nth_business_day's docstring): this fixture's holiday set is
    # only the Cabinet Office CSV, which excludes the 年末年始 closure and bank
    # holidays. This January result happens to match the fixture as given,
    # but it is not validated Bank of Japan behaviour -- do not read a passing
    # assertion here as proof the real January business-day count is right.
    holidays = parse_holiday_csv((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    # 2026-01: 1(Thu) is 元日, 2(Fri) and 5(Mon) are business days,
    # 3-4 weekend, so business days run 2, 5, 6, 7, 8, ...
    assert nth_business_day(2026, 1, 1, holidays) == date(2026, 1, 2)
    assert nth_business_day(2026, 1, 2, holidays) == date(2026, 1, 5)
    assert nth_business_day(2026, 1, 5, holidays) == date(2026, 1, 8)


def test_nth_business_day_raises_when_the_month_is_too_short():
    with pytest.raises(ValueError, match="month 2026-02 has no 25th business day"):
        nth_business_day(2026, 2, 25, set())


def test_resolve_release_for_nth_business_day_returns_an_aware_datetime():
    # CAVEAT: n=5 in January is exactly the Bank of Japan 消費活動指数 rule this
    # module was built for, but the fixture's holiday set has the same
    # 年末年始/bank-holiday gap noted on nth_business_day -- this test checks the
    # arithmetic and the timezone, not that the real BOJ date is reproduced.
    holidays = parse_holiday_csv((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    rule = ReleaseRule(kind="nth_business_day", n=5, time="14:00", tz="Asia/Tokyo", calendar="jp")
    # Period ending 2025-12-31 is published in the month after the period ends.
    got = resolve_release(rule, date(2025, 12, 31), holidays)
    assert got == datetime(2026, 1, 8, 14, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_for_fixed_day():
    rule = ReleaseRule(kind="fixed_day", day=19, time="08:30", tz="Asia/Tokyo", calendar="jp")
    got = resolve_release(rule, date(2026, 1, 31), set())
    assert got == datetime(2026, 2, 19, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_for_nth_weekday():
    # 3rd Friday of the month after the period. 2026-02: Fridays are 6, 13, 20.
    rule = ReleaseRule(
        kind="nth_weekday", n=3, weekday=4, time="08:30", tz="Asia/Tokyo", calendar="jp"
    )
    got = resolve_release(rule, date(2026, 1, 31), set())
    assert got == datetime(2026, 2, 20, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_returns_none_for_manual_rules():
    rule = ReleaseRule(kind="manual", tz="Asia/Tokyo", calendar="jp")
    assert resolve_release(rule, date(2026, 1, 31), set()) is None


def test_resolve_release_rejects_the_us_calendar():
    # calendar="us" is a valid ReleaseRule value, but resolve_release only
    # knows how to apply Japanese holiday logic. Silently applying it to a
    # US-marked rule would be wrong, not just unimplemented -- US release
    # dates come from FRED's releases endpoint instead.
    rule = ReleaseRule(kind="fixed_day", day=19, time="08:30", tz="America/New_York", calendar="us")
    with pytest.raises(ValueError, match="only knows the 'jp' calendar"):
        resolve_release(rule, date(2026, 1, 31), set())


def test_month_offset_two_expresses_a_two_month_publication_lag():
    """法人企業統計 publishes about two months after the quarter ends."""
    rule = ReleaseRule(kind="fixed_day", day=1, month_offset=2)
    assert resolve_release(rule, date(2026, 6, 30), holidays=set()).date() == date(2026, 8, 1)


def test_month_offset_defaults_to_one_so_existing_rules_are_unchanged():
    rule = ReleaseRule(kind="fixed_day", day=10)
    assert resolve_release(rule, date(2026, 6, 30), holidays=set()).date() == date(2026, 7, 10)


def test_month_offset_rolls_over_the_year_boundary():
    rule = ReleaseRule(kind="fixed_day", day=15, month_offset=2)
    assert resolve_release(rule, date(2026, 12, 31), holidays=set()).date() == date(2027, 2, 15)


def test_month_offset_must_be_positive():
    with pytest.raises(ValidationError):
        ReleaseRule(kind="fixed_day", day=1, month_offset=0)
