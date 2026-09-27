"""Saved macro research compares only observed, released matching snapshots."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import MacroObservation
from market_research.storage import CacheKey, ResearchStore

T1 = datetime(2026, 9, 25, 12, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
KEY = CacheKey("alfred", "macro", "GDP", "quarterly", "billions", "none")


def _row(value=100.0, *, release_at=T1, vintage_id="initial"):
    return MacroObservation(
        "GDP",
        date(2025, 1, 1),
        release_at,
        value,
        "alfred",
        vintage_id,
        unit="billions",
        frequency="quarterly",
        seasonal_adjustment="sa",
        observed_at=release_at,
    )


def test_macro_snapshot_comparison_keeps_release_and_observation_times(tmp_path):
    from market_research.research.macro_view import macro_snapshot_table

    initial = _row()
    revision = _row(120, release_at=T2, vintage_id="revision")
    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, macro=(initial,))
        second = store.save(KEY, b"second", observed_at=T2, macro=(initial, revision))
        result = macro_snapshot_table(
            store, second.snapshot_id, as_of=T2, previous_snapshot_id=first.snapshot_id
        )
        row = result.table.loc[date(2025, 1, 1)]
        assert row["value"] == 120
        assert row["previous_value"] == 100
        assert row["revision"] == 20
        assert row["release_at"] == T2
        assert row["observed_at"] == T2
        assert row["source"] == "alfred"
        assert row["unit"] == "billions"
        assert result.current_snapshot_id == second.snapshot_id
        assert result.previous_snapshot_id == first.snapshot_id
        before = macro_snapshot_table(store, first.snapshot_id, as_of=T1)
        assert before.table.loc[date(2025, 1, 1), "value"] == 100
        assert pd.isna(before.table.loc[date(2025, 1, 1), "revision"])


def test_future_partial_or_mismatched_macro_snapshot_fails_closed(tmp_path):
    from market_research.research.macro_view import macro_snapshot_table

    with ResearchStore(tmp_path) as store:
        first = store.save(KEY, b"first", observed_at=T1, macro=(_row(),))
        second = store.save(
            KEY,
            b"second",
            observed_at=T2,
            macro=(_row(), _row(120, release_at=T2, vintage_id="revision")),
        )
        other = store.save(
            replace(KEY, provider="mof"),
            b"other",
            observed_at=T1,
            macro=(replace(_row(), source="mof"),),
        )
        partial = store.save(
            KEY, b"partial", observed_at=T2, macro=(_row(),), complete=False, cursor="next"
        )
        with pytest.raises(ValueError, match="future"):
            macro_snapshot_table(store, second.snapshot_id, as_of=T1)
        with pytest.raises(ValueError, match="complete"):
            macro_snapshot_table(store, partial.snapshot_id, as_of=T2)
        with pytest.raises(ValueError, match="key"):
            macro_snapshot_table(
                store, second.snapshot_id, as_of=T2, previous_snapshot_id=other.snapshot_id
            )
        with pytest.raises(ValueError, match="earlier"):
            macro_snapshot_table(
                store, first.snapshot_id, as_of=T2, previous_snapshot_id=second.snapshot_id
            )
        with pytest.raises(ValueError, match="different"):
            macro_snapshot_table(
                store, first.snapshot_id, as_of=T2, previous_snapshot_id=first.snapshot_id
            )
        with pytest.raises(ValueError, match="timezone-aware"):
            macro_snapshot_table(store, first.snapshot_id, as_of=T2.replace(tzinfo=None))
