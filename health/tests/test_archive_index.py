from types import SimpleNamespace

import pytest
from health.archive import Archive
from health.archive_index import ArchiveIndex
from health.store import Store


def source():
    return SimpleNamespace(
        key="heart-rate:list",
        data_type="heart-rate",
        label="Heart rate",
        preferred_method="list",
        representation="source",
        availability="candidate",
    )


def test_previous_complete_interval_survives_later_failure(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    index.register(source())
    archive = Archive(tmp_path / "archive")
    request = {"range_start": "2020-01-01", "range_end": "2020-01-02", "params": {}}
    success = index.start(source().key, request, "source")
    index.record_page(success, 0, archive.put(b'{"dataPoints":[{}]}'), 200, 1)
    index.confirm_terminal(success, next_page_token=None)
    index.finish(success, "complete")
    failure = index.start(source().key, {**request, "range_start": "2020-01-03"}, "source")
    index.record_page(failure, 0, archive.put(b'{"error":403}'), 403, 0)
    index.finish(failure, "permission_denied", "Readonly scope not granted", http_status=403)
    row = index.coverage()[0]
    assert row["status"] == "permission_denied"
    assert row["http_status"] == 403
    assert row["history_complete"] is False
    assert row["intervals"] == [{"start": "2020-01-01", "end": "2020-01-02", "status": "complete"}]
    store.close()


def test_cursor_and_page_survive_reopening_database(tmp_path):
    path = tmp_path / "health.duckdb"
    store = Store(path)
    index = ArchiveIndex(store.con)
    index.register(source())
    request = {"params": {"filter": "fixed"}}
    attempt = index.start(source().key, request, "source")
    ref = Archive(tmp_path / "archive").put(b'{"dataPoints":[],"nextPageToken":"next"}')
    index.record_page(attempt, 0, ref, 200, 0)
    index.save_cursor(source().key, request, "next", attempt)
    index.finish(attempt, "partial")
    store.close()
    reopened = Store(path)
    resumed = ArchiveIndex(reopened.con)
    work = resumed.work(source().key)
    assert work["page_token"] == "next"
    assert work["request"] == request
    assert work["attempt_id"] == attempt
    assert resumed.page_count(attempt) == 1
    assert resumed.coverage()[0]["status"] == "partial"
    reopened.close()


def test_legacy_import_is_non_destructive_and_not_full_history(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    store.con.execute(
        "INSERT INTO raw_json VALUES ('steps', '2020-01-01', '2020-01-31', 0, now(), ?)",
        ['{"dataPoints":[]}'],
    )
    index = ArchiveIndex(store.con)
    archive = Archive(tmp_path / "archive")
    assert index.import_legacy(archive) == 1
    assert index.import_legacy(archive) == 0
    assert store.con.execute("SELECT count(*) FROM raw_json").fetchone()[0] == 1
    row = index.coverage()[0]
    assert row["history_complete"] is False
    assert row["representation"] == "legacy_json"
    assert (row["stored_pages"], row["stored_points"]) == (1, 0)
    assert row["status"] == "unknown_history"
    store.close()


def test_registered_unvisited_source_is_pending(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    index.register(source())
    assert index.coverage()[0]["status"] == "pending"
    assert index.coverage()[0]["last_attempt_at"] is None
    assert index.coverage()[0]["stored_pages"] == index.coverage()[0]["stored_points"] == 0
    store.close()


def test_success_requires_explicitly_verified_terminal_page(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    index.register(source())
    attempt = index.start(source().key, {}, "source")
    ref = Archive(tmp_path / "archive").put(b'{"dataPoints":[],"nextPageToken":"next"}')
    index.record_page(attempt, 0, ref, 200, 0)
    with pytest.raises(ValueError, match="terminal"):
        index.finish(attempt, "empty", history_complete=True)
    with pytest.raises(ValueError, match="terminal"):
        index.confirm_terminal(attempt, next_page_token="next")
    assert not index.coverage()[0]["history_complete"]
    store.close()


def test_interrupted_legacy_import_retries_without_duplicate_observations(tmp_path, monkeypatch):
    store = Store(tmp_path / "health.duckdb")
    store.con.execute(
        "INSERT INTO raw_json VALUES ('steps','2020-01-01','2020-01-31',0,now(), '{}'),"
        "('steps','2020-02-01','2020-02-28',0,now(), '{\"dataPoints\":[]}')"
    )
    index = ArchiveIndex(store.con)
    archive = Archive(tmp_path / "archive")
    put = archive.put
    calls = 0

    def fail_second(body):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return put(body)

    with monkeypatch.context() as patch:
        patch.setattr(archive, "put", fail_second)
        with pytest.raises(OSError):
            index.import_legacy(archive)
    assert index.import_legacy(archive) == 2
    assert store.con.execute("SELECT count(*) FROM archive_pages").fetchone()[0] == 2
    assert store.con.execute("SELECT count(*) FROM raw_json").fetchone()[0] == 2
    store.close()


def test_detail_queue_failure_rolls_back_source_attempt_and_work(tmp_path, monkeypatch):
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    detail = SimpleNamespace(key="weight.get.resource.one", representation="source")
    start = index.start

    def fail_after_start(*args):
        start(*args)
        raise OSError("disk full before commit")

    with monkeypatch.context() as patch:
        patch.setattr(index, "start", fail_after_start)
        with pytest.raises(OSError):
            index.enqueue_detail(detail, {"resource_name": "one"})
    assert index.work(detail.key) is None
    assert store.con.execute("SELECT count(*) FROM archive_sources").fetchone()[0] == 0
    assert store.con.execute("SELECT count(*) FROM archive_attempts").fetchone()[0] == 0
    index.enqueue_detail(detail, {"resource_name": "one"})
    store.close()
    store = Store(tmp_path / "health.duckdb")
    index = ArchiveIndex(store.con)
    assert index.work(detail.key)["request"] == {"resource_name": "one"}
    assert store.con.execute("SELECT count(*) FROM archive_attempts").fetchone()[0] == 1
    store.close()


def test_stored_counts_span_all_attempts_without_changing_latest_or_history(tmp_path):
    store = Store(tmp_path / "counts.duckdb")
    index = ArchiveIndex(store.con)
    archive = Archive(tmp_path / "archive")
    index.register(source())
    try:
        # Identical bodies still represent distinct saved response observations.
        reference = archive.put(b'{"dataPoints":[{},{}]}')
        for _ in range(2):
            attempt = index.start(source().key, {}, "source")
            index.record_page(attempt, 0, reference, 200, 2)
            index.confirm_terminal(attempt, next_page_token=None)
            index.finish(attempt, "complete")
        failed = index.start(source().key, {}, "source")
        index.record_page(failed, 0, archive.put(b'{"error":403}'), 403, 0)
        index.finish(failed, "permission_denied", http_status=403)
        row = index.coverage()[0]
        assert (row["pages"], row["points"]) == (1, 0)
        assert (row["stored_pages"], row["stored_points"]) == (3, 4)
        assert row["history_complete"] is False
        assert row["status"] == "permission_denied"
        index.start(source().key, {}, "source")  # Newly started, no response yet.
        row = index.coverage()[0]
        assert (row["pages"], row["points"]) == (0, 0)
        assert (row["stored_pages"], row["stored_points"]) == (3, 4)
        assert row["history_complete"] is False
    finally:
        store.close()


def test_detail_prototype_sums_child_storage_across_their_attempts(tmp_path):
    store = Store(tmp_path / "details.duckdb")
    index = ArchiveIndex(store.con)
    archive = Archive(tmp_path / "archive")
    parent = source()
    prototype = SimpleNamespace(
        key="heart-rate.get",
        data_type="heart-rate",
        label="Details",
        representation="source",
        preferred_method="get",
        detail_parent=parent.key,
    )
    index.register(parent)
    index.register(prototype)
    try:
        for name, points in (("one", 2), ("two", 3)):
            child = SimpleNamespace(**{**vars(prototype), "key": f"heart-rate.get.resource.{name}"})
            index.register(child)
            attempt = index.start(child.key, {}, "source")
            index.record_page(attempt, 0, archive.put(b'{"dataPoints":[]}'), 200, points)
            index.confirm_terminal(attempt, next_page_token=None)
            index.finish(attempt, "complete")
            failure = index.start(child.key, {}, "source")
            index.record_page(failure, 0, archive.put(b'{"error":403}'), 403, 0)
            index.finish(failure, "permission_denied", http_status=403)
        row = next(row for row in index.coverage() if row["stream_id"] == prototype.key)
        assert (row["pages"], row["points"]) == (2, 0)
        assert (row["stored_pages"], row["stored_points"]) == (4, 5)
        assert row["history_complete"] is False
    finally:
        store.close()
