"""Macro features that are point-in-time *by construction*.

A macro indicator is monthly/quarterly and gets revised. To turn it into a
feature aligned to a (daily) trading index without look-ahead, we evaluate it
through :func:`quantkit.macro.store.as_of` at each date: the value on day ``d`` is the
most recent *period* whose ``release_date <= d``. That is not a silent
forward-fill — it is literally what an analyst knew on ``d`` — and we expose
``days_since_release`` so staleness is auditable, never hidden.

Appending a later vintage cannot change a feature value on an earlier date; the
causality test in ``tests/test_features.py`` checks exactly this.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..macro.store import as_of
from ..utils.dates import to_ts


def _visible_level(
    frame: pd.DataFrame, d: pd.Timestamp
) -> tuple[float, pd.Timestamp, pd.Timestamp]:
    """(value, period_start, release_date) of the latest period visible at ``d``."""
    s = as_of(frame, d)
    if s.empty:
        return (np.nan, pd.NaT, pd.NaT)
    period = s.index[-1]
    visible = frame[pd.to_datetime(frame["release_date"]) <= d]
    rel = visible.loc[visible["period_start"] == period, "release_date"].max()
    return (float(s.iloc[-1]), period, rel)


def pit_feature_frame(frame: pd.DataFrame, dates) -> pd.DataFrame:
    """Point-in-time macro panel aligned to ``dates``.

    Columns: ``value`` (latest visible release), ``period_start`` (which period it
    refers to), ``release_date`` (when it became known), and ``days_since_release``
    (staleness in days). Dates before the first release are NaN — not back-filled.
    """
    idx = pd.DatetimeIndex([to_ts(d) for d in dates])
    rows = [_visible_level(frame, d) for d in idx]
    out = pd.DataFrame(rows, index=idx, columns=["value", "period_start", "release_date"])
    rel = pd.to_datetime(out["release_date"])
    out["days_since_release"] = (out.index.to_series() - rel).dt.days
    return out


def pit_level(frame: pd.DataFrame, dates) -> pd.Series:
    """Just the point-in-time level aligned to ``dates`` (see :func:`pit_feature_frame`)."""
    return pit_feature_frame(frame, dates)["value"]


def pit_change(frame: pd.DataFrame, dates, periods: int = 1) -> pd.Series:
    """Change of the macro level over ``periods`` *released periods*, aligned to dates.

    For each date we compare the latest visible period's value to the value
    ``periods`` periods earlier (e.g. ``periods=12`` on monthly data ≈ YoY). Built
    on the as_of-aligned period series, so it inherits the no-look-ahead guard.
    """
    feat = pit_feature_frame(frame, dates)
    out = pd.Series(np.nan, index=feat.index, name="value")
    for d in feat.index:
        s = as_of(frame, d)
        if len(s) > periods:
            prev = s.iloc[-1 - periods]
            if prev != 0 and not np.isnan(prev):
                out.loc[d] = s.iloc[-1] / prev - 1.0
    return out


def pit_zscore(frame: pd.DataFrame, dates, window: int) -> pd.Series:
    """Trailing z-score of the latest visible release vs the prior ``window`` releases.

    A crude "surprise" measure: how unusual the current print is relative to the
    recent (already-released) history. Trailing window → causal.
    """
    feat = pit_feature_frame(frame, dates)
    out = pd.Series(np.nan, index=feat.index, name="value")
    for d in feat.index:
        s = as_of(frame, d)
        if len(s) >= window:
            recent = s.iloc[-window:]
            sd = recent.std()
            if sd and not np.isnan(sd):
                out.loc[d] = (s.iloc[-1] - recent.mean()) / sd
    return out
