"""User-triggered acquisition and explicit fallback to immutable observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta

from .calendars import SessionCalendar
from .fetch import FetchError, HttpClient
from .prices import PriceView
from .providers import PriceRequest, fetch_prices
from .storage import CacheKey, CacheUnavailableError, ResearchStore, Snapshot, _json


@dataclass(frozen=True, slots=True)
class IngestResult:
    snapshot: Snapshot
    view: PriceView
    stale: bool = False
    error: str | None = None


def cache_key(
    provider: str, request: PriceRequest, calendar: SessionCalendar | None = None
) -> CacheKey:
    schedule = None
    if calendar is not None:
        schedule = {
            "market": calendar.market,
            "version": calendar.version,
            "hash": calendar.digest,
            "sessions": [
                {"date": day, "open": bounds[0], "close": bounds[1]}
                for day, bounds in sorted(calendar.sessions.items())
                if request.start <= day <= request.end
            ],
        }
    metadata = {
        **asdict(request),
        "normalization_version": 1,
        "calendar": schedule or "crypto-utc-v1",
    }
    return CacheKey(
        provider,
        "prices",
        request.instrument.instrument_id,
        "1d",
        request.instrument.currency,
        request.adjustment,
        request_json=_json(metadata),
    )


def ingest_prices(
    store: ResearchStore,
    provider: str,
    request: PriceRequest,
    *,
    calendar: SessionCalendar | None = None,
    client: HttpClient | None = None,
    now=lambda: datetime.now(UTC),
    allow_stale: bool = False,
    max_age: timedelta = timedelta(days=1),
    resume: bool = False,
) -> IngestResult:
    key = cache_key(provider, request, calendar)
    resume_raw = None
    if resume:
        if provider != "jquants":
            raise ValueError("resume is supported only for J-Quants pagination")
        try:
            pending = store.pending_snapshot(key)
        except CacheUnavailableError:
            pass
        else:
            resume_raw = store.read_raw(pending)
    failure = None
    try:
        batch = fetch_prices(
            provider, request, calendar=calendar, client=client, now=now, resume_raw=resume_raw
        )
    except FetchError as error:
        failure = error
    if failure is None:
        snapshot = store.save(
            key, batch.raw, observed_at=batch.observed_at, prices=batch.bars, gaps=batch.gaps
        )
        return IngestResult(snapshot, store.snapshot_price_view(snapshot, batch.observed_at))
    observed = now()
    if failure.partial_raw:
        store.save(
            key, failure.partial_raw, observed_at=observed, complete=False, cursor=failure.cursor
        )
    if not allow_stale:
        raise failure
    snapshot = store.latest_snapshot(key, now=observed, max_age=max_age, allow_stale=True)
    # A failed refresh is visible even when the cached observation is younger than max_age.
    snapshot = replace(snapshot, stale=True)
    return IngestResult(
        snapshot, store.snapshot_price_view(snapshot, observed), True, failure.category
    )
