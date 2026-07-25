from datetime import date, timedelta

import pytest
from health.auth import AuthError
from health.client import ApiError, RateLimited, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, RECONCILE, Metric, ParsedRows, PayloadError
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
    assert store.get_sync_checkpoint("test").status == SYNC_IN_PROGRESS
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
    assert store.get_sync_checkpoint("test").status == SYNC_IN_PROGRESS


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
    assert store.get_sync_checkpoint("test").status == SYNC_OK


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
    # 2026-07-18 falls in the aligned 90-day chunk 2026-05-14..2026-08-11,
    # requested clipped to [chunk start, today].
    assert client.calls[0][2:] == (date(2026, 5, 14), date(2026, 7, 20))


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
    # 2026-07-17 falls in the same aligned chunk as 2026-07-18.
    assert client.calls[0][2:] == (date(2026, 5, 14), date(2026, 7, 20))


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
    checkpoint = store.get_sync_checkpoint("test")
    assert checkpoint.last_synced == date(2026, 1, 1)
    assert checkpoint.status == SYNC_IN_PROGRESS

    second = FakeClient()
    SyncEngine(
        second,
        store,
        [metric(days=1)],
        today=date(2026, 1, 4),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        max_requests=1,
    ).sync_all()
    # An interrupted overlap window resumes at the day after the chunk it
    # actually completed, so it re-fetches every day in the window instead
    # of skipping the ones it had not reached yet.
    assert second.calls[0][2:] == (date(2026, 1, 2), date(2026, 1, 2))


def test_interrupted_trailing_overlap_refetches_every_day_in_the_window(store):
    """A `greatest()` watermark would let the resumed run skip past days the
    interrupted overlap pass never reached; the trailing-refetch window
    exists precisely to reconcile late-arriving values and upstream
    deletions in those days, so every one of them must be requested again
    across the resumed runs."""
    store.set_sync_state("test", date(2026, 1, 2), SYNC_OK)
    today = date(2026, 1, 10)
    client = FakeClient()

    for _ in range(20):  # generous cap; each capped run advances one day
        SyncEngine(
            client,
            store,
            [metric(days=1)],
            today=today,
            environ={"HEALTH_BACKFILL_START": "2026-01-01"},
            max_requests=1,
        ).sync_all()
        if store.get_sync_checkpoint("test").status == SYNC_OK:
            break
    else:
        pytest.fail("sync never reached SYNC_OK within the iteration budget")

    requested_days = {d for call in client.calls for d in call[2:4]}
    assert date(2026, 1, 2) in requested_days


def test_intraday_first_run_takes_the_recent_window_then_backfills(store):
    client = FakeClient()
    m = next(item for item in CATALOG if item.name == "intraday_hr")

    SyncEngine(client, store, [m], today=date(2026, 7, 20), environ={}, max_requests=50).sync_all()

    assert len(client.calls) == 30
    assert client.calls[0][2] == date(2026, 7, 14)  # recency pass runs first
    assert min(call[2] for call in client.calls) == date(2026, 6, 21)  # floor still reached
    assert store.get_sync_state("intraday_hr") == date(2026, 7, 20)


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


class FailingClient(FakeClient):
    """Fails every send for one metric, succeeds for the others."""

    def __init__(self, failing_metric, error):
        super().__init__()
        self.failing_metric = failing_metric
        self.error = error

    def _send(self, method, metric_, start, end, budget, payload):
        if metric_.name == self.failing_metric:
            budget.consume()
            raise self.error
        return super()._send(method, metric_, start, end, budget, payload)


def test_api_error_isolates_one_metric_and_continues(store):
    client = FailingClient("first", ApiError(403, "insufficient scope", code=403))
    report = SyncEngine(
        client,
        store,
        [metric(name="first"), metric(name="second")],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()

    assert [f.metric for f in report.failures] == ["first"]
    assert report.failures[0].kind == "api"
    assert report.failures[0].status_code == 403
    assert [call[1] for call in client.calls] == ["second"]
    assert store.get_sync_state("second") == date(2026, 1, 1)
    assert store.get_sync_state("first") is None
    assert report.progress[0].done is False
    assert report.progress[1].done is True


def test_payload_error_isolates_one_metric_and_continues(store):
    def explode(_pages):
        raise PayloadError("first", "rollupDataPoint missing civilStartTime.date")

    report = SyncEngine(
        FakeClient(),
        store,
        [metric(name="first", parser=explode), metric(name="second")],
        today=date(2026, 1, 1),
        environ={"HEALTH_BACKFILL_START": "2026-01-01"},
    ).sync_all()

    assert [f.metric for f in report.failures] == ["first"]
    assert report.failures[0].kind == "payload"
    assert store.get_sync_state("second") == date(2026, 1, 1)
    assert store.get_sync_state("first") is None
    assert report.progress[0].done is False
    assert report.progress[1].done is True


class FailingAfterNCallsClient(FakeClient):
    """Succeeds on a metric's first `succeed_calls` sends, then fails every
    later send for that metric with `error`. Other metrics are unaffected.
    Models a metric whose recency window spans more than one aligned chunk
    and starts failing partway through it."""

    def __init__(self, failing_metric, error, succeed_calls):
        super().__init__()
        self.failing_metric = failing_metric
        self.error = error
        self.succeed_calls = succeed_calls
        self._failing_metric_calls = 0

    def _send(self, method, metric_, start, end, budget, payload):
        if metric_.name == self.failing_metric:
            self._failing_metric_calls += 1
            if self._failing_metric_calls > self.succeed_calls:
                budget.consume()
                raise self.error
        return super()._send(method, metric_, start, end, budget, payload)


def test_metric_abandoned_mid_recency_pass_is_not_retried_in_history_pass(store):
    """A metric that fails on a later recency chunk -- after an earlier one
    already gave it a usable backfilled_from -- must stay abandoned for the
    rest of the run. Before the fix, `_history_pass` only checked whether a
    checkpoint/backfilled_from existed, so it retried (and re-failed) this
    same metric a moment later, producing a duplicate MetricFailure and a
    wasted request."""
    client = FailingAfterNCallsClient("flaky", ApiError(500, "boom", code=500), succeed_calls=1)
    catalog = [metric(name="flaky", days=1), metric(name="healthy", days=1)]

    report = SyncEngine(
        client,
        store,
        catalog,
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-06-01"},
        max_requests=60,
    ).sync_all()

    # At most one failure for "flaky" this run -- not one per pass.
    assert [f.metric for f in report.failures] == ["flaky"]

    flaky_calls = [call for call in client.calls if call[1] == "flaky"]
    assert len(flaky_calls) == 1  # only the one recency chunk that succeeded
    assert not any(p.metric == "flaky" and p.done for p in report.progress)

    # The healthy metric is unaffected: it finishes its recency pass and
    # still walks history in the same run.
    healthy_calls = [call for call in client.calls if call[1] == "healthy"]
    assert len(healthy_calls) > 7  # more than the 7-day recency window alone
    assert any(p.metric == "healthy" and p.done for p in report.progress)


def test_auth_error_stops_the_whole_run(store):
    client = FailingClient("first", AuthError("token revoked"))

    with pytest.raises(AuthError):
        SyncEngine(
            client,
            store,
            [metric(name="first"), metric(name="second")],
            today=date(2026, 1, 1),
            environ={"HEALTH_BACKFILL_START": "2026-01-01"},
        ).sync_all()

    assert store.get_sync_state("second") is None


def test_daily_syncs_reuse_one_raw_chunk_key(store):
    """The review's finding: five daily syncs used to leave six raw rows."""
    m = metric(days=90)
    for offset in range(5):
        SyncEngine(
            FakeClient(),
            store,
            [m],
            today=date(2026, 7, 20) + timedelta(days=offset),
            environ={"HEALTH_BACKFILL_START": "2026-07-01"},
        ).sync_all()

    ranges = store.con.execute(
        "SELECT DISTINCT range_start, range_end FROM raw_json WHERE metric = 'test'"
    ).fetchall()
    assert len(ranges) == 1


def test_typed_rows_outside_a_narrowed_refetch_survive_inside_the_same_chunk(store):
    """Reviewer's reproduction: a floor that advances forward (either via
    HEALTH_BACKFILL_START or the default "five years ago today" rolling
    forward one day per run) narrows the request on the next sync, but stays
    inside the same aligned 90-day chunk. Days no longer covered by the
    request must not lose their previously-synced typed rows."""

    class DateEchoClient(FakeClient):
        def daily_rollup(self, metric_, start, end, budget):
            payload = {"start": start.isoformat(), "end": end.isoformat()}
            return self._send("rollup", metric_, start, end, budget, payload)

    def one_row_per_requested_day(pages):
        payload = pages[0]
        start = date.fromisoformat(payload["start"])
        end = date.fromisoformat(payload["end"])
        out = []
        d = start
        while d <= end:
            out.append(("test", d, 1.0))
            d += timedelta(days=1)
        return ParsedRows(daily=tuple(out))

    m = metric(days=90, parser=one_row_per_requested_day)

    SyncEngine(
        DateEchoClient(),
        store,
        [m],
        today=date(2025, 1, 20),
        environ={"HEALTH_BACKFILL_START": "2025-01-01"},
    ).sync_all()

    SyncEngine(
        DateEchoClient(),
        store,
        [m],
        today=date(2025, 1, 21),
        environ={"HEALTH_BACKFILL_START": "2025-01-10"},
    ).sync_all()

    dates = {
        row[0]
        for row in store.con.execute(
            "SELECT date FROM daily_series WHERE metric = 'test'"
        ).fetchall()
    }
    for day in range(1, 10):
        assert date(2025, 1, day) in dates


def test_first_run_covers_every_metric_before_any_history(store):
    catalog = [metric(name=f"m{i}", days=90) for i in range(4)]
    client = FakeClient()

    SyncEngine(
        client,
        store,
        catalog,
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=4,
    ).sync_all()

    # With a budget of exactly one request per metric, every metric gets its
    # recent window; none of it is spent on one metric's history.
    assert [call[1] for call in client.calls] == ["m0", "m1", "m2", "m3"]
    for item in catalog:
        assert store.get_sync_state(item.name) == date(2026, 7, 20)


def test_history_walks_backward_round_robin_after_the_recent_pass(store):
    catalog = [metric(name="a", days=90), metric(name="b", days=90)]
    client = FakeClient()

    SyncEngine(
        client,
        store,
        catalog,
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=6,
    ).sync_all()

    names = [call[1] for call in client.calls]
    assert names[:2] == ["a", "b"]  # recency pass
    assert names[2:] == ["a", "b", "a", "b"]  # history, one chunk each per round
    # Two history rounds walk 2026-05-14 back through 2026-02-13 to 2025-11-15.
    assert store.get_sync_checkpoint("a").backfilled_from == date(2025, 11, 15)
    assert store.get_sync_state("a") == date(2026, 7, 20)  # watermark not dragged back


def test_history_stops_at_the_configured_floor(store):
    client = FakeClient()
    engine = SyncEngine(
        client,
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-06-01"},
        max_requests=50,
    )

    report = engine.sync_all()

    assert report.history_remaining == {"test": 0}
    # The aligned chunk holding today (2026-05-14..2026-08-11) already starts
    # before the floor, so there is no history left to walk.
    assert store.get_sync_checkpoint("test").backfilled_from <= date(2026, 6, 1)
    assert len(client.calls) == 1


def test_report_counts_remaining_history_chunks(store):
    report = SyncEngine(
        FakeClient(),
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2021-07-20"},
        max_requests=1,
    ).sync_all()

    # 2021-07-20..2026-05-18 still missing, in 90-day aligned chunks.
    assert report.history_remaining["test"] == 20


def test_request_range_is_clipped_to_floor_and_today(store):
    client = FakeClient()
    SyncEngine(
        client,
        store,
        [metric(days=90)],
        today=date(2026, 7, 20),
        environ={"HEALTH_BACKFILL_START": "2026-07-01"},
    ).sync_all()

    _, _, request_start, request_end = client.calls[0]
    assert request_start == date(2026, 7, 1)  # never older than the floor
    assert request_end == date(2026, 7, 20)  # never in the future
    assert store.get_sync_state("test") == date(2026, 7, 20)  # watermark is the clipped end
