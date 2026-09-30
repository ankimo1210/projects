"""Offline checks for the Fukuoka L01 ZIP manifest, link fields and continuing-site table."""

import csv
import hashlib
import io
import json
import re
import zipfile

import fukuoka_continuing_sites as continuing
import fukuoka_land_price_history as history
import global_city_pilot as pilot
import pytest

NAMESPACES = 'xmlns:ksj="http://nlftp.mlit.go.jp/ksj/schemas/ksj-app"'


def land_price(number, price, previous="000", status=None, previous_ward=None, group="000"):
    ward = f"<ksj:administrativeAreaCode>{previous_ward}</ksj:administrativeAreaCode>"
    change = (
        "<ksj:attributeChange><ksj:AttributeChange>"
        f"<ksj:selectedLandStatus>{status}</ksj:selectedLandStatus>"
        "<ksj:address>false</ksj:address></ksj:AttributeChange></ksj:attributeChange>"
        if status
        else ""
    )
    return (
        "<ksj:LandPrice><ksj:representedLandCode><ksj:RepresentedLandCode>"
        f"<ksj:indexNumber>{group}</ksj:indexNumber><ksj:sequenceNumber>{number}</ksj:sequenceNumber>"
        "</ksj:RepresentedLandCode></ksj:representedLandCode>"
        "<ksj:previousRepresentedLandCode><ksj:RepresentedLandCode>"
        + (ward if previous_ward else "")
        + f"<ksj:indexNumber>{'000' if previous == '000' else group}</ksj:indexNumber>"
        f"<ksj:sequenceNumber>{previous}</ksj:sequenceNumber>"
        "</ksj:RepresentedLandCode></ksj:previousRepresentedLandCode>"
        f"<ksj:postedLandPrice>{price}</ksj:postedLandPrice>{change}"
        "<ksj:administrativeAreaCode>40131</ksj:administrativeAreaCode>"
        f"<ksj:address>東区{number}</ksj:address><ksj:currentUse>住宅</ksj:currentUse>"
        "</ksj:LandPrice>"
    )


def l01_zip(year, sites):
    xml = f'<?xml version="1.0" encoding="UTF-8"?><ksj:Dataset {NAMESPACES}>{"".join(sites)}</ksj:Dataset>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo(f"L01-{year % 100:02d}_40.xml"), xml.encode())
        archive.writestr(zipfile.ZipInfo(f"KS-META-L01-{year % 100:02d}_40.xml"), b"<meta/>")
    return buffer.getvalue()


ZIPS = {
    2025: l01_zip(2025, [land_price("001", 100), land_price("002", 300)]),
    2026: l01_zip(
        2026,
        [
            land_price("001", 110, previous="001", status="1", previous_ward="40131"),
            land_price("003", 330, previous="002", status="2"),
            land_price("004", 900, status="4"),
        ],
    ),
}


def fetch_from(zips):
    calls = []

    def fetch(url):
        calls.append(url)
        return zips[2000 + int(re.search(r"L01-(\d\d)_40", url)[1])]

    return fetch, calls


def test_download_records_url_size_and_hash_then_verifies_without_fetching(tmp_path):
    fetch, calls = fetch_from(ZIPS)
    manifest = history.download_missing(tmp_path, [2025, 2026], fetch)
    entry = manifest["files"]["L01-26_40_GML.zip"]
    assert entry["url"] == history.source_url(2026)
    assert entry["url"].endswith("/L01-26/L01-26_40_GML.zip")
    assert entry["bytes"] == len(ZIPS[2026])
    assert entry["sha256"] == hashlib.sha256(ZIPS[2026]).hexdigest()
    assert entry["recorded_from"] == "download"
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert len(calls) == 2

    history.download_missing(tmp_path, [2025, 2026], fetch)
    assert len(calls) == 2  # saved files are verified, not fetched again
    assert history.verify_manifest(tmp_path, [2025, 2026])["files"].keys() == {
        "L01-25_40_GML.zip",
        "L01-26_40_GML.zip",
    }


def test_existing_zip_without_entry_is_recorded_from_disk(tmp_path):
    history.zip_path(2025, tmp_path).write_bytes(ZIPS[2025])
    fetch, calls = fetch_from(ZIPS)
    manifest = history.download_missing(tmp_path, [2025], fetch)
    assert manifest["files"]["L01-25_40_GML.zip"]["recorded_from"] == "existing_file"
    assert calls == []


def test_changed_zip_stops_download_and_build_check(tmp_path):
    fetch, _ = fetch_from(ZIPS)
    history.download_missing(tmp_path, [2025, 2026], fetch)
    path = history.zip_path(2026, tmp_path)
    path.write_bytes(ZIPS[2025])
    with pytest.raises(ValueError, match="mismatch"):
        history.download_missing(tmp_path, [2026], fetch)
    with pytest.raises(ValueError, match="mismatch"):
        history.verify_manifest(tmp_path, [2026])

    path.unlink()  # a re-download must match the recorded hash before it is saved
    changed, _ = fetch_from({2026: ZIPS[2025]})
    with pytest.raises(ValueError, match="mismatch"):
        history.download_missing(tmp_path, [2026], changed)
    assert not path.exists()


def test_verify_requires_a_manifest(tmp_path):
    history.zip_path(2026, tmp_path).write_bytes(ZIPS[2026])
    with pytest.raises(FileNotFoundError, match="--download"):
        history.verify_manifest(tmp_path, [2026])


def test_read_year_keeps_previous_code_and_selection_status(tmp_path):
    history.zip_path(2026, tmp_path).write_bytes(ZIPS[2026])
    rows = {row["code_number"]: row for row in history.read_year(2026, tmp_path)}
    assert rows["001"]["previous_code"] == "40131-000-001"  # code with municipality
    assert rows["003"]["previous_code"] == "40131-000-002"  # older two-part code
    assert rows["004"]["previous_code"] == ""  # new site: 000-000
    assert [rows[n]["land_status"] for n in ("001", "003", "004")] == ["1", "2", "4"]


def test_pilot_reads_links_from_verified_zips_for_old_snapshots(tmp_path):
    fetch, _ = fetch_from(ZIPS)
    history.download_missing(tmp_path, [2025, 2026], fetch)
    rows = [row for year in (2025, 2026) for row in history.read_year(year, tmp_path)]
    stream = io.StringIO()
    fields = ["year", "ward_code", "code_group", "code_number", "price_yen_m2"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode()

    linked, source = pilot.fukuoka_link_rows(payload, tmp_path)
    assert (
        source["l01_manifest_sha256"]
        == hashlib.sha256((tmp_path / "manifest.json").read_bytes()).hexdigest()
    )
    chained = pilot.fukuoka_matched_site_index(linked)
    assert chained == {"index": {"2025": 100.0, "2026": 110.0}, "matches": {"2026": 2}}

    with pytest.raises(ValueError, match="disagree"):
        pilot.fukuoka_link_rows(payload.replace(b",330", b",331"), tmp_path)


def test_era_codes_follow_the_l01_history_fields():
    assert [continuing.era_code(y) for y in (1983, 1988, 1989, 2018, 2019, 2026)] == [
        "S58",
        "S63",
        "H01",
        "H30",
        "R01",
        "R08",
    ]


def test_fixed_sites_need_every_price_and_continuing_or_renumbered_status():
    def site(ward, prices, statuses):
        return {"ward_code": ward, "prices": prices, "statuses": statuses}

    keep = site("40131", {2024: 100, 2025: 110, 2026: 121}, {2025: "1", 2026: "2"})
    gap = site("40131", {2024: 0, 2025: 110, 2026: 121}, {2025: "1", 2026: "1"})
    replaced = site("40132", {2024: 100, 2025: 110, 2026: 300}, {2025: "4", 2026: "1"})
    fixed = continuing.fixed_sites([keep, gap, replaced], 2024)
    assert fixed == [keep]
    assert continuing.median_change_pct(fixed, 2024) == pytest.approx(21.0)
    assert continuing.pct(21.04) == "+21.0%"
