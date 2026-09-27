"""Explicit single-series e-Stat snapshots with bounded page recovery."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .contracts import MacroObservation, _utc
from .fetch import FetchError, HttpClient
from .storage import CacheKey, CacheUnavailableError, ResearchStore, Snapshot, _json

URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
MISSING = frozenset({"", "-", "－", "***", "X", "..."})
DIMENSIONS = frozenset({"tab", "area", *(f"cat{i:02d}" for i in range(1, 16))})


@dataclass(frozen=True, slots=True)
class EstatRequest:
    stats_data_id: str
    indicator: str
    unit: str
    frequency: str
    classifications: tuple[tuple[str, str], ...]

    def __post_init__(self):
        for name in ("stats_data_id", "indicator", "unit"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if self.frequency not in {"annual", "monthly"}:
            raise ValueError("e-Stat frequency must be annual or monthly")
        if not self.classifications or len(set(name for name, _ in self.classifications)) != len(
            self.classifications
        ):
            raise ValueError("e-Stat classifications must be explicit and unique")
        if any(name not in DIMENSIONS or not code for name, code in self.classifications):
            raise ValueError("invalid e-Stat classification")

    @property
    def key(self) -> CacheKey:
        return CacheKey(
            "estat",
            "macro",
            self.indicator,
            self.frequency,
            self.unit,
            "none",
            request_json=_json(
                {
                    "stats_data_id": self.stats_data_id,
                    "classifications": sorted(self.classifications),
                    "normalization_version": 1,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class EstatResult:
    snapshot: Snapshot
    rows: tuple[MacroObservation, ...]


def parse_estat_time(code: str, frequency: str) -> date:
    """Accept only the documented Gregorian annual/monthly 10-digit forms."""
    if not isinstance(code, str) or len(code) != 10 or not code.isdigit() or code[4:6] != "00":
        raise ValueError("unsupported e-Stat time code")
    year = int(code[:4])
    tail = code[6:]
    if frequency == "annual" and tail == "0000":
        return date(year, 1, 1)
    if frequency == "monthly" and tail[:2] == tail[2:] and 1 <= int(tail[:2]) <= 12:
        return date(year, int(tail[:2]), 1)
    raise ValueError("unsupported e-Stat time code")


def _envelope(key: CacheKey, limit: int, pages: list[str], next_position: int) -> bytes:
    return _json(
        {
            "key_digest": key.digest,
            "limit": limit,
            "pages": pages,
            "next_position": next_position,
        }
    ).encode()


def _page_data(raw: bytes, request: EstatRequest) -> tuple[list[dict], int | None]:
    payload = json.loads(raw)
    body = payload["GET_STATS_DATA"]
    if int(body["RESULT"]["STATUS"]) != 0:
        raise FetchError("provider")
    data = body["STATISTICAL_DATA"]
    if data["TABLE_INF"]["@id"] != request.stats_data_id:
        raise ValueError("e-Stat table ID differs from request")
    values = data["DATA_INF"].get("VALUE", [])
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        raise ValueError("e-Stat VALUE must be a list")
    next_key = data["RESULT_INF"].get("NEXT_KEY")
    return values, int(next_key) if next_key is not None else None


def _parse_rows(
    pages: list[str], request: EstatRequest, observed: datetime, digest: str
) -> tuple[MacroObservation, ...]:
    classes = dict(request.classifications)
    values: dict[date, MacroObservation] = {}
    for page in pages:
        raw = base64.b64decode(page)
        observations, _ = _page_data(raw, request)
        for item in observations:
            extra = {
                key[1:]
                for key in item
                if key.startswith("@") and key not in ("@time", "@unit", "@annotation")
            }
            if extra != set(classes) or any(
                item.get("@" + name) != code for name, code in classes.items()
            ):
                raise ValueError("e-Stat classification differs from requested series")
            if str(item.get("@unit", "")) != request.unit:
                raise ValueError("e-Stat unit differs from request")
            period = parse_estat_time(item["@time"], request.frequency)
            cell = str(item.get("$", "")).strip()
            if cell in MISSING:
                continue
            value = float(cell.replace(",", ""))
            if not math.isfinite(value):
                raise ValueError("non-finite e-Stat value")
            row = MacroObservation(
                indicator=request.indicator,
                period_start=period,
                release_at=observed,
                value=value,
                source="estat",
                vintage_id=observed.isoformat(),
                vintage_kind="snapshot",
                unit=request.unit,
                frequency=request.frequency,
                seasonal_adjustment=None,
                release_precision="snapshot",
                observed_at=observed,
                raw_hash=digest,
                source_ref=request.stats_data_id,
            )
            previous = values.get(period)
            if previous is not None and previous.value != row.value:
                raise ValueError("conflicting e-Stat values for one period")
            values[period] = row
    if not values:
        raise ValueError("e-Stat response has no numeric values")
    return tuple(values[key] for key in sorted(values))


def ingest_estat(
    store: ResearchStore,
    request: EstatRequest,
    *,
    client: HttpClient | None = None,
    app_id: str | None = None,
    now=lambda: datetime.now(UTC),
    limit: int = 100000,
    resume: bool = False,
) -> EstatResult:
    secret = app_id if app_id is not None else os.environ.get("ESTAT_APP_ID")
    if not secret:
        raise ValueError("ESTAT_APP_ID is required")
    if not 1 <= limit <= 100000:
        raise ValueError("invalid e-Stat page limit")
    pages: list[str] = []
    position = 1
    if resume:
        try:
            pending = json.loads(store.read_raw(store.pending_snapshot(request.key)))
        except CacheUnavailableError:
            pass
        else:
            if pending["key_digest"] != request.key.digest or pending["limit"] != limit:
                raise ValueError("e-Stat pending snapshot does not match request")
            pages = pending["pages"]
            position = pending["next_position"]
    http = client or HttpClient()
    for _ in range(1000):
        params = {
            "appId": secret,
            "statsDataId": request.stats_data_id,
            "startPosition": position,
            "limit": limit,
            **{"cd" + name[0].upper() + name[1:]: code for name, code in request.classifications},
        }
        try:
            raw = http.get(URL, params=params)
            observations, next_key = _page_data(raw, request)
        except FetchError as error:
            if pages:
                partial = _envelope(request.key, limit, pages, position)
                store.save(
                    request.key,
                    partial,
                    observed_at=_utc(now(), "observed_at"),
                    complete=False,
                    cursor=str(position),
                )
            raise FetchError(
                error.category,
                status=error.status,
                partial_raw=partial if pages else None,
                cursor=str(position) if pages else None,
            ) from None
        safe = raw.replace(secret.encode(), b"[REDACTED]")
        pages.append(base64.b64encode(safe).decode())
        if next_key is None:
            break
        if not observations or next_key <= position:
            raise ValueError("e-Stat pagination made no progress")
        position = next_key
        if sum(len(page) for page in pages) > 64 * 1024 * 1024:
            raise ValueError("e-Stat batch exceeds size limit")
    else:
        raise ValueError("e-Stat page limit exceeded")
    observed = _utc(now(), "observed_at")
    raw = _envelope(request.key, limit, pages, position)
    digest = hashlib.sha256(raw).hexdigest()
    rows = _parse_rows(pages, request, observed, digest)
    snapshot = store.save(request.key, raw, observed_at=observed, macro=rows)
    return EstatResult(snapshot, rows)
