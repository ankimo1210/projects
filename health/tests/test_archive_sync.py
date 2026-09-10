import json
from dataclasses import replace
from datetime import date

import pytest
from health.archive import Archive
from health.archive_index import ArchiveIndex
from health.archive_sync import ArchiveEngine
from health.client import ApiError, RateLimited, RequestBudget
from health.source_catalog import load_sources
from health.store import Store


class Client:
    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def request_page(self, request, budget, *, capture=None):
        budget.consume()
        self.requests.append(request)
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            capture(b'{"error":{}}', getattr(page, "status_code", 500))
            raise page
        capture(json.dumps(page).encode(), 200)
        return page


def source():
    base = next(
        s for s in load_sources() if s.data_type == "heart-rate" and s.preferred_method == "list"
    )
    return replace(base, unbounded_verified=True)


def engine(tmp_path, client, sources=None):
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    return (
        store,
        index,
        ArchiveEngine(
            client,
            Archive(tmp_path / "archive"),
            index,
            sources or [source()],
            today=date(2026, 9, 7),
        ),
    )


def test_restarts_mid_pagination_without_claiming_complete(tmp_path):
    client = Client(
        [
            {"dataPoints": [{"name": "a"}], "nextPageToken": "second"},
            {"dataPoints": [{"name": "b"}]},
        ]
    )
    store, index, sync = engine(tmp_path, client)
    report = sync.sync(RequestBudget(1))
    assert report.remaining == 1
    assert index.coverage()[0]["status"] == "partial"
    store.close()
    store, index, resumed = engine(tmp_path, client)
    report = resumed.sync(RequestBudget(1))
    assert report.remaining == 0
    assert client.requests[1].params["pageToken"] == "second"
    assert "filter" not in client.requests[0].params
    assert index.coverage()[0]["points"] == 2
    assert index.coverage()[0]["history_complete"] is True
    store.close()


def test_failure_does_not_hide_success_from_another_source(tmp_path):
    a = replace(source(), key="a")
    b = replace(source(), key="b")
    client = Client([ApiError(403, "sensitive upstream text"), {"dataPoints": []}])
    store, index, sync = engine(tmp_path, client, [a, b])
    report = sync.sync(RequestBudget(5))
    statuses = {r["stream_id"]: r["status"] for r in index.coverage()}
    assert statuses == {"a": "permission_denied", "b": "empty"}
    assert report.failures and "sensitive upstream text" not in str(report.failures)
    store.close()


def test_repeated_token_is_failed_instead_of_looping(tmp_path):
    client = Client(
        [{"dataPoints": [], "nextPageToken": "same"}, {"dataPoints": [], "nextPageToken": "same"}]
    )
    store, index, sync = engine(tmp_path, client)
    report = sync.sync(RequestBudget(10))
    assert len(client.requests) == 2
    assert index.coverage()[0]["status"] == "failed"
    assert report.remaining == 1
    store.close()


def test_pages_are_scheduled_fairly_before_continuations(tmp_path):
    client = Client([{"dataPoints": [], "nextPageToken": "a2"}, {"dataPoints": []}])
    store, index, sync = engine(
        tmp_path, client, [replace(source(), key="a"), replace(source(), key="b")]
    )
    sync.sync(RequestBudget(2))
    statuses = {r["stream_id"]: r["status"] for r in index.coverage()}
    assert statuses == {"a": "partial", "b": "empty"}
    store.close()


def test_unverified_unbounded_response_is_not_all_history_proof(tmp_path):
    client = Client([{"dataPoints": []}])
    store, index, sync = engine(tmp_path, client, [replace(source(), unbounded_verified=False)])
    sync.sync(RequestBudget(1))
    assert index.coverage()[0]["history_complete"] is False
    assert index.coverage()[0]["status"] == "unknown_history"
    store.close()


def test_rate_limit_retains_received_error_body_and_stops(tmp_path):
    client = Client([RateLimited(429, "wait", 30)])
    store, index, sync = engine(tmp_path, client)
    report = sync.sync(RequestBudget(10))
    assert report.stopped_reason == "rate_limited"
    assert index.coverage()[0]["pages"] == 1
    assert len(list((tmp_path / "archive/objects").glob("*.json.gz"))) == 1
    store.close()


def test_storage_failure_stops_without_advancing_cursor(tmp_path, monkeypatch):
    client = Client([{"dataPoints": []}])
    store, index, sync = engine(tmp_path, client)

    def full(*args):
        raise OSError("disk full")

    monkeypatch.setattr(sync.archive, "put", full)
    report = sync.sync(RequestBudget(10))
    assert report.stopped_reason == "storage_error"
    assert index.coverage()[0]["status"] == "storage_error"
    assert index.work(source().key)["page_token"] is None
    store.close()


def test_detail_jobs_resume_and_prototype_reports_completion(tmp_path):
    sources = load_sources()
    parent = replace(next(s for s in sources if s.key == "weight.list"), unbounded_verified=True)
    detail = next(s for s in sources if s.key == "weight.get")
    name = "users/me/dataTypes/weight/dataPoints/one"
    client = Client([{"dataPoints": [{"name": name}]}, {"name": name, "weight": {"kg": 70}}])
    store, index, sync = engine(tmp_path, client, [parent, detail])
    sync.sync(RequestBudget(1))
    assert next(r for r in index.coverage() if r["stream_id"] == detail.key)["status"] == "partial"
    store.close()
    store, index, sync = engine(tmp_path, client, [parent, detail])
    sync.sync(RequestBudget(1))
    row = next(r for r in index.coverage() if r["stream_id"] == detail.key)
    assert row["status"] == "complete"
    assert row["history_complete"] is True
    assert row["pages"] == 1
    assert client.requests[-1].path.endswith("/dataPoints/one")
    store.close()


def test_empty_parent_proves_no_detail_jobs_only_when_history_verified(tmp_path):
    sources = load_sources()
    parent = replace(next(s for s in sources if s.key == "weight.list"), unbounded_verified=True)
    detail = next(s for s in sources if s.key == "weight.get")
    store, index, sync = engine(tmp_path, Client([{"dataPoints": []}]), [parent, detail])
    sync.sync(RequestBudget(1))
    row = next(r for r in index.coverage() if r["stream_id"] == detail.key)
    assert row["status"] == "empty"
    assert row["history_complete"] is True
    store.close()


def weight_sources():
    sources = load_sources()
    return [
        replace(next(s for s in sources if s.key == "weight.list"), unbounded_verified=True),
        next(s for s in sources if s.key == "weight.get"),
    ]


@pytest.mark.parametrize("restart", [False, True])
@pytest.mark.parametrize("rescan", [False, True])
def test_detail_queue_write_failure_can_resume(tmp_path, monkeypatch, restart, rescan):
    sources = weight_sources()
    name = "users/me/dataTypes/weight/dataPoints/one"
    parent_page = {"dataPoints": [{"name": name}]}
    client = Client([parent_page, parent_page, {"name": name, "weight": {"kg": 70}}])
    store, index, sync = engine(tmp_path, client, sources)
    start = index.start

    def fail_detail_start(key, *args, **kwargs):
        if ".resource." in key:
            raise OSError("disk full after detail registration")
        return start(key, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(index, "start", fail_detail_start)
        assert sync.sync(RequestBudget(3)).stopped_reason == "storage_error"
    assert not any(".resource." in key for key in sync.sources)
    assert (
        store.con.execute(
            "SELECT count(*) FROM archive_sources WHERE stream_id LIKE '%.resource.%'"
        ).fetchone()[0]
        == 0
    )
    if restart:
        store.close()
        store, index, sync = engine(tmp_path, client, sources)
    report = sync.sync(RequestBudget(3), rescan=rescan)
    assert report.remaining == 0
    assert [request.path for request in client.requests].count("/v4/" + name) == 1
    assert (
        next(r for r in index.coverage() if r["stream_id"] == "weight.get")["history_complete"]
        is True
    )
    store.close()


@pytest.mark.parametrize("rescan", [False, True])
def test_registered_detail_without_work_is_repaired_on_rediscovery(tmp_path, rescan):
    sources = weight_sources()
    name = "users/me/dataTypes/weight/dataPoints/one"
    client = Client([{"dataPoints": [{"name": name}]}, {"name": name}])
    store, index, _ = engine(tmp_path, client, sources)
    index.register(replace(sources[1], key="weight.get.resource.3d6bb04d7a9f11e76be93375"))
    store.close()
    store, index, sync = engine(tmp_path, client, sources)
    report = sync.sync(RequestBudget(3), rescan=rescan)
    assert report.remaining == 0
    assert client.requests[-1].path == "/v4/" + name
    store.close()


@pytest.mark.parametrize(
    "bad_point", [{"weight": {"kg": 71}}, {"name": "https://invalid.example/"}]
)
def test_missing_detail_id_survives_resume_until_successful_rescan(tmp_path, bad_point):
    sources = weight_sources()
    one = "users/me/dataTypes/weight/dataPoints/one"
    two = "users/me/dataTypes/weight/dataPoints/two"
    client = Client(
        [
            {"dataPoints": [{"name": one}, bad_point], "nextPageToken": "next"},
            {"name": one},
            {"dataPoints": []},
        ]
    )
    store, index, sync = engine(tmp_path, client, sources)
    sync.sync(RequestBudget(1))
    store.close()
    store, index, sync = engine(tmp_path, client, sources)
    report = sync.sync(RequestBudget(2))
    row = next(r for r in index.coverage() if r["stream_id"] == "weight.get")
    assert row["status"] == "unknown_history"
    assert row["history_complete"] is False
    assert any(r["stream_id"] == "weight.get" for r in report.failures)
    assert client.requests[-1].params["pageToken"] == "next"
    store.close()

    client = Client([{"dataPoints": [{"name": one}, {"name": two}]}, {"name": one}, {"name": two}])
    store, index, sync = engine(tmp_path, client, sources)
    assert (
        next(r for r in index.coverage() if r["stream_id"] == "weight.get")["history_complete"]
        is False
    )
    report = sync.sync(RequestBudget(3), rescan=True)
    row = next(r for r in index.coverage() if r["stream_id"] == "weight.get")
    assert row["status"] == "complete"
    assert row["history_complete"] is True
    assert report.remaining == 0
    store.close()
