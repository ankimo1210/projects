"""Date helpers used across the data layer."""

from __future__ import annotations

import pandas as pd


def to_ts(d) -> pd.Timestamp:
    """Coerce a date-like to a tz-naive pandas Timestamp (normalized to midnight)."""
    return pd.Timestamp(d).tz_localize(None).normalize()


def business_days(start, end) -> pd.DatetimeIndex:
    """Calendar business days (Mon-Fri) between start and end inclusive.

    A market-agnostic reference index. Real exchange holidays are NOT removed
    here; gaps vs this index are reported as data-quality info, never silently
    filled.
    """
    return pd.bdate_range(to_ts(start), to_ts(end))
