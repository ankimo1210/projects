import json
from datetime import UTC, datetime

from macrokit.snapshot import last_sha, manifest_path, save_snapshot


def _save(root, content, *, day, indicator="jp_cpi_core"):
    return save_snapshot(
        root,
        "estat",
        indicator,
        content,
        ingested_at=datetime(2026, 8, day, 9, 0, tzinfo=UTC),
        url="https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData",
        http_status=200,
        filename="payload.json",
    )


def test_first_save_writes_the_file_and_reports_a_change(tmp_path):
    result = _save(tmp_path, b'{"a": 1}', day=17)
    assert result.changed is True
    assert result.path is not None
    assert result.path.read_bytes() == b'{"a": 1}'
    assert result.size == 8


def test_identical_content_on_a_later_day_is_not_stored_again(tmp_path):
    # Publishing is idempotent between revisions: fetching the same file every
    # day must not fill the disk with copies. Only a CHANGE is worth storing.
    _save(tmp_path, b'{"a": 1}', day=17)
    second = _save(tmp_path, b'{"a": 1}', day=18)
    assert second.changed is False
    assert second.path is None
    stored = list(tmp_path.rglob("payload.json"))
    assert len(stored) == 1


def test_changed_content_is_stored_alongside_the_original(tmp_path):
    # A change IS the revision event -- this is where RevisionShock comes from.
    _save(tmp_path, b'{"a": 1}', day=17)
    second = _save(tmp_path, b'{"a": 2}', day=18)
    assert second.changed is True
    stored = sorted(p.parent.name for p in tmp_path.rglob("payload.json"))
    assert stored == ["2026-08-17", "2026-08-18"]


def test_every_attempt_is_recorded_in_the_manifest_even_when_unchanged(tmp_path):
    _save(tmp_path, b'{"a": 1}', day=17)
    _save(tmp_path, b'{"a": 1}', day=18)
    lines = manifest_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert [r["changed"] for r in records] == [True, False]
    assert records[0]["source"] == "estat"
    assert records[0]["indicator"] == "jp_cpi_core"
    assert records[0]["http_status"] == 200
    assert len(records[0]["sha256"]) == 64


def test_last_sha_tracks_indicators_independently(tmp_path):
    _save(tmp_path, b"one", day=17, indicator="a")
    _save(tmp_path, b"two", day=17, indicator="b")
    assert last_sha(tmp_path, "estat", "a") != last_sha(tmp_path, "estat", "b")
    assert last_sha(tmp_path, "estat", "never_fetched") is None


def test_stored_snapshots_are_never_overwritten(tmp_path):
    # Immutability is the whole guarantee: the Japanese vintage record is only
    # as trustworthy as the promise that a stored file is never rewritten.
    first = _save(tmp_path, b"original", day=17)
    assert first.path is not None
    _save(tmp_path, b"different", day=17)
    assert first.path.read_bytes() == b"original"
