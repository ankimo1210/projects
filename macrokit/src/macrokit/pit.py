"""Point-in-time access. The single guard against look-ahead via revised data.

`as_of(con, indicator, when)` answers "what could an analyst actually have known
on this date": for each period, the latest vintage whose release_date is at or
before `when`. Periods first released after `when` are absent -- this function
never forward-fills, because inventing a value for a period nobody had yet is
exactly the bug it exists to prevent.
"""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

_AS_OF_SQL = """
SELECT period_start, value
FROM (
  SELECT period_start, value,
         row_number() OVER (PARTITION BY period_start ORDER BY release_date DESC) AS rn
  FROM observations
  WHERE indicator = ? AND release_date <= ?
)
WHERE rn = 1
ORDER BY period_start
"""

_LATEST_SQL = """
SELECT period_start, value
FROM (
  SELECT period_start, value,
         row_number() OVER (PARTITION BY period_start ORDER BY release_date DESC) AS rn
  FROM observations
  WHERE indicator = ?
)
WHERE rn = 1
ORDER BY period_start
"""

_REVISIONS_SQL = """
SELECT release_date, value, vintage_seq, vintage_kind
FROM observations
WHERE indicator = ? AND period_start = ?
ORDER BY release_date
"""


def _to_series(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype="float64", name="value")
    series = frame.set_index("period_start")["value"]
    series.name = "value"
    # DuckDB's .df() can hand back a DATE column as either object-dtype
    # datetime.date values or datetime64, depending on the duckdb/pandas
    # pair. Normalise to plain datetime.date so the index is stable and
    # comparable against date literals regardless of that version pairing.
    series.index = pd.Index(
        [v.date() if isinstance(v, pd.Timestamp) else v for v in series.index],
        name="period_start",
    )
    return series


def as_of(con: duckdb.DuckDBPyConnection, indicator: str, when: datetime) -> pd.Series:
    """Values visible at ``when``, indexed by period_start. Never forward-filled."""
    return _to_series(con.execute(_AS_OF_SQL, [indicator, when]).df())


def latest(con: duckdb.DuckDBPyConnection, indicator: str) -> pd.Series:
    """Latest-vintage values, revisions included."""
    return _to_series(con.execute(_LATEST_SQL, [indicator]).df())


def revisions(con: duckdb.DuckDBPyConnection, indicator: str, period_start: date) -> pd.DataFrame:
    """Every vintage recorded for one period, oldest release first."""
    return con.execute(_REVISIONS_SQL, [indicator, period_start]).df()
