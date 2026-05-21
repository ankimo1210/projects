"""
recompute_public_notice_features.py
公示地価地点に施設・地形特徴量をバッチ付与する。

グリッド方式: lat/lon を精度3桁（≈100m）で丸めたグリッドキー単位で
Overpass API を1回呼び出し、同一グリッド内の全地点に特徴量を割り当てる。
これにより API 呼び出し数を大幅に削減する。

使い方:
    python recompute_public_notice_features.py --pref 13 --year 2026
    python recompute_public_notice_features.py --pref 13 --limit 50 --sleep 1.5
    python recompute_public_notice_features.py --year 2026 --sleep 1.5

注意: DuckDB は同時書き込みロックのため、Streamlit アプリを停止してから実行すること。
      ./stop_local.sh でアプリを停止後に実行し、終了後に ./run_local.sh で再起動する。

進捗: location_features に fetched_at が保存されるため、再実行時は
      --stale-days で指定した日数以内のキャッシュをスキップする。
      東京都 全地点（約300〜400グリッド）を処理する場合の目安: 約10〜15分（sleep=1.5s）。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import db
from config import get_logger
from facility_sources import (
    FacilitySearchError,
    find_nearby_facility_groups,
    summarize_facility_groups,
)
from terrain_sources import (
    TerrainSearchError,
    fetch_elevation_gsi,
    find_nearby_water,
    summarize_terrain_features,
)
from terrain_sources import elevation_band as _elevation_band

logger = get_logger(__name__)

# 物件分析タブと同じカテゴリセット
_FACILITY_CATEGORIES = [
    "convenience_store",
    "supermarket",
    "station",
    "bus_stop",
    "pachinko",
    "restaurant",
    "school",
    "hospital",
    "park",
]

# Overpass クエリ半径
_RADIUS_M = 1000

# グリッドキー精度（3桁 ≈ 111m × cos(lat) ≈ 80〜100m）
_GRID_PRECISION = 3


def _make_grid_key(lat: float, lon: float) -> str:
    return f"{round(lat, _GRID_PRECISION):.{_GRID_PRECISION}f},{round(lon, _GRID_PRECISION):.{_GRID_PRECISION}f}"


def _fetch_location_features(lat: float, lon: float) -> dict:
    """Overpass + GSI で施設・地形情報を取得して dict にまとめる。"""
    grouped: dict = {}
    elevation_result: dict = {}
    water_features: list[dict] = []

    try:
        raw_grouped = find_nearby_facility_groups(_FACILITY_CATEGORIES, lon=lon, lat=lat, radius_m=_RADIUS_M)
        grouped = {
            cat: [
                {
                    "category": f.category,
                    "name": f.name,
                    "distance_m": f.distance_m,
                    "brand": f.brand,
                    "operator": f.operator,
                    "osm_type": f.osm_type,
                    "osm_id": f.osm_id,
                    "lat": f.lat,
                    "lon": f.lon,
                }
                for f in facilities
            ]
            for cat, facilities in raw_grouped.items()
        }
    except FacilitySearchError as exc:
        logger.warning("施設取得エラー (%.5f,%.5f): %s", lat, lon, exc)

    try:
        elev = fetch_elevation_gsi(lon=lon, lat=lat)
        elevation_result = {"elevation_m": elev.elevation_m, "source": elev.source}
    except TerrainSearchError as exc:
        logger.warning("標高取得エラー (%.5f,%.5f): %s", lat, lon, exc)

    try:
        raw_water = find_nearby_water(lon=lon, lat=lat, radius_m=_RADIUS_M)
        water_features = [
            {
                "name": f.name,
                "type_label": f.type_label,
                "distance_m": f.distance_m,
                "osm_type": f.osm_type,
                "osm_id": f.osm_id,
                "lat": f.lat,
                "lon": f.lon,
            }
            for f in raw_water
        ]
    except TerrainSearchError as exc:
        logger.warning("水辺取得エラー (%.5f,%.5f): %s", lat, lon, exc)

    facility_summary = summarize_facility_groups(grouped, _FACILITY_CATEGORIES)
    terrain_summary = summarize_terrain_features(elevation_result, water_features, radius_m=_RADIUS_M)

    elevation_m = elevation_result.get("elevation_m")

    return {
        "facility_radius_m": _RADIUS_M,
        "terrain_radius_m": _RADIUS_M,
        "elevation_m": elevation_m,
        "elevation_band": _elevation_band(elevation_m),
        "elevation_source": elevation_result.get("source"),
        "nearest_water_m": terrain_summary.get("nearest_water_m"),
        "water_count_1000m": terrain_summary.get("water_count_1000m"),
        **{k: v for k, v in facility_summary.items()},
        "_grouped": grouped,
        "_water": water_features,
    }


def run(
    *,
    pref_code: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    stale_days: int = 30,
    sleep_sec: float = 1.0,
    dry_run: bool = False,
) -> dict[str, int]:
    conn = db.get_connection()
    db.create_tables_if_needed(conn)

    # 対象地点を取得
    conditions = ["lat IS NOT NULL", "lon IS NOT NULL"]
    params = []
    if pref_code:
        conditions.append("prefecture_code = ?")
        params.append(pref_code)
    if year:
        conditions.append("year = ?")
        params.append(year)
    where = " AND ".join(conditions)

    sql = f"SELECT DISTINCT point_id, lat, lon, year FROM land_prices_public_notice WHERE {where} ORDER BY point_id"
    if limit:
        sql += f" LIMIT {limit}"

    points = conn.execute(sql, params).fetchdf()
    logger.info("対象地点数: %d", len(points))

    if points.empty:
        logger.info("対象地点なし。終了。")
        return {"done": 0, "skipped": 0, "failed": 0}

    # グリッドキーでグループ化
    points["grid_key"] = points.apply(lambda r: _make_grid_key(r["lat"], r["lon"]), axis=1)
    grid_groups = points.groupby("grid_key")
    logger.info("ユニークグリッド数: %d", len(grid_groups))

    done = 0
    skipped = 0
    failed = 0

    for grid_key, group in grid_groups:
        # グリッド中心座標（最初の地点を代表）
        rep = group.iloc[0]
        grid_lat = float(rep["lat"])
        grid_lon = float(rep["lon"])
        grid_location_key = db.make_location_key(grid_lat, grid_lon, precision=_GRID_PRECISION)

        # DuckDB キャッシュチェック（stale_days 以内ならスキップ）
        cached = db.get_cached_location_features(conn, grid_location_key, max_age_days=stale_days)
        if cached is not None:
            skipped += len(group)
            # リンクテーブルだけ更新（新しい地点が増えた場合）
            if not dry_run:
                _upsert_point_links(conn, group, grid_location_key)
            continue

        if dry_run:
            logger.info("[dry-run] grid %s (%d points)", grid_key, len(group))
            done += len(group)
            continue

        try:
            features = _fetch_location_features(grid_lat, grid_lon)
        except Exception as exc:
            logger.error("特徴量取得失敗 grid=%s: %s", grid_key, exc)
            failed += len(group)
            if sleep_sec > 0:
                time.sleep(sleep_sec)
            continue

        grouped = features.pop("_grouped", {})
        water = features.pop("_water", [])

        location_row = {
            "location_key": grid_location_key,
            "lat": grid_lat,
            "lon": grid_lon,
            **features,
        }

        try:
            db.upsert_location_features(conn, location_row)
            all_pois = [poi | {"category": cat} for cat, pois in grouped.items() for poi in pois]
            db.upsert_facility_pois(conn, grid_location_key, all_pois)
            db.upsert_water_features(conn, grid_location_key, water)
            _upsert_point_links(conn, group, grid_location_key)
            done += len(group)
            logger.info(
                "grid %s: %d points saved (%.5f,%.5f)",
                grid_key, len(group), grid_lat, grid_lon,
            )
        except Exception as exc:
            logger.error("DB保存失敗 grid=%s: %s", grid_key, exc)
            failed += len(group)

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    result = {"done": done, "skipped": skipped, "failed": failed}
    logger.info("完了: %s", result)
    return result


def _upsert_point_links(conn, group: pd.DataFrame, location_key: str) -> None:
    """public_notice_location_features にリンクレコードを upsert する。"""
    for _, row in group.iterrows():
        conn.execute(
            """
            INSERT OR REPLACE INTO public_notice_location_features
                (point_id, year, location_key, computed_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [str(row["point_id"]), int(row["year"]), location_key],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="公示地価地点に施設・地形特徴量をバッチ付与する")
    parser.add_argument("--pref", help="都道府県コード (例: 13)")
    parser.add_argument("--year", type=int, help="対象年度 (例: 2026)")
    parser.add_argument("--limit", type=int, help="最大処理地点数（テスト用）")
    parser.add_argument("--stale-days", type=int, default=30, help="キャッシュ有効日数 (default: 30)")
    parser.add_argument("--sleep", type=float, default=1.0, help="API呼び出し間の待機秒数 (default: 1.0)")
    parser.add_argument("--dry-run", action="store_true", help="API呼び出しをスキップして件数だけ確認")
    args = parser.parse_args()

    result = run(
        pref_code=args.pref,
        year=args.year,
        limit=args.limit,
        stale_days=args.stale_days,
        sleep_sec=args.sleep,
        dry_run=args.dry_run,
    )
    print(f"done={result['done']}  skipped={result['skipped']}  failed={result['failed']}")


if __name__ == "__main__":
    main()
