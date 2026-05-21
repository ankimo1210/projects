"""Symbol normalization helpers.

Rules:
- 4-digit numeric codes (e.g. "7203") are treated as Japanese stocks and
  suffixed with ".T" (Tokyo) for yfinance.
- Already-suffixed tickers ("7203.T", "AAPL", "BRK-B") pass through unchanged
  except for upper-casing.
"""

from __future__ import annotations

import re

_JP_4DIGIT = re.compile(r"^\d{4}$")


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if _JP_4DIGIT.match(s):
        return f"{s}.T"
    return s


def is_japanese(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    return s.endswith(".T") or s.endswith(".JP")
