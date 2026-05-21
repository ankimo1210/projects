"""
ui/rent_benchmark_panel.py
地域賃料ベンチマークの共通表示。
"""

from __future__ import annotations

from typing import Any

import db
import pandas as pd
import streamlit as st
from utils import safe_float as _num
from utils import safe_str

_RENTABLE_EFFICIENCY_BY_STRUCTURE: dict[str, tuple[float, float]] = {
    "wood": (0.90, 0.95),
    "wood_mortar": (0.88, 0.93),
    "steel": (0.80, 0.90),
    "rc": (0.75, 0.88),
    "src": (0.75, 0.88),
}

_FLOOR_AREA_ASSUMPTIONS_SQM: dict[str, tuple[int, int]] = {
    "ワンルーム": (18, 25),
    "1K/1DK": (22, 35),
    "1LDK/2K/2DK": (35, 50),
    "2LDK/3K/3DK": (50, 70),
    "3LDK/4K～": (70, 95),
}


def render_rent_benchmark_panel(conn, listing: dict[str, Any], *, title_level: int = 4) -> None:
    """e-Stat と保存済み掲載物件から地域賃料ベンチマークを表示する。"""
    benchmark = build_rent_benchmark(conn, listing)
    if not benchmark["has_signal"]:
        return

    heading = "#" * max(1, min(title_level, 6))
    st.markdown("---")
    st.markdown(f"{heading} 🏠 地域賃料ベンチマーク")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "e-Stat市区町村平均",
        _fmt_yen_sqm(benchmark["estat_rent_per_sqm"]),
        _fmt_monthly_estimate(benchmark["estat_monthly_yen"]),
        help="住宅・土地統計調査の延べ面積1m²当たり家賃。民営借家を優先し、なければ総数を使います。",
    )
    c2.metric(
        "自前掲載中央値",
        _fmt_yen_sqm(benchmark["own_median_rent_per_sqm"]),
        f"n={benchmark['own_sample_count']}" if benchmark["own_sample_count"] else None,
        help="保存済み掲載物件の同一市区町村・同一物件種別を優先。3件未満なら同一市区町村全体を使います。",
    )
    c3.metric(
        "物件掲載賃料",
        _fmt_yen_sqm(benchmark["listing_rent_per_sqm"]),
        _fmt_monthly_estimate(benchmark["listing_monthly_yen"]),
        help="掲載ページから取得した月額/年額賃料を建物面積で割った値です。",
    )
    c4.metric(
        "平均との差",
        _fmt_gap(benchmark["gap_vs_best_pct"]),
        benchmark["confidence"],
        help="比較可能な基準値に対する物件掲載賃料の乖離率。自前中央値を優先し、なければe-Stat平均と比較します。",
    )

    st.caption(benchmark["note"])
    render_suumo_income_property_rent_panel(conn, listing, title_level=title_level)


def render_suumo_income_property_rent_panel(
    conn, listing: dict[str, Any], *, title_level: int = 4
) -> None:
    """延床×賃貸効率ベースでSUUMO賃料妥当性を表示する。"""
    benchmark = build_suumo_income_property_rent_benchmark(conn, listing)
    if not benchmark["has_signal"]:
        return

    heading = "#" * max(1, min(title_level, 6))
    st.markdown(f"{heading} 🏢 SUUMO賃料妥当性（一棟推定）")
    st.info(
        "部屋ミックスが不明なため、延床面積×構造別の賃貸効率から賃貸可能面積を推定し、"
        "平均戸当たり面積に近いSUUMO間取り帯の㎡単価で相場賃料を概算しています。"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("賃貸効率", benchmark["efficiency_label"], benchmark["structure_label"])
    c2.metric(
        "推定賃貸可能面積",
        benchmark["rentable_area_label"],
        f"延床 {benchmark['building_area_label']}",
    )
    c3.metric("採用間取り帯", benchmark["floor_plan_bucket"], benchmark["avg_unit_area_label"])
    c4.metric("SUUMO㎡単価", benchmark["suumo_unit_price_label"], benchmark["suumo_source_label"])

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("推定相場月額賃料", benchmark["market_monthly_label"])
    r2.metric("推定相場年収", benchmark["market_annual_label"])
    r3.metric("掲載賃料との比較", benchmark["listed_gap_label"], benchmark["listed_annual_label"])
    r4.metric("年収改善余地", benchmark["upside_annual_label"], benchmark["yield_upside_label"])

    st.markdown(
        f'<div style="padding:10px 12px;border-radius:8px;border:1px solid {benchmark["assessment_border"]};'
        f'background:{benchmark["assessment_bg"]};color:{benchmark["assessment_color"]};font-weight:700">'
        f"{benchmark['assessment_label']}</div>",
        unsafe_allow_html=True,
    )

    st.caption(benchmark["note"])


def build_suumo_income_property_rent_benchmark(conn, listing: dict[str, Any]) -> dict[str, Any]:
    city_name = _city_name_for_listing(conn, listing)
    if not city_name:
        return {"has_signal": False}

    building_area = _num(listing.get("building_area_sqm"))
    if building_area is None or building_area <= 0:
        return {"has_signal": False}

    structure = _normalize_structure(_text_or_none(listing.get("structure")))
    eff_low, eff_high = _rentable_efficiency_range(
        structure, _text_or_none(listing.get("property_type"))
    )
    rentable_low = building_area * eff_low
    rentable_high = building_area * eff_high

    unit_count = _num(listing.get("num_units"))
    avg_unit_area = (
        ((rentable_low + rentable_high) / 2.0) / unit_count
        if unit_count and unit_count > 0
        else None
    )
    floor_plan_bucket = _floor_plan_bucket_from_area(avg_unit_area)
    if floor_plan_bucket is None:
        floor_plan_bucket = _fallback_floor_plan_bucket(_text_or_none(listing.get("property_type")))

    suumo = _find_suumo_rent_row(conn, city_name, _suumo_property_type(listing), floor_plan_bucket)
    if suumo is None:
        return {"has_signal": False}

    monthly_rent = _num(suumo.get("monthly_rent_yen"))
    if monthly_rent is None or monthly_rent <= 0:
        return {"has_signal": False}

    area_min, area_max = _FLOOR_AREA_ASSUMPTIONS_SQM[floor_plan_bucket]
    unit_price_low = monthly_rent / area_max
    unit_price_high = monthly_rent / area_min
    market_monthly_low = rentable_low * unit_price_low
    market_monthly_high = rentable_high * unit_price_high
    market_annual_low = market_monthly_low * 12
    market_annual_high = market_monthly_high * 12

    listed_monthly = _listing_monthly_rent(listing)
    listed_annual = listed_monthly * 12 if listed_monthly is not None else None
    gap_low = (
        ((listed_annual / market_annual_high) - 1.0) * 100
        if listed_annual and market_annual_high > 0
        else None
    )
    gap_high = (
        ((listed_annual / market_annual_low) - 1.0) * 100
        if listed_annual and market_annual_low > 0
        else None
    )
    market_annual_mid = (market_annual_low + market_annual_high) / 2.0
    upside_annual = market_annual_mid - listed_annual if listed_annual is not None else None
    asking_price = _num(listing.get("asking_price_yen"))
    yield_upside_pct = (
        (upside_annual / asking_price * 100.0)
        if upside_annual is not None and asking_price and asking_price > 0
        else None
    )
    assessment = _rent_assessment(gap_low, gap_high, upside_annual)

    source_date = suumo.get("updated_date")
    source_label = f"{city_name} / {suumo.get('property_type_label')} / {floor_plan_bucket}"
    if source_date is not None and not pd.isna(source_date):
        source_label += f" / {source_date}"

    note_parts = [
        f"賃貸効率前提: {eff_low:.0%}〜{eff_high:.0%}",
        f"SUUMO月額相場: {monthly_rent / 1e4:,.1f}万円",
        f"代表面積前提: {area_min}〜{area_max}㎡",
    ]
    if avg_unit_area is None:
        note_parts.append("総戸数がないため物件種別から間取り帯を仮定")

    return {
        "has_signal": True,
        "efficiency_label": f"{eff_low:.0%}〜{eff_high:.0%}",
        "structure_label": structure or _text_or_none(listing.get("structure")) or "構造不明",
        "building_area_label": f"{building_area:,.1f}㎡",
        "rentable_area_label": f"{rentable_low:,.1f}〜{rentable_high:,.1f}㎡",
        "floor_plan_bucket": floor_plan_bucket,
        "avg_unit_area_label": f"平均 {avg_unit_area:.1f}㎡/戸" if avg_unit_area else "戸数不明",
        "suumo_unit_price_label": f"{unit_price_low:,.0f}〜{unit_price_high:,.0f}円/m²",
        "suumo_source_label": source_label,
        "market_monthly_label": f"{market_monthly_low / 1e4:,.1f}〜{market_monthly_high / 1e4:,.1f}万円",
        "market_annual_label": f"{market_annual_low / 1e4:,.0f}〜{market_annual_high / 1e4:,.0f}万円",
        "listed_gap_label": _fmt_range_gap(gap_low, gap_high),
        "listed_annual_label": f"掲載 {listed_annual / 1e4:,.0f}万円/年"
        if listed_annual
        else "掲載賃料なし",
        "upside_annual_label": _fmt_annual_upside(upside_annual),
        "yield_upside_label": f"利回り換算 {yield_upside_pct:+.2f}pt"
        if yield_upside_pct is not None
        else None,
        "assessment_label": assessment["label"],
        "assessment_color": assessment["color"],
        "assessment_bg": assessment["bg"],
        "assessment_border": assessment["border"],
        "note": " / ".join(note_parts),
    }


def build_rent_benchmark(conn, listing: dict[str, Any]) -> dict[str, Any]:
    city_code = _text_or_none(listing.get("city_code"))
    area = _num(listing.get("building_area_sqm"))
    property_type = _text_or_none(listing.get("property_type"))
    listing_id = _text_or_none(listing.get("listing_id"))

    listing_monthly = _listing_monthly_rent(listing)
    listing_rent_sqm = (
        listing_monthly / area if listing_monthly is not None and area and area > 0 else None
    )

    estat_rent_sqm = None
    estat_monthly = None
    estat_source = None
    if city_code:
        rent_df = db.get_rent_market(conn, city_code)
        if not rent_df.empty:
            estat_row = _pick_estat_rent_row(rent_df)
            if estat_row is not None:
                estat_rent_sqm = _num(estat_row.get("rent_per_sqm"))
                estat_source = (
                    f"e-Stat {int(estat_row['survey_year'])}年/{estat_row['ownership_type']}"
                )
                if estat_rent_sqm is not None and area and area > 0:
                    estat_monthly = estat_rent_sqm * area

    own = _own_listing_rent_stats(
        conn, city_code, property_type=property_type, exclude_listing_id=listing_id
    )
    own_median = own["median_rent_per_sqm"]
    own_monthly = own_median * area if own_median is not None and area and area > 0 else None

    best_base = own_median if own_median is not None else estat_rent_sqm
    gap = (
        ((listing_rent_sqm / best_base) - 1.0) * 100.0
        if listing_rent_sqm and best_base and best_base > 0
        else None
    )

    signal_count = sum(
        value is not None for value in [estat_rent_sqm, own_median, listing_rent_sqm]
    )
    if estat_rent_sqm is not None and own["sample_count"] >= 5 and listing_rent_sqm is not None:
        confidence = "high"
    elif signal_count >= 2 or own["sample_count"] >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    notes = []
    if estat_source:
        notes.append(f"公的統計: {estat_source}")
    if own["sample_count"]:
        scope = "同一市区町村・同一種別" if own["scope"] == "city_property_type" else "同一市区町村"
        notes.append(f"自前掲載: {scope} n={own['sample_count']}")
    if area is None or area <= 0:
        notes.append("建物面積がないため月額換算は一部非表示")
    if listing_rent_sqm is None:
        notes.append("掲載賃料がないため平均との差は未計算")

    return {
        "has_signal": signal_count > 0 or own["sample_count"] > 0,
        "city_code": city_code,
        "building_area_sqm": area,
        "estat_rent_per_sqm": estat_rent_sqm,
        "estat_monthly_yen": estat_monthly,
        "own_median_rent_per_sqm": own_median,
        "own_monthly_yen": own_monthly,
        "own_sample_count": own["sample_count"],
        "listing_rent_per_sqm": listing_rent_sqm,
        "listing_monthly_yen": listing_monthly,
        "gap_vs_best_pct": gap,
        "confidence": confidence,
        "note": " / ".join(notes) if notes else "利用できる賃料データが限られています。",
    }


def _pick_estat_rent_row(rent_df: pd.DataFrame) -> dict[str, Any] | None:
    for ownership_type in ["private", "total"]:
        df = rent_df[rent_df["ownership_type"] == ownership_type]
        if not df.empty:
            return df.sort_values("survey_year", ascending=False).iloc[0].to_dict()
    if rent_df.empty:
        return None
    return rent_df.sort_values("survey_year", ascending=False).iloc[0].to_dict()


def _own_listing_rent_stats(
    conn,
    city_code: str | None,
    *,
    property_type: str | None,
    exclude_listing_id: str | None,
) -> dict[str, Any]:
    if not city_code:
        return {"median_rent_per_sqm": None, "sample_count": 0, "scope": None}

    df = db.read_listings(conn, filters={"city_code": city_code}, limit=5000)
    if df.empty:
        return {"median_rent_per_sqm": None, "sample_count": 0, "scope": None}
    if exclude_listing_id and "listing_id" in df.columns:
        df = df[df["listing_id"].astype(str) != exclude_listing_id]

    typed = df
    if property_type and "property_type" in df.columns:
        typed = df[df["property_type"].fillna("").astype(str) == property_type]
    typed_stats = _rent_stats_from_df(typed)
    if typed_stats["sample_count"] >= 3:
        typed_stats["scope"] = "city_property_type"
        return typed_stats

    city_stats = _rent_stats_from_df(df)
    city_stats["scope"] = "city"
    return city_stats


def _rent_stats_from_df(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"median_rent_per_sqm": None, "sample_count": 0}
    work = df.copy()
    annual = pd.to_numeric(work.get("gross_rent_annual_yen"), errors="coerce")
    monthly = pd.to_numeric(work.get("gross_rent_monthly_yen"), errors="coerce")
    area = pd.to_numeric(work.get("building_area_sqm"), errors="coerce")
    monthly_equiv = annual.div(12).fillna(monthly)
    rent_sqm = monthly_equiv.div(area)
    rent_sqm = rent_sqm[(rent_sqm > 0) & rent_sqm.notna()]
    if rent_sqm.empty:
        return {"median_rent_per_sqm": None, "sample_count": 0}
    return {"median_rent_per_sqm": float(rent_sqm.median()), "sample_count": len(rent_sqm)}


def _listing_monthly_rent(listing: dict[str, Any]) -> float | None:
    monthly = _num(listing.get("gross_rent_monthly_yen"))
    if monthly is not None and monthly > 0:
        return monthly
    annual = _num(listing.get("gross_rent_annual_yen"))
    if annual is not None and annual > 0:
        return annual / 12.0
    return None


def _city_name_for_listing(conn, listing: dict[str, Any]) -> str | None:
    city_code = _text_or_none(listing.get("city_code"))
    if city_code:
        row = conn.execute(
            """
            SELECT city_name
            FROM (
                SELECT city_name FROM land_prices_public_notice WHERE city_code = ? AND city_name IS NOT NULL
                UNION ALL
                SELECT city_name FROM trade_prices WHERE city_code = ? AND city_name IS NOT NULL
            )
            LIMIT 1
            """,
            [city_code, city_code],
        ).fetchone()
        if row and row[0]:
            return str(row[0])

    address = _text_or_none(listing.get("address"))
    if not address:
        return None
    import re

    match = re.match(
        r"^(?:北海道|東京都|京都府|大阪府|.{2,3}県)(.+?(?:市.+?区|市|区|町|村|郡))", address
    )
    return match.group(1) if match else None


def _normalize_structure(value: str | None) -> str | None:
    if not value:
        return None
    if value in _RENTABLE_EFFICIENCY_BY_STRUCTURE:
        return value
    mapping = {
        "木造": "wood",
        "木骨モルタル": "wood_mortar",
        "木造モルタル": "wood_mortar",
        "鉄骨造": "steel",
        "鉄骨": "steel",
        "S造": "steel",
        "RC造": "rc",
        "RC": "rc",
        "鉄筋コンクリート": "rc",
        "SRC造": "src",
        "SRC": "src",
        "鉄骨鉄筋コンクリート": "src",
    }
    return mapping.get(value)


def _rentable_efficiency_range(
    structure: str | None, property_type: str | None
) -> tuple[float, float]:
    if property_type and "戸建" in property_type:
        return (0.95, 1.00)
    if structure and structure in _RENTABLE_EFFICIENCY_BY_STRUCTURE:
        return _RENTABLE_EFFICIENCY_BY_STRUCTURE[structure]
    return (0.80, 0.90)


def _floor_plan_bucket_from_area(avg_unit_area: float | None) -> str | None:
    if avg_unit_area is None or avg_unit_area <= 0:
        return None
    if avg_unit_area < 22:
        return "ワンルーム"
    if avg_unit_area < 35:
        return "1K/1DK"
    if avg_unit_area < 50:
        return "1LDK/2K/2DK"
    if avg_unit_area < 70:
        return "2LDK/3K/3DK"
    return "3LDK/4K～"


def _fallback_floor_plan_bucket(property_type: str | None) -> str:
    if property_type and "戸建" in property_type:
        return "3LDK/4K～"
    if property_type and "アパート" in property_type:
        return "1K/1DK"
    return "1LDK/2K/2DK"


def _suumo_property_type(listing: dict[str, Any]) -> str:
    property_type = _text_or_none(listing.get("property_type")) or ""
    if "戸建" in property_type or "一戸建" in property_type:
        return "ikkodate"
    if "アパート" in property_type:
        return "apartment"
    return "mansion"


def _find_suumo_rent_row(
    conn, city_name: str, property_type: str, floor_plan_bucket: str
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM suumo_rent_market
        WHERE city_name = ?
          AND property_type = ?
          AND floor_plan_bucket = ?
          AND monthly_rent_yen IS NOT NULL
        ORDER BY updated_date DESC NULLS LAST
        LIMIT 1
        """,
        [city_name, property_type, floor_plan_bucket],
    ).fetchone()
    if row:
        cols = [desc[0] for desc in conn.description]
        return dict(zip(cols, row, strict=False))

    row = conn.execute(
        """
        SELECT *
        FROM suumo_rent_market
        WHERE city_name = ?
          AND floor_plan_bucket = ?
          AND monthly_rent_yen IS NOT NULL
        ORDER BY
          CASE WHEN property_type = 'mansion' THEN 0 ELSE 1 END,
          updated_date DESC NULLS LAST
        LIMIT 1
        """,
        [city_name, floor_plan_bucket],
    ).fetchone()
    if row:
        cols = [desc[0] for desc in conn.description]
        return dict(zip(cols, row, strict=False))
    return None


def _fmt_range_gap(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "—"
    if low > high:
        low, high = high, low
    return f"{low:+.1f}%〜{high:+.1f}%"


def _fmt_annual_upside(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value / 1e4:,.0f}万円/年"


def _rent_assessment(
    gap_low: float | None, gap_high: float | None, upside_annual: float | None
) -> dict[str, str]:
    if gap_low is None or gap_high is None or upside_annual is None:
        return {
            "label": "判定: 掲載賃料または価格情報が不足しているため、改善余地は参考値です。",
            "color": "#d0e4f0",
            "bg": "rgba(144,164,174,0.12)",
            "border": "rgba(144,164,174,0.35)",
        }
    if gap_high < -10:
        return {
            "label": "判定: 掲載賃料はSUUMO推定相場を下回る可能性があります。賃料改定・空室募集条件の見直し余地があります。",
            "color": "#81c784",
            "bg": "rgba(76,175,80,0.15)",
            "border": "rgba(76,175,80,0.45)",
        }
    if gap_low > 10:
        return {
            "label": "判定: 掲載賃料はSUUMO推定相場を上回る可能性があります。満室想定賃料の持続性を慎重に確認してください。",
            "color": "#ffb74d",
            "bg": "rgba(255,167,38,0.14)",
            "border": "rgba(255,167,38,0.42)",
        }
    return {
        "label": "判定: 掲載賃料はSUUMO推定相場レンジ内または近辺です。賃料面の大きな乖離は限定的です。",
        "color": "#7fc3ea",
        "bg": "rgba(79,195,247,0.12)",
        "border": "rgba(79,195,247,0.35)",
    }


def _text_or_none(value: Any) -> str | None:
    s = safe_str(value, fallback="")
    return s or None


def _fmt_yen_sqm(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f} 円/m²"


def _fmt_monthly_estimate(value: float | None) -> str | None:
    if value is None:
        return None
    return f"月額 {value / 1e4:,.1f}万円"


def _fmt_gap(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"
