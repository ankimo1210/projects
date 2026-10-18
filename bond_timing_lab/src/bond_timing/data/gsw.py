"""GSW zero curve from the macrokit snapshot, cut at the longest published maturity (design §4.1).

GSW publishes SVENYnn only up to the longest maturity its bond sample supports on each day
(1-7 years from 1961-06, 10 years from 1971-08-16, 15 from 1971-11-15, 20 from 1981-07-02,
30 from 1985-11-25; verified 2026-10-19). The Svensson parameters extrapolate beyond that;
those values are never used.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from macrokit.sources.us_term import GswDay, gsw_zero, month_end_days, parse_gsw

from .store import MACROKIT_RAW, read_latest

_MISSING = ("", "NA", None)


def published_max_years(content: bytes) -> dict[date, int]:
    """Longest maturity, in whole years, with a published SVENYnn value on each day."""
    lines = content.decode("utf-8", errors="replace").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    out: dict[date, int] = {}
    for row in csv.DictReader(lines[start:]):
        published = [n for n in range(1, 31) if row.get(f"SVENY{n:02d}") not in _MISSING]
        out[date.fromisoformat(row["Date"])] = max(published, default=0)
    return out


@dataclass(frozen=True)
class GswCurve:
    days: tuple[GswDay, ...]
    max_years: dict[date, int]

    def zeros(self, days: Sequence[GswDay], months: Sequence[float]) -> np.ndarray:
        """Decimal continuously compounded zero yields; NaN beyond the published range."""
        grid = np.asarray(months, dtype=float)
        out = np.full((len(days), len(grid)), np.nan)
        for i, day in enumerate(days):
            inside = grid <= 12 * self.max_years.get(day.obs_date, 0) + 1e-9
            if inside.any():
                out[i, inside] = gsw_zero(day, grid[inside]) / 100.0
        return out

    def month_ends(self) -> list[GswDay]:
        """Last observation of each month, without a final month that is still in progress."""
        ends = month_end_days(self.days)
        if ends:
            last = pd.Timestamp(ends[-1].obs_date)
            if last != pd.offsets.BMonthEnd().rollforward(last):
                ends = ends[:-1]
        return ends

    def days_by_month(self) -> dict[pd.Period, list[GswDay]]:
        grouped: dict[pd.Period, list[GswDay]] = defaultdict(list)
        for day in sorted(self.days, key=lambda d: d.obs_date):
            grouped[pd.Period(day.obs_date, freq="M")].append(day)
        return dict(grouped)


def parse_curve(content: bytes) -> GswCurve:
    return GswCurve(tuple(parse_gsw(content)), published_max_years(content))


def load_curve(root: Path = MACROKIT_RAW) -> GswCurve:
    return parse_curve(read_latest(root, "us_term", "gsw"))


def month_end_zeros(curve: GswCurve, months: Sequence[int]) -> pd.DataFrame:
    ends = curve.month_ends()
    index = pd.PeriodIndex([pd.Period(d.obs_date, freq="M") for d in ends], freq="M")
    frame = pd.DataFrame(curve.zeros(ends, months), index=index, columns=list(months))
    return frame.reindex(pd.period_range(index[0], index[-1], freq="M"))
