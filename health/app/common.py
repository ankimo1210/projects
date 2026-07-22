"""Shared app context: paths and cached resources."""

from pathlib import Path

import streamlit as st
from health.auth import GoogleHealthAuth
from health.store import Store

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@st.cache_resource
def get_store() -> Store:
    return Store(DATA_DIR / "health.duckdb")


def get_auth() -> GoogleHealthAuth:
    return GoogleHealthAuth.from_env(DATA_DIR)
