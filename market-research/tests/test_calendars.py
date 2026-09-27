from datetime import UTC, date, datetime

import pandas as pd
import pytest
from market_research.calendars import SessionCalendar, daily_timings
from market_research.contracts import Instrument


def test_explicit_calendar_preserves_dst_early_close_and_holiday():
    inst = Instrument("XNYS", "ACME", "USD", "America/New_York")
    sessions = {
        date(2026, 3, 6): (
            datetime(2026, 3, 6, 14, 30, tzinfo=UTC),
            datetime(2026, 3, 6, 21, tzinfo=UTC),
        ),
        date(2026, 3, 9): (
            datetime(2026, 3, 9, 13, 30, tzinfo=UTC),
            datetime(2026, 3, 9, 20, tzinfo=UTC),
        ),
        date(2026, 11, 27): (
            datetime(2026, 11, 27, 14, 30, tzinfo=UTC),
            datetime(2026, 11, 27, 18, tzinfo=UTC),
        ),
    }
    calendar = SessionCalendar("XNYS", "test-v1", sessions)
    labels = pd.DatetimeIndex(["2026-03-06", "2026-03-09", "2026-11-27"], tz=inst.timezone)
    timing = daily_timings(labels, inst, datetime(2026, 12, 1, tzinfo=UTC), calendar=calendar)
    assert [row.bar_end.hour for row in timing.values()] == [21, 20, 18]
    with pytest.raises(ValueError, match="session"):
        daily_timings(
            pd.DatetimeIndex(["2026-11-26"], tz=inst.timezone),
            inst,
            datetime(2026, 12, 1, tzinfo=UTC),
            calendar=calendar,
        )


def test_crypto_open_day_is_not_final():
    inst = Instrument("CRYPTO", "BTCUSDT", "USDT", "UTC")
    labels = pd.DatetimeIndex(["2026-09-24", "2026-09-25"], tz="UTC")
    timing = daily_timings(labels, inst, datetime(2026, 9, 25, 14, tzinfo=UTC))
    assert [row.is_final for row in timing.values()] == [True, False]


def test_equity_without_verified_calendar_fails_closed():
    inst = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    with pytest.raises(ValueError, match="calendar"):
        daily_timings(
            pd.DatetimeIndex(["2026-09-25"], tz=inst.timezone),
            inst,
            datetime(2026, 9, 25, 5, tzinfo=UTC),
        )
