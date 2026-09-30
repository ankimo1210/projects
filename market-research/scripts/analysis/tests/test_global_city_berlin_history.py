"""The full Berlin reference-zone history uses a fixed official year set."""

from global_city_berlin_history import YEARS, matched_zone_change, source


def test_full_year_range_and_wfs_typenames():
    assert YEARS == tuple(range(2002, 2027))
    first_url, first_params = source(2002)
    last_url, last_params = source(2026)
    assert first_url.endswith("/brw2002")
    assert first_params["typeNames"] == "brw2002:brw_2002_vector"
    assert last_url.endswith("/brw2026")
    assert last_params["typeNames"] == "brw2026:brw2026_vector"


def test_source_requests_only_attributes_and_complete_set():
    _, params = source(2019)
    assert params["count"] == 10000
    assert params["outputFormat"] == "application/json"
    assert "geom" not in params["propertyName"]


def test_matched_zone_change_excludes_new_zones_and_changed_density():
    rows = [
        {"year": 2022, "borough": "A", "zone_id": "1", "gfz": "1.0", "brw_eur_m2": 100},
        {"year": 2022, "borough": "A", "zone_id": "2", "gfz": "1.0", "brw_eur_m2": 200},
        {"year": 2022, "borough": "A", "zone_id": "3", "gfz": "1.0", "brw_eur_m2": 400},
        {"year": 2026, "borough": "A", "zone_id": "1", "gfz": "1.0", "brw_eur_m2": 80},
        {"year": 2026, "borough": "A", "zone_id": "2", "gfz": "1.0", "brw_eur_m2": 160},
        {"year": 2026, "borough": "A", "zone_id": "3", "gfz": "2.0", "brw_eur_m2": 1000},
        {"year": 2026, "borough": "A", "zone_id": "4", "gfz": "1.0", "brw_eur_m2": 1000},
    ]
    assert matched_zone_change(rows, 2022, 2026) == {"zones": 2, "median_change_pct": -20.0}
