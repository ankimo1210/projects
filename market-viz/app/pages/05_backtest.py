"""Backtest: 日次戦略バックテスト。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from app.components.charts import candlestick_chart, drawdown_chart, equity_chart
from market_viz.analytics.backtest import (
    ma_cross_signal,
    momentum_signal,
    run_backtest,
    volatility_breakout_signal,
    zscore_reversion_signal,
)
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


@st.cache_data(ttl=60)
def load_prices(ticker: str, start: str) -> pd.DataFrame:
    return get_db().get_prices([ticker], frequency="1d", start=start)


st.set_page_config(layout="wide")
st.title("🔬 Backtest")

# ----------------------------------------------------------------
# Controls
# ----------------------------------------------------------------
st.subheader("設定")
col1, col2, col3 = st.columns(3)
with col1:
    tickers = get_tickers()
    default_idx = tickers.index("BTC-USD") if "BTC-USD" in tickers else 0
    ticker = st.selectbox("銘柄", tickers, index=default_idx)
with col2:
    period_days = st.selectbox("バックテスト期間", [180, 365, 730, 1825], index=1)
with col3:
    strategy = st.selectbox(
        "戦略",
        ["MA Cross", "Z-Score Reversion", "Momentum", "Volatility Breakout"],
        index=0,
    )

# Strategy params
st.subheader("戦略パラメータ")
if strategy == "MA Cross":
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fast = st.slider("Fast MA", 5, 100, 20)
    with col_p2:
        slow = st.slider("Slow MA", 20, 300, 60)

    def signal_fn(c):
        return ma_cross_signal(c, fast=fast, slow=slow)

elif strategy == "Z-Score Reversion":
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        z_window = st.slider("Z ウィンドウ", 10, 252, 60)
    with col_p2:
        z_entry = st.slider("エントリー閾値 (abs)", 1.0, 3.0, 2.0, step=0.1)
    with col_p3:
        z_exit = st.slider("エグジット閾値 (abs)", 0.0, 1.5, 0.5, step=0.1)

    def signal_fn(c):
        return zscore_reversion_signal(c, window=z_window, entry=z_entry, exit_=z_exit)

elif strategy == "Momentum":
    mom_window = st.slider("モメンタム ウィンドウ", 5, 252, 20)

    def signal_fn(c):
        return momentum_signal(c, window=mom_window)

else:  # Volatility Breakout
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        vb_window = st.slider("ウィンドウ", 5, 100, 20)
    with col_p2:
        vb_mult = st.slider("マルチプライヤー", 0.5, 3.0, 1.0, step=0.1)

    def signal_fn(c):
        return volatility_breakout_signal(c, window=vb_window, mult=vb_mult)


commission = st.slider("手数料 (%)", 0.0, 0.5, 0.1, step=0.01) / 100
slippage = st.slider("スリッページ (%)", 0.0, 0.5, 0.05, step=0.01) / 100

# ----------------------------------------------------------------
# Run backtest
# ----------------------------------------------------------------
if st.button("▶ バックテスト実行", type="primary"):
    start_str = (date.today() - timedelta(days=period_days)).isoformat()
    prices_df = load_prices(ticker, start_str)
    if prices_df.empty:
        st.error("データがありません。データ更新を実行してください。")
        st.stop()

    with st.spinner("計算中..."):
        result = run_backtest(
            prices_df,
            ticker,
            signal_fn=signal_fn,
            commission=commission,
            slippage=slippage,
        )

    m = result.metrics

    # Metrics
    st.markdown("---")
    st.subheader("結果サマリー")
    cols = st.columns(7)
    metric_items = [
        ("累積リターン", f"{m.get('total_return', 0):.1%}"),
        ("年率リターン", f"{m.get('annual_return', 0):.1%}"),
        ("年率ボラ", f"{m.get('annual_volatility', 0):.1%}"),
        ("シャープ比", f"{m.get('sharpe_ratio', 0):.2f}"),
        ("最大DD", f"{m.get('max_drawdown', 0):.1%}"),
        ("勝率", f"{m.get('win_rate', 0):.1%}"),
        ("取引回数", str(m.get("trade_count", 0))),
    ]
    for col, (label, val) in zip(cols, metric_items, strict=False):
        col.metric(label, val)

    # Charts
    st.plotly_chart(
        equity_chart(result.equity, title=f"{ticker} | {strategy}"), use_container_width=True
    )
    st.plotly_chart(drawdown_chart(result.equity), use_container_width=True)

    # Price with MA if applicable
    if strategy == "MA Cross":
        st.plotly_chart(
            candlestick_chart(
                prices_df.sort_values("timestamp"),
                ticker=ticker,
                show_volume=False,
                ma_windows=[fast, slow],
            ),
            use_container_width=True,
        )

    # Trades table
    if not result.trades.empty:
        with st.expander(f"取引履歴 ({len(result.trades)}件)"):
            st.dataframe(result.trades, use_container_width=True)
