"""
ui/rent_market_tab.py
e-Stat 市区町村別賃料データの俯瞰タブ。
"""
from __future__ import annotations

import plotly.express as px
import pandas as pd
import streamlit as st

import db
from ui.table import muted, num_str, plain, render_html_table
from ui.constants import PREFECTURE_NAMES as _PREF_NAMES


_OWNERSHIP_LABELS = {
    "total": "総数",
    "private": "民営借家",
    "public": "公営借家",
    "kiko": "UR・公社",
    "company": "給与住宅",
}


_MAJOR_PREFS_FIRST = ["東京都", "神奈川県", "大阪府", "愛知県", "福岡県", "北海道", "沖縄県"]
_PREF_SEPARATOR = "──────────"

_FLOOR_AREA_ASSUMPTIONS_SQM: dict[str, tuple[int, int]] = {
    "ワンルーム": (18, 25),
    "1K/1DK": (22, 35),
    "1LDK/2K/2DK": (35, 50),
    "2LDK/3K/3DK": (50, 70),
    "3LDK/4K～": (70, 95),
}


def render_rent_market_tab(conn) -> None:
    st.header("🏘 賃料相場")
    st.caption("e-Stat 住宅・土地統計調査の市区町村別「延べ面積1m²当たり家賃」を俯瞰します。")

    df = db.read_rent_market_overview(conn)
    if df.empty:
        st.info("賃料相場データがありません。Admin または CLI から `sync_rent_market.py` を実行してください。")
        st.code("python sync_rent_market.py --year 2023", language="bash")
        return

    df = _prepare_display_df(df)
    _render_timeseries_section(df)
    filtered = _render_filters(df)
    if filtered.empty:
        st.info("条件に一致する賃料データがありません。フィルターを緩めてください。")
        return

    _render_summary(filtered)
    _render_charts(filtered)
    _render_table(filtered)
    _render_suumo_section(conn)


def _prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["prefecture_name"] = result["prefecture_name"].fillna(result["prefecture_code"].map(_PREF_NAMES))
    result["prefecture_name"] = result["prefecture_name"].fillna(result["prefecture_code"])
    result["city_name"] = result["city_name"].fillna(result["city_code"])
    result["ownership_label"] = result["ownership_type"].map(_OWNERSHIP_LABELS).fillna(result["ownership_type"])
    result["rent_per_sqm"] = pd.to_numeric(result["rent_per_sqm"], errors="coerce")
    result["rent_50sqm"] = result["rent_per_sqm"] * 50
    result["rent_70sqm"] = result["rent_per_sqm"] * 70
    return result.dropna(subset=["rent_per_sqm"])


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    c1, c2, c3, c4 = st.columns(4)
    years = sorted(df["survey_year"].dropna().astype(int).unique().tolist(), reverse=True)
    ownerships = _ordered_labels(df, "ownership_label", ["民営借家", "総数", "公営借家", "UR・公社", "給与住宅"])
    prefs = _pref_ordered_options(df["prefecture_name"].dropna().unique().tolist())

    year = c1.selectbox("調査年", years, index=0, key="rent_market_year")
    ownership = c2.selectbox("所有区分", ownerships, index=0 if ownerships else None, key="rent_market_ownership")
    selected_prefs = c3.multiselect("都道府県", prefs, key="rent_market_pref")
    min_rent = c4.number_input("最低賃料 円/m²", min_value=0, value=0, step=100, key="rent_market_min_rent")

    keyword = st.text_input("市区町村キーワード", placeholder="例: 新宿区 / 那覇市", key="rent_market_keyword")

    result = df[(df["survey_year"].astype(int) == int(year)) & (df["ownership_label"] == ownership)].copy()
    if selected_prefs:
        selected_prefs = [pref for pref in selected_prefs if pref != _PREF_SEPARATOR]
    if selected_prefs:
        result = result[result["prefecture_name"].isin(selected_prefs)]
    if min_rent > 0:
        result = result[result["rent_per_sqm"] >= float(min_rent)]
    if keyword.strip():
        needle = keyword.strip()
        result = result[result["city_name"].fillna("").astype(str).str.contains(needle, case=False, na=False, regex=False)]
    return result


def _ordered_labels(df: pd.DataFrame, col: str, preferred: list[str]) -> list[str]:
    existing = set(df[col].dropna().astype(str).tolist())
    ordered = [label for label in preferred if label in existing]
    return ordered + sorted(existing - set(ordered))


def _pref_ordered_options(values) -> list[str]:
    existing = {str(value).strip() for value in values if str(value).strip()}
    ordered = [name for name in _MAJOR_PREFS_FIRST if name in existing]
    rest = [name for name in _PREF_NAMES.values() if name in existing and name not in ordered]
    extras = sorted(existing - set(ordered) - set(rest))
    if ordered and (rest or extras):
        return ordered + [_PREF_SEPARATOR] + rest + extras
    return ordered + rest + extras


def _render_timeseries_section(df: pd.DataFrame) -> None:
    """複数調査年のデータがある場合に賃料推移グラフを表示する。"""
    years = sorted(df["survey_year"].dropna().astype(int).unique().tolist())
    if len(years) < 2:
        return

    with st.expander("📈 賃料推移（複数年比較）", expanded=True):
        # 都市選択
        prefs = _pref_ordered_options(df["prefecture_name"].dropna().unique().tolist())
        sel_pref = st.selectbox(
            "都道府県",
            [p for p in prefs if p != _PREF_SEPARATOR],
            index=0,
            key="rent_ts_pref",
        )
        cities_in_pref = sorted(
            df[df["prefecture_name"] == sel_pref]["city_name"].dropna().unique().tolist()
        )
        sel_cities = st.multiselect(
            "市区町村（複数選択で比較）",
            cities_in_pref,
            default=cities_in_pref[:3],
            key="rent_ts_cities",
        )
        ownerships = _ordered_labels(df, "ownership_label", ["民営借家", "総数", "公営借家"])
        sel_ownership = st.selectbox("所有区分", ownerships, key="rent_ts_ownership")

        if not sel_cities:
            st.caption("市区町村を選択してください。")
            return

        ts = df[
            (df["city_name"].isin(sel_cities))
            & (df["ownership_label"] == sel_ownership)
        ][["survey_year", "city_name", "rent_per_sqm"]].copy()
        ts["survey_year"] = ts["survey_year"].astype(int)
        ts = ts.sort_values("survey_year")

        if ts.empty:
            st.caption("選択条件のデータがありません。")
            return

        fig = px.line(
            ts,
            x="survey_year",
            y="rent_per_sqm",
            color="city_name",
            markers=True,
            labels={"survey_year": "調査年", "rent_per_sqm": "円/m²", "city_name": "市区町村"},
            height=340,
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,27,42,0.6)",
            font_color="#c8dff0",
            legend={"title": ""},
            xaxis={"tickmode": "array", "tickvals": years},
        )
        fig.update_traces(line_width=2, marker_size=7)
        st.plotly_chart(fig, use_container_width=True)

        # 変化率サマリー
        if len(years) >= 2:
            base_yr, latest_yr = years[0], years[-1]
            base = ts[ts["survey_year"] == base_yr][["city_name", "rent_per_sqm"]].set_index("city_name")
            latest = ts[ts["survey_year"] == latest_yr][["city_name", "rent_per_sqm"]].set_index("city_name")
            merged = base.join(latest, lsuffix="_base", rsuffix="_latest").dropna()
            if not merged.empty:
                merged["change_pct"] = (merged["rent_per_sqm_latest"] - merged["rent_per_sqm_base"]) / merged["rent_per_sqm_base"] * 100
                cols = st.columns(min(len(merged), 4))
                for i, (city, row) in enumerate(merged.iterrows()):
                    if i >= 4:
                        break
                    chg = row["change_pct"]
                    sign = "+" if chg >= 0 else ""
                    delta_color = "#81c784" if chg >= 0 else "#ef9a9a"
                    cols[i].markdown(
                        f"""<div style="background:#132035;border:1px solid #243d5e;border-radius:8px;padding:10px 12px;">
                        <div style="color:#95b8cf;font-size:0.72rem;">{city}</div>
                        <div style="color:#e8f4ff;font-size:1rem;font-weight:700;">{row['rent_per_sqm_latest']:,.0f} 円/m²</div>
                        <div style="color:{delta_color};font-size:0.8rem;">{sign}{chg:.1f}% ({base_yr}→{latest_yr})</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )


def _render_summary(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("市区町村数", f"{df['city_code'].nunique():,}")
    c2.metric("中央値", f"{df['rent_per_sqm'].median():,.0f} 円/m²")
    c3.metric("上位10%目安", f"{df['rent_per_sqm'].quantile(0.9):,.0f} 円/m²")
    c4.metric("70m²換算中央値", f"{(df['rent_per_sqm'].median() * 70) / 1e4:,.1f} 万円/月")


def _render_charts(df: pd.DataFrame) -> None:
    left, right = st.columns([1.1, 1])

    top = df.sort_values("rent_per_sqm", ascending=False).head(25).copy()
    top["label"] = top["city_name"] + "（" + top["prefecture_name"] + "）"
    with left:
        st.markdown("#### 高賃料エリア TOP25")
        fig = px.bar(
            top.sort_values("rent_per_sqm"),
            x="rent_per_sqm",
            y="label",
            orientation="h",
            labels={"rent_per_sqm": "円/m²", "label": "市区町村"},
            color="rent_per_sqm",
            color_continuous_scale="Blues",
            height=620,
        )
        fig.update_layout(margin={"l": 0, "r": 0, "t": 10, "b": 0}, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### 都道府県別分布")
        pref_counts = df["prefecture_name"].value_counts()
        valid_prefs = pref_counts[pref_counts >= 3].index
        box_df = df[df["prefecture_name"].isin(valid_prefs)].copy()
        if box_df.empty:
            st.info("分布表示に必要な件数がありません。")
        else:
            pref_order = (
                box_df.groupby("prefecture_name")["rent_per_sqm"]
                .median()
                .sort_values(ascending=False)
                .index
                .tolist()
            )
            fig = px.box(
                box_df,
                x="rent_per_sqm",
                y="prefecture_name",
                category_orders={"prefecture_name": pref_order},
                labels={"rent_per_sqm": "円/m²", "prefecture_name": "都道府県"},
                height=620,
            )
            fig.update_layout(margin={"l": 0, "r": 0, "t": 10, "b": 0})
            st.plotly_chart(fig, use_container_width=True)


def _render_table(df: pd.DataFrame) -> None:
    st.markdown("#### 市区町村一覧")
    table = df.copy()
    table["rent_per_sqm_label"] = table["rent_per_sqm"].map(lambda v: f"{v:,.0f}")
    table["rent_50sqm_label"] = table["rent_50sqm"].map(lambda v: f"{v/1e4:,.1f}")
    table["rent_70sqm_label"] = table["rent_70sqm"].map(lambda v: f"{v/1e4:,.1f}")
    table = table.sort_values("rent_per_sqm", ascending=False)
    render_html_table(
        table,
        [
            {"key": "survey_year", "label": "年", "width": 58, "align": "right", "render": num_str},
            {"key": "ownership_label", "label": "区分", "width": 86, "render": muted},
            {"key": "prefecture_name", "label": "都道府県", "width": 82, "render": muted},
            {"key": "city_name", "label": "市区町村", "width": 140, "render": plain},
            {"key": "city_code", "label": "コード", "width": 70, "render": muted},
            {"key": "rent_per_sqm_label", "label": "円/m²", "width": 86, "align": "right", "render": num_str},
            {"key": "rent_50sqm_label", "label": "50m²万円/月", "width": 106, "align": "right", "render": num_str},
            {"key": "rent_70sqm_label", "label": "70m²万円/月", "width": 106, "align": "right", "render": num_str},
        ],
        caption=f"{len(table):,} 件",
        min_width=760,
        max_height=520,
    )


def _render_suumo_section(conn) -> None:
    suumo = db.read_suumo_rent_market(conn)
    if suumo.empty:
        st.markdown("---")
        st.markdown("#### SUUMO賃貸相場")
        st.info("SUUMO賃貸相場データは未取得です。")
        st.code(".venv/bin/python sync_suumo_rent_market.py --pref okinawa", language="bash")
        return

    st.markdown("---")
    st.markdown("#### SUUMO賃貸相場")
    st.caption("SUUMO登録賃貸物件を元にした目安です。掲載中物件の平均金額とは異なる場合があります。")
    st.info(
        "SUUMO家賃相場は月額賃料のみのため、㎡単価は間取り帯ごとの代表面積レンジで割った推定値です。"
        "前提: ワンルーム18〜25㎡、1K/1DK 22〜35㎡、1LDK/2K/2DK 35〜50㎡、"
        "2LDK/3K/3DK 50〜70㎡、3LDK/4K〜 70〜95㎡。"
    )

    work = suumo.copy()
    work["monthly_rent_yen"] = pd.to_numeric(work["monthly_rent_yen"], errors="coerce")
    work["monthly_rent_man"] = work["monthly_rent_yen"] / 1e4
    work = _add_suumo_unit_price_assumptions(work)

    c1, c2, c3 = st.columns(3)
    prefs = _pref_ordered_options(work["prefecture_name"].dropna().unique().tolist())
    default_prefs = ["沖縄県"] if "沖縄県" in prefs else prefs[:1]
    selected_prefs = c1.multiselect("SUUMO都道府県", prefs, default=default_prefs, key="suumo_rent_pref")
    property_types = ["建物種別全体平均"] + sorted(work["property_type_label"].dropna().unique().tolist())
    selected_property = c2.selectbox("建物種別", property_types, key="suumo_rent_property_type")
    floor_plans = ["間取り全体平均"] + _floor_plan_ordered_options(work["floor_plan_bucket"].dropna().unique().tolist())
    selected_floor = c3.selectbox("間取り帯", floor_plans, key="suumo_rent_floor")

    if selected_prefs:
        selected_prefs = [pref for pref in selected_prefs if pref != _PREF_SEPARATOR]
    if selected_prefs:
        work = work[work["prefecture_name"].isin(selected_prefs)]
    if selected_floor == "間取り全体平均":
        work = _aggregate_suumo_floor_plan_average(work)
    else:
        work = work[work["floor_plan_bucket"] == selected_floor].copy()
    if selected_property == "建物種別全体平均":
        work = _aggregate_suumo_property_type_average(work)
    else:
        work = work[work["property_type_label"] == selected_property].copy()
    if work.empty:
        st.info("条件に一致するSUUMO相場データがありません。")
        return

    top = work.sort_values("unit_price_mid_yen_per_sqm", ascending=False).head(25).sort_values("unit_price_mid_yen_per_sqm")
    fig = px.scatter(
        top,
        x="unit_price_mid_yen_per_sqm",
        y="city_name",
        error_x="unit_price_error_plus",
        error_x_minus="unit_price_error_minus",
        labels={"unit_price_mid_yen_per_sqm": "推定円/m²", "city_name": "市区郡"},
        color="unit_price_mid_yen_per_sqm",
        color_continuous_scale="Greens",
        height=460,
    )
    fig.update_traces(marker={"size": 10, "line": {"width": 1, "color": "#e8f4ff"}})
    fig.update_layout(margin={"l": 0, "r": 0, "t": 10, "b": 0}, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    table = work.sort_values("unit_price_mid_yen_per_sqm", ascending=False).copy()
    table["monthly_rent_label"] = table["monthly_rent_man"].map(lambda v: f"{v:,.1f}")
    table["area_range_label"] = table.apply(_format_area_assumption, axis=1)
    table["unit_price_range_label"] = table.apply(_format_unit_price_range, axis=1)
    table["updated_date_label"] = table["updated_date"].astype(str)
    render_html_table(
        table,
        [
            {"key": "updated_date_label", "label": "更新日", "width": 96, "render": muted},
            {"key": "prefecture_name", "label": "都道府県", "width": 82, "render": muted},
            {"key": "city_name", "label": "市区郡", "width": 130, "render": plain},
            {"key": "property_type_label", "label": "建物種別", "width": 110, "render": muted},
            {"key": "floor_plan_bucket", "label": "間取り帯", "width": 120, "render": muted},
            {"key": "monthly_rent_label", "label": "万円/月", "width": 86, "align": "right", "render": num_str},
            {"key": "area_range_label", "label": "代表面積", "width": 92, "align": "right", "render": muted},
            {"key": "unit_price_range_label", "label": "推定円/m²", "width": 132, "align": "right", "render": num_str},
        ],
        caption=f"{len(table):,} 件",
        min_width=920,
        max_height=520,
    )


def _add_suumo_unit_price_assumptions(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["assumed_area_min_sqm"] = result["floor_plan_bucket"].map(
        lambda value: _FLOOR_AREA_ASSUMPTIONS_SQM.get(str(value), (None, None))[0]
    )
    result["assumed_area_max_sqm"] = result["floor_plan_bucket"].map(
        lambda value: _FLOOR_AREA_ASSUMPTIONS_SQM.get(str(value), (None, None))[1]
    )
    min_area = pd.to_numeric(result["assumed_area_min_sqm"], errors="coerce")
    max_area = pd.to_numeric(result["assumed_area_max_sqm"], errors="coerce")
    rent = pd.to_numeric(result["monthly_rent_yen"], errors="coerce")
    result["unit_price_low_yen_per_sqm"] = rent / max_area
    result["unit_price_high_yen_per_sqm"] = rent / min_area
    result["unit_price_mid_yen_per_sqm"] = (
        result["unit_price_low_yen_per_sqm"] + result["unit_price_high_yen_per_sqm"]
    ) / 2
    result["unit_price_error_minus"] = result["unit_price_mid_yen_per_sqm"] - result["unit_price_low_yen_per_sqm"]
    result["unit_price_error_plus"] = result["unit_price_high_yen_per_sqm"] - result["unit_price_mid_yen_per_sqm"]
    return result


def _floor_plan_ordered_options(values) -> list[str]:
    existing = {str(value).strip() for value in values if str(value).strip()}
    ordered = [name for name in _FLOOR_AREA_ASSUMPTIONS_SQM if name in existing]
    return ordered + sorted(existing - set(ordered))


def _aggregate_suumo_floor_plan_average(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    grouped = (
        df.groupby(["prefecture_name", "city_name", "property_type_label"], as_index=False)
        .agg(
            monthly_rent_yen=("monthly_rent_yen", "mean"),
            monthly_rent_man=("monthly_rent_man", "mean"),
            unit_price_low_yen_per_sqm=("unit_price_low_yen_per_sqm", "mean"),
            unit_price_high_yen_per_sqm=("unit_price_high_yen_per_sqm", "mean"),
            updated_date=("updated_date", "max"),
            floor_plan_count=("floor_plan_bucket", "count"),
        )
    )
    grouped["floor_plan_bucket"] = "間取り全体平均"
    grouped["assumed_area_min_sqm"] = pd.NA
    grouped["assumed_area_max_sqm"] = pd.NA
    grouped["unit_price_mid_yen_per_sqm"] = (
        grouped["unit_price_low_yen_per_sqm"] + grouped["unit_price_high_yen_per_sqm"]
    ) / 2
    grouped["unit_price_error_minus"] = grouped["unit_price_mid_yen_per_sqm"] - grouped["unit_price_low_yen_per_sqm"]
    grouped["unit_price_error_plus"] = grouped["unit_price_high_yen_per_sqm"] - grouped["unit_price_mid_yen_per_sqm"]
    return grouped


def _aggregate_suumo_property_type_average(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    group_cols = ["prefecture_name", "city_name", "floor_plan_bucket"]
    aggregations = {
        "monthly_rent_yen": ("monthly_rent_yen", "mean"),
        "monthly_rent_man": ("monthly_rent_man", "mean"),
        "unit_price_low_yen_per_sqm": ("unit_price_low_yen_per_sqm", "mean"),
        "unit_price_high_yen_per_sqm": ("unit_price_high_yen_per_sqm", "mean"),
        "updated_date": ("updated_date", "max"),
        "property_type_count": ("property_type_label", "count"),
    }
    if "floor_plan_count" in df.columns:
        aggregations["floor_plan_count"] = ("floor_plan_count", "sum")
    grouped = (
        df.groupby(group_cols, as_index=False)
        .agg(**aggregations)
    )
    grouped["property_type_label"] = "建物種別全体平均"
    grouped["assumed_area_min_sqm"] = pd.NA
    grouped["assumed_area_max_sqm"] = pd.NA
    grouped["unit_price_mid_yen_per_sqm"] = (
        grouped["unit_price_low_yen_per_sqm"] + grouped["unit_price_high_yen_per_sqm"]
    ) / 2
    grouped["unit_price_error_minus"] = grouped["unit_price_mid_yen_per_sqm"] - grouped["unit_price_low_yen_per_sqm"]
    grouped["unit_price_error_plus"] = grouped["unit_price_high_yen_per_sqm"] - grouped["unit_price_mid_yen_per_sqm"]
    return grouped


def _format_area_assumption(row: pd.Series) -> str:
    if row.get("floor_plan_bucket") == "間取り全体平均":
        count = row.get("floor_plan_count")
        return f"{int(count)}間取り平均" if pd.notna(count) else "全体平均"
    low = row.get("assumed_area_min_sqm")
    high = row.get("assumed_area_max_sqm")
    if pd.isna(low) or pd.isna(high):
        return "—"
    return f"{int(low)}〜{int(high)}㎡"


def _format_unit_price_range(row: pd.Series) -> str:
    low = row.get("unit_price_low_yen_per_sqm")
    high = row.get("unit_price_high_yen_per_sqm")
    if pd.isna(low) or pd.isna(high):
        return "—"
    return f"推定 {float(low):,.0f}〜{float(high):,.0f}"
