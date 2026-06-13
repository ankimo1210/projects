"""
ui/search_tab.py
Search タブ: テーブル検索・ソート・CSV ダウンロード。
"""

import io
import math

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.table import (
    area_num,
    gap_bar,
    muted,
    price_man,
    render_html_table,
    truncate,
    use_category_badge,
    year_num,
)
from ui.unit_price import (
    add_tsubo_price_column,
    convert_yen_columns_to_man,
    format_yen_per_sqm_with_tsubo,
    yen_to_man,
)

_DISPLAY_COLS = [
    "point_id",
    "standard_land_number",
    "location_text",
    "city_name",
    "prefecture_name",
    "use_category_name",
    "price_yen_per_sqm",
    "last_year_price_yen_per_sqm",
    "yoy_change_pct",
    "area_sqm",
    "year",
]

_COL_LABELS = {
    "point_id": "地点ID",
    "standard_land_number": "標準地番号",
    "location_text": "所在地",
    "city_name": "市区町村",
    "prefecture_name": "都道府県",
    "use_category_name": "用途区分",
    "price_yen_per_sqm": "価格(万円/m²)",
    "price_yen_per_tsubo": "坪(万円/坪)",
    "last_year_price_yen_per_sqm": "前年価格",
    "last_year_price_yen_per_tsubo": "前年坪",
    "yoy_change_pct": "前年比(%)",
    "area_sqm": "面積(m²)",
    "year": "年度",
}


def render_search_tab(df: pd.DataFrame | None, filters: dict) -> None:
    st.header("🔍 地点検索")

    if df is None or df.empty:
        st.info("データがありません。Admin タブからデータを同期してください。")
        return

    filtered = _apply_search_controls(df)
    _render_summary(filtered)

    if filtered.empty:
        st.warning("条件に合う地点がありません。フィルタを少し緩めてください。")
        return

    st.markdown("---")
    _render_insights(filtered, filters)
    st.markdown("---")

    # 表示列のみ抽出
    show_cols = [c for c in _DISPLAY_COLS if c in filtered.columns]
    display_df = filtered[show_cols].copy()
    display_df = add_tsubo_price_column(display_df, "price_yen_per_sqm", "price_yen_per_tsubo")
    display_df = add_tsubo_price_column(
        display_df, "last_year_price_yen_per_sqm", "last_year_price_yen_per_tsubo"
    )
    display_df = convert_yen_columns_to_man(
        display_df, ["price_yen_per_sqm", "last_year_price_yen_per_sqm"]
    )
    render_html_table(
        display_df,
        [
            {"key": "year", "label": "年度", "width": 50, "align": "right", "render": year_num},
            {
                "key": "location_text",
                "label": "所在地",
                "width": 180,
                "render": lambda v: truncate(v, 170),
            },
            {"key": "city_name", "label": "市区町村", "width": 90, "render": muted},
            {"key": "prefecture_name", "label": "都道府県", "width": 70, "render": muted},
            {
                "key": "use_category_name",
                "label": "用途",
                "width": 75,
                "render": use_category_badge,
            },
            {
                "key": "price_yen_per_sqm",
                "label": "価格(万/m²)",
                "width": 85,
                "align": "right",
                "render": price_man,
            },
            {
                "key": "price_yen_per_tsubo",
                "label": "坪(万/坪)",
                "width": 75,
                "align": "right",
                "render": price_man,
            },
            {
                "key": "last_year_price_yen_per_sqm",
                "label": "前年価格",
                "width": 75,
                "align": "right",
                "render": price_man,
            },
            {
                "key": "last_year_price_yen_per_tsubo",
                "label": "前年坪",
                "width": 65,
                "align": "right",
                "render": price_man,
            },
            {"key": "yoy_change_pct", "label": "前年比", "width": 130, "render": gap_bar},
            {
                "key": "area_sqm",
                "label": "面積(m²)",
                "width": 75,
                "align": "right",
                "render": area_num,
            },
        ],
        caption=f"{len(display_df):,} 件",
        min_width=900,
    )

    # CSV ダウンロード
    csv_buf = io.StringIO()
    filtered[show_cols].to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 CSV ダウンロード",
        data=csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"land_prices_{filters.get('year', 'all')}.csv",
        mime="text/csv",
    )


def _apply_search_controls(df: pd.DataFrame) -> pd.DataFrame:
    """検索・絞り込み・ソートの UI を描画し、条件適用後の DataFrame を返す。"""
    result = df.copy()

    keyword = st.text_input(
        "所在地・市区町村・標準地番号を検索",
        placeholder="例: 東京都, 新宿区, 銀座, 住宅地",
        key="search_keyword",
    )
    if keyword:
        keyword_cols = [
            "location_text",
            "city_name",
            "prefecture_name",
            "standard_land_number",
            "use_category_name",
            "zoning_name",
        ]
        mask = pd.Series(False, index=result.index)
        for col in keyword_cols:
            if col in result.columns:
                mask |= (
                    result[col].astype(str).str.contains(keyword, case=False, na=False, regex=False)
                )
        result = result[mask].copy()

    with st.expander("条件フィルタ", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            pref_labels = _option_labels(result, "prefecture_code", "prefecture_name")
            selected_pref_labels = st.multiselect(
                "都道府県",
                pref_labels,
                default=[],
                placeholder="すべて",
                key="search_prefectures",
            )
            if selected_pref_labels and "prefecture_code" in result.columns:
                selected_codes = [_split_code_label(v)[0] for v in selected_pref_labels]
                result = result[result["prefecture_code"].isin(selected_codes)].copy()

        with c2:
            city_labels = _option_labels(result, "city_code", "city_name")
            selected_city_labels = st.multiselect(
                "市区町村",
                city_labels,
                default=[],
                placeholder="すべて",
                key="search_cities",
            )
            if selected_city_labels and "city_code" in result.columns:
                selected_codes = [_split_code_label(v)[0] for v in selected_city_labels]
                result = result[result["city_code"].isin(selected_codes)].copy()

        with c3:
            use_options = _sorted_unique(result, "use_category_name")
            selected_uses = st.multiselect(
                "用途区分",
                use_options,
                default=[],
                placeholder="すべて",
                key="search_use_categories",
            )
            if selected_uses and "use_category_name" in result.columns:
                result = result[result["use_category_name"].isin(selected_uses)].copy()

        c4, c5, c6 = st.columns(3)
        result = _apply_price_range(
            c4, result, "price_yen_per_sqm", "価格レンジ (万円/m²)", "search_price_range"
        )
        result = _apply_numeric_range(
            c5, result, "yoy_change_pct", "前年比レンジ (%)", "search_yoy_range", round_to=0.1
        )
        result = _apply_numeric_range(
            c6, result, "area_sqm", "面積レンジ (m²)", "search_area_range", round_to=1
        )

        c7, c8 = st.columns([2, 1])
        sortable = {
            "価格(万円/m²)": "price_yen_per_sqm",
            "前年比(%)": "yoy_change_pct",
            "面積(m²)": "area_sqm",
            "市区町村": "city_name",
            "所在地": "location_text",
        }
        available_sort = {label: col for label, col in sortable.items() if col in result.columns}
        with c7:
            sort_label = st.selectbox(
                "並び替え",
                list(available_sort.keys()),
                index=0,
                key="search_sort_col",
            )
        with c8:
            sort_desc = st.toggle("降順", value=True, key="search_sort_desc")

    sort_col = available_sort.get(sort_label)
    if sort_col:
        result = result.sort_values(sort_col, ascending=not sort_desc, na_position="last")

    return result.reset_index(drop=True)


def _render_summary(df: pd.DataFrame) -> None:
    """絞り込み結果の主要指標を表示する。"""
    price = df["price_yen_per_sqm"] if "price_yen_per_sqm" in df.columns else pd.Series(dtype=float)
    yoy = df["yoy_change_pct"] if "yoy_change_pct" in df.columns else pd.Series(dtype=float)
    area = df["area_sqm"] if "area_sqm" in df.columns else pd.Series(dtype=float)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("該当地点", f"{len(df):,}件")
    c2.metric(
        "中央値価格", format_yen_per_sqm_with_tsubo(price.median()) if price.notna().any() else "—"
    )
    c3.metric("平均前年比", f"{yoy.mean():+.2f}%" if yoy.notna().any() else "—")
    c4.metric("平均面積", f"{area.mean():,.0f}m²" if area.notna().any() else "—")


def _render_insights(df: pd.DataFrame, filters: dict) -> None:
    """絞り込み後データの簡易分析チャートを表示する。"""
    tab_use, tab_city, tab_dist = st.tabs(["用途別", "市区町村", "分布"])

    with tab_use:
        if "use_category_name" not in df.columns or df["use_category_name"].dropna().empty:
            st.info("用途区分データがありません。")
        else:
            use_df = (
                df.dropna(subset=["price_yen_per_sqm"])
                .groupby("use_category_name", as_index=False)
                .agg(
                    平均価格=("price_yen_per_sqm", "mean"),
                    地点数=("point_id", "count"),
                    平均前年比=("yoy_change_pct", "mean"),
                )
                .sort_values("平均価格", ascending=True)
            )
            use_df["平均価格"] = use_df["平均価格"].map(yen_to_man)
            fig = px.bar(
                use_df,
                x="平均価格",
                y="use_category_name",
                orientation="h",
                color="平均前年比",
                color_continuous_scale="RdBu_r",
                color_continuous_midpoint=0,
                text="地点数",
                labels={
                    "use_category_name": "用途区分",
                    "平均価格": "平均価格(万円/m²)",
                    "平均前年比": "平均前年比(%)",
                },
                title="用途別 平均価格",
            )
            fig.update_traces(texttemplate="%{text:,}件", textposition="outside")
            fig.update_layout(**_base_layout(height=max(320, len(use_df) * 54)))
            fig.update_xaxes(tickformat=",.1f")
            st.plotly_chart(fig, use_container_width=True)

    with tab_city:
        required = {"city_name", "price_yen_per_sqm", "point_id"}
        if not required.issubset(df.columns):
            st.info("市区町村別集計に必要なデータがありません。")
        else:
            min_points = st.slider(
                "市区町村の最小地点数",
                min_value=1,
                max_value=20,
                value=3,
                step=1,
                key="search_city_min_points",
            )
            city_df = (
                df.dropna(subset=["price_yen_per_sqm"])
                .groupby(["prefecture_name", "city_name"], dropna=False, as_index=False)
                .agg(
                    平均価格=("price_yen_per_sqm", "mean"),
                    中央値=("price_yen_per_sqm", "median"),
                    地点数=("point_id", "count"),
                    平均前年比=("yoy_change_pct", "mean"),
                )
            )
            city_df = city_df[city_df["地点数"] >= min_points].nlargest(20, "平均価格")
            if city_df.empty:
                st.info("条件を満たす市区町村がありません。")
            else:
                city_df["表示名"] = (
                    city_df["city_name"].fillna("")
                    + "（"
                    + city_df["prefecture_name"].fillna("")
                    + "）"
                )
                plot_df = city_df.sort_values("平均価格").copy()
                plot_df["平均価格"] = plot_df["平均価格"].map(yen_to_man)
                fig = px.bar(
                    plot_df,
                    x="平均価格",
                    y="表示名",
                    orientation="h",
                    color="平均前年比",
                    color_continuous_scale="RdBu_r",
                    color_continuous_midpoint=0,
                    text="地点数",
                    labels={
                        "平均価格": "平均価格(万円/m²)",
                        "表示名": "市区町村",
                        "平均前年比": "平均前年比(%)",
                    },
                    title=f"市区町村別 平均価格 TOP20 ({filters.get('year', 'all')}年)",
                )
                fig.update_traces(texttemplate="%{text:,}件", textposition="outside")
                layout = _base_layout(height=max(420, len(plot_df) * 28))
                layout["margin"] = dict(l=180, r=90, t=50, b=45)
                fig.update_layout(**layout)
                fig.update_xaxes(tickformat=",.1f")
                st.plotly_chart(fig, use_container_width=True)

    with tab_dist:
        plot = (
            df.dropna(subset=["price_yen_per_sqm"]).copy()
            if "price_yen_per_sqm" in df.columns
            else pd.DataFrame()
        )
        if plot.empty:
            st.info("価格データがありません。")
        else:
            plot["price_man_per_sqm"] = plot["price_yen_per_sqm"].map(yen_to_man)
            color_col = "use_category_name" if "use_category_name" in plot.columns else None
            fig = px.histogram(
                plot,
                x="price_man_per_sqm",
                color=color_col,
                nbins=40,
                labels={"price_man_per_sqm": "価格(万円/m²)", "use_category_name": "用途区分"},
                title="価格分布",
            )
            fig.update_layout(**_base_layout(height=380))
            fig.update_xaxes(tickformat=",.1f")
            st.plotly_chart(fig, use_container_width=True)


def _apply_numeric_range(
    container, df: pd.DataFrame, col: str, label: str, key: str, round_to: float
) -> pd.DataFrame:
    """数値列のレンジスライダーを適用する。"""
    with container:
        if col not in df.columns or df[col].dropna().empty:
            st.caption(f"{label}: データなし")
            return df

        values = df[col].dropna()
        min_v = _round_down(float(values.min()), round_to)
        max_v = _round_up(float(values.max()), round_to)
        if min_v == max_v:
            st.caption(f"{label}: {min_v:g}")
            return df

        selected = st.slider(
            label,
            min_value=float(min_v),
            max_value=float(max_v),
            value=(float(min_v), float(max_v)),
            step=float(round_to),
            key=key,
        )
    return df[df[col].between(selected[0], selected[1], inclusive="both")].copy()


def _apply_price_range(container, df: pd.DataFrame, col: str, label: str, key: str) -> pd.DataFrame:
    """円/m²列を万円/m²のレンジとして表示・適用する。"""
    with container:
        if col not in df.columns or df[col].dropna().empty:
            st.caption(f"{label}: データなし")
            return df

        values = df[col].dropna().map(yen_to_man)
        min_v = _round_down(float(values.min()), 0.1)
        max_v = _round_up(float(values.max()), 0.1)
        if min_v == max_v:
            st.caption(f"{label}: {min_v:.1f}")
            return df

        selected = st.slider(
            label,
            min_value=float(min_v),
            max_value=float(max_v),
            value=(float(min_v), float(max_v)),
            step=0.1,
            key=key,
        )
    lo_yen, hi_yen = selected[0] * 10_000, selected[1] * 10_000
    return df[df[col].between(lo_yen, hi_yen, inclusive="both")].copy()


def _option_labels(df: pd.DataFrame, code_col: str, name_col: str) -> list[str]:
    if code_col not in df.columns or name_col not in df.columns:
        return []
    rows = (
        df[[code_col, name_col]]
        .dropna()
        .drop_duplicates()
        .sort_values([code_col, name_col])
        .itertuples(index=False, name=None)
    )
    return [f"{code} | {name}" for code, name in rows]


def _split_code_label(label: str) -> str:
    return label.split(" | ", 1)[0]


def _sorted_unique(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())


def _round_down(value: float, unit: float) -> float:
    return math.floor(value / unit) * unit


def _round_up(value: float, unit: float) -> float:
    return math.ceil(value / unit) * unit


def _base_layout(height: int = 400) -> dict:
    return dict(
        height=height,
        template="plotly_dark",
        hovermode="y unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font_color="#c8dff0",
        legend=dict(orientation="h", y=-0.22, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=55, l=10, r=10),
    )
