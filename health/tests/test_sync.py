from datetime import date

import pytest

from health.client import RateLimited
from health.endpoints import CATALOG, Metric, ParsedRows
from health.store import Store
from health.sync import SyncEngine


class FakeClient:
    """Scripted FitbitClient stand-in: returns {} and records paths."""

    def __init__(self, remaining=100, fail_after=None):
        self.calls = []
        self.remaining = remaining
        self.reset_s = 1800
        self.fail_after = fail_after  # raise RateLimited after N calls

    def get(self, path):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise RateLimited(900)
        self.calls.append(path)
        if path.endswith("/profile.json"):
            return {"user": {"memberSince": "2026-05-01"}}
        return {}


def steps_only():
    m = next(m for m in CATALOG if m.name == "steps")
    return [m]


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.close()


def test_backfill_uses_member_since_and_sets_state(store):
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20))
    report = engine.sync_all()
    assert client.calls[0].endswith("/profile.json")
    assert "/date/2026-05-01/2026-07-20.json" in client.calls[1]
    assert store.get_sync_state("steps") == date(2026, 7, 20)
    assert report.progress[0].done and not report.paused


def test_incremental_refetches_trailing_3_days(store):
    store.set_sync_state("steps", date(2026, 7, 19))
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all()
    assert "/date/2026-07-17/2026-07-20.json" in client.calls[0]


def test_up_to_date_metric_skips_requests(store):
    # fully synced through today: only the trailing refetch window remains
    store.set_sync_state("steps", date(2026, 7, 20))
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all()
    assert "/date/2026-07-18/2026-07-20.json" in client.calls[0]


def test_trailing_metric_starts_30_days_back(store):
    m = next(m for m in CATALOG if m.name == "intraday_hr")
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2020, 1, 1))
    engine.sync_all()
    assert "/date/2026-06-21/1d/1min.json" in client.calls[0]
    assert len(client.calls) == 30  # one per day
    assert store.get_sync_state("intraday_hr") == date(2026, 7, 20)


def test_budget_exhaustion_pauses_and_resumes(store):
    client = FakeClient(remaining=3)  # below min_budget after first check
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    report = engine.sync_all(min_budget=5)
    assert report.paused and report.resume_in_s == 1800
    assert client.calls == []  # stopped before any fetch


def test_rate_limited_mid_run_pauses_with_retry_after(store):
    m = next(m for m in CATALOG if m.name == "intraday_hr")
    client = FakeClient(fail_after=5)
    engine = SyncEngine(client, store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2020, 1, 1))
    report = engine.sync_all()
    assert report.paused and report.resume_in_s == 900
    # progress persisted: 5 days done -> resume window starts near there
    assert store.get_sync_state("intraday_hr") == date(2026, 6, 25)


def test_progress_callback_invoked(store):
    seen = []
    client = FakeClient()
    engine = SyncEngine(client, store, catalog=steps_only(), today=date(2026, 7, 20),
                        member_since=date(2026, 5, 1))
    engine.sync_all(progress_cb=lambda metric, msg: seen.append((metric, msg)))
    assert seen and seen[0][0] == "steps"


def test_parsed_rows_are_stored(store):
    parsed = ParsedRows(daily=[("steps", "2026-07-19", 1.0)])
    m = Metric("steps", "/1/user/-/activities/steps/date/{start}/{end}.json",
               "range", 1095, "activity", True, lambda payload: parsed)
    engine = SyncEngine(FakeClient(), store, catalog=[m], today=date(2026, 7, 20),
                        member_since=date(2026, 7, 1))
    engine.sync_all()
    assert not store.daily_frame(["steps"]).empty
