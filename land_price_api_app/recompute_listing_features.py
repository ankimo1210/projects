"""
recompute_listing_features.py
保存済み掲載物件に対して location_features / snapshot / valuation を再計算する。
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from datetime import date

import db
import pandas as pd
from analytics import find_nearby_points
from facility_sources import find_nearby_facility_groups, summarize_facility_groups
from hazard_sources import summarize_hazard_risk
from terrain_sources import fetch_elevation_gsi, find_nearby_water, summarize_terrain_features
from valuation import build_valuation_result, score_location_features

PROPERTY_FACILITY_CATEGORIES = [
    "convenience",
    "supermarket",
    "transit",
    "pachinko",
    "food",
    "school",
    "medical",
    "park",
]
FEATURE_VERSION = 1
RADIUS_STEPS = [1000, 2000, 3000, 4000, 5000]


def run_recompute(
    *,
    limit: int = 100,
    stale_days: int = 7,
    sleep_sec: float = 0.0,
    listing_ids: list[str] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    conn = db.get_connection()
    db.create_tables_if_needed(conn)

    latest_years = db.get_available_years(conn)
    latest_year = latest_years[0] if latest_years else 2025
    trade_years_in_db = db.get_trade_available_years(conn)
    trade_years = (
        tuple(sorted(set(trade_years_in_db[:2]), reverse=True))
        if trade_years_in_db
        else (latest_year,)
    )
    land_all = db.read_land_prices(conn, filters={"year": latest_year})
    trade_all = db.read_trade_prices(conn, filters={"year": list(trade_years)})
    if listing_ids:
        targets = db.get_listings_by_ids(conn, listing_ids)
    else:
        targets = db.get_listings_for_recompute(conn, limit=limit, stale_days=stale_days)

    done = 0
    failed = 0
    for idx, row in targets.iterrows():
        listing_id = str(row["listing_id"])
        try:
            _recompute_one(conn, row.to_dict(), land_all, trade_all)
            done += 1
        except Exception:
            failed += 1
        if progress_cb:
            progress_cb(idx + 1, len(targets), listing_id)
        if sleep_sec > 0:
            time.sleep(float(sleep_sec))

    conn.close()
    return {"done": done, "failed": failed}


def _recompute_one(
    conn, listing_row: dict, land_all: pd.DataFrame, trade_all: pd.DataFrame
) -> None:
    lat = float(listing_row["lat"])
    lon = float(listing_row["lon"])
    rounded_lat = round(lat, 5)
    rounded_lon = round(lon, 5)
    location_key = db.make_location_key(rounded_lat, rounded_lon)

    grouped = find_nearby_facility_groups(
        PROPERTY_FACILITY_CATEGORIES, lon=rounded_lon, lat=rounded_lat, radius_m=1000
    )
    facility_summary = summarize_facility_groups(grouped, PROPERTY_FACILITY_CATEGORIES)
    elevation_result = fetch_elevation_gsi(lon=rounded_lon, lat=rounded_lat)
    water_features = find_nearby_water(lon=rounded_lon, lat=rounded_lat, radius_m=1000)
    terrain_summary = summarize_terrain_features(elevation_result, water_features, radius_m=1000)
    hazard_summary = summarize_hazard_risk(lat=rounded_lat, lon=rounded_lon)
    score_summary = score_location_features(
        {**facility_summary, **terrain_summary, **hazard_summary}
    )

    location_row = {
        "location_key": location_key,
        "lat": rounded_lat,
        "lon": rounded_lon,
        "city_code": listing_row.get("city_code"),
        "feature_version": FEATURE_VERSION,
        "facility_radius_m": 1000,
        "terrain_radius_m": 1000,
        **facility_summary,
        **terrain_summary,
        **hazard_summary,
        **score_summary,
    }
    db.upsert_location_features(conn, location_row)

    nearby_land = _find_market_nearby(land_all, lon, lat)
    nearby_trade = _find_market_nearby(trade_all, lon, lat)

    snapshot_row = _build_snapshot(listing_row, location_key, nearby_land, nearby_trade)
    db.upsert_listing_feature_snapshot(conn, snapshot_row)

    valuation_row = build_valuation_result(
        listing_row, snapshot_row, location_row, valuation_version=FEATURE_VERSION
    )
    db.upsert_valuation_result(conn, valuation_row)


def _find_market_nearby(df: pd.DataFrame, lon: float, lat: float) -> pd.DataFrame:
    result = pd.DataFrame()
    for radius_m in RADIUS_STEPS:
        result = find_nearby_points(df, lon, lat, radius_m=radius_m)
        if len(result) >= 3:
            break
    return result


def _build_snapshot(
    listing_row: dict, location_key: str, nearby_land: pd.DataFrame, nearby_trade: pd.DataFrame
) -> dict:
    asking_price = _num(listing_row.get("asking_price_yen"))
    land_area = _num(listing_row.get("land_area_sqm"))
    building_area = _num(listing_row.get("building_area_sqm"))

    land_p25 = (
        float(nearby_land["price_yen_per_sqm"].quantile(0.25)) if not nearby_land.empty else None
    )
    land_p50 = float(nearby_land["price_yen_per_sqm"].median()) if not nearby_land.empty else None
    land_p75 = (
        float(nearby_land["price_yen_per_sqm"].quantile(0.75)) if not nearby_land.empty else None
    )
    trade_median = (
        float(nearby_trade["trade_price_per_sqm"].median()) if not nearby_trade.empty else None
    )

    unit_area_basis = None
    unit_area_sqm = None
    if land_area:
        unit_area_basis = "land"
        unit_area_sqm = land_area
    elif building_area:
        unit_area_basis = "building"
        unit_area_sqm = building_area

    unit_price = asking_price / unit_area_sqm if asking_price and unit_area_sqm else None
    public_gap = (unit_price / land_p50 - 1.0) * 100.0 if unit_price and land_p50 else None
    trade_gap = (unit_price / trade_median - 1.0) * 100.0 if unit_price and trade_median else None

    land_price_low = land_p25 * land_area if land_area and land_p25 else None
    land_price_high = land_p75 * land_area if land_area and land_p75 else None
    residual_low = asking_price - land_price_high if asking_price and land_price_high else None
    residual_high = asking_price - land_price_low if asking_price and land_price_low else None

    return {
        "listing_id": listing_row["listing_id"],
        "snapshot_date": date.today(),
        "location_key": location_key,
        "feature_version": FEATURE_VERSION,
        "asking_price_yen": asking_price,
        "unit_area_basis": unit_area_basis,
        "unit_area_sqm": unit_area_sqm,
        "unit_price_yen_per_sqm": unit_price,
        "nearby_land_count": len(nearby_land),
        "nearby_trade_count": len(nearby_trade),
        "land_unit_price_p25_yen_per_sqm": land_p25,
        "land_unit_price_p75_yen_per_sqm": land_p75,
        "trade_unit_price_median_yen_per_sqm": trade_median,
        "public_notice_gap_pct": public_gap,
        "trade_gap_pct": trade_gap,
        "land_price_estimate_low_yen": land_price_low,
        "land_price_estimate_high_yen": land_price_high,
        "building_residual_low_yen": residual_low,
        "building_residual_high_yen": residual_high,
    }


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--stale-days", type=int, default=7)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    result = run_recompute(limit=args.limit, stale_days=args.stale_days, sleep_sec=args.sleep)
    print(result)


if __name__ == "__main__":
    main()
