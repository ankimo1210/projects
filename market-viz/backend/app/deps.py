"""FastAPI dependency: shared DuckDB client."""

from __future__ import annotations

from functools import lru_cache

from market_viz import config as mv_config
from market_viz.storage.duckdb_client import DuckDBClient


@lru_cache(maxsize=1)
def _load_settings() -> dict:
    return mv_config.load_settings()


@lru_cache(maxsize=1)
def get_db() -> DuckDBClient:
    settings = _load_settings()
    db_path = mv_config.PROJECT_ROOT / settings["data"]["db_path"]
    db = DuckDBClient(db_path)
    db.connect()
    return db


@lru_cache(maxsize=1)
def load_instruments() -> list[dict]:
    return mv_config.load_instruments()


def get_ticker_meta() -> dict[str, dict]:
    return {
        i["ticker"]: {
            "name": i.get("name", i["ticker"]),
            "asset_class": i.get("asset_class", ""),
            "market": i.get("market", ""),
        }
        for i in load_instruments()
    }
