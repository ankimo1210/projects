"""Data-quality diagnostics.

These functions REPORT problems; they never silently repair them (a core
platform rule). Callers decide what to do with missing data, gaps, or stale
series — the platform makes the issues explicit instead of hiding them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..utils.dates import business_days


@dataclass
class DataQualityReport:
    """A non-repairing summary of a (date-indexed) frame's health."""

    rows: int
    start: pd.Timestamp | None
    end: pd.Timestamp | None
    missing_pct: dict[str, float]  # per column
    duplicate_index: int
    monotonic_index: bool
    business_day_gaps: int  # missing weekdays inside [start, end]
    stale_days: int | None  # weekdays between last obs and `as_of` (None if not checked)
    schema_ok: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.schema_ok and self.duplicate_index == 0 and self.monotonic_index

    def summary(self) -> str:
        rng = f"{self.start.date()}..{self.end.date()}" if self.start is not None else "empty"
        worst = max(self.missing_pct.values(), default=0.0)
        flags = "OK" if self.ok and not self.warnings else f"{len(self.warnings)} warning(s)"
        return (
            f"rows={self.rows} range={rng} max_missing={worst:.1%} "
            f"gaps={self.business_day_gaps} dup={self.duplicate_index} [{flags}]"
        )


def assess(
    frame: pd.DataFrame,
    *,
    required_columns: list[str] | None = None,
    as_of: pd.Timestamp | None = None,
    stale_threshold_days: int = 5,
) -> DataQualityReport:
    """Diagnose a date-indexed DataFrame without modifying it."""
    warnings: list[str] = []
    idx = frame.index
    start = pd.Timestamp(idx.min()) if len(frame) else None
    end = pd.Timestamp(idx.max()) if len(frame) else None

    missing_pct = {
        str(c): (float(frame[c].isna().mean()) if len(frame) else 1.0) for c in frame.columns
    }
    for c, p in missing_pct.items():
        if p > 0.0:
            warnings.append(f"column '{c}' is {p:.1%} missing (NOT filled)")

    dup = int(idx.duplicated().sum())
    if dup:
        warnings.append(f"{dup} duplicate index timestamps")
    mono = bool(idx.is_monotonic_increasing) if len(frame) else True
    if not mono:
        warnings.append("index is not monotonically increasing")

    gaps = 0
    if start is not None and end is not None and end > start:
        expected = business_days(start, end)
        gaps = len(expected.difference(idx.normalize().unique()))
        if gaps:
            warnings.append(f"{gaps} missing business days inside the range (NOT filled)")

    schema_ok = True
    if required_columns:
        missing_cols = [c for c in required_columns if c not in frame.columns]
        if missing_cols:
            schema_ok = False
            warnings.append(f"missing required columns: {missing_cols}")

    stale = None
    if as_of is not None and end is not None:
        stale = int(len(business_days(end, as_of)) - 1)
        if stale > stale_threshold_days:
            warnings.append(f"data is stale: {stale} business days behind as_of")

    return DataQualityReport(
        rows=len(frame),
        start=start,
        end=end,
        missing_pct=missing_pct,
        duplicate_index=dup,
        monotonic_index=mono,
        business_day_gaps=gaps,
        stale_days=stale,
        schema_ok=schema_ok,
        warnings=warnings,
    )
