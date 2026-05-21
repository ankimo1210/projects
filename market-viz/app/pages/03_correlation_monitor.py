"""Correlation Monitor: ヒートマップ & ローリング相関。"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta

import streamlit as st
import yaml

from src.storage.duckdb_client import DuckDBClient
from src.analytics.correlation import latest_correlations, rolling_correlation
from app.components.charts import correlation_heatmap, line_chart

with open("src/config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)

DB_PATH = _cfg["data"]["db_path"]

# デフォルト相関ペア
DEFAULT_PAIRS = [
    ("BTC-USD", "SPY"),
    ("USDJPY=X", "^N225"),
    ("^TNX", "SPY"),
    ("BTC-USD", "QQQ"),
    ("GLD", "USDJPY=X"),
]


@st.cache_resource
def get_db() -> DuckDBClient:
    db = DuckDBClient(DB_PATH)
    db.connect()
    return db


@st.cache_data(ttl=300)
def get_tickers() -> list[str]:
    with open("src/config/instruments.yaml") as f:
        cfg = yaml.safe_load(f)
    return [i["ticker"] for g in cfg["instruments"].values() for i in g]


@st.cache_data(ttl=300)
def load_prices_multi(tickers: tuple, start: str):
    import pandas as pd
    db = get_db()
    return db.get_prices(list(tickers), frequency="1d", start=start)


st.set_page_config(layout="wide")
st.title("🔗 Correlation Monitor")

# ----------------------------------------------------------------
# Controls
# ----------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    period_days = st.selectbox("期間", [90, 180, 365, 730], index=2)
with col2:
    heatmap_window = st.slider("ヒートマップ ウィンドウ (日)", 20, 252, 60)
with col3:
    rolling_window = st.slider("ローリング相関 ウィンドウ (日)", 10, 120, 20)

start_str = (date.today() - timedelta(days=period_days)).isoformat()
all_tickers = get_tickers()
prices_df = load_prices_multi(tuple(all_tickers), start_str)

if prices_df.empty:
    st.warning("データがありません。データ更新を実行してください。")
    st.stop()

# ----------------------------------------------------------------
# Heatmap
# ----------------------------------------------------------------
st.subheader("相関ヒートマップ")
corr = latest_correlations(prices_df, window=heatmap_window)
if not corr.empty:
    st.plotly_chart(correlation_heatmap(corr, f"相関マトリクス (直近{heatmap_window}日)"),
                    use_container_width=True)
else:
    st.info("相関計算に十分なデータがありません。")

st.markdown("---")

# ----------------------------------------------------------------
# Rolling correlation pairs
# ----------------------------------------------------------------
st.subheader("ローリング相関")

tab_default, tab_custom = st.tabs(["デフォルトペア", "カスタムペア"])

with tab_default:
    available_tickers = set(prices_df["ticker"].unique())
    for ta, tb in DEFAULT_PAIRS:
        if ta not in available_tickers or tb not in available_tickers:
            continue
        rc = rolling_correlation(prices_df, ta, tb, window=rolling_window)
        if not rc.dropna().empty:
            fig = line_chart(
                {f"corr({ta},{tb})": rc},
                title=f"{ta} vs {tb}",
                yformat=".2f",
                height=250,
            )
            import plotly.graph_objects as go
            fig.add_hline(y=0, line_color="gray", line_dash="dot", opacity=0.5)
            st.plotly_chart(fig, use_container_width=True)

with tab_custom:
    col_a, col_b = st.columns(2)
    with col_a:
        ticker_a = st.selectbox("銘柄 A", all_tickers, index=0, key="corr_a")
    with col_b:
        ticker_b = st.selectbox("銘柄 B", all_tickers, index=1, key="corr_b")
    rc_custom = rolling_correlation(prices_df, ticker_a, ticker_b, window=rolling_window)
    if not rc_custom.dropna().empty:
        fig_c = line_chart(
            {f"corr({ticker_a},{ticker_b})": rc_custom},
            title=f"{ticker_a} vs {ticker_b} (rolling {rolling_window}d)",
            yformat=".2f",
        )
        import plotly.graph_objects as go
        fig_c.add_hline(y=0, line_color="gray", line_dash="dot", opacity=0.5)
        st.plotly_chart(fig_c, use_container_width=True)
        latest_val = rc_custom.dropna().iloc[-1]
        st.metric(f"最新相関係数", f"{latest_val:.3f}")
    else:
        st.info("選択銘柄のデータが不足しています。")
