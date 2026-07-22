from datetime import date, datetime

import pytest
from health.endpoints import CATALOG, KNOWN_DATA_TYPES, ParsedRows
from health.inventory import (
    PUBLISHED_COLUMNS,
    STORED_COLUMNS,
    build_inventory,
    build_series_inventory,
)
from health.store import Store


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / "health.duckdb")
    yield result
    result.close()


def catalog_metric(name):
    return next(metric for metric in CATALOG if metric.name == name)


def test_inventory_lists_every_published_type_with_implemented_flag(store):
    inventory = build_inventory(store)
    assert list(inventory.columns) == PUBLISHED_COLUMNS
    assert set(inventory["data_type"]) == set(KNOWN_DATA_TYPES)
    assert inventory["implemented"].dtype == bool


def test_only_catalog_data_types_are_implemented(store):
    inventory = build_inventory(store).set_index("data_type")
    implemented = {metric.data_type for metric in CATALOG}
    assert set(inventory.index[inventory["implemented"]]) == implemented
    assert not inventory.loc["blood-glucose", "implemented"]
    assert inventory.loc["steps", "metrics"] == "steps, intraday_steps"


def test_multi_series_catalog_entry_has_stats_for_each_series(store):
    store.upsert_daily(
        [
            ("minutes_lightly_active", "2026-07-01", 10),
            ("minutes_fairly_active", "2026-07-01", 20),
            ("minutes_very_active", "2026-07-01", 30),
        ]
    )
    rows = build_series_inventory(store)
    active = rows[rows["metric"] == "active_minutes"].set_index("series")
    assert set(active.index) == {
        "minutes_lightly_active",
        "minutes_fairly_active",
        "minutes_very_active",
    }
    assert (active["n"] == 1).all()


def test_daily_sleep_intraday_and_raw_stats(store):
    day = date(2026, 7, 1)
    sleep_row = {
        "provider_id": "sleep-abc",
        "date": day,
        "start_ts": datetime(2026, 6, 30, 23),
        "end_ts": datetime(2026, 7, 1, 7),
        "minutes_asleep": 420,
        "minutes_deep": 0,
        "minutes_light": 0,
        "minutes_rem": 0,
        "minutes_wake": 0,
        "efficiency": 90,
        "is_main": True,
    }
    store.replace_chunk(
        catalog_metric("sleep"),
        day,
        day,
        [{"dataPoints": []}, {"dataPoints": []}],
        ParsedRows(daily=(("sleep_minutes", day, 420),), sleep=(sleep_row,)),
    )
    store.replace_chunk(
        catalog_metric("intraday_hr"),
        day,
        day,
        [{"dataPoints": []}],
        ParsedRows(intraday=(("hr", datetime(2026, 7, 1, 12), 65),)),
    )

    rows = build_series_inventory(store).set_index(["metric", "series"])
    assert rows.loc[("sleep", "sleep_minutes"), "n"] == 1
    assert rows.loc[("sleep", "sleep_sessions"), "n"] == 1
    assert rows.loc[("sleep", "sleep_sessions"), "storage"] == "sleep"
    assert rows.loc[("intraday_hr", "hr"), "n"] == 1
    assert rows.loc[("sleep", "sleep_minutes"), "n_raw_pages"] == 2
    assert rows.loc[("sleep", "sleep_minutes"), "raw_first_range"].date() == day
    assert rows.loc[("sleep", "sleep_minutes"), "raw_last_range"].date() == day


def test_empty_inventory_has_stable_columns_and_zero_counts(store):
    published = build_inventory(store)
    stored = build_series_inventory(store)
    assert list(published.columns) == PUBLISHED_COLUMNS
    assert list(stored.columns) == STORED_COLUMNS
    assert not published.empty and not stored.empty
    assert (stored["n"] == 0).all()
    assert (stored["n_raw_pages"] == 0).all()
