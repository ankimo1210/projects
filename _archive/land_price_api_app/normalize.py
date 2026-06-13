"""
normalize.py
XPT002 の GeoJSON Feature を分析用 DataFrame に変換する。

不動産情報ライブラリ XPT002 は GeoJSON FeatureCollection を返す。
各 Feature の properties はAPI仕様に応じた日本語キー・英語キー混在の場合がある。
ここでは複数の候補キーを試して snake_case カラムにマッピングする。
"""

import json
from typing import Any

import pandas as pd
from config import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# フィールドマッピング定義
# candidates は優先順位順。最初に見つかった値を使う。
# --------------------------------------------------------------------------

# 実際の XPT002 API レスポンスプロパティ名（2025年3月時点で確認済み）
_FIELD_CANDIDATES: dict[str, list[str]] = {
    # 標準地番号（例: "札幌中央-21"）
    "standard_land_number": [
        "standard_lot_number_ja",
        "place_name_ja",
    ],
    # 都道府県
    "prefecture_code": ["prefecture_code"],
    "prefecture_name": ["prefecture_name_ja"],
    # 市区町村（ward_town_village_name_ja = 区町村, city_county_name_ja = 市郡）
    # 政令市: city_county_name_ja="札幌市", ward_town_village_name_ja="中央区"
    # 東京23区: city_county_name_ja="", ward_town_village_name_ja="千代田区"
    "city_code": ["city_code"],
    "city_name": ["ward_town_village_name_ja", "city_county_name_ja"],
    "district_name": ["city_county_name_ja"],
    # 所在地
    "location_text": ["location"],
    # 前年価格（数値: 円/m²）
    "last_year_price_yen_per_sqm": ["last_years_price"],
    # 変動率（数値: %）
    "yoy_change_pct": ["year_on_year_change_rate"],
    # 利用現況
    "usage_status_name": ["usage_status_name_ja"],
    # 建物構造
    "building_structure_name": ["building_structure_name_ja"],
    # 建物用途（利用現況より上位）
    "current_use_name": ["current_usage_status_of_surrounding_land_name_ja"],
    # 前面道路
    "front_road_name": ["front_road_name_ja"],
    # 用途区分（住宅地 / 商業地 / 工業地 など）
    "use_category_code": ["land_price_type"],  # 0=公示, 1=調査
    "use_category_name": ["use_category_name_ja"],
    # 都市計画用途地域
    "zoning_name": ["regulations_use_category_name_ja", "area_division_name_ja"],
    # 最寄り駅
    "nearest_station_name": ["nearest_station_name_ja"],
    "road_distance_to_station": ["u_road_distance_to_nearest_station_name_ja"],
    # 前面道路情報
    "front_road_condition": ["front_road_condition"],
}

# 数値として扱うカラム
_NUMERIC_COLUMNS = [
    "price_yen_per_sqm",
    "last_year_price_yen_per_sqm",
    "yoy_change_pct",
    "area_sqm",
    "building_coverage_ratio",
    "floor_area_ratio",
    "lon",
    "lat",
]


# --------------------------------------------------------------------------
# ユーティリティ
# --------------------------------------------------------------------------


def _get_field(props: dict[str, Any], candidates: list[str]) -> Any:
    """候補キーを順に試して最初に見つかった値を返す。なければ None。"""
    for key in candidates:
        if key in props:
            val = props[key]
            if val is not None and val != "":
                return val
    return None


def _extract_lonlat(feature: dict[str, Any]) -> tuple[float | None, float | None]:
    """GeoJSON Feature の geometry から (lon, lat) を抽出する。"""
    try:
        geom = feature.get("geometry", {})
        if geom and geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                return float(coords[0]), float(coords[1])
    except (TypeError, ValueError, KeyError):
        pass
    return None, None


# --------------------------------------------------------------------------
# メイン変換
# --------------------------------------------------------------------------


def feature_to_record(
    feature: dict[str, Any],
    year: int,
    price_classification: int,
) -> dict[str, Any]:
    """
    GeoJSON Feature 1 件を分析用 dict に変換する。

    Parameters
    ----------
    feature : dict
        GeoJSON Feature オブジェクト。
    year : int
        同期対象年度。
    price_classification : int
        0=地価公示, 1=地価調査。

    Returns
    -------
    dict
        snake_case カラム名の辞書。
    """
    props: dict[str, Any] = feature.get("properties") or {}
    lon, lat = _extract_lonlat(feature)

    # API 固有の point_id フィールドを優先
    raw_pid = props.get("point_id")
    if raw_pid is not None:
        point_id = str(raw_pid)
    elif lon is not None and lat is not None:
        point_id = f"coord_{lon:.6f}_{lat:.6f}"
    else:
        point_id = None

    # 現在価格: 数値フィールドがなく文字列 "331,000(円/㎡)" から抽出する
    price_yen_per_sqm = _parse_price_string(props.get("u_current_years_price_ja", ""))

    # 地積: 文字列 "1,696(㎡)" から数値抽出
    area_sqm = _parse_area_string(props.get("u_cadastral_ja", ""))

    # 建ぺい率・容積率: "80(%)" → 80.0
    bcr = _parse_ratio_string(props.get("u_regulations_building_coverage_ratio_ja", ""))
    far = _parse_ratio_string(props.get("u_regulations_floor_area_ratio_ja", ""))

    record: dict[str, Any] = {
        "point_id": point_id,
        "year": year,
        "price_classification": price_classification,
        "survey_source": "地価公示" if price_classification == 0 else "地価調査",
        "lon": lon,
        "lat": lat,
        "price_yen_per_sqm": price_yen_per_sqm,
        "area_sqm": area_sqm,
        "building_coverage_ratio": bcr,
        "floor_area_ratio": far,
        "raw_properties": json.dumps(props, ensure_ascii=False),
    }

    # フィールドマッピングを適用（既にセットした key は上書きしない）
    for col, candidates in _FIELD_CANDIDATES.items():
        if col not in record:
            record[col] = _get_field(props, candidates)

    # standard_land_number を point_id 候補から取る
    record["standard_land_number"] = _get_field(props, _FIELD_CANDIDATES["standard_land_number"])

    return record


def _parse_price_string(s: Any) -> float | None:
    """
    "331,000(円/㎡)" や 331000 などから数値を抽出する。
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    # 数字とカンマのみを残して変換
    import re

    m = re.search(r"[\d,]+", str(s))
    if m:
        try:
            return float(m.group().replace(",", ""))
        except ValueError:
            pass
    return None


def _parse_area_string(s: Any) -> float | None:
    """
    "1,696(㎡)" から数値を抽出する。
    """
    return _parse_price_string(s)


def _parse_ratio_string(s: Any) -> float | None:
    """
    "80(%)" から 80.0 を返す。
    """
    return _parse_price_string(s)


def normalize_features_to_dataframe(
    features: list[dict[str, Any]],
    year: int,
    price_classification: int = 0,
) -> pd.DataFrame:
    """
    GeoJSON Feature リストを正規化した DataFrame に変換する。

    Parameters
    ----------
    features : list[dict]
        GeoJSON Feature オブジェクトのリスト。
    year : int
        調査年度。
    price_classification : int
        0=地価公示, 1=地価調査。

    Returns
    -------
    pd.DataFrame
        正規化済み DataFrame。point_id が None の行は除外する。
    """
    if not features:
        return _empty_dataframe()

    records = [feature_to_record(f, year, price_classification) for f in features]
    df = pd.DataFrame(records)

    # point_id が空の行を除外
    df = df[df["point_id"].notna() & (df["point_id"] != "")]
    if df.empty:
        return _empty_dataframe()

    df = clean_numeric_columns(df)
    return df


def clean_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    数値カラムを適切な型に変換する。変換不可能な値は NaN にする。

    Parameters
    ----------
    df : pd.DataFrame
        入力 DataFrame（in-place 変更しない）。

    Returns
    -------
    pd.DataFrame
        数値変換済み DataFrame。
    """
    df = df.copy()
    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # yoy_change_pct: "%" 文字が含まれていることがある
    if "yoy_change_pct" in df.columns:
        df["yoy_change_pct"] = (
            df["yoy_change_pct"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    return df


# --------------------------------------------------------------------------
# XIT001 フィールドマッピング
# --------------------------------------------------------------------------

_XIT001_FIELD_CANDIDATES: dict[str, list[str]] = {
    "trade_type": ["Type", "取引の種類"],
    "prefecture_name": ["Prefecture", "都道府県名"],
    "city_code": ["MunicipalityCode", "市区町村コード"],
    "city_name": ["Municipality", "市区町村名"],
    "district_name": ["DistrictName", "地区名"],
    "trade_price_total": ["TradePrice", "取引価格（総額）"],
    "trade_price_per_sqm": ["UnitPrice", "PricePerUnit", "取引価格（㎡単価）"],
    "area_sqm": ["Area", "面積（㎡）"],
    "floor_plan": ["FloorPlan", "間取り"],
    "land_shape": ["LandShape", "土地の形状"],
    "frontage": ["Frontage", "間口"],
    "total_floor_area_sqm": ["TotalFloorArea", "延床面積（㎡）"],
    "build_year_str": ["BuildingYear", "建築年"],
    "building_structure": ["Structure", "建物の構造"],
    "use_name": ["Use", "用途"],
    "purpose_name": ["Purpose", "今後の利用目的"],
    "front_road_direction": ["Direction", "前面道路：方位"],
    "front_road_type": ["Classification", "前面道路：種類"],
    "front_road_breadth": ["Breadth", "前面道路：幅員（m）"],
    "city_planning": ["CityPlanning", "都市計画"],
    "coverage_ratio": ["CoverageRatio", "建ぺい率（%）"],
    "floor_area_ratio": ["FloorAreaRatio", "容積率（%）"],
    "period_str": ["Period", "取引時点"],
    "renovation": ["Renovation", "改装"],
    "remarks": ["Remarks", "取引の事情等"],
}

_XIT001_NUMERIC_COLUMNS = [
    "trade_price_total",
    "trade_price_per_sqm",
    "area_sqm",
    "frontage",
    "total_floor_area_sqm",
    "front_road_breadth",
    "coverage_ratio",
    "floor_area_ratio",
    "lon",
    "lat",
]


def normalize_xit001_features_to_dataframe(
    records: list[dict[str, Any]],
    year: int,
    quarter: int,
) -> pd.DataFrame:
    """
    XIT001 レコードリスト（{"status":"OK","data":[...]} の data 部分）を
    正規化した DataFrame に変換する。座標情報は含まれない。

    Parameters
    ----------
    records : list[dict]
        XIT001 API の data 配列。
    year : int
        取引年。
    quarter : int
        四半期 (1-4)。

    Returns
    -------
    pd.DataFrame
        正規化済み DataFrame。
    """
    if not records:
        return pd.DataFrame()

    out_records = []
    for i, props in enumerate(records):
        record: dict[str, Any] = {
            "year": year,
            "quarter": quarter,
            "raw_properties": json.dumps(props, ensure_ascii=False),
        }

        for col, candidates in _XIT001_FIELD_CANDIDATES.items():
            record[col] = _get_field(props, candidates)

        city_code = record.get("city_code", "")
        district = record.get("district_name", "") or ""
        record["trade_id"] = f"xit001_{year}{quarter}_{city_code}_{district}_{i}"

        if city_code and len(str(city_code)) >= 2:
            record["prefecture_code"] = str(city_code)[:2]
        else:
            record["prefecture_code"] = None

        record["build_year"] = _parse_japanese_year(record.pop("build_year_str", None))
        out_records.append(record)

    df = pd.DataFrame(out_records)

    for col in _XIT001_NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 単価が空の場合は総額÷面積で補完
    if "trade_price_per_sqm" in df.columns and "trade_price_total" in df.columns:
        mask = (
            df["trade_price_per_sqm"].isna()
            & df["trade_price_total"].notna()
            & df["area_sqm"].notna()
        )
        df.loc[mask, "trade_price_per_sqm"] = (
            df.loc[mask, "trade_price_total"] / df.loc[mask, "area_sqm"]
        )

    return df


def _parse_japanese_year(s: Any) -> int | None:
    """和暦文字列を西暦に変換する。例: "昭和45年" → 1970"""
    import re

    if s is None:
        return None
    s = str(s).strip()
    if not s or s in ("", "nan"):
        return None
    m = re.match(r"^(\d{4})年?$", s)
    if m:
        return int(m.group(1))
    era_map = {"明治": 1868, "大正": 1912, "昭和": 1926, "平成": 1989, "令和": 2019}
    for era, base in era_map.items():
        m = re.match(rf"{era}(\d+)年?", s)
        if m:
            return base + int(m.group(1)) - 1
    return None


# --------------------------------------------------------------------------
# (既存) 空 DataFrame
# --------------------------------------------------------------------------


def _empty_dataframe() -> pd.DataFrame:
    """スキーマ定義済みの空 DataFrame を返す。"""
    cols = [
        "point_id",
        "year",
        "price_classification",
        "survey_source",
        *list(_FIELD_CANDIDATES.keys()),
        "lon",
        "lat",
        "raw_properties",
    ]
    # survey_year_from_props は除外し standard_land_number を追加
    cols = [c for c in cols if c != "survey_year_from_props"]
    return pd.DataFrame(columns=cols)
