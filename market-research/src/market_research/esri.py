"""ESRI GDP release listings and the archived headline CSV vintages."""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from .contracts import MacroObservation, _utc
from .fetch import FetchError, HttpClient
from .storage import CacheKey, CacheUnavailableError, ResearchStore, Snapshot, _json

CALENDAR_URL = "https://www.esri.cao.go.jp/jp/sna/e-stat_sna.xml"
MENU_BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files"
LABEL = "年率換算の実質季節調整系列(前期比)"
KIND_MAP = {
    "1次速報": "1st_prelim",
    "2次速報": "2nd_prelim",
    "2次速報（改定値）": "2nd_prelim_revised",
}
JST = ZoneInfo("Asia/Tokyo")
PERIOD_RE = re.compile(r"^(?:平成(\d+)|(\d{4}))年(\d+)-(\d+)月期$")
QUARTERS = {"1-3": 1, "4-6": 4, "7-9": 7, "10-12": 10}
CSV_LABEL = re.compile(r"^(?:(\d{4})/)?\s*(\d{1,2}-\s?\d{1,2})\.?$")
CALENDAR_KEY = CacheKey("esri_calendar", "release_calendar", "GDP", "quarterly", "none", "none")


@dataclass(frozen=True, slots=True)
class EsriRelease:
    period_start: date
    period_end: date
    release_kind: str
    release_at: datetime
    status: str
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class EsriGdpRequest:
    period_start: date
    release_kind: str
    indicator: str = "JP_REAL_GDP_QOQ_SAAR"
    column: str = "国内総生産(支出側)"
    series_label: str = LABEL
    menu_override: str | None = None

    def __post_init__(self):
        if self.period_start.month not in (1, 4, 7, 10) or self.period_start.day != 1:
            raise ValueError("GDP period_start must be a quarter start")
        if self.release_kind not in KIND_MAP.values():
            raise ValueError("unknown ESRI GDP release kind")
        if self.release_kind == "2nd_prelim_revised" and self.menu_override is None:
            raise ValueError("revised ESRI release needs an explicit menu URL")
        if self.menu_override is not None:
            _official_url(self.menu_override)

    @property
    def key(self) -> CacheKey:
        return CacheKey(
            "esri_gdp",
            "macro",
            self.indicator,
            "quarterly",
            "percent_saar",
            "none",
            request_json=_json(
                {
                    "period_start": self.period_start,
                    "release_kind": self.release_kind,
                    "column": self.column,
                    "series_label": self.series_label,
                    "menu_override": self.menu_override,
                    "normalization_version": 1,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class EsriGdpResult:
    snapshot: Snapshot
    rows: tuple[MacroObservation, ...]


def _official_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "www.esri.cao.go.jp" or parts.username:
        raise ValueError("ESRI URL must be on the official HTTPS host")
    if parts.query or parts.fragment:
        raise ValueError("ESRI URL must not contain a query or fragment")
    return url


def _period(name: str) -> tuple[date, date]:
    match = PERIOD_RE.fullmatch(name.strip())
    if match is None:
        raise ValueError("unknown ESRI GDP period label")
    era_year, western, start_month, end_month = match.groups()
    year = 1988 + int(era_year) if era_year else int(western)
    start = int(start_month)
    end = int(end_month)
    if start not in (1, 4, 7, 10) or end != start + 2:
        raise ValueError("ESRI GDP label is not a calendar quarter")
    day = 31 if end in (3, 12) else 30
    return date(year, start, 1), date(year, end, day)


def parse_esri_calendar(raw: bytes, observed_at: datetime) -> tuple[EsriRelease, ...]:
    observed = _utc(observed_at, "observed_at")
    root = ET.fromstring(raw)
    events = []
    for category in root.iter("class_1"):
        if category.get("name") != "四半期別ＧＤＰ速報":
            continue
        for period in category.findall("class_2"):
            start, end = _period(period.get("name", ""))
            for kind in period.findall("class_3"):
                if kind.get("name") not in KIND_MAP:
                    raise ValueError("unknown ESRI GDP release kind")
                for entry in kind.iter("class_5"):
                    parts = [
                        int(entry.findtext(name))
                        for name in (
                            "release_year",
                            "release_month",
                            "release_day",
                            "release_hour",
                            "release_minute",
                        )
                    ]
                    release = datetime(*parts, tzinfo=JST).astimezone(UTC)
                    events.append(
                        EsriRelease(
                            start,
                            end,
                            KIND_MAP[kind.get("name")],
                            release,
                            "scheduled" if release > observed else "listed_past",
                            observed,
                        )
                    )
    if not events:
        raise ValueError("ESRI calendar contains no GDP events")
    return tuple(sorted(events, key=lambda event: (event.period_start, event.release_at)))


def ingest_esri_calendar(
    store: ResearchStore,
    *,
    client: HttpClient | None = None,
    now=lambda: datetime.now(UTC),
) -> Snapshot:
    raw = (client or HttpClient()).get(CALENDAR_URL)
    observed = _utc(now(), "observed_at")
    parse_esri_calendar(raw, observed)
    return store.save(CALENDAR_KEY, raw, observed_at=observed)


def releases_from_snapshot(
    store: ResearchStore, snapshot: Snapshot, when: datetime
) -> tuple[EsriRelease, ...]:
    cutoff = _utc(when, "when")
    saved = store.get_snapshot(snapshot.snapshot_id)
    if not saved.complete or saved.key != CALENDAR_KEY or saved.observed_at > cutoff:
        raise CacheUnavailableError("complete ESRI calendar snapshot unavailable")
    return parse_esri_calendar(store.read_raw(saved), saved.observed_at)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.words: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.words = []

    def handle_data(self, data):
        if self.href is not None:
            self.words.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.words)))
            self.href = None


class _Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings: list[str] = []
        self.active: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in ("title", "h1"):
            self.active = []

    def handle_data(self, data):
        if self.active is not None:
            self.active.append(data)

    def handle_endtag(self, tag):
        if tag in ("title", "h1") and self.active is not None:
            self.headings.append("".join(self.active))
            self.active = None


def select_series_url(menu_html: bytes, menu_url: str, *, label: str = LABEL) -> str:
    links = _Links()
    links.feed(menu_html.decode("utf-8", errors="replace"))
    expected = unicodedata.normalize("NFKC", label)
    matches = []
    for href, text in links.links:
        stem = href.rsplit("/", 1)[-1]
        if expected not in unicodedata.normalize("NFKC", text):
            continue
        if re.search(r"(?:^|[_-])nritu[_-]", stem) is None:
            continue
        resolved = _official_url(urljoin(menu_url, href))
        if not resolved.lower().endswith(".csv"):
            continue
        matches.append(resolved)
    if len(matches) != 1:
        raise ValueError("ESRI GDP menu has no unique headline CSV")
    return matches[0]


def _expected_menu_url(request: EsriGdpRequest) -> str:
    year = request.period_start.year
    quarter = (request.period_start.month - 1) // 3 + 1
    suffix = "_2" if request.release_kind == "2nd_prelim" else ""
    return f"{MENU_BASE}/{year}/qe{year % 100:02d}{quarter}{suffix}/gdemenuja.html"


def _menu_url(request: EsriGdpRequest) -> str:
    return request.menu_override or _expected_menu_url(request)


def _validate_release_menu(request: EsriGdpRequest, menu_url: str, menu: bytes) -> None:
    if request.release_kind != "2nd_prelim_revised":
        if menu_url != _expected_menu_url(request):
            raise ValueError("ESRI GDP menu URL does not match release period and kind")
        return
    headings = _Headings()
    headings.feed(menu.decode("utf-8", errors="replace"))
    year, month = request.period_start.year, request.period_start.month
    period_labels = (f"{year}年{month}-{month + 2}月期",)
    if 1989 <= year <= 2018:
        period_labels += (f"平成{year - 1988}年{month}-{month + 2}月期",)
    if year >= 2019:
        period_labels += (f"令和{year - 2018}年{month}-{month + 2}月期",)
    for heading in headings.headings:
        normalized = re.sub(r"\s+", "", unicodedata.normalize("NFKC", heading))
        if any(period in normalized for period in period_labels) and all(
            word in normalized for word in ("2次速報", "改定")
        ):
            return
    raise ValueError("ESRI GDP menu heading does not identify revised release")


def _validate_csv_url(csv_url: str, menu_url: str) -> None:
    csv_url = _official_url(csv_url)
    if not csv_url.startswith(menu_url.rsplit("/", 1)[0] + "/"):
        raise ValueError("ESRI GDP CSV URL is outside release menu directory")


def parse_gdp_csv(raw: bytes, column: str) -> dict[date, float]:
    reader = list(csv.reader(io.StringIO(raw.decode("cp932"))))

    def stripped(cell: str) -> str:
        return re.sub(r"\s+", "", cell)

    target = stripped(column)
    header = next((row for row in reader if target in [stripped(c) for c in row]), None)
    if header is None:
        raise ValueError("ESRI GDP column not found")
    index = [stripped(c) for c in header].index(target)
    start_at = reader.index(header) + 1
    year = None
    values = {}
    for record in reader[start_at:]:
        if not record:
            continue
        match = CSV_LABEL.fullmatch(record[0].strip())
        if match is None:
            continue
        label_year, quarter = match.groups()
        year = int(label_year) if label_year else year
        if year is None:
            raise ValueError("ESRI GDP quarter has no year")
        month = QUARTERS.get(quarter.replace(" ", ""))
        if month is None:
            raise ValueError("unknown ESRI GDP quarter")
        if index >= len(record) or record[index].strip() in ("", "***"):
            continue
        values[date(year, month, 1)] = float(record[index].strip())
    if not values:
        raise ValueError("ESRI GDP CSV has no values")
    return values


def _envelope(
    request: EsriGdpRequest, event: EsriRelease, url: str, menu: bytes, csv_raw: bytes | None = None
) -> bytes:
    return _json(
        {
            "key_digest": request.key.digest,
            "release_at": event.release_at,
            "csv_url": url,
            "menu": base64.b64encode(menu).decode(),
            "csv": base64.b64encode(csv_raw).decode() if csv_raw is not None else None,
        }
    ).encode()


def ingest_esri_gdp(
    store: ResearchStore,
    request: EsriGdpRequest,
    event: EsriRelease,
    *,
    client: HttpClient | None = None,
    now=lambda: datetime.now(UTC),
    resume: bool = False,
) -> EsriGdpResult:
    if (event.period_start, event.release_kind) != (request.period_start, request.release_kind):
        raise ValueError("GDP request does not match the release event")
    if event.release_at > _utc(now(), "observed_at"):
        raise ValueError("GDP release is still scheduled")
    menu_url = _menu_url(request)
    if request.release_kind != "2nd_prelim_revised" and menu_url != _expected_menu_url(request):
        raise ValueError("ESRI GDP menu URL does not match release period and kind")
    http = client or HttpClient()
    pending = None
    if resume:
        try:
            pending = json.loads(store.read_raw(store.pending_snapshot(request.key)))
        except CacheUnavailableError:
            pass
    if pending is not None:
        if (
            pending["key_digest"] != request.key.digest
            or pending["release_at"] != event.release_at.isoformat()
        ):
            raise ValueError("GDP pending snapshot does not match release")
        menu = base64.b64decode(pending["menu"])
        csv_url = _official_url(pending["csv_url"])
    else:
        menu = http.get(menu_url)
        csv_url = select_series_url(menu, menu_url, label=request.series_label)
    _validate_release_menu(request, menu_url, menu)
    _validate_csv_url(csv_url, menu_url)
    try:
        csv_raw = http.get(csv_url)
    except FetchError as error:
        raw = _envelope(request, event, csv_url, menu)
        store.save(
            request.key, raw, observed_at=_utc(now(), "observed_at"), complete=False, cursor="csv"
        )
        raise FetchError(
            error.category, status=error.status, partial_raw=raw, cursor="csv"
        ) from None
    values = parse_gdp_csv(csv_raw, request.column)
    if max(values) != request.period_start:
        raise ValueError("ESRI GDP CSV final quarter does not match release period")
    observed = _utc(now(), "observed_at")
    if event.release_at > observed:
        raise ValueError("GDP release is still scheduled")
    rows = tuple(
        MacroObservation(
            indicator=request.indicator,
            period_start=period,
            release_at=event.release_at,
            value=value,
            source="esri_gdp",
            vintage_id=f"{event.period_start.isoformat()}:{event.release_kind}",
            vintage_kind="actual",
            unit="percent_saar",
            frequency="quarterly",
            seasonal_adjustment="sa",
            release_precision="instant",
            source_release_date=event.release_at.astimezone(JST).date(),
            source_ref=csv_url,
        )
        for period, value in sorted(values.items())
    )
    snapshot = store.save(
        request.key,
        _envelope(request, event, csv_url, menu, csv_raw),
        observed_at=observed,
        macro=rows,
    )
    return EsriGdpResult(snapshot, rows)
