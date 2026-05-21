"""
property_persistence.py
PropertyData ↔ listing_master DB行 の双方向変換を担う。

UI層（property_tab.py）と DB層（db.py）の橋渡し役であり、
どちらにも依存しない純粋な変換ロジックをここに集める。
"""
from __future__ import annotations

import json
from hashlib import sha1
from typing import Optional

from property_scraper import PropertyData, extract_source_property_id
from utils import safe_float, safe_int, safe_str


# --------------------------------------------------------------------------
# PropertyData → listing_master 行
# --------------------------------------------------------------------------

def property_to_listing_row(
    prop: PropertyData,
    source_url: str,
    city_code: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
    region_label: Optional[str] = None,
) -> dict:
    """PropertyData を listing_master upsert 用の dict に変換する。"""
    source = prop.platform or "unknown"
    source_property_id = extract_source_property_id(source_url)
    fallback = sha1(source_url.encode("utf-8")).hexdigest()[:16]
    listing_id = f"{source}:{source_property_id or fallback}"
    return {
        "listing_id": listing_id,
        "source": source,
        "source_property_id": source_property_id,
        "source_url": source_url,
        "region_label": region_label,
        "property_name": prop.property_name,
        "address": prop.address,
        "city_code": city_code,
        "lat": lat,
        "lon": lon,
        "asking_price_yen": prop.asking_price_yen,
        "gross_rent_monthly_yen": prop.gross_rent_monthly_yen,
        "gross_rent_annual_yen": prop.gross_rent_annual_yen,
        "gross_yield_pct": prop.gross_yield_pct,
        "build_year_month": prop.build_year_month,
        "age_years": prop.age_years,
        "structure": prop.structure,
        "property_type": prop.property_type,
        "building_area_sqm": prop.building_area_sqm,
        "land_area_sqm": prop.land_area_sqm,
        "land_rights": prop.land_rights,
        "legal_far_pct": prop.legal_far_pct,
        "bcr_pct": prop.bcr_pct,
        "num_units": prop.num_units,
        "road_frontage": prop.road_frontage,
        "nearest_station": prop.nearest_station,
        "station_walk_min": prop.station_walk_min,
        "floor_plan": prop.floor_plan,
        "num_floors": prop.num_floors,
        "land_category": prop.land_category,
        "city_planning_area": prop.city_planning_area,
        "updated_date": prop.updated_date,
        "transaction_type": prop.transaction_type,
        "listing_date": prop.listing_date,
        "platform": prop.platform,
        "extraction_confidence": prop.extraction_confidence,
        "raw_extraction_json": prop.raw_extraction,
        "llm_filled_fields_json": sorted(prop.llm_filled_fields),
    }


# --------------------------------------------------------------------------
# listing_master 行 → PropertyData
# --------------------------------------------------------------------------

def listing_row_to_property(row: dict) -> PropertyData:
    """listing_master の行 dict を PropertyData に変換する。"""
    raw: dict = {}
    raw_json = row.get("raw_extraction_json")
    if raw_json:
        try:
            raw = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except (ValueError, TypeError):
            pass

    llm_fields: set = set()
    llm_json = row.get("llm_filled_fields_json")
    if llm_json:
        try:
            llm_fields = set(json.loads(llm_json) if isinstance(llm_json, str) else llm_json)
        except (ValueError, TypeError):
            pass

    def _s(k: str) -> Optional[str]:
        v = safe_str(row.get(k), fallback="")
        return v or None

    return PropertyData(
        property_name=_s("property_name"),
        address=_s("address"),
        asking_price_yen=safe_int(row.get("asking_price_yen")),
        gross_rent_monthly_yen=safe_int(row.get("gross_rent_monthly_yen")),
        gross_rent_annual_yen=safe_int(row.get("gross_rent_annual_yen")),
        gross_yield_pct=safe_float(row.get("gross_yield_pct")),
        build_year_month=_s("build_year_month"),
        age_years=safe_int(row.get("age_years")),
        structure=_s("structure"),
        property_type=_s("property_type"),
        building_area_sqm=safe_float(row.get("building_area_sqm")),
        land_area_sqm=safe_float(row.get("land_area_sqm")),
        land_rights=_s("land_rights"),
        legal_far_pct=safe_float(row.get("legal_far_pct")),
        bcr_pct=safe_float(row.get("bcr_pct")),
        num_units=safe_int(row.get("num_units")),
        road_frontage=_s("road_frontage"),
        nearest_station=_s("nearest_station"),
        station_walk_min=safe_int(row.get("station_walk_min")),
        floor_plan=_s("floor_plan"),
        num_floors=safe_int(row.get("num_floors")),
        land_category=_s("land_category"),
        city_planning_area=_s("city_planning_area"),
        updated_date=_s("updated_date"),
        transaction_type=_s("transaction_type"),
        listing_date=_s("listing_date"),
        platform=_s("platform") or "unknown",
        extraction_confidence=_s("extraction_confidence") or "low",
        raw_extraction=raw,
        llm_filled_fields=llm_fields,
    )
