from datetime import date

import pytest

from health.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_upsert_daily_idempotent(store):
    rows = [("steps", "2026-07-01", 100.0), ("steps", "2026-07-02", 200.0)]
    store.upsert_daily(rows)
    store.upsert_daily([("steps", "2026-07-02", 250.0)])  # overwrite
    df = store.daily_frame(["steps"])
    assert len(df) == 2
    # date dtype after duckdb->pandas may be datetime64 or object; compare as prefix
    mask = df["date"].astype(str).str.startswith("2026-07-02")
    assert df.loc[mask, "steps"].iloc[0] == 250.0


def test_daily_frame_missing_metric_gives_nan_column(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0)])
    df = store.daily_frame(["steps", "resting_hr"])
    assert "resting_hr" in df.columns and df["resting_hr"].isna().all()


def test_upsert_daily_empty_noop(store):
    store.upsert_daily([])
    assert store.daily_frame(["steps"]).empty


def test_sleep_roundtrip_idempotent(store):
    row = {"log_id": 1, "date": "2026-07-01", "start_ts": "2026-06-30 23:41:30",
           "end_ts": "2026-07-01 07:05:30", "minutes_asleep": 402, "minutes_deep": 80,
           "minutes_light": 220, "minutes_rem": 102, "minutes_wake": 42,
           "efficiency": 93, "is_main": True}
    store.upsert_sleep([row])
    store.upsert_sleep([row])
    assert len(store.sleep_frame()) == 1


def test_sleep_upsert_revises_all_columns(store):
    # trailing-3-day refetch can deliver a revised sleep log for the same log_id;
    # every non-PK column (not just minutes_asleep/efficiency) must refresh.
    row = {"log_id": 1, "date": "2026-07-01", "start_ts": "2026-06-30 23:41:30",
           "end_ts": "2026-07-01 07:05:30", "minutes_asleep": 402, "minutes_deep": 80,
           "minutes_light": 220, "minutes_rem": 102, "minutes_wake": 42,
           "efficiency": 93, "is_main": True}
    store.upsert_sleep([row])
    revised = dict(row, minutes_deep=95, start_ts="2026-06-30 23:20:00")
    store.upsert_sleep([revised])
    df = store.sleep_frame()
    assert len(df) == 1
    assert df.loc[0, "minutes_deep"] == 95
    assert str(df.loc[0, "start_ts"]).startswith("2026-06-30 23:20:00")


def test_intraday_roundtrip(store):
    store.upsert_intraday([("hr", "2026-07-01 00:00:00", 62.0),
                           ("hr", "2026-07-01 00:01:00", 63.0),
                           ("hr", "2026-07-02 00:00:00", 60.0)])
    df = store.intraday_frame("hr", date(2026, 7, 1))
    assert len(df) == 2 and list(df["value"]) == [62.0, 63.0]


def test_sync_state_roundtrip(store):
    assert store.get_sync_state("steps") is None
    store.set_sync_state("steps", date(2026, 7, 1))
    store.set_sync_state("steps", date(2026, 7, 5))
    assert store.get_sync_state("steps") == date(2026, 7, 5)
    states = store.sync_states()
    assert list(states["metric"]) == ["steps"] and list(states["status"]) == ["ok"]


def test_series_stats(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0), ("steps", "2026-07-03", 2.0),
                        ("resting_hr", "2026-07-02", 60.0)])
    stats = store.series_stats().set_index("metric")
    assert stats.loc["steps", "n"] == 2
    assert str(stats.loc["steps", "first_date"]).startswith("2026-07-01")


def test_raw_upsert_idempotent(store):
    store.upsert_raw("steps", "2026-07-01_2026-07-02", {"a": 1})
    store.upsert_raw("steps", "2026-07-01_2026-07-02", {"a": 2})
    n = store.con.execute("SELECT count(*) FROM raw_json").fetchone()[0]
    assert n == 1
