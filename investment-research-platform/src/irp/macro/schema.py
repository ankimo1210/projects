"""Macro observation schema.

Every macro observation carries enough metadata to be used point-in-time: the
period it refers to, the date it was RELEASED, and the vintage it belongs to.
The platform never lets a value be used before its ``release_date``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

#: canonical column order for a macro frame (one row per observation/vintage)
MACRO_COLUMNS = [
    "indicator_name",
    "country",
    "period_start",
    "period_end",
    "release_date",
    "vintage_date",
    "value",
    "unit",
    "frequency",
    "seasonal_adjustment",
    "source",
    "source_url",
    "last_updated",
    "vintage_available",
]


@dataclass
class MacroObservation:
    indicator_name: str
    country: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    release_date: pd.Timestamp
    value: float
    source: str
    frequency: str = ""
    unit: str = ""
    seasonal_adjustment: str = ""
    source_url: str = ""
    vintage_date: pd.Timestamp | None = None
    last_updated: pd.Timestamp | None = None
    #: True if release_date is a real vintage date; False if it is an estimate
    #: (so callers know the point-in-time guarantee is approximate for this row).
    vintage_available: bool = False

    def as_row(self) -> dict:
        return asdict(self)


def to_macro_frame(observations: list[MacroObservation]) -> pd.DataFrame:
    """Build a normalized macro frame (sorted by period, then release)."""
    if not observations:
        return pd.DataFrame(columns=MACRO_COLUMNS)
    df = pd.DataFrame([o.as_row() for o in observations])
    for c in ("period_start", "period_end", "release_date", "vintage_date", "last_updated"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df = df.reindex(columns=MACRO_COLUMNS)
    return df.sort_values(["period_start", "release_date"]).reset_index(drop=True)
