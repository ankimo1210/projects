from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

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
