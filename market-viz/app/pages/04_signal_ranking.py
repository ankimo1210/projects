"""Signal Ranking: z-score / percentile ランキング。"""

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
def load_signals(start: str) -> pd.DataFrame:
    db = get_db()
    with open("src/config/instruments.yaml") as f:
        cfg = yaml.safe_load(f)
    tickers = [i["ticker"] for g in cfg["instruments"].values() for i in g]
    prices = db.get_prices(tickers, frequency="1d", start=start)
    if prices.empty:
        return pd.DataFrame()
    df = build_signal_df(prices)
    # attach metadata
    meta = {
        i["ticker"]: {"name": i.get("name", ""), "asset_class": i.get("asset_class", "")}
        for g in cfg["instruments"].values()
        for i in g
    }
    df["name"] = df["ticker"].map(lambda t: meta.get(t, {}).get("name", t))
    df["asset_class"] = df["ticker"].map(lambda t: meta.get(t, {}).get("asset_class", ""))
    return df


st.set_page_config(layout="wide")
st.title("🚦 Signal Ranking")

col1, col2 = st.columns([2, 8])
with col1:
    period_days = st.selectbox("期間", [90, 180, 365, 730], index=2)

start_str = (date.today() - timedelta(days=period_days)).isoformat()
df = load_signals(start_str)

if df.empty:
    st.warning("データがありません。データ更新を実行してください。")
    st.stop()

# ----------------------------------------------------------------
# Filter controls
# ----------------------------------------------------------------
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    all_classes = sorted(df["asset_class"].dropna().unique().tolist())
    selected_classes = st.multiselect("アセットクラス", all_classes, default=all_classes)
with col_f2:
    signal_filter = st.multiselect(
        "シグナル",
        ["Overbought", "Oversold", "Watch-High", "Watch-Low", "Neutral", "N/A"],
        default=["Overbought", "Oversold", "Watch-High", "Watch-Low"],
    )
with col_f3:
    sort_col = st.selectbox(
        "ソート基準",
        ["zscore_20d", "zscore_60d", "pct_20d", "pct_60d", "ret_20d", "vol_20d"],
        index=0,
    )

df_filtered = df[df["asset_class"].isin(selected_classes)]
if "signal" in df_filtered.columns and signal_filter:
    df_filtered = df_filtered[df_filtered["signal"].isin(signal_filter)]

# sort by abs zscore
if sort_col in df_filtered.columns:
    df_filtered = df_filtered.copy()
    df_filtered["_sort_key"] = df_filtered[sort_col].abs()
    df_filtered = df_filtered.sort_values("_sort_key", ascending=False).drop(columns=["_sort_key"])

st.markdown(f"**{len(df_filtered)} 件**")

# ----------------------------------------------------------------
# Ranking table
# ----------------------------------------------------------------
display_cols = [
    "ticker",
    "name",
    "asset_class",
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
display_cols = [c for c in display_cols if c in df_filtered.columns]
show = df_filtered[display_cols].copy()

rename = {
    "ticker": "Ticker",
    "name": "銘柄名",
    "asset_class": "クラス",
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
show = show.rename(columns=rename)

fmt: dict = {}
for c in ["1D%", "5D%", "20D%", "60D%", "Vol(20)", "Vol(60)", "現在DD", "最大DD"]:
    if c in show.columns:
        fmt[c] = "{:.2%}"
for c in ["Z(20)", "Z(60)"]:
    if c in show.columns:
        fmt[c] = "{:.2f}"
for c in ["Pct(20)", "Pct(60)"]:
    if c in show.columns:
        fmt[c] = "{:.0f}%"


def _cpct(v):
    if pd.isna(v):
        return ""
    return "color: #26a69a" if v >= 0 else "color: #ef5350"


def _cz(v):
    if pd.isna(v):
        return ""
    if v >= 2.0:
        return "color: #ff9800; font-weight:bold"
    if v <= -2.0:
        return "color: #42a5f5; font-weight:bold"
    if abs(v) >= 1.5:
        return "color: #ffee58"
    return ""


def _csig(v):
    return {
        "Overbought": "color:#ff9800;font-weight:bold",
        "Oversold": "color:#42a5f5;font-weight:bold",
        "Watch-High": "color:#ffee58",
        "Watch-Low": "color:#ffee58",
    }.get(v, "")


styled = show.style.format(fmt, na_rep="-")
for col in ["1D%", "5D%", "20D%", "60D%"]:
    if col in show.columns:
        styled = styled.applymap(_cpct, subset=[col])
for col in ["Z(20)", "Z(60)"]:
    if col in show.columns:
        styled = styled.applymap(_cz, subset=[col])
if "シグナル" in show.columns:
    styled = styled.applymap(_csig, subset=["シグナル"])

st.dataframe(styled, use_container_width=True, height=600)

# ----------------------------------------------------------------
# Z-score distribution
# ----------------------------------------------------------------
if "zscore_20d" in df.columns:
    st.markdown("---")
    st.subheader("Z-Score(20d) 分布")
    import plotly.express as px

    fig = px.histogram(
        df.dropna(subset=["zscore_20d"]),
        x="zscore_20d",
        nbins=30,
        color="asset_class",
        template="plotly_dark",
        title="Z-Score 分布",
    )
    fig.add_vline(x=2, line_color="#ff9800", line_dash="dash")
    fig.add_vline(x=-2, line_color="#42a5f5", line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)
