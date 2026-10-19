"""Point-in-time checks R1 and R2 (design §5.1). G2 feeds them future values on purpose."""

from __future__ import annotations

import pandas as pd


class LeakError(AssertionError):
    """An input was observed later than the decision it feeds."""


def check_window(
    row_dates: pd.DatetimeIndex,
    row_us_dates: pd.DatetimeIndex,
    us_day: pd.Timestamp,
    day: pd.Timestamp,
) -> None:
    """R1: the signal of Japanese day d reads rows dated before d, and US returns up to s(d) < d."""
    if not us_day < day:
        raise LeakError(f"the US day {us_day.date()} of {day.date()} is not before it")
    if len(row_dates) and row_dates.max() >= day:
        raise LeakError(f"a window row of {day.date()} is dated {row_dates.max().date()}")
    if len(row_us_dates) and row_us_dates.max() > us_day:
        raise LeakError(
            f"a window row of {day.date()} holds US returns of {row_us_dates.max().date()},"
            f" after s(d) = {us_day.date()}"
        )


def check_lookback(last_read: pd.Series) -> None:
    """R2: what decides the baskets and share counts of day d was read on a day before d.

    ``last_read`` maps each day d to the last date its inputs came from.
    """
    known = last_read.dropna()
    late = known[pd.DatetimeIndex(known.to_numpy()) >= pd.DatetimeIndex(known.index)]
    if len(late):
        raise LeakError(f"the baskets of {late.index[0].date()} read {late.iloc[0].date()}")
