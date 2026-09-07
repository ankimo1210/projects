"""Publish private, consistent, full-resolution typed web-data generations.

Only the root manifest is replaced. Generation IDs are immutable; readers keep
using their original generation even while a new export is being assembled.
No raw response, credential, continuation token, or absolute source path is read.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from health.endpoints import KNOWN_DATA_TYPES
from health.store import Store
from health.web_analytics import build_analytics

DAILY_UNITS = dict(
    sorted(
        {
            "steps": "steps",
            "distance_km": "km",
            "calories": "kcal",
            "minutes_lightly_active": "min",
            "minutes_fairly_active": "min",
            "minutes_very_active": "min",
            "weight_kg": "kg",
            "fat_pct": "%",
            "resting_hr": "bpm",
            "hrv_rmssd": "ms",
            "hrv_deep_rmssd": "ms",
            "spo2_avg": "%",
            "spo2_lower_bound": "%",
            "spo2_upper_bound": "%",
            "temp_skin_relative": "°C",
            "breathing_rate": "breaths/min",
            "sleep_minutes": "min",
        }.items()
    )
)
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z", re.ASCII)
_REASONS = {
    "pending": "No archival attempt recorded.",
    "partial": "Acquisition has not finished.",
    "permission_denied": "Read permission was denied.",
    "unsupported": "This source has no supported retrieval method.",
    "failed": "Acquisition failed; inspect the local sync status.",
    "rate_limited": "The service request limit was reached.",
    "unknown_history": "The full historical range has not been verified.",
    "storage_error": "Local archival storage failed.",
}


def _safe_id(value: str) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ValueError("invalid generation or metric path component")
    return value


def _directory(path: Path) -> None:
    """Create only private directories and reject symlink traversal."""
    for component in [*reversed(path.parents), path]:
        if component.is_symlink():
            raise ValueError("export paths must not traverse symlinks")
        if not component.exists():
            component.mkdir(mode=0o700)
        elif not component.is_dir():
            raise ValueError("export parent must be a directory")


def _finite(value):
    """Convert pandas/scalar values into strictly finite standard JSON types."""
    if isinstance(value, dict):
        return {str(key): _finite(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_finite(item) for item in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value) -> None:
    _directory(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(
            _finite(value),
            stream,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _day(value) -> str | None:
    return None if value is None or pd.isna(value) else pd.Timestamp(value).date().isoformat()


def _pending_sources() -> list[dict]:
    # A legacy DB must not be migrated just to render its dashboard. When the
    # source catalog is installed, enumerate it without registering any rows.
    try:
        from health.source_catalog import load_sources
    except ModuleNotFoundError as error:
        if error.name != "health.source_catalog":
            raise
        sources = [
            {
                "stream_id": f"pending:{key}",
                "data_type": key,
                "label": label,
                "representation": "unverified",
                "method": None,
            }
            for key, (label, _) in sorted(KNOWN_DATA_TYPES.items())
        ]
    else:
        sources = [
            {
                "stream_id": source.key,
                "data_type": source.data_type,
                "label": source.label,
                "representation": source.representation,
                "method": source.preferred_method,
            }
            for source in load_sources()
        ]
    return [
        dict(
            source,
            status="pending",
            requested_start=None,
            requested_end=None,
            history_complete=False,
            intervals=[],
            pages=0,
            points=0,
            stored_pages=0,
            stored_points=0,
            last_attempt_at=None,
            reason=_REASONS["pending"],
            http_status=None,
            projection_status="not_implemented",
        )
        for source in sources
    ]


def _source_inventory(store) -> list[dict]:
    rows = {row["stream_id"]: row for row in _pending_sources()}
    exists = store.con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='main' AND table_name='archive_sources'"
    ).fetchone()[0]
    if exists:
        from health.archive_index import ArchiveIndex

        for row in ArchiveIndex(store.con, initialize=False).coverage():
            # Allowlist public fields. Error bodies, requests and pagination
            # state must never find their way into a static asset.
            clean = {
                key: row.get(key)
                for key in (
                    "stream_id",
                    "data_type",
                    "label",
                    "representation",
                    "status",
                    "method",
                    "history_complete",
                    "pages",
                    "points",
                    "stored_pages",
                    "stored_points",
                    "last_attempt_at",
                    "http_status",
                    "projection_status",
                )
            }
            clean["requested_start"] = _day(row.get("requested_start"))
            clean["requested_end"] = _day(row.get("requested_end"))
            clean["intervals"] = sorted(
                [
                    {
                        "start": _day(item.get("start")),
                        "end": _day(item.get("end")),
                        **(
                            {"status": item["status"]}
                            if item.get("status") in {"complete", "empty"}
                            else {}
                        ),
                    }
                    for item in row.get("intervals", [])
                ],
                key=lambda item: (item["start"] or "", item["end"] or "", item.get("status", "")),
            )
            clean["reason"] = _REASONS.get(row["status"])
            rows[row["stream_id"]] = clean
    return [rows[key] for key in sorted(rows)]


def _series_inventory(store: Store) -> list[dict]:
    rows = []
    for storage, frame in (
        ("daily", store.series_stats()),
        ("intraday", store.intraday_stats()),
        ("sleep", store.sleep_stats()),
    ):
        for row in frame.to_dict("records"):
            if not row["n"]:
                continue
            metric = row.get("metric", "sleep_sessions")
            unit = {"hr": "bpm", "sleep_sessions": "sessions"}.get(
                metric, DAILY_UNITS.get(metric, "unknown")
            )
            rows.append(
                {
                    "metric": metric,
                    "storage": storage,
                    "n": int(row["n"]),
                    "first_date": _day(row["first_date"]),
                    "last_date": _day(row["last_date"]),
                    "unit": unit,
                }
            )
    return sorted(rows, key=lambda row: (row["metric"], row["storage"]))


def _daily_data(store) -> tuple[pd.DataFrame, dict]:
    stored_metrics = [
        row[0]
        for row in store.con.execute(
            "SELECT DISTINCT metric FROM daily_series ORDER BY metric"
        ).fetchall()
    ]
    metrics = sorted(set(DAILY_UNITS) | set(stored_metrics))
    for metric in metrics:
        _safe_id(metric)
    frame = store.daily_frame(metrics)
    if not frame.empty:
        frame = (
            frame.set_index("date")
            .reindex(pd.date_range(frame["date"].min(), frame["date"].max(), freq="D"))
            .rename_axis("date")
            .reset_index()
        )
    return frame, {
        "dates": [_day(day) for day in frame["date"]],
        "series": {metric: frame[metric].tolist() for metric in metrics},
        "units": {metric: DAILY_UNITS.get(metric, "unknown") for metric in metrics},
    }


def _non_finite_count(store, table, *, metric=None, day=None) -> int:
    # SQL distinguishes actual NULL from IEEE NaN, unlike a pandas float
    # column. Only original non-finite observations are quality issues.
    if table == "daily_series":
        return store.con.execute(
            "SELECT count(*) FROM daily_series WHERE value IS NOT NULL AND NOT isfinite(value)"
        ).fetchone()[0]
    return store.con.execute(
        "SELECT count(*) FROM intraday WHERE metric=? AND CAST(ts AS DATE)=? "
        "AND value IS NOT NULL AND NOT isfinite(value)",
        [metric, day],
    ).fetchone()[0]


def export_web(
    store: Store,
    out_dir: Path,
    *,
    generation_id: str | None = None,
    generated_at: datetime | None = None,
) -> Path:
    """Return meta.json after committing a complete generation from one snapshot.

    The caller owns Store and must not run other operations on its connection
    concurrently. Other connections may write: this read transaction pins a
    consistent DuckDB snapshot, including inventory and per-day enumeration.
    """
    generation = _safe_id(uuid4().hex if generation_id is None else generation_id)
    timestamp = datetime.now(UTC) if generated_at is None else generated_at
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("generated_at must have a timezone")
    out_dir = Path(out_dir).absolute()
    _directory(out_dir)
    generations = out_dir / "generations"
    _directory(generations)
    target = generations / generation
    # mkdir is the atomic reservation: existing generations are immutable.
    target.mkdir(mode=0o700)
    manifest = out_dir / "meta.json"
    temporary_meta = out_dir / f".meta-{uuid4().hex}.json"
    published = False
    in_transaction = False
    files: dict[str, str] = {}
    quality = []

    def write(relative: str, data) -> None:
        _write_json(target / relative, {"schemaVersion": 1, "generation": generation, "data": data})
        files[relative] = relative

    try:
        store.con.execute("BEGIN TRANSACTION")
        in_transaction = True
        daily, daily_data = _daily_data(store)
        write("daily.json", daily_data)
        count = _non_finite_count(store, "daily_series")
        if count:
            quality.append({"path": "daily.json", "reason": "non_finite_number", "count": count})
        sleep = store.sleep_frame().sort_values(
            ["date", "start_ts", "end_ts", "provider_id"], kind="stable"
        )
        sessions = sleep.to_dict("records")
        for row in sessions:
            row["date"] = _day(row["date"])
        write("sleep.json", {"sessions": sessions, "timeBasis": "civil"})
        write("analytics.json", build_analytics(daily, sleep))

        # Enumerate only metric/day keys, then load one full-resolution day at a
        # time. All-history point payloads are never accumulated in memory.
        days = store.con.execute(
            "SELECT DISTINCT metric, CAST(ts AS DATE) AS day FROM intraday ORDER BY metric, day"
        ).fetchall()
        intraday = {}
        for metric, day in days:
            _safe_id(metric)
            day_string = day.isoformat()
            relative = f"intraday/{metric}/{day_string}.json"
            frame = store.intraday_frame(metric, day)
            points = []
            for ts, value in frame.itertuples(index=False, name=None):
                # Integer arithmetic retains DuckDB TIMESTAMP microseconds,
                # including the final microsecond before local midnight.
                micros = ((ts.hour * 60 + ts.minute) * 60 + ts.second) * 1_000_000 + ts.microsecond
                points.append([micros, value])
            write(
                relative,
                {
                    "date": day_string,
                    "metric": metric,
                    "timeBasis": "civil",
                    "timeUnit": "microseconds_since_local_midnight",
                    "points": points,
                },
            )
            entry = intraday.setdefault(
                metric,
                {
                    "unit": "bpm" if metric == "hr" else DAILY_UNITS.get(metric, "unknown"),
                    "days": [],
                },
            )
            entry["days"].append({"date": day_string, "path": relative, "count": len(points)})
            count = _non_finite_count(store, "intraday", metric=metric, day=day)
            if count:
                quality.append({"path": relative, "reason": "non_finite_number", "count": count})
        write("intraday-index.json", {"metrics": intraday})
        sources = _source_inventory(store)
        write(
            "inventory.json",
            {
                "sources": sources,
                "series": _series_inventory(store),
                "quality": sorted(quality, key=lambda row: row["path"]),
            },
        )
        current = [row for row in sources if row["representation"] != "legacy_json"]
        if current and all(
            row["history_complete"] and row["status"] in {"complete", "empty"} for row in current
        ):
            archive_status = "complete"
        elif all(row["status"] == "pending" for row in sources):
            archive_status = "pending"
        else:
            archive_status = "partial"
        meta = {
            "schemaVersion": 1,
            "generation": generation,
            "generatedAt": timestamp.isoformat(),
            "basePath": f"generations/{generation}/",
            "files": dict(sorted(files.items())),
            "freshness": {
                "archiveStatus": archive_status,
                "projectionStatus": "available"
                if not daily.empty or not sleep.empty or days
                else "empty",
            },
        }
        store.con.execute("COMMIT")
        in_transaction = False
        _write_json(temporary_meta, meta)
        for directory, _, _ in os.walk(target, topdown=False):
            _sync_directory(Path(directory))
        _sync_directory(generations)
        _sync_directory(out_dir)
        # Publication is the final fallible action: failures while preparing,
        # syncing or committing cannot replace a previously valid manifest.
        os.replace(temporary_meta, manifest)
        published = True
    finally:
        if in_transaction:
            store.con.execute("ROLLBACK")
        if not published:
            with contextlib.suppress(FileNotFoundError):
                temporary_meta.unlink()
            shutil.rmtree(target)
    return manifest
