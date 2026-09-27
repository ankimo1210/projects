"""Normalize raw price DataFrames to the prices table schema."""

from __future__ import annotations

import pandas as pd

PRICE_COLUMNS = [
    "timestamp",
    "ticker",
    "asset_class",
    "market",
    "frequency",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "updated_at",
]


def normalize_prices(df: pd.DataFrame, asset_class: str = "", market: str = "") -> pd.DataFrame:
    """Ensure df matches the prices table schema."""
    out = df.copy()
    if "asset_class" not in out.columns:
        out["asset_class"] = asset_class
    if "market" not in out.columns:
        out["market"] = market
    if "updated_at" not in out.columns:
        out["updated_at"] = pd.Timestamp.now()
    if "frequency" not in out.columns:
        out["frequency"] = "1d"

    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out.dropna(subset=["timestamp", "close"])
    out = out.sort_values(["ticker", "timestamp"]).reset_index(drop=True)

    # keep only schema columns that exist
    keep = [c for c in PRICE_COLUMNS if c in out.columns]
    out = out[keep]
    return out
