import os
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from macrokit.sources import esri_calendar

FIXTURES = Path(__file__).parent / "fixtures"
JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _events():
    content = (FIXTURES / "esri_sna_calendar.xml").read_bytes()
    return esri_calendar.parse_calendar_xml(
        content, indicator="jp_real_gdp_qoq_saar", source_url="u", ingested_at=NOW
    )


@pytest.mark.parametrize(
    ("name", "start", "end"),
    [
        ("平成20年10-12月期", date(2008, 10, 1), date(2008, 12, 31)),
        ("2026年4-6月期", date(2026, 4, 1), date(2026, 6, 30)),
        ("2026年10-12月期", date(2026, 10, 1), date(2026, 12, 31)),
    ],
)
def test_parse_period_name_handles_both_era_and_western_forms(name, start, end):
    assert esri_calendar.parse_period_name(name) == (start, end)


def test_only_the_quarterly_gdp_branch_is_read():
    """民間企業資本ストック速報 shares the file and must not leak into releases."""
    assert len(_events()) == 5


def test_the_three_release_kinds_are_mapped():
    kinds = sorted({e.release_kind for e in _events()})
    assert kinds == ["1st_prelim", "2nd_prelim", "2nd_prelim_revised"]


def test_release_datetimes_are_jst_aware_at_0850():
    event = next(e for e in _events() if e.period_start == date(2026, 4, 1))
    assert event.release_date == datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    assert event.release_kind == "1st_prelim"


def test_a_future_dated_row_is_marked_scheduled():
    future = next(e for e in _events() if e.period_start == date(2026, 10, 1))
    past = next(e for e in _events() if e.period_start == date(2026, 4, 1))
    assert future.scheduled is True
    assert past.scheduled is False


def test_a_half_width_gdp_name_finds_nothing():
    """The statistic is named with a full-width ＧＤＰ; guard the constant."""
    assert "ＧＤＰ" in esri_calendar.GDP_CLASS_1
    assert "GDP" not in esri_calendar.GDP_CLASS_1


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("MACROKIT_LIVE"), reason="live network test; set MACROKIT_LIVE=1 to run"
)
def test_the_live_feed_still_has_the_counts_the_spec_measured():
    adapter = esri_calendar.EsriCalendarAdapter()
    content, url, _ = adapter.fetch_raw()
    events = adapter.parse(
        content, indicator="jp_real_gdp_qoq_saar", source_url=url,
        ingested_at=datetime.now(UTC),
    )
    kinds = Counter(e.release_kind for e in events)
    assert kinds["1st_prelim"] >= 73
    assert kinds["2nd_prelim"] >= 73
    assert kinds["2nd_prelim_revised"] == 2
    assert min(e.release_date.date() for e in events) == date(2009, 2, 16)
