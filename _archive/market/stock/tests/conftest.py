"""Shared fixtures for stockkit tests.

All tests run without network access. The DuckDB cache is redirected to a
per-test temporary directory by overriding the module-level constant
``cache._DEFAULT_DIR`` (it is resolved at import time, so the
``STOCKKIT_DATA_DIR`` env var alone would not take effect).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from stockkit.data import cache as cache_mod


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    """Redirect the DuckDB cache to a temporary directory for one test."""
    monkeypatch.setattr(cache_mod, "_DEFAULT_DIR", tmp_path)
    return cache_mod


@pytest.fixture
def ohlcv():
    """Deterministic 10-row OHLCV frame with a daily DatetimeIndex."""
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    close = pd.Series(
        [100, 102, 101, 105, 107, 106, 110, 108, 112, 115], index=idx, dtype=float
    )
    df = pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "adj_close": close,
            "volume": pd.Series(range(1000, 1000 + 10 * 10, 10), index=idx, dtype=float),
        }
    )
    return df


@pytest.fixture
def price_panel_2():
    """Two-symbol wide adj_close panel with known returns (A: +10%, B: +5%)."""
    idx = pd.date_range("2020-01-01", periods=2, freq="D")
    return pd.DataFrame({"A": [100.0, 110.0], "B": [200.0, 210.0]}, index=idx)
