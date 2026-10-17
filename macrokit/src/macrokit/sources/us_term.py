"""US validation data for the JGB term-premium re-test (design 2026-10-17 §3.5).

Verified 2026-10-17:
- GSW zero curve (FRB): a text preamble, then a ``Date,BETA0,...`` header. ``NA``
  marks missing values; a Nelson-Siegel day has ``BETA3 = 0`` and ``TAU2 = -999.99``.
- NY Fed ACM term premia: legacy BIFF ``.xls`` (xlrd). Sheet ``ACM Monthly``,
  ``DATE`` as text such as ``30-Jun-1961``, columns ACMY01..10, ACMTP01..10, ACMRNY01..10.
- Wu-Xia shadow rate (Atlanta Fed): ``.xlsx`` (openpyxl). Sheet ``Data``; column A
  is the first of the month, column C the shadow rate. Updates stopped after 2022-02.

These files are stored as raw snapshots only; nothing here writes to DuckDB.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

import httpx
import numpy as np
import openpyxl
import xlrd

from ..termstructure.curve import svensson_zero

SOURCE = "us_term"
INDICATORS = {
    "gsw": "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv",
    "acm": "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls",
    "wuxia": (
        "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/datafiles/cqer/"
        "research/wu-xia-shadow-federal-funds-rate/WuXiaShadowRate.xlsx"
    ),
}
FILENAMES = {"gsw": "feds200628.csv", "acm": "ACMTermPremium.xls", "wuxia": "WuXiaShadowRate.xlsx"}
_MISSING = ("", "NA", None)
_PARAMS = ("BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2")


class UsTermError(RuntimeError):
    """A US validation file could not be fetched or parsed."""


@dataclass(frozen=True)
class GswDay:
    obs_date: date
    params: tuple[float, float, float, float, float, float]  # beta0..beta3, tau1, tau2


def parse_gsw(content: bytes) -> list[GswDay]:
    lines = content.decode("utf-8", errors="replace").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    except StopIteration as exc:
        raise UsTermError("GSW payload has no 'Date,' header row") from exc
    days: list[GswDay] = []
    for row in csv.DictReader(lines[start:]):
        values = [row.get(name) for name in _PARAMS]
        if any(v in _MISSING for v in values[:5]):
            continue
        b0, b1, b2, b3, tau1 = (float(v) for v in values[:5])
        tau2 = -999.99 if values[5] in _MISSING else float(values[5])
        if b3 == 0.0 or tau2 <= 0:
            b3, tau2 = 0.0, 1.0  # Nelson-Siegel day: no second hump
        days.append(GswDay(date.fromisoformat(row["Date"]), (b0, b1, b2, b3, tau1, tau2)))
    return days


def month_end_days(days: Sequence[GswDay]) -> list[GswDay]:
    last: dict[tuple[int, int], GswDay] = {}
    for day in sorted(days, key=lambda d: d.obs_date):
        last[(day.obs_date.year, day.obs_date.month)] = day
    return [last[key] for key in sorted(last)]


def gsw_zero(day: GswDay, months: np.ndarray) -> np.ndarray:
    return svensson_zero(np.array(day.params), np.asarray(months, dtype=float) / 12.0)


def parse_acm_rows(rows: Sequence[Sequence]) -> dict[tuple[int, int], dict[str, float]]:
    header = [str(cell) for cell in rows[0]]
    if not header or header[0] != "DATE":
        raise UsTermError(f"ACM sheet header must start with DATE, got {header[:2]}")
    out: dict[tuple[int, int], dict[str, float]] = {}
    for row in rows[1:]:
        if not row or row[0] in _MISSING:
            continue
        day = datetime.strptime(str(row[0]), "%d-%b-%Y").date()
        out[(day.year, day.month)] = {
            name: float(value)
            for name, value in zip(header[1:], row[1:], strict=True)
            if value not in _MISSING
        }
    return out


def parse_acm(content: bytes) -> dict[tuple[int, int], dict[str, float]]:
    sheet = xlrd.open_workbook(file_contents=content).sheet_by_name("ACM Monthly")
    return parse_acm_rows([sheet.row_values(i) for i in range(sheet.nrows)])


def parse_wuxia(content: bytes) -> dict[tuple[int, int], float]:
    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    out: dict[tuple[int, int], float] = {}
    for row in book["Data"].iter_rows(min_row=2, values_only=True):
        if not row or not isinstance(row[0], datetime) or row[2] is None:
            continue
        out[(row[0].year, row[0].month)] = float(row[2])
    return out


def fetch(url: str, *, timeout: float = 180.0) -> tuple[bytes, int]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; macrokit research)"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise UsTermError(f"GET {url} returned {response.status_code}")
    return response.content, response.status_code
