"""
terrain_sources のネットワークなし単体テスト。
"""

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import terrain_sources as ts  # noqa: E402


def test_parse_elevation_payload_accepts_numeric_value():
    result = ts._parse_elevation_payload({"elevation": "12.3", "hsrc": "5m（レーザ）"})

    assert result.elevation_m == 12.3
    assert result.source == "5m（レーザ）"


def test_parse_elevation_payload_treats_no_data_as_none():
    result = ts._parse_elevation_payload({"elevation": "-----"})

    assert result.elevation_m is None
    assert result.source is None


def test_elevation_band():
    assert ts.elevation_band(None) == "不明"
    assert ts.elevation_band(2.9) == "3m未満"
    assert ts.elevation_band(9.9) == "10m未満"
    assert ts.elevation_band(10.0) == "10m以上"


def test_build_water_query_contains_expected_filters():
    query = ts._build_water_query(lat=35.0, lon=139.0, radius_m=1000)

    assert '["waterway"="river"]' in query
    assert '["waterway"="stream"]' in query
    assert '["natural"="water"]' in query
    assert '["natural"="coastline"]' in query
    assert "around:1000,35.0000000,139.0000000" in query
    assert "out center tags" in query


def test_element_to_water_feature_uses_node_coords_and_distance():
    el = {
        "type": "node",
        "id": 123,
        "lat": 35.0009,
        "lon": 139.0,
        "tags": {"name": "テスト川", "waterway": "river"},
    }

    feature = ts._element_to_water_feature(el, origin_lon=139.0, origin_lat=35.0)

    assert feature is not None
    assert feature.feature_id == "osm:node:123"
    assert feature.name == "テスト川"
    assert feature.type_label == "河川"
    assert 95 <= feature.distance_m <= 105


def test_element_to_water_feature_uses_way_center():
    el = {
        "type": "way",
        "id": 456,
        "center": {"lat": 35.0, "lon": 139.001},
        "tags": {"natural": "water"},
    }

    feature = ts._element_to_water_feature(el, origin_lon=139.0, origin_lat=35.0)

    assert feature is not None
    assert feature.feature_id == "osm:way:456"
    assert feature.name == "池・水面"
    assert feature.type_label == "池・水面"


def test_summarize_terrain_features():
    summary = ts.summarize_terrain_features(
        {"elevation_m": 7.5, "source": "5m"},
        [{"distance_m": 120}, {"distance_m": 820}],
    )

    assert summary["elevation_m"] == 7.5
    assert summary["elevation_band"] == "10m未満"
    assert summary["elevation_source"] == "5m"
    assert summary["nearest_water_m"] == 120
    assert summary["water_count_1000m"] == 2
