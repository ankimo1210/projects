"""Input parsing and visible schema checks; quantitative cleaning is unfinished."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = (
    "obs_id", "instrument_id", "source", "timestamp", "currency",
    "instrument_type", "maturity_date", "maturity_years", "start_years",
    "coupon_rate", "payment_frequency", "day_count", "quote_type",
    "quote_value", "quote_unit", "bid", "ask", "liquidity_score",
    "settlement_days",
)


def load_market_data(path: str | Path) -> pd.DataFrame:
    """Load a CSV, require the public columns, and coerce documented numerics."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"market data not found: {source}")
    frame = pd.read_csv(source)
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    for name in ("maturity_years", "start_years", "coupon_rate", "payment_frequency", "quote_value", "bid", "ask", "liquidity_score", "settlement_days"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    return frame
