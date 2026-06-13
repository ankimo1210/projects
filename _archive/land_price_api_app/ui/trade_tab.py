"""
ui/trade_tab.py
不動産取引価格情報タブ (XIT001)。
地図表示・フィルタ・公示価格との乖離率を表示する。
"""

import db
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.constants import PREFECTURE_NAMES as _PREF_NAMES
from ui.table import (
    area_num,
    count_num,
    muted,
    price_man,
    render_html_table,
    truncate_muted,
    year_num,
)
from ui.unit_price import (
    add_tsubo_price_column,
    convert_yen_columns_to_man,
    format_yen_per_sqm_with_tsubo,
    yen_to_man,
)

# --------------------------------------------------------------------------
# 定数
# --------------------------------------------------------------------------

_TRADE_TYPES = ["土地", "土地と建物", "建物", "マンション等"]


# --------------------------------------------------------------------------
# キャッシュ付きデータロード
# --------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def _load_trade_data(
    _conn,
    year: int,
    quarter: int | None,
    pref_code: str | None,
    trade_type: str | None,
) -> pd.DataFrame:
    filters: dict = {"year": year}
    if quarter:
        filters["quarter"] = quarter
    if pref_code:
        filters["prefecture_code"] = pref_code
    if trade_type:
        filters["trade_type"] = trade_type
    return db.read_trade_prices(_conn, filters=filters, limit=20000)


@st.cache_data(ttl=3600, show_spinner=False)
def _get_trade_years(_conn) -> list[int]:
    return db.get_trade_available_years(_conn)


@st.cache_data(ttl=3600, show_spinner=False)
def _get_trade_prefs(_conn) -> list[str]:
    rows = _conn.execute(
        "SELECT DISTINCT prefecture_code FROM trade_prices ORDER BY prefecture_code"
    ).fetchall()
    return [r[0] for r in rows if r[0]]


# --------------------------------------------------------------------------
# メイン描画
# --------------------------------------------------------------------------


def render_trade_tab(conn, filters: dict) -> None:
    st.header("🏠 不動産取引価格")

    available_years = _get_trade_years(conn)
    if not available_years:
        _render_no_data_guide()
        return

    # ── コントロール ───────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

    with c1:
        selected_year = st.selectbox("年", available_years, index=0, key="trade_year")

    with c2:
        quarter_opts = ["全四半期", "Q1 (1-3月)", "Q2 (4-6月)", "Q3 (7-9月)", "Q4 (10-12月)"]
        quarter_sel = st.selectbox("四半期", quarter_opts, index=0, key="trade_quarter")
        quarter_arg = None if quarter_sel == "全四半期" else int(quarter_sel[1])

    with c3:
        existing_prefs = _get_trade_prefs(conn)
        pref_opts = {"": "全国"}
        pref_opts.update({code: _PREF_NAMES.get(code, code) for code in sorted(existing_prefs)})
        pref_sel = st.selectbox(
            "都道府県",
            options=list(pref_opts.keys()),
            format_func=lambda c: pref_opts[c],
            key="trade_pref",
        )
        pref_arg = pref_sel if pref_sel else None

    with c4:
        type_opts = ["すべて", *_TRADE_TYPES]
        type_sel = st.selectbox("取引種別", type_opts, index=0, key="trade_type")
        type_arg = None if type_sel == "すべて" else type_sel

    # ── データ取得 ─────────────────────────────────────────────────
    with st.spinner("データを読み込み中..."):
        df = _load_trade_data(conn, selected_year, quarter_arg, pref_arg, type_arg)

    if df.empty:
        st.warning("選択条件に合うデータがありません。管理タブからデータを同期してください。")
        return

    # ── KPI カード ─────────────────────────────────────────────────
    _render_kpi_cards(df)
    st.markdown("---")

    # ── タブ ───────────────────────────────────────────────────────
    tab_trend, tab_deviation, tab_dist, tab_table = st.tabs(
        ["📈 価格推移", "📊 公示価格との乖離", "📊 価格分布", "📋 データ"]
    )

    with tab_trend:
        _render_trend(conn, pref_arg, type_arg)

    with tab_deviation:
        _render_deviation(conn, selected_year, pref_arg)

    with tab_dist:
        _render_distribution(df)

    with tab_table:
        _render_table(df)


# --------------------------------------------------------------------------
# KPI カード
# --------------------------------------------------------------------------


def _render_kpi_cards(df: pd.DataFrame) -> None:
    trade_count = len(df)
    avg_per_sqm = df["trade_price_per_sqm"].mean() if "trade_price_per_sqm" in df.columns else None
    median_total = df["trade_price_total"].median() if "trade_price_total" in df.columns else None
    avg_area = df["area_sqm"].mean() if "area_sqm" in df.columns else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("取引件数", f"{trade_count:,}件")
    with c2:
        st.metric(
            "平均単価 (万円/m²)",
            format_yen_per_sqm_with_tsubo(avg_per_sqm)
            if avg_per_sqm and not pd.isna(avg_per_sqm)
            else "—",
        )
    with c3:
        st.metric(
            "取引価格中央値",
            f"¥{median_total:,.0f}" if median_total and not pd.isna(median_total) else "—",
        )
    with c4:
        st.metric(
            "平均面積",
            f"{avg_area:.0f}m²" if avg_area and not pd.isna(avg_area) else "—",
        )


# --------------------------------------------------------------------------
# 価格推移（四半期別）
# --------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def _load_trade_trend(_conn, pref_code: str | None, trade_type: str | None) -> pd.DataFrame:
    return db.get_trade_city_summary(_conn, pref_codes=[pref_code] if pref_code else None)


def _render_trend(conn, pref_code: str | None, trade_type: str | None) -> None:
    df = _load_trade_trend(conn, pref_code, trade_type)
    if df.empty:
        st.info("トレンドデータがありません。")
        return

    if trade_type:
        df = df[df["trade_type"] == trade_type]

    # 年+四半期を時系列軸に変換
    df["period"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    summary = (
        df.groupby("period", as_index=False)
        .agg(avg_price=("avg_price_per_sqm", "mean"), trade_count=("trade_count", "sum"))
        .sort_values("period")
    )
    summary["avg_price"] = summary["avg_price"].map(yen_to_man)

    fig = px.line(
        summary,
        x="period",
        y="avg_price",
        markers=True,
        labels={"avg_price": "平均単価 (万円/m²)", "period": "期"},
        title="四半期別 平均取引単価推移",
    )
    fig.update_layout(**_base_layout())
    fig.update_yaxes(tickformat=",.1f")
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------
# 公示価格との乖離
# --------------------------------------------------------------------------


def _render_deviation(conn, year: int, pref_code: str | None) -> None:
    st.caption("同年・同市区町村の地価公示平均価格との比率。取引価格 ÷ 公示価格 × 100。")

    trade_df = db.get_trade_city_summary(
        conn, year=year, pref_codes=[pref_code] if pref_code else None
    )
    notice_df = db.get_city_summary(conn, year=year)

    if trade_df.empty or notice_df.empty:
        st.info("比較データが不足しています。両データを同期してください。")
        return

    # city_code で結合
    merged = pd.merge(
        trade_df[["city_code", "city_name", "trade_type", "avg_price_per_sqm", "trade_count"]],
        notice_df[["city_code", "avg_price"]].rename(columns={"avg_price": "notice_avg_price"}),
        on="city_code",
        how="inner",
    )

    if merged.empty:
        st.info("共通する市区町村が見つかりませんでした。")
        return

    merged["deviation_pct"] = (merged["avg_price_per_sqm"] / merged["notice_avg_price"] - 1) * 100
    merged = merged.sort_values("deviation_pct", ascending=False).head(30)

    fig = px.bar(
        merged,
        x="deviation_pct",
        y="city_name",
        color="deviation_pct",
        color_continuous_scale="RdBu_r",
        color_continuous_midpoint=0,
        orientation="h",
        labels={"deviation_pct": "乖離率 (%)", "city_name": "市区町村"},
        title=f"取引価格 vs 公示価格 乖離率 ({year}年)",
        hover_data={"avg_price_per_sqm": True, "notice_avg_price": True, "trade_count": True},
    )
    fig.update_layout(**_base_layout(height=max(400, len(merged) * 22)))
    fig.update_xaxes(ticksuffix="%", tickformat=".1f")
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------
# データテーブル
# --------------------------------------------------------------------------


def _render_distribution(df: pd.DataFrame) -> None:
    """取引単価の分布（ヒストグラム）と取引種別の内訳を表示する。"""
    col_l, col_r = st.columns(2)

    with col_l:
        plot = df.dropna(subset=["trade_price_per_sqm"])
        if plot.empty:
            st.info("単価データなし")
        else:
            plot = plot.copy()
            plot["trade_price_man_per_sqm"] = plot["trade_price_per_sqm"].map(yen_to_man)
            fig = px.histogram(
                plot,
                x="trade_price_man_per_sqm",
                color="trade_type",
                nbins=40,
                labels={"trade_price_man_per_sqm": "取引単価 (万円/m²)", "trade_type": "取引種別"},
                title="取引単価 分布",
            )
            fig.update_layout(**_base_layout(height=380))
            fig.update_xaxes(tickformat=",.1f")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        if "trade_type" in df.columns:
            counts = df["trade_type"].value_counts().reset_index()
            counts.columns = ["取引種別", "件数"]
            fig2 = px.pie(
                counts,
                values="件数",
                names="取引種別",
                title="取引種別 内訳",
            )
            fig2.update_layout(**_base_layout(height=380))
            st.plotly_chart(fig2, use_container_width=True)


def _render_table(df: pd.DataFrame) -> None:
    display_cols = [
        c
        for c in [
            "year",
            "quarter",
            "prefecture_name",
            "city_name",
            "district_name",
            "trade_type",
            "trade_price_per_sqm",
            "trade_price_total",
            "area_sqm",
            "build_year",
            "building_structure",
            "floor_plan",
            "city_planning",
            "period_str",
        ]
        if c in df.columns
    ]

    display_df = add_tsubo_price_column(
        df[display_cols],
        "trade_price_per_sqm",
        "trade_price_per_tsubo",
    )
    display_df = convert_yen_columns_to_man(display_df, ["trade_price_per_sqm"])

    render_html_table(
        display_df,
        [
            {"key": "year", "label": "年", "width": 48, "align": "right", "render": year_num},
            {"key": "quarter", "label": "Q", "width": 30, "align": "right", "render": year_num},
            {"key": "period_str", "label": "取引時点", "width": 90, "render": muted},
            {"key": "prefecture_name", "label": "都道府県", "width": 70, "render": muted},
            {"key": "city_name", "label": "市区町村", "width": 90, "render": muted},
            {
                "key": "district_name",
                "label": "地区",
                "width": 100,
                "render": lambda v: truncate_muted(v, 95),
            },
            {"key": "trade_type", "label": "種別", "width": 90, "render": muted},
            {
                "key": "trade_price_per_sqm",
                "label": "単価(万/m²)",
                "width": 85,
                "align": "right",
                "render": price_man,
            },
            {
                "key": "trade_price_per_tsubo",
                "label": "坪(万/坪)",
                "width": 75,
                "align": "right",
                "render": price_man,
            },
            {
                "key": "trade_price_total",
                "label": "総額(万円)",
                "width": 85,
                "align": "right",
                "render": lambda v: count_num(
                    round(float(v) / 1e4) if v is not None and v == v else None
                ),
            },
            {
                "key": "area_sqm",
                "label": "面積(m²)",
                "width": 70,
                "align": "right",
                "render": area_num,
            },
            {
                "key": "build_year",
                "label": "建築年",
                "width": 60,
                "align": "right",
                "render": year_num,
            },
            {"key": "building_structure", "label": "構造", "width": 60, "render": muted},
            {"key": "floor_plan", "label": "間取り", "width": 55, "render": muted},
        ],
        caption=f"{len(display_df):,} 件",
        min_width=900,
    )
    st.download_button(
        "CSVダウンロード",
        data=df[display_cols].to_csv(index=False, encoding="utf-8-sig"),
        file_name="trade_prices.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------
# ヘルパー
# --------------------------------------------------------------------------


def _render_no_data_guide() -> None:
    st.info("取引価格データがありません。Admin タブ → 取引価格同期 からデータを取得してください。")
    st.markdown("""
**取得方法 (CLI)**:
```bash
python sync_trade_prices.py --pref 47 --year 2024
```

**対応パラメータ**:
- `--pref`: 都道府県コード (例: 47=沖縄, 13=東京)
- `--year`: 取得年 (例: 2024)
- `--quarter`: 四半期のみ取得 (1-4, 省略時は全四半期)
""")


def _base_layout(height: int = 420) -> dict:
    return dict(
        height=height,
        template="plotly_dark",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,42,0.6)",
        font_color="#c8dff0",
        legend=dict(orientation="h", y=-0.22, bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=60, l=10, r=10),
    )
