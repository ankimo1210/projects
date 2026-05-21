"""
ui/property_nearby.py
周辺地価・近隣物件・施設・地図・地形リスクの表示。
"""
from __future__ import annotations
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from analytics import find_nearby_points, find_nearby_listings
from config import get_logger
from facility_sources import (
    FACILITY_CATEGORY_LABELS,
    FacilitySearchError,
    find_nearby_facility_groups,
    summarize_facility_groups,
)
from hazard_sources import summarize_hazard_risk
from property_scraper import PropertyData, STRUCTURE_JP
from terrain_sources import (
    TerrainSearchError,
    elevation_band,
    fetch_elevation_gsi,
    find_nearby_water,
    summarize_terrain_features,
)
from ui.unit_price import add_tsubo_price_column, format_man, format_yen_per_sqm_and_tsubo_jp, yen_to_man
from ui.table import render_html_table, plain, muted, truncate, gap_bar, signed_pct_str, num_str, dist_str
from ui.components import render_population_card
from analytics import compute_population_trend

logger = get_logger(__name__)

def _load_nearby_land(_conn, year: int) -> pd.DataFrame:
    return db.read_land_prices(_conn, filters={"year": year})


@st.cache_data(ttl=600, show_spinner=False)
def _load_nearby_trade(_conn, years: tuple) -> pd.DataFrame:
    return db.read_trade_prices(_conn, filters={"year": list(years)})


_PROPERTY_FACILITY_CATEGORIES = [
    "convenience",
    "supermarket",
    "transit",
    "pachinko",
    "food",
    "school",
    "medical",
    "park",
]


@st.cache_data(ttl=86400, show_spinner=False)
def _load_nearby_facility_groups(categories: tuple[str, ...], lat: float, lon: float, radius_m: int) -> dict[str, list[dict]]:
    """Overpass API の結果を Streamlit キャッシュしやすい dict にして返す。"""
    grouped = find_nearby_facility_groups(list(categories), lon=lon, lat=lat, radius_m=radius_m)
    return {
        category: [
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
        for category, facilities in grouped.items()
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _load_elevation(lat: float, lon: float) -> dict:
    """国土地理院の標高結果を Streamlit キャッシュしやすい dict にして返す。"""
    result = fetch_elevation_gsi(lon=lon, lat=lat)
    return {
        "elevation_m": result.elevation_m,
        "source": result.source,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _load_nearby_water(lat: float, lon: float, radius_m: int) -> list[dict]:
    """Overpass API の河川・水辺結果を Streamlit キャッシュしやすい dict にして返す。"""
    features = find_nearby_water(lon=lon, lat=lat, radius_m=radius_m)
    return [
        {
            "name": f.name,
            "type_label": f.type_label,
            "distance_m": f.distance_m,
            "osm_type": f.osm_type,
            "osm_id": f.osm_id,
            "lat": f.lat,
            "lon": f.lon,
        }
        for f in features
    ]


def _render_nearby_prices(
    nearby_land: pd.DataFrame,
    nearby_trade: pd.DataFrame,
    prop,
    radius_m: int,
    radius_trade=None,
    conn=None,
    city_code: Optional[str] = None,
) -> None:
    st.markdown("---")
    label = f"{radius_m // 1000}km"
    trade_label = radius_trade if isinstance(radius_trade, str) else f"{radius_trade // 1000}km"
    st.markdown(f"#### 📊 近傍地価データ（公示地価: 半径{label} ／ 取引価格: {trade_label}）")

    col_land, col_trade = st.columns(2)

    with col_land:
        st.markdown("**公示地価**")
        if nearby_land.empty:
            st.info("近傍の公示地価データがありません。")
        else:
            land_ref, land_use_label, land_ref_note = _select_land_price_reference_points(nearby_land, prop)
            median_price = land_ref["price_yen_per_sqm"].median()
            avg_yoy = land_ref["yoy_change_pct"].mean() if "yoy_change_pct" in land_ref.columns else None
            land_metrics = [
                ("地点数", f"{len(land_ref)} 件", f"用途: {land_use_label}"),
                ("中央値単価", format_yen_per_sqm_and_tsubo_jp(median_price), None),
            ]
            if avg_yoy is not None:
                land_metrics.append(("平均騰落率", f"{avg_yoy:+.1f} %", None))
            _render_summary_panel(None, land_metrics, columns=3)
            st.caption(land_ref_note)

            # 全近傍地点を表示し、分析物件の用途と一致する行をハイライト
            target_uses = set(_land_use_candidates_for_property(prop))
            show_all = nearby_land.copy()
            show_cols = ["year", "distance_m", "location_text", "price_yen_per_sqm", "use_category_name", "yoy_change_pct"]
            show_cols = [c for c in show_cols if c in show_all.columns]
            disp = show_all[show_cols].copy()
            if "distance_m" in disp.columns:
                disp = disp.sort_values("distance_m")
                disp["distance_m"] = disp["distance_m"].map(lambda x: f"{x:.0f}")
            if "price_yen_per_sqm" in disp.columns:
                disp = add_tsubo_price_column(disp, "price_yen_per_sqm", "price_tsubo_man")
                disp["price_yen_per_sqm"] = disp["price_yen_per_sqm"].map(lambda x: format_man(yen_to_man(x)))
                disp["price_tsubo_man"] = disp["price_tsubo_man"].map(format_man)
            if "yoy_change_pct" in disp.columns:
                disp["yoy_change_pct"] = disp["yoy_change_pct"].map(lambda x: f"{x:+.1f}%")
            disp = disp.rename(columns=
                {"year": "年度", "distance_m": "距離(m)", "location_text": "所在地",
                 "price_yen_per_sqm": "単価(万円/m²)", "price_tsubo_man": "坪(万円/坪)",
                 "use_category_name": "用途", "yoy_change_pct": "前年比"}
            )

            def _row_style(row: pd.Series) -> str:
                if row.get("用途") in target_uses:
                    return "border-left:3px solid #4fc3f7;background:rgba(21,65,120,0.35);"
                return "border-left:3px solid transparent;opacity:0.55;"

            from ui.table import use_category_badge as _ucbadge
            render_html_table(disp.head(20), [
                {"key": "年度",       "label": "年度",       "width": 50,  "align": "right", "render": plain},
                {"key": "距離(m)",    "label": "距離(m)",    "width": 70,  "align": "right", "render": dist_str},
                {"key": "所在地",     "label": "所在地",     "width": 180, "render": lambda v: truncate(v, 170)},
                {"key": "単価(万円/m²)","label": "単価(万/m²)","width": 85, "align": "right", "render": num_str},
                {"key": "坪(万円/坪)","label": "坪(万/坪)",  "width": 75,  "align": "right", "render": num_str},
                {"key": "用途",       "label": "用途",       "width": 75,  "render": _ucbadge},
                {"key": "前年比",     "label": "前年比",     "width": 80,  "align": "right", "render": signed_pct_str},
            ], row_style_fn=_row_style)
            if target_uses:
                st.caption(f"💡 ハイライト行（青枠）= 分析物件の用途に対応: {' / '.join(sorted(target_uses))}")

    with col_trade:
        st.markdown("**取引価格**")
        if nearby_trade.empty:
            st.info("近傍の取引価格データがありません。")
        else:
            med_trade = nearby_trade["trade_price_per_sqm"].median()
            avg_area = nearby_trade["area_sqm"].mean() if "area_sqm" in nearby_trade.columns else None
            trade_metrics = [
                ("件数", f"{len(nearby_trade)} 件", None),
                ("中央値単価", format_yen_per_sqm_and_tsubo_jp(med_trade), None),
            ]
            if avg_area is not None:
                trade_metrics.append(("平均面積", f"{avg_area:.0f} m²", None))
            _render_summary_panel(None, trade_metrics, columns=3)

            land_unit_median = None
            trade_for_display = nearby_trade.copy()
            estimate_counts = {"land_estimate_count": 0, "building_split_count": 0}
            if not nearby_land.empty and "price_yen_per_sqm" in nearby_land.columns:
                land_ref, land_use_label, land_ref_note = _select_land_price_reference_points(nearby_land, prop)
                land_prices = pd.to_numeric(land_ref["price_yen_per_sqm"], errors="coerce").dropna()
                if not land_prices.empty:
                    land_unit_p25 = float(land_prices.quantile(0.25))
                    land_unit_p75 = float(land_prices.quantile(0.75))
                    trade_for_display, estimate_counts = _estimate_trade_land_building_split(
                        trade_for_display,
                        land_unit_p25,
                        land_unit_p75,
                    )
                    if estimate_counts["land_estimate_count"] > 0:
                        estimated_building_low = pd.to_numeric(
                            trade_for_display["estimated_building_price_low_yen"],
                            errors="coerce",
                        ).dropna()
                        estimated_building_high = pd.to_numeric(
                            trade_for_display["estimated_building_price_high_yen"],
                            errors="coerce",
                        ).dropna()
                        estimate_metrics = [
                            (
                                "土地単価前提",
                                f"{format_yen_per_sqm_and_tsubo_jp(land_unit_p25)}〜{format_yen_per_sqm_and_tsubo_jp(land_unit_p75)}",
                                f"用途: {land_use_label}",
                            ),
                            ("土地推定件数", f"{estimate_counts['land_estimate_count']} 件", "宅地(土地) / 宅地(土地と建物)"),
                        ]
                        if estimate_counts["building_split_count"] > 0:
                            estimate_metrics.append(
                                ("建物分離件数", f"{estimate_counts['building_split_count']} 件", "宅地(土地と建物) のみ")
                            )
                        if not estimated_building_low.empty and not estimated_building_high.empty:
                            estimate_metrics.append(
                                (
                                    "推定建物価格中央値",
                                    f"{estimated_building_low.median() / 1e4:,.0f}〜{estimated_building_high.median() / 1e4:,.0f} 万円",
                                    "取引総額 - 推定土地価格レンジ",
                                )
                            )
                        _render_summary_panel("土地/建物分離（概算）", estimate_metrics, columns=3)
                        st.caption(
                            "取引事例の土地価格は 用途で絞った近傍公示地価の 25〜75%ile × 取引面積 で概算しています。"
                            " 建物価格の残余計算は 宅地(土地と建物) のみです。"
                        )
                        st.caption(land_ref_note)

            _QUARTER_LABEL = {1: "1〜3月期", 2: "4〜6月期", 3: "7〜9月期", 4: "10〜12月期"}

            show_cols = ["year", "quarter", "distance_m", "city_name", "district_name",
                         "trade_price_per_sqm", "trade_price_total", "trade_type", "area_sqm", "total_floor_area_sqm"]
            show_cols = [c for c in show_cols if c in nearby_trade.columns]
            if estimate_counts["land_estimate_count"] > 0:
                show_cols.extend(
                    [
                        "estimated_land_price_low_yen",
                        "estimated_land_price_high_yen",
                        "estimated_building_price_low_yen",
                        "estimated_building_price_high_yen",
                        "estimated_building_price_low_per_sqm",
                        "estimated_building_price_high_per_sqm",
                    ]
                )
            show_cols = [c for c in show_cols if c in trade_for_display.columns]
            disp = trade_for_display[show_cols].copy()
            if "quarter" in disp.columns:
                disp["quarter"] = disp["quarter"].map(lambda q: _QUARTER_LABEL.get(int(q), f"Q{q}") if pd.notna(q) else "")
            if "distance_m" in disp.columns:
                disp = disp.sort_values("distance_m")
                disp["distance_m"] = disp["distance_m"].map(lambda x: f"{x:.0f}")
            if "trade_price_per_sqm" in disp.columns:
                disp = add_tsubo_price_column(disp, "trade_price_per_sqm", "trade_price_tsubo_man")
                disp["trade_price_per_sqm"] = disp["trade_price_per_sqm"].map(lambda x: format_man(yen_to_man(x)))
                disp["trade_price_tsubo_man"] = disp["trade_price_tsubo_man"].map(format_man)
            for col in [
                "trade_price_total",
                "estimated_land_price_low_yen",
                "estimated_land_price_high_yen",
                "estimated_building_price_low_yen",
                "estimated_building_price_high_yen",
            ]:
                if col in disp.columns:
                    disp[col] = pd.to_numeric(disp[col], errors="coerce").map(
                        lambda x: format_man(yen_to_man(x)) if pd.notna(x) else "—"
                    )
            if "area_sqm" in disp.columns:
                disp["area_sqm"] = disp["area_sqm"].map(lambda x: f"{x:.0f}")
            if "total_floor_area_sqm" in disp.columns:
                disp["total_floor_area_sqm"] = pd.to_numeric(disp["total_floor_area_sqm"], errors="coerce").map(
                    lambda x: f"{x:.0f}" if pd.notna(x) else "—"
                )
            for src_col, tsubo_col in [
                ("estimated_building_price_low_per_sqm", "estimated_building_price_low_per_tsubo_man"),
                ("estimated_building_price_high_per_sqm", "estimated_building_price_high_per_tsubo_man"),
            ]:
                if src_col in disp.columns:
                    disp = add_tsubo_price_column(disp, src_col, tsubo_col)
                    disp[src_col] = pd.to_numeric(
                        disp[src_col],
                        errors="coerce",
                    ).map(lambda x: format_man(yen_to_man(x)) if pd.notna(x) else "—")
                    disp[tsubo_col] = disp[tsubo_col].map(
                        lambda x: format_man(x) if pd.notna(x) else "—"
                    )
            disp = disp.rename(columns=
                {"year": "年度", "quarter": "時期", "distance_m": "距離(m)",
                 "city_name": "市区町村", "district_name": "地区",
                 "trade_price_total": "総額(万円)",
                 "trade_price_per_sqm": "単価(万円/m²)", "trade_price_tsubo_man": "坪(万円/坪)",
                 "trade_type": "種別", "area_sqm": "土地面積(m²)", "total_floor_area_sqm": "延床面積(m²)",
                 "estimated_land_price_low_yen": "推定土地価格下限(万円)",
                 "estimated_land_price_high_yen": "推定土地価格上限(万円)",
                 "estimated_building_price_low_yen": "推定建物価格下限(万円)",
                 "estimated_building_price_high_yen": "推定建物価格上限(万円)",
                 "estimated_building_price_low_per_sqm": "建物単価下限(万円/m²)",
                 "estimated_building_price_low_per_tsubo_man": "建物坪下限(万円/坪)",
                 "estimated_building_price_high_per_sqm": "建物単価上限(万円/m²)",
                 "estimated_building_price_high_per_tsubo_man": "建物坪上限(万円/坪)"}
            )
            render_html_table(disp.head(20), [
                {"key": "年度",       "label": "年度",    "width": 50,  "align": "right", "render": plain},
                {"key": "時期",       "label": "時期",    "width": 75,  "render": muted},
                {"key": "距離(m)",    "label": "距離(m)", "width": 65,  "align": "right", "render": dist_str},
                {"key": "市区町村",   "label": "市区町村","width": 80,  "render": muted},
                {"key": "地区",       "label": "地区",    "width": 85,  "render": lambda v: truncate(v, 80)},
                {"key": "種別",       "label": "種別",    "width": 80,  "render": muted},
                {"key": "単価(万円/m²)","label": "単価(万/m²)","width": 85,"align": "right","render": num_str},
                {"key": "坪(万円/坪)","label": "坪(万/坪)","width": 75, "align": "right", "render": num_str},
                {"key": "総額(万円)", "label": "総額(万円)","width": 85, "align": "right", "render": num_str},
                {"key": "土地面積(m²)","label": "土地(m²)","width": 65, "align": "right", "render": num_str},
                {"key": "延床面積(m²)","label": "延床(m²)","width": 65, "align": "right", "render": num_str},
                {"key": "推定土地価格下限(万円)", "label": "土地下限(万)", "width": 80, "align": "right", "render": num_str},
                {"key": "推定土地価格上限(万円)", "label": "土地上限(万)", "width": 80, "align": "right", "render": num_str},
                {"key": "推定建物価格下限(万円)", "label": "建物下限(万)", "width": 80, "align": "right", "render": num_str},
                {"key": "推定建物価格上限(万円)", "label": "建物上限(万)", "width": 80, "align": "right", "render": num_str},
            ], min_width=800)

def _render_nearby_listings(conn, geo: tuple[float, float], current_listing_id: Optional[str]) -> None:
    """半径内の保存済み掲載物件を表示する。"""
    lat, lon = geo
    _RADII = [1000, 3000, 5000]
    _MIN_COUNT = 2

    nearby = pd.DataFrame()
    radius_used = _RADII[-1]
    for r in _RADII:
        df = find_nearby_listings(conn, lon, lat, radius_m=r, exclude_listing_id=current_listing_id)
        if len(df) >= _MIN_COUNT:
            nearby = df
            radius_used = r
            break
        if not df.empty:
            nearby = df
            radius_used = r

    label = f"{radius_used // 1000}km"
    st.markdown("---")
    st.markdown(f"#### 📦 近隣の掲載物件（半径{label}以内）")

    if nearby.empty:
        st.caption("近隣に保存済み掲載物件がありません。")
        return

    from ui.unit_price import yen_to_man, format_man

    disp = nearby.copy()
    disp["price_man"] = disp["asking_price_yen"].apply(
        lambda v: f"{float(v)/1e4:,.0f}" if v is not None and v == v else "—"
    )
    disp["yield_str"] = disp["gross_yield_pct"].apply(
        lambda v: f"{float(v):.1f}%" if v is not None and v == v else "—"
    )
    disp["age_str"] = disp["age_years"].apply(
        lambda v: f"築{int(v)}年" if v is not None and v == v else "—"
    )
    disp["area_str"] = disp["building_area_sqm"].apply(
        lambda v: f"{float(v):.0f}m²" if v is not None and v == v else "—"
    )
    disp["dist_str"] = disp["distance_m"].apply(lambda v: f"{v:.0f}m")
    disp["name_label"] = disp.apply(
        lambda row: row.get("property_name") or row.get("address") or "—", axis=1
    )

    render_html_table(
        disp.head(15),
        [
            {"key": "dist_str",    "label": "距離",     "width": 65,  "align": "right", "render": muted},
            {"key": "name_label",  "label": "物件名",   "width": 160, "render": lambda v: truncate(v, 150)},
            {"key": "property_type","label": "種別",    "width": 80,  "render": muted},
            {"key": "price_man",   "label": "価格(万円)","width": 90,  "align": "right", "render": plain},
            {"key": "yield_str",   "label": "表面利回り","width": 80,  "align": "right", "render": plain},
            {"key": "age_str",     "label": "築年数",   "width": 65,  "align": "right", "render": muted},
            {"key": "area_str",    "label": "延床面積", "width": 70,  "align": "right", "render": muted},
        ],
        caption=f"{len(nearby)} 件",
        min_width=620,
    )


def _render_nearby_facility_summary(geo: tuple[float, float]) -> None:
    """物件周辺施設を Overpass API から取得して表示する。"""
    lat, lon = geo
    radius_m = 1000

    st.markdown("---")
    st.markdown("#### 🧭 周辺施設")
    st.caption("OpenStreetMap の POI を使った簡易チェックです。未登録施設は検出できません。半径は 1km 固定です。")

    rounded_lat = round(float(lat), 5)
    rounded_lon = round(float(lon), 5)
    summary_rows: list[dict] = []
    detail_frames: list[pd.DataFrame] = []

    with st.spinner("周辺施設を取得中..."):
        try:
            grouped = _load_nearby_facility_groups(
                tuple(_PROPERTY_FACILITY_CATEGORIES),
                rounded_lat,
                rounded_lon,
                radius_m,
            )
        except FacilitySearchError as exc:
            logger.warning("周辺施設取得失敗: %s", exc)
            st.warning("周辺施設情報を取得できませんでした。時間を置いて再読み込みしてください。")
            return
        except Exception as exc:
            logger.exception("周辺施設取得中に予期しないエラー")
            st.warning(f"周辺施設情報を取得できませんでした: {exc}")
            return

        for category in _PROPERTY_FACILITY_CATEGORIES:
            label = FACILITY_CATEGORY_LABELS.get(category, category)
            facilities = grouped.get(category, [])
            if facilities:
                df = pd.DataFrame(facilities).sort_values("distance_m").reset_index(drop=True)
                nearest = df.iloc[0]
                within_500m = int((df["distance_m"] <= 500).sum())
                summary_rows.append(
                    {
                        "項目": label,
                        "1km以内": f"{len(df)} 件",
                        "500m以内": f"{within_500m} 件",
                        "最寄り": f"{nearest['distance_m']:.0f} m",
                    }
                )

                detail = df.head(5).copy()
                detail["項目"] = label
                detail["distance_m"] = detail["distance_m"].map(lambda x: f"{x:.0f}")
                detail["brand"] = detail["brand"].fillna(detail["operator"]).fillna("—")
                detail_frames.append(
                    detail[["項目", "name", "distance_m", "brand"]].rename(
                        columns={"name": "施設名", "distance_m": "距離(m)", "brand": "ブランド/運営"}
                    )
                )
            else:
                summary_rows.append({"項目": label, "1km以内": "0 件", "500m以内": "0 件", "最寄り": "—"})

    render_html_table(pd.DataFrame(summary_rows), [
        {"key": "項目",    "label": "施設種別", "width": 90,  "render": plain},
        {"key": "1km以内", "label": "1km以内",  "width": 70,  "align": "right", "render": plain},
        {"key": "500m以内","label": "500m以内", "width": 70,  "align": "right", "render": plain},
        {"key": "最寄り",  "label": "最寄り",   "width": 80,  "align": "right", "render": dist_str},
    ])

    if detail_frames:
        with st.expander("近い施設の一覧", expanded=False):
            details = pd.concat(detail_frames, ignore_index=True)
            col_filter, col_limit = st.columns([3, 1])
            with col_filter:
                available_labels = [
                    FACILITY_CATEGORY_LABELS.get(c, c)
                    for c in _PROPERTY_FACILITY_CATEGORIES
                    if FACILITY_CATEGORY_LABELS.get(c, c) in set(details["項目"])
                ]
                selected_labels = st.multiselect(
                    "表示する項目",
                    options=available_labels,
                    default=available_labels,
                    key="property_facility_detail_filter",
                )
            with col_limit:
                per_category = st.number_input(
                    "各項目の件数",
                    min_value=1,
                    max_value=20,
                    value=5,
                    step=1,
                    key="property_facility_detail_limit",
                )

            filtered = details[details["項目"].isin(selected_labels)].copy() if selected_labels else details.iloc[0:0].copy()
            filtered["_distance_num"] = pd.to_numeric(filtered["距離(m)"], errors="coerce")
            filtered = (
                filtered.sort_values(["項目", "_distance_num"])
                .groupby("項目", group_keys=False)
                .head(int(per_category))
                .drop(columns=["_distance_num"])
            )
            render_html_table(filtered, [
                {"key": "項目",       "label": "種別",       "width": 80,  "render": muted},
                {"key": "施設名",     "label": "施設名",     "width": 150, "render": lambda v: truncate(v, 140)},
                {"key": "距離(m)",    "label": "距離(m)",    "width": 70,  "align": "right", "render": dist_str},
                {"key": "ブランド/運営","label": "ブランド/運営","width": 120,"render": muted},
            ])


def _render_location_map(
    geo: tuple[float, float],
    nearby_land: pd.DataFrame,
    nearby_trade: pd.DataFrame,
    conn=None,
) -> None:
    """物件・近傍地価・周辺施設・水辺を1枚の Plotly Mapbox に重ねて表示する。

    DuckDB に POI キャッシュがあれば優先使用し、Overpass API 呼び出しを省略する。
    """
    import plotly.graph_objects as go

    lat, lon = geo
    rounded_lat = round(float(lat), 5)
    rounded_lon = round(float(lon), 5)
    location_key = db.make_location_key(rounded_lat, rounded_lon)

    st.markdown("---")
    st.markdown("#### 🗺 位置・周辺マップ")

    _FACILITY_COLORS: dict[str, str] = {
        "convenience_store": "#FFD700",
        "supermarket":       "#2ECC71",
        "station":           "#9B59B6",
        "bus_stop":          "#8E44AD",
        "pachinko":          "#C0392B",
        "restaurant":        "#E67E22",
        "school":            "#3498DB",
        "hospital":          "#E74C3C",
        "park":              "#27AE60",
    }

    traces: list = []

    # 近傍公示地価
    if not nearby_land.empty:
        lm = nearby_land.dropna(subset=["lat", "lon"])
        if not lm.empty:
            loc_text = lm["location_text"] if "location_text" in lm.columns else pd.Series(["公示地価"] * len(lm), index=lm.index)
            traces.append(go.Scattermapbox(
                lat=lm["lat"], lon=lm["lon"],
                mode="markers",
                marker=dict(size=8, color="#4A90D9", opacity=0.75),
                name="公示地価",
                text=loc_text.fillna("公示地価"),
                hovertemplate="%{text}<extra>公示地価</extra>",
            ))

    # 近傍取引価格
    if not nearby_trade.empty:
        tm = nearby_trade.dropna(subset=["lat", "lon"])
        if not tm.empty:
            traces.append(go.Scattermapbox(
                lat=tm["lat"], lon=tm["lon"],
                mode="markers",
                marker=dict(size=6, color="#F5A623", opacity=0.65),
                name="取引価格",
                hovertemplate="取引価格<extra></extra>",
            ))

    # 周辺施設（DuckDB キャッシュ優先 → Overpass フォールバック）
    try:
        grouped: dict[str, list[dict]] = {}
        if conn is not None:
            grouped = db.get_cached_facility_pois(conn, location_key)
        if not grouped:
            grouped = _load_nearby_facility_groups(
                tuple(_PROPERTY_FACILITY_CATEGORIES), rounded_lat, rounded_lon, 1000
            )
        for category, facilities in grouped.items():
            if not facilities:
                continue
            label = FACILITY_CATEGORY_LABELS.get(category, category)
            color = _FACILITY_COLORS.get(category, "#95A5A6")
            df_f = pd.DataFrame(facilities)
            traces.append(go.Scattermapbox(
                lat=df_f["lat"], lon=df_f["lon"],
                mode="markers",
                marker=dict(size=7, color=color, opacity=0.85),
                name=label,
                text=df_f["name"].fillna(label),
                customdata=df_f["distance_m"].map(lambda x: f"{x:.0f}"),
                hovertemplate="%{text} (%{customdata}m)<extra>" + label + "</extra>",
            ))
    except Exception:
        pass

    # 河川・水辺（DuckDB キャッシュ優先 → Overpass フォールバック）
    try:
        water_features: list[dict] = []
        if conn is not None:
            water_features = db.get_cached_water_features(conn, location_key)
        if not water_features:
            water_features = _load_nearby_water(rounded_lat, rounded_lon, 1000)
        if water_features:
            wdf = pd.DataFrame(water_features)
            traces.append(go.Scattermapbox(
                lat=wdf["lat"], lon=wdf["lon"],
                mode="markers",
                marker=dict(size=6, color="#1ABC9C", opacity=0.75),
                name="河川・水辺",
                text=wdf["name"].fillna("水辺"),
                hovertemplate="%{text}<extra>河川・水辺</extra>",
            ))
    except Exception:
        pass

    # 対象物件（最前面）
    traces.append(go.Scattermapbox(
        lat=[lat], lon=[lon],
        mode="markers",
        marker=dict(size=18, color="#E74C3C", opacity=1.0),
        name="対象物件",
        hovertemplate="対象物件<extra></extra>",
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=14),
        margin=dict(l=0, r=0, t=0, b=0),
        height=850,
        legend=dict(
            orientation="v", x=0.01, y=0.99,
            bgcolor="rgba(20,20,20,0.65)",
            font=dict(color="white", size=11),
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})


def _render_terrain_risk_summary(geo: tuple[float, float]) -> None:
    """標高と河川・水辺距離を簡易な地形シグナルとして表示する。"""
    lat, lon = geo
    radius_m = 1000
    rounded_lat = round(float(lat), 5)
    rounded_lon = round(float(lon), 5)

    st.markdown("---")
    st.markdown("#### 🌊 地形・水害リスク（簡易）")
    st.caption(
        "標高は国土地理院、河川・水辺は OpenStreetMap を使った簡易チェックです。"
        "自治体ハザードマップや浸水想定区域の判定ではありません。"
    )

    elevation_result: dict | None = None
    water_features: list[dict] = []
    elevation_error: str | None = None
    water_error: str | None = None

    with st.spinner("地形・水辺情報を取得中..."):
        try:
            elevation_result = _load_elevation(rounded_lat, rounded_lon)
        except TerrainSearchError as exc:
            logger.warning("標高取得失敗: %s", exc)
            elevation_error = "標高情報を取得できませんでした。"
        except Exception as exc:
            logger.exception("標高取得中に予期しないエラー")
            elevation_error = f"標高情報を取得できませんでした: {exc}"

        try:
            water_features = _load_nearby_water(rounded_lat, rounded_lon, radius_m)
        except TerrainSearchError as exc:
            logger.warning("河川・水辺取得失敗: %s", exc)
            water_error = "河川・水辺情報を取得できませんでした。"
        except Exception as exc:
            logger.exception("河川・水辺取得中に予期しないエラー")
            water_error = f"河川・水辺情報を取得できませんでした: {exc}"

    elevation_m = elevation_result.get("elevation_m") if elevation_result else None
    elevation_source = elevation_result.get("source") if elevation_result else None
    nearest_water = min(water_features, key=lambda f: f["distance_m"]) if water_features else None

    _render_summary_panel(
        None,
        [
            ("標高", f"{elevation_m:.1f} m" if elevation_m is not None else "—", None),
            ("標高区分", elevation_band(elevation_m), None),
            ("最寄り水辺", f"{nearest_water['distance_m']:.0f} m" if nearest_water else "—", None),
            ("1km内水辺", f"{len(water_features)} 件", None),
        ],
        columns=4,
    )

    if elevation_source:
        st.caption(f"標高データソース: {elevation_source}")
    if elevation_error:
        st.warning(elevation_error)
    if water_error:
        st.warning(water_error)

    if water_features:
        water_df = pd.DataFrame(water_features).sort_values("distance_m").head(10)
        water_df["distance_m"] = water_df["distance_m"].map(lambda x: f"{x:.0f}")
        water_df = water_df[["name", "type_label", "distance_m"]].rename(
            columns={"name": "名称", "type_label": "種別", "distance_m": "距離(m)"}
        )
        with st.expander("近い河川・水辺の一覧", expanded=False):
            render_html_table(water_df, [
                {"key": "名称",    "label": "名称",    "width": 140, "render": lambda v: truncate(v, 130)},
                {"key": "種別",    "label": "種別",    "width": 80,  "render": muted},
                {"key": "距離(m)", "label": "距離(m)", "width": 70,  "align": "right", "render": dist_str},
            ])
    elif not water_error:
        st.info("1km以内に OpenStreetMap 上の河川・水辺は見つかりませんでした。")

