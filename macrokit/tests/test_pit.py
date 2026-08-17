from datetime import UTC, date, datetime

import pandas as pd

from macrokit.pit import as_of, latest, revisions
from macrokit.store import Observation, connect, insert_observations


def _seed(con) -> None:
    """Two periods. January was revised twice; February was released once.

    January:  2024-04-01 -> 120.849, then 2024-04-26 -> 120.909
    February: 2024-04-26 -> 121.100
    """
    common = dict(
        indicator="us_core_pce",
        unit="index_2017_100",
        sa="sa",
        freq="M",
        source="alfred",
        source_url="https://example.invalid",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        vintage_kind="actual",
    )
    insert_observations(
        con,
        [
            Observation(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                release_date=datetime(2024, 4, 1, tzinfo=UTC),
                vintage_seq=1,
                value=120.849,
                **common,
            ),
            Observation(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                release_date=datetime(2024, 4, 26, tzinfo=UTC),
                vintage_seq=2,
                value=120.909,
                **common,
            ),
            Observation(
                period_start=date(2024, 2, 1),
                period_end=date(2024, 2, 29),
                release_date=datetime(2024, 4, 26, tzinfo=UTC),
                vintage_seq=1,
                value=121.100,
                **common,
            ),
        ],
    )


def test_as_of_returns_the_latest_vintage_released_on_or_before_the_date(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    assert got.loc[date(2024, 1, 1)] == 120.849  # the revision has not happened yet


def test_as_of_never_includes_a_release_in_the_future_of_the_query(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    # February was only released on 2024-04-26, so it must be absent entirely.
    assert date(2024, 2, 1) not in got.index


def test_as_of_does_not_forward_fill(tmp_path):
    # A period with no release on or before the date is ABSENT, not carried
    # forward from a neighbour. Forward-filling here would invent data that no
    # analyst could have seen.
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    assert list(got.index) == [date(2024, 1, 1)]
    assert not got.isna().any()


def test_as_of_before_any_release_is_empty(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 1, 1, tzinfo=UTC))
    assert got.empty


def test_as_of_today_equals_latest(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    pd.testing.assert_series_equal(
        as_of(con, "us_core_pce", datetime(2030, 1, 1, tzinfo=UTC)),
        latest(con, "us_core_pce"),
    )


def test_latest_takes_the_most_recent_revision(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = latest(con, "us_core_pce")
    assert got.loc[date(2024, 1, 1)] == 120.909
    assert got.loc[date(2024, 2, 1)] == 121.100


def test_revisions_lists_every_vintage_for_one_period_in_order(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = revisions(con, "us_core_pce", date(2024, 1, 1))
    assert list(got["value"]) == [120.849, 120.909]
    assert list(got["vintage_seq"]) == [1, 2]
    assert list(got.columns) == ["release_date", "value", "vintage_seq", "vintage_kind"]


def test_vintage_seq_is_dense_and_starts_at_one_per_period(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    rows = con.execute(
        "SELECT period_start, list(vintage_seq ORDER BY release_date) "
        "FROM observations WHERE indicator = 'us_core_pce' GROUP BY period_start"
    ).fetchall()
    for _period, seqs in rows:
        assert seqs == list(range(1, len(seqs) + 1))
