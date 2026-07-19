"""Activity: steps/calories trends, weekly heatmap."""
import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_store

# dataviz skill palette (references/palette.md).
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
MUTED_TEXT = "#898781"
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100",
               "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
# sequential blue ramp, light -> dark (palette.md "Sequential hue")
SEQUENTIAL_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
                   "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]


def _style(fig):
    fig.update_layout(plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font_color="#0b0b0b",
                       legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(t=30, l=10, r=10, b=10),
                       hovermode="x unified")
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS_LINE, tickfont_color=MUTED_TEXT, zeroline=False)
    return fig


def activity_page() -> None:
    st.title("活動")
    df = get_store().daily_frame(
        ["steps", "calories", "distance_km", "minutes_very_active"])
    if df.empty:
        st.info("活動データがありません。")
        return
    days = st.slider("表示日数", 30, 365, 90, key="act_days")
    df = df.tail(days).copy()

    st.subheader("歩数（7日移動平均つき）")
    df["ma7"] = df["steps"].rolling(7).mean()
    fig = px.bar(df, x="date", y="steps", labels={"date": "日付", "steps": "歩数"})
    fig.update_traces(marker_color=CATEGORICAL[0], name="歩数", showlegend=True)
    fig.add_scatter(x=df["date"], y=df["ma7"], mode="lines", name="7日平均",
                    line=dict(color=CATEGORICAL[1], width=2))
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    # Two measures of different scale (kcal vs minutes) never share one axis
    # (dataviz anti-pattern: mismatched-scale series flattens the smaller one) —
    # split into two single-series charts instead of the brief's combined chart.
    st.subheader("消費カロリー")
    fig = px.line(df, x="date", y="calories", labels={"date": "日付", "calories": "kcal"})
    fig.update_traces(line_color=CATEGORICAL[0], line_width=2)
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("高強度アクティブ分")
    fig = px.line(df, x="date", y="minutes_very_active",
                 labels={"date": "日付", "minutes_very_active": "分"})
    fig.update_traces(line_color=CATEGORICAL[0], line_width=2)
    st.plotly_chart(_style(fig), use_container_width=True, theme=None)

    st.subheader("週間ヒートマップ（歩数）")
    hm = df.copy()
    hm["date"] = pd.to_datetime(hm["date"])
    hm["weekday"] = hm["date"].dt.weekday
    hm["week"] = hm["date"].dt.strftime("%G-W%V")
    pivot = hm.pivot_table(index="weekday", columns="week", values="steps")
    labels = ["月", "火", "水", "木", "金", "土", "日"]
    pivot.index = [labels[i] for i in pivot.index]  # index by weekday number, not position
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale=SEQUENTIAL_BLUE,
                    labels=dict(color="歩数", x="週", y="曜日"))
    fig.update_layout(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font_color="#0b0b0b",
                      margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)
