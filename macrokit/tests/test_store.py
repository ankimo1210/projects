from datetime import UTC, date, datetime

import pytest

from macrokit.periods import period_end_for
from macrokit.store import Observation, connect, insert_observations


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
