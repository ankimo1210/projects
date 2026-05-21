"""Market Dashboard: 全銘柄サマリー表示。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yaml
from market_viz.analytics.signals import build_signal_df
from market_viz.storage.duckdb_client import DuckDBClient

with open("src/config/settings.yaml") as f:
    _cfg = yaml.safe_load(f)

DB_PATH = _cfg["data"]["db_path"]


@st.cache_resource
def get_db() -> DuckDBClient:
    db = DuckDBClient(DB_PATH)
    db.connect()
    return db


@st.cache_data(ttl=300)
def load_signal_data(start: str) -> pd.DataFrame:
    db = get_db()
    with open("src/config/instruments.yaml") as f:
        instruments_cfg = yaml.safe_load(f)
    tickers = [i["ticker"] for g in instruments_cfg["instruments"].values() for i in g]
    prices = db.get_prices(tickers, frequency="1d", start=start)
    if prices.empty:
        return pd.DataFrame()
    return build_signal_df(prices)


st.set_page_config(layout="wide")
st.title("📊 Market Dashboard")

col_ctrl1, col_ctrl2 = st.columns([2, 8])
with col_ctrl1:
    lookback_days = st.selectbox("期間", [90, 180, 365, 730], index=2)

start_str = (date.today() - timedelta(days=lookback_days)).isoformat()
df = load_signal_data(start_str)

if df.empty:
    st.warning("データがありません。サイドバーの「データ更新」ボタンを押してください。")
    st.stop()

# ----------------------------------------------------------------
# Asset class filter
# ----------------------------------------------------------------
with open("src/config/instruments.yaml") as f:
    inst_cfg = yaml.safe_load(f)
ticker_meta = {
    i["ticker"]: {"name": i.get("name", ""), "asset_class": i.get("asset_class", "")}
    for g in inst_cfg["instruments"].values()
    for i in g
}
df["name"] = df["ticker"].map(lambda t: ticker_meta.get(t, {}).get("name", t))
df["asset_class"] = df["ticker"].map(lambda t: ticker_meta.get(t, {}).get("asset_class", ""))

all_classes = sorted(df["asset_class"].dropna().unique().tolist())
selected_classes = st.multiselect(
    "アセットクラス",
    options=all_classes,
    default=all_classes,
)
df = df[df["asset_class"].isin(selected_classes)]

# ----------------------------------------------------------------
# Summary metrics
# ----------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    ob = (df["signal"] == "Overbought").sum() if "signal" in df.columns else 0
    st.metric("Overbought", ob)
with col2:
    os_ = (df["signal"] == "Oversold").sum() if "signal" in df.columns else 0
    st.metric("Oversold", os_)
with col3:
    watch = df["signal"].isin(["Watch-High", "Watch-Low"]).sum() if "signal" in df.columns else 0
    st.metric("Watch", watch)
with col4:
    st.metric("銘柄数", len(df))

st.markdown("---")

# ----------------------------------------------------------------
# Main table
# ----------------------------------------------------------------
display_cols_ordered = [
    "ticker",
    "name",
    "asset_class",
    "last_close",
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "vol_20d",
    "vol_60d",
    "zscore_20d",
    "zscore_60d",
    "pct_20d",
    "pct_60d",
    "current_dd",
    "max_dd",
    "signal",
]
display_cols = [c for c in display_cols_ordered if c in df.columns]
show_df = df[display_cols].copy()

# column rename for display
rename = {
    "ticker": "Ticker",
    "name": "銘柄名",
    "asset_class": "クラス",
    "last_close": "終値",
    "ret_1d": "1D%",
    "ret_5d": "5D%",
    "ret_20d": "20D%",
    "ret_60d": "60D%",
    "vol_20d": "Vol(20)",
    "vol_60d": "Vol(60)",
    "zscore_20d": "Z(20)",
    "zscore_60d": "Z(60)",
    "pct_20d": "Pct(20)",
    "pct_60d": "Pct(60)",
    "current_dd": "現在DD",
    "max_dd": "最大DD",
    "signal": "シグナル",
}
show_df = show_df.rename(columns=rename)

# Format
fmt: dict[str, str] = {}
for col in ["1D%", "5D%", "20D%", "60D%", "Vol(20)", "Vol(60)", "現在DD", "最大DD"]:
    if col in show_df.columns:
        fmt[col] = "{:.2%}"
for col in ["Z(20)", "Z(60)"]:
    if col in show_df.columns:
        fmt[col] = "{:.2f}"
for col in ["Pct(20)", "Pct(60)"]:
    if col in show_df.columns:
        fmt[col] = "{:.0f}%"
if "終値" in show_df.columns:
    fmt["終値"] = "{:.4f}"


def color_pct(val):
    if pd.isna(val):
        return ""
    return "color: #26a69a" if val >= 0 else "color: #ef5350"


def color_z(val):
    if pd.isna(val):
        return ""
    if val >= 2.0:
        return "color: #ff9800; font-weight:bold"
    if val <= -2.0:
        return "color: #42a5f5; font-weight:bold"
    if abs(val) >= 1.5:
        return "color: #ffee58"
    return ""


def color_signal(val):
    mapping = {
        "Overbought": "color: #ff9800; font-weight:bold",
        "Oversold": "color: #42a5f5; font-weight:bold",
        "Watch-High": "color: #ffee58",
        "Watch-Low": "color: #ffee58",
        "Neutral": "",
    }
    return mapping.get(val, "")


styled = show_df.style.format(fmt, na_rep="-")
for col in ["1D%", "5D%", "20D%", "60D%"]:
    if col in show_df.columns:
        styled = styled.applymap(color_pct, subset=[col])
for col in ["Z(20)", "Z(60)"]:
    if col in show_df.columns:
        styled = styled.applymap(color_z, subset=[col])
if "シグナル" in show_df.columns:
    styled = styled.applymap(color_signal, subset=["シグナル"])

st.dataframe(styled, use_container_width=True, height=600)

# ----------------------------------------------------------------
# Signal breakdown
# ----------------------------------------------------------------
if "signal" in df.columns:
    st.markdown("---")
    st.subheader("シグナル内訳")
    sig_counts = df["signal"].value_counts().reset_index()
    sig_counts.columns = ["signal", "count"]
    st.bar_chart(sig_counts.set_index("signal"))
