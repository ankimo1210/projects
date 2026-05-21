"""
facility_sources のネットワークなし単体テスト。
"""

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import facility_sources as fs  # noqa: E402


def test_element_to_facility_uses_node_coords_and_distance():
    el = {
        "type": "node",
        "id": 123,
        "lat": 35.0009,
        "lon": 139.0,
        "tags": {"name": "テストコンビニ", "brand": "Brand A"},
    }

    facility = fs._element_to_facility(
        el, origin_lon=139.0, origin_lat=35.0, category="convenience"
    )

    assert facility is not None
    assert facility.facility_id == "osm:node:123"
    assert facility.name == "テストコンビニ"
    assert facility.brand == "Brand A"
    assert 95 <= facility.distance_m <= 105


def test_element_to_facility_uses_way_center():
    el = {
        "type": "way",
        "id": 456,
        "center": {"lat": 35.0, "lon": 139.001},
        "tags": {"operator": "Operator B"},
    }

    facility = fs._element_to_facility(
        el, origin_lon=139.0, origin_lat=35.0, category="convenience"
    )

    assert facility is not None
    assert facility.facility_id == "osm:way:456"
    assert facility.name == "Operator B"
    assert facility.operator == "Operator B"


def test_build_convenience_query_contains_expected_filter():
    query = fs._build_convenience_query(lat=35.0, lon=139.0, radius_m=1000)

    assert '["shop"="convenience"]' in query
    assert "around:1000,35.0000000,139.0000000" in query
    assert "out center tags" in query


def test_build_category_query_contains_multiple_filters():
    query = fs._build_category_query(category="pachinko", lat=35.0, lon=139.0, radius_m=1000)

    assert '["leisure"="adult_gaming_centre"]' in query
    assert '["gambling"="pachinko"]' in query
    assert '["amenity"="gambling"]' in query


def test_build_multi_category_query_contains_each_category_filter_once():
    query = fs._build_multi_category_query(
        categories=["convenience", "supermarket"],
        lat=35.0,
        lon=139.0,
        radius_m=1000,
    )

    assert query.count('["shop"="convenience"]') == 3
    assert query.count('["shop"="supermarket"]') == 3


def test_matching_categories():
    assert fs._matching_categories({"shop": "supermarket"}, ["convenience", "supermarket"]) == [
        "supermarket"
    ]
    assert fs._matching_categories({"gambling": "pachinko"}, ["pachinko"]) == ["pachinko"]


def test_summarize_facility_groups():
    grouped = {
        "convenience": [
            {"distance_m": 120},
            {"distance_m": 620},
        ],
        "supermarket": [],
    }

    summary = fs.summarize_facility_groups(grouped, ["convenience", "supermarket"])

    assert summary["convenience_count_500m"] == 1
    assert summary["convenience_count_1000m"] == 2
    assert summary["convenience_nearest_m"] == 120
    assert summary["supermarket_count_500m"] == 0
    assert summary["supermarket_nearest_m"] is None
