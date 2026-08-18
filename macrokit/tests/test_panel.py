import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from macrokit import expectations, panel, store

JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=JST)
INDICATOR = "jp_real_gdp_qoq_saar"


def _period_end(period_start: date) -> date:
    end_month = period_start.month + 2
    last_day = 31 if end_month in (3, 12) else 30
    return date(period_start.year, end_month, last_day)


def _event(period_start, kind, release_date, *, scheduled=False):
    return store.ReleaseEvent(
        indicator=INDICATOR, period_start=period_start, period_end=_period_end(period_start),
        release_kind=kind, release_date=release_date, scheduled=scheduled,
        source="esri_calendar", source_url="u", ingested_at=NOW,
    )


def _observation(period_start, release_date, value, seq):
    return store.Observation(
        indicator=INDICATOR, period_start=period_start, period_end=_period_end(period_start),
        release_date=release_date, vintage_seq=seq, value=value, unit="percent_saar", sa="sa",
        freq="Q", source="esri_gdp", source_url="u", ingested_at=NOW, vintage_kind="actual",
    )


def _rate(obs_date, tenor_y, yield_pct):
    return store.RateObservation(
        curve="jgb", obs_date=obs_date, tenor_y=tenor_y, yield_pct=yield_pct,
        source="mof_jgb", source_url="u", ingested_at=NOW,
    )


def _expectation(period_start, release_kind, method, expected, as_of):
    return store.Expectation(
        indicator=INDICATOR, period_start=period_start, release_kind=release_kind,
        method=method, expected=expected, as_of=as_of, source="macrokit",
        source_url="computed://macrokit/expectations", ingested_at=NOW,
    )


def _seed_2026_q2(con):
    """The 2026 Q2 1st-preliminary release, its rate move, and its expectations.

    2026 Q1 has three vintages across its own two releases plus the revision
    riding along on the 2026 Q2 release day: 2.1 (1st_prelim, 5/18), 1.8
    (2nd_prelim, 6/8), 1.9 (revised on 8/17, the same day as the Q2 release).
    `random_walk`'s expectation for the Q2 print must land on 1.8 -- the
    value knowable strictly before 8/17 -- not 1.9 (same-day) or 2.1 (stale).
    """
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    may = datetime(2026, 5, 18, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)

    event = _event(date(2026, 4, 1), "1st_prelim", august)
    store.insert_releases(con, [event])
    store.insert_observations(con, [
        _observation(date(2026, 1, 1), may, 2.1, 1),
        _observation(date(2026, 1, 1), june, 1.8, 2),
        _observation(date(2026, 1, 1), august, 1.9, 1),
        _observation(date(2026, 4, 1), august, 1.1, 1),
    ])
    store.insert_rates(con, [
        _rate(date(2026, 8, 14), 2.0, 1.657),
        _rate(date(2026, 8, 14), 10.0, 2.878),
        _rate(date(2026, 8, 17), 2.0, 1.697),
        _rate(date(2026, 8, 17), 10.0, 2.930),
    ])
    store.insert_expectations(con, expectations.compute(con, [event]))


def _seed_uniform_surprises(con, count):
    """`count` 1st_prelim releases, oldest first, whose random_walk surprise is
    exactly its 0-indexed position: expected is pinned to 0.0 so surprise ==
    actual == i. This gives `_expanding_z` a surprise series with a
    hand-computable prior standard deviation, unlike a single seeded event
    (whose std() is always NaN and so proves nothing about the expanding,
    strictly-prior computation).

    Also seeds one JGB session per release plus one earlier base session, so
    every row has a d1_bp move and survives event_panel's any-tenor-present
    filter.
    """
    store.insert_rates(con, [_rate(date(1999, 12, 1), 10.0, 2.0)])
    for i in range(count):
        year, quarter = divmod(i, 4)
        period_start = date(2000 + year, quarter * 3 + 1, 1)
        release_date = datetime(2000 + year, quarter * 3 + 1, 15, 8, 50, tzinfo=JST)
        event = _event(period_start, "1st_prelim", release_date)
        store.insert_releases(con, [event])
        store.insert_observations(con, [_observation(period_start, release_date, float(i), 1)])
        store.insert_rates(con, [_rate(release_date.date(), 10.0, 2.0 + 0.01 * i)])
        store.insert_expectations(con, [
            _expectation(period_start, "1st_prelim", "random_walk", 0.0, release_date.date())
        ])


def _seed_future_release(con):
    """A scheduled 2027 release with an actual and an expectation but no market_rates."""
    release_date = datetime(2027, 2, 15, 8, 50, tzinfo=JST)
    event = _event(date(2026, 10, 1), "1st_prelim", release_date, scheduled=True)
    store.insert_releases(con, [event])
    store.insert_observations(con, [_observation(date(2026, 10, 1), release_date, 1.5, 1)])
    store.insert_expectations(con, [
        _expectation(date(2026, 10, 1), "1st_prelim", "random_walk", 1.2, date(2027, 2, 12))
    ])


def test_the_panel_pairs_a_release_with_that_days_move(con):
    _seed_2026_q2(con)

    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(2.0, 10.0))
    row = frame[frame["method"] == "random_walk"].iloc[0]

    assert row["release_date"].date() == date(2026, 8, 17)
    assert row["actual"] == 1.1
    assert row["expected"] == 1.8
    assert row["surprise"] == pytest.approx(-0.7)
    assert row["d1_bp_10y"] == pytest.approx(5.2, abs=0.1)
    assert row["d1_bp_2y"] == pytest.approx(4.0, abs=0.1)


def test_surprise_z_divides_by_the_std_of_strictly_prior_surprises(con):
    # A single seeded event cannot pin this behaviour: std() over one value is
    # NaN under ddof=1, so `surprise_z.isna().all()` would hold for the
    # correct expanding/strictly-prior computation, for a full-sample sigma
    # (exactly the look-ahead spec section 6.2 forbids), and for a stub that
    # always returns NaN. Seed 21 releases instead so min_periods=20 is
    # satisfied for the 21st, and pin its value.
    _seed_uniform_surprises(con, 21)
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    assert len(frame) == 21

    # The first 20 releases (surprises 0..19) have fewer than 20 strictly
    # prior surprises each, so all of them stay null.
    assert frame["surprise_z"].iloc[:20].isna().all()

    # The 21st release's z divides its surprise (20.0) by the sample std
    # (ddof=1) of the 20 *prior* surprises 0..19 -- not the current one.
    prior_sigma = math.sqrt(35.0)  # std(range(20), ddof=1) == sqrt(665 / 19)
    assert frame["surprise_z"].iloc[20] == pytest.approx(20.0 / prior_sigma)


def test_a_tenor_that_did_not_exist_yet_is_null_not_zero(con):
    _seed_2026_q2(con)  # seeds 2y and 10y only
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0, 40.0))
    assert frame["d1_bp_40y"].isna().all()
    assert frame["d1_bp_10y"].notna().all()


def test_a_release_with_no_rate_row_is_dropped_from_the_panel(con):
    # Drops the row silently -- spec section 7's "record the exclusion
    # reason" is not implemented, so this only verifies the drop itself, not
    # a count of exclusions or why.
    _seed_2026_q2(con)
    _seed_future_release(con)  # a scheduled 2027 release, no market_rates
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    assert (frame["release_date"].dt.year == 2027).sum() == 0
