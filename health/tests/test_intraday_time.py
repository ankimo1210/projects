"""Synthetic clocks repeat after a timezone change; observations must not disappear."""

from datetime import UTC, date, datetime, timezone

import duckdb
import pytest
from health.endpoints import CATALOG, PayloadError
from health.store import Store

DAY = date(2025, 1, 1)


def payload(name, instants=("2025-01-01T05:00:00Z", "2025-01-01T06:00:00Z")):
    civil = {"date": {"year": 2025, "month": 1, "day": 1}, "time": {"hours": 14}}
    points = []
    for instant, offset, value in zip(instants, ("32400s", "28800s"), (65, 72), strict=True):
        if name == "intraday_hr":
            points.append(
                {
                    "heartRate": {
                        "sampleTime": {
                            "civilTime": civil,
                            "physicalTime": instant,
                            "utcOffset": offset,
                        },
                        "beatsPerMinute": value,
                    }
                }
            )
        else:
            points.append(
                {
                    "steps": {
                        "interval": {
                            "civilStartTime": civil,
                            "startTime": instant,
                            "startUtcOffset": offset,
                        },
                        "count": value,
                    }
                }
            )
    return {"dataPoints": points}


def metric(name):
    return next(m for m in CATALOG if m.name == name)


@pytest.mark.parametrize("name", ["intraday_hr", "intraday_steps"])
def test_distinct_instants_with_same_civil_clock_survive(name, tmp_path):
    m = metric(name)
    page = payload(name)
    rows = m.parse_pages([page])
    assert [r[1] for r in rows.intraday] == [datetime(2025, 1, 1, 14)] * 2
    assert [t.utc_ts for t in rows.intraday_times] == [
        datetime(2025, 1, 1, 5, tzinfo=UTC),
        datetime(2025, 1, 1, 6, tzinfo=UTC),
    ]
    with_store = Store(tmp_path / "health.duckdb")
    try:
        with_store.replace_chunk(m, DAY, DAY, [page], rows)
        frame = with_store.intraday_time_frame(m.series_names[0], DAY)
        assert frame.value.tolist() == [65, 72]
        assert frame.utc_offset_seconds.tolist() == [32400, 28800]
    finally:
        with_store.close()


@pytest.mark.parametrize("name", ["intraday_hr", "intraday_steps"])
def test_duplicate_instant_is_rejected_even_when_civil_differs(name):
    page = payload(name, ("2025-01-01T05:00:00Z",) * 2)
    block = page["dataPoints"][1]["heartRate" if name.endswith("hr") else "steps"]
    clock = block["sampleTime" if name.endswith("hr") else "interval"]
    clock["civilTime" if name.endswith("hr") else "civilStartTime"] = {
        "date": {"year": 2025, "month": 1, "day": 1},
        "time": {"hours": 13},
    }
    with pytest.raises(PayloadError, match="duplicate"):
        metric(name).parse_pages([page])


def test_migration_preserves_legacy_and_is_idempotent(tmp_path):
    path = tmp_path / "health.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE intraday(metric VARCHAR, ts TIMESTAMP, value DOUBLE, PRIMARY KEY(metric, ts))"
    )
    con.execute("INSERT INTO intraday VALUES ('hr', '2025-01-01 14:00:00', 60)")
    con.close()
    for _ in range(2):
        store = Store(path)
        try:
            assert store.con.execute("SELECT * FROM intraday_legacy").fetchall() == [
                ("hr", datetime(2025, 1, 1, 14), 60)
            ]
            assert store.con.execute(
                "SELECT utc_ts, utc_offset_seconds FROM intraday"
            ).fetchall() == [(None, None)]
            assert store.intraday_frame("hr", DAY).value.tolist() == [60]
        finally:
            store.close()


def test_typed_rebuild_preserves_raw_and_checkpoint(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    m = metric("intraday_hr")
    page = payload(m.name)
    try:
        store.replace_chunk(m, DAY, DAY, [{"dataPoints": []}], m.parse_pages([]))
        before = store.con.execute("SELECT * FROM raw_json").fetchall()
        checkpoint = store.get_sync_checkpoint(m.name)
        store.replace_intraday(m, DAY, m.parse_pages([page]))
        assert store.con.execute("SELECT * FROM raw_json").fetchall() == before
        assert store.get_sync_checkpoint(m.name) == checkpoint
        assert store.intraday_frame("hr", DAY).value.tolist() == [65, 72]
    finally:
        store.close()
