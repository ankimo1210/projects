"""Point-in-time macro access.

Two views of the same indicator are kept separate:
  * **point-in-time** (all vintages, each tagged with its release_date)
  * **latest vintage** (today's best estimate, revisions included)

``as_of(frame, date)`` returns what an analyst could actually have known on
``date`` — for each period, the latest vintage whose ``release_date <= date``.
This is the single guard that prevents look-ahead via revised macro data. It
never forward-fills: periods with no release on/before ``date`` are absent.
"""

from __future__ import annotations

import pandas as pd

from ..utils.dates import to_ts


def as_of(frame: pd.DataFrame, date) -> pd.Series:
    """Series (indexed by period_start) visible at ``date``.

    For each period, take the row with the greatest release_date that is
    ``<= date``. Periods first released after ``date`` are excluded.
    """
    if frame.empty:
        return pd.Series(dtype="float64", name="value")
    d = to_ts(date)
    visible = frame[pd.to_datetime(frame["release_date"]) <= d]
    if visible.empty:
        return pd.Series(dtype="float64", name="value")
    # latest release per period
    chosen = (
        visible.sort_values("release_date")
        .groupby("period_start", as_index=True)
        .tail(1)
        .set_index("period_start")["value"]
        .sort_index()
    )
    chosen.name = "value"
    return chosen


def latest(frame: pd.DataFrame) -> pd.Series:
    """Latest-vintage series (most recent release per period; revisions included)."""
    if frame.empty:
        return pd.Series(dtype="float64", name="value")
    s = (
        frame.sort_values("release_date")
        .groupby("period_start", as_index=True)
        .tail(1)
        .set_index("period_start")["value"]
        .sort_index()
    )
    s.name = "value"
    return s


def revisions(frame: pd.DataFrame, period_start) -> pd.DataFrame:
    """All vintages for one period (to inspect how an estimate was revised)."""
    p = to_ts(period_start)
    sub = frame[pd.to_datetime(frame["period_start"]) == p]
    return sub.sort_values("release_date")[["release_date", "value", "vintage_available"]]
