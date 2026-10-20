"""Rules that correct the yfinance errors for the rerun after the verdict (PREREG §5).

Design 2026-10-20 §3. Every rule is a pure function of the panels on their trading days, and
``correct`` applies them in the design's order (C2, C1, C4, C5, C6, C3, C7), listing each change.
``missing_known`` checks that every known error of the design's §2 was changed by its rule.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace

import numpy as np
import pandas as pd

from . import baskets as bk
from .baskets import Panel
from .data import jpx

JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close
LOOKBACK = 2  # C6: the recorded day and the ETF's two rows before it
RULES = ("C2", "C1", "C4", "C5", "C6", "C3")  # C7 changes how the signal is built, not a value


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


def market_move(stocks: Panel) -> pd.Series:
    """The stocks' median overnight return, dividends included (the yardstick of C4 and C6)."""
    return bk.close_to_open(stocks).median(axis=1)


def split_day_dividends(panel: Panel, market: pd.Series) -> tuple[Panel, list[Change]]:
    """C4: a dividend on the day of a split of ratio k, left in pre-split units.

    D becomes D/k when D/k is closer than D to the series' previous dividend (in logs) and D/(kP)
    is closer than D/P to the day's drop: the stocks' median overnight return less the series'
    opening gap (P is the previous close). A series without an earlier dividend keeps D.
    """
    dividends = panel.dividends.copy()
    previous = panel.close.shift(1)
    drop = -bk.opening_gap(panel).sub(market, axis=0)
    events = (panel.splits.fillna(0.0) > 0) & (dividends.fillna(0.0) > 0)
    changes = []
    for day, column in _cells(events):
        k, d, p = panel.splits.at[day, column], dividends.at[day, column], previous.at[day, column]
        paid = dividends[column]
        paid = paid[(paid.index < day) & (paid > 0)]
        if paid.empty:
            continue
        last, fall = paid.iloc[-1], drop.at[day, column]
        by_history = abs(math.log(d / k / last)) < abs(math.log(d / last))
        by_drop = abs(d / (k * p) - fall) < abs(d / p - fall)  # False when either is missing
        if by_history and by_drop:
            dividends.at[day, column] = d / k
            changes.append(Change("C4", column, day, "dividends", float(d), float(d / k)))
    return replace(panel, dividends=dividends), changes


def oversized_dividends(panel: Panel) -> tuple[Panel, list[Change]]:
    """C5: a dividend above the previous close.

    When the series' latest jump (C1) before it was down, D is divided by the jump's size (the
    previous close over the close: 506 for 1629.T in 2015). D becomes 0 when there is no such
    jump, or when the result is still above the previous close.
    """
    ratio = close_ratio(panel.close).where(panel.breaks)
    dividends = panel.dividends.copy()
    previous = panel.close.shift(1)
    changes = []
    for day, column in _cells(dividends.fillna(0.0) > previous):
        d, p = dividends.at[day, column], previous.at[day, column]
        jumps = ratio[column]
        jumps = jumps[(jumps.index < day) & jumps.notna()]
        after = 0.0
        if len(jumps) and jumps.iloc[-1] < 1.0 / JUMP:
            after = d * jumps.iloc[-1]
            after = 0.0 if after > p else after
        dividends.at[day, column] = after
        changes.append(Change("C5", column, day, "dividends", float(d), float(after)))
    return replace(panel, dividends=dividends), changes


def late_etf_dividends(
    etf: Panel, market: pd.Series, lookback: int = LOOKBACK
) -> tuple[Panel, list[Change]]:
    """C6: an ETF dividend moves to the day on which the ETFs opened lowest against the stocks.

    The candidates are the recorded day and the ETF's ``lookback`` rows before it; each day scores
    the mean, over the ETFs that traded, of the opening gap less the stocks' median overnight
    return. The earliest of equal scores wins; a recorded day without any score keeps it.
    """
    score = bk.opening_gap(etf).sub(market, axis=0).mean(axis=1)
    dividends = etf.dividends.copy()
    changes = []
    for day, column in _cells(etf.dividends.fillna(0.0) > 0):
        rows = etf.close.index[etf.close[column].notna().to_numpy()]
        here = rows.get_loc(day)
        scores = score.reindex(rows[max(0, here - lookback) : here + 1])
        if scores.isna().all():
            continue
        target = scores.idxmin()
        if target != day:
            amount = dividends.at[day, column]
            dividends.at[target, column] = np.nan_to_num(dividends.at[target, column]) + amount
            dividends.at[day, column] = 0.0
            changes.append(
                Change("C6", column, day, "dividend_date", str(day.date()), str(target.date()))
            )
    return replace(etf, dividends=dividends), changes


@dataclass(frozen=True)
class Corrected:
    etf: Panel
    stocks: Panel
    us_breaks: pd.DataFrame  # US days after a jump in the close (C1)
    signal_days: pd.DatetimeIndex  # the Japanese days the signal's rows may use (C3)
    signal: pd.DataFrame  # the signal's Japanese side on those days (C7)
    changes: list[dict]


def _record(change: Change, kind: str, name: Callable[[object], str]) -> dict:
    return {
        "rule": change.rule,
        "kind": kind,
        "series": name(change.column),
        "date": str(change.day.date()),
        "field": change.field,
        "before": change.before,
        "after": change.after,
    }


def correct(
    etf: Panel, stocks: Panel, us_close: pd.DataFrame, us_splits: pd.DataFrame
) -> Corrected:
    """Every rule in the design's order. ``us_close`` and ``us_splits`` are on the US days."""
    found: list[tuple[str, Change]] = []

    def kept(kind: str, result: tuple[Panel, list[Change]]) -> Panel:
        panel, changes = result
        found.extend((kind, change) for change in changes)
        return panel

    etf = kept("etf", zero_opens(etf))
    stocks = kept("stock", zero_opens(stocks))
    etf = kept("etf", with_breaks(etf))
    stocks = kept("stock", with_breaks(stocks))
    us_breaks = scale_breaks(us_close, us_splits)
    found.extend(("us", change) for change in _jump_changes(us_close, us_breaks))
    market = market_move(stocks)
    etf = kept("etf", split_day_dividends(etf, market))
    stocks = kept("stock", split_day_dividends(stocks, market))
    etf = kept("etf", oversized_dividends(etf))
    stocks = kept("stock", oversized_dividends(stocks))
    etf = kept("etf", late_etf_dividends(etf, market))
    gaps = missing_rows(etf.close)
    found.extend(("etf", Change("C3", c, day, "row", None, None)) for day, c in _cells(gaps))
    days = etf.close.index[~gaps.any(axis=1).to_numpy()]
    names = {
        "etf": lambda k: jpx.ETF_TICKERS[int(k) - 1],
        "stock": jpx.stock_ticker,
        "us": str,
    }
    order = {rule: i for i, rule in enumerate(RULES)}
    records = [
        _record(change, kind, names[kind])
        for kind, change in sorted(found, key=lambda item: order[item[1].rule])
    ]
    return Corrected(etf, stocks, us_breaks, days, signal_returns(etf, days), records)


@dataclass(frozen=True)
class Known:
    label: str  # the row of design §2
    rule: str
    kind: str
    series: str | None  # None: any series of the kind
    date: str | None  # None: any date
    count: int  # changes needed


KNOWN = (
    Known("1629.T: the unrecorded split of 2015-01-05", "C1", "etf", "1629.T", "2015-01-05", 1),
    Known("1629.T: prices at 1/500 from 2026-03-30", "C1", "etf", "1629.T", "2026-03-30", 1),
    Known("1629.T: prices back on 2026-04-01", "C1", "etf", "1629.T", "2026-04-01", 1),
    Known(
        "1629.T: the dividend of 2015-07-15 per pre-split unit",
        "C5",
        "etf",
        "1629.T",
        "2015-07-15",
        1,
    ),
    Known("16 ETFs without a row on 2025-10-24", "C3", "etf", None, "2025-10-24", 16),
    Known("ETF dividends dated late (17 ETFs, 2013-2026)", "C6", "etf", None, None, 238),
    Known("ETF opens of 0 in 2009", "C2", "etf", None, None, 53),
    Known("8303.T: dividends of 200-240 million yen", "C5", "stock", "8303.T", None, 12),
    Known("9861.T: the split-day dividend of 2013", "C4", "stock", "9861.T", "2013-08-28", 1),
    Known("5401.T: the split-day dividend of 2025", "C4", "stock", "5401.T", "2025-09-29", 1),
    Known("8766.T: the split-day dividend of 2026", "C4", "stock", "8766.T", "2026-09-29", 1),
    Known(
        "8227.T: the 1:3 split price before its record", "C1", "stock", "8227.T", "2026-02-18", 1
    ),
)


def missing_known(changes: list[dict], known: tuple[Known, ...] = KNOWN) -> list[dict]:
    """The known errors that their rule did not change (design §3: stop and report them)."""
    out = []
    for item in known:
        found = sum(
            change["rule"] == item.rule
            and change["kind"] == item.kind
            and item.series in (None, change["series"])
            and item.date in (None, change["date"])
            for change in changes
        )
        if found < item.count:
            out.append({**asdict(item), "found": found})
    return out


def counts(changes: list[dict]) -> dict[str, dict[str, int]]:
    """How many changes each rule made, by kind of series."""
    out: dict[str, dict[str, int]] = {rule: {} for rule in RULES}
    for change in changes:
        by_kind = out[change["rule"]]
        by_kind[change["kind"]] = by_kind.get(change["kind"], 0) + 1
    return out
