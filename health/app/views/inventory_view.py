"""Inventory page: which metrics have data, ranges, sync status."""

import streamlit as st
from common import get_store
from health.inventory import build_inventory, build_series_inventory


def inventory_page() -> None:
    st.title("データ棚卸し")
    store = get_store()
    st.subheader("公開データ型")
    st.caption("Google Health が公開するデータ型と、このアプリの実装状況")
    st.dataframe(build_inventory(store), use_container_width=True, height=420)
    st.subheader("保存系列")
    st.caption("DuckDB の typed series / sleep sessions / raw page の件数と期間")
    st.dataframe(build_series_inventory(store), use_container_width=True, height=600)
