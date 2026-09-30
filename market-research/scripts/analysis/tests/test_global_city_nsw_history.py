"""Contracts for the NSW rental-bond history and ABS postcode boundary."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

import global_city_nsw_history as history
import pytest


def workbook(sheet_name: str, numbered_rows: list[tuple[int, dict[str, str]]]) -> bytes:
    rows = []
    for row_number, fields in numbered_rows:
        cells = "".join(
            f'<c r="{column}{row_number}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            for column, value in fields.items()
        )
        rows.append(f'<row r="{row_number}">{cells}</row>')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(rows)}</sheetData></worksheet>",
        )
    return stream.getvalue()


def test_abs_membership_keeps_boundary_postcodes_explicit():
    mb = workbook(
        "MB_2021_AUST",
        [
            (
                1,
                {
                    "A": "MB_CODE_2021",
                    "B": "MB_CATEGORY_2021",
                    "L": "GCCSA_CODE_2021",
                    "N": "STATE_CODE_2021",
                },
            ),
            (2, {"A": "m1", "B": "Residential", "L": "1GSYD", "N": "1"}),
            (3, {"A": "m2", "B": "Residential", "L": "1GSYD", "N": "1"}),
            (4, {"A": "m3", "B": "Residential", "L": "1RNSW", "N": "1"}),
            (5, {"A": "m4", "B": "Residential", "L": "1RNSW", "N": "1"}),
            (6, {"A": "m5", "B": "Residential", "L": "1RNSW", "N": "1"}),
            (7, {"A": "m6", "B": "Commercial", "L": "1GSYD", "N": "1"}),
            (8, {"A": "m7", "B": "Residential", "L": "1GSYD", "N": "1"}),
            (9, {"A": "m8", "B": "Residential", "L": "1RNSW", "N": "1"}),
        ],
    )
    poa = workbook(
        "POA_2021_AUST",
        [
            (1, {"A": "MB_CODE_2021", "B": "POA_CODE_2021"}),
            (2, {"A": "m1", "B": "2000"}),
            (3, {"A": "m2", "B": "2259"}),
            (4, {"A": "m3", "B": "2259"}),
            (5, {"A": "m4", "B": "2787"}),
            (6, {"A": "m5", "B": "2787"}),
            (7, {"A": "m6", "B": "2000"}),
            (8, {"A": "m7", "B": "2000"}),
            (9, {"A": "m8", "B": "2000"}),
        ],
    )
    mapping, quality = history.derive_metro_postcodes(mb, poa)
    assert mapping["2000"]["metro_share"] == pytest.approx(2 / 3)
    assert mapping["2000"]["is_metro"]
    assert mapping["2259"]["metro_share"] == pytest.approx(0.5)
    assert not mapping["2259"]["is_metro"]
    assert mapping["2787"]["metro_share"] == 0
    assert quality["mixed_postcodes"] == 2


def test_nsw_history_splits_new_tenancy_rent_by_month_and_geography():
    data = workbook(
        "Year 2025 Rental Bond Lodgments",
        [
            (
                3,
                {
                    "A": "Lodgement Date",
                    "B": "Postcode",
                    "C": "Dwelling Type",
                    "D": "Bedrooms",
                    "E": "Weekly Rent",
                },
            ),
            (4, {"A": "2025-01-01", "B": "2000", "C": "F", "D": "1", "E": "1000"}),
            (5, {"A": "2025-01-02", "B": "2000", "C": "F", "D": "2", "E": "1200"}),
            (6, {"A": "2025-01-02", "B": "2010", "C": "F", "D": "1", "E": "800"}),
            (7, {"A": "2025-02-02", "B": "2010", "C": "F", "D": "1", "E": "900"}),
            (8, {"A": "2025-02-03", "B": "2000", "C": "F", "D": "2", "E": "U"}),
            (9, {"A": "2025-02-03", "B": "2000", "C": "F", "D": "2", "E": "0"}),
            (10, {"A": "2025-02-03", "B": "2000", "C": "H", "D": "2", "E": "1500"}),
        ],
    )
    mapping = {
        "2000": {"is_metro": True},
        "2010": {"is_metro": False},
    }
    rows, quality = history.parse_bond_workbook(data, "2025", mapping)
    values = {(r["period"], r["bedrooms"], r["geo_id"]): (r["count"], r["value"]) for r in rows}
    assert values["2025-01", "1", "nsw_state"] == (2, 900)
    assert values["2025-01", "1", "greater_sydney_proxy"] == (1, 1000)
    assert values["2025-01", "2", "greater_sydney_proxy"] == (1, 1200)
    assert values["2025-01", "1-2", "greater_sydney_proxy"] == (2, 1100)
    assert values["2025-02", "1", "nsw_state"] == (1, 900)
    assert ("2025-02", "1", "greater_sydney_proxy") not in values
    assert quality["raw_rows"] == 7
    assert quality["unknown_rent"] == 1
    assert quality["zero_rent"] == 1
    assert quality["eligible_state"] == 4


def test_nsw_history_rejects_date_outside_source_period():
    data = workbook(
        "Sheet1",
        [
            (
                3,
                {
                    "A": "Lodgement Date",
                    "B": "Postcode",
                    "C": "Dwelling Type",
                    "D": "Bedrooms",
                    "E": "Weekly Rent",
                },
            ),
            (4, {"A": "2024-12-31", "B": "2000", "C": "F", "D": "1", "E": "1000"}),
        ],
    )
    with pytest.raises(ValueError, match="period"):
        history.parse_bond_workbook(data, "2025", {"2000": {"is_metro": True}})


def test_catalog_finds_only_requested_lodgement_files():
    html = (
        '<a href="/annual.xlsx">Rental bond lodgement data - year 2025</a>'
        '<a href="/aug.xlsx">Rental bond lodgement data - August 2026</a>'
        '<a href="/refund.xlsx">Rental bond refund data - August 2026</a>'
    )
    sources = history.catalog_sources(html, "https://www.nsw.gov.au/page")
    assert sources == {
        "nsw_2025.xlsx": "https://www.nsw.gov.au/annual.xlsx",
        "nsw_2026-08.xlsx": "https://www.nsw.gov.au/aug.xlsx",
    }


def test_html_report_keeps_price_yield_claims_out_and_shows_boundary():
    rows = [
        {"period": period, "bedrooms": bedroom, "geo_id": geo, "value": value, "count": count}
        for period, bedroom, geo, value, count in [
            ("2021-08", "1", "nsw_state", 420, 100),
            ("2021-08", "1", "greater_sydney_proxy", 440, 90),
            ("2026-08", "1", "nsw_state", 700, 100),
            ("2026-08", "1", "greater_sydney_proxy", 710, 90),
            ("2021-08", "2", "nsw_state", 485, 100),
            ("2021-08", "2", "greater_sydney_proxy", 507.5, 90),
            ("2026-08", "2", "nsw_state", 800, 100),
            ("2026-08", "2", "greater_sydney_proxy", 845, 90),
            ("2021-08", "1-2", "greater_sydney_proxy", 480, 90),
            ("2026-08", "1-2", "greater_sydney_proxy", 775, 90),
        ]
    ]
    quality = {
        "month_count": 68,
        "mapping": {"metro_postcodes": 257, "mixed_postcodes": 3},
        "file_quality": {},
    }
    html = history.render_html(rows, quality, ":root{--series-1:red;--series-2:blue}")
    assert "<!doctype html>" in html
    assert "<style>:root{--series-1:red;--series-2:blue}" in html
    assert "2021-08" in html and "2026-08" in html
    assert "257" in html
    assert "NOI" in html
    assert "61.4%" in html  # 440 -> 710 for 1-bedroom metro rents
