"""Chart Workbench: インタラクティブチャート。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from app.components.charts import candlestick_chart, line_chart
from market_viz.analytics.drawdown import drawdown_series
from market_viz.analytics.returns import cumulative_return
from market_viz.analytics.volatility import realized_vol
from market_viz.analytics.zscore import rolling_zscore
from market_viz.config import PROJECT_ROOT, load_instruments_config, load_settings
from market_viz.storage.duckdb_client import DuckDBClient

_cfg = load_settings()

DB_PATH = PROJECT_ROOT / _cfg["data"]["db_path"]


@st.cache_resource
def get_db() -> DuckDBClient:
    db = DuckDBClient(DB_PATH)
    db.connect()
    return db


@st.cache_data(ttl=300)
def get_tickers() -> list[str]:
    cfg = load_instruments_config()
    return [i["ticker"] for g in cfg["instruments"].values() for i in g]


@st.cache_data(ttl=300)
def load_prices(ticker: str, start: str, frequency: str) -> pd.DataFrame:
    return get_db().get_prices([ticker], frequency=frequency, start=start)


st.set_page_config(layout="wide")
st.title("📈 Chart Workbench")

# ----------------------------------------------------------------
# Controls
# ----------------------------------------------------------------
col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
with col1:
    tickers = get_tickers()
    default_idx = tickers.index("BTC-USD") if "BTC-USD" in tickers else 0
    ticker = st.selectbox("銘柄", tickers, index=default_idx)
with col2:
    period_days = st.selectbox("期間", [30, 90, 180, 365, 730, 1825], index=3)
with col3:
    interval = st.selectbox("時間軸", ["1d", "1wk", "1mo"], index=0)
with col4:
    ma_windows = st.multiselect("移動平均", [10, 20, 50, 100, 200], default=[20, 50])

start_str = (date.today() - timedelta(days=period_days)).isoformat()
df = load_prices(ticker, start_str, interval)

if df.empty:
    st.warning(f"{ticker} のデータがありません。データ更新を実行してください。")
    st.stop()

df = df.sort_values("timestamp")

# ----------------------------------------------------------------
# Candlestick
# ----------------------------------------------------------------
st.plotly_chart(
    candlestick_chart(df, ticker=ticker, show_volume=True, ma_windows=ma_windows or None),
    use_container_width=True,
)

# ----------------------------------------------------------------
# Sub-charts
# ----------------------------------------------------------------
tab_ret, tab_vol, tab_dd, tab_z = st.tabs(["リターン", "ボラティリティ", "ドローダウン", "Z-Score"])

close = df.set_index("timestamp")["close"]

with tab_ret:
    cum_ret = cumulative_return(close)
    st.plotly_chart(
        line_chart({"累積リターン": cum_ret}, title="累積リターン", yformat=".1%"),
        use_container_width=True,
    )

with tab_vol:
    v20 = realized_vol(close, window=20)
    v60 = realized_vol(close, window=60)
    st.plotly_chart(
        line_chart(
            {"Vol(20d)": v20, "Vol(60d)": v60}, title="実現ボラティリティ（年率）", yformat=".1%"
        ),
        use_container_width=True,
    )

with tab_dd:
    dd = drawdown_series(close)
    st.plotly_chart(
        line_chart({"ドローダウン": dd}, title="ドローダウン", yformat=".1%"),
        use_container_width=True,
    )

with tab_z:
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        z_window = st.slider("Z-Score ウィンドウ", 10, 252, 60)
    z = rolling_zscore(close, window=z_window)
    fig_z = line_chart(
        {f"Z-Score({z_window}d)": z}, title=f"Z-Score (window={z_window})", yformat=".2f"
    )
    # Add horizontal lines at ±2, ±1.5

    for level, color, dash in [
        (2, "#ff9800", "dash"),
        (-2, "#42a5f5", "dash"),
        (1.5, "#ffee58", "dot"),
        (-1.5, "#ffee58", "dot"),
    ]:
        fig_z.add_hline(y=level, line_color=color, line_dash=dash, opacity=0.7)
    st.plotly_chart(fig_z, use_container_width=True)

# ----------------------------------------------------------------
# Raw data
# ----------------------------------------------------------------
with st.expander("生データ"):
    st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)
