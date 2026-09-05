"""Input parsing and visible schema checks."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = (
    "obs_id", "instrument_id", "source", "timestamp", "currency",
    "instrument_type", "maturity_date", "maturity_years", "start_years",
    "coupon_rate", "payment_frequency", "day_count", "quote_type",
    "quote_value", "quote_unit", "bid", "ask", "liquidity_score",
    "settlement_days",
)

NUMERIC_COLUMNS = (
    "maturity_years", "start_years", "coupon_rate", "payment_frequency",
    "quote_value", "bid", "ask", "liquidity_score", "settlement_days",
)


def load_market_data(path: str | Path) -> pd.DataFrame:
    """Load a CSV, require the public columns, and coerce documented numerics.

    Non-numeric strings in numeric columns become NaN here; the cleaning stage
    records them as data-quality issues instead of silently dropping rows.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"market data not found: {source}")
    try:
        frame = pd.read_csv(source, dtype=str, keep_default_na=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise ValueError(f"market data could not be parsed as CSV: {source}: {exc}") from exc
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    if len(frame) == 0:
        raise ValueError(f"market data contains no observations: {source}")
    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    for name in NUMERIC_COLUMNS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    for name in ("obs_id", "instrument_id", "source", "timestamp", "currency", "instrument_type", "maturity_date", "day_count", "quote_type", "quote_unit"):
        frame[name] = frame[name].astype("string").str.strip()
    return frame


def parse_valuation_date(value: str | date | datetime) -> date:
    """Parse ``YYYY-MM-DD`` (or a date/datetime) into a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"valuation date must be YYYY-MM-DD, got {value!r}") from exc
