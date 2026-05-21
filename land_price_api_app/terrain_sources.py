"""
terrain_sources.py
物件周辺の標高・河川/水辺情報を外部ソースから取得する小さなクライアント。

標高は国土地理院の標高取得プログラム、河川/水辺は OpenStreetMap Overpass API を使う。
ハザード区域判定ではなく、物件分析タブで使う簡易な地形シグナルとして扱う。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import requests

from config import get_logger
from facility_sources import OVERPASS_ENDPOINT, OVERPASS_TIMEOUT_SEC

logger = get_logger(__name__)

GSI_ELEVATION_ENDPOINT = "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php"
GSI_TIMEOUT_SEC = 10

WATER_RADIUS_M = 1000
_WATER_FILTERS: list[tuple[str, str]] = [
    ("waterway", "river"),
    ("waterway", "stream"),
    ("waterway", "canal"),
    ("natural", "water"),
    ("natural", "coastline"),
    ("water", "river"),
]


class TerrainSearchError(Exception):
    """地形・水辺情報の取得が失敗したときの例外。"""


@dataclass(frozen=True)
class ElevationResult:
    elevation_m: float | None
    source: str | None = None


@dataclass(frozen=True)
class WaterFeature:
    feature_id: str
    name: str
    type_label: str
    distance_m: float
    lon: float
    lat: float
    osm_type: str | None = None
    osm_id: int | None = None


def fetch_elevation_gsi(
    lon: float,
    lat: float,
    *,
    timeout: int = GSI_TIMEOUT_SEC,
) -> ElevationResult:
    """国土地理院の標高取得プログラムから標高を取得する。"""
    try:
        resp = requests.get(
            GSI_ELEVATION_ENDPOINT,
            params={"lon": f"{lon:.7f}", "lat": f"{lat:.7f}", "outtype": "JSON"},
            timeout=timeout,
            headers={
                "User-Agent": "land-price-local-app/0.1 (terrain lookup)",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise TerrainSearchError(f"GSI elevation request failed: {exc}") from exc
    except ValueError as exc:
        raise TerrainSearchError(f"GSI elevation API returned invalid JSON: {exc}") from exc

    return _parse_elevation_payload(payload)


def find_nearby_water(
    lon: float,
    lat: float,
    radius_m: int = WATER_RADIUS_M,
    *,
    timeout: int = OVERPASS_TIMEOUT_SEC,
) -> list[WaterFeature]:
    """指定座標の周辺にある河川・水辺を距離順で返す。"""
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")

    query = _build_water_query(lat=lat, lon=lon, radius_m=radius_m)
    try:
        resp = requests.post(
            OVERPASS_ENDPOINT,
            data={"data": query},
            timeout=timeout,
            headers={
                "User-Agent": "land-price-local-app/0.1 (terrain lookup)",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise TerrainSearchError(f"Overpass water request failed: {exc}") from exc
    except ValueError as exc:
        raise TerrainSearchError(f"Overpass water API returned invalid JSON: {exc}") from exc

    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise TerrainSearchError("Overpass water API response has no elements list")

    features: list[WaterFeature] = []
    seen: set[str] = set()
    for el in elements:
        feature = _element_to_water_feature(el, origin_lon=lon, origin_lat=lat)
        if feature is None or feature.feature_id in seen:
            continue
        if feature.distance_m <= radius_m:
            features.append(feature)
            seen.add(feature.feature_id)

    return sorted(features, key=lambda f: f.distance_m)


def elevation_band(elevation_m: float | None) -> str:
    """標高を簡易な低地シグナルに分類する。"""
    if elevation_m is None:
        return "不明"
    if elevation_m < 3:
        return "3m未満"
    if elevation_m < 10:
        return "10m未満"
    return "10m以上"


def summarize_terrain_features(
    elevation: ElevationResult | dict[str, Any] | None,
    water_features: list[Any],
    *,
    radius_m: int = WATER_RADIUS_M,
) -> dict[str, Any]:
    """標高・水辺情報を DB 保存向けの dict にまとめる。"""
    elevation_m, elevation_source = _coerce_elevation(elevation)
    water_distances = sorted(
        d for d in (_item_distance_m(item) for item in water_features)
        if d is not None
    )
    nearest_water_m = water_distances[0] if water_distances else None
    water_count = sum(1 for d in water_distances if d <= radius_m)
    return {
        "elevation_m": elevation_m,
        "elevation_band": elevation_band(elevation_m),
        "elevation_source": elevation_source,
        "nearest_water_m": nearest_water_m,
        f"water_count_{radius_m}m": water_count,
    }


def _parse_elevation_payload(payload: Any) -> ElevationResult:
    if not isinstance(payload, dict):
        raise TerrainSearchError("GSI elevation API response is not an object")

    raw_elevation = payload.get("elevation")
    elevation_m: float | None
    if raw_elevation in (None, "", "-----"):
        elevation_m = None
    else:
        try:
            elevation_m = float(raw_elevation)
        except (TypeError, ValueError) as exc:
            raise TerrainSearchError(f"invalid elevation value: {raw_elevation}") from exc

    source = _optional_str(payload.get("hsrc"))
    return ElevationResult(elevation_m=elevation_m, source=source)


def _coerce_elevation(elevation: ElevationResult | dict[str, Any] | None) -> tuple[float | None, str | None]:
    if elevation is None:
        return None, None
    if isinstance(elevation, ElevationResult):
        return elevation.elevation_m, elevation.source
    if isinstance(elevation, dict):
        value = elevation.get("elevation_m")
        source = _optional_str(elevation.get("source"))
        try:
            elevation_m = float(value) if value is not None else None
        except (TypeError, ValueError):
            elevation_m = None
        return elevation_m, source
    return None, None


def _build_water_query(lat: float, lon: float, radius_m: int) -> str:
    statements: list[str] = []
    for key, value in _WATER_FILTERS:
        selector = f'["{key}"="{value}"]'
        statements.extend(
            [
                f"  node(around:{radius_m},{lat:.7f},{lon:.7f}){selector};",
                f"  way(around:{radius_m},{lat:.7f},{lon:.7f}){selector};",
                f"  relation(around:{radius_m},{lat:.7f},{lon:.7f}){selector};",
            ]
        )
    body = "\n".join(statements)
    return f"""
[out:json][timeout:{OVERPASS_TIMEOUT_SEC}];
(
{body}
);
out center tags;
"""


def _element_to_water_feature(
    el: dict[str, Any],
    *,
    origin_lon: float,
    origin_lat: float,
) -> WaterFeature | None:
    osm_type = str(el.get("type") or "")
    osm_id_raw = el.get("id")
    if not osm_type or osm_id_raw is None:
        return None

    coords = _element_coords(el)
    if coords is None:
        return None
    lat, lon = coords

    tags = el.get("tags") if isinstance(el.get("tags"), dict) else {}
    type_label = _water_type_label(tags)
    name = str(tags.get("name") or type_label or "名称不明")
    distance_m = _haversine_m(origin_lon, origin_lat, lon, lat)

    return WaterFeature(
        feature_id=f"osm:{osm_type}:{osm_id_raw}",
        name=name,
        type_label=type_label,
        distance_m=distance_m,
        lon=lon,
        lat=lat,
        osm_type=osm_type,
        osm_id=int(osm_id_raw),
    )


def _water_type_label(tags: dict[str, Any]) -> str:
    waterway = str(tags.get("waterway") or "")
    natural = str(tags.get("natural") or "")
    water = str(tags.get("water") or "")
    if waterway == "river" or water == "river":
        return "河川"
    if waterway == "stream":
        return "水路・小川"
    if waterway == "canal":
        return "運河・水路"
    if natural == "coastline":
        return "海岸線"
    if natural == "water":
        return "池・水面"
    return "水辺"


def _element_coords(el: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])
    center = el.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _item_distance_m(item: Any) -> float | None:
    if isinstance(item, dict):
        value = item.get("distance_m")
    else:
        value = getattr(item, "distance_m", None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
