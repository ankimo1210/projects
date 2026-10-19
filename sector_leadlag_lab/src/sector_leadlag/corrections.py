"""Rules that correct the yfinance errors for the rerun after the verdict (PREREG §5).

Design 2026-10-20 §3. Every rule is a pure function of the panels on their trading days, and
``correct`` applies them in the design's order (C2, C1, C4, C5, C6, C3, C7), listing each change.
``missing_known`` checks that every known error of the design's §2 was changed by its rule.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import baskets as bk
from .baskets import Panel

JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close


@dataclass(frozen=True)
class Change:
    rule: str
    column: object  # the panel column: an ETF's sector code, a stock code or a US ticker
    day: pd.Timestamp
    field: str
    before: float | str | None
    after: float | str | None


def _cells(mask: pd.DataFrame) -> list[tuple[pd.Timestamp, object]]:
    """(day, column) of every True cell, column by column and day by day."""
    columns, rows = np.nonzero(mask.to_numpy(dtype=bool).T)
    return [(mask.index[r], mask.columns[c]) for c, r in zip(columns, rows, strict=True)]


def zero_opens(panel: Panel) -> tuple[Panel, list[Change]]:
    """C2: an open of 0 on a day with trades becomes missing (its O2C and C2O with it)."""
    bad = (panel.open == 0) & bk.traded(panel)
    changes = [Change("C2", column, day, "open", 0.0, None) for day, column in _cells(bad)]
    return replace(panel, open=panel.open.mask(bad)), changes


def close_ratio(close: pd.DataFrame) -> pd.DataFrame:
    """Each close over the series' previous close (across days on which it has no row)."""
    return close / close.ffill().shift(1)


def scale_breaks(close: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """C1: a close over twice, or under half, the previous one on a day without a split."""
    ratio = close_ratio(close)
    jump = (ratio > JUMP) | (ratio < 1.0 / JUMP)
    return jump & ~(splits.fillna(0.0) > 0)


def _jump_changes(close: pd.DataFrame, breaks: pd.DataFrame) -> list[Change]:
    ratio = close_ratio(close)
    return [
        Change("C1", column, day, "returns", float(ratio.at[day, column]), None)
        for day, column in _cells(breaks)
    ]


def with_breaks(panel: Panel) -> tuple[Panel, list[Change]]:
    """C1 on a panel: the returns from the previous close across a jump become missing."""
    breaks = scale_breaks(panel.close, panel.splits)
    return replace(panel, breaks=breaks), _jump_changes(panel.close, breaks)


def missing_rows(close: pd.DataFrame) -> pd.DataFrame:
    """C3: a day inside a series' listed span (its first row to its last) without a row."""
    listed = close.ffill().notna() & close.bfill().notna()
    return listed & close.isna()


def _onto(frame: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Sums of the rows of ``frame`` on the first of ``days`` on or after each row's date."""
    position = days.searchsorted(frame.index, side="left")
    inside = position < len(days)
    sums = frame[inside].groupby(days[position[inside]]).sum()
    return sums.reindex(days, fill_value=0.0)


def signal_returns(etf: Panel, days: pd.DatetimeIndex) -> pd.DataFrame:
    """C7: the signal's Japanese side on ``days``: (close + dividend) over the previous close.

    Days without trades count, as with the adjusted close of the record; a jump (C1) makes the
    return missing. A dividend or a jump on a day left out of ``days`` (C3) goes to the next one.
    """
    close = etf.close.reindex(days)
    paid = _onto(etf.dividends.fillna(0.0), days)
    broken = _onto(etf.breaks.astype(float), days) > 0
    return ((close + paid) / close.shift(1) - 1.0).mask(broken)
