"""Activity: steps/intensity/distance/calories trends, heatmap, intraday steps."""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from common import clip_days, load_daily, load_intraday, period_days
from theme import palette, style

INTENSITIES = [
    ("minutes_lightly_active", "軽い"),
    ("minutes_fairly_active", "中程度"),
    ("minutes_very_active", "高強度"),
]
HEATMAP_MAX_WEEKS = 26
WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


def activity_page() -> None:
    st.title("活動")
    p = palette()
    df = load_daily(
        (
            "steps",
            "calories",
            "distance_km",
            "minutes_lightly_active",
            "minutes_fairly_active",
            "minutes_very_active",
        )
    )
    if df.empty:
        st.info("活動データがありません。まず「同期」ページで同期してください。")
        return
    df = clip_days(df, period_days()).copy()

    st.subheader("歩数（7日移動平均つき）")
    df["ma7"] = df["steps"].rolling(7).mean()
    fig = px.bar(df, x="date", y="steps", labels={"date": "日付", "steps": "歩数"})
    fig.update_traces(marker_color=p["categorical"][0], name="歩数", showlegend=True)
    fig.add_scatter(
        x=df["date"],
        y=df["ma7"],
        mode="lines",
        name="7日平均",
        line=dict(color=p["categorical"][1], width=2),
    )
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("活動強度の内訳（分）")
    intensity_columns = [c for c, _ in INTENSITIES]
    im = df[["date", *intensity_columns]].dropna(how="all", subset=intensity_columns)
    if im.empty:
        st.caption("データなし（デバイス非対応の可能性）")
    else:
        long = im.melt(id_vars=["date"], var_name="intensity", value_name="minutes")
        long["intensity"] = long["intensity"].map(dict(INTENSITIES))
        colors = {label: p["categorical"][i] for i, (_, label) in enumerate(INTENSITIES)}
        fig = px.bar(
            long,
            x="date",
            y="minutes",
            color="intensity",
            color_discrete_map=colors,
            labels={"date": "日付", "minutes": "分", "intensity": "強度"},
        )
        fig.update_traces(marker_line_color=p["surface"], marker_line_width=1)
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    # Two measures of different scale (kcal vs km) never share one axis
    # (dataviz anti-pattern: mismatched-scale series flattens the smaller one).
    st.subheader("距離 (km)")
    fig = px.line(df, x="date", y="distance_km", labels={"date": "日付", "distance_km": "km"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("消費カロリー")
    fig = px.line(df, x="date", y="calories", labels={"date": "日付", "calories": "kcal"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), use_container_width=True, theme=None)

    st.subheader("週間ヒートマップ（歩数）")
    hm = df.copy()
    hm["date"] = pd.to_datetime(hm["date"])
    hm["weekday"] = hm["date"].dt.weekday
    hm["week"] = hm["date"].dt.strftime("%G-W%V")
    pivot = hm.pivot_table(index="weekday", columns="week", values="steps")
    if pivot.shape[1] > HEATMAP_MAX_WEEKS:
        pivot = pivot.iloc[:, -HEATMAP_MAX_WEEKS:]
        st.caption(f"直近 {HEATMAP_MAX_WEEKS} 週のみ表示")
    pivot.index = [WEEKDAY_LABELS[i] for i in pivot.index]  # weekday number, not position
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=p["sequential"],
        labels=dict(color="歩数", x="週", y="曜日"),
    )
    fig.update_layout(
        paper_bgcolor=p["surface"],
        plot_bgcolor=p["surface"],
        font_color=p["ink"],
        margin=dict(t=30, l=10, r=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.subheader("日内歩数ビューア")
    day = st.date_input("日付", value=date.today(), key="act_day")
    intra = load_intraday("steps", day)
    if intra.empty:
        st.caption("この日の intraday データはありません（直近30日のみ取得）。")
    else:
        fig = px.bar(intra, x="ts", y="value", labels={"value": "歩数", "ts": "時刻"})
        fig.update_traces(marker_color=p["categorical"][0])
        st.plotly_chart(style(fig, p), use_container_width=True, theme=None)
