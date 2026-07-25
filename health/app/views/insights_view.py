"""Insights: baseline deviations, lagged relationships, sleep rhythm, coverage."""

import pandas as pd
import plotly.express as px
import streamlit as st
from common import clip_days, load_daily, load_sleep, period_days
from health.analytics import (
    coverage_calendar,
    lagged_correlation,
    rolling_baseline_z,
    social_jetlag_hours,
)
from theme import palette, style

# Deviation is only meaningful for metrics with a stable personal baseline.
DEVIATION_METRICS = [
    ("resting_hr", "安静時心拍", "bpm"),
    ("hrv_rmssd", "HRV (RMSSD)", "ms"),
    ("temp_skin_relative", "皮膚温（基準比）", "℃"),
]
PAIRS = [
    ("sleep_minutes", "睡眠時間", "resting_hr", "安静時心拍"),
    ("sleep_minutes", "睡眠時間", "hrv_rmssd", "HRV"),
    ("steps", "歩数", "sleep_minutes", "睡眠時間"),
]
ALERT_Z = 2.0


def _deviation_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("ベースラインからの逸脱")
    st.caption("直近30日の自分の平均と比べた標準化スコア。|z| >= 2 を注目日として扱います。")
    for metric, label, unit in DEVIATION_METRICS:
        if metric not in df:
            continue
        scored = rolling_baseline_z(df[["date", metric]], metric)
        scored = scored.dropna(subset=["z"])
        if scored.empty:
            st.caption(f"{label}: 判定に必要な履歴が不足しています（30日で10日以上必要）")
            continue
        latest = scored.iloc[-1]
        st.metric(
            label,
            f"{latest[metric]:.1f} {unit}",
            delta=f"z = {latest['z']:+.1f}",
            delta_color="off",
        )
        fig = px.line(scored, x="date", y="z", labels={"date": "日付", "z": "z"})
        fig.update_traces(line_color=p["categorical"][0], line_width=2)
        fig.add_hline(y=ALERT_Z, line_dash="dot", line_color=p["muted"])
        fig.add_hline(y=-ALERT_Z, line_dash="dot", line_color=p["muted"])
        fig.update_layout(height=180)
        st.plotly_chart(style(fig, p), width="stretch", theme=None)


def _relationship_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("翌日への影響（ラグ相関）")
    st.caption("Spearman順位相関。lag=1 は「その日の値」と「翌日の値」の関係です。")
    rows = []
    for x_col, x_label, y_col, y_label in PAIRS:
        if x_col not in df or y_col not in df:
            continue
        table = lagged_correlation(df, x_col, y_col)
        for _, row in table.iterrows():
            rows.append(
                {
                    "関係": f"{x_label} → {y_label}",
                    "lag（日）": int(row["lag"]),
                    "相関": row["spearman"],
                    "日数": int(row["n"]),
                }
            )
    if not rows:
        st.caption("相関を計算できる系列がありません。")
        return
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("日数が20未満の組み合わせは相関を計算せず空欄になります。")


def _rhythm_section(sleep_df: pd.DataFrame) -> None:
    st.subheader("睡眠リズム")
    jetlag = social_jetlag_hours(sleep_df)
    if jetlag is None:
        st.caption("平日・休日それぞれ2晩以上の記録が必要です。")
        return
    st.metric("ソーシャル・ジェットラグ", f"{jetlag:+.1f} 時間")
    st.caption("休日の睡眠中央時刻から平日の中央時刻を引いた差。プラスは休日に遅寝遅起き。")


def _coverage_section(df: pd.DataFrame, p: dict) -> None:
    st.subheader("データ欠損カレンダー")
    if df.empty:
        return
    start, end = df["date"].min(), df["date"].max()
    coverage = coverage_calendar(df, "steps", start, end)
    coverage["weekday"] = coverage["date"].dt.weekday
    coverage["week"] = coverage["date"].dt.strftime("%G-W%V")
    pivot = coverage.pivot_table(index="weekday", columns="week", values="has_data")
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=p["sequential"],
        labels=dict(color="記録あり", x="週", y="曜日"),
    )
    fig.update_layout(
        paper_bgcolor=p["surface"],
        plot_bgcolor=p["surface"],
        font_color=p["ink"],
        margin=dict(t=30, l=10, r=10, b=10),
    )
    st.plotly_chart(fig, width="stretch", theme=None)
    st.caption("色が薄い日は歩数データがありません（未装着か未同期）。")


def insights_page() -> None:
    st.title("気づき")
    p = palette()
    df = load_daily(("steps", "sleep_minutes", "resting_hr", "hrv_rmssd", "temp_skin_relative"))
    if df.empty:
        st.info("データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days()).copy()
    df["date"] = pd.to_datetime(df["date"])
    _deviation_section(df, p)
    _relationship_section(df, p)
    _rhythm_section(load_sleep())
    _coverage_section(df, p)
