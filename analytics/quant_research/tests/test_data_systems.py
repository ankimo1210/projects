from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from quant_textbook.data_systems import (
    TemporalRecord,
    audit_columnar_memory,
    audit_schema_evolution,
    point_in_time_snapshot,
    point_in_time_snapshot_sqlite,
)


def _timestamp(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def _records() -> tuple[TemporalRecord, ...]:
    return (
        TemporalRecord(
            "issuer-a",
            "assets",
            100.0,
            _timestamp("2020-03-31"),
            _timestamp("2020-05-01"),
            _timestamp("2020-05-01"),
            _timestamp("2020-05-04"),
        ),
        TemporalRecord(
            "issuer-a",
            "assets",
            110.0,
            _timestamp("2020-06-30"),
            _timestamp("2020-08-01"),
            _timestamp("2020-08-01"),
            _timestamp("2020-08-03"),
        ),
        TemporalRecord(
            "issuer-a",
            "assets",
            112.0,
            _timestamp("2020-06-30"),
            _timestamp("2020-08-01"),
            _timestamp("2020-09-10"),
            _timestamp("2020-09-11"),
        ),
        TemporalRecord(
            "issuer-a",
            "liabilities",
            70.0,
            _timestamp("2020-06-30"),
            _timestamp("2020-08-01"),
            _timestamp("2020-08-01"),
            _timestamp("2020-08-03"),
        ),
    )


def test_point_in_time_snapshot_excludes_future_revision() -> None:
    decisions = pd.DataFrame(
        {
            "decision_id": ["early", "late"],
            "entity_id": ["issuer-a", "issuer-a"],
            "decision_time": [_timestamp("2020-08-10"), _timestamp("2020-09-20")],
        }
    )

    snapshot = point_in_time_snapshot(_records(), decisions)

    early_assets = snapshot.loc[
        (snapshot["decision_id"] == "early") & (snapshot["field"] == "assets"), "value"
    ].item()
    late_assets = snapshot.loc[
        (snapshot["decision_id"] == "late") & (snapshot["field"] == "assets"), "value"
    ].item()
    assert early_assets == 110.0
    assert late_assets == 112.0
    assert (snapshot["availability_time"] <= snapshot["decision_time"]).all()


def test_sqlite_and_pandas_pit_implementations_agree() -> None:
    decisions = pd.DataFrame(
        {
            "decision_id": ["d1", "d2"],
            "entity_id": ["issuer-a", "issuer-a"],
            "decision_time": [_timestamp("2020-08-10"), _timestamp("2020-09-20")],
        }
    )

    pandas_result = point_in_time_snapshot(_records(), decisions)
    sqlite_result = point_in_time_snapshot_sqlite(_records(), decisions)

    pd.testing.assert_frame_equal(pandas_result, sqlite_result, check_dtype=False)


def test_temporal_record_requires_ordered_timezone_aware_times() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TemporalRecord(
            "issuer-a",
            "assets",
            1.0,
            pd.Timestamp("2020-01-01"),
            _timestamp("2020-01-02"),
            _timestamp("2020-01-02"),
            _timestamp("2020-01-03"),
        )
    with pytest.raises(ValueError, match="release_time"):
        TemporalRecord(
            "issuer-a",
            "assets",
            1.0,
            _timestamp("2020-01-03"),
            _timestamp("2020-01-02"),
            _timestamp("2020-01-02"),
            _timestamp("2020-01-04"),
        )


def test_schema_evolution_distinguishes_addition_removal_and_mutation() -> None:
    compatible = audit_schema_evolution(
        {"entity_id": "string", "value": "float64"},
        {"entity_id": "string", "value": "float64", "available_at": "timestamp[UTC]"},
    )
    incompatible = audit_schema_evolution(
        {"entity_id": "string", "value": "float64"},
        {"entity_id": "int64"},
    )

    assert compatible.compatible
    assert compatible.added_fields == ("available_at",)
    assert not incompatible.compatible
    assert incompatible.removed_fields == ("value",)
    assert incompatible.changed_types == (("entity_id", "string", "int64"),)


def test_columnar_memory_audit_preserves_per_column_accounting() -> None:
    frame = pd.DataFrame(
        {
            "entity": ["a", "b", "c"],
            "value": np.array([1.0, 2.0, 3.0]),
            "flag": [True, False, True],
        }
    )

    audit = audit_columnar_memory(frame)

    assert audit.row_count == 3
    assert audit.column_count == 3
    assert set(audit.bytes_by_column) == set(frame.columns)
    assert audit.total_columnar_bytes == sum(audit.bytes_by_column.values())
    assert audit.row_dictionary_bytes > 0
