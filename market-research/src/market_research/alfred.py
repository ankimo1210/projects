"""ALFRED vintages: date-only release metadata and bounded pagination."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .contracts import MacroObservation, _utc
from .fetch import FetchError, HttpClient
from .storage import CacheKey, CacheUnavailableError, ResearchStore, Snapshot, _json

URL = "https://api.stlouisfed.org/fred/series/observations"
NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class AlfredRequest:
    series_id: str
    indicator: str
    start: date
    end: date
    unit: str
    frequency: str
    seasonal_adjustment: str
    realtime_start: date = date(1776, 7, 4)
    realtime_end: date = date(9999, 12, 31)

    def __post_init__(self) -> None:
        for name in ("series_id", "indicator", "unit", "frequency", "seasonal_adjustment"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if self.start > self.end or self.realtime_start > self.realtime_end:
            raise ValueError("invalid ALFRED date range")

    @property
    def key(self) -> CacheKey:
        return CacheKey(
            "alfred",
            "macro",
            self.indicator,
            self.frequency,
            self.unit,
            "none",
            request_json=_json(
                {
                    "series_id": self.series_id,
                    "start": self.start,
                    "end": self.end,
                    "realtime_start": self.realtime_start,
                    "realtime_end": self.realtime_end,
                    "seasonal_adjustment": self.seasonal_adjustment,
                    "normalization_version": 1,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class AlfredBatch:
    key: CacheKey
    raw: bytes
    rows: tuple[MacroObservation, ...]
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class MacroIngestResult:
    snapshot: Snapshot
    rows: tuple[MacroObservation, ...]
    stale: bool = False
    error: str | None = None


def _envelope(digest: str, limit: int, pages: list[str], next_offset: int) -> bytes:
    return _json(
        {"key_digest": digest, "limit": limit, "pages": pages, "next_offset": next_offset}
    ).encode()


def _parse_pages(pages: list[str], request: AlfredRequest) -> tuple[MacroObservation, ...]:
    values: dict[tuple[date, date], MacroObservation] = {}
    for page in pages:
        payload = json.loads(base64.b64decode(page))
        for item in payload["observations"]:
            if item["value"] == ".":
                continue
            period = date.fromisoformat(item["date"])
            published = date.fromisoformat(item["realtime_start"])
            if not request.start <= period <= request.end:
                raise ValueError("ALFRED returned an observation outside the requested range")
            if not request.realtime_start <= published <= request.realtime_end:
                raise ValueError("ALFRED returned a vintage outside the requested range")
            available = datetime.combine(published + timedelta(days=1), time.min, NY)
            row = MacroObservation(
                indicator=request.indicator,
                period_start=period,
                release_at=available.astimezone(UTC),
                value=float(item["value"]),
                source="alfred",
                vintage_id=published.isoformat(),
                vintage_kind="estimated",
                unit=request.unit,
                frequency=request.frequency,
                seasonal_adjustment=request.seasonal_adjustment,
                release_precision="date",
                source_release_date=published,
                source_ref=request.series_id,
            )
            identity = (period, published)
            previous = values.get(identity)
            if previous is not None and previous != row:
                raise ValueError("conflicting ALFRED vintage")
            values[identity] = row
    return tuple(values[key] for key in sorted(values))


def fetch_alfred(
    request: AlfredRequest,
    *,
    client: HttpClient | None = None,
    api_key: str | None = None,
    now=lambda: datetime.now(UTC),
    limit: int = 100000,
    resume_raw: bytes | None = None,
) -> AlfredBatch:
    """Fetch a full bounded realtime window; a partial envelope can be resumed."""
    secret = api_key if api_key is not None else os.environ.get("FRED_API_KEY")
    if not secret:
        raise ValueError("FRED_API_KEY is required")
    if not 1 <= limit <= 100000:
        raise ValueError("ALFRED limit must be between 1 and 100000")
    key = request.key
    pages: list[str] = []
    offset = 0
    if resume_raw is not None:
        previous = json.loads(resume_raw)
        if previous["key_digest"] != key.digest or previous["limit"] != limit:
            raise ValueError("ALFRED resume data does not match the request")
        pages = previous["pages"]
        offset = previous["next_offset"]
    http = client or HttpClient()
    for _ in range(1000):
        try:
            raw = http.get(
                URL,
                params={
                    "series_id": request.series_id,
                    "api_key": secret,
                    "file_type": "json",
                    "observation_start": request.start.isoformat(),
                    "observation_end": request.end.isoformat(),
                    "realtime_start": request.realtime_start.isoformat(),
                    "realtime_end": request.realtime_end.isoformat(),
                    "limit": limit,
                    "offset": offset,
                },
            )
        except FetchError as error:
            if not pages:
                raise
            raise FetchError(
                error.category,
                status=error.status,
                partial_raw=_envelope(key.digest, limit, pages, offset),
                cursor=str(offset),
            ) from None
        payload = json.loads(raw)
        if not isinstance(payload.get("observations"), list):
            raise ValueError("ALFRED response lacks observations")
        count = int(payload["count"])
        response_offset = int(payload["offset"])
        observations = payload["observations"]
        if response_offset != offset or count < 0 or len(observations) > limit:
            raise ValueError("invalid ALFRED page bounds")
        safe = raw.replace(secret.encode(), b"[REDACTED]")
        pages.append(base64.b64encode(safe).decode())
        offset += len(observations)
        if offset >= count:
            break
        if not observations:
            raise ValueError("ALFRED pagination made no progress")
        if sum(len(page) for page in pages) > 64 * 1024 * 1024:
            raise ValueError("ALFRED batch exceeds size limit")
    else:
        raise ValueError("ALFRED page limit exceeded")
    observed = _utc(now(), "observed_at")
    return AlfredBatch(
        key, _envelope(key.digest, limit, pages, offset), _parse_pages(pages, request), observed
    )


def ingest_alfred(
    store: ResearchStore,
    request: AlfredRequest,
    *,
    client: HttpClient | None = None,
    api_key: str | None = None,
    now=lambda: datetime.now(UTC),
    limit: int = 100000,
    resume: bool = False,
    allow_stale: bool = False,
    max_age: timedelta = timedelta(days=1),
) -> MacroIngestResult:
    resume_raw = None
    if resume:
        try:
            resume_raw = store.read_raw(store.pending_snapshot(request.key))
        except CacheUnavailableError:
            pass
    try:
        batch = fetch_alfred(
            request, client=client, api_key=api_key, now=now, limit=limit, resume_raw=resume_raw
        )
    except FetchError as error:
        observed = _utc(now(), "observed_at")
        if error.partial_raw:
            store.save(
                request.key,
                error.partial_raw,
                observed_at=observed,
                complete=False,
                cursor=error.cursor,
            )
        if not allow_stale:
            raise
        snapshot = store.latest_snapshot(
            request.key, now=observed, max_age=max_age, allow_stale=True
        )
        return MacroIngestResult(
            replace(snapshot, stale=True),
            store.snapshot_macro_view(snapshot, observed),
            True,
            error.category,
        )
    snapshot = store.save(batch.key, batch.raw, observed_at=batch.observed_at, macro=batch.rows)
    return MacroIngestResult(snapshot, store.snapshot_macro_view(snapshot, batch.observed_at))
