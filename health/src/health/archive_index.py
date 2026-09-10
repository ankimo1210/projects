"""Durable response observations and honest coverage on the Store connection."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from health.archive import Archive, ObjectRef

STATES = frozenset(
    {
        "pending",
        "complete",
        "empty",
        "partial",
        "permission_denied",
        "unsupported",
        "failed",
        "rate_limited",
        "unknown_history",
        "storage_error",
    }
)
_SCHEMA = """
CREATE TABLE IF NOT EXISTS archive_sources (stream_id VARCHAR PRIMARY KEY, metadata JSON);
CREATE TABLE IF NOT EXISTS archive_attempts (
 id VARCHAR PRIMARY KEY, stream_id VARCHAR, request_json JSON, representation VARCHAR,
 started_at TIMESTAMP DEFAULT current_timestamp, finished_at TIMESTAMP,
 status VARCHAR, reason VARCHAR, http_status INTEGER, history_complete BOOLEAN DEFAULT false
);
CREATE TABLE IF NOT EXISTS archive_pages (
 attempt_id VARCHAR, page_seq INTEGER, sha256 VARCHAR, object_path VARCHAR,
 byte_count BIGINT, http_status INTEGER, point_count BIGINT,
 PRIMARY KEY(attempt_id, page_seq)
);
CREATE TABLE IF NOT EXISTS archive_work (
 stream_id VARCHAR PRIMARY KEY, request_json JSON, page_token VARCHAR, attempt_id VARCHAR,
 next_visit BIGINT DEFAULT 0, state VARCHAR, seen_tokens JSON DEFAULT '[]', completed_on DATE
);
CREATE TABLE IF NOT EXISTS archive_meta (key VARCHAR PRIMARY KEY, value VARCHAR);
CREATE TABLE IF NOT EXISTS archive_terminal (attempt_id VARCHAR PRIMARY KEY, page_seq INTEGER);
CREATE TABLE IF NOT EXISTS archive_detail_failures (
 parent_attempt_id VARCHAR, stream_id VARCHAR, PRIMARY KEY(parent_attempt_id, stream_id)
);
INSERT INTO archive_meta VALUES ('schema_version', '1') ON CONFLICT DO NOTHING;
"""


def _decode(value):
    return json.loads(value) if isinstance(value, str) else value


def _request_dict(request) -> dict:
    if is_dataclass(request):
        return asdict(request)
    return dict(request)


def _iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


class ArchiveIndex:
    def __init__(self, con, *, initialize: bool = True):
        self.con = con
        if initialize:
            con.execute("BEGIN TRANSACTION")
            try:
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        con.execute(statement)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

    def register(self, source) -> None:
        metadata = asdict(source) if is_dataclass(source) else vars(source)
        self.con.execute(
            "INSERT INTO archive_sources VALUES (?, ?) ON CONFLICT(stream_id) "
            "DO UPDATE SET metadata = excluded.metadata",
            [source.key, json.dumps(metadata)],
        )

    def start(self, stream_id: str, request, representation: str) -> str:
        attempt_id = uuid4().hex
        encoded = json.dumps(_request_dict(request), sort_keys=True)
        self.con.execute(
            "INSERT INTO archive_attempts(id,stream_id,request_json,representation,status) "
            "VALUES (?,?,?,?, 'partial')",
            [attempt_id, stream_id, encoded, representation],
        )
        visit = self.next_visit()
        self.con.execute(
            "INSERT INTO archive_work(stream_id,request_json,attempt_id,next_visit,state) "
            "VALUES (?,?,?,?, 'partial') ON CONFLICT(stream_id) DO UPDATE SET "
            "request_json=excluded.request_json, attempt_id=excluded.attempt_id, "
            "page_token=NULL, state='partial', seen_tokens='[]', next_visit=excluded.next_visit",
            [stream_id, encoded, attempt_id, visit],
        )
        return attempt_id

    def next_visit(self) -> int:
        return self.con.execute(
            "SELECT coalesce(max(next_visit),0)+1 FROM archive_work"
        ).fetchone()[0]

    def enqueue_detail(self, source, request) -> None:
        """Publish a discovered resource and its resumable work together."""
        self.con.execute("BEGIN TRANSACTION")
        try:
            self.register(source)
            self.start(source.key, request, source.representation)
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise

    def record_detail_failure(self, parent_attempt_id: str, stream_id: str) -> None:
        # Keep the evidence for this scan; a new parent attempt can resolve it.
        self.con.execute(
            "INSERT INTO archive_detail_failures VALUES (?, ?) ON CONFLICT DO NOTHING",
            [parent_attempt_id, stream_id],
        )

    def record_page(
        self,
        attempt_id: str,
        page_seq: int,
        ref: ObjectRef,
        status_code: int,
        point_count: int | None = None,
    ) -> None:
        self.con.execute("DELETE FROM archive_terminal WHERE attempt_id=?", [attempt_id])
        self.con.execute(
            "INSERT INTO archive_pages VALUES (?,?,?,?,?,?,?)",
            [
                attempt_id,
                page_seq,
                ref.sha256,
                ref.relative_path,
                ref.byte_count,
                status_code,
                point_count,
            ],
        )

    def confirm_terminal(self, attempt_id: str, *, next_page_token: str | None) -> None:
        """Record a parsed, successful final page; a continuation cannot prove completion."""
        if next_page_token not in (None, ""):
            raise ValueError("terminal page still has a continuation token")
        row = self.con.execute(
            "SELECT page_seq,http_status,point_count FROM archive_pages WHERE attempt_id=? "
            "ORDER BY page_seq DESC LIMIT 1",
            [attempt_id],
        ).fetchone()
        if row is None or not 200 <= row[1] < 300 or row[2] is None:
            raise ValueError("terminal page must be successfully saved and parsed")
        self.con.execute(
            "INSERT INTO archive_terminal VALUES (?,?) ON CONFLICT(attempt_id) "
            "DO UPDATE SET page_seq=excluded.page_seq",
            [attempt_id, row[0]],
        )

    def set_points(self, attempt_id: str, page_seq: int, count: int) -> None:
        self.con.execute(
            "UPDATE archive_pages SET point_count=? WHERE attempt_id=? AND page_seq=?",
            [count, attempt_id, page_seq],
        )

    def page_count(self, attempt_id: str) -> int:
        return self.con.execute(
            "SELECT count(*) FROM archive_pages WHERE attempt_id=?", [attempt_id]
        ).fetchone()[0]

    def point_count(self, attempt_id: str) -> int:
        return self.con.execute(
            "SELECT coalesce(sum(point_count),0) FROM archive_pages "
            "WHERE attempt_id=? AND http_status BETWEEN 200 AND 299",
            [attempt_id],
        ).fetchone()[0]

    def save_cursor(self, stream_id: str, request, token: str, attempt_id: str) -> None:
        work = self.work(stream_id)
        tokens = work["seen_tokens"] if work else []
        if token in tokens:
            raise ValueError("repeated continuation token")
        tokens.append(token)
        self.con.execute(
            "UPDATE archive_work SET request_json=?,page_token=?,attempt_id=?,next_visit=?,"
            "state='partial',seen_tokens=? WHERE stream_id=?",
            [
                json.dumps(_request_dict(request), sort_keys=True),
                token,
                attempt_id,
                self.next_visit(),
                json.dumps(tokens),
                stream_id,
            ],
        )

    def work(self, stream_id: str) -> dict | None:
        cursor = self.con.execute("SELECT * FROM archive_work WHERE stream_id=?", [stream_id])
        names = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if row is None:
            return None
        result = dict(zip(names, row, strict=True))
        result["request"] = _decode(result.pop("request_json"))
        result["seen_tokens"] = _decode(result["seen_tokens"]) or []
        return result

    def finish(
        self,
        attempt_id: str,
        status: str,
        reason: str | None = None,
        *,
        http_status: int | None = None,
        history_complete: bool = False,
        completed_on: date | None = None,
    ) -> None:
        if status not in STATES:
            raise ValueError("unknown archival status")
        if status in {"complete", "empty"}:
            terminal = self.con.execute(
                "SELECT page_seq FROM archive_terminal WHERE attempt_id=?", [attempt_id]
            ).fetchone()
            if terminal is None:
                raise ValueError("cannot complete a query without a verified terminal page")
        elif history_complete:
            raise ValueError("history completeness requires successful terminal status")
        self.con.execute(
            "UPDATE archive_attempts SET status=?,reason=?,http_status=?,history_complete=?,"
            "finished_at=current_timestamp WHERE id=?",
            [status, reason, http_status, history_complete, attempt_id],
        )
        self.con.execute(
            "UPDATE archive_work SET state=?,next_visit=?,completed_on=coalesce(?,completed_on) "
            "WHERE attempt_id=?",
            [status, self.next_visit(), completed_on, attempt_id],
        )

    def next_run(self) -> int:
        row = self.con.execute("SELECT value FROM archive_meta WHERE key='run_number'").fetchone()
        value = int(row[0]) + 1 if row else 1
        self.con.execute(
            "INSERT INTO archive_meta VALUES ('run_number',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            [str(value)],
        )
        return value

    def coverage(self) -> list[dict]:
        sources = self.con.execute(
            "SELECT stream_id,metadata FROM archive_sources ORDER BY stream_id"
        ).fetchall()
        # Count saved response observations across every attempt, not distinct
        # content objects. Error pages are stored too; only successful parsed
        # responses contribute known points. Legacy/unknown point counts add 0.
        stored = {
            stream_id: (pages, points)
            for stream_id, pages, points in self.con.execute(
                "SELECT a.stream_id,count(*),coalesce(sum(CASE "
                "WHEN p.http_status BETWEEN 200 AND 299 THEN p.point_count ELSE 0 END),0) "
                "FROM archive_attempts a JOIN archive_pages p ON p.attempt_id=a.id "
                "GROUP BY a.stream_id"
            ).fetchall()
        }
        result = []
        latest_attempts = {}
        for stream_id, encoded in sources:
            metadata = _decode(encoded)
            cursor = self.con.execute(
                "SELECT * FROM archive_attempts WHERE stream_id=? ORDER BY started_at,id",
                [stream_id],
            )
            names = [column[0] for column in cursor.description]
            attempts = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            latest = attempts[-1] if attempts else None
            latest_attempts[stream_id] = latest["id"] if latest else None
            request = _decode(latest["request_json"]) if latest else {}
            intervals = []
            for attempt in attempts:
                window = _decode(attempt["request_json"])
                if attempt["status"] in {"complete", "empty"}:
                    interval = {
                        "start": window.get("range_start"),
                        "end": window.get("range_end"),
                        "status": attempt["status"],
                    }
                    if interval not in intervals:
                        intervals.append(interval)
            pages = self.page_count(latest["id"]) if latest else 0
            points = self.point_count(latest["id"]) if latest else 0
            stored_pages, stored_points = stored.get(stream_id, (0, 0))
            history_complete = any(attempt["history_complete"] for attempt in attempts)
            result.append(
                {
                    "stream_id": stream_id,
                    "data_type": metadata.get("data_type", stream_id),
                    "label": metadata.get("label", stream_id),
                    "representation": metadata.get("representation", "source"),
                    "status": latest["status"] if latest else "pending",
                    "method": metadata.get("preferred_method"),
                    "requested_start": request.get("range_start"),
                    "requested_end": request.get("range_end"),
                    "history_complete": bool(history_complete),
                    "intervals": intervals,
                    "pages": pages,
                    "points": points,
                    "stored_pages": stored_pages,
                    "stored_points": stored_points,
                    "last_attempt_at": _iso(latest["started_at"]) if latest else None,
                    "reason": latest["reason"] if latest else None,
                    "http_status": latest["http_status"] if latest else None,
                    "projection_status": "not_implemented",
                }
            )
        # A detail endpoint is a family of discovered resource jobs. Its catalog
        # row summarizes them instead of remaining pending forever without a URL.
        by_key = {row["stream_id"]: row for row in result}
        for key, encoded in sources:
            parent_key = _decode(encoded).get("detail_parent")
            if not parent_key or ".resource." in key:
                continue
            row, parent = by_key[key], by_key.get(parent_key)
            children = [
                item for name, item in by_key.items() if name.startswith(key + ".resource.")
            ]
            row.update(
                stored_pages=sum(c["stored_pages"] for c in children),
                stored_points=sum(c["stored_points"] for c in children),
            )
            if not parent:
                continue
            row.update(
                pages=sum(c["pages"] for c in children),
                points=sum(c["points"] for c in children),
                last_attempt_at=max(
                    (c["last_attempt_at"] or "" for c in [parent, *children]), default=""
                )
                or None,
            )
            failed = next(
                (
                    c
                    for c in children
                    if c["status"] not in {"complete", "empty", "partial", "pending"}
                ),
                None,
            )
            unresolved = self.con.execute(
                "SELECT 1 FROM archive_detail_failures WHERE parent_attempt_id=? AND stream_id=?",
                [latest_attempts.get(parent_key), key],
            ).fetchone()
            if unresolved:
                row.update(
                    status="unknown_history",
                    reason="Parent response contained unusable detail resource names",
                    history_complete=False,
                )
            elif failed:
                row.update(
                    status=failed["status"],
                    reason=failed["reason"],
                    http_status=failed["http_status"],
                )
            elif any(c["status"] in {"partial", "pending"} for c in children):
                row.update(status="partial", reason="Discovered detail requests are still pending")
            elif parent["status"] not in {"complete", "empty"}:
                row.update(
                    status=parent["status"],
                    reason=parent["reason"],
                    http_status=parent["http_status"],
                )
            elif not children and parent["points"]:
                row.update(
                    status="unknown_history",
                    reason="Parent response contained no usable detail resource names",
                )
            else:
                row.update(
                    status="complete" if children else "empty",
                    reason=None,
                    history_complete=parent["history_complete"]
                    and all(c["history_complete"] for c in children),
                )
        return result

    def import_legacy(self, archive: Archive) -> int:
        if self.con.execute("SELECT value FROM archive_meta WHERE key='legacy_import'").fetchone():
            return 0
        # Objects are durable before index writes; rollback leaves only harmless
        # content-addressed objects, which a retry can reuse without duplicate rows.
        self.con.execute("BEGIN TRANSACTION")
        try:
            count = self._import_legacy(archive)
            self.con.execute("COMMIT")
            return count
        except Exception:
            self.con.execute("ROLLBACK")
            raise

    def _import_legacy(self, archive: Archive) -> int:
        count = 0
        metrics = self.con.execute(
            "SELECT DISTINCT metric FROM raw_json ORDER BY metric"
        ).fetchall()
        for (metric,) in metrics:
            key = f"legacy:{metric}"
            self.register(
                SimpleNamespace(
                    key=key,
                    data_type=metric,
                    label=metric,
                    preferred_method=None,
                    representation="legacy_json",
                    availability="unverified",
                )
            )
            attempt = self.start(key, {}, "legacy_json")
            rows = self.con.execute(
                "SELECT payload FROM raw_json WHERE metric=? ORDER BY range_start,range_end,page_index",
                [metric],
            ).fetchall()
            for seq, (payload,) in enumerate(rows):
                ref = archive.put(
                    payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                )
                self.record_page(attempt, seq, ref, 200)
                count += 1
            self.finish(
                attempt, "unknown_history", "Legacy parsed JSON; source coverage was not recorded"
            )
        self.con.execute(
            "INSERT INTO archive_meta VALUES ('legacy_import','1') ON CONFLICT DO NOTHING"
        )
        return count
