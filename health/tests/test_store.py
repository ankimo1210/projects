from datetime import date, datetime

import duckdb
import pytest
from health.endpoints import CATALOG, Metric, ParsedRows
from health.store import Store


def by_name(name: str) -> Metric:
    return next(m for m in CATALOG if m.name == name)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def sleep_row(provider_id="8f14e45f-ceea-467e-b115-8bb0f0c76a8f", d="2026-07-01"):
    return {
        "provider_id": provider_id,
        "date": d,
        "start_ts": "2026-06-30 23:41:30",
        "end_ts": f"{d} 07:05:30",
        "minutes_asleep": 402,
        "minutes_deep": 80,
        "minutes_light": 220,
        "minutes_rem": 102,
        "minutes_wake": 42,
        "efficiency": 93,
        "is_main": True,
    }


# -- legacy upsert helpers (seed script / low-level writes) -------------------


def test_upsert_daily_idempotent(store):
    rows = [("steps", "2026-07-01", 100.0), ("steps", "2026-07-02", 200.0)]
    store.upsert_daily(rows)
    store.upsert_daily([("steps", "2026-07-02", 250.0)])  # overwrite
    df = store.daily_frame(["steps"])
    assert len(df) == 2
    mask = df["date"].astype(str).str.startswith("2026-07-02")
    assert df.loc[mask, "steps"].iloc[0] == 250.0


def test_daily_frame_missing_metric_gives_nan_column(store):
    store.upsert_daily([("steps", "2026-07-01", 1.0)])
    df = store.daily_frame(["steps", "resting_hr"])
    assert "resting_hr" in df.columns and df["resting_hr"].isna().all()


def test_upsert_daily_empty_noop(store):
    store.upsert_daily([])
    assert store.daily_frame(["steps"]).empty


def test_sleep_roundtrip_stores_uuid_like_provider_id(store):
    row = sleep_row()
    store.upsert_sleep([row])
    store.upsert_sleep([row])  # idempotent
    df = store.sleep_frame()
    assert len(df) == 1
    assert df.loc[0, "provider_id"] == row["provider_id"]


def test_sleep_upsert_revises_all_columns(store):
    # trailing refetch can deliver a revised sleep log for the same provider_id;
    # every non-PK column (not just minutes_asleep/efficiency) must refresh.
    row = sleep_row()
    store.upsert_sleep([row])
    revised = dict(row, minutes_deep=95, start_ts="2026-06-30 23:20:00")
    store.upsert_sleep([revised])
    df = store.sleep_frame()
    assert len(df) == 1
    assert df.loc[0, "minutes_deep"] == 95
    assert str(df.loc[0, "start_ts"]).startswith("2026-06-30 23:20:00")


def test_intraday_roundtrip(store):
    store.upsert_intraday(
        [
            ("hr", "2026-07-01 00:00:00", 62.0),
            ("hr", "2026-07-01 00:01:00", 63.0),
            ("hr", "2026-07-02 00:00:00", 60.0),
        ]
    )
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
    store.upsert_daily(
        [
            ("steps", "2026-07-01", 1.0),
            ("steps", "2026-07-03", 2.0),
            ("resting_hr", "2026-07-02", 60.0),
        ]
    )
    stats = store.series_stats().set_index("metric")
    assert stats.loc["steps", "n"] == 2
    assert str(stats.loc["steps", "first_date"]).startswith("2026-07-01")


# -- summary frames -----------------------------------------------------------


def test_raw_stats_counts_pages_per_metric(store):
    metric = by_name("steps")
    store.replace_chunk(
        metric, date(2026, 7, 1), date(2026, 7, 3), [{"p": 0}, {"p": 1}], ParsedRows()
    )
    stats = store.raw_stats().set_index("metric")
    assert stats.loc["steps", "n_pages"] == 2


def test_sleep_stats_summarizes_sessions(store):
    store.upsert_sleep([sleep_row("uuid-1", "2026-07-01"), sleep_row("uuid-2", "2026-07-02")])
    stats = store.sleep_stats()
    assert stats.loc[0, "n"] == 2


def test_intraday_stats_counts_rows_per_metric(store):
    store.upsert_intraday(
        [("hr", "2026-07-01 00:00:00", 60.0), ("hr", "2026-07-01 00:01:00", 61.0)]
    )
    stats = store.intraday_stats().set_index("metric")
    assert stats.loc["hr", "n"] == 2


# -- replace_chunk: raw page replacement --------------------------------------


def test_replace_chunk_stores_all_pages(store):
    metric = by_name("steps")
    payloads = [{"page": 0}, {"page": 1}, {"page": 2}]
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 3), payloads, ParsedRows())
    idxs = [
        r[0]
        for r in store.con.execute(
            "SELECT page_index FROM raw_json WHERE metric = ? ORDER BY page_index", [metric.name]
        ).fetchall()
    ]
    assert idxs == [0, 1, 2]


def test_replace_chunk_refetch_with_fewer_pages_drops_stale_pages(store):
    metric = by_name("steps")
    start, end = date(2026, 7, 1), date(2026, 7, 3)
    store.replace_chunk(metric, start, end, [{"p": 0}, {"p": 1}, {"p": 2}], ParsedRows())
    store.replace_chunk(metric, start, end, [{"p": 0}], ParsedRows())
    idxs = [
        r[0]
        for r in store.con.execute(
            "SELECT page_index FROM raw_json WHERE metric = ?", [metric.name]
        ).fetchall()
    ]
    assert idxs == [0]


# -- replace_chunk: typed row scoping ------------------------------------------


def test_replace_chunk_daily_scopes_to_own_series_and_range(store):
    metric = by_name("steps")  # series_names == ("steps",)
    store.upsert_daily(
        [
            ("steps", "2026-06-15", 500.0),  # same series, out of range -> survives
            ("distance_km", "2026-07-02", 5.0),  # different series, in range -> survives
            ("steps", "2026-07-01", 100.0),  # same series, in range -> replaced
        ]
    )
    rows = ParsedRows(
        daily=(("steps", date(2026, 7, 1), 111.0), ("steps", date(2026, 7, 2), 222.0))
    )
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 3), [{"p": 0}], rows)
    got = set(
        store.con.execute(
            "SELECT metric, date, value FROM daily_series ORDER BY metric, date"
        ).fetchall()
    )
    assert got == {
        ("steps", date(2026, 6, 15), 500.0),
        ("distance_km", date(2026, 7, 2), 5.0),
        ("steps", date(2026, 7, 1), 111.0),
        ("steps", date(2026, 7, 2), 222.0),
    }


def test_replace_chunk_active_minutes_replaces_all_three_series_together(store):
    metric = by_name("active_minutes")
    assert metric.series_names == (
        "minutes_lightly_active",
        "minutes_fairly_active",
        "minutes_very_active",
    )
    start = date(2026, 7, 1)
    store.upsert_daily(
        [
            ("minutes_lightly_active", "2026-07-01", 10.0),
            ("minutes_fairly_active", "2026-07-01", 20.0),
            ("minutes_very_active", "2026-07-01", 30.0),
        ]
    )
    rows = ParsedRows(
        daily=(
            ("minutes_lightly_active", start, 11.0),
            ("minutes_fairly_active", start, 21.0),
            ("minutes_very_active", start, 31.0),
        )
    )
    store.replace_chunk(metric, start, start, [{"p": 0}], rows)
    got = dict(
        store.con.execute(
            "SELECT metric, value FROM daily_series WHERE date = ?", [start]
        ).fetchall()
    )
    assert got == {
        "minutes_lightly_active": 11.0,
        "minutes_fairly_active": 21.0,
        "minutes_very_active": 31.0,
    }


def test_replace_chunk_sleep_removes_upstream_deleted_sessions(store):
    metric = by_name("sleep")
    store.upsert_sleep([sleep_row("uuid-1", "2026-07-01"), sleep_row("uuid-2", "2026-07-02")])
    # a re-sync of the same wake-date range where upstream deleted uuid-1
    rows = ParsedRows(sleep=(sleep_row("uuid-2", "2026-07-02"),))
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 3), [{"p": 0}], rows)
    df = store.sleep_frame()
    assert list(df["provider_id"]) == ["uuid-2"]


def test_replace_chunk_intraday_replaces_only_target_days(store):
    metric = by_name("intraday_hr")  # series_names == ("hr",)
    store.upsert_intraday(
        [
            ("hr", "2026-07-01 00:00:00", 60.0),  # different day -> survives
            ("hr", "2026-07-02 00:00:00", 61.0),  # target day, stale -> replaced
        ]
    )
    rows = ParsedRows(intraday=(("hr", datetime(2026, 7, 2, 0, 1), 99.0),))
    store.replace_chunk(metric, date(2026, 7, 2), date(2026, 7, 2), [{"p": 0}], rows)
    got = sorted(store.con.execute("SELECT ts, value FROM intraday ORDER BY ts").fetchall())
    assert got == [
        (datetime(2026, 7, 1, 0, 0, 0), 60.0),
        (datetime(2026, 7, 2, 0, 1, 0), 99.0),
    ]


# -- replace_chunk: transaction + watermark semantics -------------------------


def test_replace_chunk_advances_watermark_only_on_success(store):
    metric = by_name("steps")
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 3), [{"p": 0}], ParsedRows())
    assert store.get_sync_state(metric.name) == date(2026, 7, 3)


def test_replace_chunk_empty_replacement_deletes_old_rows_and_still_advances_watermark(store):
    metric = by_name("steps")
    store.upsert_daily([("steps", "2026-07-01", 500.0), ("steps", "2026-08-01", 1.0)])
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 3), [], ParsedRows())
    df = store.daily_frame(["steps"])
    assert len(df) == 1  # the July row was deleted; the out-of-range August row survives
    assert store.get_sync_state(metric.name) == date(2026, 7, 3)
    n_raw = store.con.execute(
        "SELECT count(*) FROM raw_json WHERE metric = ?", [metric.name]
    ).fetchone()[0]
    assert n_raw == 0


def test_replace_chunk_delete_range_is_inclusive_of_both_boundaries(store):
    metric = by_name("steps")
    store.upsert_daily(
        [
            ("steps", "2026-06-30", 1.0),  # start - 1 -> survives
            ("steps", "2026-07-01", 2.0),  # start -> deleted
            ("steps", "2026-07-05", 3.0),  # end -> deleted
            ("steps", "2026-07-06", 4.0),  # end + 1 -> survives
        ]
    )
    store.replace_chunk(metric, date(2026, 7, 1), date(2026, 7, 5), [{"p": 0}], ParsedRows())
    got = {r[0] for r in store.con.execute("SELECT date FROM daily_series").fetchall()}
    assert got == {date(2026, 6, 30), date(2026, 7, 6)}


def test_replace_chunk_daily_then_intraday_same_series_name_no_cross_table_delete(store):
    # "steps" (daily rollup) and "intraday_steps" (reconcile intraday) share the
    # literal series name "steps" but write to different tables; one metric's
    # replace_chunk must never delete the other's rows.
    daily_metric = by_name("steps")
    intraday_metric = by_name("intraday_steps")
    assert daily_metric.series_names == intraday_metric.series_names == ("steps",)
    day = date(2026, 7, 10)

    store.replace_chunk(
        daily_metric, day, day, [{"p": 0}], ParsedRows(daily=(("steps", day, 1234.0),))
    )
    store.replace_chunk(
        intraday_metric,
        day,
        day,
        [{"p": 0}],
        ParsedRows(intraday=(("steps", datetime(2026, 7, 10, 8, 0), 50.0),)),
    )

    daily_rows = store.con.execute("SELECT metric, date, value FROM daily_series").fetchall()
    assert daily_rows == [("steps", day, 1234.0)]
    intraday_rows = store.con.execute("SELECT metric, ts, value FROM intraday").fetchall()
    assert intraday_rows == [("steps", datetime(2026, 7, 10, 8, 0), 50.0)]


def test_replace_chunk_intraday_then_daily_same_series_name_no_cross_table_delete(store):
    # same collision, opposite call order -- must be symmetric.
    daily_metric = by_name("steps")
    intraday_metric = by_name("intraday_steps")
    day = date(2026, 7, 10)

    store.replace_chunk(
        intraday_metric,
        day,
        day,
        [{"p": 0}],
        ParsedRows(intraday=(("steps", datetime(2026, 7, 10, 8, 0), 50.0),)),
    )
    store.replace_chunk(
        daily_metric, day, day, [{"p": 0}], ParsedRows(daily=(("steps", day, 1234.0),))
    )

    daily_rows = store.con.execute("SELECT metric, date, value FROM daily_series").fetchall()
    assert daily_rows == [("steps", day, 1234.0)]
    intraday_rows = store.con.execute("SELECT metric, ts, value FROM intraday").fetchall()
    assert intraday_rows == [("steps", datetime(2026, 7, 10, 8, 0), 50.0)]


def test_replace_chunk_rolls_back_raw_typed_and_watermark_on_failure(store):
    metric = by_name("steps")
    start, end = date(2026, 7, 1), date(2026, 7, 3)
    store.upsert_daily([("steps", "2026-07-01", 500.0)])
    store.set_sync_state(metric.name, date(2026, 6, 1))
    # a malformed date string makes the typed INSERT raise mid-transaction
    bad_rows = ParsedRows(daily=(("steps", "not-a-date", 1.0),))
    with pytest.raises(duckdb.Error):
        store.replace_chunk(metric, start, end, [{"p": 0}], bad_rows)
    n_raw = store.con.execute(
        "SELECT count(*) FROM raw_json WHERE metric = ?", [metric.name]
    ).fetchone()[0]
    assert n_raw == 0
    df = store.daily_frame(["steps"])
    assert len(df) == 1 and df.loc[0, "steps"] == 500.0
    assert store.get_sync_state(metric.name) == date(2026, 6, 1)
