"""Japanese public holidays, taken from the Cabinet Office's official CSV.

Using the government file rather than a third-party package keeps the production
dependency count at zero and makes holidays just another government data source,
consistent with everything else this package fetches.

The file is cp932 (Shift-JIS), not UTF-8, and covers 1955 through the following
year. Rows look like `2026/1/1,元日`; substitute holidays appear under the name
`休日` and count as holidays too, so every dated row is taken.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import httpx

HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


def parse_holiday_csv(raw: bytes) -> set[date]:
    """Parse the Cabinet Office holiday CSV into a set of dates."""
    text = raw.decode("cp932")
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # header: 国民の祝日・休日月日,国民の祝日・休日名称
    holidays: set[date] = set()
    for row in reader:
        if not row or not row[0].strip():
            continue
        year, month, day = (int(part) for part in row[0].strip().split("/"))
        holidays.add(date(year, month, day))
    return holidays


def load_holidays(cache_dir: Path, *, fetch: bool = True) -> set[date]:
    """Return Japanese holidays, downloading and caching the CSV if needed.

    ``fetch=False`` makes this offline-only, which is what tests and any
    no-network run want.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / "syukujitsu.csv"
    if not cached.exists():
        if not fetch:
            raise FileNotFoundError(f"no cached holiday CSV at {cached} and fetch=False")
        response = httpx.get(HOLIDAY_CSV_URL, timeout=30.0)
        response.raise_for_status()
        cached.write_bytes(response.content)
    return parse_holiday_csv(cached.read_bytes())
