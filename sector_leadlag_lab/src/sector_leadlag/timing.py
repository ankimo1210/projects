"""Trading days, the US day each Japanese day uses, and the paired rows of the windows (design §5).

Two readings of how the papers pair US and Japanese returns inside a window (design §5.2):

- ``same_date``: only days on which both markets traded, each paired with itself. Both papers
  write the window with one date index for every asset ("the close of business day d'"), and
  the strategy paper says it uses "only business days observable in both markets".
- ``lagged``: every Japanese day d' paired with the US day s(d') before it, the information
  timing of the trade itself.

Each market's close-to-close return runs from its own previous trading day.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VARIANTS = ("same_date", "lagged")
MIN_TRADED_SHARE = 0.5


def jp_trading_days(volume: pd.DataFrame) -> pd.DatetimeIndex:
    """Dates on which at least half of the stocks listed at the time traded (design §4).

    A stock counts as listed from its first row to its last, so a stray row on a holiday does
    not make the holiday a trading day.
    """
    dates = volume.index.to_numpy()
    first = volume.apply(pd.Series.first_valid_index).to_numpy(dtype="datetime64[ns]")
    last = volume.apply(pd.Series.last_valid_index).to_numpy(dtype="datetime64[ns]")
    listed = ((dates[:, None] >= first) & (dates[:, None] <= last)).sum(axis=1)
    traded = (volume > 0).sum(axis=1).to_numpy()
    share = np.divide(traded, listed, out=np.zeros(len(dates)), where=listed > 0)
    return pd.DatetimeIndex(volume.index[share >= MIN_TRADED_SHARE], name="date")


def us_trading_days(volume: pd.Series) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(volume.index[volume > 0], name="date")


def last_us_before(jp_days: pd.DatetimeIndex, us_days: pd.DatetimeIndex) -> pd.Series:
    """s(d): the last US trading day strictly before each Japanese day d (design §5.1)."""
    position = us_days.searchsorted(jp_days, side="left") - 1
    keep = position >= 0
    return pd.Series(us_days[position[keep]], index=jp_days[keep], name="us_day")


def close_to_close(prices: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Returns from each day's previous row on ``days`` (one market's own calendar)."""
    p = prices.reindex(days)
    return p / p.shift(1) - 1.0


@dataclass(frozen=True)
class Rows:
    """The paired US and Japanese returns that every correlation window is cut from."""

    dates: pd.DatetimeIndex  # the row's date: a common day, or the Japanese day d'
    us_dates: pd.DatetimeIndex  # the US day of the row's US returns
    us: np.ndarray  # (rows, 11)
    jp: np.ndarray  # (rows, 17)
    us_names: tuple[str, ...]
    jp_names: tuple[int, ...]


def pair_rows(variant: str, us_ret: pd.DataFrame, jp_ret: pd.DataFrame, s_map: pd.Series) -> Rows:
    names = (tuple(us_ret.columns), tuple(jp_ret.columns))
    if variant == "same_date":
        common = jp_ret.index.intersection(us_ret.index)
        us = us_ret.reindex(common).to_numpy()
        return Rows(common, common, us, jp_ret.reindex(common).to_numpy(), *names)
    if variant == "lagged":
        jp_days = s_map.index.intersection(jp_ret.index)
        us_days = pd.DatetimeIndex(s_map.reindex(jp_days).to_numpy())
        us = us_ret.reindex(us_days).to_numpy()
        return Rows(jp_days, us_days, us, jp_ret.reindex(jp_days).to_numpy(), *names)
    raise ValueError(f"unknown pairing {variant!r}; expected one of {VARIANTS}")
