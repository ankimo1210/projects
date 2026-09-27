"""Seven offline views with separate synthetic and saved-data modes."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from market_research.macro import as_of
from market_research.reports import render_demo_report
from market_research.research.run_store import load_demo_run, save_current_demo_run
from market_research.services import build_demo_run

st.set_page_config(page_title="market-research", layout="wide")
data_mode = st.sidebar.radio("データ", ("合成デモ", "保存データ"), key="data_mode")
if data_mode == "保存データ":
    from market_research.app_real import render_real_app

    render_real_app()
    st.stop()

run = build_demo_run()
st.title("market-research")
st.caption(f"合成デモ | run {run.run_id} | 実データ・口座情報は含みません")
st.info(
    "この入口は工程3の初期版です。表示用の合成価格は取得を行わず、投資判断用の値ではありません。"
)

titles = [
    "市場概要",
    "銘柄・バスケット",
    "シグナル・スクリーナー",
    "戦略比較",
    "マクロと公表",
    "仮想配分・リスク",
    "品質・実行履歴",
]
tabs = st.tabs(titles)
prices = run.prices
returns = prices.pct_change().dropna()

with tabs[0]:
    st.subheader("市場概要")
    st.plotly_chart(px.line(prices, title="合成価格の推移"), use_container_width=True)
    st.metric("観測数", len(prices))
    st.caption("監視銘柄と実データ更新は次の工程で接続します。")

with tabs[1]:
    st.subheader("銘柄・バスケット")
    selected = st.selectbox("合成銘柄", prices.columns, key="symbol")
    st.plotly_chart(px.line(prices[selected], title=selected), use_container_width=True)
    equal_basket = (prices / prices.iloc[0]).mean(axis=1)
    st.plotly_chart(
        px.line(equal_basket, title="合成2銘柄の等ウェイト比較"), use_container_width=True
    )
    st.caption("財務・指数構成銘柄・実際の調整価格は未接続です。")

with tabs[2]:
    st.subheader("シグナル・スクリーナー")
    momentum = prices.pct_change(5).iloc[-1]
    ranking = pd.DataFrame(
        {"5観測の変化率": momentum, "次期の目標ウェイト": run.target_weights.iloc[-1]}
    )
    st.dataframe(ranking.sort_values("5観測の変化率", ascending=False))
    st.caption("デモの条件だけを表示しています。実データのスクリーナーは未接続です。")

with tabs[3]:
    st.subheader("戦略比較")
    st.plotly_chart(
        px.line(run.backtest.equity, title="lag 1・close-to-close 研究近似"),
        use_container_width=True,
    )
    st.metric("合成デモの最終資産倍率", f"{run.backtest.equity.iloc[-1]:.3f}")
    st.caption("手数料3 bps + スリッページ2 bps。翌日始値での実約定を示すものではありません。")

with tabs[4]:
    st.subheader("マクロと公表")
    point = st.selectbox("情報時点", list(prices.index), index=len(prices) - 1, key="asof")
    available = as_of(
        run.macro_observations, "DEMO_CPI", point.to_pydatetime() + timedelta(hours=1)
    )
    if available:
        row = available[0]
        st.metric("合成 CPI 指標", f"{row.value:.1f}")
        st.caption(f"公表 {row.release_at.isoformat()} / 版 {row.vintage_id}")
    else:
        st.write("この時点では未公表")
    st.caption("ALFRED・ESRI・MoF 等の実データは未接続です。")

with tabs[5]:
    st.subheader("仮想配分・リスク")
    allocation = run.target_weights.iloc[-1]
    st.dataframe(allocation.rename("仮想ウェイト").to_frame())
    annual_volatility = float((allocation @ returns.cov() @ allocation) ** 0.5 * 252**0.5)
    st.metric("合成系列の年率ボラティリティ", f"{annual_volatility:.1%}")
    st.caption("実口座の保有・損益は扱いません。")

with tabs[6]:
    st.subheader("品質・実行履歴")
    st.metric("警告・拒否の数", sum(bar.quality != "ok" for bar in run.bars))
    st.json(
        {
            "run_id": run.run_id,
            "mode": run.mode,
            "input_hash": run.input_hash,
            "price_adjustment": "raw",
            "network_fetch": False,
        }
    )
    st.download_button(
        "実行要約を保存",
        data=f"{run.run_id} / 合成デモ\n",
        file_name=f"market-research-{run.run_id}.txt",
    )
    html = render_demo_report(run)
    st.download_button(
        "HTMLレポートを保存",
        data=html,
        file_name=f"market-research-{run.run_id}.html",
        mime="text/html",
    )
    data_root = Path(
        st.text_input(
            "研究runの保存先（WSLパス）",
            value=os.environ.get(
                "MARKET_RESEARCH_DATA_ROOT", str(Path.home() / ".local/share/market-research")
            ),
        )
    )
    artifact_root = data_root / "runs"
    if st.button("合成runを永続保存"):
        try:
            artifact = save_current_demo_run(artifact_root, run, html=html)
            st.success(f"保存済み合成run: {artifact.artifact_id}")
        except (ValueError, OSError) as error:
            st.error(f"合成runを保存できません: {error}")
    saved = sorted(artifact_root.glob("*/manifest.json")) if artifact_root.is_dir() else []
    if saved:
        artifact_id = saved[-1].parent.name
        try:
            artifact = load_demo_run(artifact_root, artifact_id, expected=run)
            st.caption(
                f"保存済み合成run {artifact.manifest['source_run_id']} / "
                f"artifact {artifact.artifact_id} / commit {artifact.manifest['code_commit']}"
            )
        except (ValueError, OSError) as error:
            st.warning(f"保存済みrunを確認できません: {error}")
    st.caption("外部通知は行いません。")
