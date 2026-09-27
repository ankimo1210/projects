"""Close series assembled from snapshots available at each decision time."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from itertools import pairwise

import pandas as pd

from market_research.storage import ResearchStore, Snapshot

from .dataset import load_price_dataset


def build_pit_close_frame(
    store: ResearchStore,
    snapshot_ids_by_instrument: Mapping[str, Sequence[str]],
    decision_times: Sequence[datetime],
    *,
    currency: str,
    adjustment: str,
    expected_bar_ends: Mapping[str, Sequence[datetime]],
) -> pd.DataFrame:
    """Use observed snapshots and caller-verified session closes at each decision."""
    if any(
        not isinstance(decision, datetime) or decision.utcoffset() is None
        for decision in decision_times
    ):
        raise ValueError("decision times must be timezone-aware")
    times = tuple(decision.astimezone(UTC) for decision in decision_times)
    if not times or any(left >= right for left, right in pairwise(times)):
        raise ValueError("decision times must be nonempty, unique and ordered")
    if not snapshot_ids_by_instrument:
        raise ValueError("at least one instrument is required")
    if set(expected_bar_ends) != set(snapshot_ids_by_instrument):
        raise ValueError("expected close times must match selected instruments")
    expected: dict[str, tuple[datetime, ...]] = {}
    for instrument_id, ends in expected_bar_ends.items():
        if len(ends) != len(times) or any(
            not isinstance(end, datetime) or end.utcoffset() is None for end in ends
        ):
            raise ValueError(f"expected close times must be aware and aligned for {instrument_id}")
        normalized = tuple(end.astimezone(UTC) for end in ends)
        if any(end > decision for end, decision in zip(normalized, times, strict=True)):
            raise ValueError(f"expected close cannot follow decision for {instrument_id}")
        if any(left >= right for left, right in pairwise(normalized)):
            raise ValueError(f"expected close times must increase for {instrument_id}")
        expected[instrument_id] = normalized
    catalog: dict[str, tuple[Snapshot, ...]] = {
        instrument_id: tuple(store.get_snapshot(snapshot_id) for snapshot_id in ids)
        for instrument_id, ids in snapshot_ids_by_instrument.items()
    }
    rows: list[dict[str, float]] = []
    previous_ends: dict[str, datetime] = {}
    previous_providers: dict[str, str] = {}
    previous_intervals: dict[str, str] = {}
    for decision_index, decision_at in enumerate(times):
        selected: list[Snapshot] = []
        for instrument_id, snapshots in catalog.items():
            eligible = [
                snapshot
                for snapshot in snapshots
                if snapshot.complete and snapshot.observed_at <= decision_at
            ]
            if not eligible:
                raise ValueError(f"no snapshot available for {instrument_id}")
            latest_time = max(snapshot.observed_at for snapshot in eligible)
            latest_snapshots = [
                snapshot for snapshot in eligible if snapshot.observed_at == latest_time
            ]
            if len({snapshot.snapshot_id for snapshot in latest_snapshots}) != 1:
                raise ValueError(f"conflicting snapshots for {instrument_id}")
            snapshot = latest_snapshots[0]
            if snapshot.key.identity != instrument_id:
                raise ValueError(f"snapshot instrument differs from {instrument_id}")
            previous_provider = previous_providers.get(instrument_id)
            if previous_provider is not None and previous_provider != snapshot.key.provider:
                raise ValueError(f"provider switch for {instrument_id}")
            previous_providers[instrument_id] = snapshot.key.provider
            previous_interval = previous_intervals.get(instrument_id)
            if previous_interval is not None and previous_interval != snapshot.key.interval:
                raise ValueError(f"interval switch for {instrument_id}")
            previous_intervals[instrument_id] = snapshot.key.interval
            selected.append(snapshot)
        dataset = load_price_dataset(
            store,
            tuple(snapshot.snapshot_id for snapshot in selected),
            as_of=decision_at,
            currency=currency,
            adjustment=adjustment,
        )
        row = {}
        for instrument_id in snapshot_ids_by_instrument:
            bars = [bar for bar in dataset.bars if bar.instrument.instrument_id == instrument_id]
            if not bars:
                raise ValueError(f"no final close for {instrument_id}")
            latest = max(bars, key=lambda bar: bar.bar_end)
            if any(
                exclusion.bar.instrument.instrument_id == instrument_id
                and exclusion.bar.bar_end >= latest.bar_end
                for exclusion in dataset.exclusions
            ):
                raise ValueError(f"non_final newer bar for {instrument_id}")
            if any(
                gap.instrument.instrument_id == instrument_id
                and gap.session_date >= latest.session_date
                for gap in dataset.gaps
            ):
                raise ValueError(f"gap after final close for {instrument_id}")
            if latest.quality != "ok":
                raise ValueError(f"price quality is {latest.quality} for {instrument_id}")
            previous_end = previous_ends.get(instrument_id)
            if previous_end is not None and latest.bar_end <= previous_end:
                raise ValueError(f"new final close required for {instrument_id}")
            if latest.bar_end != expected[instrument_id][decision_index]:
                raise ValueError(f"expected close is unavailable for {instrument_id}")
            previous_ends[instrument_id] = latest.bar_end
            row[instrument_id] = latest.close
        rows.append(row)
    frame = pd.DataFrame(rows, index=pd.DatetimeIndex(times))
    frame.attrs["timing"] = "decision_close"
    return frame
