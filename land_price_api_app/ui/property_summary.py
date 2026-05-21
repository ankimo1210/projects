"""
ui/property_summary.py
物件サマリー・ヒーローカード・土地建物試算の表示。
"""

from __future__ import annotations

import db
import pandas as pd
import streamlit as st
from config import get_logger
from property_scraper import LEGAL_LIFE_YEARS, STRUCTURE_JP, PropertyData, remaining_life

from ui.components import render_hero_card
from ui.unit_price import (
    format_man,
    format_yen_per_sqm_and_tsubo_jp,
    yen_to_man,
)

logger = get_logger(__name__)


def _render_hero_banner(prop: PropertyData, source_url: str | None = None) -> None:
    """物件の主要情報を1行に集約したヒーローカードを表示する。"""
    structure_jp = STRUCTURE_JP.get(prop.structure or "", prop.structure or "—")
    price_label = f"{prop.asking_price_yen / 1e4:,.0f} 万円" if prop.asking_price_yen else "—"
    yield_label = f"{prop.gross_yield_pct:.2f}%" if prop.gross_yield_pct is not None else "—"
    age_label = f"{prop.age_years}年" if prop.age_years is not None else "—"
    area_label = f"{prop.building_area_sqm:.0f} m²" if prop.building_area_sqm else "—"
    render_hero_card(
        title=prop.property_name or prop.property_type or "物件",
        address=prop.address or "",
        price_label=price_label,
        yield_label=yield_label,
        age_label=age_label,
        structure_label=structure_jp,
        area_label=area_label,
        source_url=source_url,
    )


def _render_property_summary(prop: PropertyData, nearby_land: pd.DataFrame) -> None:
    conf_label, _conf_type = _CONFIDENCE_LABELS.get(prop.extraction_confidence, ("?", "info"))
    platform_label = _PLATFORM_LABELS.get(prop.platform, "不明")

    llm = prop.llm_filled_fields  # LLMで補完されたフィールドセット

    def _v(field: str, val: str) -> str:
        """LLM補完フィールドなら値に * を付ける。"""
        return f"{val} *" if field in llm and val not in ("—", "") else val

    st.markdown("---")
    st.markdown(f"#### 📋 物件サマリー　{conf_label}　｜　取得元: {platform_label}")
    if llm:
        st.caption(f"\\* LLM補完: {', '.join(sorted(llm))}")

    if prop.property_name:
        st.markdown(f"### 🏢 {_v('property_name', prop.property_name)}")
    if prop.address:
        st.markdown(f"📍 {_v('address', prop.address)}")

    actual_far: float | None = (
        prop.building_area_sqm / prop.land_area_sqm * 100
        if prop.building_area_sqm and prop.land_area_sqm
        else None
    )

    structure_jp = STRUCTURE_JP.get(prop.structure or "", prop.structure or "—")
    legal = LEGAL_LIFE_YEARS.get(prop.structure or "")
    structure_label = (
        f"{structure_jp}（法定{legal}年）" if legal and structure_jp != "—" else structure_jp
    )
    build_year_label = _v("build_year_month", prop.build_year_month or "—")
    remaining_years = (
        remaining_life(prop.structure, prop.age_years) if prop.age_years is not None else None
    )
    age_label = _v("age_years", f"{prop.age_years}年" if prop.age_years is not None else "—")
    remaining_label = f"{remaining_years}年" if remaining_years is not None else "—"
    walk = f"徒歩{prop.station_walk_min}分" if prop.station_walk_min else ""
    station = f"{prop.nearest_station} {walk}".strip() if prop.nearest_station else "—"
    building_area = f"{prop.building_area_sqm:.1f} m²" if prop.building_area_sqm else "—"
    land_area = f"{prop.land_area_sqm:.1f} m²" if prop.land_area_sqm else "—"
    price_str = f"{prop.asking_price_yen:,.0f} 円" if prop.asking_price_yen else "—"
    yield_str = f"{prop.gross_yield_pct:.2f} %" if prop.gross_yield_pct is not None else "—"
    if prop.gross_rent_annual_yen:
        rent_str = f"{prop.gross_rent_annual_yen:,.0f} 円/年"
    elif prop.gross_rent_monthly_yen:
        rent_str = f"{prop.gross_rent_monthly_yen:,.0f} 円/月"
    else:
        rent_str = "—"

    if actual_far is not None:
        actual_far_value = f"{actual_far:.1f}%"
        actual_far_delta = (
            f"{actual_far / prop.legal_far_pct * 100:.0f}% 使用中" if prop.legal_far_pct else None
        )
    else:
        actual_far_value = "—"
        actual_far_delta = None

    if actual_far is not None and prop.legal_far_pct:
        surplus = prop.legal_far_pct - actual_far
        surplus_value = f"{surplus:.1f}%"
        surplus_delta = "開発余地あり" if surplus > 20 else None
    else:
        surplus_value = "—"
        surplus_delta = None

    static_metrics = [
        ("物件種別", _v("property_type", prop.property_type or "—"), None),
        ("構造", _v("structure", structure_label), None),
        ("建築年月", build_year_label, None),
        ("間取り", prop.floor_plan or "—", None),
        ("建物面積", _v("building_area_sqm", building_area), None),
        ("土地面積", _v("land_area_sqm", land_area), None),
        ("総戸数", f"{prop.num_units}戸" if prop.num_units else "—", None),
        ("階数", f"地上{prop.num_floors}階" if prop.num_floors else "—", None),
        ("最寄駅", _v("nearest_station", station), None),
        ("接道状況", prop.road_frontage or "—", None),
        ("土地権利", _v("land_rights", prop.land_rights or "—"), None),
        ("取引態様", _v("transaction_type", prop.transaction_type or "—"), None),
        ("容積率（制限）", f"{prop.legal_far_pct:.0f}%" if prop.legal_far_pct else "—", None),
        ("建蔽率（制限）", f"{prop.bcr_pct:.0f}%" if prop.bcr_pct else "—", None),
        ("実質容積率", actual_far_value, actual_far_delta),
        ("余剰容積率", surplus_value, surplus_delta),
    ]
    if prop.land_category or prop.city_planning_area:
        static_metrics.extend(
            [
                ("地目", prop.land_category or "—", None),
                ("都市計画区域", prop.city_planning_area or "—", None),
            ]
        )

    variable_metrics = [
        ("物件価格", _v("asking_price_yen", price_str), None),
        ("年間賃料", _v("gross_rent_annual_yen", rent_str), None),
        ("表面利回り", _v("gross_yield_pct", yield_str), None),
        ("築年数", age_label, None),
        ("残存耐用年数", remaining_label, None),
        ("更新日", prop.updated_date or "—", None),
        ("情報登録日", prop.listing_date or "—", None),
    ]

    left_col, right_col = st.columns(2)
    with left_col:
        _render_summary_panel("固定スペック", static_metrics, columns=2)
    with right_col:
        _render_summary_panel("変動しうる指標", variable_metrics, columns=1)

    # ── 土地/建物価格試算 ────────────────────────────────────────────
    _render_land_building_estimate(prop, nearby_land)


def _render_summary_panel(
    title: str | None,
    metrics: list[tuple[str, str, str | None]],
    *,
    columns: int = 2,
) -> None:
    """物件サマリー用のコンパクトなグリッドを描画する。"""
    if not metrics:
        return
    classes = f"property-summary-grid cols-{columns}"
    items_html: list[str] = []
    for label, value, note in metrics:
        note_html = (
            f'<div class="property-summary-item-note">{html.escape(str(note))}</div>'
            if note
            else ""
        )
        items_html.append(
            '<div class="property-summary-item">'
            f'<div class="property-summary-item-label">{html.escape(str(label))}</div>'
            f'<div class="property-summary-item-value">{html.escape(str(value))}</div>'
            f"{note_html}"
            "</div>"
        )
    panel_html = (
        '<div class="property-summary-panel">'
        f"{f'<div class="property-summary-panel-title">{html.escape(title)}</div>' if title else ''}"
        f'<div class="{classes}">'
        f"{''.join(items_html)}"
        "</div></div>"
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def _render_land_building_estimate(prop: PropertyData, nearby_land: pd.DataFrame) -> None:
    """公示地価から土地価格レンジを試算し、残余を建物価格として表示する。"""
    if not prop.land_area_sqm or not prop.asking_price_yen:
        return
    if nearby_land.empty or "price_yen_per_sqm" not in nearby_land.columns:
        return

    land_ref, land_use_label, land_ref_note = _select_land_price_reference_points(nearby_land, prop)
    prices = land_ref["price_yen_per_sqm"].dropna()
    if len(prices) == 0:
        return

    # 25〜75パーセンタイルのレンジで試算
    lo_unit = float(prices.quantile(0.25))
    hi_unit = float(prices.quantile(0.75))
    land_lo = lo_unit * prop.land_area_sqm
    land_hi = hi_unit * prop.land_area_sqm
    bld_lo = prop.asking_price_yen - land_hi
    bld_hi = prop.asking_price_yen - land_lo
    land_unit_note = (
        f"単価 {format_man(yen_to_man(lo_unit))}〜{format_man(yen_to_man(hi_unit))} 万円/m²"
    )

    st.markdown("**🏗️ 公示地価ベース 土地/建物価格試算**")
    st.caption(
        f"基準用途: {land_use_label} / "
        "近傍公示地価 "
        f"{format_yen_per_sqm_and_tsubo_jp(lo_unit)}〜{format_yen_per_sqm_and_tsubo_jp(hi_unit)}"
        f"（25〜75%ile, {len(prices)}地点）"
        f" × 土地面積 {prop.land_area_sqm:.0f} m²"
    )
    st.caption(land_ref_note)
    if bld_hi > 0:
        bld_label = f"{max(0, bld_lo) / 1e4:,.0f}〜{bld_hi / 1e4:,.0f} 万円"
        if prop.building_area_sqm and prop.building_area_sqm > 0:
            bld_unit_lo = max(0.0, bld_lo) / prop.building_area_sqm
            bld_unit_hi = bld_hi / prop.building_area_sqm
            bld_note = (
                "単価 "
                f"{format_man(yen_to_man(bld_unit_lo))}〜{format_man(yen_to_man(bld_unit_hi))} 万円/m²"
            )
        else:
            bld_note = "物件価格 − 土地価格推定値"
    else:
        bld_label = "—"
        bld_note = "土地価格が物件価格を超過"
    _render_summary_panel(
        "価格試算",
        [
            (
                "土地価格（推定）",
                f"{land_lo / 1e4:,.0f}〜{land_hi / 1e4:,.0f} 万円",
                land_unit_note,
            ),
            ("建物価格（残余）", bld_label, bld_note),
        ],
        columns=2,
    )


def _estimate_trade_land_building_split(
    trade_df: pd.DataFrame,
    land_unit_price_low_yen_per_sqm: float,
    land_unit_price_high_yen_per_sqm: float,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """近傍公示地価から取引事例の土地/建物価格を粗く分離する。"""
    if trade_df.empty:
        return trade_df.copy(), {"land_estimate_count": 0, "building_split_count": 0}

    df = trade_df.copy()
    trade_type = (
        df["trade_type"].fillna("").astype(str)
        if "trade_type" in df.columns
        else pd.Series("", index=df.index)
    )
    land_valid_mask = (
        trade_type.str.contains("宅地")
        & pd.to_numeric(df.get("trade_price_total"), errors="coerce").notna()
        & pd.to_numeric(df.get("area_sqm"), errors="coerce").notna()
    )
    building_valid_mask = land_valid_mask & trade_type.str.contains("土地と建物")
    if not land_valid_mask.any():
        return df, {"land_estimate_count": 0, "building_split_count": 0}

    df["estimated_land_price_low_yen"] = None
    df["estimated_land_price_high_yen"] = None
    df["estimated_building_price_low_yen"] = None
    df["estimated_building_price_high_yen"] = None
    df["estimated_building_price_low_per_sqm"] = None
    df["estimated_building_price_high_per_sqm"] = None

    land_area = pd.to_numeric(df.loc[land_valid_mask, "area_sqm"], errors="coerce")
    total_price = pd.to_numeric(df.loc[land_valid_mask, "trade_price_total"], errors="coerce")
    estimated_land_low = land_area * float(land_unit_price_low_yen_per_sqm)
    estimated_land_high = land_area * float(land_unit_price_high_yen_per_sqm)
    estimated_building_low = total_price - estimated_land_high
    estimated_building_high = total_price - estimated_land_low

    df.loc[land_valid_mask, "estimated_land_price_low_yen"] = estimated_land_low
    df.loc[land_valid_mask, "estimated_land_price_high_yen"] = estimated_land_high
    df.loc[building_valid_mask, "estimated_building_price_low_yen"] = estimated_building_low.loc[
        building_valid_mask
    ]
    df.loc[building_valid_mask, "estimated_building_price_high_yen"] = estimated_building_high.loc[
        building_valid_mask
    ]

    if "total_floor_area_sqm" in df.columns:
        total_floor = pd.to_numeric(
            df.loc[building_valid_mask, "total_floor_area_sqm"], errors="coerce"
        )
        floor_mask = total_floor.notna() & (total_floor > 0)
        low_unit = (
            estimated_building_low.loc[building_valid_mask].loc[floor_mask]
            / total_floor.loc[floor_mask]
        )
        high_unit = (
            estimated_building_high.loc[building_valid_mask].loc[floor_mask]
            / total_floor.loc[floor_mask]
        )
        df.loc[low_unit.index, "estimated_building_price_low_per_sqm"] = low_unit
        df.loc[high_unit.index, "estimated_building_price_high_per_sqm"] = high_unit

    return df, {
        "land_estimate_count": int(land_valid_mask.sum()),
        "building_split_count": int(building_valid_mask.sum()),
    }


def _fallback_trade_by_city(
    conn,
    address: str,
    trade_years: tuple,
) -> pd.DataFrame:
    """
    住所文字列から都道府県・市区町村を抽出して取引価格を取得する。
    lat/lon が NULL で近傍検索が空の場合のフォールバック。
    """
    # 都道府県を抽出
    pref_match = re.match(r"(.+?[都道府県])", address)
    pref = pref_match.group(1) if pref_match else None

    # 市区町村を抽出（都道府県の後）
    city_match = re.match(r".+?[都道府県](.+?[市区町村])", address)
    city = city_match.group(1) if city_match else None

    if not pref and not city:
        return pd.DataFrame()

    year = trade_years[0] if trade_years else None
    return db.read_trade_prices_by_city(
        conn, city_name=city, prefecture_name=pref, year=year, limit=50
    )
