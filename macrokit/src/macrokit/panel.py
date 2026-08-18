"""The event panel: one row per (release, expectation method), built as a query.

Deliberately not a table. The surprise normalisation and the change window are
the two things most likely to need revisiting, and materialising them would
freeze both.

Reading a single row is not meaningful. The only free JGB data is the daily
close, which cannot separate an 08:50 release from everything else that day --
on 2026-08-17 the curve sold off on BoJ and fiscal repricing while the GDP print
itself had undershot. Read the panel as a statistic over ~142 events.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

DEFAULT_TENORS = (2.0, 5.0, 10.0, 20.0, 30.0)


def event_panel(
    con: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    tenors: tuple[float, ...] = DEFAULT_TENORS,
    z_min_observations: int = 20,
) -> pd.DataFrame:
    # 2nd_prelim_revised is deliberately excluded, not merely un-widened: the
    # CLI's `gdp vintages` never records a revised release's release_date in
    # `observations` (it has no derivable menu URL -- see
    # sources/esri_gdp.menu_url), so this JOIN has nothing to match a
    # 2nd_prelim_revised row against. There used to be an `include_revised`
    # flag here; it was removed because "include" implies a real choice, and
    # on live data it returned the identical rows as leaving it off.
    kinds = ("1st_prelim", "2nd_prelim")
    frame = con.execute(
        """
        SELECT r.release_date, r.period_start, r.period_end, r.release_kind,
               o.value AS actual, e.method, e.expected, e.as_of,
               o.value - e.expected AS surprise
        FROM releases r
        JOIN observations o
          ON o.indicator = r.indicator
         AND o.period_start = r.period_start
         AND o.release_date = r.release_date
        JOIN expectations e
          ON e.indicator = r.indicator
         AND e.period_start = r.period_start
         AND e.release_kind = r.release_kind
        WHERE r.indicator = ?
          AND list_contains(?::VARCHAR[], r.release_kind)
        ORDER BY r.release_date, e.method
        """,
        [indicator, list(kinds)],
    ).df()
    if frame.empty:
        return frame

    frame = _attach_rate_changes(con, frame, tenors)
    frame = frame[_any_tenor_present(frame, tenors)]
    frame["surprise_z"] = _expanding_z(frame, z_min_observations)
    return frame.reset_index(drop=True)


def _label(tenor: float) -> str:
    return f"{int(tenor)}y"


def _any_tenor_present(frame: pd.DataFrame, tenors: tuple[float, ...]) -> pd.Series:
    columns = [f"d1_bp_{_label(t)}" for t in tenors]
    return frame[columns].notna().any(axis=1)


def _attach_rate_changes(
    con: duckdb.DuckDBPyConnection, frame: pd.DataFrame, tenors: tuple[float, ...]
) -> pd.DataFrame:
    curve = con.execute(
        "SELECT obs_date, tenor_y, yield_pct FROM market_rates WHERE curve = 'jgb' "
        "ORDER BY obs_date"
    ).df()
    if curve.empty:
        for tenor in tenors:
            frame[f"d1_bp_{_label(tenor)}"] = pd.NA
            frame[f"d2_bp_{_label(tenor)}"] = pd.NA
        return frame

    wide = curve.pivot(index="obs_date", columns="tenor_y", values="yield_pct").sort_index()
    # DuckDB's .df() hands `obs_date` (a DATE column) back as datetime64/Timestamp,
    # not datetime.date -- a dict keyed on that index would never match a lookup
    # keyed on release_date.date() below (equal by value, but Timestamp and date
    # hash differently). Normalise to plain dates so the lookup actually hits.
    wide.index = pd.Index(
        [day.date() if hasattr(day, "date") else day for day in wide.index], name="obs_date"
    )
    sessions = list(wide.index)
    position = {day: i for i, day in enumerate(sessions)}

    for tenor in tenors:
        d1, d2 = [], []
        for release_date in frame["release_date"]:
            day = release_date.date()
            index = position.get(day)
            if index is None or index == 0 or tenor not in wide.columns:
                d1.append(pd.NA)
                d2.append(pd.NA)
                continue
            base = wide[tenor].iloc[index - 1]
            d1.append(_bp(wide[tenor].iloc[index], base))
            forward = index + 1
            d2.append(_bp(wide[tenor].iloc[forward], base) if forward < len(sessions) else pd.NA)
        frame[f"d1_bp_{_label(tenor)}"] = d1
        frame[f"d2_bp_{_label(tenor)}"] = d2
    return frame


def _bp(value, base):
    if pd.isna(value) or pd.isna(base):
        return pd.NA
    return (float(value) - float(base)) * 100.0


def _expanding_z(frame: pd.DataFrame, minimum: int) -> pd.Series:
    """Divide by the standard deviation of *prior* surprises for the same method.

    Expanding, not full-sample: a full-sample sigma would let every early row see
    the dispersion of surprises that had not happened yet.
    """
    # np.nan, not pd.NA -- pandas 3.x's float64 Series constructor cannot fill
    # an ndarray with pd.NA (TypeError), only a plain NaN.
    result = pd.Series(np.nan, index=frame.index, dtype="float64")
    for _method, group in frame.groupby("method", sort=False):
        surprises = group["surprise"].astype(float)
        sigma = surprises.shift(1).expanding(min_periods=minimum).std()
        result.loc[group.index] = surprises / sigma
    return result
