from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.esri import (
    EsriGdpRequest,
    EsriRelease,
    ingest_esri_calendar,
    ingest_esri_gdp,
    releases_from_snapshot,
    select_series_url,
)
from market_research.fetch import FetchError
from market_research.storage import CacheUnavailableError, ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)
XML = """<e-stat><class_1 name="四半期別ＧＤＰ速報">
<class_2 name="平成20年10-12月期"><class_3 name="1次速報"><class_5>
<release_year>2009</release_year><release_month>2</release_month><release_day>16</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_3></class_2>
<class_2 name="2026年4-6月期"><class_3 name="1次速報"><class_5>
<release_year>2026</release_year><release_month>8</release_month><release_day>17</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_3></class_2>
<class_2 name="2026年10-12月期"><class_3 name="2次速報"><class_5>
<release_year>2027</release_year><release_month>3</release_month><release_day>9</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_3></class_2>
</class_1></e-stat>""".encode()
MENU = """<a href="tables/knritu-jk2621.csv">年率換算の実質季節調整系列（前期比）</a>
<a href="tables/nritu-jk2621.csv">年率換算の実質季節調整系列（前期比）</a>""".encode()
CSV = """,国内総生産(支出側),民間企業設備
2026/ 1- 3.,1.9,3.0
4- 6.,1.1,***
""".encode("cp932")
MENU_URL = (
    "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262/gdemenuja.html"
)
CSV_URL = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262/tables/nritu-jk2621.csv"


class Client:
    def __init__(self, *, fail_csv=False, csv=CSV, menu=MENU):
        self.fail_csv = fail_csv
        self.csv = csv
        self.menu = menu
        self.urls = []

    def get(self, url, *, params=None):
        self.urls.append(url)
        if url.endswith("e-stat_sna.xml"):
            return XML
        if url == MENU_URL:
            return self.menu
        if url == CSV_URL and self.fail_csv:
            raise FetchError("network")
        if url == CSV_URL:
            return self.csv
        raise AssertionError(url)


def test_calendar_is_versioned_and_future_listing_stays_scheduled(tmp_path):
    with ResearchStore(tmp_path) as store:
        saved = ingest_esri_calendar(store, client=Client(), now=lambda: NOW)
        events = releases_from_snapshot(store, saved, NOW)
        assert [event.period_start for event in events] == [
            date(2008, 10, 1),
            date(2026, 4, 1),
            date(2026, 10, 1),
        ]
        assert events[0].release_at == datetime(2009, 2, 15, 23, 50, tzinfo=UTC)
        assert events[2].status == "scheduled"
        assert events[1].status == "listed_past"
        with pytest.raises(CacheUnavailableError):
            releases_from_snapshot(store, saved, NOW - timedelta(microseconds=1))
        assert (
            releases_from_snapshot(store, saved, NOW + timedelta(days=400))[2].status == "scheduled"
        )


def test_gdp_menu_selects_headline_and_stores_historical_quarter_revisions(tmp_path):
    assert select_series_url(MENU, MENU_URL) == CSV_URL
    request = EsriGdpRequest(period_start=date(2026, 4, 1), release_kind="1st_prelim")
    with ResearchStore(tmp_path) as store:
        calendar = ingest_esri_calendar(store, client=Client(), now=lambda: NOW)
        event = releases_from_snapshot(store, calendar, NOW)[1]
        result = ingest_esri_gdp(store, request, event, client=Client(), now=lambda: NOW)
        assert len(result.rows) == 2
        assert [row.value for row in result.rows] == [1.9, 1.1]
        assert all(row.vintage_id == "2026-04-01:1st_prelim" for row in result.rows)
        assert (
            store.macro_view(
                "JP_REAL_GDP_QOQ_SAAR", event.release_at - timedelta(microseconds=1), "esri_gdp"
            )
            == ()
        )
        visible = store.macro_view("JP_REAL_GDP_QOQ_SAAR", event.release_at, "esri_gdp")
        assert [row.period_start for row in visible] == [date(2026, 1, 1), date(2026, 4, 1)]


def test_gdp_menu_partial_does_not_publish_and_resumes_csv(tmp_path):
    request = EsriGdpRequest(period_start=date(2026, 4, 1), release_kind="1st_prelim")
    with ResearchStore(tmp_path) as store:
        calendar = ingest_esri_calendar(store, client=Client(), now=lambda: NOW)
        event = releases_from_snapshot(store, calendar, NOW)[1]
        with pytest.raises(FetchError):
            ingest_esri_gdp(store, request, event, client=Client(fail_csv=True), now=lambda: NOW)
        assert store.macro_view("JP_REAL_GDP_QOQ_SAAR", NOW, "esri_gdp") == ()
        pending = store.pending_snapshot(request.key)
        assert pending.cursor == "csv"
        resumed = Client()
        ingest_esri_gdp(store, request, event, client=resumed, now=lambda: NOW, resume=True)
        assert resumed.urls == [CSV_URL]


def test_gdp_rejects_override_for_another_release_period(tmp_path):
    event = EsriRelease(
        date(2025, 4, 1),
        date(2025, 6, 30),
        "1st_prelim",
        datetime(2025, 8, 15, tzinfo=UTC),
        "listed_past",
        NOW,
    )
    request = EsriGdpRequest(
        period_start=event.period_start,
        release_kind=event.release_kind,
        menu_override=MENU_URL,
    )
    with ResearchStore(tmp_path) as store, pytest.raises(ValueError, match="menu URL"):
        ingest_esri_gdp(store, request, event, client=Client(), now=lambda: NOW)
    with ResearchStore(tmp_path) as store:
        assert store.macro_view("JP_REAL_GDP_QOQ_SAAR", NOW, "esri_gdp") == ()


def test_gdp_rejects_csv_with_a_later_quarter_than_release(tmp_path):
    request = EsriGdpRequest(period_start=date(2026, 4, 1), release_kind="1st_prelim")
    future = CSV + "7- 9.,2.2,***\n".encode("cp932")
    with ResearchStore(tmp_path) as store:
        calendar = ingest_esri_calendar(store, client=Client(), now=lambda: NOW)
        event = releases_from_snapshot(store, calendar, NOW)[1]
        with pytest.raises(ValueError, match="final quarter"):
            ingest_esri_gdp(store, request, event, client=Client(csv=future), now=lambda: NOW)
        assert store.macro_view("JP_REAL_GDP_QOQ_SAAR", NOW, "esri_gdp") == ()


def test_revised_release_requires_period_and_kind_in_menu(tmp_path):
    event = EsriRelease(
        date(2026, 4, 1),
        date(2026, 6, 30),
        "2nd_prelim_revised",
        datetime(2026, 9, 20, tzinfo=UTC),
        "listed_past",
        NOW,
    )
    request = EsriGdpRequest(
        period_start=event.period_start,
        release_kind=event.release_kind,
        menu_override=MENU_URL,
    )
    with ResearchStore(tmp_path) as store, pytest.raises(ValueError, match="menu heading"):
        ingest_esri_gdp(store, request, event, client=Client(), now=lambda: NOW)
    verified_menu = "<title>2026年4-6月期 2次速報（改定値）</title>".encode() + MENU
    with ResearchStore(tmp_path) as store:
        result = ingest_esri_gdp(
            store, request, event, client=Client(menu=verified_menu), now=lambda: NOW
        )
        assert result.rows[-1].period_start == event.period_start
