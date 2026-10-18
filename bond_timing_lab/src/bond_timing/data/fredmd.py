"""FRED-MD vintages: archive members, parsing, tcode transforms and macro sources (design §4.4).

Verified 2026-10-19: vintage v holds data through v-1; the first row is the header
(``sasdate``), the second the ``Transform:`` codes; dates are ``M/D/YYYY``; the newest row is
ragged (several series blank). Archive members are ``.../1999-08.csv``, ``2017-02.csv``,
``FRED-MD_2024m03.csv`` or ``FRED-MD-2025m05.csv``. Monthly files from 2026 are
``monthly/YYYY-MM-md.csv`` (2026-08 was published as ``monthly/2026-rev-08-md.csv``).
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

import numpy as np
import pandas as pd

from ..pit import check_vintage

BASE = "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md"
HISTORICAL = {
    "hist_1999_2014": f"{BASE}/historical_fred-md.zip",
    "hist_2015_2025": f"{BASE}/historical-vintages-of-fred-md-2015-01-to-2025-12.zip",
}
FIRST_MONTHLY = pd.Period("2026-01", "M")
MAX_LAG = 6
_MEMBER = re.compile(r"(\d{4})(?:-|m)(\d{2})\.csv$")
_NA = {"", "NA", "NaN", "nan", "."}


def monthly_urls(month: pd.Period) -> list[str]:
    return [
        f"{BASE}/monthly/{month.year:04d}-{month.month:02d}-md.csv",
        f"{BASE}/monthly/{month.year:04d}-rev-{month.month:02d}-md.csv",
    ]


def member_vintage(name: str) -> pd.Period | None:
    match = _MEMBER.search(name.rsplit("/", 1)[-1])
    return pd.Period(f"{match.group(1)}-{match.group(2)}", "M") if match else None


def zip_vintages(content: bytes) -> dict[pd.Period, bytes]:
    out: dict[pd.Period, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            vintage = member_vintage(name)
            if vintage is None:
                continue
            if vintage in out:
                raise ValueError(f"vintage {vintage} appears twice in the archive")
            out[vintage] = archive.read(name)
    return out


def transform(x: pd.Series, tcode: int) -> pd.Series:
    """McCracken-Ng codes: 1 level, 2 diff, 3 diff2, 4 log, 5 dlog, 6 d2log, 7 d(x/x[-1] - 1)."""
    if tcode == 1:
        return x
    if tcode == 2:
        return x.diff()
    if tcode == 3:
        return x.diff().diff()
    if tcode in (4, 5, 6):
        logged = np.log(x.where(x > 0))
        if tcode == 4:
            return logged
        return logged.diff() if tcode == 5 else logged.diff().diff()
    if tcode == 7:
        return (x / x.shift(1) - 1.0).diff()
    raise ValueError(f"unknown FRED-MD tcode {tcode}")


@dataclass(frozen=True)
class Vintage:
    vintage: pd.Period
    levels: pd.DataFrame  # data month x series, contiguous monthly index
    tcodes: dict[str, int]

    @cached_property
    def transformed(self) -> pd.DataFrame:
        return pd.DataFrame(
            {name: transform(self.levels[name], code) for name, code in self.tcodes.items()},
            index=self.levels.index,
        )


def parse_vintage(vintage: pd.Period, content: bytes) -> Vintage:
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig", errors="replace"))))
    header = [cell.strip() for cell in rows[0]]
    if header[0].lower() != "sasdate":
        raise ValueError(f"vintage {vintage}: the first header cell is {header[0]!r}")
    if not rows[1] or not rows[1][0].strip().lower().startswith("transform"):
        raise ValueError(f"vintage {vintage}: the second row is not the Transform: row")
    names = header[1:]
    codes: dict[str, int] = {}
    for name, code in zip(names, rows[1][1:], strict=False):
        if name and name not in codes and code.strip() not in _NA:
            codes[name] = int(float(code))
    months, values = [], []
    for row in rows[2:]:
        if not row or not row[0].strip():
            continue
        months.append(pd.Period(datetime.strptime(row[0].strip(), "%m/%d/%Y"), freq="M"))
        cells = [cell.strip() for cell in row[1 : 1 + len(names)]]
        cells += [""] * (len(names) - len(cells))
        values.append([np.nan if cell in _NA else float(cell) for cell in cells])
    frame = pd.DataFrame(values, index=pd.PeriodIndex(months, freq="M"), columns=names)
    frame = frame.loc[:, ~frame.columns.duplicated()]
    frame = frame.loc[:, [name for name in frame.columns if name in codes]]
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.reindex(pd.period_range(frame.index[0], frame.index[-1], freq="M"))
    return Vintage(vintage, frame, {name: codes[name] for name in frame.columns})


@dataclass(frozen=True)
class MacroView:
    """The series one refit uses and the publication lag (months) each keeps all year."""

    names: tuple[str, ...]
    lags: tuple[int, ...]


def lagged_values(frame: pd.DataFrame, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
    """x_j(s - lag_j) for every row s; NaN where the series or the month is absent."""
    out = np.full((len(rows), len(view.names)), np.nan)
    for j, (name, lag) in enumerate(zip(view.names, view.lags, strict=True)):
        if name in frame.columns:
            out[:, j] = frame[name].reindex(rows - lag).to_numpy(dtype=float)
    return out


def latest_values(frame: pd.DataFrame, view: MacroView, t: pd.Period) -> np.ndarray:
    """The latest value at or before t - lag_j of each series; NaN if the series is absent."""
    out = np.full(len(view.names), np.nan)
    for j, (name, lag) in enumerate(zip(view.names, view.lags, strict=True)):
        if name in frame.columns:
            column = frame[name].loc[: t - lag].dropna()
            if len(column):
                out[j] = column.iloc[-1]
    return out


class RealTimeMacro:
    """Decision t sees vintage t-1 (R1). A series' lag is t minus its last valid month there."""

    def __init__(self, vintage: Callable[[pd.Period], Vintage]):
        self._vintage = vintage

    def _frame_at(self, vintage: pd.Period, t: pd.Period) -> pd.DataFrame:
        check_vintage(vintage, t)
        return self._vintage(vintage).transformed

    def view(self, t: pd.Period) -> MacroView:
        frame = self._frame_at(t - 1, t)
        names, lags = [], []
        for name in frame.columns:
            last = frame[name].last_valid_index()
            if last is not None and (t - last).n <= MAX_LAG:
                names.append(name)
                lags.append((t - last).n)
        return MacroView(tuple(names), tuple(lags))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame_at(t - 1, t), view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame_at(t - 1, t), view, t)


class FinalMacro:
    """One vintage for every decision, publication lag ignored (design §7, V0-V2)."""

    def __init__(self, vintage: Vintage):
        self._frame = vintage.transformed

    def view(self, t: pd.Period) -> MacroView:
        return MacroView(tuple(self._frame.columns), (0,) * len(self._frame.columns))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame, view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame, view, t)


class PanelMacro:
    """A single panel seen with one lag for every series (the simulated macro of G3)."""

    def __init__(self, frame: pd.DataFrame, lag: int = 2):
        self._frame, self._lag = frame, lag

    def view(self, t: pd.Period) -> MacroView:
        return MacroView(tuple(self._frame.columns), (self._lag,) * len(self._frame.columns))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame, view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame, view, t)
