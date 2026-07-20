from datetime import date

import pytest

from health.inventory import build_inventory
from health.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_inventory_lists_all_catalog_metrics_even_empty(store):
    inv = build_inventory(store)
    assert (inv["source"] == "catalog").sum() >= 15
    steps = inv[inv["metric"] == "steps"].iloc[0]
    assert steps["n_days"] == 0 and steps["last_synced"] is None


def test_inventory_merges_stats_and_state(store):
    store.upsert_daily([("spo2_avg", "2026-07-01", 96.0), ("spo2_avg", "2026-07-02", 95.5)])
    store.set_sync_state("spo2", date(2026, 7, 2))
    inv = build_inventory(store).set_index("metric")
    assert inv.loc["spo2", "status"] == "ok"
    assert inv.loc["spo2_avg", "source"] == "derived"
    assert inv.loc["spo2_avg", "n_days"] == 2
