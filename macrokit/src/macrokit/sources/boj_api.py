"""BoJ Time-Series Data Search API: the uncollateralized overnight call rate.

Verified 2026-10-17: ``GET https://www.stat-search.boj.or.jp/api/v1/getDataCode``
with ``format=json&lang=en&db=...&code=...&startDate=YYYYMM`` needs no key and
returns ``RESULTSET[0].VALUES.{SURVEY_DATES, VALUES}``, with ``null`` on days
without a value and ``NEXTPOSITION`` set when the answer is paged (60,000 points
per request; the full daily history is about 15,000).

The daily series (FM01 STRDCLUCON) starts 1998-01-05. The monthly average
(FM02 STRACLUCON) starts 1985-07 and is the curve anchor before 1998 (design
2026-10-17 §3.2). Monthly rows are dated on the first of the month. The current
month's average is incomplete when fetched and ``INSERT OR IGNORE`` never
updates it; only months before 1998 are used, so that row does not matter.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import httpx

from ..store import RateObservation

API_URL = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"
DAILY = ("FM01", "STRDCLUCON", "199801")
MONTHLY_AVERAGE = ("FM02", "STRACLUCON", "198501")
DAILY_CURVE = "jp_call_on"
MONTHLY_CURVE = "jp_call_on_mavg"
OVERNIGHT_TENOR_Y = 1 / 365


class BojApiError(RuntimeError):
    """The BoJ API payload could not be fetched or parsed."""


def _survey_date(code: int) -> date:
    text = str(code)
    if len(text) == 8:
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    if len(text) == 6:
        return date(int(text[:4]), int(text[4:]), 1)
    raise BojApiError(f"unexpected SURVEY_DATES entry {code!r}")


def parse_series(
    content: bytes, *, curve: str, source_url: str, ingested_at: datetime
) -> list[RateObservation]:
    """Rows of one single-series ``getDataCode`` response; nulls are skipped."""
    payload = json.loads(content)
    if payload.get("STATUS") != 200:
        raise BojApiError(f"{source_url}: {payload.get('MESSAGEID')} {payload.get('MESSAGE')}")
    if payload.get("NEXTPOSITION") is not None:
        raise BojApiError(f"{source_url}: paged response (NEXTPOSITION); narrow startDate")
    results = payload.get("RESULTSET") or []
    if len(results) != 1:
        raise BojApiError(f"{source_url}: expected one series, got {len(results)}")
    values = results[0]["VALUES"]
    rows: list[RateObservation] = []
    for code, value in zip(values["SURVEY_DATES"], values["VALUES"], strict=True):
        if value is None:
            continue
        rows.append(
            RateObservation(
                curve=curve,
                obs_date=_survey_date(code),
                tenor_y=OVERNIGHT_TENOR_Y,
                yield_pct=float(value),
                source="boj_api",
                source_url=source_url,
                ingested_at=ingested_at,
            )
        )
    return rows


class BojCallRateAdapter:
    source = "boj_api"

    def __init__(self, *, timeout: float = 60.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> list[tuple[bytes, str, int, str]]:
        """(content, url, status, curve) for the daily and the monthly-average series."""
        payloads: list[tuple[bytes, str, int, str]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for (db, code, start), curve in (
                (DAILY, DAILY_CURVE),
                (MONTHLY_AVERAGE, MONTHLY_CURVE),
            ):
                params = {
                    "format": "json",
                    "lang": "en",
                    "db": db,
                    "code": code,
                    "startDate": start,
                }
                response = client.get(API_URL, params=params)
                if response.status_code != 200:
                    raise BojApiError(f"GET {response.url} returned {response.status_code}")
                payloads.append((response.content, str(response.url), response.status_code, curve))
        return payloads

    def parse(
        self, payloads: list[tuple[bytes, str, int, str]], *, ingested_at: datetime
    ) -> list[RateObservation]:
        rows: list[RateObservation] = []
        for content, url, _status, curve in payloads:
            rows.extend(parse_series(content, curve=curve, source_url=url, ingested_at=ingested_at))
        return rows
