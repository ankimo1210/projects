"""Offline SEC filing values selected from explicit complete snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from market_research.storage import ResearchStore


@dataclass(frozen=True, slots=True)
class FundamentalField:
    name: str
    taxonomy: str
    concept: str
    unit: str
    form: str

    def __post_init__(self) -> None:
        for name in ("name", "taxonomy", "concept", "unit"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if self.form not in {"10-K", "10-Q"}:
            raise ValueError("fundamental form must be 10-K or 10-Q")

    def identity(self, cik: int) -> str:
        return f"CIK{cik:010d}:{self.taxonomy}:{self.concept}:{self.unit}:{self.form}"


@dataclass(frozen=True, slots=True)
class FundamentalRequest:
    instrument_id: str
    cik: int
    field: FundamentalField
    snapshot_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, str) or not self.instrument_id.strip():
            raise ValueError("instrument_id must be nonempty")
        if type(self.cik) is not int or self.cik <= 0:
            raise ValueError("CIK must be a positive integer")
        if self.snapshot_id is not None and (
            not isinstance(self.snapshot_id, str) or not self.snapshot_id.strip()
        ):
            raise ValueError("snapshot_id must be nonempty or None")


def load_fundamental_table(
    store: ResearchStore, requests: Sequence[FundamentalRequest], *, as_of: datetime
) -> pd.DataFrame:
    """Return latest disclosed periods without backdating snapshot observation."""
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    when = as_of.astimezone(UTC)
    if not requests:
        raise ValueError("at least one fundamental request is required")
    seen: set[tuple[str, str]] = set()
    records = []
    for request in requests:
        key = (request.instrument_id, request.field.name)
        if key in seen:
            raise ValueError("duplicate instrument and fundamental field")
        seen.add(key)
        record = {
            "instrument_id": request.instrument_id,
            "field": request.field.name,
            "as_of": when,
            "value": float("nan"),
            "unit": request.field.unit,
            "period_start": None,
            "period_end": None,
            "available_at": None,
            "observed_at": None,
            "vintage_kind": None,
            "accession": None,
            "snapshot_id": request.snapshot_id,
            "missing_reason": "not_collected" if request.snapshot_id is None else "not_available",
        }
        if request.snapshot_id is not None:
            snapshot = store.get_snapshot(request.snapshot_id)
            if snapshot.observed_at > when:
                raise ValueError("future snapshot cannot supply fundamental research values")
            expected_interval = "annual" if request.field.form == "10-K" else "quarterly"
            if not snapshot.complete or snapshot.key.dataset != "fundamental":
                raise ValueError("complete fundamental snapshot required")
            if snapshot.key.provider != "sec":
                raise ValueError("SEC fundamental snapshot required")
            if snapshot.key.identity != request.field.identity(request.cik):
                raise ValueError("fundamental CIK or field identity differs from request")
            if (
                snapshot.key.interval != expected_interval
                or snapshot.key.currency != request.field.unit
                or snapshot.key.adjustment != "none"
            ):
                raise ValueError("fundamental snapshot contract differs from request")
            rows = store.snapshot_fundamental_view(snapshot, when)
            record["observed_at"] = snapshot.observed_at
            if rows:
                latest_end = max(row.period_end for row in rows)
                latest = [row for row in rows if row.period_end == latest_end]
                if len(latest) != 1:
                    raise ValueError("ambiguous latest fundamental period")
                row = latest[0]
                record.update(
                    value=row.value,
                    period_start=row.period_start,
                    period_end=row.period_end,
                    available_at=row.available_at,
                    vintage_kind=row.vintage_kind,
                    accession=row.accession,
                    missing_reason="",
                )
        records.append(record)
    return pd.DataFrame.from_records(records).set_index(["instrument_id", "field"])
