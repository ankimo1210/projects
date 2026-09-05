"""Input loading and strict public-schema validation."""

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


def validate_schema(frame: pd.DataFrame) -> list[str]:
    """Return actionable schema/type issues without changing the input frame."""
    issues: list[str] = []
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        return [f"missing required columns: {', '.join(missing)}"]
    if frame.empty:
        issues.append("market data contains no observations")
    if frame["obs_id"].isna().any() or (frame["obs_id"].astype(str).str.strip() == "").any():
        issues.append("obs_id contains null or empty values")
    if frame["instrument_id"].isna().any() or (frame["instrument_id"].astype(str).str.strip() == "").any():
        issues.append("instrument_id contains null or empty values")
    parsed_timestamp = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    parsed_maturity = pd.to_datetime(frame["maturity_date"], errors="coerce")
    if parsed_timestamp.isna().any():
        issues.append("timestamp contains unparseable values")
    if parsed_maturity.isna().any():
        issues.append("maturity_date contains unparseable values")
    for col in ("maturity_years", "start_years", "payment_frequency", "liquidity_score", "settlement_days"):
        if frame[col].isna().any():
            issues.append(f"{col} contains non-numeric or missing values")
    return issues
