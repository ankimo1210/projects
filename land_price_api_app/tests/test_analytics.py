"""
tests/test_analytics.py
analytics.py のユニットテスト。DuckDB インメモリ DB を使う（ネットワーク接続なし）。
"""
import math
import pathlib
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import duckdb
import pandas as pd

import analytics


# --------------------------------------------------------------------------
# テスト用フィクスチャ
# --------------------------------------------------------------------------

def _make_land_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"point_id": "P1", "year": 2024, "lon": 139.70, "lat": 35.69, "price_yen_per_sqm": 1_000_000, "yoy_change_pct": 5.0, "city_code": "13101", "city_name": "千代田区", "prefecture_code": "13", "prefecture_name": "東京都", "use_category_name": "住宅地"},
        {"point_id": "P2", "year": 2024, "lon": 139.72, "lat": 35.70, "price_yen_per_sqm": 800_000,   "yoy_change_pct": 3.0, "city_code": "13101", "city_name": "千代田区", "prefecture_code": "13", "prefecture_name": "東京都", "use_category_name": "住宅地"},
        {"point_id": "P3", "year": 2024, "lon": 135.50, "lat": 34.69, "price_yen_per_sqm": 500_000,   "yoy_change_pct": -1.0,"city_code": "27100", "city_name": "大阪市",  "prefecture_code": "27", "prefecture_name": "大阪府", "use_category_name": "商業地"},
        {"point_id": "P1", "year": 2023, "lon": 139.70, "lat": 35.69, "price_yen_per_sqm": 950_000,   "yoy_change_pct": 4.0, "city_code": "13101", "city_name": "千代田区", "prefecture_code": "13", "prefecture_name": "東京都", "use_category_name": "住宅地"},
    ])


def _make_conn_with_listings() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE listing_master (
            listing_id VARCHAR, property_name VARCHAR, address VARCHAR,
            property_type VARCHAR, structure VARCHAR,
            asking_price_yen BIGINT, gross_yield_pct DOUBLE,
            gross_rent_annual_yen BIGINT, gross_rent_monthly_yen BIGINT,
            age_years INTEGER, building_area_sqm DOUBLE, land_area_sqm DOUBLE,
            num_units INTEGER, nearest_station VARCHAR, station_walk_min INTEGER,
            source_url VARCHAR, lat DOUBLE, lon DOUBLE
        )
    """)
    conn.execute("""
        INSERT INTO listing_master VALUES
            ('A1', 'マンションA', '東京都千代田区', 'マンション', 'rc',
             100000000, 5.5, 5500000, 458333, 10, 200, 150, 20, '東京駅', 5, 'http://a', 35.691, 139.701),
            ('A2', 'アパートB',   '東京都千代田区', 'アパート',   'wood',
             50000000, 7.0, 3500000, 291667, 20, 100, 200, 8, '神田駅', 8, 'http://b', 35.693, 139.703),
            ('A3', '遠い物件',    '大阪府大阪市',   'マンション', 'rc',
             80000000, 4.5, 3600000, 300000, 5,  150, 100, 15, '大阪駅', 3, 'http://c', 34.702, 135.495)
    """)
    return conn


# --------------------------------------------------------------------------
# テストケース
# --------------------------------------------------------------------------

class TestComputeCitySummary(unittest.TestCase):
    def test_basic(self):
        df = _make_land_df()
        result = analytics.compute_city_summary(df)
        self.assertFalse(result.empty)
        self.assertIn("avg_price", result.columns)
        self.assertIn("point_count", result.columns)

    def test_empty_input(self):
        result = analytics.compute_city_summary(pd.DataFrame())
        self.assertTrue(result.empty)


class TestComputePriceRankings(unittest.TestCase):
    def test_order(self):
        df = _make_land_df()
        ranked = analytics.compute_price_rankings(df, top_n=3, year=2024)
        self.assertEqual(len(ranked), 3)
        prices = ranked["price_yen_per_sqm"].tolist()
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_rank_column(self):
        df = _make_land_df()
        ranked = analytics.compute_price_rankings(df, top_n=2, year=2024)
        self.assertListEqual(ranked["rank"].tolist(), [1, 2])


class TestFindNearbyPoints(unittest.TestCase):
    def test_within_radius(self):
        df = _make_land_df()
        # 千代田区付近で1km半径
        result = analytics.find_nearby_points(df, lon=139.70, lat=35.69, radius_m=5000, year=2024)
        self.assertGreater(len(result), 0)
        self.assertIn("distance_m", result.columns)
        # 大阪市は含まれないはず
        self.assertTrue((result["city_code"] == "13101").all())

    def test_sorted_by_distance(self):
        df = _make_land_df()
        result = analytics.find_nearby_points(df, lon=139.70, lat=35.69, radius_m=50000)
        distances = result["distance_m"].tolist()
        self.assertEqual(distances, sorted(distances))

    def test_empty_df(self):
        result = analytics.find_nearby_points(pd.DataFrame(), lon=139.70, lat=35.69)
        self.assertTrue(result.empty)


class TestFindNearbyListings(unittest.TestCase):
    def setUp(self):
        self.conn = _make_conn_with_listings()

    def tearDown(self):
        self.conn.close()

    def test_finds_nearby(self):
        result = analytics.find_nearby_listings(self.conn, lon=139.70, lat=35.69, radius_m=2000)
        self.assertEqual(len(result), 2)  # A1, A2 は千代田区付近

    def test_excludes_self(self):
        result = analytics.find_nearby_listings(
            self.conn, lon=139.701, lat=35.691, radius_m=2000, exclude_listing_id="A1"
        )
        ids = result["listing_id"].tolist()
        self.assertNotIn("A1", ids)

    def test_no_match(self):
        result = analytics.find_nearby_listings(self.conn, lon=0.0, lat=0.0, radius_m=100)
        self.assertTrue(result.empty)


class TestComputeYoyRankings(unittest.TestCase):
    def test_ascending(self):
        df = _make_land_df()
        result = analytics.compute_yoy_rankings(df, top_n=2, year=2024, ascending=True)
        self.assertGreater(len(result), 0)
        yoys = result["yoy_change_pct"].tolist()
        self.assertEqual(yoys, sorted(yoys))

    def test_descending(self):
        df = _make_land_df()
        result = analytics.compute_yoy_rankings(df, top_n=2, year=2024, ascending=False)
        yoys = result["yoy_change_pct"].tolist()
        self.assertEqual(yoys, sorted(yoys, reverse=True))


class TestComputeIndexedPrices(unittest.TestCase):
    def test_base_year_equals_100(self):
        city_df = pd.DataFrame([
            {"year": 2022, "city_code": "13101", "use_category_name": "住宅地", "avg_price": 1_000_000, "point_count": 5},
            {"year": 2023, "city_code": "13101", "use_category_name": "住宅地", "avg_price": 1_100_000, "point_count": 5},
            {"year": 2024, "city_code": "13101", "use_category_name": "住宅地", "avg_price": 1_200_000, "point_count": 5},
        ])
        result = analytics.compute_indexed_prices(city_df, base_year=2022)
        base_row = result[result["year"] == 2022]
        self.assertAlmostEqual(base_row["index_100"].iloc[0], 100.0, places=1)

    def test_higher_year_above_100(self):
        city_df = pd.DataFrame([
            {"year": 2022, "city_code": "13101", "use_category_name": "住宅地", "avg_price": 1_000_000, "point_count": 5},
            {"year": 2024, "city_code": "13101", "use_category_name": "住宅地", "avg_price": 1_200_000, "point_count": 5},
        ])
        result = analytics.compute_indexed_prices(city_df, base_year=2022)
        later = result[result["year"] == 2024]["index_100"].iloc[0]
        self.assertGreater(later, 100.0)


class TestComputePopulationTrend(unittest.TestCase):
    def setUp(self):
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("""
            CREATE TABLE population_stats (
                city_code VARCHAR, survey_year INTEGER,
                total_population BIGINT, households BIGINT,
                pop_change_pct DOUBLE, households_change_pct DOUBLE,
                aging_rate DOUBLE, net_migration BIGINT
            )
        """)
        self.conn.execute("""
            INSERT INTO population_stats VALUES
                ('13101', 2018, 60000, 30000, NULL, NULL, 15.0, NULL),
                ('13101', 2023, 65000, 33000, NULL, NULL, 16.5, NULL)
        """)

    def tearDown(self):
        self.conn.close()

    def test_returns_latest(self):
        result = analytics.compute_population_trend(self.conn, "13101")
        self.assertEqual(result["latest_year"], 2023)
        self.assertEqual(result["total_population"], 65000)

    def test_change_pct(self):
        result = analytics.compute_population_trend(self.conn, "13101")
        expected = (65000 - 60000) / 60000 * 100
        self.assertAlmostEqual(result["pop_5yr_change_pct"], expected, places=1)

    def test_empty_city(self):
        result = analytics.compute_population_trend(self.conn, "99999")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
