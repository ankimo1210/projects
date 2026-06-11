"""market_lake.py — reinfolib タイル API の地域一括ダンプ（市場データレイク）。

re_invest_os の市場エビデンス分析に必要なレイヤーをローカル DuckDB へ同期する:

- XPT001 不動産取引価格ポイント（年ウィンドウ、座標つき取引事例）
- XKT002 用途地域 / XKT026 洪水 / XKT028 津波 / XKT029 土砂災害（ポリゴン）
- XKT013 将来推計人口 250m メッシュ（PT00_YYYY 総人口のみ採用）

設計:
- 取得は api_client.fetch_json（リトライ/バックオフ/gzip 対応済み）。
- フェッチのみ ThreadPoolExecutor で並列化し、DuckDB 書き込みは
  メインスレッドで行う（DuckDB 接続はスレッド間共有しない）。
- (layer, tile, window) 単位で lake_tile_state に完了を記録し、
  再実行時は未完了分だけを取得する（resume）。
- 表示文字列のパース（"65,000万円" 等）は re_invest_os
  apps/api/src/api/services/market/points.py と同一仕様の移植。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from itertools import islice

from api_client import fetch_json
from config import REINFOLIB_BASE_URL, get_logger
from tiles import PREFECTURE_BBOX, lonlat_to_tile_indices

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 対象エリア定義 (lon_min, lon_max, lat_min, lat_max)
# ──────────────────────────────────────────────────────────────────────────────

_KANTO_PREFS = ["08", "09", "10", "11", "12", "13", "14"]
_KANSAI_PREFS = ["25", "26", "27", "28", "29", "30"]

# 関東・関西の都道府県域外にある政令指定都市（市域をおおむね覆う bbox）
_CITY_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "sapporo": (141.10, 141.60, 42.90, 43.20),
    "sendai": (140.60, 141.10, 38.15, 38.45),
    "niigata": (138.90, 139.30, 37.70, 38.05),
    "shizuoka": (138.20, 138.65, 34.85, 35.20),
    "hamamatsu": (137.50, 137.95, 34.60, 34.95),
    "nagoya": (136.70, 137.10, 35.00, 35.35),
    "okayama": (133.70, 134.10, 34.50, 34.80),
    "hiroshima": (132.20, 132.70, 34.30, 34.60),
    "fukuoka_kitakyushu": (130.20, 131.05, 33.45, 34.05),
    "kumamoto": (130.55, 130.90, 32.70, 32.95),
}
_OKINAWA_MAIN = (127.63, 128.35, 26.05, 26.90)


def area_bboxes(groups: Iterable[str]) -> dict[str, tuple[float, float, float, float]]:
    """エリアグループ名 → {area_key: bbox}。未知のグループは ValueError。"""
    out: dict[str, tuple[float, float, float, float]] = {}
    for g in groups:
        if g == "kanto":
            for p in _KANTO_PREFS:
                out[f"pref{p}"] = PREFECTURE_BBOX[p]
        elif g == "kansai":
            for p in _KANSAI_PREFS:
                out[f"pref{p}"] = PREFECTURE_BBOX[p]
        elif g == "cities":
            out.update(_CITY_BBOXES)
        elif g == "okinawa":
            out["okinawa_main"] = _OKINAWA_MAIN
        else:
            raise ValueError(f"unknown area group: {g} (kanto/kansai/cities/okinawa)")
    return out


def target_tiles(groups: Iterable[str], z: int) -> list[tuple[int, int]]:
    """対象エリア群をカバーするタイル (x, y) の集合（エリア重複は dedup）。"""
    tiles: set[tuple[int, int]] = set()
    for lon_min, lon_max, lat_min, lat_max in area_bboxes(groups).values():
        x_min, y_max = lonlat_to_tile_indices(lon_min, lat_min, z)
        x_max, y_min = lonlat_to_tile_indices(lon_max, lat_max, z)
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tiles.add((x, y))
    return sorted(tiles)


# ──────────────────────────────────────────────────────────────────────────────
# 表示文字列パース（re_invest_os points.py と同一仕様）
# ──────────────────────────────────────────────────────────────────────────────

_NUM = r"\d[\d,]*(?:\.\d+)?"
_OKU_RE = re.compile(rf"({_NUM})億")
_MAN_RE = re.compile(rf"({_NUM})万")
_NUM_RE = re.compile(_NUM)
_YQ_RE = re.compile(r"(\d{4})年第(\d)四半期")
_YEAR_RE = re.compile(r"(\d{4})年")


def parse_price_ja(s: str | None) -> float | None:
    """"65,000万円"→6.5e8, "1億2,000万円"→1.2e8, "710,000(円/㎡)"→710000。"""
    if not s or not s.strip():
        return None
    s = s.strip()
    total = 0.0
    has_unit = False
    m = _OKU_RE.search(s)
    if m:
        total += float(m.group(1).replace(",", "")) * 1e8
        has_unit = True
    m = _MAN_RE.search(s)
    if m:
        total += float(m.group(1).replace(",", "")) * 1e4
        has_unit = True
    if not has_unit:
        m = _NUM_RE.search(s)
        if not m:
            return None
        total = float(m.group(0).replace(",", ""))
    return total if total > 0 else None


def parse_area_ja(s: str | None) -> float | None:
    if not s or not s.strip():
        return None
    m = _NUM_RE.search(s)
    if not m:
        return None
    v = float(m.group(0).replace(",", ""))
    return v if v > 0 else None


def parse_year_quarter(s: str | None) -> tuple[int | None, int | None]:
    if not s:
        return None, None
    m = _YQ_RE.search(s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _YEAR_RE.search(s)
    if m:
        return int(m.group(1)), None
    return None, None


def _feature_latlon(feature: dict) -> tuple[float, float] | None:
    geom = feature.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    try:
        if gtype == "Point":
            return float(coords[1]), float(coords[0])
        if gtype == "Polygon":
            ring = coords[0]
        elif gtype == "MultiPolygon":
            ring = coords[0][0]
        else:
            return None
        lats = [float(p[1]) for p in ring]
        lons = [float(p[0]) for p in ring]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        return None


# ──────────────────────────────────────────────────────────────────────────────
# レイヤー定義と正規化
# ──────────────────────────────────────────────────────────────────────────────

GIS_LAYERS = ("xkt002", "xkt026", "xkt028", "xkt029")
ALL_LAYERS = ("xpt001", "xkt013", *GIS_LAYERS)

# レイヤー別の最小ズーム（API 制約・実測）。
# XKT026 洪水 / XKT028 津波は z=13 が 400 Bad Request になるため z=14 で掃引する。
LAYER_MIN_Z: dict[str, int] = {"xkt026": 14, "xkt028": 14}


def layer_zoom(layer: str, z: int) -> int:
    return max(z, LAYER_MIN_Z.get(layer, z))


def fetch_tile(layer: str, z: int, x: int, y: int, window: str) -> dict:
    """1 タイル分の GeoJSON を取得する。window は xpt001 のみ年 ("2024")。"""
    params: dict = {"response_format": "geojson", "z": z, "x": x, "y": y}
    if layer == "xpt001":
        params["from"] = f"{window}1"
        params["to"] = f"{window}4"
    url = f"{REINFOLIB_BASE_URL}/{layer.upper()}"
    data = fetch_json(url, params=params)
    if not isinstance(data, dict):
        return {"type": "FeatureCollection", "features": []}
    data.setdefault("features", [])
    return data


def normalize_tx_features(features: list[dict]) -> list[dict]:
    """XPT001 features → lake_tx_points 行。"""
    rows: list[dict] = []
    for f in features:
        latlon = _feature_latlon(f)
        if latlon is None:
            continue
        p = f.get("properties", {}) or {}
        price = parse_price_ja(p.get("u_transaction_price_total_ja"))
        per_sqm = parse_price_ja(p.get("u_transaction_price_unit_price_square_meter_ja"))
        area = parse_area_ja(p.get("u_area_ja"))
        if per_sqm is None and price is not None and area is not None:
            per_sqm = price / area
        year, quarter = parse_year_quarter(p.get("point_in_time_name_ja"))
        cyear, _ = parse_year_quarter(p.get("u_construction_year_ja"))
        rows.append(
            {
                "lat": latlon[0],
                "lon": latlon[1],
                "year": year,
                "quarter": quarter,
                "price_yen": price,
                "price_per_sqm": per_sqm,
                "area_sqm": area,
                "land_type": p.get("land_type_name_ja") or None,
                "district": p.get("district_name_ja") or None,
                "city_code": str(p["city_code"]) if p.get("city_code") else None,
                "building_structure": p.get("building_structure_name_ja") or None,
                "floor_plan": p.get("floor_plan_name_ja") or None,
                "construction_year": cyear,
                "raw_properties": json.dumps(p, ensure_ascii=False),
            }
        )
    return rows


_PT00_RE = re.compile(r"^PT00_(\d{4})$")


def normalize_pop_features(features: list[dict]) -> list[dict]:
    """XKT013 features → lake_pop_mesh 行（メッシュ × 年の long format）。"""
    rows: list[dict] = []
    for idx, f in enumerate(features):
        latlon = _feature_latlon(f)
        if latlon is None:
            continue
        p = f.get("properties", {}) or {}
        for k, v in p.items():
            m = _PT00_RE.match(str(k))
            if not m:
                continue
            try:
                pop = float(v)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "mesh_idx": idx,
                    "lat": latlon[0],
                    "lon": latlon[1],
                    "year": int(m.group(1)),
                    "population": pop,
                }
            )
    return rows


def normalize_gis_features(features: list[dict]) -> list[dict]:
    """XKT002/026/028/029 features → lake_gis_features 行（生 JSON 保持）。"""
    rows: list[dict] = []
    for idx, f in enumerate(features):
        geom = f.get("geometry")
        if not geom:
            continue
        rows.append(
            {
                "feature_idx": idx,
                "properties": json.dumps(f.get("properties", {}) or {}, ensure_ascii=False),
                "geometry": json.dumps(geom, ensure_ascii=False),
            }
        )
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# 同期オーケストレータ
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WorkItem:
    layer: str
    z: int
    x: int
    y: int
    window: str  # xpt001: "2024" / その他: "-"


def build_worklist(
    layers: Iterable[str],
    groups: Iterable[str],
    years: Iterable[int],
    z: int,
) -> list[WorkItem]:
    tiles_by_z: dict[int, list[tuple[int, int]]] = {}

    def _tiles(zoom: int) -> list[tuple[int, int]]:
        if zoom not in tiles_by_z:
            tiles_by_z[zoom] = target_tiles(groups, zoom)
        return tiles_by_z[zoom]

    items: list[WorkItem] = []
    for layer in layers:
        lz = layer_zoom(layer, z)
        tiles = _tiles(lz)
        if layer == "xpt001":
            for year in years:
                items.extend(WorkItem(layer, lz, x, y, str(year)) for x, y in tiles)
        else:
            items.extend(WorkItem(layer, lz, x, y, "-") for x, y in tiles)
    return items


def run_sync(
    conn,
    layers: Iterable[str],
    groups: Iterable[str],
    years: Iterable[int],
    *,
    z: int = 13,
    workers: int = 6,
    resume: bool = True,
    limit_tiles: int | None = None,
    progress_every: int = 200,
) -> dict:
    """同期を実行し、サマリ dict を返す。conn はメインスレッド専有。"""
    import db

    db.create_market_lake_tables(conn)

    work = build_worklist(layers, groups, years, z)
    if resume:
        done = db.lake_synced_keys(conn)
        before = len(work)
        work = [w for w in work if (w.layer, w.z, w.x, w.y, w.window) not in done]
        logger.info("resume: %d / %d 件をスキップ", before - len(work), before)
    if limit_tiles is not None:
        work = work[:limit_tiles]

    total = len(work)
    logger.info(
        "同期開始: %d リクエスト (layers=%s, groups=%s, z=%d, workers=%d)",
        total,
        ",".join(layers),
        ",".join(groups),
        z,
        workers,
    )

    stats = {"requested": total, "ok": 0, "failed": 0, "features": 0, "started_at": datetime.now().isoformat()}

    def _fetch(w: WorkItem):
        try:
            data = fetch_tile(w.layer, w.z, w.x, w.y, w.window)
            return w, data.get("features", []), None
        except Exception as e:  # 失敗タイルは記録だけして続行（resume で再試行可能）
            return w, None, e

    # フェッチはウィンドウ投入で in-flight を制限する。
    # 一括 submit すると futures リストが完了済み結果（GeoJSON）への参照を保持し続け、
    # 全レスポンスがメモリに累積する（実測: 136k 件で RSS 47GB → OOM kill rc=137）。
    work_iter = iter(work)
    window = max(workers * 4, 8)
    processed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        in_flight = {ex.submit(_fetch, w) for w in islice(work_iter, window)}
        while in_flight:
            done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
            for fut in done:
                w, features, err = fut.result()
                processed += 1
                if err is not None:
                    stats["failed"] += 1
                    logger.warning(
                        "失敗 %s z%d/%d/%d w=%s: %s", w.layer, w.z, w.x, w.y, w.window, err
                    )
                else:
                    n = len(features)
                    if w.layer == "xpt001":
                        rows = normalize_tx_features(features)
                        db.replace_lake_tx(conn, w.z, w.x, w.y, w.window, rows)
                    elif w.layer == "xkt013":
                        rows = normalize_pop_features(features)
                        db.replace_lake_pop(conn, w.z, w.x, w.y, rows)
                    else:
                        rows = normalize_gis_features(features)
                        db.replace_lake_gis(conn, w.layer, w.z, w.x, w.y, rows)
                    db.mark_lake_synced(conn, w.layer, w.z, w.x, w.y, w.window, n)
                    stats["ok"] += 1
                    stats["features"] += n
                if processed % progress_every == 0 or processed == total:
                    logger.info(
                        "進捗 %d/%d (ok=%d failed=%d features=%d)",
                        processed,
                        total,
                        stats["ok"],
                        stats["failed"],
                        stats["features"],
                    )
            # 消費した分だけ補充（in-flight ≤ window を維持）
            in_flight |= {ex.submit(_fetch, w) for w in islice(work_iter, len(done))}

    stats["finished_at"] = datetime.now().isoformat()
    logger.info("同期完了: %s", stats)
    return stats
