from datetime import UTC, date, datetime

import pandas as pd
import pytest

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


def _seed_other_indicator(con) -> None:
    """A second indicator sharing the January 2024 period with us_core_pce,
    plus one period of its own, all with unmistakably different values.

    The shared period is deliberate: if a query ever drops its
    ``WHERE indicator = ?`` filter, ``row_number() OVER (PARTITION BY
    period_start ...)`` would blend this indicator's row into
    ``us_core_pce``'s partition and change *which value wins*, not just add
    an extra row -- a corruption that a "does it still run" check would miss
    but an exact-value assertion catches.

    us_headline_cpi:
      2024-01 -> 999.999 released 2024-04-05 (between us_core_pce's two Jan
                 vintages: 2024-04-01 and 2024-04-26)
      2024-03 -> 1001.001 released 2024-04-26 (a period us_core_pce has none of)
    """
    common = dict(
        indicator="us_headline_cpi",
        unit="index_1982_84_100",
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
                release_date=datetime(2024, 4, 5, tzinfo=UTC),
                vintage_seq=1,
                value=999.999,
                **common,
            ),
            Observation(
                period_start=date(2024, 3, 1),
                period_end=date(2024, 3, 31),
                release_date=datetime(2024, 4, 26, tzinfo=UTC),
                vintage_seq=1,
                value=1001.001,
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


def test_as_of_rejects_a_naive_datetime(tmp_path):
    # A naive `when` would be interpreted by DuckDB in the host's local
    # session timezone, so the same query returns different rows on a machine
    # in Tokyo versus one in UTC. That must fail loudly, not silently.
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    with pytest.raises(ValueError, match="timezone-aware"):
        as_of(con, "us_core_pce", datetime(2024, 4, 10))


def test_as_of_returns_only_the_requested_indicator(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    _seed_other_indicator(con)

    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    # us_headline_cpi's Jan release (2024-04-05, value 999.999) is on or
    # before the query date and shares the January partition -- if the
    # indicator filter were dropped, it would outrank us_core_pce's own
    # 2024-04-01 vintage and 999.999 would win instead of 120.849.
    assert got.loc[date(2024, 1, 1)] == 120.849
    assert date(2024, 3, 1) not in got.index  # us_headline_cpi's own period

    other = as_of(con, "us_headline_cpi", datetime(2024, 5, 1, tzinfo=UTC))
    assert other.loc[date(2024, 1, 1)] == 999.999
    assert other.loc[date(2024, 3, 1)] == 1001.001
    assert date(2024, 2, 1) not in other.index  # us_core_pce's own period


def test_latest_returns_only_the_requested_indicator(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    _seed_other_indicator(con)

    got = latest(con, "us_core_pce")
    assert got.loc[date(2024, 1, 1)] == 120.909
    assert date(2024, 3, 1) not in got.index

    # us_core_pce's own Jan 2024 vintage (2024-04-26) is more recent than
    # us_headline_cpi's (2024-04-05), so a dropped filter would make this
    # query return 120.909 -- someone else's value -- instead of 999.999.
    other = latest(con, "us_headline_cpi")
    assert other.loc[date(2024, 1, 1)] == 999.999
    assert other.loc[date(2024, 3, 1)] == 1001.001
    assert date(2024, 2, 1) not in other.index


def test_revisions_returns_only_the_requested_indicator(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    _seed_other_indicator(con)

    # Same period_start (2024-01-01) on both indicators: revisions() already
    # filters by period_start, so this is the case where dropping the
    # indicator filter would slip an extra row past that other condition.
    got = revisions(con, "us_core_pce", date(2024, 1, 1))
    assert list(got["value"]) == [120.849, 120.909]
    assert 999.999 not in set(got["value"])


def test_vintage_seq_is_dense_and_starts_at_one_per_period(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    rows = con.execute(
        "SELECT period_start, list(vintage_seq ORDER BY release_date) "
        "FROM observations WHERE indicator = 'us_core_pce' GROUP BY period_start"
    ).fetchall()
    for _period, seqs in rows:
        assert seqs == list(range(1, len(seqs) + 1))
