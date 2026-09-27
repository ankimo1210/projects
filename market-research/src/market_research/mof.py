"""MoF JGB yield snapshots from the historical and current CP932 CSVs."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .contracts import MacroObservation, _utc
from .fetch import FetchError, HttpClient
from .storage import CacheKey, CacheUnavailableError, ResearchStore, Snapshot, _json

BASE = "https://www.mof.go.jp/jgbs/reference/interest_rate"
HISTORY_URL = f"{BASE}/data/jgbcm_all.csv"
CURRENT_URL = f"{BASE}/jgbcm.csv"
ERA_OFFSET = {"S": 1925, "H": 1988, "R": 2018}


@dataclass(frozen=True, slots=True)
class MoFRequest:
    tenor_years: float
    start: date | None = None
    end: date | None = None

    def __post_init__(self):
        if not math.isfinite(self.tenor_years) or self.tenor_years <= 0:
            raise ValueError("tenor_years must be positive")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("invalid MoF date range")

    @property
    def indicator(self) -> str:
        tenor = f"{self.tenor_years:g}"
        return f"JP_JGB_{tenor}Y"

    @property
    def key(self) -> CacheKey:
        return CacheKey(
            "mof_jgb",
            "macro",
            self.indicator,
            "daily",
            "percent",
            "none",
            request_json=_json(
                {
                    "tenor_years": self.tenor_years,
                    "start": self.start,
                    "end": self.end,
                    "normalization_version": 1,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class MoFResult:
    snapshot: Snapshot
    rows: tuple[MacroObservation, ...]


def _wareki(token: str) -> date:
    token = token.strip()
    if token[:1] not in ERA_OFFSET:
        raise ValueError("unknown Japanese era")
    year, month, day = (int(part) for part in token[1:].split("."))
    return date(ERA_OFFSET[token[0]] + year, month, day)


def _parse_csv(raw: bytes, tenor: float) -> dict[date, float]:
    rows = list(csv.reader(io.StringIO(raw.decode("cp932"))))
    if len(rows) < 2:
        raise ValueError("MoF CSV lacks a header")
    headers = rows[1]
    matches = [i for i, cell in enumerate(headers) if cell.strip() == f"{tenor:g}年"]
    if len(matches) != 1:
        raise ValueError("MoF CSV has no unique requested tenor")
    index = matches[0]
    values = {}
    for cells in rows[2:]:
        if not cells or cells[0][:1] not in ERA_OFFSET:
            continue
        day = _wareki(cells[0])
        if index >= len(cells) or cells[index].strip() in ("", "-"):
            continue
        value = float(cells[index].strip())
        if not math.isfinite(value):
            raise ValueError("non-finite MoF yield")
        if day in values and values[day] != value:
            raise ValueError("conflicting MoF yield in CSV")
        values[day] = value
    return values


def _envelope(key: CacheKey, history: bytes, current: bytes | None) -> bytes:
    return _json(
        {
            "key_digest": key.digest,
            "history": base64.b64encode(history).decode(),
            "current": base64.b64encode(current).decode() if current is not None else None,
        }
    ).encode()


def ingest_mof_jgb(
    store: ResearchStore,
    request: MoFRequest,
    *,
    client: HttpClient | None = None,
    now=lambda: datetime.now(UTC),
    resume: bool = False,
) -> MoFResult:
    http = client or HttpClient()
    pending = None
    if resume:
        try:
            pending = json.loads(store.read_raw(store.pending_snapshot(request.key)))
        except CacheUnavailableError:
            pass
    if pending is not None:
        if pending["key_digest"] != request.key.digest:
            raise ValueError("MoF pending snapshot does not match request")
        history = base64.b64decode(pending["history"])
    else:
        history = http.get(HISTORY_URL)
    try:
        current = http.get(CURRENT_URL)
    except FetchError as error:
        raw = _envelope(request.key, history, None)
        store.save(
            request.key,
            raw,
            observed_at=_utc(now(), "observed_at"),
            complete=False,
            cursor="current",
        )
        raise FetchError(
            error.category, status=error.status, partial_raw=raw, cursor="current"
        ) from None
    historical = _parse_csv(history, request.tenor_years)
    recent = _parse_csv(current, request.tenor_years)
    values = historical.copy()
    for day, value in recent.items():
        if day in values and values[day] != value:
            raise ValueError("conflicting MoF yields across files")
        values[day] = value
    observed = _utc(now(), "observed_at")
    raw = _envelope(request.key, history, current)
    digest = hashlib.sha256(raw).hexdigest()
    rows = tuple(
        MacroObservation(
            indicator=request.indicator,
            period_start=day,
            release_at=observed,
            value=value,
            source="mof_jgb",
            vintage_id=observed.isoformat(),
            vintage_kind="snapshot",
            unit="percent",
            frequency="daily",
            seasonal_adjustment="none",
            release_precision="snapshot",
            observed_at=observed,
            raw_hash=digest,
            source_ref=HISTORY_URL if day in historical else CURRENT_URL,
        )
        for day, value in sorted(values.items())
        if (request.start is None or day >= request.start)
        and (request.end is None or day <= request.end)
    )
    snapshot = store.save(request.key, raw, observed_at=observed, macro=rows)
    return MoFResult(snapshot, rows)
