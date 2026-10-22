"""The registered discount rate: local 10-year government yield plus the US implied ERP.

Yields come from the issuing governments' own tables (US Treasury par yield
curve, Japan's Ministry of Finance 国債金利情報); a day's row is taken as
published at 18:00 local time. The ERP is Damodaran's monthly
"ERP (T12 m with sustainable payout)", read with the standard library from the
workbook, whose dates use the 1904 system.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date, datetime, time, timedelta
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from portfolio_analyzer.ai_bubble.inputs import parse_utc

PUBLISHED_AT = time(18, 0)
NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
ERP_COLUMN = "ERP (T12 m with sustainable payout)"
_ERA = {"R": 2018, "H": 1988}
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _latest_published(
    series: list[tuple[date, float]], zone: ZoneInfo, as_of_utc: str
) -> tuple[str, float]:
    cutoff = parse_utc(as_of_utc, "as_of_utc")
    usable = [
        (day, value) for day, value in series if datetime.combine(day, PUBLISHED_AT, zone) <= cutoff
    ]
    if not usable:
        raise ValueError(f"no yield published by {as_of_utc}")
    day, value = max(usable)
    return day.isoformat(), value


def treasury_10y(text: str, as_of_utc: str) -> tuple[str, float]:
    """(date, yield as a fraction) from the Treasury daily par yield curve CSV."""
    series = []
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("10 Yr"):
            month, day, year = (int(x) for x in row["Date"].split("/"))
            series.append((date(year, month, day), round(float(row["10 Yr"]) / 100, 6)))
    return _latest_published(series, NEW_YORK, as_of_utc)


def mof_10y(text: str, as_of_utc: str) -> tuple[str, float]:
    """(date, yield as a fraction) from the MOF CSV (decoded text; dates like R8.10.20)."""
    rows = list(csv.reader(io.StringIO(text)))
    header = next(i for i, row in enumerate(rows) if row and row[0] == "基準日")
    column = rows[header].index("10年")
    series = []
    for row in rows[header + 1 :]:
        stamp = re.fullmatch(r"([RH])(\d+)\.(\d+)\.(\d+)", row[0].strip()) if row else None
        if stamp and row[column].strip():
            era, year, month, day = stamp.groups()
            series.append(
                (
                    date(_ERA[era] + int(year), int(month), int(day)),
                    round(float(row[column]) / 100, 6),
                )
            )
    return _latest_published(series, TOKYO, as_of_utc)


def _xlsx_rows(data: bytes) -> tuple[list[list[Any]], bool]:
    """First worksheet as rows of raw cell values, and whether dates use the 1904 system."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        workbook = z.read("xl/workbook.xml").decode()
        date1904 = bool(re.search(r'date1904="(1|true)"', workbook))
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for item in ElementTree.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_MAIN}si"):
                shared.append("".join(t.text or "" for t in item.iter(f"{_MAIN}t")))
        sheet = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter(f"{_MAIN}row"):
        cells: dict[int, Any] = {}
        for cell in row.iter(f"{_MAIN}c"):
            letters = re.match(r"[A-Z]+", cell.get("r", "")).group(0)
            index = 0
            for letter in letters:
                index = index * 26 + ord(letter) - 64
            value = cell.find(f"{_MAIN}v")
            if value is not None:
                cells[index - 1] = shared[int(value.text)] if cell.get("t") == "s" else value.text
        rows.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
    return rows, date1904


def _cell_date(value: str, date1904: bool) -> date:
    """A date cell: a serial number in the workbook's date system, or text such as 1-Sep-24."""
    try:
        serial = float(value)
    except ValueError:
        for pattern in ("%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), pattern).date()
            except ValueError:
                continue
        raise ValueError(f"unreadable date cell {value!r}") from None
    base = date(1904, 1, 1) if date1904 else date(1899, 12, 30)
    return base + timedelta(days=int(serial))


def _fraction(value: str) -> float:
    """A rate cell: a number, or text such as 4.05%."""
    text = str(value).strip()
    return float(text[:-1]) / 100 if text.endswith("%") else float(text)


def damodaran_erp(data: bytes, as_of_utc: str, column: str = ERP_COLUMN) -> tuple[str, float]:
    """(start of month, ERP) of the latest month starting on or before the as-of date."""
    rows, date1904 = _xlsx_rows(data)
    header = rows[0]
    month_col, erp_col = header.index("Start of month"), header.index(column)
    cutoff = parse_utc(as_of_utc, "as_of_utc").date()
    series = []
    for row in rows[1:]:
        if len(row) > erp_col and row[month_col] and row[erp_col]:
            day = _cell_date(row[month_col], date1904)
            if day <= cutoff:
                series.append((day, round(_fraction(row[erp_col]), 6)))
    if not series:
        raise ValueError(f"no ERP month on or before {as_of_utc}")
    day, value = max(series)
    return day.isoformat(), value


def discount_rate(
    country: str, yields: dict[str, tuple[str, float]], erp: tuple[str, float]
) -> float:
    """r_j for an issuer whose home government bond is ``country``'s."""
    if country not in yields:
        raise ValueError(f"no registered 10-year yield source for {country}")
    return yields[country][1] + erp[1]
