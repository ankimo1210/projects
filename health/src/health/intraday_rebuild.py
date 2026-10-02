"""Offline repair of intraday projections from complete, saved responses.

Never make HTTP requests or rewrite the source observations. An interrupted
repair can be rerun: each day is atomic and replay provenance is idempotent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import uuid4

from health.archive import Archive, ArchiveError, ObjectRef
from health.archive_index import ArchiveIndex
from health.endpoints import CATALOG, PayloadError, response_points
from health.store import Store


@dataclass(frozen=True)
class _Candidate:
    observed_at: datetime
    attempt_id: str | None = None  # None identifies raw_json rather than CAS.
    request: dict | None = None


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _pages(store: Store, archive: Archive, name: str, day: date, candidate: _Candidate):
    refs = []
    if candidate.attempt_id is None:
        saved = store.con.execute(
            "SELECT page_index, payload FROM raw_json WHERE metric=? "
            "AND range_start=? AND range_end=? ORDER BY page_index",
            [name, day, day],
        ).fetchall()
        numbers = [seq for seq, _ in saved]
        pages = [_json(body) for _, body in saved]
    else:
        saved = store.con.execute(
            "SELECT page_seq, sha256, object_path, byte_count, http_status "
            "FROM archive_pages WHERE attempt_id=? ORDER BY page_seq",
            [candidate.attempt_id],
        ).fetchall()
        numbers = [row[0] for row in saved]
        pages = []
        for _, sha, path, size, status in saved:
            if not 200 <= status < 300:
                raise ValueError("unsuccessful archived response")
            ref = ObjectRef(sha, path, size)
            pages.append(json.loads(archive.read(ref)))
            refs.append(ref)
    if not pages or numbers != list(range(len(pages))):
        raise ValueError("missing response pages")
    for i, page in enumerate(pages):
        if not isinstance(page, dict) or "error" in page:
            raise ValueError("invalid response page")
        token = page.get("nextPageToken")
        if i == len(pages) - 1:
            if token not in (None, ""):
                raise ValueError("unfinished response pagination")
        elif not isinstance(token, str) or not token:
            raise ValueError("non-terminal page has no continuation")
    return pages, refs


def _record_replay(store, index, name, candidate, refs, pages, metric):
    # start() would replace archive_work's live/resumable cursor. Offline
    # provenance has no queued network work, so create only the observation.
    existing = store.con.execute(
        "SELECT 1 FROM archive_attempts WHERE stream_id=? "
        "AND json_extract_string(request_json, '$.replayed_from')=? "
        "AND status IN ('complete','empty') LIMIT 1",
        [f"projection:{name}", candidate.attempt_id],
    ).fetchone()
    if existing:
        return
    attempt = uuid4().hex
    request = {**candidate.request, "replayed_from": candidate.attempt_id}
    store.con.execute("BEGIN TRANSACTION")
    try:
        store.con.execute(
            "INSERT INTO archive_attempts(id,stream_id,request_json,representation,status) "
            "VALUES (?,?,?,'projection','partial')",
            [attempt, f"projection:{name}", json.dumps(request)],
        )
        counts = []
        for i, (ref, page) in enumerate(zip(refs, pages, strict=True)):
            count = len(response_points(metric, page))
            counts.append(count)
            index.record_page(attempt, i, ref, 200, count)
        index.confirm_terminal(attempt, next_page_token=None)
        index.finish(attempt, "complete" if sum(counts) else "empty")
        store.con.execute("COMMIT")
    except Exception:
        store.con.execute("ROLLBACK")
        raise


def rebuild_intraday(store: Store, archive: Archive, *, through: date) -> dict:
    """Rebuild each saved one-day response; return counts, never health values."""
    index = ArchiveIndex(store.con)
    candidates: dict[tuple[str, date], _Candidate] = {}
    for name, day, observed in store.con.execute(
        "SELECT metric, range_start, max(fetched_at) FROM raw_json "
        "WHERE metric IN ('intraday_hr','intraday_steps') AND range_start=range_end "
        "AND range_start<=? GROUP BY metric,range_start",
        [through],
    ).fetchall():
        candidates[name, day] = _Candidate(observed)
    for attempt, stream, encoded, observed in store.con.execute(
        "SELECT id,stream_id,request_json,started_at FROM archive_attempts "
        "WHERE stream_id IN ('projection:intraday_hr','projection:intraday_steps') "
        "AND finished_at IS NOT NULL ORDER BY started_at,id"
    ).fetchall():
        request = _json(encoded)
        if request.get("replayed_from"):
            continue
        try:
            start = date.fromisoformat(request["range_start"])
            end = date.fromisoformat(request["range_end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end != start + timedelta(days=1) or start > through:
            continue
        key = stream.removeprefix("projection:"), start
        if key not in candidates or observed > candidates[key].observed_at:
            candidates[key] = _Candidate(observed, attempt, request)
    catalog = {m.name: m for m in CATALOG}
    successful: dict[str, set[date]] = {"intraday_hr": set(), "intraday_steps": set()}
    report = {"rebuilt_days": 0, "rebuilt_points": 0, "failed_days": 0, "checkpoints_advanced": 0}
    for (name, day), candidate in sorted(candidates.items()):
        try:
            pages, refs = _pages(store, archive, name, day, candidate)
            metric = catalog[name]
            parsed = metric.parse_pages(pages)
            store.replace_intraday(metric, day, parsed)
            if candidate.attempt_id:
                _record_replay(store, index, name, candidate, refs, pages, metric)
        except (ArchiveError, PayloadError, ValueError, KeyError, TypeError):
            report["failed_days"] += 1
            continue
        successful[name].add(day)
        report["rebuilt_days"] += 1
        report["rebuilt_points"] += len(parsed.intraday)
    for name, days in successful.items():
        checkpoint = store.get_sync_checkpoint(name)
        if checkpoint is None or checkpoint.status != "in_progress":
            continue
        reached = checkpoint.last_synced
        while reached < through and reached + timedelta(days=1) in days:
            reached += timedelta(days=1)
        if reached != checkpoint.last_synced:
            store.con.execute(
                "UPDATE sync_state SET last_synced_date=?,status=?,updated_at=now() WHERE metric=?",
                [reached, "ok" if reached == through else "in_progress", name],
            )
            report["checkpoints_advanced"] += 1
    return report
