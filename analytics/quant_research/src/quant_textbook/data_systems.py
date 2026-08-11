"""Bitemporal and columnar-data teaching primitives for B10."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TemporalRecord:
    """One feature value with observation, release, revision, and availability time."""

    entity_id: str
    field: str
    value: float
    observation_time: pd.Timestamp
    release_time: pd.Timestamp
    revision_time: pd.Timestamp
    availability_time: pd.Timestamp

    def __post_init__(self) -> None:
        if not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise ValueError("entity_id must be a non-empty string")
        if not isinstance(self.field, str) or not self.field.strip():
            raise ValueError("field must be a non-empty string")
        if not np.isfinite(self.value):
            raise ValueError("value must be finite")
        timestamps = (
            self.observation_time,
            self.release_time,
            self.revision_time,
            self.availability_time,
        )
        if any(not isinstance(timestamp, pd.Timestamp) for timestamp in timestamps):
            raise TypeError("all record times must be pandas.Timestamp values")
        if any(timestamp.tzinfo is None for timestamp in timestamps):
            raise ValueError("all record times must be timezone-aware")
        if self.release_time < self.observation_time:
            raise ValueError("release_time cannot precede observation_time")
        if self.revision_time < self.release_time:
            raise ValueError("revision_time cannot precede release_time")
        if self.availability_time < self.revision_time:
            raise ValueError("availability_time cannot precede revision_time")


@dataclass(frozen=True)
class SchemaEvolutionAudit:
    """Compatibility verdict for one explicit schema transition."""

    added_fields: tuple[str, ...]
    removed_fields: tuple[str, ...]
    changed_types: tuple[tuple[str, str, str], ...]
    compatible: bool


@dataclass(frozen=True)
class ColumnarMemoryAudit:
    """Observed pandas memory by column and row-oriented Python estimate."""

    row_count: int
    column_count: int
    bytes_by_column: dict[str, int]
    total_columnar_bytes: int
    row_dictionary_bytes: int


def _timestamp(value: Any, *, name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return timestamp


def temporal_records_frame(records: tuple[TemporalRecord, ...]) -> pd.DataFrame:
    """Convert validated records to a stable long-form table."""

    if not isinstance(records, tuple) or not records:
        raise ValueError("records must be a non-empty tuple")
    if not all(isinstance(record, TemporalRecord) for record in records):
        raise TypeError("records must contain only TemporalRecord values")
    frame = pd.DataFrame(
        [
            {
                "entity_id": record.entity_id,
                "field": record.field,
                "value": record.value,
                "observation_time": record.observation_time,
                "release_time": record.release_time,
                "revision_time": record.revision_time,
                "availability_time": record.availability_time,
            }
            for record in records
        ]
    )
    duplicates = frame.duplicated(
        ["entity_id", "field", "observation_time", "revision_time"], keep=False
    )
    if duplicates.any():
        raise ValueError("records contain duplicate bitemporal keys")
    return frame.sort_values(
        ["entity_id", "field", "observation_time", "revision_time"]
    ).reset_index(drop=True)


def point_in_time_snapshot(
    records: tuple[TemporalRecord, ...], decisions: pd.DataFrame
) -> pd.DataFrame:
    """Select the latest available record for each entity/field/decision."""

    record_frame = temporal_records_frame(records)
    if not isinstance(decisions, pd.DataFrame):
        raise TypeError("decisions must be a pandas DataFrame")
    if set(("decision_id", "entity_id", "decision_time")) - set(decisions.columns):
        raise ValueError("decisions require decision_id, entity_id, and decision_time")
    if decisions.empty:
        raise ValueError("decisions must be non-empty")
    if decisions["decision_id"].duplicated().any():
        raise ValueError("decision_id must be unique")
    decision_frame = decisions.loc[:, ["decision_id", "entity_id", "decision_time"]].copy()
    decision_frame["decision_time"] = [
        _timestamp(value, name="decision_time") for value in decision_frame["decision_time"]
    ]
    merged = decision_frame.merge(record_frame, on="entity_id", how="left", validate="many_to_many")
    eligible = merged.loc[
        merged["availability_time"].notna()
        & (merged["availability_time"] <= merged["decision_time"])
        & (merged["observation_time"] <= merged["decision_time"])
    ].copy()
    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "decision_id",
                "entity_id",
                "decision_time",
                "field",
                "value",
                "observation_time",
                "release_time",
                "revision_time",
                "availability_time",
            ]
        )
    ordered = eligible.sort_values(
        [
            "decision_id",
            "field",
            "observation_time",
            "revision_time",
            "availability_time",
        ]
    )
    selected = ordered.groupby(["decision_id", "field"], sort=False).tail(1)
    return (
        selected.loc[
            :,
            [
                "decision_id",
                "entity_id",
                "decision_time",
                "field",
                "value",
                "observation_time",
                "release_time",
                "revision_time",
                "availability_time",
            ],
        ]
        .sort_values(["decision_id", "field"])
        .reset_index(drop=True)
    )


def point_in_time_snapshot_sqlite(
    records: tuple[TemporalRecord, ...], decisions: pd.DataFrame
) -> pd.DataFrame:
    """Independent SQLite window-query implementation of the PIT snapshot."""

    record_frame = temporal_records_frame(records).copy()
    if not isinstance(decisions, pd.DataFrame) or decisions.empty:
        raise ValueError("decisions must be a non-empty pandas DataFrame")
    required = {"decision_id", "entity_id", "decision_time"}
    if required - set(decisions.columns):
        raise ValueError("decisions require decision_id, entity_id, and decision_time")
    decision_frame = decisions.loc[:, sorted(required)].copy()
    if decision_frame["decision_id"].duplicated().any():
        raise ValueError("decision_id must be unique")
    decision_frame["decision_time"] = [
        _timestamp(value, name="decision_time").tz_convert("UTC").isoformat()
        for value in decision_frame["decision_time"]
    ]
    for column in (
        "observation_time",
        "release_time",
        "revision_time",
        "availability_time",
    ):
        record_frame[column] = record_frame[column].map(
            lambda timestamp: timestamp.tz_convert("UTC").isoformat()
        )
    with sqlite3.connect(":memory:") as connection:
        record_frame.to_sql("records", connection, index=False)
        decision_frame.to_sql("decisions", connection, index=False)
        result = pd.read_sql_query(
            """
            WITH eligible AS (
                SELECT
                    d.decision_id,
                    d.entity_id,
                    d.decision_time,
                    r.field,
                    r.value,
                    r.observation_time,
                    r.release_time,
                    r.revision_time,
                    r.availability_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.decision_id, r.field
                        ORDER BY r.observation_time DESC,
                                 r.revision_time DESC,
                                 r.availability_time DESC
                    ) AS row_number
                FROM decisions AS d
                JOIN records AS r
                  ON d.entity_id = r.entity_id
                 AND r.availability_time <= d.decision_time
                 AND r.observation_time <= d.decision_time
            )
            SELECT decision_id, entity_id, decision_time, field, value,
                   observation_time, release_time, revision_time, availability_time
            FROM eligible
            WHERE row_number = 1
            ORDER BY decision_id, field
            """,
            connection,
        )
    for column in (
        "decision_time",
        "observation_time",
        "release_time",
        "revision_time",
        "availability_time",
    ):
        result[column] = pd.to_datetime(result[column], utc=True)
    return result


def audit_schema_evolution(
    previous: dict[str, str], current: dict[str, str]
) -> SchemaEvolutionAudit:
    """Reject removal or type mutation while allowing additive fields."""

    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise TypeError("schemas must be dictionaries")
    if not previous or not current:
        raise ValueError("schemas must be non-empty")
    if any(not isinstance(key, str) or not key for key in (*previous, *current)):
        raise ValueError("schema field names must be non-empty strings")
    removed = tuple(sorted(set(previous) - set(current)))
    added = tuple(sorted(set(current) - set(previous)))
    changed = tuple(
        (field, previous[field], current[field])
        for field in sorted(set(previous) & set(current))
        if previous[field] != current[field]
    )
    return SchemaEvolutionAudit(
        added_fields=added,
        removed_fields=removed,
        changed_types=changed,
        compatible=not removed and not changed,
    )


def audit_columnar_memory(frame: pd.DataFrame) -> ColumnarMemoryAudit:
    """Compare pandas per-column bytes with an explicit Python row representation."""

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("frame must be a non-empty pandas DataFrame")
    bytes_by_column = {
        str(column): int(frame[column].memory_usage(index=False, deep=True))
        for column in frame.columns
    }
    row_dictionaries = frame.to_dict(orient="records")
    row_bytes = sum(
        sum(len(str(key).encode()) + len(str(value).encode()) for key, value in row.items())
        for row in row_dictionaries
    )
    return ColumnarMemoryAudit(
        row_count=len(frame),
        column_count=frame.shape[1],
        bytes_by_column=bytes_by_column,
        total_columnar_bytes=sum(bytes_by_column.values()),
        row_dictionary_bytes=int(row_bytes),
    )


__all__ = [
    "ColumnarMemoryAudit",
    "SchemaEvolutionAudit",
    "TemporalRecord",
    "audit_columnar_memory",
    "audit_schema_evolution",
    "point_in_time_snapshot",
    "point_in_time_snapshot_sqlite",
    "temporal_records_frame",
]
