"""
recompute_market_features.py
公示地価・取引価格地点へ共通の location_features を付与する。
"""
from __future__ import annotations

import argparse
import time

import db
from facility_sources import find_nearby_facility_groups, summarize_facility_groups
from hazard_sources import summarize_hazard_risk
from terrain_sources import fetch_elevation_gsi, find_nearby_water, summarize_terrain_features
from valuation import score_location_features

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


def run_market_feature_backfill(dataset: str, *, year: int | None = None, limit: int = 500, sleep_sec: float = 0.0) -> dict[str, int]:
    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    if dataset == "public_notice":
        targets = db.get_public_notice_feature_targets(conn, year=year, limit=limit)
    elif dataset == "trade":
        targets = db.get_trade_feature_targets(conn, year=year, limit=limit)
    else:
        raise ValueError(f"unknown dataset: {dataset}")

    done = 0
    failed = 0
    for _, row in targets.iterrows():
        try:
            location_key = _ensure_location_feature(conn, row["lat"], row["lon"], row.get("city_code"))
            if dataset == "public_notice":
                db.upsert_public_notice_location_feature(
                    conn,
                    {
                        "point_id": row["point_id"],
                        "year": int(row["year"]),
                        "location_key": location_key,
                        "feature_version": FEATURE_VERSION,
                    },
                )
            else:
                db.upsert_trade_location_feature(
                    conn,
                    {
                        "trade_id": row["trade_id"],
                        "year": int(row["year"]),
                        "quarter": int(row["quarter"]),
                        "location_key": location_key,
                        "feature_version": FEATURE_VERSION,
                    },
                )
            done += 1
        except Exception:
            failed += 1
        if sleep_sec > 0:
            time.sleep(float(sleep_sec))

    conn.close()
    return {"done": done, "failed": failed}


def _ensure_location_feature(conn, lat: float, lon: float, city_code: str | None) -> str:
    rounded_lat = round(float(lat), 5)
    rounded_lon = round(float(lon), 5)
    location_key = db.make_location_key(rounded_lat, rounded_lon)
    existing = db.get_location_features(conn, location_key)
    if not existing.empty:
        return location_key

    grouped = find_nearby_facility_groups(PROPERTY_FACILITY_CATEGORIES, lon=rounded_lon, lat=rounded_lat, radius_m=1000)
    facility_summary = summarize_facility_groups(grouped, PROPERTY_FACILITY_CATEGORIES)
    elevation_result = fetch_elevation_gsi(lon=rounded_lon, lat=rounded_lat)
    water_features = find_nearby_water(lon=rounded_lon, lat=rounded_lat, radius_m=1000)
    terrain_summary = summarize_terrain_features(elevation_result, water_features, radius_m=1000)
    hazard_summary = summarize_hazard_risk(lat=rounded_lat, lon=rounded_lon)
    score_summary = score_location_features({**facility_summary, **terrain_summary, **hazard_summary})

    db.upsert_location_features(
        conn,
        {
            "location_key": location_key,
            "lat": rounded_lat,
            "lon": rounded_lon,
            "city_code": city_code,
            "feature_version": FEATURE_VERSION,
            "facility_radius_m": 1000,
            "terrain_radius_m": 1000,
            **facility_summary,
            **terrain_summary,
            **hazard_summary,
            **score_summary,
        },
    )
    return location_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=["public_notice", "trade"])
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    print(run_market_feature_backfill(args.dataset, year=args.year, limit=args.limit, sleep_sec=args.sleep))


if __name__ == "__main__":
    main()
