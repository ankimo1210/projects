"""
app.py
不動産情報ライブラリ 地価公示 ローカルアプリ - Streamlit エントリポイント。

起動方法:
    streamlit run app.py --server.address 127.0.0.1
"""
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加（ui/ サブモジュールから import できるように）
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

import db
from config import ensure_dirs, get_logger, validate_api_key
from ui.styles import DARK_THEME_CSS


logger = get_logger(__name__)

# --------------------------------------------------------------------------
# ページ設定
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="地価公示ローカルアプリ",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# セッション初期化
# --------------------------------------------------------------------------

@st.cache_resource
def get_db_connection():
    """DuckDB 接続をキャッシュして返す。"""
    ensure_dirs()
    conn = db.get_connection()
    db.create_tables_if_needed(conn)
    return conn


def check_api_key() -> bool:
    try:
        validate_api_key()
        return True
    except EnvironmentError:
        return False


def load_filtered_data(conn, filters: dict):
    """フィルタ条件に合わせて DB からデータを読み込む。"""
    if not filters.get("year"):
        return None
    active_filters = {k: v for k, v in filters.items() if v is not None}
    return db.read_land_prices(conn, filters=active_filters)


# --------------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------------

def main():
    conn = get_db_connection()

    # ── 年度セレクタ（ページ上部） ──────────────────────────────
    years = db.get_available_years(conn)
    col_year, col_warn = st.columns([1, 5])
    with col_year:
        if years:
            selected_year = st.selectbox("📅 年度", years, index=0, key="global_year")
        else:
            st.info("データなし。Admin タブから同期してください。")
            selected_year = None
    with col_warn:
        if not check_api_key():
            st.warning("APIキー未設定。.env を確認してください。")

    filters = {"year": selected_year}

    pages = [
        "🗺 Map",
        "🔍 Search",
        "🏙 都市トレンド",
        "🏆 Ranking",
        "🏠 取引価格",
        "🏘 賃料相場",
        "🏢 物件分析",
        "📦 掲載物件",
        "⚙ Admin",
    ]
    selected_page = st.radio(
        "ページ",
        pages,
        horizontal=True,
        label_visibility="collapsed",
        key="active_page",
    )

    # st.tabs は非表示タブも実行するため、選択中ページだけを遅延 import/render する。
    if selected_page in {"🗺 Map", "🔍 Search", "🏆 Ranking"}:
        df = load_filtered_data(conn, filters)
    else:
        df = None

    if selected_page == "🗺 Map":
        from ui.map_tab import render_map_tab

        render_map_tab(df, filters, conn=conn)
    elif selected_page == "🔍 Search":
        from ui.search_tab import render_search_tab

        render_search_tab(df, filters)
    elif selected_page == "🏙 都市トレンド":
        from ui.trend_tab import render_trend_tab

        render_trend_tab(conn, filters)
    elif selected_page == "🏆 Ranking":
        from ui.ranking_tab import render_ranking_tab

        render_ranking_tab(df, filters)
    elif selected_page == "🏠 取引価格":
        from ui.trade_tab import render_trade_tab

        render_trade_tab(conn, filters)
    elif selected_page == "🏘 賃料相場":
        from ui.rent_market_tab import render_rent_market_tab

        render_rent_market_tab(conn)
    elif selected_page == "🏢 物件分析":
        from ui.property_tab import render_property_tab

        render_property_tab(conn, filters)
    elif selected_page == "📦 掲載物件":
        from ui.listings_tab import render_listings_tab

        render_listings_tab(conn)
    elif selected_page == "⚙ Admin":
        from ui.admin_tab import render_admin_tab

        render_admin_tab(conn)


if __name__ == "__main__":
    main()
