"""Synthetic-store integration tests for atomic, private static generations."""

import json
import os
import stat
from datetime import UTC, datetime, timezone
from types import SimpleNamespace

import duckdb
import pytest
from health.store import Store
from health.web_export import export_web


@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path / "synthetic.duckdb")
    yield value
    value.close()


def read_export(path, filename):
    meta = json.loads(path.read_text())
    snapshot = json.loads((path.parent / meta["basePath"] / meta["files"][filename]).read_text())
    assert snapshot["schemaVersion"] == 1
    assert snapshot["generation"] == meta["generation"]
    return snapshot["data"]


def test_empty_export_lists_pending_inventory_without_mutating_legacy_db(store, tmp_path):
    before = store.con.execute("SHOW TABLES").fetchall()
    path = export_web(store, tmp_path / "web", generation_id="empty")
    assert path == tmp_path / "web" / "meta.json"
    assert store.con.execute("SHOW TABLES").fetchall() == before
    meta = json.loads(path.read_text())
    assert meta["freshness"] == {"archiveStatus": "pending", "projectionStatus": "empty"}
    daily = read_export(path, "daily.json")
    assert daily["dates"] == []
    assert len(daily["series"]) == 17
    assert all(values == [] for values in daily["series"].values())
    assert read_export(path, "sleep.json") == {"sessions": [], "timeBasis": "civil"}
    sources = read_export(path, "inventory.json")["sources"]
    assert sources and all(
        row["status"] == "pending" and not row["history_complete"] for row in sources
    )


def test_daily_alignment_nulls_units_and_quality(store, tmp_path):
    store.upsert_daily(
        [
            ("steps", "2025-01-01", 100),
            ("steps", "2025-01-03", float("inf")),
            ("weight_kg", "2025-01-03", 65.5),
            ("fat_pct", "2025-01-01", float("nan")),
        ]
    )
    path = export_web(store, tmp_path / "web")
    data = read_export(path, "daily.json")
    assert data["dates"] == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert data["series"]["steps"] == [100.0, None, None]
    assert data["series"]["weight_kg"] == [None, None, 65.5]
    assert all(len(values) == 3 for values in data["series"].values())
    assert data["units"]["weight_kg"] == "kg"
    assert data["units"]["fat_pct"] == "%"
    assert read_export(path, "inventory.json")["quality"] == [
        {"path": "daily.json", "reason": "non_finite_number", "count": 2},
    ]


def test_intraday_full_resolution_civil_microseconds_and_day_partition(store, tmp_path):
    rows = [("hr", datetime(2025, 1, 1, 0, 0, i), float(60 + i)) for i in range(60)]
    rows += [
        ("hr", datetime(2025, 1, 1, 23, 59, 59, 999999), 70),
        ("hr", datetime(2025, 1, 2, 0, 0, 0, 1), float("inf")),
        ("steps", datetime(2025, 1, 1, 0, 0, 0, 123456), 12),
    ]
    store.upsert_intraday(reversed(rows))
    path = export_web(store, tmp_path / "web")
    data = read_export(path, "intraday/hr/2025-01-01.json")
    assert data["timeBasis"] == "civil"
    assert data["timeUnit"] == "microseconds_since_local_midnight"
    assert len(data["points"]) == 61
    assert data["points"][1] == [1_000_000, 61.0]
    assert data["points"][-1] == [86_399_999_999, 70.0]
    assert read_export(path, "intraday/hr/2025-01-02.json")["points"] == [[1, None]]
    index = read_export(path, "intraday-index.json")["metrics"]
    assert index["hr"]["unit"] == "bpm"
    assert index["hr"]["days"] == [
        {"date": "2025-01-01", "path": "intraday/hr/2025-01-01.json", "count": 61},
        {"date": "2025-01-02", "path": "intraday/hr/2025-01-02.json", "count": 1},
    ]


def test_sleep_preserves_actual_rows_naps_classic_and_microseconds(store, tmp_path):
    row = {
        "provider_id": "main",
        "date": "2025-01-02",
        "start_ts": "2025-01-01T23:00:00.123456",
        "end_ts": "2025-01-02T07:00:00",
        "minutes_asleep": 470,
        "minutes_deep": None,
        "minutes_light": None,
        "minutes_rem": None,
        "minutes_wake": 10,
        "efficiency": 98,
        "is_main": True,
    }
    store.upsert_sleep([dict(row, provider_id="nap", is_main=False, minutes_asleep=30), row])
    path = export_web(store, tmp_path / "web")
    sessions = read_export(path, "sleep.json")["sessions"]
    assert [item["provider_id"] for item in sessions] == ["main", "nap"]
    assert sessions[0] == row
    assert sessions[1]["is_main"] is False
    assert sessions[1]["minutes_asleep"] == 30
    assert set(sessions[0]) == set(store.sleep_frame().columns)


@pytest.mark.parametrize(
    "generation", ["../escape", "/absolute", "a/b", "a\\b", ".", "..", "", "a%2fb", "x" * 129]
)
def test_unsafe_generation_rejected_before_any_export(store, tmp_path, generation):
    with pytest.raises(ValueError):
        export_web(store, tmp_path / "web", generation_id=generation)
    assert not (tmp_path / "web").exists()


def test_existing_generation_and_symlinks_cannot_be_overwritten(store, tmp_path):
    path = export_web(store, tmp_path / "web", generation_id="keep")
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        export_web(store, path.parent, generation_id="keep")
    assert path.read_bytes() == before
    external = tmp_path / "external"
    external.mkdir()
    (path.parent / "generations" / "linked").symlink_to(external, target_is_directory=True)
    with pytest.raises((ValueError, FileExistsError)):
        export_web(store, path.parent, generation_id="linked")
    assert list(external.iterdir()) == []
    link = tmp_path / "linked-output"
    link.symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError):
        export_web(store, link, generation_id="invalid")


def test_unsafe_typed_metric_cannot_escape_generation(store, tmp_path):
    store.upsert_intraday([("../../escape", "2025-01-01", 1)])
    with pytest.raises(ValueError):
        export_web(store, tmp_path / "web")
    assert not (tmp_path / "web" / "meta.json").exists()
    assert not (tmp_path / "escape").exists()


def test_failed_write_keeps_previous_meta_and_all_referenced_files(store, tmp_path, monkeypatch):
    path = export_web(store, tmp_path / "web", generation_id="old")
    original = path.read_bytes()
    old = {
        item: item.read_bytes() for item in (path.parent / "generations" / "old").rglob("*.json")
    }
    real_dump = json.dump

    def fail_inventory(value, stream, *args, **kwargs):
        if "sources" in value.get("data", {}) and "quality" in value["data"]:
            raise OSError("synthetic disk full")
        return real_dump(value, stream, *args, **kwargs)

    monkeypatch.setattr(json, "dump", fail_inventory)
    with pytest.raises(OSError, match="synthetic disk full"):
        export_web(store, path.parent, generation_id="failed")
    assert path.read_bytes() == original
    assert all(item.read_bytes() == content for item, content in old.items())
    assert not (path.parent / "generations" / "failed").exists()
    assert store.con.execute("SELECT count(*) FROM daily_series").fetchone() == (0,)


def test_export_uses_one_database_snapshot_with_concurrent_writer(store, tmp_path, monkeypatch):
    store.upsert_daily([("steps", "2025-01-01", 100)])
    store.upsert_intraday([("hr", "2025-01-01T00:00:00", 60)])
    writer = duckdb.connect(str(store.path))
    original = store.daily_frame

    def read_then_update(metrics):
        result = original(metrics)
        writer.execute("INSERT INTO daily_series VALUES ('steps', '2025-01-02', 200)")
        writer.execute("INSERT INTO intraday VALUES ('hr', '2025-01-02T00:00:00', 70)")
        return result

    monkeypatch.setattr(store, "daily_frame", read_then_update)
    try:
        path = export_web(store, tmp_path / "web")
    finally:
        writer.close()
    assert read_export(path, "daily.json")["dates"] == ["2025-01-01"]
    assert len(read_export(path, "intraday-index.json")["metrics"]["hr"]["days"]) == 1
    assert store.con.execute("SELECT count(*) FROM intraday").fetchone() == (2,)


def test_generation_is_deterministic_sorted_private_and_excludes_raw(store, tmp_path):
    store.upsert_daily([("steps", "2025-01-01", 100)])
    store.con.execute(
        "INSERT INTO raw_json VALUES ('steps', '2025-01-01', '2025-01-01', 0, now(), ?)",
        [json.dumps({"access_token": "SECRET_SENTINEL", "raw": "SOURCE_SENTINEL"})],
    )
    now = datetime(2025, 1, 3, tzinfo=UTC)
    one = export_web(store, tmp_path / "one", generation_id="same", generated_at=now)
    two = export_web(store, tmp_path / "two", generation_id="same", generated_at=now)
    assert one.read_bytes() == two.read_bytes()
    meta = json.loads(one.read_text())
    assert list(meta["files"]) == sorted(meta["files"])
    for filename in meta["files"]:
        left = one.parent / meta["basePath"] / filename
        right = two.parent / meta["basePath"] / filename
        assert left.read_bytes() == right.read_bytes()
        text = left.read_text()
        assert "SECRET_SENTINEL" not in text and "SOURCE_SENTINEL" not in text
        assert str(tmp_path) not in text
        assert "NaN" not in text and "Infinity" not in text
        if os.name == "posix":
            assert stat.S_IMODE(left.stat().st_mode) == 0o600
            assert stat.S_IMODE(left.parent.stat().st_mode) == 0o700
    assert read_export(one, "inventory.json")["sources"][0]["history_complete"] is False


def test_archive_coverage_is_read_only_and_reasons_cannot_leak(store, tmp_path):
    from health.archive_index import ArchiveIndex

    index = ArchiveIndex(store.con)
    index.register(
        SimpleNamespace(
            key="synthetic:list",
            data_type="synthetic",
            label="Synthetic",
            preferred_method="list",
            representation="source",
        )
    )
    attempt = index.start("synthetic:list", {}, "source")
    index.finish(
        attempt, "permission_denied", "Bearer SECRET_TOKEN /private/token.json", http_status=403
    )
    before = store.con.execute("SELECT * FROM archive_attempts").fetchall()
    path = export_web(store, tmp_path / "web")
    assert store.con.execute("SELECT * FROM archive_attempts").fetchall() == before
    row = next(
        row
        for row in read_export(path, "inventory.json")["sources"]
        if row["stream_id"] == "synthetic:list"
    )
    assert row["status"] == "permission_denied" and row["http_status"] == 403
    assert "SECRET_TOKEN" not in json.dumps(row)
    assert "/private" not in json.dumps(row)
    assert row["reason"]
    assert json.loads(path.read_text())["freshness"]["archiveStatus"] == "partial"


def test_inventory_retains_typed_series_counts_separate_from_raw_pages(store, tmp_path):
    store.upsert_daily([("steps", "2025-01-01", 10), ("steps", "2025-01-03", None)])
    store.upsert_intraday([("steps", "2025-01-02", 2)])
    path = export_web(store, tmp_path / "web")
    series = read_export(path, "inventory.json")["series"]
    daily = next(row for row in series if row["metric"] == "steps" and row["storage"] == "daily")
    intraday = next(
        row for row in series if row["metric"] == "steps" and row["storage"] == "intraday"
    )
    assert daily == {
        "metric": "steps",
        "storage": "daily",
        "n": 2,
        "first_date": "2025-01-01",
        "last_date": "2025-01-03",
        "unit": "steps",
    }
    assert intraday["n"] == 1
    assert intraday["first_date"] == intraday["last_date"] == "2025-01-02"
    assert read_export(path, "inventory.json")["quality"] == []


def test_archive_intervals_keep_success_status_after_later_failure(store, tmp_path, monkeypatch):
    from health.archive import Archive
    from health.archive_index import ArchiveIndex

    from health import source_catalog

    source = SimpleNamespace(
        key="synthetic:list",
        data_type="synthetic",
        label="Synthetic",
        preferred_method="list",
        representation="source",
    )
    monkeypatch.setattr(source_catalog, "load_sources", lambda: (source,))
    index = ArchiveIndex(store.con)
    index.register(source)
    attempt = index.start(
        source.key, {"range_start": "2025-01-01", "range_end": "2025-01-31"}, "source"
    )
    reference = Archive(tmp_path / "archive").put(b'{"dataPoints": []}')
    index.record_page(attempt, 0, reference, 200, 0)
    index.confirm_terminal(attempt, next_page_token=None)
    index.finish(attempt, "empty", history_complete=True)
    path = export_web(store, tmp_path / "web", generation_id="complete")
    assert json.loads(path.read_text())["freshness"]["archiveStatus"] == "complete"
    failed = index.start(source.key, {}, "source")
    index.finish(failed, "failed", "private detail")
    path = export_web(store, tmp_path / "web", generation_id="failed-refresh")
    row = read_export(path, "inventory.json")["sources"][0]
    assert row["history_complete"] is True
    assert row["status"] == "failed"
    assert row["intervals"] == [{"start": "2025-01-01", "end": "2025-01-31", "status": "empty"}]
    assert json.loads(path.read_text())["freshness"]["archiveStatus"] == "partial"


@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_final_publication_failure_preserves_old_generation(store, tmp_path, monkeypatch, failure):
    path = export_web(store, tmp_path / "web", generation_id="old")
    before = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("synthetic publication failure")

    monkeypatch.setattr(os, failure, fail)
    with pytest.raises(OSError, match="synthetic publication failure"):
        export_web(store, path.parent, generation_id="new")
    assert path.read_bytes() == before
    assert read_export(path, "daily.json")["dates"] == []
    assert not (path.parent / "generations" / "new").exists()
    assert list(path.parent.glob(".meta-*.json")) == []


def test_export_retains_stored_counts_after_permission_failure_read_only(store, tmp_path):
    from health.archive import Archive
    from health.archive_index import ArchiveIndex

    index = ArchiveIndex(store.con)
    archive = Archive(tmp_path / "archive")
    index.register(
        SimpleNamespace(
            key="synthetic:list",
            data_type="synthetic",
            label="Synthetic",
            preferred_method="list",
            representation="source",
        )
    )
    attempt = index.start("synthetic:list", {}, "source")
    index.record_page(attempt, 0, archive.put(b'{"dataPoints":[{},{}]}'), 200, 2)
    index.confirm_terminal(attempt, next_page_token=None)
    index.finish(attempt, "complete")
    failure = index.start("synthetic:list", {}, "source")
    index.finish(failure, "permission_denied", http_status=403)
    before = index.coverage()
    path = export_web(store, tmp_path / "web")
    assert index.coverage() == before
    rows = read_export(path, "inventory.json")["sources"]
    row = next(row for row in rows if row["stream_id"] == "synthetic:list")
    assert (row["pages"], row["points"]) == (0, 0)
    assert (row["stored_pages"], row["stored_points"]) == (1, 2)
    assert row["status"] == "permission_denied" and row["history_complete"] is False
    pending = [row for row in rows if row["status"] == "pending"]
    assert pending and all(row["stored_pages"] == row["stored_points"] == 0 for row in pending)
