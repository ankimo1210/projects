from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.sources import boj_api

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


def _parse(name, curve):
    content = (FIXTURES / name).read_bytes()
    return boj_api.parse_series(content, curve=curve, source_url="u", ingested_at=NOW)


def test_daily_rows_skip_nulls_and_keep_the_mid_month_hike():
    rows = _parse("boj_call_daily.json", boj_api.DAILY_CURVE)
    by_day = {r.obs_date: r.yield_pct for r in rows}
    assert len(rows) == 22  # 30 calendar days, 8 nulls (weekends)
    assert date(2026, 6, 6) not in by_day
    assert by_day[date(2026, 6, 16)] == 0.727
    assert by_day[date(2026, 6, 17)] == 0.978
    assert by_day[date(2026, 6, 30)] == 0.976
    assert {r.curve for r in rows} == {"jp_call_on"}
    assert {r.tenor_y for r in rows} == {1 / 365}


def test_monthly_rows_are_dated_on_the_first_of_the_month():
    rows = _parse("boj_call_mavg.json", boj_api.MONTHLY_CURVE)
    assert [(r.obs_date, r.yield_pct) for r in rows] == [
        (date(1985, 7, 1), 6.4167),
        (date(1985, 8, 1), 6.5),
    ]


def test_an_error_status_is_raised_with_the_message():
    content = b'{"STATUS":400,"MESSAGEID":"M181005E","MESSAGE":"Invalid DB","RESULTSET":[]}'
    with pytest.raises(boj_api.BojApiError, match="M181005E"):
        boj_api.parse_series(content, curve="x", source_url="u", ingested_at=NOW)


def test_a_paged_response_is_refused():
    content = (
        (FIXTURES / "boj_call_daily.json")
        .read_text()
        .replace('"NEXTPOSITION":null', '"NEXTPOSITION":2')
    )
    with pytest.raises(boj_api.BojApiError, match="NEXTPOSITION"):
        boj_api.parse_series(content.encode(), curve="x", source_url="u", ingested_at=NOW)


def test_adapter_parse_keeps_each_payloads_curve():
    daily = (FIXTURES / "boj_call_daily.json").read_bytes()
    monthly = (FIXTURES / "boj_call_mavg.json").read_bytes()
    rows = boj_api.BojCallRateAdapter().parse(
        [(daily, "u1", 200, boj_api.DAILY_CURVE), (monthly, "u2", 200, boj_api.MONTHLY_CURVE)],
        ingested_at=NOW,
    )
    assert {r.curve for r in rows} == {"jp_call_on", "jp_call_on_mavg"}
    assert len(rows) == 24
