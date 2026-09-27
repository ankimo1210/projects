"""SEC companyfacts ingestion with filed-date precision kept explicit."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .contracts import FundamentalObservation, _utc
from .fetch import HttpClient
from .storage import CacheKey, ResearchStore, Snapshot, _json

NY = ZoneInfo("America/New_York")
BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


@dataclass(frozen=True, slots=True)
class SecRequest:
    cik: int
    taxonomy: str
    concept: str
    unit: str
    form: str

    def __post_init__(self):
        if type(self.cik) is not int or self.cik <= 0:
            raise ValueError("CIK must be a positive integer")
        for name in ("taxonomy", "concept", "unit"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if self.form not in {"10-K", "10-Q"}:
            raise ValueError("only 10-K and 10-Q forms are supported")

    @property
    def identity(self) -> str:
        return f"CIK{self.cik:010d}:{self.taxonomy}:{self.concept}:{self.unit}:{self.form}"

    @property
    def key(self) -> CacheKey:
        return CacheKey(
            "sec",
            "fundamental",
            self.identity,
            "annual" if self.form == "10-K" else "quarterly",
            self.unit,
            "none",
            request_json=_json({"normalization_version": 1}),
        )


@dataclass(frozen=True, slots=True)
class SecResult:
    snapshot: Snapshot
    rows: tuple[FundamentalObservation, ...]


def _parse_companyfacts(raw: bytes, request: SecRequest) -> tuple[FundamentalObservation, ...]:
    payload = json.loads(raw)
    if int(payload.get("cik", -1)) != request.cik:
        raise ValueError("SEC CIK does not match request")
    try:
        facts = payload["facts"][request.taxonomy][request.concept]["units"][request.unit]
    except (KeyError, TypeError) as exc:
        raise ValueError("SEC concept or unit unavailable") from exc
    if not isinstance(facts, list):
        raise ValueError("SEC concept units must be a list")
    rows = []
    for item in facts:
        if item.get("form") != request.form:
            continue
        if not all(item.get(name) for name in ("end", "filed", "accn")):
            raise ValueError("SEC fact lacks filing metadata")
        filed = date.fromisoformat(item["filed"])
        available = datetime.combine(filed + timedelta(days=1), time.min, NY)
        rows.append(
            FundamentalObservation(
                cik=request.cik,
                taxonomy=request.taxonomy,
                concept=request.concept,
                unit=request.unit,
                period_start=date.fromisoformat(item["start"]) if item.get("start") else None,
                period_end=date.fromisoformat(item["end"]),
                filed=filed,
                available_at=available.astimezone(UTC),
                observed_at=None,
                value=float(item["val"]),
                form=request.form,
                accession=item["accn"],
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.period_end, row.available_at, row.accession)))


def ingest_sec_companyfacts(
    store: ResearchStore,
    request: SecRequest,
    *,
    client: HttpClient | None = None,
    user_agent: str | None = None,
    now=lambda: datetime.now(UTC),
) -> SecResult:
    agent = user_agent if user_agent is not None else os.environ.get("SEC_USER_AGENT")
    if not agent or "@" not in agent or " " not in agent:
        raise ValueError("SEC_USER_AGENT must identify the researcher and contact")
    raw = (client or HttpClient()).get(BASE.format(cik=request.cik), headers={"User-Agent": agent})
    rows = _parse_companyfacts(raw, request)
    observed = _utc(now(), "observed_at")
    if any(row.filed > observed.astimezone(NY).date() for row in rows):
        raise ValueError("SEC filing date lies after this snapshot")
    snapshot = store.save(request.key, raw, observed_at=observed, fundamentals=rows)
    return SecResult(snapshot, rows)
