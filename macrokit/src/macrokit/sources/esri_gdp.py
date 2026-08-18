"""Japan's quarterly GDP as each release published it -- the true vintage history.

The foundation spec's organising claim is that Japanese revision history cannot
be recovered. That is true of the e-Stat *API*, which has no realtime parameter.
It is not true of this archive: ESRI keeps every release's own statistical
table, so fetching them one at a time rebuilds the vintages the API will not
serve.

Menu-page URLs follow a stable pattern; the CSV behind them does not. A 2009
release serves ``/jp/sna/content/20120227_nritu_jk0911.csv`` and a 2026 one
serves ``tables/nritu-jk2621.csv``. Never construct the data URL -- read the
menu and pick by label.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from ..store import Observation

MENU_BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files"

MISSING = "***"

# Keyed on the split-and-stripped (left, right) pair of a reference-period
# label such as "1- 3" or "10-12" -- not on the ministry's exact spacing,
# which is inconsistent (a leading space on single-digit months, none on
# "10-12"). Matching on the stripped pair sidesteps that inconsistency
# entirely instead of trying to reproduce it.
_QUARTER_START_MONTH = {("1", "3"): 1, ("4", "6"): 4, ("7", "9"): 7, ("10", "12"): 10}

# "1994/ 1- 3." or "4- 6." -- the year is printed only on the first quarter of
# each year and carries forward to the next three rows.
_LABEL_RE = re.compile(r"^(?:(\d{4})/)?\s*(\d{1,2}-\s?\d{1,2})\.?$")

_KIND_SUFFIX = {"1st_prelim": "", "2nd_prelim": "_2"}


class EsriGdpError(RuntimeError):
    """A release's archive page or table could not be located or parsed."""


def menu_url(period_start: date, release_kind: str) -> str:
    """The release's menu page. Keyed on the *period's* year, not the release's."""
    if release_kind not in _KIND_SUFFIX:
        raise EsriGdpError(
            f"no menu-page URL pattern is known for release_kind={release_kind!r}. "
            "Only 1st_prelim and 2nd_prelim follow the qe{YY}{Q}[_2] scheme; "
            "2nd_prelim_revised is an off-cycle correction and must be located by hand."
        )
    quarter = (period_start.month - 1) // 3 + 1
    stem = f"qe{period_start.year % 100:02d}{quarter}{_KIND_SUFFIX[release_kind]}"
    return f"{MENU_BASE}/{period_start.year}/{stem}/gdemenuja.html"


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text).strip()))
            self._href = None


def select_series_url(
    menu_html: bytes, menu_url_: str, *, series_label: str, stem_prefix: str
) -> str:
    """Resolve the one link that is both labelled ``series_label`` and not a reference series.

    Both eras publish two links carrying the identical label -- ``nritu`` and
    ``knritu``. The ``k`` variant is a reference series with different numbers, so
    matching on the label alone silently loads the wrong data.

    The catalog's ``series_label`` is configured with half-width parentheses,
    but the 2009 archive (qe091/qe092/qe093, both preliminary rounds) prints
    the same label with full-width ones -- ``（前期比）`` instead of
    ``(前期比)``. A raw containment test misses on every one of those six
    pages, silently skipping the release rather than raising. NFKC-normalising
    both sides equates the two widths while keeping this a containment test,
    not equality: the page label always carries a trailing
    ``（CSV形式：…KB）`` size suffix that equality would reject.
    """
    parser = _LinkCollector()
    parser.feed(menu_html.decode("utf-8", errors="replace"))

    normalised_label = unicodedata.normalize("NFKC", series_label)
    matches = [
        href
        for href, label in parser.links
        if normalised_label in unicodedata.normalize("NFKC", label)
        and _stem_matches(href, stem_prefix)
    ]
    if not matches:
        raise EsriGdpError(
            f"{menu_url_}: no link labelled {series_label!r} with a basename carrying "
            f"{stem_prefix!r} as a token. The page layout or the file naming changed."
        )
    if len(matches) > 1:
        raise EsriGdpError(
            f"{menu_url_}: {len(matches)} links match {series_label!r}/{stem_prefix!r}: "
            f"{matches}. Refusing to guess which is the headline series."
        )
    return urljoin(menu_url_, matches[0])


def _stem_matches(href: str, stem_prefix: str) -> bool:
    """True when the basename carries ``stem_prefix`` as a whole token.

    The stem does not always sit at position 0. Older releases prefix the file
    with a migration date -- ``20120227_nritu_jk0911.csv`` -- so a
    ``startswith`` test rejects the very file it is meant to select, and
    rejects the ``knritu`` reference series along with it, leaving nothing.

    Requiring a boundary before the stem keeps ``knritu`` out for free: in
    ``20120227_knritu_jk0911.csv`` the stem is preceded by ``k``, which is not
    a boundary.
    """
    basename = href.rsplit("/", 1)[-1]
    return re.search(rf"(?:^|[_-]){re.escape(stem_prefix)}[_-]", basename) is not None


def _normalise_header(cell: str) -> str:
    """Strip every whitespace character from a header cell, including embedded
    newlines and full-width spaces (``　``).

    Some releases wrap a header across two physical lines inside one CSV cell
    -- ``国内総生産\\n(支出側)`` for ``国内総生産(支出側)`` -- so an exact match
    against the single-line column name configured in the catalog would
    otherwise miss it. Whitespace is removed entirely rather than collapsed to
    a single space: the wrapped cell has no space where it breaks, so
    collapsing to `` `` would still not equal the unbroken name.
    """
    return re.sub(r"\s+", "", cell)


def parse_nritu_csv(content: bytes, *, column: str) -> dict[date, float]:
    """Map each reference period's start date to the annualised QoQ percent change."""
    reader = list(csv.reader(io.StringIO(content.decode("cp932"))))
    target = _normalise_header(column)

    header_index = next(
        (i for i, row in enumerate(reader) if target in [_normalise_header(c) for c in row]), None
    )
    if header_index is None:
        available = sorted(
            {c.strip() for row in reader[:8] for c in row if c.strip() and "," not in c}
        )
        raise EsriGdpError(f"column {column!r} not found; header cells seen: {available}")
    col = [_normalise_header(c) for c in reader[header_index]].index(target)

    series: dict[date, float] = {}
    year: int | None = None
    for record in reader[header_index + 1 :]:
        if not record or not record[0].strip():
            continue
        match = _LABEL_RE.match(record[0].strip())
        if match is None:
            continue  # English header rows and the trailing formula note
        label_year, quarter = match.groups()
        if label_year:
            year = int(label_year)
        if year is None:
            raise EsriGdpError(f"quarter {quarter!r} appears before any year label")
        left, right = (part.strip() for part in quarter.split("-"))
        month = _QUARTER_START_MONTH.get((left, right))
        if month is None:
            raise EsriGdpError(f"unrecognised reference-period quarter: {quarter!r}")
        if col >= len(record):
            continue
        cell = record[col].strip()
        if not cell or cell == MISSING:
            continue
        series[date(year, month, 1)] = float(cell)
    return series


class EsriGdpAdapter:
    source = "esri_gdp"

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_release(self, event, *, series_label: str, stem_prefix: str):
        """Return ``(csv_bytes, csv_url, status)`` for one release."""
        page = menu_url(event.period_start, event.release_kind)
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            menu = client.get(page)
            if menu.status_code != 200:
                raise EsriGdpError(f"GET {page} returned {menu.status_code}")
            data_url = select_series_url(
                menu.content, page, series_label=series_label, stem_prefix=stem_prefix
            )
            data = client.get(data_url)
            if data.status_code != 200:
                raise EsriGdpError(f"GET {data_url} returned {data.status_code}")
        return data.content, data_url, data.status_code

    def parse(
        self, event, content: bytes, *, indicator: str, column: str,
        source_url: str, ingested_at: datetime,
    ) -> list[Observation]:
        series = parse_nritu_csv(content, column=column)
        return [
            Observation(
                indicator=indicator,
                period_start=period_start,
                period_end=_quarter_end(period_start),
                release_date=event.release_date,
                vintage_seq=1 if event.release_kind == "1st_prelim" else 2,
                value=value,
                unit="percent_saar",
                sa="sa",
                freq="Q",
                source=self.source,
                source_url=source_url,
                ingested_at=ingested_at,
                vintage_kind="actual",
            )
            for period_start, value in sorted(series.items())
        ]


def _quarter_end(period_start: date) -> date:
    end_month = period_start.month + 2
    last_day = 31 if end_month in (3, 12) else 30
    return date(period_start.year, end_month, last_day)
