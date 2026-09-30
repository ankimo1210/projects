"""Checks for the Berlin official land reference value pilot."""

import pytest
from global_city_berlin_land import parse_zones, summarize_zones


def feature(zone_id, value, *, use="W - Wohngebiet", borough="Mitte", special=None):
    return {
        "properties": {
            "brwid": zone_id,
            "brw": value,
            "nutzung": use,
            "bezirk": borough,
            "anwert": special,
            "stichtag": "2026-01-01",
            "gfz": 1.0,
        }
    }


def test_parse_regular_residential_zones_only():
    payload = {
        "type": "FeatureCollection",
        "numberMatched": 5,
        "numberReturned": 5,
        "features": [
            feature("1", 100),
            feature("2", 300),
            feature("3", 900, use="G - Gewerbe"),
            feature("4", 500, special="N"),
            feature("5", 400, borough="Pankow"),
        ],
    }
    zones, quality = parse_zones(payload, 2026)
    assert [zone["brw_eur_m2"] for zone in zones] == [100, 300, 400]
    assert quality["residential_regular"] == 3
    assert quality["excluded_special_residential"] == 1


def test_reject_incomplete_or_duplicate_source():
    payload = {
        "type": "FeatureCollection",
        "numberMatched": 3,
        "numberReturned": 2,
        "features": [feature("1", 100), feature("2", 200)],
    }
    with pytest.raises(ValueError, match="incomplete"):
        parse_zones(payload, 2026)
    payload["numberMatched"] = 2
    payload["features"][1]["properties"]["brwid"] = "1"
    with pytest.raises(ValueError, match="duplicate"):
        parse_zones(payload, 2026)


def test_accept_official_midnight_timestamp_but_reject_wrong_date():
    payload = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [feature("1", 100)],
    }
    props = payload["features"][0]["properties"]
    props["stichtag"] = "2026-01-01T00:00:00+01:00"
    assert parse_zones(payload, 2026)[1]["residential_regular"] == 1
    props["stichtag"] = "2026-01-02T00:00:00+01:00"
    with pytest.raises(ValueError, match="valuation date"):
        parse_zones(payload, 2026)


def test_summarize_is_zone_count_median_not_area_weighted():
    rows = [
        {"year": 2006, "borough": "Mitte", "brw_eur_m2": 100},
        {"year": 2006, "borough": "Mitte", "brw_eur_m2": 300},
        {"year": 2006, "borough": "Pankow", "brw_eur_m2": 900},
    ]
    summary = summarize_zones(rows)
    assert summary[(2006, "Berlin")]["median_eur_m2"] == 300
    assert summary[(2006, "Mitte")] == {"zones": 2, "median_eur_m2": 200}
