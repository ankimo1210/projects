"""
ui/ranking_tab.py
Ranking タブ: 価格・変動率・市区町村別ランキング。
"""
import re
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

import analytics
from ui.unit_price import add_tsubo_price_column, convert_yen_columns_to_man, yen_to_man
from ui.table import render_html_table, gap_bar, price_man, truncate, muted, rank_num, count_num, use_category_badge


_USE_CATEGORY_OPTIONS = ["住宅地", "商業地", "工業地", "すべて"]


def render_ranking_tab(df: Optional[pd.DataFrame], filters: dict) -> None:
    st.header("🏆 ランキング")

    if df is None or df.empty:
        st.info("データがありません。")
        return

    year = filters.get("year")

    # 用途区分フィルタ（住宅地デフォルト）
    col_use, col_n = st.columns([3, 1])
    with col_use:
        available_cats = sorted(df["use_category_name"].dropna().unique().tolist()) if "use_category_name" in df.columns else []
        options = [c for c in _USE_CATEGORY_OPTIONS if c == "すべて" or c in available_cats]
        selected_use = st.radio(
            "用途区分",
            options,
            index=0,
            horizontal=True,
            key="ranking_use_category",
        )
    with col_n:
        top_n = st.slider("表示件数", 10, 100, 30, 10)

    filtered_df = df if selected_use == "すべて" else df[df["use_category_name"] == selected_use]

    tab1, tab2, tab3, tab4 = st.tabs(
        ["高価格", "変動率", "市区町村別平均", "🏛 都道府県別"]
    )

    with tab1:
        _render_price_ranking(filtered_df, year, top_n, show_category=(selected_use == "すべて"))

    with tab2:
        _render_yoy_combined(filtered_df, year, top_n, show_category=(selected_use == "すべて"))

    with tab3:
        _render_city_avg_ranking(filtered_df, year, top_n)

    with tab4:
        _render_pref_ranking(filtered_df, year)


def _render_price_ranking(df: pd.DataFrame, year, top_n: int, show_category: bool = True) -> None:
    st.subheader("価格ランキング（高い順）")
    ranked = analytics.compute_price_rankings(df, top_n=top_n, year=year)
    if ranked.empty:
        st.info("データなし")
        return

    show_cols = [c for c in [
        "rank", "location_text", "city_name", "prefecture_name",
        "use_category_name", "price_yen_per_sqm", "yoy_change_pct",
    ] if c in ranked.columns]
    display_df = add_tsubo_price_column(ranked[show_cols], "price_yen_per_sqm", "price_yen_per_tsubo")
    display_df = convert_yen_columns_to_man(display_df, ["price_yen_per_sqm"])
    col_specs = [
        {"key": "rank",              "label": "順位",       "width": 45,  "align": "right", "render": rank_num},
        {"key": "location_text",     "label": "所在地",     "width": 180, "render": lambda v: truncate(v, 170)},
        {"key": "city_name",         "label": "市区町村",   "width": 90,  "render": muted},
        {"key": "prefecture_name",   "label": "都道府県",   "width": 70,  "render": muted},
        {"key": "price_yen_per_sqm", "label": "価格(万/m²)","width": 85,  "align": "right", "render": price_man},
        {"key": "price_yen_per_tsubo","label": "坪(万/坪)", "width": 75,  "align": "right", "render": price_man},
        {"key": "yoy_change_pct",    "label": "前年比",     "width": 130, "render": gap_bar},
    ]
    if show_category:
        col_specs.insert(4, {"key": "use_category_name", "label": "用途", "width": 75, "render": use_category_badge})
    render_html_table(display_df, col_specs)

    # 棒グラフ（上位 20 件）
    plot_df = ranked.head(20).sort_values("price_yen_per_sqm")
    plot_df = plot_df.copy()
    plot_df["price_man_per_sqm"] = plot_df["price_yen_per_sqm"].map(yen_to_man)
    label = plot_df["location_text"].fillna(plot_df.get("city_name", ""))
    fig = px.bar(
        plot_df, x="price_man_per_sqm", y=label, orientation="h",
        labels={"price_man_per_sqm": "価格(万円/m²)", "y": "所在地"},
        title=f"価格ランキング TOP20 ({year}年)",
        text="price_man_per_sqm",
        color="price_man_per_sqm",
        color_continuous_scale="RdYlGn_r",
    )
    fig.update_traces(texttemplate="%{text:,.1f}", textposition="outside")
    fig.update_layout(height=max(400, len(plot_df) * 26), margin=dict(l=300))
    st.plotly_chart(fig, use_container_width=True)


def _render_yoy_combined(df: pd.DataFrame, year, top_n: int, show_category: bool = True) -> None:
    """上昇率・下落率を左右に並べて表示する。"""
    col_up, col_dn = st.columns(2)
    with col_up:
        _render_yoy_ranking(df, year, top_n, ascending=False, show_category=show_category)
    with col_dn:
        _render_yoy_ranking(df, year, top_n, ascending=True, show_category=show_category)


def _render_yoy_ranking(df: pd.DataFrame, year, top_n: int, ascending: bool, show_category: bool = True) -> None:
    title = "下落率ランキング" if ascending else "上昇率ランキング"
    st.subheader(title)
    ranked = analytics.compute_yoy_rankings(df, top_n=top_n, year=year, ascending=ascending)
    if ranked.empty:
        st.info("データなし（前年比データが必要です）")
        return

    show_cols = [c for c in [
        "location_text", "city_name", "prefecture_name",
        "use_category_name", "price_yen_per_sqm", "yoy_change_pct",
    ] if c in ranked.columns]
    display_df = add_tsubo_price_column(ranked[show_cols], "price_yen_per_sqm", "price_yen_per_tsubo")
    display_df = convert_yen_columns_to_man(display_df, ["price_yen_per_sqm"])
    col_specs = [
        {"key": "location_text",      "label": "所在地",     "width": 180, "render": lambda v: truncate(v, 170)},
        {"key": "city_name",          "label": "市区町村",   "width": 90,  "render": muted},
        {"key": "prefecture_name",    "label": "都道府県",   "width": 70,  "render": muted},
        {"key": "price_yen_per_sqm",  "label": "価格(万/m²)","width": 85,  "align": "right", "render": price_man},
        {"key": "price_yen_per_tsubo","label": "坪(万/坪)",  "width": 75,  "align": "right", "render": price_man},
        {"key": "yoy_change_pct",     "label": "前年比",     "width": 130, "render": gap_bar},
    ]
    if show_category:
        col_specs.insert(3, {"key": "use_category_name", "label": "用途", "width": 75, "render": use_category_badge})
    render_html_table(display_df, col_specs)

    plot_df = ranked.head(20).sort_values("yoy_change_pct", ascending=not ascending)
    label = plot_df["location_text"].fillna(plot_df.get("city_name", ""))
    color_scale = "Blues" if ascending else "Reds"
    fig = px.bar(
        plot_df, x="yoy_change_pct", y=label, orientation="h",
        labels={"yoy_change_pct": "前年比(%)", "y": "所在地"},
        title=f"{title} TOP20 ({year}年)",
        color="yoy_change_pct",
        color_continuous_scale=color_scale,
    )
    fig.update_layout(height=max(400, len(plot_df) * 26), margin=dict(l=300))
    st.plotly_chart(fig, use_container_width=True)


def _extract_neighborhood(location_text: str, city_name: str) -> str:
    """location_text から丁目・番以下を除いた町名を抽出する。
    例: "沖縄県那覇市古島３丁目…" + city="那覇市" → "古島"
    """
    if not location_text:
        return "不明"
    s = str(location_text)
    if city_name and city_name in s:
        s = s[s.index(city_name) + len(city_name):]
    s = s.lstrip("字")
    m = re.match(r"^([^\d０-９丁番号地先]+)", s)
    result = m.group(1).strip() if m and m.group(1).strip() else s[:12]
    return result or "不明"


def _render_city_avg_ranking(df: pd.DataFrame, year, top_n: int) -> None:
    st.subheader("市区町村別平均価格ランキング")
    city_df = analytics.compute_city_summary(df)
    if city_df.empty:
        st.info("データなし")
        return

    if year:
        city_df = city_df[city_df["year"] == year]

    # 用途区分を跨いで市区町村単位に集約（点数加重平均）
    grp = city_df.groupby(
        ["city_code", "city_name", "prefecture_code", "prefecture_name"], dropna=False
    )
    city_agg = grp.apply(
        lambda g: pd.Series({
            "avg_price":    (g["avg_price"] * g["point_count"]).sum() / g["point_count"].sum(),
            "median_price": g["median_price"].median(),
            "point_count":  g["point_count"].sum(),
            "avg_yoy_pct":  (g["avg_yoy_pct"] * g["point_count"]).sum() / g["point_count"].sum(),
        }),
        include_groups=False,
    ).reset_index()

    # ── 都道府県セレクタ ──────────────────────────────────────
    available_prefs = sorted(city_agg["prefecture_name"].dropna().unique().tolist())
    pref_options = ["全都道府県"] + available_prefs
    selected_pref = st.selectbox("都道府県で絞り込み", pref_options, key="city_rank_pref")

    if selected_pref == "全都道府県":
        display_df = city_agg.nlargest(top_n, "avg_price").copy()
        display_df["label"] = display_df["city_name"].fillna("") + "（" + display_df["prefecture_name"].fillna("") + "）"
        title_suffix = f"全都道府県 TOP{top_n}"
    else:
        display_df = city_agg[city_agg["prefecture_name"] == selected_pref].copy()
        display_df["label"] = display_df["city_name"].fillna("")
        title_suffix = selected_pref

    if display_df.empty:
        st.info("データなし")
        return

    n_rows = len(display_df)
    chart_h = max(320, n_rows * 28)

    # ── 価格 + 前年比を横並び（クリックで町丁目ドリルダウン） ──
    col_price, col_yoy = st.columns(2)
    event_p = event_y = None

    with col_price:
        sorted_p = display_df.sort_values("avg_price")
        sorted_p = sorted_p.copy()
        sorted_p["avg_price_man"] = sorted_p["avg_price"].map(yen_to_man)
        fig_p = px.bar(
            sorted_p, x="avg_price_man", y="label", orientation="h",
            text="avg_price_man", color="avg_price_man",
            color_continuous_scale="Blues_r",
            custom_data=["city_name"],
            labels={"avg_price_man": "平均価格(万円/m²)", "label": "市区町村"},
            title=f"平均価格 — {title_suffix} ({year}年)",
        )
        fig_p.update_traces(texttemplate="%{text:,.1f}", textposition="outside")
        fig_p.update_layout(
            **_base_layout(height=chart_h),
            xaxis=dict(tickformat=",.1f"),
            coloraxis_showscale=False,
            margin=dict(l=110, r=80, t=50, b=40),
        )
        event_p = st.plotly_chart(
            fig_p, use_container_width=True,
            on_select="rerun", selection_mode="points", key="city_price_chart",
        )

    with col_yoy:
        yoy_df = display_df.dropna(subset=["avg_yoy_pct"])
        if yoy_df.empty:
            st.info("前年比データなし")
        else:
            sorted_y = yoy_df.sort_values("avg_yoy_pct")
            abs_max = max(sorted_y["avg_yoy_pct"].abs().max(), 1.0)
            fig_y = px.bar(
                sorted_y, x="avg_yoy_pct", y="label", orientation="h",
                text="avg_yoy_pct", color="avg_yoy_pct",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                range_color=[-abs_max, abs_max],
                custom_data=["city_name"],
                labels={"avg_yoy_pct": "前年比(%)", "label": "市区町村"},
                title=f"前年比 — {title_suffix} ({year}年)",
            )
            fig_y.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
            fig_y.update_layout(
                **_base_layout(height=chart_h),
                xaxis=dict(ticksuffix="%", tickformat=".1f"),
                coloraxis_showscale=False,
                margin=dict(l=110, r=80, t=50, b=40),
            )
            event_y = st.plotly_chart(
                fig_y, use_container_width=True,
                on_select="rerun", selection_mode="points", key="city_yoy_chart",
            )

    # クリックされた市区町村を取得
    selected_city = None
    for ev in [event_p, event_y]:
        if ev and ev.selection and ev.selection.points:
            pt = ev.selection.points[0]
            cd = pt.get("customdata", [])
            selected_city = str(cd[0]) if cd else str(pt.get("y", ""))
            break

    # ── テーブル ─────────────────────────────────────────────
    table_df = display_df.sort_values("avg_price", ascending=False).reset_index(drop=True)
    table_df.insert(0, "順位", range(1, len(table_df) + 1))
    show_cols = ["順位", "city_name", "prefecture_name", "avg_price",
                 "median_price", "point_count", "avg_yoy_pct"]
    if selected_pref != "全都道府県":
        show_cols.remove("prefecture_name")
    display_table = table_df[[c for c in show_cols if c in table_df.columns]]
    display_table = add_tsubo_price_column(display_table, "avg_price", "avg_price_tsubo")
    display_table = add_tsubo_price_column(display_table, "median_price", "median_price_tsubo")
    display_table = convert_yen_columns_to_man(display_table, ["avg_price", "median_price"])
    render_html_table(display_table, [
        {"key": "順位",            "label": "順位",        "width": 45,  "align": "right", "render": rank_num},
        {"key": "city_name",       "label": "市区町村",    "width": 110, "render": muted},
        {"key": "prefecture_name", "label": "都道府県",    "width": 70,  "render": muted},
        {"key": "avg_price",       "label": "平均価格(万/m²)","width": 95,"align": "right", "render": price_man},
        {"key": "avg_price_tsubo", "label": "平均坪",      "width": 75,  "align": "right", "render": price_man},
        {"key": "median_price",    "label": "中央値",      "width": 75,  "align": "right", "render": price_man},
        {"key": "median_price_tsubo","label": "中央値坪",  "width": 65,  "align": "right", "render": price_man},
        {"key": "point_count",     "label": "地点数",      "width": 60,  "align": "right", "render": count_num},
        {"key": "avg_yoy_pct",     "label": "前年比",      "width": 130, "render": gap_bar},
    ])

    # ── 町丁目別ドリルダウン（グラフクリック時のみ） ─────────
    if selected_city:
        st.markdown("---")
        _render_neighborhood_detail(df, selected_city, year)


def _render_neighborhood_detail(df: pd.DataFrame, city_name: str, year) -> None:
    """市区町村内を町丁目単位で集計して価格・前年比ランキングを表示する。"""
    mask = df["city_name"] == city_name
    if year:
        mask &= df["year"] == year
    pts = df[mask].dropna(subset=["price_yen_per_sqm"]).copy()

    if pts.empty:
        st.info("地点データなし")
        return

    pts["neighborhood"] = pts["location_text"].apply(
        lambda t: _extract_neighborhood(str(t) if pd.notna(t) else "", city_name)
    )

    grp = pts.groupby("neighborhood")
    nbhd = grp.apply(
        lambda g: pd.Series({
            "avg_price":   g["price_yen_per_sqm"].mean(),
            "avg_yoy_pct": g["yoy_change_pct"].mean() if g["yoy_change_pct"].notna().any() else float("nan"),
            "point_count": len(g),
        }),
        include_groups=False,
    ).reset_index().sort_values("avg_price", ascending=False)

    st.subheader(f"📍 {city_name} — 町丁目別平均 ({year}年)")

    chart_h = max(300, len(nbhd) * 26)
    col_p, col_y = st.columns(2)

    with col_p:
        sorted_p = nbhd.sort_values("avg_price")
        sorted_p = sorted_p.copy()
        sorted_p["avg_price_man"] = sorted_p["avg_price"].map(yen_to_man)
        fig_p = px.bar(
            sorted_p, x="avg_price_man", y="neighborhood", orientation="h",
            text="avg_price_man", color="avg_price_man",
            color_continuous_scale="Blues_r",
            labels={"avg_price_man": "平均価格(万円/m²)", "neighborhood": "町丁目"},
            title=f"町丁目別平均価格 — {city_name}",
        )
        fig_p.update_traces(texttemplate="%{text:,.1f}", textposition="outside")
        fig_p.update_layout(
            **_base_layout(height=chart_h),
            xaxis=dict(tickformat=",.1f"),
            coloraxis_showscale=False,
            margin=dict(l=130, r=80, t=50, b=40),
        )
        st.plotly_chart(fig_p, use_container_width=True)

    with col_y:
        yoy_n = nbhd.dropna(subset=["avg_yoy_pct"])
        if yoy_n.empty:
            st.info("前年比データなし")
        else:
            sorted_y = yoy_n.sort_values("avg_yoy_pct")
            abs_max = max(sorted_y["avg_yoy_pct"].abs().max(), 1.0)
            fig_y = px.bar(
                sorted_y, x="avg_yoy_pct", y="neighborhood", orientation="h",
                text="avg_yoy_pct", color="avg_yoy_pct",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                range_color=[-abs_max, abs_max],
                labels={"avg_yoy_pct": "前年比(%)", "neighborhood": "町丁目"},
                title=f"町丁目別前年比 — {city_name}",
            )
            fig_y.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
            fig_y.update_layout(
                **_base_layout(height=chart_h),
                xaxis=dict(ticksuffix="%", tickformat=".1f"),
                coloraxis_showscale=False,
                margin=dict(l=130, r=80, t=50, b=40),
            )
            st.plotly_chart(fig_y, use_container_width=True)

    nbhd_disp = nbhd.copy()
    nbhd_disp.insert(0, "順位", range(1, len(nbhd_disp) + 1))
    nbhd_disp = add_tsubo_price_column(nbhd_disp, "avg_price", "avg_price_tsubo")
    nbhd_disp = convert_yen_columns_to_man(nbhd_disp, ["avg_price"])
    render_html_table(nbhd_disp, [
        {"key": "順位",           "label": "順位",        "width": 45,  "align": "right", "render": rank_num},
        {"key": "neighborhood",   "label": "町丁目",      "width": 130, "render": muted},
        {"key": "avg_price",      "label": "平均価格(万/m²)","width": 95,"align": "right", "render": price_man},
        {"key": "avg_price_tsubo","label": "平均坪",      "width": 75,  "align": "right", "render": price_man},
        {"key": "avg_yoy_pct",    "label": "前年比",      "width": 130, "render": gap_bar},
        {"key": "point_count",    "label": "地点数",      "width": 60,  "align": "right", "render": count_num},
    ])


def _render_pref_ranking(df: pd.DataFrame, year) -> None:
    st.subheader("都道府県別ランキング")

    pref_df = analytics.compute_pref_summary(df)
    if pref_df.empty:
        st.info("データなし")
        return

    if year:
        pref_df = pref_df[pref_df["year"] == year].copy()

    if pref_df.empty:
        st.info(f"{year}年のデータなし")
        return

    pref_df = pref_df.sort_values("avg_price", ascending=False).reset_index(drop=True)
    pref_df.index += 1  # 1始まり順位

    # ── 上段: 価格 + 前年比 を横並び ──────────────────────────
    col_price, col_yoy = st.columns(2)

    with col_price:
        st.markdown("**平均価格 (万円/m²)**")
        sorted_p = pref_df.sort_values("avg_price")
        sorted_p = sorted_p.copy()
        sorted_p["avg_price_man"] = sorted_p["avg_price"].map(yen_to_man)
        fig_p = px.bar(
            sorted_p,
            x="avg_price_man",
            y="prefecture_name",
            orientation="h",
            text="avg_price_man",
            color="avg_price_man",
            color_continuous_scale="plasma_r",
            labels={"avg_price_man": "平均価格(万円/m²)", "prefecture_name": "都道府県"},
            title=f"平均価格ランキング ({year}年)",
        )
        fig_p.update_traces(
            texttemplate="%{text:,.1f}",
            textposition="outside",
        )
        fig_p.update_layout(
            **_base_layout(height=max(300, len(pref_df) * 28)),
            xaxis=dict(tickformat=",.1f"),
            coloraxis_showscale=False,
            margin=dict(l=120, r=80, t=50, b=40),
        )
        st.plotly_chart(fig_p, use_container_width=True)

    with col_yoy:
        st.markdown("**前年比 (%)**")
        if "avg_yoy_pct" not in pref_df.columns or pref_df["avg_yoy_pct"].isna().all():
            st.info("前年比データなし（複数年のデータが必要です）")
        else:
            sorted_y = pref_df.dropna(subset=["avg_yoy_pct"]).sort_values("avg_yoy_pct")
            abs_max = max(sorted_y["avg_yoy_pct"].abs().max(), 1.0)
            fig_y = px.bar(
                sorted_y,
                x="avg_yoy_pct",
                y="prefecture_name",
                orientation="h",
                text="avg_yoy_pct",
                color="avg_yoy_pct",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                range_color=[-abs_max, abs_max],
                labels={"avg_yoy_pct": "前年比(%)", "prefecture_name": "都道府県"},
                title=f"前年比ランキング ({year}年)",
            )
            fig_y.update_traces(
                texttemplate="%{text:+.2f}%",
                textposition="outside",
            )
            fig_y.update_layout(
                **_base_layout(height=max(300, len(sorted_y) * 28)),
                xaxis=dict(ticksuffix="%", tickformat=".1f"),
                coloraxis_showscale=False,
                margin=dict(l=120, r=80, t=50, b=40),
            )
            st.plotly_chart(fig_y, use_container_width=True)

    # ── 下段: サマリーテーブル ────────────────────────────────
    st.markdown("**サマリーテーブル**")
    disp = pref_df[["prefecture_name", "avg_price", "median_price",
                    "point_count", "avg_yoy_pct"]].copy()
    disp.insert(0, "順位", range(1, len(disp) + 1))
    disp = add_tsubo_price_column(disp, "avg_price", "avg_price_tsubo")
    disp = add_tsubo_price_column(disp, "median_price", "median_price_tsubo")
    disp = convert_yen_columns_to_man(disp, ["avg_price", "median_price"])
    render_html_table(disp, [
        {"key": "順位",             "label": "順位",         "width": 45,  "align": "right", "render": rank_num},
        {"key": "prefecture_name",  "label": "都道府県",     "width": 80,  "render": muted},
        {"key": "avg_price",        "label": "平均価格(万/m²)","width": 95,"align": "right", "render": price_man},
        {"key": "avg_price_tsubo",  "label": "平均坪",       "width": 75,  "align": "right", "render": price_man},
        {"key": "median_price",     "label": "中央値",       "width": 75,  "align": "right", "render": price_man},
        {"key": "median_price_tsubo","label": "中央値坪",    "width": 65,  "align": "right", "render": price_man},
        {"key": "point_count",      "label": "地点数",       "width": 65,  "align": "right", "render": count_num},
        {"key": "avg_yoy_pct",      "label": "前年比",       "width": 130, "render": gap_bar},
    ])


def _base_layout(height: int = 400) -> dict:
    return dict(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font_color="#c8dff0",
        hovermode="y unified",
    )
