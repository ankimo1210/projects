"""
ui/listings_tab.py
保存済み掲載物件の一覧比較タブ。
"""
from __future__ import annotations

import html
import re

import plotly.express as px
import pandas as pd
import streamlit as st

import streamlit.components.v1 as components

import analytics
import db
from property_scraper import LEGAL_LIFE_YEARS, STRUCTURE_JP, remaining_life
from ui.rent_benchmark_panel import render_rent_benchmark_panel
from ui.unit_price import SQM_PER_TSUBO, format_man, yen_to_man
from valuation import render_reason_texts
from utils import safe_float as _float_or_none, safe_int as _int_or_none, safe_str as _safe_str


REPLACEMENT_COST_YEN_PER_SQM: dict[str, int] = {
    "wood": 180_000,
    "wood_mortar": 170_000,
    "steel": 250_000,
    "rc": 280_000,
    "src": 300_000,
}

_PREF_ORDER = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府",
    "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県",
    "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県",
    "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]


def render_listings_tab(conn) -> None:
    st.header("📦 掲載物件一覧")

    all_listings = db.read_listings(conn, limit=5000)
    if all_listings.empty:
        st.info("保存済み掲載物件がありません。物件分析タブから取り込んでください。")
        return

    filters = _render_filters(all_listings)
    listings = _apply_table_filters(all_listings, filters).head(1000)
    if listings.empty:
        st.info("条件に一致する掲載物件がありません。フィルターを緩めてください。")
        return

    _render_summary(listings)
    _render_eval_chips(listings)
    _render_html_table(listings)

    # 詳細パネル用の物件選択
    st.markdown("---")
    names = ["（物件を選択）"] + [
        f"{i+1}. {row.get('property_name') or row.get('listing_id') or '—'}"
        for i, row in listings.iterrows()
    ]
    sel_label = st.selectbox("🔍 詳細を見る物件", names, key="listings_select_detail")
    if sel_label and sel_label != "（物件を選択）":
        idx = int(sel_label.split(".")[0]) - 1
        if 0 <= idx < len(listings):
            selected = listings.iloc[idx].to_dict()
            _render_listing_detail(conn, selected)
            _render_listing_map(selected)


def _render_filters(df: pd.DataFrame) -> dict:
    filter_df = _with_filter_columns(df)
    st.caption("ドロップダウンは未選択なら全件表示です。複数選択できます。")

    c1, c2, c3, c4 = st.columns(4)
    keyword = c1.text_input("キーワード", placeholder="住所・物件名・駅", key="listings_keyword")
    prefectures = c2.multiselect("都道府県", _pref_ordered_options(filter_df["prefecture"]), key="listings_prefecture_filter")
    municipalities = c3.multiselect("市区町村", _option_list(filter_df["municipality"]), key="listings_municipality_filter")
    source = c4.multiselect("サイト", _option_list(filter_df["source"]), key="listings_source_filter")

    f1, f2, f3, f4, f5 = st.columns(5)
    property_type = f1.multiselect("物件種別", _option_list(filter_df["property_type"]), key="listings_property_type_filter")
    structure = f2.multiselect("構造", _option_list(filter_df["structure_label"]), key="listings_structure_filter")
    cheap_label = f3.multiselect("評価", _ordered_options(filter_df["cheap_or_expensive"], list(_EVAL_CFG.keys())), key="listings_eval_filter")
    confidence = f4.multiselect("信頼度", _option_list(filter_df["confidence"]), key="listings_confidence_filter")
    region_label = f5.multiselect("地域ラベル", _option_list(filter_df["region_label"]), key="listings_region_filter")

    p1, p2, p3, p4 = st.columns(4)
    min_price = p1.number_input("最低価格(万円)", min_value=0, value=0, step=1000, key="listings_min_price")
    max_price = p2.number_input("最高価格(万円)", min_value=0, value=0, step=1000, key="listings_max_price")
    min_yield = p3.number_input("最低利回り(%)", min_value=0.0, value=0.0, step=0.5, key="listings_min_yield")
    max_yield = p4.number_input("最高利回り(%)", min_value=0.0, value=0.0, step=0.5, key="listings_max_yield")

    filters: dict = {}
    if keyword:
        filters["keyword"] = keyword
    if prefectures:
        filters["prefecture"] = prefectures
    if municipalities:
        filters["municipality"] = municipalities
    if source:
        filters["source"] = source
    if property_type:
        filters["property_type"] = property_type
    if structure:
        filters["structure_label"] = structure
    if cheap_label:
        filters["cheap_or_expensive"] = cheap_label
    if confidence:
        filters["confidence"] = confidence
    if region_label:
        filters["region_label"] = region_label
    if min_price > 0:
        filters["min_price"] = int(min_price * 10_000)
    if max_price > 0:
        filters["max_price"] = int(max_price * 10_000)
    if min_yield > 0:
        filters["min_yield"] = float(min_yield)
    if max_yield > 0:
        filters["max_yield"] = float(max_yield)
    return filters


def _option_list(series: pd.Series) -> list[str]:
    values = []
    for value in series.dropna().tolist():
        text = str(value).strip()
        if text and text not in ("—", "nan", "None", "NaT"):
            values.append(text)
    return sorted(set(values))


def _pref_ordered_options(series: pd.Series) -> list[str]:
    existing = set(_option_list(series))
    ordered = [name for name in _PREF_ORDER if name in existing]
    return ordered + sorted(existing - set(ordered))


def _ordered_options(series: pd.Series, preferred_order: list[str]) -> list[str]:
    existing = set(_option_list(series))
    ordered = [value for value in preferred_order if value in existing]
    extras = sorted(existing - set(ordered))
    return ordered + extras


def _split_address(address: str) -> tuple[str, str, str]:
    if address == "—":
        return "—", "—", "—"
    pref_match = re.match(r"^(北海道|東京都|京都府|大阪府|.{2,3}県)(.*)$", address)
    if not pref_match:
        return "—", "—", address
    pref = pref_match.group(1)
    rest = pref_match.group(2).strip()
    city_match = re.match(r"^(.+?(?:市.+?区|市|区|町|村))(.*)$", rest)
    if not city_match:
        return pref, "—", rest or "—"
    city = city_match.group(1)
    detail = city_match.group(2).strip() or "—"
    return pref, city, detail


def _with_filter_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    addresses = result.get("address", pd.Series(index=result.index, dtype=object)).fillna("—").astype(str)
    parts = addresses.map(lambda value: _split_address(value.strip() or "—"))
    result["prefecture"] = parts.map(lambda item: item[0])
    result["municipality"] = parts.map(lambda item: item[1])
    result["address_detail"] = parts.map(lambda item: item[2])
    structures = result.get("structure", pd.Series(index=result.index, dtype=object)).fillna("").astype(str)
    result["structure_label"] = structures.map(lambda value: STRUCTURE_JP.get(value, value) or "—")
    return result


def _apply_table_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    result = _with_filter_columns(df)
    if not filters:
        return result

    keyword = filters.get("keyword")
    if keyword:
        needle = str(keyword).strip()
        if needle:
            search_cols = ["address", "property_name", "nearest_station", "region_label"]
            mask = pd.Series(False, index=result.index)
            for col in search_cols:
                if col in result.columns:
                    mask = mask | result[col].fillna("").astype(str).str.contains(needle, case=False, na=False, regex=False)
            result = result[mask]

    for col in [
        "prefecture",
        "municipality",
        "source",
        "property_type",
        "structure_label",
        "cheap_or_expensive",
        "confidence",
        "region_label",
    ]:
        selected = filters.get(col)
        if selected:
            result = result[result[col].fillna("").astype(str).isin(selected)]

    min_price = filters.get("min_price")
    if min_price is not None:
        result = result[pd.to_numeric(result["asking_price_yen"], errors="coerce") >= float(min_price)]
    max_price = filters.get("max_price")
    if max_price is not None:
        result = result[pd.to_numeric(result["asking_price_yen"], errors="coerce") <= float(max_price)]
    min_yield = filters.get("min_yield")
    if min_yield is not None:
        result = result[pd.to_numeric(result["gross_yield_pct"], errors="coerce") >= float(min_yield)]
    max_yield = filters.get("max_yield")
    if max_yield is not None:
        result = result[pd.to_numeric(result["gross_yield_pct"], errors="coerce") <= float(max_yield)]
    return result


_EVAL_CFG: dict[str, tuple[str, str, str]] = {
    # label: (bg, border, text)
    "割安":    ("rgba(76,175,80,0.18)",   "rgba(76,175,80,0.5)",   "#81c784"),
    "やや割安": ("rgba(129,199,132,0.15)", "rgba(129,199,132,0.4)", "#a5d6a7"),
    "中立":    ("rgba(144,164,174,0.15)", "rgba(144,164,174,0.35)","#90a4ae"),
    "やや割高": ("rgba(255,167,38,0.15)",  "rgba(255,167,38,0.4)",  "#ffb74d"),
    "割高":    ("rgba(239,83,80,0.15)",   "rgba(239,83,80,0.45)",  "#ef9a9a"),
    "良好":    ("rgba(79,195,247,0.12)",  "rgba(79,195,247,0.35)", "#4fc3f7"),
}


def _eval_badge_html(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '<span style="color:#4a6580">—</span>'
    value = str(value).strip()
    if not value or value in ("—", "nan", "None"):
        return '<span style="color:#4a6580">—</span>'
    cfg = _EVAL_CFG.get(value)
    if not cfg:
        return f'<span style="color:#90a4ae">{html.escape(value)}</span>'
    bg, border, text = cfg
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{bg};border:1px solid {border};color:{text};'
        f'font-size:0.72rem;font-weight:700;white-space:nowrap">'
        f'{html.escape(value)}</span>'
    )


def _score_badge_html(value, kind: str = "life") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '<span style="color:#4a6580">—</span>'
    v = float(value)
    if kind == "life":
        if v >= 70:
            label, color, bg = "良好", "#81c784", "rgba(76,175,80,0.15)"
        elif v >= 45:
            label, color, bg = "中立", "#90a4ae", "rgba(144,164,174,0.12)"
        else:
            label, color, bg = "弱め", "#ffb74d", "rgba(255,167,38,0.12)"
    else:
        if v >= 60:
            label, color, bg = "注意", "#ef9a9a", "rgba(239,83,80,0.15)"
        elif v >= 35:
            label, color, bg = "中立", "#90a4ae", "rgba(144,164,174,0.12)"
        else:
            label, color, bg = "低め", "#81c784", "rgba(76,175,80,0.15)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 7px;'
        f'border-radius:4px;background:{bg};color:{color};font-size:0.72rem;font-weight:600;white-space:nowrap">'
        f'{label} <span style="opacity:0.7;font-weight:400">({v:.0f})</span></span>'
    )


def _gap_bar_html(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '<span style="color:#4a6580">—</span>'
    v = float(value)
    pct = min(abs(v), 500) / 500 * 54
    color = "#66bb6a" if v >= 0 else "#ef5350"
    text_color = "#81c784" if v >= 0 else "#ef9a9a"
    sign = "+" if v >= 0 else ""
    return (
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'<div style="width:54px;height:5px;background:#0a1c30;border-radius:3px;overflow:hidden;flex-shrink:0">'
        f'<div style="width:{pct:.0f}px;height:100%;border-radius:3px;background:{color}"></div></div>'
        f'<span style="color:{text_color};font-variant-numeric:tabular-nums;min-width:52px;text-align:right;font-size:0.8rem">'
        f'{sign}{v:.1f}%</span></div>'
    )


def _yield_html(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '<span style="color:#4a6580">—</span>'
    v = float(value)
    if v >= 8:
        color, weight = "#81c784", "700"
    elif v >= 5:
        color, weight = "#4fc3f7", "600"
    elif v >= 3:
        color, weight = "#d0e4f0", "400"
    else:
        color, weight = "#90a4ae", "400"
    return f'<span style="color:{color};font-weight:{weight};font-variant-numeric:tabular-nums">{v:.1f}%</span>'


def _render_eval_chips(df: pd.DataFrame) -> None:
    """評価別件数を静的バッジで表示する。"""
    counts = df["cheap_or_expensive"].value_counts() if "cheap_or_expensive" in df.columns else pd.Series(dtype=int)
    chips_html = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px">'
    for label, cfg in _EVAL_CFG.items():
        n = int(counts.get(label, 0))
        if n == 0:
            continue
        bg, border, text = cfg
        chips_html += (
            f'<span style="padding:3px 10px;border-radius:5px;border:1px solid {border};'
            f'background:{bg};color:{text};font-size:0.75rem;font-weight:600">'
            f'{html.escape(label)} ({n})</span>'
        )
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# listings_tab 専用セルレンダラー（モジュールレベル）
# --------------------------------------------------------------------------

def _money_man_html(v, *, muted_value: str = "—") -> str:
    n = _float_or_none(v)
    if n is None:
        return f'<span style="color:#4a6580">{muted_value}</span>'
    return (
        '<span style="color:#e8f4ff;font-variant-numeric:tabular-nums;font-weight:600">'
        f'{n/1e4:,.0f}</span>'
    )


def _small_html(v, color: str = "#a8c8e0") -> str:
    text = _safe_str(v)
    if text == "—":
        return '<span style="color:#4a6580">—</span>'
    return f'<span style="color:{color};font-size:0.76rem">{html.escape(text)}</span>'


def _area_html(v) -> str:
    n = _float_or_none(v)
    if n is None:
        return '<span style="color:#4a6580">—</span>'
    return f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{n:,.1f}</span>'


def _unit_price_man_html(v) -> str:
    n = _float_or_none(v)
    if n is None:
        return '<span style="color:#4a6580">—</span>'
    return f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{n/1e4:.1f}</span>'


def _unit_price_range_man_html(low, high, *, estimated: bool = False) -> str:
    low_n = _float_or_none(low)
    high_n = _float_or_none(high)
    if low_n is None and high_n is None:
        return '<span style="color:#4a6580">—</span>'
    if low_n is not None and high_n is not None:
        if low_n > high_n:
            low_n, high_n = high_n, low_n
        value = f"{low_n/1e4:.1f}〜{high_n/1e4:.1f}"
    else:
        value_n = low_n if low_n is not None else high_n
        value = f"{value_n/1e4:.1f}"
    label = "推定 " if estimated else ""
    return (
        '<span style="color:#b8d0e8;font-variant-numeric:tabular-nums;white-space:nowrap">'
        f'{label}{value}</span>'
    )


def _land_unit_price_range_html(row: pd.Series) -> str:
    area = _float_or_none(row.get("land_area_sqm"))
    low = _float_or_none(row.get("land_price_estimate_low_yen"))
    high = _float_or_none(row.get("land_price_estimate_high_yen"))
    if area is not None and area > 0 and (low is not None or high is not None):
        return _unit_price_range_man_html(
            low / area if low is not None else None,
            high / area if high is not None else None,
            estimated=True,
        )
    p25 = _float_or_none(row.get("land_unit_price_p25_yen_per_sqm"))
    p75 = _float_or_none(row.get("land_unit_price_p75_yen_per_sqm"))
    if p25 is not None or p75 is not None:
        return _unit_price_range_man_html(p25, p75, estimated=True)
    return '<span style="color:#4a6580">—</span>'


def _station_html(row: pd.Series) -> str:
    station = _safe_str(row.get("nearest_station"))
    walk = _float_or_none(row.get("station_walk_min"))
    if station == "—" and walk is None:
        return '<span style="color:#4a6580">—</span>'
    walk_text = f' <span style="color:#7fc3ea">徒歩{walk:.0f}分</span>' if walk is not None else ""
    return f'<span style="color:#a8c8e0;font-size:0.76rem">{html.escape(station)}{walk_text}</span>'


def _structure_html(value) -> str:
    return _small_html(STRUCTURE_JP.get(str(value or ""), value))


def _age_html(value) -> str:
    age = _float_or_none(value)
    if age is None:
        return '<span style="color:#4a6580">—</span>'
    return f'<span style="color:#7fc3ea;font-variant-numeric:tabular-nums">{age:.0f}</span>'


def _source_html(value) -> str:
    source = _safe_str(value)
    if source == "—":
        return '<span style="color:#4a6580">—</span>'
    return (
        '<span style="display:inline-block;padding:2px 7px;border-radius:4px;'
        'background:rgba(79,195,247,0.12);border:1px solid rgba(79,195,247,0.35);'
        'color:#7fc3ea;font-size:0.72rem;font-weight:600">'
        f'{html.escape(source)}</span>'
    )


def _property_name_html(row: pd.Series, name: str) -> str:
    url = _safe_str(row.get("source_url"), fallback="")
    escaped_name = html.escape(name)
    if not url:
        return f'<span style="color:#d8ecf8;font-size:0.85rem">{escaped_name}</span>'
    escaped_url = html.escape(url, quote=True)
    return (
        f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" '
        'style="color:#7fc3ea;font-size:0.85rem;text-decoration:none;font-weight:600">'
        f'{escaped_name}</a>'
    )


def _confidence_html(value) -> str:
    conf = _safe_str(value)
    if conf == "—":
        return '<span style="color:#4a6580">—</span>'
    color = "#81c784" if conf == "high" else "#ffb74d" if conf == "partial" else "#90a4ae"
    return f'<span style="color:{color};font-size:0.72rem;font-weight:600">{html.escape(conf)}</span>'


def _ds(v) -> str:
    """data-sort 属性用の生数値文字列。None/NaN は空文字。"""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v)


def _render_html_table(df: pd.DataFrame) -> None:
    """デザインシステム準拠のリッチHTMLテーブルを描画する。"""
    rows_html = ""
    for i, row in df.iterrows():
        region = _safe(row.get("region_label"), "")
        region_html = (
            f'<span style="color:#7fc3ea;font-size:0.75rem">{html.escape(region)}</span>'
            if region
            else '<span style="color:#3a5570">—</span>'
        )

        name = _safe(row.get("property_name")) if _safe(row.get("property_name")) != "—" else _safe(row.get("listing_id"))
        addr = _safe(row.get("address"))
        pref, city, address_detail = _split_address(addr)

        price_yen = row.get("asking_price_yen")
        price_html = _money_man_html(price_yen)

        saved = _safe(row.get("last_seen_at"), _safe(row.get("first_seen_at"), "—"))[:10]

        zebra = "background:rgba(19,32,53,0.4)" if i % 2 == 0 else "background:transparent"
        rows_html += (
            f'<tr style="{zebra};border-bottom:1px solid rgba(36,61,94,0.4);transition:background 0.1s" '
            f'onmouseover="this.style.background=\'rgba(26,46,71,0.6)\'" '
            f'onmouseout="this.style.background=\'{("rgba(19,32,53,0.4)" if i % 2 == 0 else "transparent")}\'">'
            f'<td data-sort="{html.escape(region)}" style="padding:8px 10px">{region_html}</td>'
            f'<td data-sort="{html.escape(_safe(row.get("source")))}" style="padding:8px 10px">{_source_html(row.get("source"))}</td>'
            f'<td data-sort="{html.escape(name)}" style="padding:8px 10px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{html.escape(name)}">'
            f'{_property_name_html(row, name)}</td>'
            f'<td data-sort="{html.escape(pref)}" style="padding:8px 10px">{_small_html(pref)}</td>'
            f'<td data-sort="{html.escape(city)}" style="padding:8px 10px">{_small_html(city)}</td>'
            f'<td data-sort="{html.escape(address_detail)}" style="padding:8px 10px;max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{html.escape(addr)}">'
            f'<span style="color:#a8c8e0;font-size:0.78rem">{html.escape(address_detail)}</span></td>'
            f'<td data-sort="{html.escape(_safe(row.get("property_type")))}" style="padding:8px 10px;white-space:nowrap">{_small_html(row.get("property_type"))}</td>'
            f'<td data-sort="{html.escape(_safe(row.get("structure")))}" style="padding:8px 10px;white-space:nowrap">{_structure_html(row.get("structure"))}</td>'
            f'<td data-sort="{_ds(row.get("age_years"))}" style="padding:8px 10px;text-align:right">{_age_html(row.get("age_years"))}</td>'
            f'<td data-sort="{html.escape(_safe(row.get("nearest_station")))}" style="padding:8px 10px;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{_station_html(row)}</td>'
            f'<td data-sort="{_ds(price_yen)}" style="padding:8px 10px;text-align:right">{price_html}</td>'
            f'<td data-sort="{_ds(row.get("gross_yield_pct"))}" style="padding:8px 10px;text-align:right">{_yield_html(row.get("gross_yield_pct"))}</td>'
            f'<td data-sort="{_ds(row.get("gross_rent_annual_yen"))}" style="padding:8px 10px;text-align:right">{_money_man_html(row.get("gross_rent_annual_yen"))}</td>'
            f'<td data-sort="{_ds(row.get("building_area_sqm"))}" style="padding:8px 10px;text-align:right">{_area_html(row.get("building_area_sqm"))}</td>'
            f'<td data-sort="{_ds(row.get("land_area_sqm"))}" style="padding:8px 10px;text-align:right">{_area_html(row.get("land_area_sqm"))}</td>'
            f'<td data-sort="{_ds(row.get("unit_price_yen_per_sqm"))}" style="padding:8px 10px;text-align:right">{_unit_price_man_html(row.get("unit_price_yen_per_sqm"))}</td>'
            f'<td data-sort="{_ds(row.get("land_unit_price_p75_yen_per_sqm"))}" style="padding:8px 10px;text-align:right">{_land_unit_price_range_html(row)}</td>'
            f'<td data-sort="{_ds(row.get("public_notice_gap_pct"))}" style="padding:8px 10px">{_gap_bar_html(row.get("public_notice_gap_pct"))}</td>'
            f'<td data-sort="{_ds(row.get("trade_gap_pct"))}" style="padding:8px 10px">{_gap_bar_html(row.get("trade_gap_pct"))}</td>'
            f'<td data-sort="{_ds(row.get("fair_value_yen"))}" style="padding:8px 10px;text-align:right">{_money_man_html(row.get("fair_value_yen"))}</td>'
            f'<td data-sort="{_ds(row.get("adjusted_gap_pct"))}" style="padding:8px 10px">{_gap_bar_html(row.get("adjusted_gap_pct"))}</td>'
            f'<td data-sort="{_ds(row.get("life_convenience_score"))}" style="padding:8px 10px">{_score_badge_html(row.get("life_convenience_score"), "life")}</td>'
            f'<td data-sort="{_ds(row.get("terrain_caution_score"))}" style="padding:8px 10px">{_score_badge_html(row.get("terrain_caution_score"), "risk")}</td>'
            f'<td data-sort="{html.escape(_safe(row.get("cheap_or_expensive")))}" style="padding:8px 10px">{_eval_badge_html(row.get("cheap_or_expensive"))}</td>'
            f'<td data-sort="{html.escape(_safe(row.get("confidence")))}" style="padding:8px 10px">{_confidence_html(row.get("confidence"))}</td>'
            f'<td data-sort="{html.escape(saved)}" style="padding:8px 10px"><span style="color:#4a6580;font-size:0.72rem">{html.escape(saved)}</span></td>'
            f'</tr>'
        )

    # クリックソート用 JS
    sort_js = """
<script>
(function(){
  var _sortCol = -1, _sortAsc = true;
  function sortTable(th) {
    var col = parseInt(th.dataset.col, 10);
    var asc = (_sortCol === col) ? !_sortAsc : true;
    _sortCol = col; _sortAsc = asc;
    var table = th.closest('table');
    table.querySelectorAll('th[data-col] .sa').forEach(function(s){ s.textContent = '⇅'; s.style.opacity='0.4'; });
    var arrow = th.querySelector('.sa');
    if(arrow){ arrow.textContent = asc ? '↑' : '↓'; arrow.style.opacity='1'; }
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b){
      var av = (a.querySelectorAll('td')[col] || {}).dataset.sort || '';
      var bv = (b.querySelectorAll('td')[col] || {}).dataset.sort || '';
      var an = parseFloat(av), bn = parseFloat(bv);
      if(av === '' && bv === '') return 0;
      if(av === '') return 1;
      if(bv === '') return -1;
      if(!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
      return asc ? av.localeCompare(bv,'ja') : bv.localeCompare(av,'ja');
    });
    rows.forEach(function(r){ tbody.appendChild(r); });
  }
  window._sortListingsTable = sortTable;
})();
</script>
"""

    th_base = (
        "padding:9px 10px;color:#95b8cf;font-size:0.72rem;font-weight:600;"
        "white-space:nowrap;border-bottom:2px solid #243d5e;user-select:none"
    )
    th_sort = th_base + ";cursor:pointer"
    th_sort_r = th_sort + ";text-align:right"
    th_nosort = th_base

    def _th(label: str, col: int, *, right: bool = False, width: str = "", sortable: bool = True) -> str:
        style = (th_sort_r if right else th_sort) if sortable else th_nosort
        w = f";width:{width}" if width else ""
        arrow = '<span class="sa" style="margin-left:3px;opacity:0.4;font-size:0.65rem">⇅</span>' if sortable else ""
        click = f'onclick="window._sortListingsTable(this)"' if sortable else ""
        return f'<th {click} data-col="{col}" style="{style}{w}">{label}{arrow}</th>'

    # テーブル固定高さ: 少数行は縮小、多数行は700px固定でスクロール
    row_px = 37
    header_px = 46
    inner_h = min(700, len(df) * row_px + header_px)

    table_html = f"""
{sort_js}
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:0; background:#0a1c30; font-family:sans-serif; }}
  .wrap {{
    width: 100%;
    height: {inner_h}px;
    overflow: auto;          /* 縦横両方スクロール */
    border: 1px solid #243d5e;
    border-radius: 8px;
    background: #0a1c30;
  }}
  table {{
    border-collapse: collapse;
    background: #0a1c30;
    min-width: 1980px;
    width: 100%;
  }}
  thead tr {{
    background: #132035;
    position: sticky;
    top: 0;
    z-index: 1;
  }}
  p.foot {{ color:#4a6580; font-size:0.72rem; margin:6px 2px 0; }}
</style>
<div class="wrap">
  <table>
    <thead>
      <tr>
        {_th("地域ラベル", 0, width="90px")}
        {_th("サイト", 1, width="74px")}
        {_th("物件名", 2, width="220px")}
        {_th("都道府県", 3, width="78px")}
        {_th("市区町村", 4, width="110px")}
        {_th("町名以下", 5, width="190px")}
        {_th("種別", 6, width="126px")}
        {_th("構造", 7, width="118px")}
        {_th("築年", 8, right=True, width="64px")}
        {_th("最寄駅", 9, width="150px")}
        {_th("価格(万円)", 10, right=True, width="90px")}
        {_th("利回り", 11, right=True, width="70px")}
        {_th("年賃料(万)", 12, right=True, width="92px")}
        {_th("建物㎡", 13, right=True, width="84px")}
        {_th("土地㎡", 14, right=True, width="84px")}
        {_th("建物㎡単価", 15, right=True, width="104px")}
        {_th("土地㎡単価(推定)", 16, right=True, width="122px")}
        {_th("公示地価比", 17, width="130px")}
        {_th("取引価格比", 18, width="130px")}
        {_th("適正価格(万)", 19, right=True, width="96px")}
        {_th("評価差", 20, width="120px")}
        {_th("生活利便", 21, width="90px")}
        {_th("低地注意", 22, width="90px")}
        {_th("評価", 23, width="80px")}
        {_th("信頼度", 24, width="72px")}
        {_th("保存日", 25, width="84px")}
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>
<p class="foot">{len(df)} 件 — 下のセレクトボックスで詳細を表示</p>
"""
    # iframe は <script> 実行のため必要。高さ = テーブルdiv + フッター分
    components.html(table_html, height=inner_h + 36, scrolling=False)


def _render_summary(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("掲載物件数", f"{len(df):,}件")
    c2.metric("中央値価格", f"{df['asking_price_yen'].median()/1e4:,.0f}万円" if df["asking_price_yen"].notna().any() else "—")
    c3.metric("中央値利回り", f"{df['gross_yield_pct'].median():.1f}%" if df["gross_yield_pct"].notna().any() else "—")
    c4.metric("割安判定数", f"{int((df['cheap_or_expensive'] == '割安').sum())}件" if "cheap_or_expensive" in df.columns else "—")


def _build_display_df(df: pd.DataFrame) -> pd.DataFrame:
    disp = df.copy()
    disp["価格(万円)"] = disp["asking_price_yen"].map(lambda x: format_man(yen_to_man(x)) if pd.notna(x) else "—")
    disp["利回り(%)"] = disp["gross_yield_pct"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
    disp["㎡単価(万円/m²)"] = disp["unit_price_yen_per_sqm"].map(lambda x: format_man(yen_to_man(x)) if pd.notna(x) else "—")
    disp["坪単価(万円/坪)"] = disp["unit_price_yen_per_sqm"].map(
        lambda x: format_man(yen_to_man(float(x) * SQM_PER_TSUBO)) if pd.notna(x) else "—"
    )
    disp["公示地価比"] = disp["public_notice_gap_pct"].map(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
    disp["取引価格比"] = disp["trade_gap_pct"].map(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
    disp["生活利便"] = disp["life_convenience_score"].map(_score_badge)
    disp["低地注意"] = disp["terrain_caution_score"].map(_risk_badge)
    disp["評価"] = disp["cheap_or_expensive"].fillna("—")
    cols = [
        "listing_id",
        "region_label",
        "property_name",
        "address",
        "価格(万円)",
        "利回り(%)",
        "㎡単価(万円/m²)",
        "坪単価(万円/坪)",
        "公示地価比",
        "取引価格比",
        "生活利便",
        "低地注意",
        "評価",
        "last_seen_at",
    ]
    available = [c for c in cols if c in disp.columns]
    return disp[available].rename(
        columns={
            "listing_id": "ID",
            "region_label": "地域ラベル",
            "property_name": "物件名",
            "address": "住所",
            "last_seen_at": "保存日時",
        }
    )


def _render_listing_detail(conn, row: dict) -> None:
    st.markdown("---")
    st.subheader(row.get("property_name") or row["listing_id"])
    st.caption(row.get("address") or "住所不明")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("価格", f"{row['asking_price_yen']/1e4:,.0f}万円" if row.get("asking_price_yen") else "—")
    c2.metric("利回り", f"{row['gross_yield_pct']:.1f}%" if row.get("gross_yield_pct") is not None else "—")
    c3.metric("評価", row.get("cheap_or_expensive") or "—")
    c4.metric("信頼度", row.get("confidence") or "—")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("生活利便", _score_badge(row.get("life_convenience_score")))
    d2.metric("ファミリー", _score_badge(row.get("family_score")))
    d3.metric("嫌悪施設", _risk_badge(row.get("negative_facility_score")))
    d4.metric("地形注意", _risk_badge(row.get("terrain_caution_score")))

    _render_listing_summary_panels(row)

    reasons = render_reason_texts(row.get("reasons_json"))
    if reasons:
        st.markdown("**判定理由**")
        for line in reasons[:5]:
            st.write(f"- {line}")

    land_low = row.get("land_price_estimate_low_yen")
    land_high = row.get("land_price_estimate_high_yen")
    bld_low = row.get("building_residual_low_yen")
    bld_high = row.get("building_residual_high_yen")
    cost_low, cost_high, cost_note = _estimate_building_cost_approach(row)
    if any(pd.notna(v) for v in [land_low, land_high, bld_low, bld_high, cost_low, cost_high]):
        st.markdown("**土地/建物価格試算（モデル比較）**")
        e1, e2, e3 = st.columns(3)
        e1.metric(
            "土地価格（推定）",
            _format_range_man(land_low, land_high),
            help="保存済みスナップショットの近傍公示地価レンジに基づく推定値",
        )
        e2.metric(
            "建物価格（残余）",
            _format_range_man(bld_low, bld_high, allow_negative_note=True),
            help="物件価格 − 推定土地価格レンジ",
        )
        e3.metric(
            "建物価格（原価法・概算）",
            _format_range_man(cost_low, cost_high),
            help="構造別の再調達単価 × 建物面積 × 残存耐用年数割合。単価は概算で、低〜高は±15%です。",
        )
        e1.caption(_format_range_unit_price(land_low, land_high, area_sqm=row.get("land_area_sqm")))
        e2.caption(
            _format_range_unit_price(
                bld_low,
                bld_high,
                area_sqm=row.get("building_area_sqm"),
                allow_negative_note=True,
            )
        )
        e3.caption(cost_note)

        p25 = row.get("land_unit_price_p25_yen_per_sqm")
        p75 = row.get("land_unit_price_p75_yen_per_sqm")
        if pd.notna(p25) or pd.notna(p75):
            st.caption(
                "土地単価前提: "
                f"{_format_existing_unit_price_range(p25, p75)}"
            )
        st.caption("参考: 残余法は売出価格に依存します。原価法は構造・面積・築年数の概算で、リフォーム状況や収益力は未反映です。")

    render_rent_benchmark_panel(conn, row, title_level=4)


@st.cache_data(show_spinner=False, ttl=3600)
def _load_latest_land_points_for_map() -> pd.DataFrame:
    conn = db.get_connection()
    try:
        years = db.get_available_years(conn)
        latest_year = years[0] if years else None
        if latest_year is None:
            return pd.DataFrame()
        df = db.read_land_prices(conn, filters={"year": latest_year})
        cols = [c for c in ["point_id", "location_text", "city_name", "use_category_name", "price_yen_per_sqm", "lat", "lon"] if c in df.columns]
        return df[cols].dropna(subset=["lat", "lon"]).copy()
    finally:
        conn.close()


def _render_listing_map(row: dict) -> None:
    lat = row.get("lat")
    lon = row.get("lon")
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return

    st.markdown("**周辺マップ**")
    land_df = _load_latest_land_points_for_map()
    nearby = analytics.find_nearby_points(land_df, float(lon), float(lat), radius_m=2000) if not land_df.empty else pd.DataFrame()

    property_df = pd.DataFrame(
        [
            {
                "label": row.get("property_name") or row.get("listing_id") or "物件",
                "lat": float(lat),
                "lon": float(lon),
                "kind": "物件",
                "price_label": _format_yen(row.get("asking_price_yen")),
            }
        ]
    )

    map_df = property_df.copy()
    if not nearby.empty:
        nearby = nearby.copy()
        nearby["label"] = nearby["location_text"].fillna(nearby["point_id"]).fillna("地価公示")
        nearby["kind"] = "公示地価"
        nearby["price_label"] = nearby["price_yen_per_sqm"].map(
            lambda x: f"{format_man(yen_to_man(float(x)))} 万円/m²" if pd.notna(x) else "—"
        )
        map_df = pd.concat(
            [
                property_df,
                nearby[["label", "lat", "lon", "kind", "price_label"]],
            ],
            ignore_index=True,
        )

    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        color="kind",
        hover_name="label",
        hover_data={"price_label": True, "lat": False, "lon": False, "kind": False},
        color_discrete_map={"物件": "#ef5350", "公示地価": "#4fc3f7"},
        mapbox_style="open-street-map",
        zoom=13,
        center={"lat": float(lat), "lon": float(lon)},
        height=850,
    )
    fig.update_traces(marker={"size": 11, "opacity": 0.9})
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend={"orientation": "h", "y": 1.02, "x": 0.0},
    )
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
    st.caption(f"赤: 物件 / 青: 周辺公示地価地点（2km以内 {len(nearby)}件）")


def _render_listing_summary_panels(row: dict) -> None:
    structure_code = row.get("structure")
    structure_jp = STRUCTURE_JP.get(structure_code or "", structure_code or "—")
    legal = LEGAL_LIFE_YEARS.get(structure_code or "")
    structure_label = f"{structure_jp}（法定{legal}年）" if legal and structure_jp != "—" else structure_jp
    age_years = row.get("age_years")
    rem_years = remaining_life(structure_code, int(age_years)) if pd.notna(age_years) else None
    walk = f"徒歩{int(row['station_walk_min'])}分" if pd.notna(row.get("station_walk_min")) else ""
    station = f"{row.get('nearest_station') or '—'} {walk}".strip()

    static_metrics = [
        ("物件種別", _text_or_dash(row.get("property_type")), None),
        ("構造", structure_label, None),
        ("建築年月", _text_or_dash(row.get("build_year_month")), None),
        ("間取り", _text_or_dash(row.get("floor_plan")), None),
        ("建物面積", _format_area(row.get("building_area_sqm")), None),
        ("土地面積", _format_area(row.get("land_area_sqm")), None),
        ("総戸数", _format_int_suffix(row.get("num_units"), "戸"), None),
        ("階数", _format_int_suffix(row.get("num_floors"), "階", prefix="地上"), None),
        ("最寄駅", station or "—", None),
        ("接道状況", _text_or_dash(row.get("road_frontage")), None),
        ("土地権利", _text_or_dash(row.get("land_rights")), None),
        ("取引態様", _text_or_dash(row.get("transaction_type")), None),
        ("容積率（制限）", _format_pct0(row.get("legal_far_pct")), None),
        ("建蔽率（制限）", _format_pct0(row.get("bcr_pct")), None),
        ("地目", _text_or_dash(row.get("land_category")), None),
        ("都市計画区域", _text_or_dash(row.get("city_planning_area")), None),
    ]
    variable_metrics = [
        ("物件価格", _format_yen(row.get("asking_price_yen")), None),
        ("月額賃料", _format_yen(row.get("gross_rent_monthly_yen"), suffix="/月"), None),
        ("年間賃料", _format_yen(row.get("gross_rent_annual_yen"), suffix="/年"), None),
        ("表面利回り", _format_pct1(row.get("gross_yield_pct")), None),
        ("築年数", _format_int_suffix(age_years, "年"), None),
        ("残存耐用年数", _format_int_suffix(rem_years, "年"), None),
        ("更新日", _text_or_dash(row.get("updated_date")), None),
        ("情報登録日", _text_or_dash(row.get("listing_date")), None),
    ]
    analysis_metrics = [
        ("㎡単価", _format_unit_price(row.get("unit_price_yen_per_sqm")), None),
        ("坪単価", _format_tsubo_unit_price(row.get("unit_price_yen_per_sqm")), None),
        ("公示地価比", _format_signed_pct(row.get("public_notice_gap_pct")), None),
        ("取引価格比", _format_signed_pct(row.get("trade_gap_pct")), None),
        ("公示地価件数", _format_int_suffix(row.get("nearby_land_count"), "件"), None),
        ("取引価格件数", _format_int_suffix(row.get("nearby_trade_count"), "件"), None),
        ("フェアバリュー", _format_yen(row.get("fair_value_yen")), None),
        ("評価差", _format_signed_pct(row.get("adjusted_gap_pct")), None),
    ]
    risk_metrics = [
        ("生活利便", _score_badge(row.get("life_convenience_score")), None),
        ("ファミリー", _score_badge(row.get("family_score")), None),
        ("嫌悪施設", _risk_badge(row.get("negative_facility_score")), None),
        ("地形注意", _risk_badge(row.get("terrain_caution_score")), None),
        ("標高", _format_float_suffix(row.get("elevation_m"), "m"), None),
        ("標高区分", _text_or_dash(row.get("elevation_band")), None),
        ("最寄り水辺", _format_float_suffix(row.get("nearest_water_m"), "m", digits=0), None),
        ("洪水", _hazard_label(row.get("flood_risk_flag"), row.get("flood_depth_rank")), None),
        ("土砂", _flag_label(row.get("landslide_risk_flag"), positive="警戒"), None),
    ]

    left_col, right_col = st.columns(2)
    with left_col:
        _render_compact_panel("固定スペック", static_metrics, columns=2)
    with right_col:
        _render_compact_panel("変動しうる指標", variable_metrics, columns=2)

    a1, a2 = st.columns(2)
    with a1:
        _render_compact_panel("価格分析", analysis_metrics, columns=2)
    with a2:
        _render_compact_panel("立地・リスク", risk_metrics, columns=2)


def _render_compact_panel(
    title: str,
    metrics: list[tuple[str, str, str | None]],
    *,
    columns: int = 2,
) -> None:
    classes = f"property-summary-grid cols-{columns}"
    items_html: list[str] = []
    for label, value, note in metrics:
        note_html = f'<div class="property-summary-item-note">{html.escape(str(note))}</div>' if note else ""
        items_html.append(
            "<div class=\"property-summary-item\">"
            f"<div class=\"property-summary-item-label\">{html.escape(str(label))}</div>"
            f"<div class=\"property-summary-item-value\">{html.escape(str(value))}</div>"
            f"{note_html}"
            "</div>"
        )
    panel_html = (
        "<div class=\"property-summary-panel\">"
        f"<div class=\"property-summary-panel-title\">{html.escape(title)}</div>"
        f"<div class=\"{classes}\">{''.join(items_html)}</div>"
        "</div>"
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def _score_badge(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    if value >= 70:
        return f"良好 ({value:.0f})"
    if value >= 45:
        return f"中立 ({value:.0f})"
    return f"弱め ({value:.0f})"


def _risk_badge(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    if value >= 60:
        return f"注意 ({value:.0f})"
    if value >= 35:
        return f"中立 ({value:.0f})"
    return f"低め ({value:.0f})"


def _estimate_building_cost_approach(row: dict) -> tuple[float | None, float | None, str]:
    structure = _normalize_structure_code(row.get("structure"))
    area = _float_or_none(row.get("building_area_sqm"))
    age = _int_or_none(row.get("age_years"))
    if not structure or area is None or area <= 0 or age is None:
        return None, None, "構造・建物面積・築年数が不足"

    legal_life = LEGAL_LIFE_YEARS.get(structure)
    unit_cost = REPLACEMENT_COST_YEN_PER_SQM.get(structure)
    if legal_life is None or unit_cost is None:
        return None, None, "構造別単価または耐用年数が未設定"

    rem_life = remaining_life(structure, age)
    if rem_life is None:
        return None, None, "残存耐用年数を計算できません"

    residual_ratio = min(1.0, max(0.0, rem_life / legal_life))
    center = unit_cost * area * residual_ratio
    low = center * 0.85
    high = center * 1.15
    structure_label = STRUCTURE_JP.get(structure, structure)
    note = (
        f"{structure_label} / 再調達単価 {unit_cost/1e4:.0f}万円/m² / "
        f"面積 {area:.1f}m² / 残存 {rem_life}/{legal_life}年"
    )
    return low, high, note


def _normalize_structure_code(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in STRUCTURE_JP:
        return text
    for code, label in STRUCTURE_JP.items():
        if text == label or text.replace("造", "") == label.replace("造", ""):
            return code
    return None




def _format_range_man(low, high, *, allow_negative_note: bool = False) -> str:
    if pd.isna(low) and pd.isna(high):
        return "—"
    if pd.notna(low) and pd.notna(high):
        low_v = float(low)
        high_v = float(high)
        if allow_negative_note and high_v <= 0:
            return "—"
        low_label = max(0.0, low_v) if allow_negative_note else low_v
        return f"{low_label/1e4:,.0f}〜{high_v/1e4:,.0f}万円"
    value = low if pd.notna(low) else high
    if allow_negative_note and float(value) <= 0:
        return "—"
    return f"{float(value)/1e4:,.0f}万円"


def _format_range_unit_price(low, high, *, area_sqm=None, allow_negative_note: bool = False) -> str:
    if area_sqm is None or pd.isna(area_sqm) or float(area_sqm) <= 0:
        return "単価 —"
    area = float(area_sqm)
    if pd.isna(low) and pd.isna(high):
        return "単価 —"
    if pd.notna(low) and pd.notna(high):
        low_v = float(low) / area
        high_v = float(high) / area
        if allow_negative_note and high_v <= 0:
            return "単価 —"
        low_label = max(0.0, low_v) if allow_negative_note else low_v
        return f"単価 {format_man(yen_to_man(low_label))}〜{format_man(yen_to_man(high_v))} 万円/m²"
    value = float(low if pd.notna(low) else high) / area
    if allow_negative_note and value <= 0:
        return "単価 —"
    return f"単価 {format_man(yen_to_man(value))} 万円/m²"


def _format_existing_unit_price_range(low, high) -> str:
    if pd.isna(low) and pd.isna(high):
        return "—"
    if pd.notna(low) and pd.notna(high):
        return (
            f"{format_man(yen_to_man(float(low)))}〜{format_man(yen_to_man(float(high)))} 万円/m²"
        )
    value = low if pd.notna(low) else high
    return f"{format_man(yen_to_man(float(value)))} 万円/m²"


def _text_or_dash(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _format_area(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.1f} m²"


def _format_yen(value, *, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.0f} 円{suffix}"


def _format_pct0(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.0f}%"


def _format_pct1(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.1f}%"


def _format_signed_pct(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):+.1f}%"


def _format_int_suffix(value, suffix: str, *, prefix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{prefix}{int(value)}{suffix}"


def _format_float_suffix(value, suffix: str, *, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f} {suffix}".replace("  ", " ")


def _format_unit_price(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{format_man(yen_to_man(float(value)))} 万円/m²"


def _format_tsubo_unit_price(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{format_man(yen_to_man(float(value) * SQM_PER_TSUBO))} 万円/坪"


def _flag_label(value, *, positive: str = "あり") -> str:
    if value is None or pd.isna(value):
        return "—"
    return positive if bool(value) else "なし"


def _hazard_label(flag, rank) -> str:
    if flag is None or pd.isna(flag):
        return "—"
    if not bool(flag):
        return "なし"
    rank_text = _text_or_dash(rank)
    return f"警戒 ({rank_text})" if rank_text != "—" else "警戒"
