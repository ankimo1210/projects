"""
analytics.py
アプリとノートブック両方で使える分析関数群。

依存: pandas のみ（重い地理計算は shapely を使わず Haversine 近似で対応）
将来: 不動産投資シミュレーターから find_nearby_points() を呼ぶ想定。
"""

import math
from typing import Any

import pandas as pd
from config import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# 内部ユーティリティ
# --------------------------------------------------------------------------


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """2 点間の Haversine 距離をメートルで返す。"""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# --------------------------------------------------------------------------
# 集計
# --------------------------------------------------------------------------


def compute_city_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    市区町村別・年別・用途別の集計を返す。

    Returns
    -------
    DataFrame with columns:
        year, prefecture_code, prefecture_name, city_code, city_name,
        use_category_name, point_count, avg_price, median_price,
        max_price, min_price, avg_yoy_pct
    """
    if df.empty:
        return pd.DataFrame()

    grp = df.groupby(
        [
            "year",
            "prefecture_code",
            "prefecture_name",
            "city_code",
            "city_name",
            "use_category_name",
        ],
        dropna=False,
    )
    return (
        grp["price_yen_per_sqm"]
        .agg(
            point_count="count",
            avg_price="mean",
            median_price="median",
            max_price="max",
            min_price="min",
        )
        .join(grp["yoy_change_pct"].mean().rename("avg_yoy_pct"))
        .reset_index()
        .sort_values("avg_price", ascending=False)
    )


def compute_pref_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    都道府県別・年別の集計を返す。
    """
    if df.empty:
        return pd.DataFrame()

    grp = df.groupby(["year", "prefecture_code", "prefecture_name"], dropna=False)
    return (
        grp["price_yen_per_sqm"]
        .agg(
            point_count="count",
            avg_price="mean",
            median_price="median",
        )
        .join(grp["yoy_change_pct"].mean().rename("avg_yoy_pct"))
        .reset_index()
        .sort_values("avg_price", ascending=False)
    )


# --------------------------------------------------------------------------
# ランキング
# --------------------------------------------------------------------------


def compute_price_rankings(
    df: pd.DataFrame,
    top_n: int = 50,
    year: int | None = None,
) -> pd.DataFrame:
    """
    地点別価格ランキング（高い順）。

    Parameters
    ----------
    df : DataFrame
    top_n : int
        返す件数。
    year : int, optional
        絞り込む年。省略時は df 内の最新年を使用。
    """
    if df.empty:
        return pd.DataFrame()
    target_year = year or df["year"].max()
    subset = df[df["year"] == target_year].copy()
    subset = subset.dropna(subset=["price_yen_per_sqm"])
    subset["rank"] = subset["price_yen_per_sqm"].rank(ascending=False, method="min").astype(int)
    cols = [
        "rank",
        "point_id",
        "standard_land_number",
        "location_text",
        "city_name",
        "prefecture_name",
        "use_category_name",
        "price_yen_per_sqm",
        "yoy_change_pct",
        "year",
    ]
    cols = [c for c in cols if c in subset.columns]
    return subset.nlargest(top_n, "price_yen_per_sqm")[cols].reset_index(drop=True)


def compute_yoy_rankings(
    df: pd.DataFrame,
    top_n: int = 50,
    ascending: bool = False,
    year: int | None = None,
) -> pd.DataFrame:
    """
    前年比変動率ランキング。

    Parameters
    ----------
    ascending : bool
        True = 下落率ランキング、False = 上昇率ランキング。
    """
    if df.empty:
        return pd.DataFrame()
    target_year = year or df["year"].max()
    subset = df[df["year"] == target_year].copy()
    subset = subset.dropna(subset=["yoy_change_pct"])

    cols = [
        "point_id",
        "standard_land_number",
        "location_text",
        "city_name",
        "prefecture_name",
        "use_category_name",
        "price_yen_per_sqm",
        "yoy_change_pct",
        "year",
    ]
    cols = [c for c in cols if c in subset.columns]
    ranked = (
        subset.nsmallest(top_n, "yoy_change_pct")
        if ascending
        else subset.nlargest(top_n, "yoy_change_pct")
    )
    return ranked[cols].reset_index(drop=True)


# --------------------------------------------------------------------------
# 時系列
# --------------------------------------------------------------------------


def compute_point_timeseries(
    df: pd.DataFrame,
    point_id: str,
) -> pd.DataFrame:
    """
    特定 point_id の年次推移データを返す。

    Returns
    -------
    DataFrame sorted by year with:
        year, price_yen_per_sqm, last_year_price_yen_per_sqm,
        yoy_change_pct, location_text, ...
    """
    ts = df[df["point_id"] == point_id].sort_values("year")
    if ts.empty:
        logger.warning("point_id '%s' のデータが見つかりません", point_id)
    return ts.reset_index(drop=True)


def compare_years(
    df: pd.DataFrame,
    year_a: int,
    year_b: int,
) -> pd.DataFrame:
    """
    2 年間で共通する point_id の価格変化を比較する。

    Returns
    -------
    DataFrame with columns:
        point_id, location_text, city_name, prefecture_name,
        price_{year_a}, price_{year_b}, absolute_change, pct_change
    """
    a = df[df["year"] == year_a][
        ["point_id", "price_yen_per_sqm", "location_text", "city_name", "prefecture_name"]
    ].copy()
    b = df[df["year"] == year_b][["point_id", "price_yen_per_sqm"]].copy()

    a = a.rename(columns={"price_yen_per_sqm": f"price_{year_a}"})
    b = b.rename(columns={"price_yen_per_sqm": f"price_{year_b}"})

    merged = a.merge(b, on="point_id", how="inner")
    merged["absolute_change"] = merged[f"price_{year_b}"] - merged[f"price_{year_a}"]
    merged["pct_change"] = (merged["absolute_change"] / merged[f"price_{year_a}"] * 100).round(2)
    return merged.sort_values("pct_change", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# 近傍検索（不動産投資シミュレーター連携を見越した実装）
# --------------------------------------------------------------------------


def find_nearby_points(
    df: pd.DataFrame,
    lon: float,
    lat: float,
    radius_m: float = 1000.0,
    year: int | None = None,
) -> pd.DataFrame:
    """
    指定座標から半径 radius_m 以内の公示地点を返す。

    将来の不動産投資シミュレーターからは、物件座標を渡して
    近傍の公示価格相場を取得する想定。

    Parameters
    ----------
    df : DataFrame  全データ（またはフィルタ済みデータ）。
    lon, lat : float  中心座標（経緯度）。
    radius_m : float  検索半径（メートル）。
    year : int, optional  絞り込む年。

    Returns
    -------
    DataFrame with additional column 'distance_m', sorted by distance.
    """
    if df.empty:
        return pd.DataFrame()

    subset = df.copy()
    if year:
        subset = subset[subset["year"] == year]

    subset = subset.dropna(subset=["lon", "lat"])
    if subset.empty:
        return pd.DataFrame()

    subset["distance_m"] = subset.apply(
        lambda row: _haversine_m(lon, lat, row["lon"], row["lat"]),
        axis=1,
    )
    nearby = subset[subset["distance_m"] <= radius_m].sort_values("distance_m")
    return nearby.reset_index(drop=True)


# --------------------------------------------------------------------------
# 多年比較・指数化（都市トレンドタブ用）
# --------------------------------------------------------------------------


def compute_indexed_prices(df: pd.DataFrame, base_year: int) -> pd.DataFrame:
    """
    city_summary 粒度の DataFrame を基準年=100 に指数化する。

    Parameters
    ----------
    df : DataFrame
        get_multiyear_city_summary() の返却値（city_code, use_category_name, year, avg_price 列必須）
    base_year : int
        指数の基準とする年（その年の avg_price を 100 とする）

    Returns
    -------
    DataFrame
        元の列に加えて index_100 列を追加。
        基準年データがないグループは index_100 = NaN（Plotly でギャップ表示）。
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result["index_100"] = float("nan")

    group_keys = ["city_code", "use_category_name"]
    for _keys, group in result.groupby(group_keys, dropna=False):
        base_rows = group[group["year"] == base_year]
        if base_rows.empty or pd.isna(base_rows["avg_price"].iloc[0]):
            continue
        base_price = base_rows["avg_price"].iloc[0]
        if base_price == 0:
            continue
        result.loc[group.index, "index_100"] = group["avg_price"] / base_price * 100

    return result.sort_values(["city_code", "use_category_name", "year"]).reset_index(drop=True)


def compute_pref_multiyear_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    city_summary 粒度データを都道府県集計に集約する。

    avg_price は point_count 加重平均。都道府県全体表示モード用。

    Parameters
    ----------
    df : DataFrame
        get_multiyear_city_summary() の返却値
    """
    if df.empty:
        return pd.DataFrame()

    grp = df.groupby(
        ["year", "prefecture_code", "prefecture_name", "use_category_name"], dropna=False
    )

    weighted_price = (
        grp.apply(
            lambda g: (
                (g["avg_price"] * g["point_count"]).sum() / g["point_count"].sum()
                if g["point_count"].sum() > 0
                else float("nan")
            ),
            include_groups=False,
        )
        .rename("avg_price")
        .reset_index()
    )
    point_counts = grp["point_count"].sum().rename("point_count").reset_index()
    avg_yoy = grp["avg_yoy_pct"].mean().rename("avg_yoy_pct").reset_index()

    result = weighted_price.merge(
        point_counts, on=["year", "prefecture_code", "prefecture_name", "use_category_name"]
    )
    result = result.merge(
        avg_yoy, on=["year", "prefecture_code", "prefecture_name", "use_category_name"]
    )
    return result.sort_values(["year", "prefecture_code"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# 価格統計サマリー（ノートブック用）
# --------------------------------------------------------------------------


def compute_basic_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    DataFrame 全体の基本統計を dict で返す。

    ノートブックや Admin タブでの表示に使用。
    """
    if df.empty:
        return {"total": 0}

    price_col = "price_yen_per_sqm"
    stats: dict[str, Any] = {
        "total": len(df),
        "years": sorted(df["year"].dropna().unique().tolist()),
        "prefecture_count": df["prefecture_name"].nunique(),
        "city_count": df["city_name"].nunique(),
    }

    if price_col in df.columns and df[price_col].notna().any():
        p = df[price_col].dropna()
        stats.update(
            {
                "price_mean": round(p.mean(), 0),
                "price_median": round(p.median(), 0),
                "price_max": round(p.max(), 0),
                "price_min": round(p.min(), 0),
                "price_std": round(p.std(), 0),
            }
        )

    if "yoy_change_pct" in df.columns and df["yoy_change_pct"].notna().any():
        y = df["yoy_change_pct"].dropna()
        stats.update(
            {
                "yoy_mean": round(y.mean(), 2),
                "yoy_max": round(y.max(), 2),
                "yoy_min": round(y.min(), 2),
            }
        )

    return stats


# --------------------------------------------------------------------------
# 人口統計
# --------------------------------------------------------------------------


def compute_population_trend(conn, city_code: str, years: int = 5) -> dict:
    """
    指定市区町村の直近N年の人口トレンドを返す。

    Returns
    -------
    dict with keys:
        latest_year, total_population, households,
        pop_5yr_change_pct, households_5yr_change_pct,
        aging_rate, net_migration, trend_df (DataFrame)
    """
    import db as _db

    df = _db.get_population_stats(conn, city_code)
    if df.empty:
        return {}

    df = df.sort_values("survey_year").tail(years + 1).reset_index(drop=True)
    latest = df.iloc[-1].to_dict()

    result: dict = {
        "latest_year": int(latest.get("survey_year", 0)),
        "total_population": latest.get("total_population"),
        "households": latest.get("households"),
        "aging_rate": latest.get("aging_rate"),
        "net_migration": latest.get("net_migration"),
        "trend_df": df,
    }

    if len(df) >= 2:
        oldest = df.iloc[0]
        pop_old = oldest.get("total_population")
        pop_new = latest.get("total_population")
        hh_old = oldest.get("households")
        hh_new = latest.get("households")
        yr_span = latest.get("survey_year", 0) - oldest.get("survey_year", 0)

        if pop_old and pop_new and yr_span > 0:
            result["pop_5yr_change_pct"] = round((pop_new - pop_old) / pop_old * 100, 2)
        else:
            result["pop_5yr_change_pct"] = None

        if hh_old and hh_new and yr_span > 0:
            result["households_5yr_change_pct"] = round((hh_new - hh_old) / hh_old * 100, 2)
        else:
            result["households_5yr_change_pct"] = None

        result["span_years"] = yr_span
    else:
        result["pop_5yr_change_pct"] = None
        result["households_5yr_change_pct"] = None
        result["span_years"] = 0

    return result


# --------------------------------------------------------------------------
# 近隣掲載物件検索
# --------------------------------------------------------------------------


def find_nearby_listings(
    conn,
    lon: float,
    lat: float,
    radius_m: float = 3000.0,
    exclude_listing_id: str | None = None,
) -> pd.DataFrame:
    """
    指定座標から半径 radius_m 以内の掲載物件（listing_master）を返す。

    Parameters
    ----------
    conn : DuckDB 接続
    lon, lat : 中心座標（経緯度）
    radius_m : 検索半径（メートル）
    exclude_listing_id : 除外する listing_id（分析中の物件自身を除く）

    Returns
    -------
    DataFrame with columns from listing_master + distance_m, sorted by distance.
    """
    df = conn.execute(
        """
        SELECT listing_id, property_name, address, property_type, structure,
               asking_price_yen, gross_yield_pct, gross_rent_annual_yen,
               gross_rent_monthly_yen, age_years, building_area_sqm,
               land_area_sqm, num_units, nearest_station, station_walk_min,
               source_url, lat, lon
        FROM listing_master
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        """
    ).df()

    if df.empty:
        return pd.DataFrame()

    if exclude_listing_id:
        df = df[df["listing_id"] != exclude_listing_id]

    df["distance_m"] = df.apply(
        lambda row: _haversine_m(lon, lat, row["lon"], row["lat"]),
        axis=1,
    )
    nearby = df[df["distance_m"] <= radius_m].sort_values("distance_m")
    return nearby.reset_index(drop=True)
