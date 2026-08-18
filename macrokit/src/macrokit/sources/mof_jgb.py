"""MoF JGB constant-maturity yields from two public CSVs (no API key).

The ministry splits the curve across two files: ``jgbcm_all.csv`` ends at the
previous month-end and ``jgbcm.csv`` carries the current month. Both must be
read and unioned, or the most recent weeks are silently absent.

Yields are not revised, so these rows carry no vintage key -- see the spec's
data-model section for why they live outside ``observations``.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

import httpx

from ..store import RateObservation

BASE = "https://www.mof.go.jp/jgbs/reference/interest_rate"
HISTORY_URL = f"{BASE}/data/jgbcm_all.csv"
CURRENT_URL = f"{BASE}/jgbcm.csv"

# Gregorian year = era offset + era year. 1925 + 49 = 1974 (Showa 49).
ERA_OFFSET = {"S": 1925, "H": 1988, "R": 2018}

MISSING = "-"


class MofJgbError(RuntimeError):
    """The MoF payload could not be fetched or parsed."""


def parse_wareki(token: str) -> date:
    """``R8.7.31`` -> ``date(2026, 7, 31)``."""
    token = token.strip()
    era = token[:1]
    if era not in ERA_OFFSET:
        raise MofJgbError(f"unknown era prefix in date {token!r}; known: {sorted(ERA_OFFSET)}")
    try:
        year, month, day = (int(part) for part in token[1:].split("."))
    except ValueError as exc:
        raise MofJgbError(f"malformed wareki date: {token!r}") from exc
    return date(ERA_OFFSET[era] + year, month, day)


def _tenor_of(header_cell: str) -> float:
    """``10年`` -> ``10.0``."""
    return float(header_cell.strip().removesuffix("年"))


def parse_jgb_csv(
    content: bytes, *, source_url: str, ingested_at: datetime
) -> list[RateObservation]:
    text = content.decode("cp932")
    reader = list(csv.reader(io.StringIO(text)))
    if len(reader) < 2:
        raise MofJgbError(f"payload from {source_url} has no header row")

    # Row 0 is a title banner; row 1 is the real header.
    tenors = [_tenor_of(cell) for cell in reader[1][1:] if cell.strip()]

    rows: list[RateObservation] = []
    for record in reader[2:]:
        if not record or not record[0].strip():
            continue  # blank separator line before the trailing notice
        if record[0][:1] not in ERA_OFFSET:
            continue  # the trailing "※..." notice line
        obs_date = parse_wareki(record[0])
        for tenor, cell in zip(tenors, record[1:], strict=False):
            value = cell.strip()
            if value == MISSING or not value:
                continue  # this tenor did not exist on this date
            rows.append(
                RateObservation(
                    curve="jgb",
                    obs_date=obs_date,
                    tenor_y=tenor,
                    yield_pct=float(value),
                    source="mof_jgb",
                    source_url=source_url,
                    ingested_at=ingested_at,
                )
            )
    return rows


class MofJgbAdapter:
    source = "mof_jgb"
    HISTORY_URL = HISTORY_URL
    CURRENT_URL = CURRENT_URL

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> list[tuple[bytes, str, int]]:
        payloads: list[tuple[bytes, str, int]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for url in (self.HISTORY_URL, self.CURRENT_URL):
                response = client.get(url)
                if response.status_code != 200:
                    raise MofJgbError(f"GET {url} returned {response.status_code}")
                payloads.append((response.content, url, response.status_code))
        return payloads

    def parse(
        self, payloads: list[tuple[bytes, str, int]], *, ingested_at: datetime
    ) -> list[RateObservation]:
        """Union the payloads, keeping the first row seen for a (date, tenor)."""
        seen: dict[tuple[date, float], RateObservation] = {}
        for content, url, _status in payloads:
            for row in parse_jgb_csv(content, source_url=url, ingested_at=ingested_at):
                seen.setdefault((row.obs_date, row.tenor_y), row)
        return sorted(seen.values(), key=lambda r: (r.obs_date, r.tenor_y))
