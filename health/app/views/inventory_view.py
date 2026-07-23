"""Inventory page: which metrics have data, ranges, sync status."""

import streamlit as st
from common import get_store
from health.inventory import build_inventory, build_series_inventory


def inventory_page() -> None:
    st.title("データ棚卸し")
    store = get_store()
    st.subheader("公開データ型")
    st.caption("Google Health が公開するデータ型と、このアプリの実装状況")
    st.dataframe(
        build_inventory(store),
        width="stretch",
        hide_index=True,
        height=420,
        column_config={
            "data_type": st.column_config.TextColumn("データ型"),
            "label": st.column_config.TextColumn("名称"),
            "scope": st.column_config.TextColumn("スコープ"),
            "implemented": st.column_config.CheckboxColumn("実装済み"),
            "metrics": st.column_config.TextColumn("メトリクス"),
            "methods": st.column_config.TextColumn("取得方法"),
        },
    )
    st.subheader("保存系列")
    st.caption("DuckDB の typed series / sleep sessions / raw page の件数と期間")
    series = build_series_inventory(store)
    series["status"] = series["status"].replace({"ok": "完了", "in_progress": "途中"})
    st.dataframe(
        series,
        width="stretch",
        hide_index=True,
        height=600,
        column_config={
            "metric": st.column_config.TextColumn("メトリクス"),
            "data_type": st.column_config.TextColumn("データ型"),
            "series": st.column_config.TextColumn("系列"),
            "storage": st.column_config.TextColumn("テーブル"),
            "n": st.column_config.NumberColumn("件数"),
            "first_date": st.column_config.DateColumn("開始日"),
            "last_date": st.column_config.DateColumn("最終日"),
            "last_synced": st.column_config.DateColumn("最終同期日"),
            "status": st.column_config.TextColumn("状態"),
            "n_raw_pages": st.column_config.NumberColumn("rawページ数"),
            "raw_first_range": st.column_config.DateColumn("raw範囲開始"),
            "raw_last_range": st.column_config.DateColumn("raw範囲終了"),
        },
    )
