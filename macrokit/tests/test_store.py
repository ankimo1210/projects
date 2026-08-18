from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from macrokit.periods import period_end_for
from macrokit.store import (
    Observation,
    RateObservation,
    ReleaseEvent,
    connect,
    insert_observations,
    insert_rates,
    insert_releases,
)


def _obs(**kw) -> Observation:
    base = dict(
        indicator="us_core_pce",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        release_date=datetime(2024, 4, 1, tzinfo=UTC),
        vintage_seq=1,
        value=120.849,
        unit="index_2017_100",
        sa="sa",
        freq="M",
        source="alfred",
        source_url="https://api.stlouisfed.org/fred/series/observations",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        vintage_kind="actual",
    )
    return Observation(**{**base, **kw})


def _rate(**kw) -> RateObservation:
    base = dict(
        curve="jgb",
        obs_date=date(2026, 7, 31),
        tenor_y=10.0,
        yield_pct=2.801,
        source="mof_jgb",
        source_url="https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    return RateObservation(**{**base, **kw})


def _release(**kw) -> ReleaseEvent:
    base = dict(
        indicator="jp_real_gdp_qoq_saar",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
        release_kind="1st_prelim",
        release_date=datetime(2026, 8, 17, 8, 50, tzinfo=ZoneInfo("Asia/Tokyo")),
        scheduled=False,
        source="esri_calendar",
        source_url="https://www.esri.cao.go.jp/jp/sna/e-stat_sna.xml",
        ingested_at=datetime(2026, 8, 18, tzinfo=UTC),
    )
    return ReleaseEvent(**{**base, **kw})


@pytest.mark.parametrize(
    ("start", "freq", "expected"),
    [
        (date(2024, 1, 1), "M", date(2024, 1, 31)),
        (date(2024, 2, 1), "M", date(2024, 2, 29)),  # leap year
        (date(2024, 1, 1), "Q", date(2024, 3, 31)),
        (date(2024, 10, 1), "Q", date(2024, 12, 31)),
        (date(2024, 1, 1), "A", date(2024, 12, 31)),
        (date(2024, 1, 3), "D", date(2024, 1, 3)),
        (date(2024, 1, 1), "W", date(2024, 1, 7)),
    ],
)
def test_period_end_is_derived_from_frequency(start, freq, expected):
    assert period_end_for(start, freq) == expected


@pytest.mark.parametrize("bad_month", [2, 3, 5, 6, 8, 9, 11, 12])
def test_period_end_for_rejects_a_quarter_start_that_is_not_a_real_quarter_start(bad_month):
    # Months 2/3/5/6/8/9 would silently return a plausible but wrong period
    # end; 11/12 would overflow past December with a confusing
    # calendar.IllegalMonthError. Both must fail clearly instead.
    with pytest.raises(ValueError, match="not a quarter start"):
        period_end_for(date(2024, bad_month, 1), "Q")


def test_round_trips_an_observation(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    assert insert_observations(con, [_obs()]) == 1
    got = con.execute(
        "SELECT indicator, period_start, value, vintage_kind FROM observations"
    ).fetchall()
    assert got == [("us_core_pce", date(2024, 1, 1), 120.849, "actual")]


def test_inserting_the_same_vintage_twice_does_not_duplicate(tmp_path):
    # Re-ingesting an unchanged series must be idempotent, otherwise a daily
    # cron run would multiply every row it has already seen.
    con = connect(tmp_path / "t.duckdb")
    insert_observations(con, [_obs()])
    insert_observations(con, [_obs()])
    assert con.execute("SELECT count(*) FROM observations").fetchone()[0] == 1


def test_rejects_an_unknown_vintage_kind(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="unknown vintage_kind: guessed"):
        insert_observations(con, [_obs(vintage_kind="guessed")])


def test_rejects_a_snapshot_released_after_it_was_ingested(tmp_path):
    # A snapshot's release_date is reconstructed from when WE fetched it, so a
    # release_date in the future of ingested_at means the reconstruction is wrong.
    con = connect(tmp_path / "t.duckdb")
    bad = _obs(
        vintage_kind="snapshot",
        release_date=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="release_date after ingested_at"):
        insert_observations(con, [bad])


def test_allows_an_actual_release_date_before_ingestion(tmp_path):
    # ALFRED legitimately reports release dates years before we fetched them.
    con = connect(tmp_path / "t.duckdb")
    assert insert_observations(con, [_obs(release_date=datetime(2020, 1, 1, tzinfo=UTC))]) == 1


def test_rejects_a_naive_release_date(tmp_path):
    # A naive release_date would be stored after DuckDB reinterprets it in the
    # local session timezone, silently host-dependent -- exactly what a
    # point-in-time platform cannot tolerate.
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="release_date must be a timezone-aware"):
        insert_observations(con, [_obs(release_date=datetime(2024, 4, 1))])


def test_rejects_a_naive_ingested_at(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="ingested_at must be a timezone-aware"):
        insert_observations(con, [_obs(ingested_at=datetime(2026, 8, 17))])


def test_round_trips_a_rate_observation(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    assert insert_rates(con, [_rate()]) == 1
    got = con.execute(
        "SELECT curve, obs_date, tenor_y, yield_pct FROM market_rates"
    ).fetchall()
    assert got == [("jgb", date(2026, 7, 31), 10.0, 2.801)]


def test_inserting_the_same_rate_twice_does_not_duplicate(tmp_path):
    # Re-ingesting an unchanged curve must be idempotent, otherwise a daily
    # cron run would multiply every row it has already seen.
    con = connect(tmp_path / "t.duckdb")
    assert insert_rates(con, [_rate()]) == 1
    # Same (curve, obs_date, tenor_y) but a different value: INSERT OR IGNORE
    # must drop it silently rather than overwrite the original.
    assert insert_rates(con, [_rate(yield_pct=9.999)]) == 0
    got = con.execute("SELECT count(*) FROM market_rates").fetchone()[0]
    assert got == 1
    stored = con.execute("SELECT yield_pct FROM market_rates").fetchone()[0]
    assert stored == 2.801


def test_rejects_a_naive_ingested_at_for_rates(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="ingested_at must be timezone-aware"):
        insert_rates(con, [_rate(ingested_at=datetime(2026, 8, 17))])


def test_round_trips_a_release_event(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    assert insert_releases(con, [_release()]) == 1
    got = con.execute(
        "SELECT indicator, period_start, release_kind, scheduled FROM releases"
    ).fetchall()
    assert got == [("jp_real_gdp_qoq_saar", date(2026, 4, 1), "1st_prelim", False)]


def test_inserting_the_same_release_twice_does_not_duplicate(tmp_path):
    # Re-ingesting an unchanged calendar fetch must be idempotent, otherwise a
    # daily cron run would multiply every row it has already seen.
    con = connect(tmp_path / "t.duckdb")
    assert insert_releases(con, [_release()]) == 1
    # Same (indicator, period_start, release_kind) but a different release_date:
    # INSERT OR IGNORE must drop it silently rather than overwrite the original.
    assert insert_releases(con, [_release(release_date=datetime(2026, 8, 18, 8, 50, tzinfo=UTC))]) == 0
    got = con.execute("SELECT count(*) FROM releases").fetchone()[0]
    assert got == 1
    stored = con.execute("SELECT release_date FROM releases").fetchone()[0]
    assert stored == datetime(2026, 8, 17, 8, 50, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_rejects_a_naive_release_date_for_releases(tmp_path):
    # release_date is the platform-wide invariant: a naive value would be
    # stored after DuckDB reinterprets it in the local session timezone.
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="release_date must be timezone-aware"):
        insert_releases(con, [_release(release_date=datetime(2026, 8, 17, 8, 50))])


def test_rejects_an_unknown_release_kind(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="unknown release_kind: flash"):
        insert_releases(con, [_release(release_kind="flash")])
