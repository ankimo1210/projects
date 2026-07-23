from datetime import date

import pytest
from health.client import RateLimited, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, RECONCILE, Metric, ParsedRows
from health.store import SYNC_IN_PROGRESS, SYNC_OK, Store
from health.sync import SyncEngine, backfill_start


def metric(name="test", method=DAILY_ROLLUP, days=90, full_history=True, parser=None):
    return Metric(
        name=name,
        data_type=name,
        method=method,
        max_range_days=days,
        scope="scope",
        full_history=full_history,
        series_names=(name,),
        parse_pages=parser or (lambda pages: ParsedRows()),
        filter_path="value.date" if method == RECONCILE else None,
    )


class FakeClient:
    def __init__(self, pages=None, rate_limit_at=None):
        self.pages = pages or [{}]
        self.rate_limit_at = rate_limit_at
        self.calls = []

    def _send(self, method, metric_, start, end, budget, payload):
        if self.rate_limit_at == len(self.calls):
            budget.consume()
            raise RateLimited(429, "slow down", 90)
        budget.consume()
        self.calls.append((method, metric_.name, start, end))
        return payload

    def daily_rollup(self, metric_, start, end, budget):
        return self._send("rollup", metric_, start, end, budget, self.pages[0])

    def iter_reconciled(self, metric_, start, end, budget):
        for page in self.pages:
            yield self._send("reconcile", metric_, start, end, budget, page)


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / "health.duckdb")
    yield result
    result.close()


def test_backfill_override_and_validation():
    today = date(2026, 7, 20)
    assert backfill_start(today, {"HEALTH_BACKFILL_START": "2024-01-02"}) == date(2024, 1, 2)
    with pytest.raises(ValueError, match="ISO date"):
        backfill_start(today, {"HEALTH_BACKFILL_START": "yesterday"})
    with pytest.raises(ValueError, match="future"):
        backfill_start(today, {"HEALTH_BACKFILL_START": "2026-07-21"})


def test_default_backfill_is_five_calendar_years_and_rounds_leap_day():
    assert backfill_start(date(2026, 7, 20), {}) == date(2021, 7, 20)
    assert backfill_start(date(2024, 2, 29), {}) == date(2019, 2, 28)


@pytest.mark.parametrize(("days", "expected"), [(14, 3), (90, 1)])
def test_rollup_chunking(store, days, expected):
    client = FakeClient()
    engine = SyncEngine(
        client,
        store,
        [metric(days=days)],
        today=date(2026, 1, 31),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    )
    report = engine.sync_all()
    assert len(client.calls) == expected
    assert report.progress[0].fetched_ranges == expected


def test_reconcile_buffers_all_pages_and_replaces_once(store, monkeypatch):
    seen = []
    pages = [{"dataPoints": [1]}, {"dataPoints": [2]}]
    m = metric(
        method=RECONCILE,
        parser=lambda received: seen.append(received) or ParsedRows(),
    )
    replacements = []
    monkeypatch.setattr(
        store, "replace_chunk", lambda *args, **kwargs: replacements.append((args, kwargs))
    )
    SyncEngine(
        FakeClient(pages),
        store,
        [m],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    assert seen == [pages]
    assert len(replacements) == 1
    assert replacements[0][0][3] == pages
    assert replacements[0][1]["status"] == SYNC_OK


def test_parser_failure_does_not_replace_or_advance_watermark(store, monkeypatch):
    def fail(_pages):
        raise ValueError("bad payload")

    called = False

    def replace(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(store, "replace_chunk", replace)
    engine = SyncEngine(
        FakeClient(),
        store,
        [metric(parser=fail)],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    )
    with pytest.raises(ValueError, match="bad payload"):
        engine.sync_all()
    assert not called
    assert store.get_sync_state("test") is None


def test_429_keeps_only_completed_chunks(store):
    client = FakeClient(rate_limit_at=1)
    m = metric(days=1)
    report = SyncEngine(
        client,
        store,
        [m],
        today=date(2026, 1, 2),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    assert report.paused and report.resume_in_s == 90
    assert report.requests_made == 2
    assert store.get_sync_state("test") == date(2026, 1, 1)
    assert store.get_sync_checkpoint("test")[1] == SYNC_IN_PROGRESS
    assert len(store.raw_stats()) == 1


def test_hard_cap_between_rollup_chunks(store):
    report = SyncEngine(
        FakeClient(),
        store,
        [metric(days=1)],
        today=date(2026, 1, 2),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        max_requests=1,
    ).sync_all()
    assert report.stopped_early and report.requests_made == 1
    assert store.get_sync_state("test") == date(2026, 1, 1)
    assert store.get_sync_checkpoint("test")[1] == SYNC_IN_PROGRESS


def test_hard_cap_during_paging_does_not_save_partial_chunk(store):
    report = SyncEngine(
        FakeClient([{"page": 1}, {"page": 2}]),
        store,
        [metric(method=RECONCILE)],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        max_requests=1,
    ).sync_all()
    assert report.stopped_early and report.requests_made == 1
    assert store.get_sync_state("test") is None
    assert store.raw_stats().empty


def test_second_run_resumes_at_first_unfinished_chunk(store):
    kwargs = {
        "catalog": [metric(days=1)],
        "today": date(2026, 1, 2),
        "environ": {"HEALTH_BACKFILL_START": "2026-01-01"},
        "max_requests": 1,
    }
    SyncEngine(FakeClient(), store, **kwargs).sync_all()
    second = FakeClient()
    report = SyncEngine(second, store, **kwargs).sync_all()
    assert second.calls[0][2:] == (date(2026, 1, 2), date(2026, 1, 2))
    assert report.progress[0].done
    assert store.get_sync_state("test") == date(2026, 1, 2)
    assert store.get_sync_checkpoint("test")[1] == SYNC_OK


def test_completed_metric_refetches_trailing_three_days(store):
    store.set_sync_state("test", date(2026, 7, 20))
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric()],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    assert client.calls[0][2:] == (date(2026, 7, 18), date(2026, 7, 20))


def test_completed_metric_refetches_from_previous_watermark_on_next_day(store):
    store.set_sync_state("test", date(2026, 7, 19), SYNC_OK)
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric()],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    assert client.calls[0][2:] == (date(2026, 7, 17), date(2026, 7, 20))


def test_legacy_ok_checkpoint_becomes_resumable_after_first_overlap_chunk(store):
    store.set_sync_state("test", date(2026, 1, 2), SYNC_OK)
    first = FakeClient()
    report = SyncEngine(
        first,
        store,
        [metric(days=1)],
        today=date(2026, 1, 4),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        max_requests=1,
    ).sync_all()
    assert report.stopped_early
    assert first.calls[0][2:] == (date(2026, 1, 1), date(2026, 1, 1))
    assert store.get_sync_checkpoint("test") == (date(2026, 1, 1), SYNC_IN_PROGRESS)

    second = FakeClient()
    SyncEngine(
        second,
        store,
        [metric(days=1)],
        today=date(2026, 1, 4),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        max_requests=1,
    ).sync_all()
    assert second.calls[0][2:] == (date(2026, 1, 2), date(2026, 1, 2))


def test_intraday_initial_sync_is_last_thirty_days(store):
    client = FakeClient()
    m = next(item for item in CATALOG if item.name == "intraday_hr")
    SyncEngine(client, store, [m], today=date(2026, 7, 20), environ={}).sync_all()
    assert len(client.calls) == 30
    assert client.calls[0][2] == date(2026, 6, 21)
    assert client.calls[-1][3] == date(2026, 7, 20)


def test_empty_response_replaces_stale_rows_and_advances_watermark(store):
    m = metric()
    store.upsert_daily([("test", date(2026, 1, 1), 5.0)])
    SyncEngine(
        FakeClient([{}]),
        store,
        [m],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()
    assert store.daily_frame(["test"]).empty
    assert store.get_sync_state("test") == date(2026, 1, 1)


def test_progress_callback_reports_metric_range_and_request_count(store):
    seen = []
    SyncEngine(
        FakeClient(),
        store,
        [metric()],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all(lambda name, message: seen.append((name, message)))
    assert seen == [("test", "2026-01-01 → 2026-01-01 (1 requests)")]


def test_unexpected_request_cap_error_type_is_not_an_api_error():
    assert not issubclass(RequestCapExceeded, RateLimited)
