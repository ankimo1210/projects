"""Configs load and parse; price_panel aligns WITHOUT silent forward-filling."""

from __future__ import annotations

import pandas as pd
from irp.data import price_panel
from irp.data.base import FetchResult
from irp.data.quality import assess
from irp.utils.config import load_config


def test_configs_load():
    ds = load_config("data_sources")
    assert ds["market"]["primary"] == "stooq"
    uni = load_config("universe")
    assert "SPY" in uni["us_etfs"]["equity"]
    assert "btc" in uni["crypto"]["symbols"]
    tax = load_config("tax_japan")
    assert tax["taxable_account"]["capital_gains_rate"] == 0.20315
    assert tax["nisa_2024"]["tax_rate_inside"] == 0.0  # assumptions in config, not code


def _fr(symbol, dates, vals):
    idx = pd.to_datetime(dates)
    df = pd.DataFrame({"adj_close": vals}, index=idx)
    return FetchResult(symbol, "test", df, assess(df, required_columns=["adj_close"]))


def test_price_panel_union_no_ffill():
    a = _fr("A", ["2024-01-02", "2024-01-03", "2024-01-04"], [1.0, 2.0, 3.0])
    b = _fr("B", ["2024-01-02", "2024-01-04"], [10.0, 12.0])  # missing 01-03
    panel = price_panel({"A": a, "B": b})
    assert list(panel.columns) == ["A", "B"]
    # union of dates; B's 2024-01-03 stays NaN (NOT forward-filled)
    assert pd.isna(panel.loc["2024-01-03", "B"])
    assert panel.loc["2024-01-04", "B"] == 12.0
