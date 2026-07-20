"""Inventory page: which metrics have data, ranges, sync status."""
import streamlit as st

from health.inventory import build_inventory

from common import get_store


def inventory_page() -> None:
    st.title("データ棚卸し")
    st.caption("カタログ上の全エンドポイントと、取得済み派生系列の一覧")
    inv = build_inventory(get_store())
    st.dataframe(inv, use_container_width=True, height=600)
