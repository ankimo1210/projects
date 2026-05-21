"""
ui/property_tab.py
物件URL → 即時分析タブ。

URLを貼り付けると:
1. 正規表現 + Ollama で物件データを抽出
2. 国土地理院APIでジオコーディング
3. 近傍の公示地価・取引価格と比較
4. 投資シミュレーション（IRR・CF表）を表示
"""
import re
import html
from typing import Optional

import pandas as pd
import streamlit as st

import db
from analytics import find_nearby_points
from config import get_logger
from facility_sources import (
    FacilitySearchError,
    find_nearby_facility_groups,
    summarize_facility_groups,
)
from geocoder import GeocodingError, GeocodingResult, geocode_address
from property_persistence import listing_row_to_property, property_to_listing_row
from property_scraper import PropertyData, ScrapingError, extract_property_data, fetch_property_html
from property_state import PropertyAnalysisState
from ui.table import render_html_table, plain, muted, truncate, gap_bar, signed_pct_str, num_str, dist_str
from ui.rent_benchmark_panel import render_rent_benchmark_panel
from valuation import build_valuation_result, score_location_features
# サブモジュール
from ui.property_summary import (
    _render_hero_banner, _render_property_summary, _render_summary_panel,
    _fallback_trade_by_city, _land_use_candidates_for_property,
)
from ui.property_nearby import (
    _load_nearby_land, _load_nearby_trade,
    _render_nearby_prices, _render_nearby_listings,
    _render_nearby_facility_summary, _render_location_map, _render_terrain_risk_summary,
    _PROPERTY_FACILITY_CATEGORIES,
)
from ui.property_investment import (
    _render_investment_metrics, _render_simulation,
    _render_sensitivity_heatmap, _render_irr_by_period, _render_param_editor,
    _build_sim_params, _SIM_AVAILABLE, run_full_analysis,
)

logger = get_logger(__name__)
_FEATURE_VERSION = 1

# property_investment.py から再エクスポートされた定数・関数
from ui.property_investment import _SIM_DEFAULTS, _DEFAULT_LAND_RATIO

_RESIDENTIAL_PROPERTY_KEYWORDS = ("アパート", "マンション", "戸建", "住宅", "土地")
_COMMERCIAL_PROPERTY_KEYWORDS = ("店舗", "事務所", "ビル", "商業")

_CONFIDENCE_LABELS = {
    "high": ("✅ 高信頼度", "success"),
    "partial": ("⚠️ 部分抽出", "warning"),
    "low": ("❌ 低信頼度", "error"),
}

_PLATFORM_LABELS = {
    "rakumachi": "楽待",
    "kenbiya": "健美家",
    "unknown": "不明",
}


# --------------------------------------------------------------------------
# メインエントリポイント
# --------------------------------------------------------------------------

def render_property_tab(conn, filters: dict) -> None:
    st.markdown("### 🏢 物件URL → 即時分析")
    st.caption("楽待・健美家などの物件ページURLを貼り付けると、周辺地価との比較と投資シミュレーションを表示します。")

    # ── URL 入力 ──────────────────────────────────────────────
    col_url, col_btn = st.columns([5, 1])
    with col_url:
        url = st.text_input(
            "物件URL",
            placeholder="https://www.rakumachi.jp/syuunyuubukken/... または https://www.kenbiya.com/...",
            key="prop_url_input",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze_clicked = st.button("分析開始", type="primary", use_container_width=True)

    if analyze_clicked and url.strip():
        _run_analysis_pipeline(conn, url.strip(), filters)

    # ── 保存済み物件のロード ──────────────────────────────────
    _render_saved_property_loader(conn)

    # ── 結果表示 ────────────────────────────────────────────────
    state = PropertyAnalysisState.load()
    prop: Optional[PropertyData] = state.prop
    geo: Optional[tuple] = state.geo
    city_code: Optional[str] = state.city_code

    if prop is None:
        st.info("URLを入力して「分析開始」を押すと、物件情報・近傍地価・投資シミュレーションを表示します。")
        return

    # 近傍地価を先にロード（サマリー内の土地/建物価格試算に使う）
    nearby_land = pd.DataFrame()
    nearby_trade = pd.DataFrame()
    radius_used = 1000
    radius_used_trade: int | str = 1000
    _RADIUS_STEPS = [1000, 2000, 3000, 4000, 5000]
    _MIN_POINTS = 3
    if geo is not None:
        lat, lon = geo
        available_years = db.get_available_years(conn)
        latest_year = available_years[0] if available_years else 2025
        trade_years_in_db = db.get_trade_available_years(conn)
        trade_years = tuple(sorted(set(trade_years_in_db[:2]), reverse=True)) if trade_years_in_db else (latest_year,)

        land_all = _load_nearby_land(conn, latest_year)
        trade_all = _load_nearby_trade(conn, trade_years)

        for r in _RADIUS_STEPS:
            nearby_land = find_nearby_points(land_all, lon, lat, radius_m=r)
            radius_used = r
            if len(nearby_land) >= _MIN_POINTS:
                break

        for r in _RADIUS_STEPS:
            nearby_trade = find_nearby_points(trade_all, lon, lat, radius_m=r)
            radius_used_trade = r
            if len(nearby_trade) >= _MIN_POINTS:
                break

        if nearby_trade.empty and prop.address:
            nearby_trade = _fallback_trade_by_city(conn, prop.address, trade_years)
            radius_used_trade = "市区町村"

    # ── ヒーローカード ────────────────────────────────────────────────
    _render_hero_banner(prop, state.source_url)

    # ── DB永続化（副作用のみ、表示は下のタブで行う） ────────────────
    persisted = _persist_property_analysis(conn, prop, geo, city_code, nearby_land, nearby_trade, state)
    if persisted:
        state.persisted_listing_id = persisted.get("listing_id")
        state.save()

    # ── タブ構成 ─────────────────────────────────────────────────────
    tab_summary, tab_finance, tab_area, tab_risk = st.tabs(
        ["📋 物件概要", "💹 収支シミュ", "🗺 周辺環境", "⚠️ リスク"]
    )

    with tab_summary:
        _render_property_summary(prop, nearby_land)
        _render_persistence_status(persisted)

    with tab_finance:
        _render_investment_metrics(prop)
        _render_property_rent_benchmark(conn, prop, city_code)

        if not _SIM_AVAILABLE:
            st.warning("フル投資シミュレーションエンジンが見つかりません。簡易計算で感度分析を表示します。")
            with st.expander("📊 金利×LTV 感度ヒートマップ（簡易）", expanded=True):
                _render_sensitivity_heatmap(prop)
            with st.expander("📈 保有年数別IRR（簡易）", expanded=True):
                _render_irr_by_period(prop)
        else:
            st.markdown("---")
            st.markdown("#### 💹 投資シミュレーション")
            base_params = _build_sim_params(prop, nearby_land, overrides={})
            with st.expander("⚙️ シミュレーションパラメータを確認・調整", expanded=False):
                overrides = _render_param_editor(base_params)
            params = _build_sim_params(prop, nearby_land, overrides=overrides)

            if prop.asking_price_yen:
                try:
                    results = run_full_analysis(params)
                    _render_simulation(results, show_heading=False)
                except Exception as exc:
                    logger.exception("シミュレーション失敗")
                    st.error(f"シミュレーションに失敗しました: {exc}")

            with st.expander("📊 金利×LTV 感度ヒートマップ", expanded=False):
                _render_sensitivity_heatmap(prop, sim_params=params)
            with st.expander("📈 保有年数別IRRグラフ", expanded=False):
                _render_irr_by_period(prop, sim_params=params)

    with tab_area:
        if geo is not None:
            # 人口・世帯カード
            if city_code:
                pop_data = compute_population_trend(conn, city_code)
                render_population_card(pop_data)
                st.markdown("")

            _render_nearby_prices(nearby_land, nearby_trade, prop, radius_used, radius_used_trade, conn, city_code)
            current_lid = state.persisted_listing_id
            _render_nearby_listings(conn, geo, current_lid)
            _render_location_map(geo, nearby_land, nearby_trade, conn=conn)
            _render_nearby_facility_summary(geo)
        else:
            st.info("住所が取得できなかったため、周辺環境データを表示できません。")

    with tab_risk:
        if geo is not None:
            _render_terrain_risk_summary(geo)
        else:
            st.info("住所が取得できなかったため、リスクデータを表示できません。")


# --------------------------------------------------------------------------
# パイプライン実行
# --------------------------------------------------------------------------

def _run_analysis_pipeline(conn, url: str, filters: dict) -> None:
    """HTML取得 → 抽出 → ジオコーディングを順に実行してセッションに保存する。"""
    with st.status("物件情報を取得中...", expanded=True) as status:
        # Step 1: HTML取得
        st.write("📥 ページを取得中...")
        try:
            html = fetch_property_html(url)
        except ScrapingError as exc:
            status.update(label="取得失敗", state="error")
            st.error(f"物件ページの取得に失敗しました: {exc}")
            _render_fallback_form()
            return

        # Step 2: 物件情報抽出
        st.write("🤖 物件情報を抽出中（正規表現 + Ollama）...")
        try:
            prop = extract_property_data(html, url)
        except Exception as exc:
            status.update(label="抽出失敗", state="error")
            st.error(f"物件情報の抽出に失敗しました: {exc}")
            _render_fallback_form()
            return

        if prop.asking_price_yen is None:
            status.update(label="価格未取得", state="error")
            st.error("物件価格を抽出できませんでした。URLを確認するか手動入力してください。")
            _render_fallback_form()
            return

        if prop.extraction_confidence == "low":
            st.warning("一部の項目が抽出できませんでした。デフォルト値で補完します。シミュレーションパラメータをご確認ください。")

        state = PropertyAnalysisState(source_url=url)
        state.set_property(prop)

        # Step 3: ジオコーディング
        if prop.address:
            st.write(f"📍 住所を変換中: {prop.address}")
            try:
                geo_result: GeocodingResult = geocode_address(prop.address)
                state.set_property(prop, geo=(geo_result.lat, geo_result.lon), city_code=geo_result.city_code)
                st.write(f"✅ 座標取得: ({geo_result.lat:.5f}, {geo_result.lon:.5f})")
            except GeocodingError as exc:
                st.warning(f"住所のジオコーディングに失敗しました: {exc} — 近傍地価比較はスキップします。")
        else:
            st.warning("住所が抽出できませんでした。近傍地価比較はスキップします。")

        status.update(label="取得完了", state="complete")


def _persist_property_analysis(
    conn,
    prop: PropertyData,
    geo: Optional[tuple[float, float]],
    city_code: Optional[str],
    nearby_land: pd.DataFrame,
    nearby_trade: pd.DataFrame,
    state: "PropertyAnalysisState | None" = None,
) -> dict | None:
    """掲載物件・座標特徴量・日次スナップショットを保存する。"""
    source_url = state.source_url if state else ""
    if not source_url:
        return None

    rounded_lat = round(float(geo[0]), 5) if geo is not None else None
    rounded_lon = round(float(geo[1]), 5) if geo is not None else None
    location_key = db.make_location_key(rounded_lat, rounded_lon) if geo is not None else None

    region_label = state.region_label if state else None
    listing_row = property_to_listing_row(prop, source_url, city_code, rounded_lat, rounded_lon, region_label)
    listing_id = db.upsert_listing_master(conn, listing_row)
    if geo is None or location_key is None:
        return {"listing_id": listing_id, "location_key": None, "partial": True}

    try:
        grouped = _load_nearby_facility_groups(tuple(_PROPERTY_FACILITY_CATEGORIES), rounded_lat, rounded_lon, 1000)
        elevation_result = _load_elevation(rounded_lat, rounded_lon)
        water_features = _load_nearby_water(rounded_lat, rounded_lon, 1000)

        location_row = _build_location_feature_row(
            location_key=location_key,
            lat=rounded_lat,
            lon=rounded_lon,
            city_code=city_code,
            grouped=grouped,
            elevation_result=elevation_result,
            water_features=water_features,
        )
        db.upsert_location_features(conn, location_row)

        # 個別 POI を保存（地図表示・バッチ特徴量付与に再利用）
        all_pois = [
            poi | {"category": cat}
            for cat, pois in grouped.items()
            for poi in pois
        ]
        db.upsert_facility_pois(conn, location_key, all_pois)
        db.upsert_water_features(conn, location_key, water_features)

        snapshot_row = _build_listing_feature_snapshot_row(
            listing_id=listing_id,
            location_key=location_key,
            prop=prop,
            nearby_land=nearby_land,
            nearby_trade=nearby_trade,
        )
        db.upsert_listing_feature_snapshot(conn, snapshot_row)
        valuation_row = build_valuation_result(listing_row, snapshot_row, location_row, valuation_version=_FEATURE_VERSION)
        db.upsert_valuation_result(conn, valuation_row)
    except (FacilitySearchError, TerrainSearchError) as exc:
        logger.warning("掲載物件特徴量の保存を一部スキップ: %s", exc)
        return {
            "listing_id": listing_id,
            "location_key": location_key,
            "partial": True,
        }
    except Exception:
        logger.exception("掲載物件特徴量の保存に失敗")
        return {
            "listing_id": listing_id,
            "location_key": location_key,
            "partial": True,
        }
    return {
        "listing_id": listing_id,
        "location_key": location_key,
        "partial": False,
        "valuation": valuation_row,
    }


def _render_property_rent_benchmark(conn, prop: PropertyData, city_code: Optional[str]) -> None:
    state = PropertyAnalysisState.load()
    source_url = state.source_url or ""
    listing_id = state.persisted_listing_id

    render_rent_benchmark_panel(
        conn,
        {
            "listing_id": listing_id,
            "city_code": city_code,
            "address": prop.address,
            "asking_price_yen": prop.asking_price_yen,
            "property_type": prop.property_type,
            "structure": prop.structure,
            "building_area_sqm": prop.building_area_sqm,
            "num_units": prop.num_units,
            "gross_rent_monthly_yen": prop.gross_rent_monthly_yen,
            "gross_rent_annual_yen": prop.gross_rent_annual_yen,
        },
        title_level=4,
    )


def _build_location_feature_row(
    *,
    location_key: str,
    lat: float,
    lon: float,
    city_code: Optional[str],
    grouped: dict[str, list[dict]],
    elevation_result: dict,
    water_features: list[dict],
) -> dict:
    facility_summary = summarize_facility_groups(grouped, _PROPERTY_FACILITY_CATEGORIES)
    terrain_summary = summarize_terrain_features(elevation_result, water_features, radius_m=1000)
    hazard_summary = summarize_hazard_risk(lat=lat, lon=lon)
    score_summary = score_location_features({**facility_summary, **terrain_summary, **hazard_summary})
    return {
        "location_key": location_key,
        "lat": lat,
        "lon": lon,
        "city_code": city_code,
        "feature_version": _FEATURE_VERSION,
        "facility_radius_m": 1000,
        "terrain_radius_m": 1000,
        **facility_summary,
        **terrain_summary,
        **score_summary,
        **hazard_summary,
    }


def _build_listing_feature_snapshot_row(
    *,
    listing_id: str,
    location_key: str,
    prop: PropertyData,
    nearby_land: pd.DataFrame,
    nearby_trade: pd.DataFrame,
) -> dict:
    filtered_land, _, _ = _select_land_price_reference_points(nearby_land, prop)
    land_ref = filtered_land if not filtered_land.empty else nearby_land
    land_p25 = float(land_ref["price_yen_per_sqm"].quantile(0.25)) if not land_ref.empty else None
    land_p50 = float(land_ref["price_yen_per_sqm"].median()) if not land_ref.empty else None
    land_p75 = float(land_ref["price_yen_per_sqm"].quantile(0.75)) if not land_ref.empty else None
    trade_median = float(nearby_trade["trade_price_per_sqm"].median()) if not nearby_trade.empty else None

    unit_area_basis = None
    unit_area_sqm = None
    if prop.land_area_sqm:
        unit_area_basis = "land"
        unit_area_sqm = float(prop.land_area_sqm)
    elif prop.building_area_sqm:
        unit_area_basis = "building"
        unit_area_sqm = float(prop.building_area_sqm)

    unit_price_yen_per_sqm = None
    if prop.asking_price_yen is not None and unit_area_sqm and unit_area_sqm > 0:
        unit_price_yen_per_sqm = prop.asking_price_yen / unit_area_sqm

    land_price_low = land_price_high = None
    building_residual_low = building_residual_high = None
    if prop.land_area_sqm and land_p25 is not None and land_p75 is not None:
        land_price_low = land_p25 * prop.land_area_sqm
        land_price_high = land_p75 * prop.land_area_sqm
        if prop.asking_price_yen is not None:
            building_residual_low = prop.asking_price_yen - land_price_high
            building_residual_high = prop.asking_price_yen - land_price_low

    public_notice_gap_pct = None
    if unit_price_yen_per_sqm is not None and land_p50 is not None and land_p50 > 0:
        public_notice_gap_pct = (unit_price_yen_per_sqm / land_p50 - 1.0) * 100.0

    trade_gap_pct = None
    if unit_price_yen_per_sqm is not None and trade_median is not None and trade_median > 0:
        trade_gap_pct = (unit_price_yen_per_sqm / trade_median - 1.0) * 100.0

    return {
        "listing_id": listing_id,
        "snapshot_date": date.today(),
        "location_key": location_key,
        "feature_version": _FEATURE_VERSION,
        "asking_price_yen": prop.asking_price_yen,
        "unit_area_basis": unit_area_basis,
        "unit_area_sqm": unit_area_sqm,
        "unit_price_yen_per_sqm": unit_price_yen_per_sqm,
        "nearby_land_count": int(len(land_ref)),
        "nearby_trade_count": int(len(nearby_trade)),
        "land_unit_price_p25_yen_per_sqm": land_p25,
        "land_unit_price_p75_yen_per_sqm": land_p75,
        "trade_unit_price_median_yen_per_sqm": trade_median,
        "public_notice_gap_pct": public_notice_gap_pct,
        "trade_gap_pct": trade_gap_pct,
        "land_price_estimate_low_yen": land_price_low,
        "land_price_estimate_high_yen": land_price_high,
        "building_residual_low_yen": building_residual_low,
        "building_residual_high_yen": building_residual_high,
    }


def _land_use_candidates_for_property(prop: PropertyData) -> list[str]:
    property_type = (prop.property_type or "").strip()
    if any(keyword in property_type for keyword in _COMMERCIAL_PROPERTY_KEYWORDS):
        return ["商業地"]
    if any(keyword in property_type for keyword in _RESIDENTIAL_PROPERTY_KEYWORDS):
        return ["住宅地"]
    return []


def _select_land_price_reference_points(
    nearby_land: pd.DataFrame,
    prop: PropertyData,
    *,
    min_points: int = 3,
) -> tuple[pd.DataFrame, str, str]:
    """物件種別に応じて公示地価の用途を絞り込む。"""
    if nearby_land.empty or "use_category_name" not in nearby_land.columns:
        return nearby_land, "全用途", "用途情報なし"

    candidates = _land_use_candidates_for_property(prop)
    if not candidates:
        return nearby_land, "全用途", "物件種別から用途を推定できないため全用途を使用"

    use_col = nearby_land["use_category_name"].fillna("").astype(str)
    mask = pd.Series(False, index=nearby_land.index)
    for candidate in candidates:
        mask = mask | use_col.str.contains(candidate)

    filtered = nearby_land.loc[mask].copy()
    if len(filtered) >= min_points:
        return filtered, " / ".join(candidates), f"{len(filtered)}地点"
    return nearby_land, "全用途", f"{' / '.join(candidates)} の地点数不足（{len(filtered)}件）のため全用途へフォールバック"


def _render_persistence_status(persisted: dict | None) -> None:
    if not persisted:
        return
    label = "保存済み" if not persisted.get("partial") else "一部保存"
    if persisted.get("location_key"):
        detail = f"listing_id={persisted['listing_id']} / location_key={persisted['location_key']}"
    else:
        detail = f"listing_id={persisted['listing_id']}"
    st.caption(f"{label}特徴量: {detail}")
    valuation = persisted.get("valuation")
    if valuation:
        _render_summary_panel(
            "保存済み評価",
            [
                ("簡易判定", valuation.get("cheap_or_expensive") or "—", None),
                (
                    "相場差",
                    f"{valuation['adjusted_gap_pct']:+.1f}%"
                    if valuation.get("adjusted_gap_pct") is not None else "—",
                    None,
                ),
                ("信頼度", valuation.get("confidence") or "—", None),
            ],
            columns=3,
        )
        reasons = render_reason_texts(valuation.get("reasons_json"))
        if reasons:
            st.caption(" / ".join(reasons[:3]))


# --------------------------------------------------------------------------
# 表示セクション
# --------------------------------------------------------------------------



@st.cache_data(ttl=60, show_spinner=False)
def _load_saved_listings(_conn) -> pd.DataFrame:
    return db.list_saved_listings(_conn)


def _render_saved_property_loader(conn) -> None:
    """保存済み物件の選択・ロードUIを表示する。"""
    saved = _load_saved_listings(conn)
    if saved.empty:
        return

    with st.expander(f"📂 保存済み物件をロード（{len(saved)}件）", expanded=False):
        # 表示ラベルの生成
        def _nonan(v) -> Optional[str]:
            """NaN・None を None に変換して返す。"""
            if v is None:
                return None
            try:
                if v != v:  # NaN check
                    return None
            except TypeError:
                pass
            s = str(v).strip()
            return s if s and s != "nan" else None

        def _label(row) -> str:
            name = _nonan(row.get("property_name")) or _nonan(row.get("address")) or "（名称不明）"
            ask = row.get("asking_price_yen")
            price = f'{float(ask)/1e4:,.0f}万円' if _nonan(ask) else "—"
            yld_v = row.get("gross_yield_pct")
            yld = f'{float(yld_v):.1f}%' if _nonan(yld_v) else "—"
            ptype = _nonan(row.get("property_type")) or ""
            age_v = row.get("age_years")
            age = f'築{int(float(age_v))}年' if _nonan(age_v) else ""
            parts = [p for p in [ptype, age] if p]
            detail = " / ".join(parts)
            return f"{name}　{price}　利回り{yld}　{detail}"

        options = {_label(row): row for _, row in saved.iterrows()}
        selected_label = st.selectbox(
            "物件を選択",
            options=list(options.keys()),
            index=None,
            placeholder="保存済み物件を選択...",
            key="saved_listing_select",
            label_visibility="collapsed",
        )

        if selected_label and st.button("この物件をロード", type="secondary", key="load_saved_btn"):
            row = options[selected_label]
            prop = listing_row_to_property(row)
            lat = row.get("lat")
            lon = row.get("lon")
            geo = (float(lat), float(lon)) if lat is not None and lon is not None else None
            city_code = row.get("city_code")

            state = PropertyAnalysisState(
                source_url=row.get("source_url") or "",
                region_label=row.get("region_label"),
            )
            state.set_property(prop, geo=geo, city_code=city_code)
            st.rerun()





