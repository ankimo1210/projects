"""Forward-only train/test partitions with purged future labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .signals import SignalDataset


@dataclass(frozen=True, slots=True)
class WalkForwardSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    test_start_at: datetime


def _int_at_least(value: int, name: str, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")


def walk_forward_splits(
    dataset: SignalDataset,
    *,
    train_size: int,
    test_size: int,
    embargo: int = 0,
    step: int | None = None,
    expanding: bool = False,
    lockbox_start: datetime | None = None,
) -> tuple[WalkForwardSplit, ...]:
    """Create nonoverlapping forward tests from a point-in-time signal dataset."""
    if not isinstance(dataset, SignalDataset):
        raise TypeError("a SignalDataset is required")
    if dataset.mode != "point_in_time" or not dataset.snapshot_ids:
        raise ValueError("point-in-time snapshot provenance is required")
    table = dataset.table
    horizon = dataset.horizon
    _int_at_least(horizon, "horizon", 1)
    _int_at_least(train_size, "train_size", 1)
    _int_at_least(test_size, "test_size", 1)
    _int_at_least(embargo, "embargo", 0)
    if step is None:
        step = test_size
    _int_at_least(step, "step", test_size)
    if not isinstance(expanding, bool):
        raise ValueError("expanding must be boolean")
    if not isinstance(table.index, pd.DatetimeIndex) or table.index.tz is None:
        raise ValueError("decision index must be timezone-aware")
    if table.index.has_duplicates or not table.index.is_monotonic_increasing:
        raise ValueError("decision index must be unique and ordered")
    if "label" not in table or "label_available_at" not in table:
        raise ValueError("label and label availability are required")
    availability = table["label_available_at"]
    if not isinstance(availability.dtype, pd.DatetimeTZDtype):
        raise ValueError("label availability must be timezone-aware")
    if lockbox_start is not None:
        if not isinstance(lockbox_start, datetime) or lockbox_start.utcoffset() is None:
            raise ValueError("lockbox_start must be timezone-aware")
        lockbox_start = lockbox_start.astimezone(UTC)
    times = table.index.tz_convert(UTC)
    for index, available_at in enumerate(availability):
        label = table["label"].iloc[index]
        if index + horizon >= len(times):
            if pd.notna(available_at) or pd.notna(label):
                raise ValueError("tail future label cannot be known")
        elif pd.notna(label) and (pd.isna(available_at) or available_at < times[index + horizon]):
            raise ValueError("label availability precedes its future close")
    results = []
    first_test = train_size + horizon + embargo
    for test_start in range(first_test, len(times) - horizon - test_size + 1, step):
        test_end = test_start + test_size
        if lockbox_start is not None and times[test_end - 1] >= lockbox_start:
            break
        train_end = test_start - horizon - embargo
        train_start = 0 if expanding else train_end - train_size
        train_indices = tuple(range(train_start, train_end))
        test_indices = tuple(range(test_start, test_end))
        test_time = times[test_start].to_pydatetime()
        for index in test_indices:
            if pd.isna(availability.iloc[index]) or not np.isfinite(table["label"].iloc[index]):
                raise ValueError("test label is incomplete")
        for index in train_indices:
            available_at = availability.iloc[index]
            if (
                pd.isna(available_at)
                or available_at >= test_time
                or not np.isfinite(table["label"].iloc[index])
                or (lockbox_start is not None and available_at >= lockbox_start)
            ):
                raise ValueError("training label availability crosses the test or lockbox boundary")
        results.append(WalkForwardSplit(train_indices, test_indices, test_time))
    if not results:
        raise ValueError("short series has no complete walk-forward split")
    return tuple(results)
