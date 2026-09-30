"""Small XLSX fixtures for the official rent-file contracts."""

import io
import json
import zipfile

import global_city_pilot as pilot
import pytest


def workbook(sheet_name, rows):
    cells = []
    for row_number, row in enumerate(rows, 3):
        content = "".join(
            f'<c r="{column}{row_number}" t="inlineStr"><is><t>{value}</t></is></c>'
            for column, value in row.items()
        )
        cells.append(f'<row r="{row_number}">{content}</row>')
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
            f"<sheetData>{''.join(cells)}</sheetData></worksheet>",
        )
    return stream.getvalue()


def test_ons_uses_fixed_geography_and_complete_quarters():
    header = {
        "A": "Time period",
        "B": "Area code",
        "C": "Area name",
        "E": "Index",
        "H": "Rental price",
    }
    data = [header]
    for month, index, rent in [(1, 90, 1000), (2, 93, 1100), (3, 96, 1200), (4, 99, 1300)]:
        data.append(
            {
                "A": f"2015-{month:02d}-01",
                "B": "E12000007",
                "C": "London",
                "E": str(index),
                "H": str(rent),
            }
        )
    data.append({"A": "2015-01-01", "B": "E99999999", "C": "Other", "E": "1", "H": "1"})
    rows, stats = pilot.parse_ons_pipr(workbook("Table 1", data))
    assert stats["selected_months"] == 4
    assert stats["incomplete_quarters"] == ["2015Q2"]
    assert [
        (row["metric"], row["period"], row["value"])
        for row in rows
        if row["frequency"] == "quarterly"
    ] == [
        ("rent_index", "2015Q1", 93.0),
    ]
    assert any(row["metric"] == "monthly_rent_gbp" and row["period"] == "2015-04" for row in rows)


def test_ons_rejects_duplicate_month():
    header = {
        "A": "Time period",
        "B": "Area code",
        "C": "Area name",
        "E": "Index",
        "H": "Rental price",
    }
    item = {"A": "2015-01-01", "B": "E12000007", "C": "London", "E": "90", "H": "1000"}
    with pytest.raises(ValueError, match="Duplicate"):
        pilot.parse_ons_pipr(workbook("Table 1", [header, item, item]))


def test_nsw_excludes_unknown_zero_and_non_flat_records():
    data = [
        {
            "A": "Lodgement Date",
            "B": "Postcode",
            "C": "Dwelling Type",
            "D": "Bedrooms",
            "E": "Weekly Rent",
        },
        {"A": "2026-08-01", "B": "2000", "C": "F", "D": "1", "E": "1000"},
        {"A": "2026-08-02", "B": "2000", "C": "F", "D": "2", "E": "1200"},
        {"A": "2026-08-02", "B": "2000", "C": "F", "D": "2", "E": "U"},
        {"A": "2026-08-02", "B": "2000", "C": "F", "D": "2", "E": "0"},
        {"A": "2026-08-02", "B": "2000", "C": "O", "D": "0", "E": "500"},
        {"A": "2026-08-02", "B": "2010", "C": "F", "D": "1", "E": "700"},
    ]
    rows, stats = pilot.parse_nsw_bonds(workbook("August26 Rental Bond Lodgments", data), "2026-08")
    assert stats["raw_rows"] == 6
    assert stats["unknown_rent"] == 1
    assert stats["zero_rent"] == 1
    assert stats["segment_count"] == 3
    assert next(row for row in rows if row["geo_id"] == "nsw_postcode_2000")["value"] == 1100
    assert next(row for row in rows if row["geo_id"] == "nsw_state")["value"] == 1000


def test_nsw_rejects_wrong_month():
    data = [
        {
            "A": "Lodgement Date",
            "B": "Postcode",
            "C": "Dwelling Type",
            "D": "Bedrooms",
            "E": "Weekly Rent",
        },
        {"A": "2026-07-31", "B": "2000", "C": "F", "D": "1", "E": "1000"},
    ]
    with pytest.raises(ValueError, match="month"):
        pilot.parse_nsw_bonds(workbook("August26 Rental Bond Lodgments", data), "2026-08")


def test_collection_archives_xlsx_with_hash_and_source_metadata(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text("year,price_yen_m2\n2026,100\n", encoding="utf-8")
    ons = workbook(
        "Table 1",
        [
            {
                "A": "Time period",
                "B": "Area code",
                "C": "Area name",
                "E": "Index",
                "H": "Rental price",
            },
            {"A": "2015-01-01", "B": "E12000007", "C": "London", "E": "90", "H": "1000"},
        ],
    )
    nsw = workbook(
        "August26 Rental Bond Lodgments",
        [
            {
                "A": "Lodgement Date",
                "B": "Postcode",
                "C": "Dwelling Type",
                "D": "Bedrooms",
                "E": "Weekly Rent",
            },
            {"A": "2026-08-01", "B": "2000", "C": "F", "D": "1", "E": "1000"},
        ],
    )
    raw = pilot.collect_sources(
        "20260928T120000Z",
        tmp_path / "data",
        fukuoka,
        fetch=lambda _url: b"Quarter,All Classes\n01-03/2026,100\n",
        include_ons=True,
        include_nsw=True,
        fetch_spreadsheet=lambda url: ons if url == pilot.ONS_SOURCE else nsw,
    )
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    assert (raw / "uk_pipr.xlsx").read_bytes() == ons
    assert (raw / "nsw_bonds.xlsx").read_bytes() == nsw
    assert manifest["sources"]["uk_pipr"]["period_start"] == "2015-01"
    assert manifest["sources"]["nsw_bonds"]["period_end"] == "2026-08"


def test_collection_rejects_xlsx_with_wrong_statistical_columns(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text("year,price_yen_m2\n2026,100\n", encoding="utf-8")
    wrong = workbook(
        "Table 1",
        [
            {
                "A": "Time period",
                "B": "Area code",
                "C": "Area name",
                "E": "Not an index",
                "H": "Rental price",
            },
            {"A": "2015-01-01", "B": "E12000007", "C": "London", "E": "90", "H": "1000"},
        ],
    )
    with pytest.raises(ValueError, match="uk_pipr"):
        pilot.collect_sources(
            "20260928T120000Z",
            tmp_path / "data",
            fukuoka,
            fetch=lambda _url: b"Quarter,All Classes\n01-03/2026,100\n",
            include_ons=True,
            fetch_spreadsheet=lambda _url: wrong,
        )
    raw = tmp_path / "data/market/raw/global_city_pilot/20260928T120000Z"
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"]["uk_pipr"]["status"] == "failed"
    assert not (raw / "uk_pipr.xlsx").exists()


def test_uk_price_rent_join_uses_only_matching_complete_quarters():
    price = {"uk_london_region": {"2015Q1": 80, "2015Q2": 100, "2015Q3": 120}}
    rents = [
        {"geo_id": "uk_london_region", "metric": "rent_index", "period": "2015Q1", "value": 90},
        {"geo_id": "uk_london_region", "metric": "rent_index", "period": "2015Q2", "value": 99},
        {
            "geo_id": "uk_london_region",
            "metric": "monthly_rent_gbp",
            "period": "2015-07",
            "value": 1000,
        },
    ]
    metrics = pilot.uk_price_rent_metrics(price, rents)
    london = metrics["uk_london_region"]
    assert list(london["relative_price_rent"]) == ["2015Q1", "2015Q2"]
    assert london["relative_price_rent"]["2015Q1"] == 100
    assert london["relative_price_rent"]["2015Q2"] == pytest.approx(100 * 1.25 / 1.1)
    assert london["latest_monthly_rent"] == {"period": "2015-07", "value": 1000}
