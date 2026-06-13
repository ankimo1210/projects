"""db/_market_lake.py — 市場データレイク（reinfolib タイルダンプ）の DDL と CRUD。

テーブル:
- lake_tx_points     XPT001 取引価格ポイント（タイル×年で置換）
- lake_gis_features  XKT002/026/028/029 ポリゴン（タイルで置換、生 JSON 保持）
- lake_pop_mesh      XKT013 将来推計人口（メッシュ×年 long format、タイルで置換）
- lake_tile_state    (layer, tile, window) の同期完了記録 — resume 用
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import duckdb
from config import get_logger

logger = get_logger(__name__)

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS lake_tx_points (
        tile_z INTEGER NOT NULL,
        tile_x INTEGER NOT NULL,
        tile_y INTEGER NOT NULL,
        window_key VARCHAR NOT NULL,
        lat DOUBLE,
        lon DOUBLE,
        year INTEGER,
        quarter INTEGER,
        price_yen DOUBLE,
        price_per_sqm DOUBLE,
        area_sqm DOUBLE,
        land_type VARCHAR,
        district VARCHAR,
        city_code VARCHAR,
        building_structure VARCHAR,
        floor_plan VARCHAR,
        construction_year INTEGER,
        raw_properties JSON,
        synced_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lake_gis_features (
        layer VARCHAR NOT NULL,
        tile_z INTEGER NOT NULL,
        tile_x INTEGER NOT NULL,
        tile_y INTEGER NOT NULL,
        feature_idx INTEGER NOT NULL,
        properties JSON,
        geometry JSON,
        synced_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lake_pop_mesh (
        tile_z INTEGER NOT NULL,
        tile_x INTEGER NOT NULL,
        tile_y INTEGER NOT NULL,
        mesh_idx INTEGER NOT NULL,
        lat DOUBLE,
        lon DOUBLE,
        year INTEGER NOT NULL,
        population DOUBLE,
        synced_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lake_tile_state (
        layer VARCHAR NOT NULL,
        tile_z INTEGER NOT NULL,
        tile_x INTEGER NOT NULL,
        tile_y INTEGER NOT NULL,
        window_key VARCHAR NOT NULL,
        feature_count INTEGER,
        synced_at TIMESTAMP,
        PRIMARY KEY (layer, tile_z, tile_x, tile_y, window_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_lake_tx_latlon ON lake_tx_points (lat, lon)",
    "CREATE INDEX IF NOT EXISTS idx_lake_tx_year ON lake_tx_points (year)",
    "CREATE INDEX IF NOT EXISTS idx_lake_gis_tile ON lake_gis_features (layer, tile_x, tile_y)",
    "CREATE INDEX IF NOT EXISTS idx_lake_pop_latlon ON lake_pop_mesh (lat, lon)",
]

_TX_COLS = [
    "tile_z",
    "tile_x",
    "tile_y",
    "window_key",
    "lat",
    "lon",
    "year",
    "quarter",
    "price_yen",
    "price_per_sqm",
    "area_sqm",
    "land_type",
    "district",
    "city_code",
    "building_structure",
    "floor_plan",
    "construction_year",
    "raw_properties",
    "synced_at",
]


def create_market_lake_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for ddl in _DDL:
        conn.execute(ddl)


def replace_lake_tx(
    conn: duckdb.DuckDBPyConnection,
    z: int,
    x: int,
    y: int,
    window: str,
    rows: list[dict[str, Any]],
) -> int:
    """(tile, window) 単位の置換 upsert。再同期しても重複しない。"""
    conn.execute(
        "DELETE FROM lake_tx_points WHERE tile_z=? AND tile_x=? AND tile_y=? AND window_key=?",
        (z, x, y, window),
    )
    if not rows:
        return 0
    now = datetime.now()
    values = [
        tuple(
            {**r, "tile_z": z, "tile_x": x, "tile_y": y, "window_key": window, "synced_at": now}.get(
                c
            )
            for c in _TX_COLS
        )
        for r in rows
    ]
    placeholders = ", ".join(["?"] * len(_TX_COLS))
    conn.executemany(
        f"INSERT INTO lake_tx_points ({', '.join(_TX_COLS)}) VALUES ({placeholders})",
        values,
    )
    return len(rows)


def replace_lake_gis(
    conn: duckdb.DuckDBPyConnection,
    layer: str,
    z: int,
    x: int,
    y: int,
    rows: list[dict[str, Any]],
) -> int:
    conn.execute(
        "DELETE FROM lake_gis_features WHERE layer=? AND tile_z=? AND tile_x=? AND tile_y=?",
        (layer, z, x, y),
    )
    if not rows:
        return 0
    now = datetime.now()
    conn.executemany(
        "INSERT INTO lake_gis_features"
        " (layer, tile_z, tile_x, tile_y, feature_idx, properties, geometry, synced_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(layer, z, x, y, r["feature_idx"], r["properties"], r["geometry"], now) for r in rows],
    )
    return len(rows)


def replace_lake_pop(
    conn: duckdb.DuckDBPyConnection,
    z: int,
    x: int,
    y: int,
    rows: list[dict[str, Any]],
) -> int:
    conn.execute(
        "DELETE FROM lake_pop_mesh WHERE tile_z=? AND tile_x=? AND tile_y=?",
        (z, x, y),
    )
    if not rows:
        return 0
    now = datetime.now()
    conn.executemany(
        "INSERT INTO lake_pop_mesh"
        " (tile_z, tile_x, tile_y, mesh_idx, lat, lon, year, population, synced_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(z, x, y, r["mesh_idx"], r["lat"], r["lon"], r["year"], r["population"], now) for r in rows],
    )
    return len(rows)


def mark_lake_synced(
    conn: duckdb.DuckDBPyConnection,
    layer: str,
    z: int,
    x: int,
    y: int,
    window: str,
    feature_count: int,
) -> None:
    # 規約に合わせ delete→insert（INSERT OR REPLACE は使わない）
    conn.execute(
        "DELETE FROM lake_tile_state"
        " WHERE layer=? AND tile_z=? AND tile_x=? AND tile_y=? AND window_key=?",
        (layer, z, x, y, window),
    )
    conn.execute(
        "INSERT INTO lake_tile_state"
        " (layer, tile_z, tile_x, tile_y, window_key, feature_count, synced_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (layer, z, x, y, window, feature_count, datetime.now()),
    )


def lake_synced_keys(conn: duckdb.DuckDBPyConnection) -> set[tuple]:
    """resume 用: 同期済み (layer, z, x, y, window) の集合。"""
    rows = conn.execute(
        "SELECT layer, tile_z, tile_x, tile_y, window_key FROM lake_tile_state"
    ).fetchall()
    return {tuple(r) for r in rows}


def lake_stats(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """レイクの件数サマリ（運用確認用）。"""
    out: dict[str, Any] = {}
    try:
        out["tx_points"] = conn.execute("SELECT COUNT(*) FROM lake_tx_points").fetchone()[0]
        out["tx_years"] = conn.execute(
            "SELECT MIN(year), MAX(year) FROM lake_tx_points"
        ).fetchone()
        out["gis_features"] = dict(
            conn.execute(
                "SELECT layer, COUNT(*) FROM lake_gis_features GROUP BY layer ORDER BY layer"
            ).fetchall()
        )
        out["pop_mesh_rows"] = conn.execute("SELECT COUNT(*) FROM lake_pop_mesh").fetchone()[0]
        out["tiles_synced"] = dict(
            conn.execute(
                "SELECT layer, COUNT(*) FROM lake_tile_state GROUP BY layer ORDER BY layer"
            ).fetchall()
        )
    except duckdb.CatalogException:
        out["error"] = "lake tables not created yet"
    return out
