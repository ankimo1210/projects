import json
from datetime import date, timedelta
from types import SimpleNamespace

from health.archive import Archive
from health.archive_index import ArchiveIndex
from health.endpoints import CATALOG
from health.intraday_rebuild import rebuild_intraday
from health.store import Store

DAY = date(2025, 1, 1)


def payload(name, instants=("2025-01-01T05:00:00Z", "2025-01-01T06:00:00Z")):
    civil = {"date": {"year": 2025, "month": 1, "day": 1}, "time": {"hours": 14}}
    points = []
    for instant, offset, value in zip(instants, ("32400s", "28800s"), (65, 72), strict=True):
        if name == "intraday_hr":
            points.append(
                {
                    "heartRate": {
                        "sampleTime": {
                            "civilTime": civil,
                            "physicalTime": instant,
                            "utcOffset": offset,
                        },
                        "beatsPerMinute": value,
                    }
                }
            )
        else:
            points.append(
                {
                    "steps": {
                        "interval": {
                            "civilStartTime": civil,
                            "startTime": instant,
                            "startUtcOffset": offset,
                        },
                        "count": value,
                    }
                }
            )
    return {"dataPoints": points}


def metric(name):
    return next(m for m in CATALOG if m.name == name)


def capture(store, archive, day=DAY, *, terminal=True, missing_page=False):
    index = ArchiveIndex(store.con)
    source = SimpleNamespace(key="projection:intraday_hr")
    index.register(source)
    request = {"range_start": day.isoformat(), "range_end": (day + timedelta(days=1)).isoformat()}
    attempt = index.start(source.key, request, "projection")
    page = payload("intraday_hr")
    if not terminal:
        page["nextPageToken"] = "more"
    index.record_page(
        attempt, 1 if missing_page else 0, archive.put(json.dumps(page).encode()), 200, 2
    )
    index.finish(attempt, "failed", "synthetic typed parse failure")
    return attempt


def test_complete_failed_projection_is_replayed_without_rewriting_failure(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    try:
        original = capture(store, archive)
        work = store.con.execute("SELECT * FROM archive_work").fetchall()
        store.set_sync_state("intraday_hr", DAY - timedelta(days=1), "in_progress")
        report = rebuild_intraday(store, archive, through=DAY)
        assert report["rebuilt_days"] == 1
        assert report["failed_days"] == 0
        assert store.intraday_frame("hr", DAY).value.tolist() == [65, 72]
        assert store.get_sync_checkpoint("intraday_hr").last_synced == DAY
        assert store.get_sync_checkpoint("intraday_hr").status == "ok"
        assert store.con.execute(
            "SELECT status FROM archive_attempts WHERE id=?", [original]
        ).fetchone() == ("failed",)
        assert store.con.execute("SELECT * FROM archive_work").fetchall() == work
        assert rebuild_intraday(store, archive, through=DAY)["rebuilt_days"] == 1
        assert store.con.execute("SELECT count(*) FROM archive_attempts").fetchone() == (2,)
    finally:
        store.close()


def test_raw_rebuild_keeps_raw_timestamps_and_does_not_skip_checkpoint_gap(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    m = metric("intraday_hr")
    try:
        store.replace_chunk(m, DAY, DAY, [payload(m.name)], m.parse_pages([payload(m.name)]))
        store.set_sync_state(m.name, DAY - timedelta(days=2), "in_progress")
        before = store.con.execute("SELECT * FROM raw_json").fetchall()
        report = rebuild_intraday(store, archive, through=DAY)
        assert report["rebuilt_days"] == 1
        assert store.con.execute("SELECT * FROM raw_json").fetchall() == before
        assert store.get_sync_checkpoint(m.name).last_synced == DAY - timedelta(days=2)
    finally:
        store.close()


def test_partial_page_or_gap_cannot_erase_existing_typed_rows(tmp_path):
    for missing_page in (False, True):
        store = Store(tmp_path / f"{missing_page}.duckdb")
        archive = Archive(tmp_path / f"archive-{missing_page}")
        try:
            store.upsert_intraday([("hr", "2025-01-01T14:00:00", 60)])
            capture(store, archive, terminal=missing_page, missing_page=missing_page)
            report = rebuild_intraday(store, archive, through=DAY)
            assert report["failed_days"] == 1
            assert report["rebuilt_days"] == 0
            assert store.intraday_frame("hr", DAY).value.tolist() == [60]
        finally:
            store.close()


def test_corrupt_archive_cannot_replace_day(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    try:
        capture(store, archive)
        path = next((archive.root / "objects").iterdir())
        path.write_bytes(b"corrupt")
        report = rebuild_intraday(store, archive, through=DAY)
        assert report["failed_days"] == 1
        assert store.intraday_frame("hr", DAY).empty
    finally:
        store.close()


def test_incomplete_new_attempt_does_not_hide_complete_archive(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    try:
        complete = capture(store, archive)
        capture(store, archive, terminal=False)
        store.set_sync_state("intraday_hr", DAY - timedelta(days=1), "in_progress")
        report = rebuild_intraday(store, archive, through=DAY)
        assert report["rebuilt_days"] == 1
        assert report["failed_days"] == 0
        assert store.intraday_frame("hr", DAY).value.tolist() == [65, 72]
        assert store.get_sync_checkpoint("intraday_hr").last_synced == DAY
        assert store.con.execute(
            "SELECT count(*) FROM archive_attempts WHERE "
            "json_extract_string(request_json, '$.replayed_from')=?",
            [complete],
        ).fetchone() == (1,)
    finally:
        store.close()


def test_latest_complete_raw_is_preferred_over_old_archive_and_new_partial(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    try:
        older = capture(store, archive)
        store.con.execute("UPDATE archive_attempts SET started_at='2024-01-01' WHERE id=?", [older])
        page = payload("intraday_hr")
        page["dataPoints"][0]["heartRate"]["beatsPerMinute"] = 80
        m = metric("intraday_hr")
        store.replace_chunk(m, DAY, DAY, [page], m.parse_pages([page]))
        capture(store, archive, terminal=False)
        assert rebuild_intraday(store, archive, through=DAY)["failed_days"] == 0
        assert store.intraday_frame("hr", DAY).value.tolist() == [80, 72]
    finally:
        store.close()


def test_crash_after_final_page_before_attempt_finish_is_recoverable(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    archive = Archive(tmp_path / "archive")
    try:
        original = capture(store, archive)
        store.con.execute(
            "UPDATE archive_attempts SET finished_at=NULL,status='partial' WHERE id=?",
            [original],
        )
        work = store.con.execute("SELECT * FROM archive_work").fetchall()
        assert rebuild_intraday(store, archive, through=DAY)["rebuilt_days"] == 1
        assert store.con.execute(
            "SELECT finished_at FROM archive_attempts WHERE id=?", [original]
        ).fetchone() == (None,)
        assert store.con.execute("SELECT * FROM archive_work").fetchall() == work
    finally:
        store.close()
