import numpy as np
import pandas as pd
from stockkit.analysis import fundamental as fnd


def _financials_desc():
    # yfinance-style: columns are period-end timestamps in DESCENDING order
    return pd.DataFrame(
        {
            pd.Timestamp("2023-12-31"): [300.0],
            pd.Timestamp("2022-12-31"): [200.0],
            pd.Timestamp("2021-12-31"): [100.0],
        },
        index=["Total Revenue"],
    )


def test_yoy_growth_sorts_ascending_then_pct_change():
    out = fnd.yoy_growth(_financials_desc(), "Total Revenue")
    # 100 -> 200 (+100%), 200 -> 300 (+50%)
    np.testing.assert_allclose(out.dropna().to_numpy(), [1.0, 0.5])


def test_yoy_growth_missing_or_empty_returns_empty():
    assert fnd.yoy_growth(pd.DataFrame(), "Total Revenue").empty
    assert fnd.yoy_growth(_financials_desc(), "No Such Row").empty


def test_snapshot_maps_info_fields_with_fallback(monkeypatch):
    info = {"shortName": "Acme", "trailingPE": 12.0, "returnOnEquity": 0.2}
    monkeypatch.setattr(fnd, "get_info", lambda s: info)
    snap = fnd.snapshot("AAA")
    assert snap["symbol"] == "AAA"
    assert snap["name"] == "Acme"  # falls back to shortName when longName absent
    assert snap["pe"] == 12.0
    assert snap["roe"] == 0.2
    assert snap["pb"] is None  # missing field -> None


def test_revenue_growth_history_uses_income_statement(monkeypatch):
    monkeypatch.setattr(fnd, "get_financials", lambda s: {"income": _financials_desc()})
    out = fnd.revenue_growth_history("AAA")
    np.testing.assert_allclose(out.dropna().to_numpy(), [1.0, 0.5])
