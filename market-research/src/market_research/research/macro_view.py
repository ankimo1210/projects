"""Offline macro table from explicit, observed immutable snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from market_research.storage import ResearchStore, Snapshot


@dataclass(frozen=True, slots=True)
class MacroSnapshotResult:
    table: pd.DataFrame
    current_snapshot_id: str
    previous_snapshot_id: str | None
    as_of: datetime
    indicator: str
    provider: str
    interval: str
    unit: str


def _validated_macro(store: ResearchStore, snapshot_id: str, when: datetime) -> Snapshot:
    snapshot = store.get_snapshot(snapshot_id)
    if not snapshot.complete or snapshot.key.dataset != "macro":
        raise ValueError("complete macro snapshot required")
    if snapshot.observed_at > when:
        raise ValueError("future macro snapshot cannot supply research values")
    return snapshot


def macro_snapshot_table(
    store: ResearchStore,
    snapshot_id: str,
    *,
    as_of: datetime,
    previous_snapshot_id: str | None = None,
) -> MacroSnapshotResult:
    """Compare current and explicit earlier vintages only after their observation."""
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    when = as_of.astimezone(UTC)
    current = _validated_macro(store, snapshot_id, when)
    previous = None
    if previous_snapshot_id is not None:
        if previous_snapshot_id == snapshot_id:
            raise ValueError("comparison requires a different previous snapshot")
        previous = _validated_macro(store, previous_snapshot_id, when)
        if previous.key != current.key:
            raise ValueError("previous macro snapshot key must match current key")
        if previous.observed_at >= current.observed_at:
            raise ValueError("previous macro snapshot must have an earlier observation")
    current_rows = store.snapshot_macro_view(current, when)
    previous_rows = (
        {row.period_start: row for row in store.snapshot_macro_view(previous, when)}
        if previous is not None
        else {}
    )
    records = []
    for row in current_rows:
        if row.unit is not None and row.unit != current.key.currency:
            raise ValueError("macro row unit differs from snapshot key")
        if row.frequency is not None and row.frequency != current.key.interval:
            raise ValueError("macro row frequency differs from snapshot key")
        old = previous_rows.get(row.period_start)
        if old is not None:
            if (
                old.unit is None
                or old.frequency is None
                or row.unit is None
                or row.frequency is None
            ):
                raise ValueError("macro comparison requires explicit unit and frequency")
            for name in ("unit", "frequency", "seasonal_adjustment"):
                if getattr(old, name) != getattr(row, name):
                    raise ValueError(f"macro comparison {name} differs between vintages")
        records.append(
            {
                "period_start": row.period_start,
                "value": row.value,
                "previous_value": old.value if old is not None else float("nan"),
                "revision": row.value - old.value if old is not None else float("nan"),
                "release_at": row.release_at,
                "observed_at": current.observed_at,
                "source_observed_at": row.observed_at,
                "vintage_kind": row.vintage_kind,
                "release_precision": row.release_precision,
                "source_release_date": row.source_release_date,
                "vintage_id": row.vintage_id,
                "source": row.source,
                "unit": row.unit or current.key.currency,
                "current_snapshot_id": current.snapshot_id,
                "previous_snapshot_id": previous.snapshot_id if previous is not None else None,
            }
        )
    table = pd.DataFrame.from_records(
        records,
        columns=[
            "period_start",
            "value",
            "previous_value",
            "revision",
            "release_at",
            "observed_at",
            "source_observed_at",
            "vintage_kind",
            "release_precision",
            "source_release_date",
            "vintage_id",
            "source",
            "unit",
            "current_snapshot_id",
            "previous_snapshot_id",
        ],
    ).set_index("period_start")
    return MacroSnapshotResult(
        table=table,
        current_snapshot_id=current.snapshot_id,
        previous_snapshot_id=previous.snapshot_id if previous is not None else None,
        as_of=when,
        indicator=current.key.identity,
        provider=current.key.provider,
        interval=current.key.interval,
        unit=current.key.currency,
    )
