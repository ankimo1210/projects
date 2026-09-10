"""Local Health Planet archive; independent of Google's database and credentials.

Contracts: https://www.healthplanet.jp/apis/api.html (checked 2026-09-07).
One request covers at most three calendar months. No unbounded history claim.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import requests

from health.archive import Archive, fsync_directory
from health.privacy import ensure_private_dir

ENDPOINTS = {
    "innerscan": ("体重・体脂肪率", "6021,6022"),
    "sphygmomanometer": ("血圧・脈拍", "622E,622F,6230"),
    "pedometer": ("歩数", "6331"),
}
METRICS = {
    "6021": ("weight_kg", "kg"),
    "6022": ("body_fat_pct", "%"),
    "622E": ("systolic_mmhg", "mmHg"),
    "622F": ("diastolic_mmhg", "mmHg"),
    "6230": ("pulse_bpm", "bpm"),
    "6331": ("steps", "steps"),
}
UNSUPPORTED = [
    {"metric": metric, "label": label, "reason": "2020-06-29に公式API連携終了"}
    for metric, label in (
        ("muscle_mass_kg", "筋肉量"),
        ("muscle_score", "筋肉スコア"),
        ("visceral_fat", "内臓脂肪レベル"),
        ("basal_metabolism_kcal", "基礎代謝量"),
        ("body_age", "体内年齢"),
        ("bone_mass_kg", "推定骨量"),
        ("exercise", "エクササイズ"),
        ("activity_calories", "活動消費カロリー"),
        ("urine_glucose", "尿糖"),
    )
]
_SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
 id INTEGER PRIMARY KEY, endpoint TEXT NOT NULL, range_start TEXT NOT NULL,
 range_end TEXT NOT NULL, attempted_at REAL NOT NULL, status TEXT NOT NULL,
 http_status INTEGER, sha256 TEXT, object_path TEXT, byte_count INTEGER,
 point_count INTEGER, unparsed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS measurements (
 id TEXT PRIMARY KEY, endpoint TEXT NOT NULL, metric TEXT NOT NULL, tag TEXT NOT NULL,
 timestamp TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, model TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def month_windows(start: date, end: date) -> list[tuple[str, str]]:
    """Inclusive civil-date bounds, newest first; explicit seconds avoid silent clipping."""
    if start > end:
        raise ValueError("history start must be before or equal to end")
    windows = []
    while start <= end:
        month_index = end.year * 12 + end.month - 3
        first = date(month_index // 12, month_index % 12 + 1, 1)
        windows.append(
            (max(start, first).strftime("%Y%m%d") + "000000", end.strftime("%Y%m%d") + "235959")
        )
        if first <= start:
            break
        end = first - timedelta(days=1)
    return windows


def _connect(data_dir: Path):
    folder = Path(data_dir) / "healthplanet"
    ensure_private_dir(folder)
    path = folder / "healthplanet.sqlite3"
    if path.is_symlink():
        raise ValueError("database must not be a symlink")
    if not path.exists():
        fd, name = tempfile.mkstemp(prefix=".initialize-", dir=folder)
        os.close(fd)
        temporary = Path(name)
        initial = None
        try:
            initial = sqlite3.connect(temporary)
            initial.executescript(_SCHEMA + "PRAGMA user_version=1;")
            initial.close()
            initial = None
            with temporary.open("rb") as saved:
                os.fsync(saved.fileno())
            os.replace(temporary, path)
            fsync_directory(folder)
        finally:
            if initial is not None:
                initial.close()
            temporary.unlink(missing_ok=True)
    path.chmod(0o600)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    if con.execute("PRAGMA user_version").fetchone()[0] != 1:
        con.close()
        raise ValueError("unsupported Health Planet database version")
    return con


def _parse(body: bytes, endpoint: str) -> tuple[list[tuple], int, int]:
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("invalid measurement response")
    records, invalid = [], 0
    occurrences: Counter = Counter()
    for item in payload["data"]:
        try:
            if not isinstance(item, dict):
                raise ValueError
            tag = item["tag"]
            if tag not in ENDPOINTS[endpoint][1].split(","):
                raise ValueError
            metric, unit = METRICS[tag]
            raw_time = item["date"]
            if (
                not isinstance(raw_time, str)
                or len(raw_time) not in (12, 14)
                or not raw_time.isascii()
                or not raw_time.isdigit()
            ):
                raise ValueError
            pattern = "%Y%m%d%H%M" if len(raw_time) == 12 else "%Y%m%d%H%M%S"
            ts = datetime.strptime(raw_time, pattern)
            if ts.strftime(pattern) != raw_time or isinstance(item["keydata"], bool):
                raise ValueError
            value = float(item["keydata"])
            if not math.isfinite(value):
                raise ValueError
            model = item.get("model", "")
            if not isinstance(model, str):
                raise ValueError
            canonical = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            # The service provides no measurement ID. Preserve identical repeated
            # rows within a response, deduplicate replayed observations across scans.
            occurrences[canonical] += 1
            identity = f"{endpoint}|{canonical}|{occurrences[canonical]}"
            key = hashlib.sha256(identity.encode()).hexdigest()
            records.append((key, endpoint, metric, tag, ts.isoformat(), value, unit, model))
        except (KeyError, TypeError, ValueError, OverflowError):
            invalid += 1
    return records, len(payload["data"]), invalid


def _finished(con, endpoint, start, end, *, now, newest_end):
    row = con.execute(
        "SELECT attempted_at,status FROM attempts WHERE endpoint=? AND range_start=? "
        "AND range_end=? ORDER BY id DESC LIMIT 1",
        (endpoint, start, end),
    ).fetchone()
    return (
        row is not None
        and row[1] in ("complete", "empty")
        and (end != newest_end or row[0] > now - 86400)
    )


def _sync(
    data_dir,
    auth,
    *,
    start,
    end,
    max_requests=30,
    rescan=False,
    endpoints=None,
    session=None,
    clock=time.time,
):
    """Archive each HTTP body before parsing; resumable across bounded CLI calls.

    No automatic retry. A durable pre-send ledger enforces a shared rolling
    60/hour budget even after network errors, interruption, or process restart.
    """
    if not 1 <= max_requests <= 60:
        raise ValueError("request budget must be between 1 and 60")
    selected = tuple(dict.fromkeys(ENDPOINTS if endpoints is None else endpoints))
    if not selected or any(endpoint not in ENDPOINTS for endpoint in selected):
        raise ValueError("unknown or empty Health Planet endpoint selection")
    windows = month_windows(start, end)
    con = _connect(Path(data_dir))
    archive = Archive(Path(data_dir) / "healthplanet" / "archive")
    own_session = session is None
    session = session or requests.Session()
    made, reason, retry_after = 0, None, None
    now = clock()
    targets = [(endpoint, lo, hi) for lo, hi in windows for endpoint in selected]
    saved_plan = con.execute("SELECT value FROM settings WHERE key='rescan_plan'").fetchone()
    plan = json.loads(saved_plan[0]) if saved_plan else {}
    if rescan and (
        not plan.get("pending")
        or plan.get("start") != start.isoformat()
        or plan.get("end") != end.isoformat()
    ):
        plan = {"start": start.isoformat(), "end": end.isoformat(), "pending": targets}
    forced = {tuple(job) for job in plan.get("pending", [])}
    jobs = [
        (endpoint, lo, hi)
        for endpoint, lo, hi in targets
        if (endpoint, lo, hi) in forced
        or not _finished(con, endpoint, lo, hi, now=now, newest_end=windows[0][1])
    ]
    remaining = len(jobs)
    failures = []
    try:
        with con:
            con.execute(
                "INSERT OR REPLACE INTO settings VALUES ('rescan_plan', ?)", (json.dumps(plan),)
            )
            con.execute(
                "INSERT OR REPLACE INTO settings VALUES ('requested_start', ?)",
                (start.isoformat(),),
            )
            con.execute(
                "INSERT OR REPLACE INTO settings VALUES ('requested_end', ?)", (end.isoformat(),)
            )
        for endpoint, lo, hi in jobs:
            if made >= max_requests:
                reason = "request_cap"
                break
            now = clock()
            cooldown = con.execute(
                "SELECT value FROM settings WHERE key='blocked_until'"
            ).fetchone()
            recent = con.execute(
                "SELECT attempted_at FROM attempts WHERE attempted_at>? ORDER BY attempted_at",
                (now - 3600,),
            ).fetchall()
            blocked_until = float(cooldown[0]) if cooldown else 0
            if len(recent) >= 60:
                blocked_until = max(blocked_until, recent[0][0] + 3600)
            if blocked_until > now:
                reason, retry_after = "rate_limited", math.ceil(blocked_until - now)
                break
            token = auth.access_token()
            with con:
                attempt = con.execute(
                    "INSERT INTO attempts(endpoint,range_start,range_end,attempted_at,status) VALUES (?,?,?,?, 'partial')",
                    (endpoint, lo, hi, now),
                ).lastrowid
            made += 1
            status, http = "failed", None
            try:
                response = session.post(
                    f"https://www.healthplanet.jp/status/{endpoint}.json",
                    data={
                        "access_token": token,
                        "date": "1",
                        "from": lo,
                        "to": hi,
                        "tag": ENDPOINTS[endpoint][1],
                    },
                    timeout=60,
                    allow_redirects=False,
                )
            except requests.RequestException:
                # Exception text may include a prepared request with credentials.
                response = None
            if response is not None:
                ref = archive.put(response.content)
                http = response.status_code
                with con:
                    con.execute(
                        "UPDATE attempts SET http_status=?,sha256=?,object_path=?,byte_count=? WHERE id=?",
                        (http, ref.sha256, ref.relative_path, ref.byte_count, attempt),
                    )
                if http == 429:
                    status, reason = "rate_limited", "rate_limited"
                    retry_after = 3600
                    with con:
                        con.execute(
                            "INSERT OR REPLACE INTO settings VALUES ('blocked_until', ?)",
                            (str(clock() + retry_after),),
                        )
                elif http in (401, 403):
                    status = "permission_denied"
                    if http == 401:
                        reason = "authorization"
                elif 200 <= http < 300:
                    try:
                        rows, count, invalid = _parse(response.content, endpoint)
                    except (ValueError, UnicodeError):
                        pass
                    else:
                        status = "complete" if count else "empty"
                        with con:
                            con.executemany(
                                "INSERT OR IGNORE INTO measurements VALUES (?,?,?,?,?,?,?,?)", rows
                            )
                            con.execute(
                                "UPDATE attempts SET point_count=?,unparsed=?,status=? WHERE id=?",
                                (count, invalid, status, attempt),
                            )
            with con:
                con.execute("UPDATE attempts SET status=? WHERE id=?", (status, attempt))
                if status in ("complete", "empty") and (endpoint, lo, hi) in forced:
                    forced.remove((endpoint, lo, hi))
                    plan["pending"] = sorted(forced)
                    con.execute(
                        "INSERT OR REPLACE INTO settings VALUES ('rescan_plan', ?)",
                        (json.dumps(plan),),
                    )
            if status in ("complete", "empty"):
                remaining -= 1
            else:
                failures.append(
                    {"source": f"healthplanet:{endpoint}", "status": status, "http_status": http}
                )
            if reason:
                break
        return {
            "provider": "healthplanet",
            "status": "partial" if remaining else "available",
            "history_complete": False,
            "history_scope": "requested_ranges",
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "requests_made": made,
            "remaining_windows": remaining,
            "stopped_reason": reason,
            "retry_after_s": retry_after,
            "failures": failures,
        }
    finally:
        con.close()
        if own_session:
            session.close()


def _day(value):
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if value else None


def sync(
    data_dir,
    auth,
    *,
    start,
    end,
    max_requests=30,
    rescan=False,
    endpoints=None,
    session=None,
    clock=time.time,
):
    """Keep rate accounting and observation writes under one local writer lock."""
    folder = Path(data_dir) / "healthplanet"
    ensure_private_dir(folder)
    path = folder / "sync.lock"
    if path.is_symlink():
        raise ValueError("writer lock must not be a symlink")
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    with path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _sync(
            data_dir,
            auth,
            start=start,
            end=end,
            max_requests=max_requests,
            rescan=rescan,
            endpoints=endpoints,
            session=session,
            clock=clock,
        )


def export_data(data_dir: Path) -> dict:
    """Read a single provider snapshot; never export raw payloads or token files."""
    path = Path(data_dir) / "healthplanet" / "healthplanet.sqlite3"
    data = {
        "provider": "healthplanet",
        "timeBasis": "civil",
        "status": "not_connected",
        "historyComplete": False,
        "sources": [],
        "measurements": [],
        "unsupported": UNSUPPORTED,
        "quality": {"unparsedRecords": 0},
    }
    con = None
    try:
        if path.exists():
            con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            con.execute("BEGIN")
            data["measurements"] = [
                dict(row)
                for row in con.execute(
                    "SELECT id,metric,tag,timestamp,value,unit,model FROM measurements ORDER BY timestamp,metric,model,id"
                )
            ]
            data["status"] = "pending"
        for endpoint, (label, _) in ENDPOINTS.items():
            attempts = (
                list(
                    con.execute("SELECT * FROM attempts WHERE endpoint=? ORDER BY id", (endpoint,))
                )
                if con
                else []
            )
            last = attempts[-1] if attempts else None
            success = [row for row in attempts if row["status"] in ("complete", "empty")]
            intervals = sorted(
                {(row["range_start"], row["range_end"], row["status"]) for row in success}
            )
            status = last["status"] if last else "pending"
            if status in ("complete", "empty"):
                status = "unknown_history"
            source = {
                "stream_id": f"healthplanet:{endpoint}",
                "data_type": endpoint,
                "label": f"Health Planet / {label}",
                "representation": "healthplanet_response",
                "status": status,
                "method": "POST",
                "history_complete": False,
                "requested_start": _day(last["range_start"]) if last else None,
                "requested_end": _day(last["range_end"]) if last else None,
                "intervals": [
                    {"start": _day(lo), "end": _day(hi), "status": state}
                    for lo, hi, state in intervals
                ],
                "pages": int(last["sha256"] is not None) if last else 0,
                "points": (last["point_count"] or 0) if last else 0,
                "stored_pages": sum(row["sha256"] is not None for row in attempts),
                "stored_points": sum(row["point_count"] or 0 for row in attempts),
                "last_attempt_at": datetime.fromtimestamp(last["attempted_at"], UTC).isoformat()
                if last
                else None,
                "http_status": last["http_status"] if last else None,
                "reason": "全履歴の取得範囲は未確認です。"
                if success
                else "未取得または取得に失敗しています。",
                "projection_status": "available" if success else "pending",
            }
            data["sources"].append(source)
            # Per-response quality counts are observations, including rescans.
            data["quality"]["unparsedRecords"] += sum(row["unparsed"] for row in attempts)
        if con:
            requested = dict(con.execute("SELECT key,value FROM settings"))
            lo, hi = requested.get("requested_start"), requested.get("requested_end")
            if lo and hi:
                unfinished = bool(
                    json.loads(requested.get("rescan_plan", "{}")).get("pending")
                ) or any(
                    not _finished(con, endpoint, start, end, now=0, newest_end=None)
                    for start, end in month_windows(date.fromisoformat(lo), date.fromisoformat(hi))
                    for endpoint in ENDPOINTS
                )
                data["status"] = "partial" if unfinished else "available"
        return data
    finally:
        if con:
            con.close()
