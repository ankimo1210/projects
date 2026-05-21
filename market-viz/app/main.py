"""Market Viz - entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import yaml

with open("src/config/settings.yaml") as f:
    _settings = yaml.safe_load(f)

st.set_page_config(
    page_title=_settings["app"]["title"],
    page_icon=_settings["app"]["page_icon"],
    layout=_settings["app"]["layout"],
    initial_sidebar_state="expanded",
)

st.sidebar.title("📈 Market Viz")
st.sidebar.markdown("---")

from src.storage.duckdb_client import DuckDBClient
from src.data.update import update_daily, update_crypto_intraday

DB_PATH = _settings["data"]["db_path"]


@st.cache_resource
def get_db() -> DuckDBClient:
    db = DuckDBClient(DB_PATH)
    db.connect()
    return db


db = get_db()

with st.sidebar:
    st.markdown("### データ更新")
    lookback = st.slider("取得日数", 30, 1825, 365, step=30)

    if st.button("📥 日次データ更新", use_container_width=True):
        progress_placeholder = st.empty()
        logs: list[str] = []

        def log(msg: str) -> None:
            logs.append(msg)
            progress_placeholder.text("\n".join(logs[-5:]))

        with st.spinner("更新中..."):
            results = update_daily(db, lookback_days=lookback, on_progress=log)

        progress_placeholder.empty()
        ok = sum(1 for v in results.values() if v.startswith("ok"))
        skipped = sum(1 for v in results.values() if v == "up-to-date")
        errors = sum(1 for v in results.values() if v.startswith("error"))
        st.success(f"完了: {ok}件更新, {skipped}件スキップ, {errors}件エラー")
        st.cache_data.clear()

    if st.button("📥 Crypto分足更新(1m)", use_container_width=True):
        with st.spinner("Crypto 1分足取得中..."):
            results = update_crypto_intraday(db, timeframe="1m", lookback_days=3)
        ok = sum(1 for v in results.values() if v.startswith("ok"))
        st.success(f"Crypto 1分足: {ok}件更新")
        st.cache_data.clear()

    st.markdown("---")
    st.caption("ローカル個人用ツール")


st.title("Market Viz")
st.markdown("""
左サイドバーの **データ更新** ボタンでデータを取得してください。

取得後、左の **Pages** から各画面に移動できます。

| ページ | 内容 |
|---|---|
| 01 Market Dashboard | 全銘柄の概況サマリー |
| 02 Chart Workbench | インタラクティブチャート |
| 03 Correlation Monitor | 相関ヒートマップ・ローリング相関 |
| 04 Signal Ranking | z-score / percentile ランキング |
| 05 Backtest | 戦略バックテスト |
| 06 Alert Monitor | アラート一覧 |
""")
