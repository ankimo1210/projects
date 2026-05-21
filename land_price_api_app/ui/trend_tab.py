"""
ui/trend_tab.py
都市トレンドタブ: 主要都市の地価推移を多年・多都市で比較する。

データソース: city_summary VIEW（集計済み）を使用しパフォーマンスを確保。
キャッシュ: @st.cache_data(ttl=3600) でクエリ結果を1時間保持。
"""
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics
import db
from ui.unit_price import add_tsubo_price_column, convert_yen_columns_to_man, format_yen_per_sqm_with_tsubo, yen_to_man
from ui.table import render_html_table, gap_bar_small, price_man, muted, year_num, count_num

# --------------------------------------------------------------------------
# 定数
# --------------------------------------------------------------------------

MAJOR_PREFS: dict[str, str] = {
    "47": "沖縄",
    "13": "東京",
    "14": "神奈川",
    "27": "大阪",
    "01": "北海道",
    "23": "愛知",
    "40": "福岡",
}

_DISPLAY_MODES = ["絶対価格 (万円/m²)", "指数化 (基準年=100)", "前年比 (%)"]

_USE_CATEGORIES = ["住宅地", "商業地", "工業地", "林地"]

# --------------------------------------------------------------------------
# キャッシュ付きデータロード
# --------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def _load_trend_data(
    _conn,
    pref_codes: tuple[str, ...],
    year_start: int,
    year_end: int,
    use_category: Optional[str],
) -> pd.DataFrame:
    return db.get_multiyear_city_summary(
        _conn, list(pref_codes), (year_start, year_end), use_category
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _get_available_years(_conn) -> list[int]:
    return db.get_available_years(_conn)


@st.cache_data(ttl=3600, show_spinner=False)
def _get_cities_for_prefs(_conn, pref_codes: tuple[str, ...]) -> list[tuple[str, str, str]]:
    """(city_code, city_name, pref_name) のリストを返す。"""
    if not pref_codes:
        return []
    placeholders = ", ".join(["?"] * len(pref_codes))
    rows = _conn.execute(
        f"SELECT DISTINCT city_code, city_name, prefecture_name "
        f"FROM city_summary WHERE prefecture_code IN ({placeholders}) "
        f"ORDER BY prefecture_code, city_code",
        list(pref_codes),
    ).fetchall()
    return rows


# --------------------------------------------------------------------------
# メイン描画
# --------------------------------------------------------------------------


def render_trend_tab(conn, filters: dict) -> None:  # noqa: C901
    st.header("🏙 都市トレンド")

    available_years = _get_available_years(conn)
    if not available_years:
        st.info("データがありません。管理タブからデータを同期してください。")
        return

    year_min = min(available_years)
    year_max = max(available_years)

    # ── コントロール行 ──────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 3, 2])

    with c1:
        # DB に存在する都道府県コードのみ、北→南（コード昇順）で列挙
        existing_prefs = _get_existing_prefs(conn)
        pref_options = dict(sorted(
            {k: v for k, v in MAJOR_PREFS.items() if k in existing_prefs}.items()
        ))
        if not pref_options:
            pref_options = dict(sorted(MAJOR_PREFS.items()))  # フォールバック

        selected_pref_codes = st.multiselect(
            "都道府県",
            options=list(pref_options.keys()),
            default=[list(pref_options.keys())[0]],
            format_func=lambda code: pref_options.get(code, code),
            key="trend_prefs",
        )

    with c2:
        # 選択都道府県の市区町村
        city_rows = _get_cities_for_prefs(conn, tuple(selected_pref_codes)) if selected_pref_codes else []
        city_options_all = ["（都道府県集計）"] + [
            f"{pref} / {name}"
            for code, name, pref in city_rows
        ]
        selected_cities_raw = st.multiselect(
            "市区町村（空=都道府県集計）",
            options=city_options_all,
            default=["（都道府県集計）"],
            key="trend_cities",
        )

    with c3:
        use_cat_options = ["すべて"] + _USE_CATEGORIES
        selected_use = st.selectbox("用途区分", use_cat_options, index=1, key="trend_use")
        use_cat_arg = None if selected_use == "すべて" else selected_use
        min_point_count = st.number_input(
            "最小地点数", min_value=1, max_value=50, value=3, step=1, key="trend_min_points",
            help="この件数未満の都市・年度を除外します",
        )

    # 年範囲 + 表示モード
    c4, c5, c6 = st.columns([3, 2, 2])

    with c4:
        if year_min == year_max:
            year_start = year_end = year_min
            st.caption(f"利用可能年度: {year_min}年（1年分のみ）")
        else:
            year_start, year_end = st.select_slider(
                "年範囲",
                options=list(range(year_min, year_max + 1)),
                value=(year_min, year_max),
                key="trend_year_range",
            )

    with c5:
        display_mode = st.selectbox("表示モード", _DISPLAY_MODES, index=0, key="trend_mode")

    with c6:
        if display_mode == "指数化 (基準年=100)":
            base_year = st.selectbox(
                "基準年",
                options=list(range(year_start, year_end + 1)),
                index=0,
                key="trend_base_year",
            )
        else:
            base_year = year_start

    if not selected_pref_codes:
        st.info("都道府県を1つ以上選択してください。")
        return

    # ── データ取得 ──────────────────────────────────────────────
    with st.spinner("データを読み込み中..."):
        raw_df = _load_trend_data(
            conn, tuple(selected_pref_codes), year_start, year_end, use_cat_arg
        )

    if raw_df.empty:
        st.warning("選択条件に合うデータがありません。管理タブからデータを同期してください。")
        return

    # 市区町村フィルタ適用
    use_pref_level = "（都道府県集計）" in selected_cities_raw or not selected_cities_raw
    selected_city_codes = _parse_city_codes(selected_cities_raw, city_rows)

    if use_pref_level:
        plot_df = analytics.compute_pref_multiyear_summary(raw_df)
        color_col = "prefecture_name"
        label_col = "prefecture_name"
    else:
        plot_df = raw_df[raw_df["city_code"].isin(selected_city_codes)].copy()
        color_col = "city_name"
        label_col = "city_name"

    # 最小地点数フィルタ
    if "point_count" in plot_df.columns and min_point_count > 1:
        plot_df = plot_df[plot_df["point_count"] >= min_point_count].copy()

    # 用途区分別に複数行ある場合のみ use_category_name を追加
    if use_cat_arg is None and "use_category_name" in plot_df.columns:
        unique_cats = plot_df["use_category_name"].dropna().unique()
        if len(unique_cats) > 1:
            plot_df = plot_df.copy()
            plot_df[label_col] = plot_df[label_col] + " / " + plot_df["use_category_name"].fillna("")

    if plot_df.empty:
        st.warning("選択した市区町村のデータがありません。")
        return

    # ── KPIカード ──────────────────────────────────────────────
    _render_kpi_cards(plot_df, year_start, year_end)

    st.markdown("---")

    # ── メインチャート ──────────────────────────────────────────
    if display_mode == "絶対価格 (万円/m²)":
        fig = _chart_absolute(plot_df, color_col, label_col, year_start, year_end)
    elif display_mode == "指数化 (基準年=100)":
        indexed = analytics.compute_indexed_prices(plot_df, base_year)
        fig = _chart_indexed(indexed, color_col, label_col, base_year, year_start, year_end)
    else:
        fig = _chart_yoy(plot_df, color_col, label_col, year_start, year_end)

    st.plotly_chart(fig, use_container_width=True)

    # ── データテーブル ──────────────────────────────────────────
    with st.expander("📋 データテーブル", expanded=False):
        display_cols = [c for c in [
            "year", "prefecture_name", "city_name", "use_category_name",
            "avg_price", "median_price", "avg_yoy_pct", "point_count",
        ] if c in plot_df.columns]
        display_df = plot_df[display_cols].copy()
        display_df = add_tsubo_price_column(display_df, "avg_price", "avg_price_tsubo")
        display_df = add_tsubo_price_column(display_df, "median_price", "median_price_tsubo")
        display_df = convert_yen_columns_to_man(display_df, ["avg_price", "median_price"])
        render_html_table(display_df, [
            {"key": "year",             "label": "年度",        "width": 50,  "align": "right", "render": year_num},
            {"key": "prefecture_name",  "label": "都道府県",    "width": 70,  "render": muted},
            {"key": "city_name",        "label": "市区町村",    "width": 100, "render": muted},
            {"key": "use_category_name","label": "用途",        "width": 70,  "render": muted},
            {"key": "avg_price",        "label": "平均(万/m²)", "width": 80,  "align": "right", "render": price_man},
            {"key": "avg_price_tsubo",  "label": "平均坪",      "width": 70,  "align": "right", "render": price_man},
            {"key": "median_price",     "label": "中央値",      "width": 70,  "align": "right", "render": price_man},
            {"key": "median_price_tsubo","label": "中央値坪",   "width": 65,  "align": "right", "render": price_man},
            {"key": "avg_yoy_pct",      "label": "前年比",      "width": 130, "render": gap_bar_small},
            {"key": "point_count",      "label": "地点数",      "width": 60,  "align": "right", "render": count_num},
        ])
        st.download_button(
            "CSVダウンロード",
            data=plot_df[display_cols].to_csv(index=False, encoding="utf-8-sig"),
            file_name="city_trend.csv",
            mime="text/csv",
        )


# --------------------------------------------------------------------------
# チャート生成
# --------------------------------------------------------------------------


def _chart_absolute(df: pd.DataFrame, color_col: str, label_col: str, yr_start: int, yr_end: int) -> go.Figure:
    plot_df = df.copy()
    plot_df["avg_price_man"] = plot_df["avg_price"].map(yen_to_man)
    fig = px.line(
        plot_df,
        x="year",
        y="avg_price_man",
        color=label_col if label_col in df.columns else color_col,
        markers=True,
        labels={"avg_price_man": "平均価格 (万円/m²)", "year": "年度"},
        hover_data={c: True for c in ["point_count", "avg_yoy_pct"] if c in df.columns},
        title="地価推移（平均価格）",
    )
    fig.update_layout(**_base_layout(height=460))
    fig.update_yaxes(tickformat=",.1f")
    return fig


def _chart_indexed(df: pd.DataFrame, color_col: str, label_col: str, base_year: int, yr_start: int, yr_end: int) -> go.Figure:
    valid = df.dropna(subset=["index_100"])
    if valid.empty:
        return _empty_fig(f"基準年 {base_year} のデータがないため指数化できません。")

    col = label_col if label_col in df.columns else color_col
    fig = px.line(
        valid,
        x="year",
        y="index_100",
        color=col,
        markers=True,
        labels={"index_100": f"価格指数 ({base_year}=100)", "year": "年度"},
        title=f"価格指数（{base_year}年=100）",
    )
    fig.add_hline(y=100, line_dash="dash", line_color="#607d8b", annotation_text=f"{base_year}年基準")
    fig.update_layout(**_base_layout(height=460))
    return fig


def _chart_yoy(df: pd.DataFrame, color_col: str, label_col: str, yr_start: int, yr_end: int) -> go.Figure:
    if "avg_yoy_pct" not in df.columns:
        return _empty_fig("前年比データがありません。")

    col = label_col if label_col in df.columns else color_col
    fig = px.bar(
        df.dropna(subset=["avg_yoy_pct"]),
        x="year",
        y="avg_yoy_pct",
        color="avg_yoy_pct",
        facet_col=col if df[col].nunique() > 1 else None,
        facet_col_wrap=3,
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        range_color=[-15, 15],
        labels={"avg_yoy_pct": "前年比 (%)", "year": "年度"},
        title="前年比変動率 (%)",
    )
    fig.update_layout(**_base_layout(height=480))
    fig.update_coloraxes(showscale=False)
    fig.update_yaxes(ticksuffix="%", tickformat=".1f")
    return fig


def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=14)
    fig.update_layout(**_base_layout(height=200))
    return fig


def _base_layout(height: int = 460) -> dict:
    return dict(
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font_color="#c8dff0",
        legend=dict(orientation="h", y=-0.22, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=80, l=10, r=10),
    )


# --------------------------------------------------------------------------
# ヘルパー
# --------------------------------------------------------------------------


def _render_kpi_cards(df: pd.DataFrame, yr_start: int, yr_end: int) -> None:
    latest_rows = df[df["year"] == df["year"].max()]
    earliest_rows = df[df["year"] == df["year"].min()]

    latest_avg = latest_rows["avg_price"].mean() if not latest_rows.empty else None
    earliest_avg = earliest_rows["avg_price"].mean() if not earliest_rows.empty else None

    period_change = None
    if latest_avg and earliest_avg and earliest_avg > 0:
        period_change = (latest_avg - earliest_avg) / earliest_avg * 100

    peak_year = df.loc[df["avg_price"].idxmax(), "year"] if not df.empty else None
    trough_year = df.loc[df["avg_price"].idxmin(), "year"] if not df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "最新平均価格",
            format_yen_per_sqm_with_tsubo(latest_avg) if latest_avg else "—",
        )
    with c2:
        st.metric(
            f"期間変化率 ({yr_start}→{df['year'].max()})",
            f"{period_change:+.1f}%" if period_change is not None else "—",
            delta=f"{period_change:+.1f}%" if period_change is not None else None,
        )
    with c3:
        st.metric("最高値年度", str(peak_year) if peak_year else "—")
    with c4:
        st.metric("最低値年度", str(trough_year) if trough_year else "—")


@st.cache_data(ttl=3600, show_spinner=False)
def _get_existing_prefs(_conn) -> set[str]:
    rows = _conn.execute(
        "SELECT DISTINCT prefecture_code FROM land_prices_public_notice"
    ).fetchall()
    return {r[0] for r in rows}


def _parse_city_codes(selected: list[str], city_rows: list[tuple]) -> list[str]:
    """選択された "都道府県名 / 市区町村名" から city_code を逆引きする。"""
    name_to_code = {f"{pref} / {name}": code for code, name, pref in city_rows}
    return [name_to_code[item] for item in selected if item in name_to_code]
