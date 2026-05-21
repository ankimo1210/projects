"""
ui/map_tab.py
Map タブ: Plotly Mapbox で地点を地図表示する。

機能:
- 年スライダー（複数年データがある場合）
- 表示モード: 絶対価格 / 前年比% / ヒートマップ
- スクロールズーム対応
- 都道府県選択時に自動センタリング
- 地点クリックで過去価格推移チャート・テーブルを表示
"""

import db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.constants import PREFECTURE_NAMES as _PREF_NAMES
from ui.table import gap_bar, muted, price_man, render_html_table, year_num
from ui.unit_price import (
    add_tsubo_price_column,
    convert_yen_columns_to_man,
    format_yen_per_sqm_with_tsubo,
    yen_per_sqm_to_tsubo_man,
    yen_to_man,
)

# (center_lat, center_lon, zoom)
_PREF_CENTERS: dict[str, tuple[float, float, int]] = {
    "01": (43.46, 142.94, 7),  # 北海道（広いのでズームを下げる）
    "02": (40.82, 140.74, 9),  # 青森
    "03": (39.70, 141.15, 9),  # 岩手
    "04": (38.27, 140.87, 9),  # 宮城
    "05": (39.72, 140.10, 9),  # 秋田
    "06": (38.24, 140.36, 9),  # 山形
    "07": (37.75, 140.47, 9),  # 福島
    "08": (36.34, 140.45, 9),  # 茨城
    "09": (36.56, 139.88, 9),  # 栃木
    "10": (36.39, 139.06, 9),  # 群馬
    "11": (35.86, 139.65, 10),  # 埼玉
    "12": (35.60, 140.12, 9),  # 千葉
    "13": (35.69, 139.69, 10),  # 東京
    "14": (35.45, 139.64, 10),  # 神奈川
    "15": (37.90, 139.02, 8),  # 新潟
    "16": (36.70, 137.21, 9),  # 富山
    "17": (36.59, 136.63, 9),  # 石川
    "18": (35.90, 136.22, 9),  # 福井
    "19": (35.66, 138.57, 9),  # 山梨
    "20": (36.15, 137.97, 8),  # 長野
    "21": (35.39, 136.72, 9),  # 岐阜
    "22": (34.98, 138.38, 9),  # 静岡
    "23": (35.18, 136.91, 9),  # 愛知
    "24": (34.73, 136.51, 9),  # 三重
    "25": (35.00, 136.22, 9),  # 滋賀
    "26": (35.02, 135.75, 10),  # 京都
    "27": (34.69, 135.50, 10),  # 大阪
    "28": (34.69, 135.18, 9),  # 兵庫
    "29": (34.37, 135.83, 9),  # 奈良
    "30": (33.90, 135.17, 9),  # 和歌山
    "31": (35.50, 133.82, 9),  # 鳥取
    "32": (35.47, 133.05, 9),  # 島根
    "33": (34.66, 133.93, 9),  # 岡山
    "34": (34.40, 132.46, 9),  # 広島
    "35": (34.19, 131.47, 9),  # 山口
    "36": (33.84, 134.23, 9),  # 徳島
    "37": (34.34, 134.05, 9),  # 香川
    "38": (33.84, 132.77, 9),  # 愛媛
    "39": (33.56, 133.53, 9),  # 高知
    "40": (33.59, 130.42, 9),  # 福岡
    "41": (33.27, 130.30, 9),  # 佐賀
    "42": (32.74, 129.87, 9),  # 長崎
    "43": (32.79, 130.74, 9),  # 熊本
    "44": (33.24, 131.61, 9),  # 大分
    "45": (31.91, 131.42, 9),  # 宮崎
    "46": (31.56, 130.56, 9),  # 鹿児島
    "47": (26.21, 127.68, 9),  # 沖縄
}


MAX_POINTS = 8000

# customdata 列インデックス
_CD_POINT_ID = 0
_CD_STD_NUM = 1
_CD_LOCATION = 2
_CD_CITY = 3
_CD_YOY = 4
_CD_USE = 5
_CD_AREA = 6
_CD_YOY_STR = 7  # 前年比の整形済み文字列 (NaN → "—")
_CD_PRICE_SQM_MAN_STR = 8
_CD_PRICE_TSUBO_STR = 9


def render_map_tab(df: pd.DataFrame | None, filters: dict, conn=None) -> None:
    st.header("🗺 地価公示 地点マップ")

    # ── コントロール行 ────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 2])

    with ctrl1:
        selected_year = filters.get("year")
        if conn is not None:
            available_years = db.get_available_years(conn)
            if len(available_years) > 1:
                selected_year = st.select_slider(
                    "表示年度",
                    options=sorted(available_years),
                    value=max(available_years),
                    key="map_year_slider",
                )
                if selected_year != filters.get("year"):
                    year_filters = {k: v for k, v in filters.items() if v is not None}
                    year_filters["year"] = selected_year
                    df = db.read_land_prices(conn, filters=year_filters)

    with ctrl2:
        display_mode = st.selectbox(
            "表示モード",
            ["絶対価格 (万円/m²)", "前年比 (%)", "ヒートマップ"],
            index=0,
            key="map_display_mode",
        )

    with ctrl3:
        # データに存在する都道府県コードに絞り、北→南（コード昇順）でズーム先を列挙
        _zoom_codes: list[str] = []
        if df is not None and "prefecture_code" in df.columns:
            _zoom_codes = sorted(
                df["prefecture_code"].dropna().unique().tolist()
            )  # 01=北海道…47=沖縄 でコード=緯度順
        _zoom_options = ["全国"] + [
            _PREF_NAMES.get(c, c) for c in _zoom_codes if c in _PREF_CENTERS
        ]
        _code_by_name = {_PREF_NAMES.get(c, c): c for c in _zoom_codes if c in _PREF_CENTERS}
        zoom_target = st.selectbox(
            "ズーム先",
            _zoom_options,
            index=0,
            key="map_zoom_target",
        )

    if df is None or df.empty:
        st.info(
            "データがありません。左サイドバーで年度を選択するか、管理タブからデータを同期してください。"
        )
        return

    plot_df = df.dropna(subset=["lon", "lat"]).copy()
    if display_mode != "ヒートマップ":
        plot_df = plot_df.dropna(subset=["price_yen_per_sqm"])

    if plot_df.empty:
        st.warning("座標・価格データのある地点がありません。")
        return

    if len(plot_df) > MAX_POINTS:
        plot_df = plot_df.sample(MAX_POINTS, random_state=42)

    # ── メトリクス ────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    if "price_yen_per_sqm" in plot_df.columns and plot_df["price_yen_per_sqm"].notna().any():
        col1.metric("平均価格", format_yen_per_sqm_with_tsubo(plot_df["price_yen_per_sqm"].mean()))
        col2.metric("最高価格", format_yen_per_sqm_with_tsubo(plot_df["price_yen_per_sqm"].max()))
    if "yoy_change_pct" in plot_df.columns and plot_df["yoy_change_pct"].notna().any():
        col3.metric("平均前年比", f"{plot_df['yoy_change_pct'].mean():+.1f}%")

    # ── マップ中心・ズーム ────────────────────────────────────
    zoom_pref_code = _code_by_name.get(zoom_target) if zoom_target != "全国" else None
    if zoom_pref_code and zoom_pref_code in _PREF_CENTERS:
        center_lat, center_lon, zoom = _PREF_CENTERS[zoom_pref_code]
    elif not plot_df.empty:
        center_lat = float(plot_df["lat"].mean())
        center_lon = float(plot_df["lon"].mean())
        zoom = 5
    else:
        center_lat, center_lon, zoom = 36.5, 137.0, 5

    # ── customdata の準備 ─────────────────────────────────────
    custom_cols = [
        "point_id",
        "standard_land_number",
        "location_text",
        "city_name",
        "yoy_change_pct",
        "use_category_name",
        "area_sqm",
        "_yoy_str",
        "_price_sqm_man_str",
        "_price_tsubo_str",
    ]
    for c in [
        "point_id",
        "standard_land_number",
        "location_text",
        "city_name",
        "yoy_change_pct",
        "use_category_name",
        "area_sqm",
    ]:
        if c not in plot_df.columns:
            plot_df[c] = None
    plot_df["_yoy_str"] = plot_df["yoy_change_pct"].apply(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
    )
    plot_df["_price_sqm_man_str"] = plot_df["price_yen_per_sqm"].map(
        lambda x: f"{yen_to_man(x):,.1f}万円/m²" if pd.notna(x) else "—"
    )
    plot_df["_price_tsubo_str"] = plot_df["price_yen_per_sqm"].map(
        lambda x: f"{yen_per_sqm_to_tsubo_man(x):,.1f}万円/坪" if pd.notna(x) else "—"
    )
    plot_df["price_man_per_sqm"] = plot_df["price_yen_per_sqm"].map(yen_to_man)

    # ── チャート生成 ──────────────────────────────────────────
    if display_mode == "絶対価格 (万円/m²)":
        # 用途区分別に percentile 正規化した相対スコアで色付け（混在表示でも識別可能）
        plot_df = plot_df.copy()
        plot_df["_price_score"] = _compute_category_score(
            plot_df, "price_man_per_sqm", "use_category_name"
        )
        fig = px.scatter_mapbox(
            plot_df,
            lat="lat",
            lon="lon",
            color="_price_score",
            custom_data=custom_cols,
            color_continuous_scale="plasma",
            range_color=[0.0, 1.0],
            mapbox_style="open-street-map",
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            height=680,
        )
        fig.update_coloraxes(
            colorbar_title="用途内<br>価格位置",
            colorbar_tickvals=[0, 0.5, 1],
            colorbar_ticktext=["低", "中", "高"],
        )
        _apply_hover(
            fig,
            color_label="価格",
            color_format="{:,.1f}万円/m²",
            color_col="price_man_per_sqm",
            df=plot_df,
        )

    elif display_mode == "前年比 (%)":
        yoy_df = plot_df.dropna(subset=["yoy_change_pct"]).copy()
        if yoy_df.empty:
            st.warning("前年比データがありません。")
            return
        abs_max = yoy_df["yoy_change_pct"].abs().quantile(0.95)
        abs_max = max(abs_max, 1.0)
        yoy_df["yoy_clamped"] = yoy_df["yoy_change_pct"].clip(-abs_max, abs_max)
        fig = px.scatter_mapbox(
            yoy_df,
            lat="lat",
            lon="lon",
            color="yoy_clamped",
            custom_data=custom_cols,
            color_continuous_scale="RdBu_r",
            color_continuous_midpoint=0,
            range_color=[-abs_max, abs_max],
            mapbox_style="open-street-map",
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            height=680,
        )
        fig.update_coloraxes(colorbar_title="前年比(%)<br>赤=上昇/青=下落")
        _apply_hover(
            fig, color_label="前年比", color_format="{:+.1f}%", color_col="yoy_clamped", df=yoy_df
        )
        plot_df = yoy_df

    else:  # ヒートマップ
        fig = px.density_mapbox(
            plot_df,
            lat="lat",
            lon="lon",
            z="price_man_per_sqm",
            radius=15,
            color_continuous_scale="Hot",
            mapbox_style="open-street-map",
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            height=680,
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
        return

    fig.update_traces(
        marker=dict(size=9, opacity=0.85),
        unselected=dict(marker=dict(opacity=0.45)),
        selected=dict(marker=dict(size=13, opacity=1.0)),
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    # ── 描画 + クリック選択 ───────────────────────────────────
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        config={"scrollZoom": True},
        on_select="rerun",
        selection_mode="points",
        key="map_chart",
    )

    # ── 選択地点の詳細 ────────────────────────────────────────
    _render_selected_point(event, conn)


# --------------------------------------------------------------------------
# ホバーテンプレート適用
# --------------------------------------------------------------------------

_HOVER_BASE = (
    "<b>%{customdata[1]}</b><br>"
    "──────────────────────<br>"
    "📍 %{customdata[2]}<br>"
    "🏙 %{customdata[3]}<br>"
    "🏷 %{customdata[5]}<br>"
    "📐 面積: %{customdata[6]:,.0f} m²<br>"
    "──────────────────────<br>"
)


def _compute_category_score(df: pd.DataFrame, price_col: str, category_col: str) -> pd.Series:
    """用途区分ごとに price_col を [0, 1] に正規化したスコアを返す。
    同じ色スケールで住宅地と商業地を区別なく公平に比較できる。"""
    scores = df[price_col].copy().astype(float)
    for _cat, group in df.groupby(category_col, dropna=False):
        vals = group[price_col].dropna()
        if vals.empty:
            continue
        p5 = vals.quantile(0.05)
        p95 = vals.quantile(0.95)
        span = p95 - p5
        if span <= 0:
            scores.loc[group.index] = 0.5
        else:
            scores.loc[group.index] = ((group[price_col] - p5) / span).clip(0.0, 1.0)
    return scores


def _apply_hover(
    fig, color_label: str, color_format: str, color_col: str, df: pd.DataFrame
) -> None:
    """読みやすいホバーテンプレートを設定する。"""
    if color_label == "価格":
        tmpl = (
            _HOVER_BASE
            + "💰 価格: %{customdata[8]}<br>"
            + "💰 坪単価: %{customdata[9]}<br>"
            + "📈 前年比: %{customdata[7]}<br>"
            + "<extra></extra>"
        )
    else:
        tmpl = _HOVER_BASE + "📈 前年比: %{marker.color:+.1f}%<br>" + "<extra></extra>"
    fig.update_traces(hovertemplate=tmpl)


# --------------------------------------------------------------------------
# 選択地点の詳細表示
# --------------------------------------------------------------------------


def _render_selected_point(event, conn) -> None:
    """クリックされた地点の過去推移チャートとテーブルを表示する。"""
    if not event or not event.selection or not event.selection.points:
        st.caption("💡 地点をクリックすると価格推移が表示されます")
        return

    pt = event.selection.points[0]
    cd = pt.get("customdata", [])
    if not cd:
        return

    point_id = str(cd[_CD_POINT_ID]) if len(cd) > _CD_POINT_ID and cd[_CD_POINT_ID] else None
    location = cd[_CD_LOCATION] if len(cd) > _CD_LOCATION else "—"
    std_num = cd[_CD_STD_NUM] if len(cd) > _CD_STD_NUM else "—"
    city = cd[_CD_CITY] if len(cd) > _CD_CITY else "—"

    st.markdown("---")
    st.subheader(f"📍 {std_num}　{location}")
    st.caption(f"市区町村: {city}")

    if point_id is None or conn is None:
        st.info("履歴データを取得できません。")
        return

    history = db.get_point_history(conn, point_id)

    if history.empty or len(history) < 1:
        st.info("この地点の履歴データが1年分しかありません。")
        return

    history = history.sort_values("year")

    # 市区町村データを先に取得して x 軸範囲を統一する
    city = cd[_CD_CITY] if len(cd) > _CD_CITY else None
    city_history = pd.DataFrame()
    if city and city not in ("—", None) and conn is not None:
        city_history = db.get_city_history(conn, city)
        if not city_history.empty:
            city_history = city_history.sort_values("year")

    # 両データの年範囲の和集合で x 軸を統一
    all_years = list(history["year"])
    if not city_history.empty:
        all_years += list(city_history["year"])
    x_range = [min(all_years) - 0.5, max(all_years) + 0.5]

    # ── 推移チャート ──────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history["year"],
            y=history["price_yen_per_sqm"].map(yen_to_man),
            customdata=history["price_yen_per_sqm"].map(yen_per_sqm_to_tsubo_man),
            mode="lines+markers",
            name="価格 (万円/m²)",
            line=dict(color="#4fc3f7", width=2.5),
            marker=dict(size=8),
            hovertemplate="<b>%{x}年</b><br>%{y:,.1f}万円/m²<br>%{customdata:,.1f}万円/坪<extra></extra>",
        )
    )

    if "yoy_change_pct" in history.columns and history["yoy_change_pct"].notna().any():
        colors = [
            "#ef5350" if (v is not None and v > 0) else "#42a5f5"
            for v in history["yoy_change_pct"].fillna(0)
        ]
        fig.add_trace(
            go.Bar(
                x=history["year"],
                y=history["yoy_change_pct"],
                name="前年比 (%)",
                yaxis="y2",
                marker_color=colors,
                opacity=0.5,
                hovertemplate="<b>%{x}年</b><br>前年比: %{y:+.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        height=360,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font_color="#c8dff0",
        xaxis=dict(title="年度", dtick=1, range=x_range),
        yaxis=dict(title="価格 (万円/m²)", tickformat=",.1f"),
        yaxis2=dict(
            title="前年比 (%)",
            overlaying="y",
            side="right",
            ticksuffix="%",
            tickformat=".1f",
            showgrid=False,
        ),
        legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        margin=dict(t=30, b=60, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 市区町村平均チャート ──────────────────────────────────
    if not city_history.empty:
        st.subheader(f"🏙 {city} 平均価格推移")

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=city_history["year"],
                y=city_history["avg_price"].map(yen_to_man),
                customdata=city_history["avg_price"].map(yen_per_sqm_to_tsubo_man),
                mode="lines+markers",
                name="市区町村平均 (万円/m²)",
                line=dict(color="#81c784", width=2.5),
                marker=dict(size=8),
                hovertemplate="<b>%{x}年</b><br>%{y:,.1f}万円/m²<br>%{customdata:,.1f}万円/坪<extra></extra>",
            )
        )

        if "avg_yoy_pct" in city_history.columns and city_history["avg_yoy_pct"].notna().any():
            colors2 = [
                "#ef5350" if (v is not None and v > 0) else "#42a5f5"
                for v in city_history["avg_yoy_pct"].fillna(0)
            ]
            fig2.add_trace(
                go.Bar(
                    x=city_history["year"],
                    y=city_history["avg_yoy_pct"],
                    name="前年比 (%)",
                    yaxis="y2",
                    marker_color=colors2,
                    opacity=0.5,
                    hovertemplate="<b>%{x}年</b><br>前年比: %{y:+.1f}%<extra></extra>",
                )
            )

        fig2.update_layout(
            height=360,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,27,42,0.6)",
            font_color="#c8dff0",
            xaxis=dict(title="年度", dtick=1, range=x_range),
            yaxis=dict(title="平均価格 (万円/m²)", tickformat=",.1f"),
            yaxis2=dict(
                title="前年比 (%)",
                overlaying="y",
                side="right",
                ticksuffix="%",
                tickformat=".1f",
                showgrid=False,
            ),
            legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
            margin=dict(t=30, b=60, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── 詳細テーブル ──────────────────────────────────────────
    with st.expander("📋 年次データ一覧", expanded=False):
        show_cols = [
            c
            for c in [
                "year",
                "price_yen_per_sqm",
                "last_year_price_yen_per_sqm",
                "yoy_change_pct",
                "use_category_name",
                "zoning_name",
            ]
            if c in history.columns
        ]
        display_history = add_tsubo_price_column(
            history[show_cols], "price_yen_per_sqm", "price_yen_per_tsubo"
        )
        display_history = add_tsubo_price_column(
            display_history, "last_year_price_yen_per_sqm", "last_year_price_yen_per_tsubo"
        )
        display_history = convert_yen_columns_to_man(
            display_history, ["price_yen_per_sqm", "last_year_price_yen_per_sqm"]
        )
        render_html_table(
            display_history.sort_values("year", ascending=False),
            [
                {"key": "year", "label": "年度", "width": 50, "align": "right", "render": year_num},
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
                {"key": "use_category_name", "label": "用途", "width": 70, "render": muted},
                {"key": "zoning_name", "label": "用途区域", "width": 90, "render": muted},
            ],
        )
