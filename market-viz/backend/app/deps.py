"""FastAPI dependency: shared DuckDB client."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from market_viz.storage.duckdb_client import DuckDBClient

# project root = 2 levels up from this file (backend/app/deps.py)
ROOT = Path(__file__).parent.parent.parent


@lru_cache(maxsize=1)
def _load_settings() -> dict:
    with open(ROOT / "src/config/settings.yaml") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_db() -> DuckDBClient:
    settings = _load_settings()
    db_path = ROOT / settings["data"]["db_path"]
    db = DuckDBClient(db_path)
    db.connect()
    return db


@lru_cache(maxsize=1)
def load_instruments() -> list[dict]:
    with open(ROOT / "src/config/instruments.yaml") as f:
        cfg = yaml.safe_load(f)
    result: list[dict] = []
    for group in cfg.get("instruments", {}).values():
        result.extend(group)
    return result


def get_ticker_meta() -> dict[str, dict]:
    return {
        i["ticker"]: {
            "name": i.get("name", i["ticker"]),
            "asset_class": i.get("asset_class", ""),
            "market": i.get("market", ""),
        }
        for i in load_instruments()
    }
