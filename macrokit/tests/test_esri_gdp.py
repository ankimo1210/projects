import os
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from macrokit.sources import esri_gdp
from macrokit.store import ReleaseEvent

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
JST = ZoneInfo("Asia/Tokyo")
MENU = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262/gdemenuja.html"


@pytest.mark.parametrize(
    ("period_start", "kind", "tail"),
    [
        (date(2026, 4, 1), "1st_prelim", "files/2026/qe262/gdemenuja.html"),
        (date(2026, 1, 1), "2nd_prelim", "files/2026/qe261_2/gdemenuja.html"),
        (date(2008, 10, 1), "1st_prelim", "files/2008/qe084/gdemenuja.html"),
        (date(2025, 10, 1), "1st_prelim", "files/2025/qe254/gdemenuja.html"),
    ],
)
def test_menu_url_keys_on_the_period_year_not_the_release_year(period_start, kind, tail):
    assert esri_gdp.menu_url(period_start, kind).endswith(tail)


def test_a_revised_second_preliminary_has_no_derivable_menu_url():
    with pytest.raises(esri_gdp.EsriGdpError, match="2nd_prelim_revised"):
        esri_gdp.menu_url(date(2020, 1, 1), "2nd_prelim_revised")


def test_the_reference_series_with_the_same_label_is_not_selected():
    html = (FIXTURES / "esri_gdemenuja.html").read_bytes()
    url = esri_gdp.select_series_url(
        html, MENU,
        series_label="年率換算の実質季節調整系列(前期比)",
        stem_prefix="nritu",
    )
    assert url.endswith("/tables/nritu-jk2621.csv")
    assert "knritu" not in url


def test_a_relative_href_is_resolved_against_the_menu_url():
    html = (FIXTURES / "esri_gdemenuja.html").read_bytes()
    url = esri_gdp.select_series_url(
        html, MENU,
        series_label="年率換算の実質季節調整系列(前期比)",
        stem_prefix="nritu",
    )
    assert url.startswith("https://www.esri.cao.go.jp/")


def test_the_carried_forward_year_is_applied_to_later_quarters():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    series = esri_gdp.parse_nritu_csv(content, column="国内総生産(支出側)")

    assert series[date(1994, 4, 1)] == -3.0
    assert series[date(1994, 10, 1)] == -1.5
    assert series[date(2026, 1, 1)] == 1.9
    assert series[date(2026, 4, 1)] == 1.1


def test_an_empty_first_quarter_produces_no_entry():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    series = esri_gdp.parse_nritu_csv(content, column="国内総生産(支出側)")
    assert date(1994, 1, 1) not in series


def test_the_column_is_chosen_by_header_text_not_position():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    capex = esri_gdp.parse_nritu_csv(content, column="民間企業設備")
    assert capex[date(2026, 4, 1)] == -4.6


def test_an_unknown_column_names_the_ones_that_exist():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    with pytest.raises(esri_gdp.EsriGdpError, match="国内総生産"):
        esri_gdp.parse_nritu_csv(content, column="存在しない列")


def test_triple_asterisk_is_missing_not_zero():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    public = esri_gdp.parse_nritu_csv(content, column="公的在庫変動")
    assert public == {}


def _event(period_start: date, kind: str) -> ReleaseEvent:
    period_end_month = period_start.month + 2
    last_day = 31 if period_end_month in (3, 12) else 30
    return ReleaseEvent(
        indicator="jp_real_gdp_qoq_saar",
        period_start=period_start,
        period_end=date(period_start.year, period_end_month, last_day),
        release_kind=kind,
        release_date=datetime(period_start.year, period_end_month, 15, 8, 50, tzinfo=JST),
        scheduled=False,
        source="esri_gdp",
        source_url="",
        ingested_at=NOW,
    )


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("MACROKIT_LIVE"), reason="live network test; set MACROKIT_LIVE=1 to run"
)
def test_the_same_quarter_reads_differently_across_two_releases():
    """2026 Q1 is +2.1 in its own 2nd preliminary and +1.9 one release later."""
    adapter = esri_gdp.EsriGdpAdapter()
    kwargs = {"series_label": "年率換算の実質季節調整系列(前期比)", "stem_prefix": "nritu"}

    own = adapter.fetch_release(_event(date(2026, 1, 1), "2nd_prelim"), **kwargs)[0]
    later = adapter.fetch_release(_event(date(2026, 4, 1), "1st_prelim"), **kwargs)[0]

    assert esri_gdp.parse_nritu_csv(own, column="国内総生産(支出側)")[date(2026, 1, 1)] == 2.1
    assert esri_gdp.parse_nritu_csv(later, column="国内総生産(支出側)")[date(2026, 1, 1)] == 1.9
    assert esri_gdp.parse_nritu_csv(later, column="国内総生産(支出側)")[date(2026, 4, 1)] == 1.1
