"""Input parsing and strict schema checks.

``load_market_data`` keeps the supplied starter behaviour (and the visible test
contract) exactly.  ``load_market_data_with_audit`` adds the information the
cleaning pipeline needs: which numeric cells were originally blank and which
ones were present but *unparseable*.  The distinction matters because a blank
quote can be reconstructed from the bid/ask mid whereas a corrupt one cannot be
trusted at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

__all__ = [
    "REQUIRED_COLUMNS",
    "NUMERIC_COLUMNS",
    "MarketDataError",
    "LoadedMarketData",
    "load_market_data",
    "load_market_data_with_audit",
]


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


class MarketDataError(ValueError):
    """Raised for unrecoverable problems with a market-data file."""


@dataclass(frozen=True)
class LoadedMarketData:
    """A loaded frame together with a per-cell parse audit."""

    frame: pd.DataFrame
    #: True where the source cell was non-empty but could not be parsed as a number.
    unparseable: pd.DataFrame
    #: True where the source cell was empty / missing.
    blank: pd.DataFrame
    path: Path


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
    for name in NUMERIC_COLUMNS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    return frame


def load_market_data_with_audit(path: str | Path) -> LoadedMarketData:
    """``load_market_data`` plus a record of blank and unparseable numeric cells."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"market data not found: {source}")
    try:
        raw = pd.read_csv(source, dtype=str, keep_default_na=False, na_values=[""])
    except pd.errors.EmptyDataError as exc:  # pragma: no cover - trivial
        raise MarketDataError(f"market data file is empty: {source}") from exc
    except pd.errors.ParserError as exc:
        raise MarketDataError(f"market data file is not valid CSV: {source}: {exc}") from exc

    missing = [name for name in REQUIRED_COLUMNS if name not in raw.columns]
    if missing:
        raise MarketDataError(f"missing required columns: {', '.join(missing)}")
    if raw.empty:
        raise MarketDataError(f"market data file contains no observation rows: {source}")

    raw = raw.loc[:, REQUIRED_COLUMNS].copy()
    frame = raw.copy()
    blank = pd.DataFrame(False, index=raw.index, columns=list(NUMERIC_COLUMNS))
    unparseable = pd.DataFrame(False, index=raw.index, columns=list(NUMERIC_COLUMNS))
    for name in NUMERIC_COLUMNS:
        original = raw[name]
        was_blank = original.isna() | original.astype(str).str.strip().eq("")
        coerced = pd.to_numeric(original, errors="coerce")
        blank[name] = was_blank.to_numpy()
        unparseable[name] = (coerced.isna() & ~was_blank).to_numpy()
        frame[name] = coerced
    for name in ("obs_id", "instrument_id", "source", "instrument_type",
                 "quote_type", "quote_unit", "currency", "day_count",
                 "timestamp", "maturity_date"):
        frame[name] = frame[name].astype("string").fillna("").str.strip()
    return LoadedMarketData(frame=frame, unparseable=unparseable, blank=blank, path=source)
