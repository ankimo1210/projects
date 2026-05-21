"""
hazard_sources.py
ローカル配置した公的ハザード GeoJSON を使って点の簡易判定を行う。

想定配置:
  _data/land_price/raw/hazard/flood_*.geojson
  _data/land_price/raw/hazard/landslide_*.geojson

データが存在しない場合は None を返してスキップする。
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from config import RAW_DIR, get_logger
from shapely.geometry import Point, shape

logger = get_logger(__name__)

HAZARD_DIR = RAW_DIR / "hazard"


def summarize_hazard_risk(lat: float, lon: float) -> dict[str, Any]:
    """ローカル GeoJSON に基づくハザード判定結果を返す。"""
    point = Point(float(lon), float(lat))
    flood = _match_hazard(point, "flood")
    landslide = _match_hazard(point, "landslide")

    summary_parts: list[str] = []
    if flood["flood_risk_flag"] is True:
        summary_parts.append(f"flood:{flood.get('flood_depth_rank') or 'inside'}")
    elif flood["flood_risk_flag"] is False:
        summary_parts.append("flood:none")

    if landslide["landslide_risk_flag"] is True:
        summary_parts.append("landslide:inside")
    elif landslide["landslide_risk_flag"] is False:
        summary_parts.append("landslide:none")

    return {
        **flood,
        **landslide,
        "hazard_source_summary": ", ".join(summary_parts) if summary_parts else None,
    }


def _match_hazard(point: Point, hazard_kind: str) -> dict[str, Any]:
    features = _load_hazard_features(hazard_kind)
    if features is None:
        if hazard_kind == "flood":
            return {"flood_risk_flag": None, "flood_depth_rank": None}
        return {"landslide_risk_flag": None}

    if hazard_kind == "flood":
        for geom, props in features:
            if geom.contains(point) or geom.touches(point):
                return {
                    "flood_risk_flag": True,
                    "flood_depth_rank": _extract_flood_depth_rank(props),
                }
        return {"flood_risk_flag": False, "flood_depth_rank": None}

    for geom, _props in features:
        if geom.contains(point) or geom.touches(point):
            return {"landslide_risk_flag": True}
    return {"landslide_risk_flag": False}


def _extract_flood_depth_rank(props: dict[str, Any]) -> str | None:
    candidates = [
        props.get("depth_rank"),
        props.get("浸水深"),
        props.get("最大浸水深"),
        props.get("rank"),
        props.get("level"),
    ]
    for value in candidates:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


@lru_cache(maxsize=4)
def _load_hazard_features(hazard_kind: str) -> list[tuple[Any, dict[str, Any]]] | None:
    if not HAZARD_DIR.exists():
        return None

    pattern = f"{hazard_kind}_*.geojson"
    paths = sorted(HAZARD_DIR.glob(pattern))
    if not paths:
        return None

    loaded: list[tuple[Any, dict[str, Any]]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("hazard geojson load failed: %s (%s)", path, exc)
            continue
        for feature in payload.get("features", []):
            geom_payload = feature.get("geometry")
            if not geom_payload:
                continue
            try:
                geom = shape(geom_payload)
            except Exception:
                continue
            props = feature.get("properties") or {}
            loaded.append((geom, props))
    return loaded or None
