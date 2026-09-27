from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from market_research.contracts import MacroObservation
from market_research.macro import as_of, latest

RELEASE = datetime(2026, 9, 25, 12, tzinfo=UTC)
PERIOD = date(2026, 8, 1)


def observation(value=100.0, **changes):
    values = dict(
        indicator="CPI",
        period_start=PERIOD,
        release_at=RELEASE,
        value=value,
        source="BLS",
        vintage_id="first",
    )
    values.update(changes)
    return MacroObservation(**values)


def test_release_boundary_excludes_future_and_includes_exact_instant():
    row = observation()
    assert as_of([row], "CPI", RELEASE - timedelta(microseconds=1)) == ()
    assert as_of([row], "CPI", RELEASE) == (row,)


def test_old_period_revision_is_visible_only_after_second_release():
    original = observation()
    revision = observation(101.0, release_at=RELEASE + timedelta(days=30), vintage_id="revised")
    rows = [original, revision]
    assert as_of(rows, "CPI", RELEASE + timedelta(days=1))[0].value == 100.0
    assert as_of(rows, "CPI", RELEASE + timedelta(days=31))[0].value == 101.0
    assert latest(rows, "CPI", now=RELEASE + timedelta(days=31))[0].vintage_id == "revised"


def test_naive_as_of_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        as_of([observation()], "CPI", datetime(2026, 9, 25, 12))


def test_release_comparison_uses_instant_not_host_timezone():
    tokyo = RELEASE.astimezone(ZoneInfo("Asia/Tokyo"))
    assert as_of([observation()], "CPI", tokyo) == (observation(),)


def test_same_source_same_release_conflict_is_rejected():
    with pytest.raises(ValueError, match="conflicting"):
        as_of([observation(), observation(101.0, vintage_id="other")], "CPI", RELEASE)


def test_two_sources_require_explicit_source_choice():
    other = observation(99.0, source="OECD", vintage_id="oecd-first")
    with pytest.raises(ValueError, match="source"):
        as_of([observation(), other], "CPI", RELEASE)
    assert as_of([observation(), other], "CPI", RELEASE, source="OECD") == (other,)
