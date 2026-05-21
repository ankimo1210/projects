"""
facility_sources.py
物件周辺の施設情報を外部ソースから取得する小さなクライアント。

OpenStreetMap Overpass API から物件周辺施設を取得する。
DB への永続化は行わず、物件分析タブのリアルタイム表示に使う。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import requests

from config import get_logger

logger = get_logger(__name__)

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT_SEC = 20


FACILITY_CATEGORY_LABELS: dict[str, str] = {
    "convenience": "コンビニ",
    "supermarket": "スーパー",
    "transit": "駅・バス停",
    "pachinko": "パチンコ",
    "food": "飲食店",
    "school": "学校",
    "medical": "病院・診療所",
    "park": "公園",
}

_CATEGORY_FILTERS: dict[str, list[tuple[str, str]]] = {
    "convenience": [("shop", "convenience")],
    "supermarket": [("shop", "supermarket")],
    "transit": [
        ("railway", "station"),
        ("highway", "bus_stop"),
        ("public_transport", "station"),
    ],
    "pachinko": [
        ("leisure", "adult_gaming_centre"),
        ("gambling", "pachinko"),
        ("amenity", "gambling"),
    ],
    "food": [
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "fast_food"),
        ("amenity", "bar"),
        ("amenity", "pub"),
    ],
    "school": [
        ("amenity", "school"),
        ("amenity", "kindergarten"),
        ("amenity", "university"),
    ],
    "medical": [
        ("amenity", "hospital"),
        ("amenity", "clinic"),
        ("amenity", "doctors"),
    ],
    "park": [
        ("leisure", "park"),
    ],
}


class FacilitySearchError(Exception):
    """施設検索が失敗したときの例外。"""


@dataclass(frozen=True)
class Facility:
    facility_id: str
    category: str
    name: str
    distance_m: float
    lon: float
    lat: float
    brand: str | None = None
    operator: str | None = None
    osm_type: str | None = None
    osm_id: int | None = None


def find_nearby_convenience(
    lon: float,
    lat: float,
    radius_m: int = 1000,
    *,
    timeout: int = OVERPASS_TIMEOUT_SEC,
) -> list[Facility]:
    """指定座標の周辺にあるコンビニを距離順で返す。"""
    return find_nearby_facilities("convenience", lon=lon, lat=lat, radius_m=radius_m, timeout=timeout)


def find_nearby_facilities(
    category: str,
    lon: float,
    lat: float,
    radius_m: int = 1000,
    *,
    timeout: int = OVERPASS_TIMEOUT_SEC,
) -> list[Facility]:
    """指定カテゴリの周辺施設を距離順で返す。"""
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    if category not in _CATEGORY_FILTERS:
        raise ValueError(f"unknown facility category: {category}")

    query = _build_category_query(category=category, lat=lat, lon=lon, radius_m=radius_m)
    try:
        resp = requests.post(
            OVERPASS_ENDPOINT,
            data={"data": query},
            timeout=timeout,
            headers={
                "User-Agent": "land-price-local-app/0.1 (facility lookup)",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise FacilitySearchError(f"Overpass API request failed: {exc}") from exc
    except ValueError as exc:
        raise FacilitySearchError(f"Overpass API returned invalid JSON: {exc}") from exc

    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise FacilitySearchError("Overpass API response has no elements list")

    facilities: list[Facility] = []
    seen: set[str] = set()
    for el in elements:
        facility = _element_to_facility(el, origin_lon=lon, origin_lat=lat, category=category)
        if facility is None or facility.facility_id in seen:
            continue
        if facility.distance_m <= radius_m:
            facilities.append(facility)
            seen.add(facility.facility_id)

    return sorted(facilities, key=lambda f: f.distance_m)


def find_nearby_facility_groups(
    categories: list[str],
    lon: float,
    lat: float,
    radius_m: int = 1000,
    *,
    timeout: int = OVERPASS_TIMEOUT_SEC,
) -> dict[str, list[Facility]]:
    """複数カテゴリの周辺施設を 1 回の Overpass クエリで取得する。"""
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    unknown = [c for c in categories if c not in _CATEGORY_FILTERS]
    if unknown:
        raise ValueError(f"unknown facility categories: {unknown}")

    query = _build_multi_category_query(categories=categories, lat=lat, lon=lon, radius_m=radius_m)
    try:
        resp = requests.post(
            OVERPASS_ENDPOINT,
            data={"data": query},
            timeout=timeout,
            headers={
                "User-Agent": "land-price-local-app/0.1 (facility lookup)",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise FacilitySearchError(f"Overpass API request failed: {exc}") from exc
    except ValueError as exc:
        raise FacilitySearchError(f"Overpass API returned invalid JSON: {exc}") from exc

    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise FacilitySearchError("Overpass API response has no elements list")

    grouped: dict[str, list[Facility]] = {category: [] for category in categories}
    seen: dict[str, set[str]] = {category: set() for category in categories}
    for el in elements:
        tags = el.get("tags") if isinstance(el.get("tags"), dict) else {}
        for category in _matching_categories(tags, categories):
            facility = _element_to_facility(el, origin_lon=lon, origin_lat=lat, category=category)
            if facility is None or facility.facility_id in seen[category]:
                continue
            if facility.distance_m <= radius_m:
                grouped[category].append(facility)
                seen[category].add(facility.facility_id)

    return {
        category: sorted(facilities, key=lambda f: f.distance_m)
        for category, facilities in grouped.items()
    }


def _build_convenience_query(lat: float, lon: float, radius_m: int) -> str:
    """Overpass QL を組み立てる。ways/relations は center を返す。"""
    return _build_category_query(category="convenience", lat=lat, lon=lon, radius_m=radius_m)


def _build_category_query(category: str, lat: float, lon: float, radius_m: int) -> str:
    """カテゴリに対応する Overpass QL を組み立てる。"""
    filters = _CATEGORY_FILTERS[category]
    statements: list[str] = []
    for key, value in filters:
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


def _build_multi_category_query(categories: list[str], lat: float, lon: float, radius_m: int) -> str:
    """複数カテゴリ分の Overpass QL をまとめて組み立てる。"""
    statements: list[str] = []
    emitted: set[tuple[str, str]] = set()
    for category in categories:
        for key, value in _CATEGORY_FILTERS[category]:
            if (key, value) in emitted:
                continue
            emitted.add((key, value))
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


def _matching_categories(tags: dict[str, Any], categories: list[str]) -> list[str]:
    matches: list[str] = []
    for category in categories:
        for key, value in _CATEGORY_FILTERS[category]:
            if str(tags.get(key, "")) == value:
                matches.append(category)
                break
    return matches


def _element_to_facility(
    el: dict[str, Any],
    *,
    origin_lon: float,
    origin_lat: float,
    category: str = "convenience",
) -> Facility | None:
    osm_type = str(el.get("type") or "")
    osm_id_raw = el.get("id")
    if not osm_type or osm_id_raw is None:
        return None

    coords = _element_coords(el)
    if coords is None:
        return None
    lat, lon = coords

    tags = el.get("tags") if isinstance(el.get("tags"), dict) else {}
    name = str(tags.get("name") or tags.get("brand") or tags.get("operator") or "名称不明")
    brand = _optional_str(tags.get("brand"))
    operator = _optional_str(tags.get("operator"))
    distance_m = _haversine_m(origin_lon, origin_lat, lon, lat)

    return Facility(
        facility_id=f"osm:{osm_type}:{osm_id_raw}",
        category=category,
        name=name,
        distance_m=distance_m,
        lon=lon,
        lat=lat,
        brand=brand,
        operator=operator,
        osm_type=osm_type,
        osm_id=int(osm_id_raw),
    )


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


def summarize_facility_groups(
    grouped: dict[str, list[Any]],
    categories: list[str],
    *,
    radii_m: tuple[int, ...] = (500, 1000),
) -> dict[str, Any]:
    """カテゴリ別の件数・最寄り距離を DB 保存向けの dict にまとめる。"""
    summary: dict[str, Any] = {}
    for category in categories:
        distances = sorted(
            d for d in (_item_distance_m(item) for item in grouped.get(category, []))
            if d is not None
        )
        for radius_m in radii_m:
            summary[f"{category}_count_{radius_m}m"] = sum(1 for d in distances if d <= radius_m)
        summary[f"{category}_nearest_m"] = distances[0] if distances else None
    return summary


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
