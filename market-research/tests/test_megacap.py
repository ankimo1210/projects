"""Hand-calculated financial ratios and honest snapshot freshness."""

from __future__ import annotations

import copy
from datetime import UTC, date, datetime
from importlib import import_module

import pandas as pd
import pytest


def tracker():
    return import_module("market_research.megacap")


def inputs():
    dates = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"])
    return {
        "symbol": "MSFT",
        "info": {
            "currency": "USD",
            "financialCurrency": "USD",
            "regularMarketPrice": 100,
            "regularMarketPreviousClose": 80,
            "regularMarketTime": 1793044800,
            "trailingEps": 5,
            "forwardEps": 8,
            "bookValue": 25,
            "marketCap": 1000,
            "enterpriseToEbitda": 10,
            "ebitda": 100,
            "returnOnEquity": 0.2,
        },
        "history": pd.DataFrame(
            {"Close": [80, 100]}, index=pd.to_datetime(["2026-10-23", "2026-10-26"])
        ),
        "income": pd.DataFrame(
            [[100, 90, 80, 70, 50], [20, 18, 16, 14, 10], [30, 27, 24, 21, 15]],
            index=["Total Revenue", "Net Income", "Operating Income"],
            columns=dates,
        ),
        "balance": pd.DataFrame(
            [[300], [100], [400], [1000]],
            index=[
                "Cash Cash Equivalents And Short Term Investments",
                "Total Debt",
                "Stockholders Equity",
                "Total Assets",
            ],
            columns=dates[:1],
        ),
        "cashflow": pd.DataFrame(
            [[40] * 5, [-10] * 5],
            index=["Operating Cash Flow", "Capital Expenditure"],
            columns=dates,
        ),
        "calendar": {"Earnings Date": [date(2026, 10, 29)], "Earnings Average": 2.5},
        "fetched_at": datetime(2026, 10, 27, 1, tzinfo=UTC),
    }


def test_ratios_use_share_denominators_and_capex_outflow():
    company = tracker().build_company(**inputs())
    metrics = company["metrics"]
    assert metrics["pe_ttm"] == 20
    assert metrics["pe_forward"] == 12.5
    assert metrics["pb"] == 4
    assert metrics["revenue_ttm"] == 340
    assert metrics["net_income_ttm"] == 68
    assert metrics["net_margin"] == 0.2
    assert metrics["operating_cf_ttm"] == 160
    assert metrics["capex_ttm"] == 40
    assert metrics["fcf_ttm"] == 120
    assert metrics["fcf_yield"] == 0.12
    assert metrics["net_cash"] == 200
    assert metrics["equity_ratio"] == 0.4
    assert metrics["revenue_growth_yoy"] == 1
    assert company["income_period_end"] == "2026-06-30"
    assert company["earnings"]["dates"] == ["2026-10-29"]
    assert company["quote"]["change_pct"] == 0.25


@pytest.mark.parametrize("denominator", [0, -2, float("nan"), None])
def test_unusable_eps_and_book_value_do_not_create_multiples(denominator):
    data = inputs()
    data["info"].update(trailingEps=denominator, forwardEps=denominator, bookValue=denominator)
    company = tracker().build_company(**data)
    assert company["metrics"]["pe_ttm"] is None
    assert company["metrics"]["pe_forward"] is None
    assert company["metrics"]["pb"] is None


def test_nonconsecutive_quarters_do_not_masquerade_as_ttm():
    data = inputs()
    data["income"] = data["income"].drop(columns=pd.Timestamp("2026-03-31"))
    company = tracker().build_company(**data)
    assert company["metrics"]["revenue_ttm"] is None
    assert company["metrics"]["ps"] is None
    assert company["metrics"]["fcf_ttm"] == 120


def test_missing_cashflow_component_is_not_replaced_with_zero():
    data = inputs()
    data["cashflow"].loc["Capital Expenditure", pd.Timestamp("2026-06-30")] = float("nan")
    company = tracker().build_company(**data)
    assert company["metrics"]["fcf_ttm"] is None
    assert company["metrics"]["operating_cf_ttm"] == 160


def test_currency_mismatch_does_not_produce_cross_currency_ratios():
    data = inputs()
    data["info"]["financialCurrency"] = "EUR"
    company = tracker().build_company(**data)
    assert company["metrics"]["ps"] is None
    assert company["metrics"]["fcf_yield"] is None
    assert company["metrics"]["net_cash"] == 200
    assert company["financial_currency"] == "EUR"


def test_missing_revenue_is_visibly_classified_as_partial_data():
    data = inputs()
    data["income"].loc["Total Revenue", pd.Timestamp("2026-06-30")] = float("nan")
    company = tracker().build_company(**data)
    assert company["fetch_status"] == "partial"
    assert any("損益TTM" in message for message in company["errors"])
    assert company["metrics"]["revenue_ttm"] is None


def test_failed_refresh_preserves_observation_time_and_marks_old_data(monkeypatch):
    module = tracker()
    old_company = module.build_company(**inputs())
    before = {"schema_version": 1, "companies": [old_company]}
    original = copy.deepcopy(before)

    def unavailable(_symbol):
        raise RuntimeError("private error content must not appear")

    monkeypatch.setattr(module, "_fetch_company", unavailable)
    snapshot = module.collect_snapshot(previous=before)
    saved = next(c for c in snapshot["companies"] if c["symbol"] == "MSFT")
    assert saved["fetched_at"] == old_company["fetched_at"]
    assert saved["quote"]["price"] == 100
    assert saved["fetch_status"] == "stale"
    assert "private error" not in str(snapshot)
    assert before == original
    assert len(snapshot["companies"]) == 7


def test_semantically_empty_provider_response_preserves_old_snapshot(monkeypatch):
    import yfinance

    module = tracker()
    old = module.build_company(**inputs())

    class EmptyTicker:
        def __init__(self):
            self.quarterly_income_stmt = pd.DataFrame()
            self.quarterly_balance_sheet = pd.DataFrame()
            self.quarterly_cashflow = pd.DataFrame()
            self.calendar = {}

        def get_info(self):
            return {"trailingPegRatio": None}

        def history(self, **_kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yfinance, "Ticker", lambda _symbol: EmptyTicker())
    snapshot = module.collect_snapshot(previous={"schema_version": 1, "companies": [old]})
    saved = next(c for c in snapshot["companies"] if c["symbol"] == "MSFT")
    assert saved["quote"]["price"] == 100
    assert saved["fetched_at"] == old["fetched_at"]
    assert saved["fetch_status"] == "stale"


def test_snapshot_roundtrip_and_no_nonfinite_json(tmp_path):
    module = tracker()
    data = inputs()
    data["info"]["marketCap"] = float("inf")
    snapshot = {
        "schema_version": 1,
        "companies": [module.build_company(**data)],
        "attempted_at": "2026-10-27T01:00:00+00:00",
    }
    path = tmp_path / "snapshot.json"
    module.save_snapshot(snapshot, path)
    assert module.load_snapshot(path) == snapshot
    assert "Infinity" not in path.read_text()


def test_past_calendar_is_not_displayed_as_an_upcoming_earnings_date():
    data = inputs()
    data["calendar"]["Earnings Date"] = [date(2026, 10, 1)]
    assert tracker().build_company(**data)["earnings"]["dates"] == []
