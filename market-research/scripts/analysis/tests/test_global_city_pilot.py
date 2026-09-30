"""Behavioral checks for the global city data pilot."""

import csv
import hashlib
import io
import json

import global_city_pilot as pilot
import pytest


def test_collection_records_html_failure_without_saving_it(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text("year,price_yen_m2\n2026,258100\n", encoding="utf-8")

    def fetch(url):
        if url.endswith("1.4Q.csv"):
            return b"<!doctype html><title>blocked</title>"
        return b"Quarter,All Classes\n01-03/2026,100\n"

    with pytest.raises(ValueError, match="hk_price_q"):
        pilot.collect_sources("20260928T120000Z", tmp_path / "data", fukuoka, fetch)

    raw = tmp_path / "data/market/raw/global_city_pilot/20260928T120000Z"
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"]["hk_price_q"]["status"] == "failed"
    assert not (raw / "hk_price_q.csv").exists()
    assert (raw / "hk_rent_q.csv").exists()


def test_collection_keeps_completed_run_immutable(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text("year,price_yen_m2\n2026,258100\n", encoding="utf-8")
    payload = b"Quarter,All Classes\n01-03/2026,100\n"
    data = tmp_path / "data"
    raw = pilot.collect_sources("20260928T120000Z", data, fukuoka, lambda _url: payload)
    before = (raw / "hk_price_q.csv").read_bytes()

    with pytest.raises(FileExistsError):
        pilot.collect_sources("20260928T120000Z", data, fukuoka, lambda _url: b"new")

    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    assert (raw / "hk_price_q.csv").read_bytes() == before
    assert manifest["sources"]["hk_price_q"]["sha256"] == hashlib.sha256(payload).hexdigest()
    assert manifest["sources"]["hk_price_q"]["raw_columns"] == ["Quarter", "All Classes"]
    assert manifest["sources"]["hk_price_q"]["source_base"] == "1999=100"
    assert manifest["sources"]["hk_price_q"]["period_start"] == "01-03/2026"


def test_quarter_label_rejects_bad_period():
    assert pilot.quarter_label("04-06/2026") == "2026Q2"
    with pytest.raises(ValueError):
        pilot.quarter_label("01-04/2026")


def test_rebase_and_relative_price_rent_are_index_changes():
    assert pilot.rebase({"2015Q1": 200.0, "2026Q2": 300.0}, "2015Q1") == {
        "2015Q1": 100.0,
        "2026Q2": 150.0,
    }
    assert pilot.relative_price_rent(150.0, 120.0) == 125.0
    with pytest.raises(ValueError):
        pilot.rebase({"2015Q1": 0}, "2015Q1")
    with pytest.raises(ValueError):
        pilot.rebase({"2026Q2": 300}, "2015Q1")


def test_hong_kong_two_row_header_preserves_missing_and_provisional():
    payload = (
        b"PRIVATE DOMESTIC PRICE INDICES,,\n"
        b"Quarter,All Classes,All Classes - Remarks\n"
        b"10-12/1979,-,\n"
        b"01-03/2015,200,\n"
        b"04-06/2026,300,P\n"
    )
    rows = pilot.parse_hk_csv(payload, "hk_price_q")
    assert [(r["period"], r["value"], r["remark"]) for r in rows] == [
        ("1979Q4", None, ""),
        ("2015Q1", 200.0, ""),
        ("2026Q2", 300.0, "P"),
    ]
    assert all(r["source_id"] == "hk_price_q" for r in rows)


def test_hong_kong_duplicate_quarter_fails():
    payload = (
        b"TITLE,,\nQuarter,All Classes,All Classes - Remarks\n01-03/2015,200,\n01-03/2015,201,\n"
    )
    with pytest.raises(ValueError, match="Duplicate"):
        pilot.parse_hk_csv(payload, "hk_price_q")


def test_fukuoka_city_average_weights_sites_not_wards():
    payload = (
        "year,ward_code,ward,code_group,code_number,price_yen_m2\n"
        "2026,40131,東区,000,001,100\n"
        "2026,40131,東区,000,002,200\n"
        "2026,40132,博多区,000,001,600\n"
        "2026,40132,博多区,005,001,900\n"
    ).encode()
    rows = pilot.parse_fukuoka_csv(payload)
    city = next(r for r in rows if r["geo_id"] == "fukuoka_city")
    assert city["count"] == 3
    assert city["value"] == 300.0
    assert all(r["source_id"] == "jp_fukuoka_land" for r in rows)


def _land_rows(text: str) -> list[dict[str, str]]:
    header = (
        "year,ward_code,code_group,code_number,address,price_yen_m2,previous_code,land_status\n"
    )
    return list(csv.DictReader(io.StringIO(header + text)))


def test_fukuoka_chain_links_previous_code_and_ignores_new_expensive_site():
    rows = _land_rows(
        "2015,40131,000,001,甲,100,,\n"
        "2015,40131,000,002,乙,300,,\n"
        "2016,40131,000,001,甲,110,40131-000-001,1\n"
        "2016,40131,000,003,乙,330,40131-000-002,2\n"  # renumbered, same site
        "2016,40131,000,004,丙,1000,,4\n"
    )
    chained = pilot.fukuoka_matched_site_index(rows)
    assert chained["index"] == {"2015": 100.0, "2016": 110.0}
    assert chained["matches"] == {"2016": 2}


def test_fukuoka_new_site_reusing_a_retired_number_is_not_linked():
    rows = _land_rows(
        "2021,40135,000,001,甲,100,,\n"
        "2021,40135,000,022,旧地点,100,,\n"
        "2022,40135,000,001,甲の地番表示,110,40135-000-001,1\n"
        "2022,40135,000,022,新地点,500,,4\n"
    )
    chained = pilot.fukuoka_matched_site_index(rows)
    assert chained["index"]["2022"] == 110.0  # address text is not used for linking
    assert chained["matches"]["2022"] == 1


def test_fukuoka_chain_skips_links_from_another_category_and_unknown_status():
    rows = _land_rows(
        "2012,40131,000,001,甲,100,,\n"
        "2012,40131,010,001,乙,100,,\n"
        "2013,40131,000,001,甲,105,40131-000-001,1\n"
        "2013,40131,000,040,乙,200,40131-010-001,2\n"
    )
    assert pilot.fukuoka_matched_site_index(rows)["matches"] == {"2013": 1}
    rows[-1]["land_status"] = "3"
    with pytest.raises(ValueError, match="selectedLandStatus"):
        pilot.fukuoka_matched_site_index(rows)


def test_fukuoka_snapshot_without_link_fields_needs_l01_zips():
    payload = b"year,ward_code,code_group,code_number,price_yen_m2\n2026,40131,000,001,100\n"
    with pytest.raises(ValueError, match="link fields"):
        pilot.fukuoka_link_rows(payload)


def test_saved_sources_produce_separate_coverage_and_relative_index(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text(
        "year,ward_code,ward,code_group,code_number,address,price_yen_m2,previous_code,land_status\n"
        + "".join(
            f"{year},40131,東区,000,001,甲,{200 if year == 2026 else 100},40131-000-001,1\n"
            for year in range(2015, 2027)
        ),
        encoding="utf-8",
    )
    rent = (
        b"TITLE,,\nQuarter,All Classes,All Classes - Remarks\n"
        b"10-12/1979,-,\n01-03/2015,100,\n04-06/2026,120,P\n"
    )
    price = (
        b"TITLE,,\nQuarter,All Classes,All Classes - Remarks\n"
        b"10-12/1979,20,\n01-03/2015,200,\n04-06/2026,300,P\n"
    )
    raw = pilot.collect_sources(
        "20260928T120000Z",
        tmp_path / "data",
        fukuoka,
        lambda url: rent if url.endswith("1.3Q.csv") else price,
    )
    processed = pilot.build_dataset(raw, tmp_path / "processed")
    summary = json.loads((processed / "summary.json").read_text(encoding="utf-8"))
    with (processed / "coverage.csv").open(encoding="utf-8") as stream:
        coverage = list(csv.DictReader(stream))
    assert summary["hong_kong"]["relative_price_rent"]["2026Q2"] == 125.0
    assert summary["hong_kong"]["relative_price_rent"].get("1979Q4") is None
    assert summary["hong_kong"]["price_rebased"]["2015Q1"] == 100.0
    assert summary["fukuoka"]["city"]["2026"]["value"] == 200.0
    assert next(x for x in coverage if x["source_id"] == "hk_rent_q")["missing_observations"] == "1"
    assert (
        next(x for x in coverage if x["source_id"] == "jp_fukuoka_land")["unique_properties"] == ""
    )


def test_saved_source_hash_mismatch_stops_processing(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text("year,price_yen_m2\n2026,258100\n", encoding="utf-8")
    raw = pilot.collect_sources(
        "20260928T120000Z",
        tmp_path / "data",
        fukuoka,
        lambda _url: b"Quarter,All Classes\n01-03/2026,100\n",
    )
    (raw / "hk_price_q.csv").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256"):
        pilot.build_dataset(raw, tmp_path / "processed")


def test_uk_index_uses_codes_and_complete_quarters_only():
    payload = (
        b"Date,Region_Name,Area_Code,Index\n"
        b"1994-12-01,London,E12000007,9\n"
        b"2015-01-01,London,E12000007,75\n"
        b"2015-02-01,London,E12000007,78\n"
        b"2015-03-01,London,E12000007,81\n"
        b"2015-01-01,Manchester,E08000003,50\n"
        b"2015-02-01,Manchester,E08000003,55\n"
        b"2015-03-01,Manchester,E08000003,60\n"
        b"2026-07-01,London,E12000007,99\n"
        b"2026-07-01,Manchester,E08000003,110\n"
        b"2015-01-01,Greater London,E99999999,100\n"
    )
    rows, stats = pilot.parse_uk_index(payload)
    assert len(rows) == 2
    assert {r["geo_id"] for r in rows} == {"uk_london_region", "uk_manchester_city"}
    assert next(r for r in rows if r["geo_id"] == "uk_london_region")["value"] == 78.0
    assert all(r["period"] == "2015Q1" for r in rows)
    assert stats["selected_months"] == 8
    assert stats["incomplete_quarters"] == ["2026Q3"]


def test_uk_index_rejects_duplicate_and_wrong_geography():
    header = "Date,Region_Name,Area_Code,Index\n"
    with pytest.raises(ValueError, match="Duplicate"):
        pilot.parse_uk_index((header + "2015-01-01,London,E12000007,75\n" * 2).encode())
    with pytest.raises(ValueError, match="geography"):
        pilot.parse_uk_index((header + "2015-01-01,City of London,E12000007,75\n").encode())


def test_report_is_self_contained_and_does_not_join_missing_quarters(tmp_path):
    fukuoka = tmp_path / "fukuoka.csv"
    fukuoka.write_text(
        "year,ward_code,ward,code_group,code_number,address,price_yen_m2,previous_code,land_status\n"
        + "".join(
            f"{year},40131,東区,000,001,甲,{200 if year == 2026 else 100},40131-000-001,1\n"
            for year in range(2015, 2027)
        ),
        encoding="utf-8",
    )
    title = "TITLE,,\nQuarter,All Classes,All Classes - Remarks\n"
    inputs = {
        pilot.SOURCES["hk_rent_q"]: (
            title + "01-03/2015,100,\n04-06/2015,-,\n07-09/2015,110,\n04-06/2026,120,P\n"
        ).encode(),
        pilot.SOURCES["hk_price_q"]: (
            title + "01-03/2015,200,\n04-06/2015,210,\n07-09/2015,220,\n04-06/2026,300,P\n"
        ).encode(),
    }
    raw = pilot.collect_sources(
        "20260928T120000Z",
        tmp_path / "data",
        fukuoka,
        lambda url: inputs[url],
    )
    processed = pilot.build_dataset(raw, tmp_path / "processed")
    css = tmp_path / "tokens.css"
    css.write_text(":root{--accent:blue}", encoding="utf-8")
    report = pilot.render_report(raw, processed, css)
    html = report.read_text(encoding="utf-8")
    assert str(tmp_path) not in html  # no collecting machine's absolute path
    assert "fukuoka_land_price_history.py" in html
    assert "2022 表記変更" in html and html.count('stroke-dasharray="3 3"') == 1
    assert "Office for National Statistics" not in html
    assert ":root{--accent:blue}" in html
    assert "福岡市" in html and "香港" in html
    assert "表面利回り" in html and "算出できない" in html
    assert "2015Q2" in html
    assert "fonts.googleapis" not in html
    assert 'class="spark"' in html
    assert "var(--s3)" not in html
    assert pilot.line_segments({"2015Q1": 100, "2015Q3": 110}, "quarterly") == [
        [("2015Q1", 100)],
        [("2015Q3", 110)],
    ]

    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"]["uk_pipr"] = {
        **manifest["sources"]["hk_rent_q"],
        "source": pilot.ONS_SOURCE,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    html = pilot.render_report(raw, processed, css).read_text(encoding="utf-8")
    assert "Source: Office for National Statistics (ONS)" in html
    assert (
        "Contains public sector information licensed under the Open Government Licence v3.0" in html
    )
