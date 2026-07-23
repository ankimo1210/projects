"""Sleep: stage composition, duration/efficiency trends, nightly gantt, weekday pattern."""

import pandas as pd
import plotly.express as px
import streamlit as st
from common import calendar_rolling_mean, clip_days, load_sleep, period_days
from theme import palette, style

STAGES = [
    ("minutes_deep", "深い"),
    ("minutes_rem", "REM"),
    ("minutes_light", "浅い"),
    ("minutes_wake", "覚醒"),
]
GANTT_MAX_NIGHTS = 90
WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


def _stage_bar(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("ステージ構成")
    stage_columns = [column for column, _ in STAGES]
    has_stages = sf[stage_columns].fillna(0).sum(axis=1) > 0
    staged = sf[has_stages]
    if staged.empty:
        # Classic sleep only: no deep/rem/light breakdown exists at all.
        st.info(
            "詳細ステージなし（Classic sleep）: 深い/REM/浅いの内訳がないため、睡眠/覚醒の2区分で表示します。"
        )
        parts = [("minutes_asleep", "睡眠"), ("minutes_wake", "覚醒")]
        staged = sf
    else:
        if not has_stages.all():
            st.caption(f"詳細ステージなし: {(~has_stages).sum()} セッション（表示対象外）")
        parts = STAGES
    colors = {label: p["categorical"][i] for i, (_, label) in enumerate(parts)}
    long = staged.melt(
        id_vars=["date"], value_vars=[c for c, _ in parts], var_name="stage", value_name="minutes"
    )
    long["stage"] = long["stage"].map(dict(parts))
    fig = px.bar(
        long,
        x="date",
        y="minutes",
        color="stage",
        color_discrete_map=colors,
        labels={"minutes": "分", "date": "日付", "stage": "ステージ"},
    )
    # surface gap between stacked segments (mark spec) instead of a border stroke
    fig.update_traces(marker_line_color=p["surface"], marker_line_width=2)
    st.plotly_chart(style(fig, p), width="stretch", theme=None)


def _trends(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("睡眠時間トレンド（7日移動平均つき）")
    trend = sf[["date", "minutes_asleep"]].copy()
    trend["ma7"] = calendar_rolling_mean(trend, "minutes_asleep")
    trend = trend.rename(columns={"minutes_asleep": "実績", "ma7": "7日移動平均"})
    fig = px.line(
        trend,
        x="date",
        y=["実績", "7日移動平均"],
        color_discrete_sequence=p["line_safe"],
        labels={"date": "日付", "value": "分", "variable": ""},
    )
    fig.update_traces(line_width=2)
    st.plotly_chart(style(fig, p), width="stretch", theme=None)

    st.subheader("睡眠効率")
    fig = px.line(sf, x="date", y="efficiency", labels={"date": "日付", "efficiency": "%"})
    fig.update_traces(line_color=p["categorical"][0], line_width=2)
    st.plotly_chart(style(fig, p), width="stretch", theme=None)


def _night_gantt(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("就寝・起床（夜ごとの睡眠区間）")
    gd = sf.tail(GANTT_MAX_NIGHTS).copy()
    if len(sf) > GANTT_MAX_NIGHTS:
        st.caption(f"直近 {GANTT_MAX_NIGHTS} 夜のみ表示")
    gd["start_ts"] = pd.to_datetime(gd["start_ts"])
    gd["end_ts"] = pd.to_datetime(gd["end_ts"])
    # Normalize every night onto one clock axis anchored at the noon before
    # the wake date, so bedtimes crossing midnight stay continuous.
    anchor = pd.to_datetime(gd["date"]) - pd.Timedelta(hours=12)
    ref = pd.Timestamp("2000-01-01")
    gd["clock_start"] = ref + (gd["start_ts"] - anchor)
    gd["clock_end"] = ref + (gd["end_ts"] - anchor)
    gd["night"] = pd.to_datetime(gd["date"]).dt.strftime("%m/%d")
    fig = px.timeline(
        gd,
        x_start="clock_start",
        x_end="clock_end",
        y="night",
        hover_data={
            "clock_start": False,
            "clock_end": False,
            "start_ts": "|%H:%M",
            "end_ts": "|%H:%M",
        },
    )
    fig.update_traces(
        marker_color=p["categorical"][0], marker_line_color=p["surface"], marker_line_width=1
    )
    fig.update_yaxes(autorange="reversed")
    ticks = list(range(6, 28, 3))
    fig.update_xaxes(
        tickvals=[ref + pd.Timedelta(hours=h) for h in ticks],
        ticktext=[f"{(12 + h) % 24}:00" for h in ticks],
    )
    fig.update_layout(height=max(300, min(900, 12 * len(gd) + 80)))
    st.plotly_chart(style(fig, p), width="stretch", theme=None)


def _weekday_pattern(sf: pd.DataFrame, p: dict) -> None:
    st.subheader("曜日パターン")
    wp = sf.copy()
    wp["weekday"] = pd.to_datetime(wp["date"]).dt.weekday
    agg = wp.groupby("weekday")["minutes_asleep"].mean().reset_index()
    agg["weekday"] = agg["weekday"].map(dict(enumerate(WEEKDAY_LABELS)))
    fig = px.bar(
        agg,
        x="weekday",
        y="minutes_asleep",
        category_orders={"weekday": WEEKDAY_LABELS},
        labels={"weekday": "曜日", "minutes_asleep": "平均睡眠時間（分）"},
    )
    fig.update_traces(marker_color=p["categorical"][0])
    st.plotly_chart(style(fig, p), width="stretch", theme=None)


def sleep_page() -> None:
    st.title("睡眠")
    p = palette()
    sf = load_sleep()
    sf = sf[sf["is_main"]].copy()
    if sf.empty:
        st.info("睡眠データがありません。まず「同期」ページで同期してください。")
        return
    sf = clip_days(sf, period_days())
    _stage_bar(sf, p)
    _trends(sf, p)
    _night_gantt(sf, p)
    _weekday_pattern(sf, p)
