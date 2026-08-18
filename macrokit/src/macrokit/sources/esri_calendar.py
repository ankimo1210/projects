"""Observed publication timestamps for Japan's quarterly GDP, from ESRI's e-Stat feed.

This is the *observed* calendar, not a rule: ``release.resolve_release`` predicts
future dates from a ``ReleaseRule``, whereas this module records what actually
happened. GDP's rule is ``manual`` precisely because these 148 exact timestamps
exist.

The feed carries scheduled and released rows in an identical shape with nothing
to distinguish them, so ``scheduled`` can only mean "still in the future when we
read it".
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from ..store import ReleaseEvent

XML_URL = "https://www.esri.cao.go.jp/jp/sna/e-stat_sna.xml"

# The ministry writes the statistic's name with a full-width ＧＤＰ. A half-width
# "GDP" matches nothing, and the mismatch is invisible in most editors.
GDP_CLASS_1 = "四半期別ＧＤＰ速報"

KIND_MAP = {
    "1次速報": "1st_prelim",
    "2次速報": "2nd_prelim",
    "2次速報（改定値）": "2nd_prelim_revised",
}

JST = ZoneInfo("Asia/Tokyo")

# 平成20年10-12月期 / 2026年4-6月期. Era years appear up to the 2019-05-20
# release and 令和 never appears at all -- they switched straight to western
# years -- so only 平成 needs an offset.
_PERIOD_RE = re.compile(r"^(?:(平成)(\d+)|(\d{4}))年(\d+)-(\d+)月期$")
_HEISEI_OFFSET = 1988

_QUARTER_END_DAY = {3: 31, 6: 30, 9: 30, 12: 31}


class EsriCalendarError(RuntimeError):
    """The calendar payload could not be fetched or parsed."""


def parse_period_name(name: str) -> tuple[date, date]:
    """``平成20年10-12月期`` -> ``(2008-10-01, 2008-12-31)``."""
    match = _PERIOD_RE.match(name.strip())
    if match is None:
        raise EsriCalendarError(f"unrecognised reference-period name: {name!r}")
    era, era_year, western, start_month, end_month = match.groups()
    year = _HEISEI_OFFSET + int(era_year) if era else int(western)
    start = date(year, int(start_month), 1)
    end_month_i = int(end_month)
    if end_month_i not in _QUARTER_END_DAY:
        raise EsriCalendarError(f"period {name!r} does not end on a quarter boundary")
    return start, date(year, end_month_i, _QUARTER_END_DAY[end_month_i])


def parse_calendar_xml(
    content: bytes, *, indicator: str, source_url: str, ingested_at: datetime
) -> list[ReleaseEvent]:
    root = ET.fromstring(content)
    events: list[ReleaseEvent] = []
    for class_1 in root.iter("class_1"):
        if class_1.get("name") != GDP_CLASS_1:
            continue
        for class_2 in class_1.findall("class_2"):
            period_start, period_end = parse_period_name(class_2.get("name", ""))
            for class_3 in class_2.findall("class_3"):
                raw_kind = class_3.get("name", "")
                if raw_kind not in KIND_MAP:
                    raise EsriCalendarError(
                        f"unknown release kind {raw_kind!r} for {class_2.get('name')!r}; "
                        f"known: {sorted(KIND_MAP)}"
                    )
                for class_5 in class_3.iter("class_5"):
                    release_date = _release_datetime(class_5)
                    events.append(
                        ReleaseEvent(
                            indicator=indicator,
                            period_start=period_start,
                            period_end=period_end,
                            release_kind=KIND_MAP[raw_kind],
                            release_date=release_date,
                            scheduled=release_date > ingested_at,
                            source="esri_calendar",
                            source_url=source_url,
                            ingested_at=ingested_at,
                        )
                    )
    return events


def _release_datetime(class_5: ET.Element) -> datetime:
    def part(tag: str) -> int:
        text = class_5.findtext(tag)
        if text is None or not text.strip():
            raise EsriCalendarError(f"release entry is missing <{tag}>")
        return int(text)

    return datetime(
        part("release_year"), part("release_month"), part("release_day"),
        part("release_hour"), part("release_minute"), tzinfo=JST,
    )


class EsriCalendarAdapter:
    source = "esri_calendar"
    XML_URL = XML_URL

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> tuple[bytes, str, int]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(self.XML_URL)
        if response.status_code != 200:
            raise EsriCalendarError(f"GET {self.XML_URL} returned {response.status_code}")
        return response.content, self.XML_URL, response.status_code

    def parse(
        self, content: bytes, *, indicator: str, source_url: str, ingested_at: datetime
    ) -> list[ReleaseEvent]:
        return parse_calendar_xml(
            content, indicator=indicator, source_url=source_url, ingested_at=ingested_at
        )
