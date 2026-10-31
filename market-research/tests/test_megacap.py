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
    assert company["quote"]["change_pct"] == 0.25
    assert company["fetch_status"] == "ok"
    assert company["notes"] == []


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
    # Zero capex would give 40 + 3 * 30 = 130; the partial quarter is skipped instead.
    assert company["metrics"]["fcf_ttm"] == 120
    assert company["metrics"]["operating_cf_ttm"] == 160
    assert company["cashflow_period_end"] == "2026-03-31"
    assert company["metric_basis"]["fcf_yield"] == "2026-03-31"
    data["cashflow"].loc["Capital Expenditure", pd.Timestamp("2026-03-31")] = float("nan")
    company = tracker().build_company(**data)
    assert company["metrics"]["fcf_ttm"] is None
    assert company["metrics"]["operating_cf_ttm"] is None


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
    assert any("2026-06-30" in message and "一部" in message for message in company["errors"])
    assert company["metrics"]["revenue_ttm"] == 290
    assert company["income_period_end"] == "2026-03-31"
    data["income"].loc["Total Revenue", pd.Timestamp("2026-03-31")] = float("nan")
    company = tracker().build_company(**data)
    assert any("損益TTM" in message for message in company["errors"])
    assert company["metrics"]["revenue_ttm"] is None


def test_failed_refresh_preserves_observation_time_and_marks_old_data(monkeypatch):
    module = tracker()
    old_company = module.build_company(**inputs())
    before = {"schema_version": 1, "companies": [old_company]}
    original = copy.deepcopy(before)

    def unavailable(_symbol, _previous=None):
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


def epoch(text):
    return datetime.fromisoformat(text).timestamp()


NAN = float("nan")


def test_ttm_skips_partial_newer_quarters_and_reports_its_own_end():
    # Yahoo on 2026-10-31: AMZN's two newest income columns carried only Diluted EPS.
    data = inputs()
    dates = pd.to_datetime(
        ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]
    )
    data["income"] = pd.DataFrame(
        [
            [NAN, NAN, 100, 90, 80, 70],
            [NAN, NAN, 20, 18, 16, 14],
            [NAN, NAN, 30, 27, 24, 21],
            [1.9, 5.75, 2.0, 1.8, 1.6, NAN],
        ],
        index=["Total Revenue", "Net Income", "Operating Income", "Diluted EPS"],
        columns=dates,
    )
    company = tracker().build_company(**data)
    metrics = company["metrics"]
    assert metrics["revenue_ttm"] == 340
    assert metrics["net_income_ttm"] == 68
    assert metrics["operating_margin"] == 102 / 340
    assert metrics["ps"] == 1000 / 340
    assert company["income_period_end"] == "2026-03-31"
    assert company["partial_quarters"]["income"] == ["2026-09-30", "2026-06-30"]
    assert company["fetch_status"] == "partial"
    assert any("2026-03-31" in message and "一部" in message for message in company["errors"])


def test_balance_metrics_use_latest_complete_balance_sheet():
    data = inputs()
    data["balance"] = pd.DataFrame(
        [[NAN, 300], [NAN, 100], [450, 400], [NAN, 1000]],
        index=[
            "Cash Cash Equivalents And Short Term Investments",
            "Total Debt",
            "Stockholders Equity",
            "Total Assets",
        ],
        columns=pd.to_datetime(["2026-09-30", "2026-06-30"]),
    )
    company = tracker().build_company(**data)
    assert company["balance_period_end"] == "2026-06-30"
    assert company["metrics"]["net_cash"] == 200
    assert company["metrics"]["equity_ratio"] == 0.4
    assert company["partial_quarters"]["balance"] == ["2026-09-30"]


def test_lease_obligations_are_reported_inside_provider_total_debt():
    data = inputs()
    data["balance"].loc["Capital Lease Obligations"] = [30]
    company = tracker().build_company(**data)
    assert company["metrics"]["debt"] == 100
    assert company["metrics"]["lease_obligations"] == 30
    assert company["metric_basis"]["lease_obligations"] == "2026-06-30"


def test_earnings_schedule_uses_new_york_time_not_the_jst_calendar_date():
    # yfinance's calendar converts with the machine's local time: on a JST machine a
    # 16:05 ET release on Oct 28 comes back as Oct 29.
    data = inputs()
    data["calendar"]["Earnings Date"] = [date(2026, 10, 29)]
    stamp = epoch("2026-10-28T20:05:00+00:00")
    data["info"].update(
        earningsTimestamp=stamp,
        earningsTimestampStart=stamp,
        earningsTimestampEnd=stamp,
        isEarningsDateEstimate=False,
    )
    earnings = tracker().build_company(**data)["earnings"]
    assert earnings["timestamp"] == "2026-10-28T20:05:00+00:00"
    assert earnings["date_et"] == "2026-10-28"
    assert earnings["time_et"] == "16:05"
    assert earnings["session"] == "after_close"
    assert earnings["is_estimate"] is False


@pytest.mark.parametrize(
    ("stamp", "day", "clock", "session"),
    [
        ("2026-10-29T11:30:00+00:00", "2026-10-29", "07:30", "before_open"),
        ("2026-11-03T21:30:00+00:00", "2026-11-03", "16:30", "after_close"),  # after DST ends
        ("2026-10-29T17:15:00+00:00", "2026-10-29", "13:15", "during_market"),
        # Yahoo stores every after-close release at 20:00:00 UTC all year (observed for all
        # seven on 2026-10-31): 16:00 EDT, but 15:00 EST after DST ends. On-the-hour values
        # are session placeholders, so no clock time is claimed.
        ("2026-10-28T20:00:00+00:00", "2026-10-28", None, "after_close"),
        ("2026-11-02T20:00:00+00:00", "2026-11-02", None, "after_close"),
        ("2026-11-17T20:00:00+00:00", "2026-11-17", None, "after_close"),
    ],
)
def test_earnings_session_is_classified_in_eastern_time(stamp, day, clock, session):
    data = inputs()
    data["info"].update(earningsTimestamp=epoch(stamp), isEarningsDateEstimate=False)
    earnings = tracker().build_company(**data)["earnings"]
    assert (earnings["date_et"], earnings["time_et"], earnings["session"]) == (day, clock, session)


def test_estimated_earnings_window_has_no_session_claim():
    data = inputs()
    data["info"].update(
        earningsTimestamp=epoch("2027-01-26T21:00:00+00:00"),
        earningsTimestampStart=epoch("2027-01-26T21:00:00+00:00"),
        earningsTimestampEnd=epoch("2027-01-30T21:00:00+00:00"),
        isEarningsDateEstimate=True,
    )
    earnings = tracker().build_company(**data)["earnings"]
    assert earnings["date_et"] == "2027-01-26"
    assert earnings["end_date_et"] == "2027-01-30"
    assert earnings["window_end"] == "2027-01-30T21:00:00+00:00"
    assert earnings["session"] is None
    assert earnings["is_estimate"] is True


def test_next_estimate_and_last_release_are_kept_apart():
    # MSFT on 2026-10-31: earningsTimestamp still pointed at the Oct 28 release while
    # Start/End already held the next (estimated) date.
    data = inputs()
    data["info"].update(
        earningsTimestamp=epoch("2026-10-28T20:00:00+00:00"),
        earningsTimestampStart=epoch("2027-01-27T20:00:00+00:00"),
        earningsTimestampEnd=epoch("2027-01-27T20:00:00+00:00"),
        isEarningsDateEstimate=True,
    )
    earnings = tracker().build_company(**data)["earnings"]
    assert earnings["date_et"] == "2027-01-27"
    assert earnings["window_end"] is None
    assert earnings["is_estimate"] is True
    assert earnings["session"] is None
    assert earnings["previous"]["date_et"] == "2026-10-28"
    assert earnings["previous"]["session"] == "after_close"
    assert earnings["previous"]["is_estimate"] is False


def test_midnight_utc_estimate_is_kept_as_a_calendar_date():
    data = inputs()
    data["info"].update(
        earningsTimestamp=epoch("2027-01-28T00:00:00+00:00"), isEarningsDateEstimate=True
    )
    earnings = tracker().build_company(**data)["earnings"]
    assert earnings["date_et"] == "2027-01-28"
    assert earnings["time_et"] is None


def test_calendar_dates_alone_are_not_used_as_the_schedule():
    data = inputs()
    data["calendar"]["Earnings Date"] = [date(2026, 10, 29)]
    earnings = tracker().build_company(**data)["earnings"]
    assert earnings["timestamp"] is None
    assert earnings["date_et"] is None
    assert earnings["eps_estimate"] == 2.5


def test_reported_event_before_fetch_is_kept_for_the_browser_to_label():
    data = inputs()
    data["info"].update(earningsTimestamp=epoch("2026-10-01T20:05:00+00:00"))
    assert tracker().build_company(**data)["earnings"]["date_et"] == "2026-10-01"


def test_metric_basis_dates_show_when_eps_and_statements_differ():
    data = inputs()
    data["income"].insert(0, pd.Timestamp("2026-09-30"), NAN)
    data["income"].loc["Diluted EPS"] = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]
    # Provider TTM EPS already includes 2026-09-30 while statements stop at 2026-06-30.
    data["info"].update(trailingEps=5.4, mostRecentQuarter=epoch("2026-09-30T00:00:00+00:00"))
    company = tracker().build_company(**data)
    assert company["basis"]["eps"] == "2026-09-30"
    assert company["basis"]["income_ttm"] == "2026-06-30"
    assert company["metric_basis"]["pe_ttm"] == "2026-09-30"
    assert company["metric_basis"]["ps"] == "2026-06-30"
    assert company["metric_basis"]["fcf_yield"] == "2026-06-30"
    assert company["metric_basis"]["net_cash"] == "2026-06-30"
    assert any("基準期末" in note for note in company["notes"])


def test_eps_basis_prefers_quarterly_evidence_over_provider_quarter_claim():
    data = inputs()
    data["income"].loc["Diluted EPS"] = [1.4, 1.3, 1.2, 1.1, 1.0]
    data["info"].update(trailingEps=5.0, mostRecentQuarter=epoch("2026-09-30T00:00:00+00:00"))
    company = tracker().build_company(**data)
    assert company["basis"]["eps"] == "2026-06-30"  # 1.4 + 1.3 + 1.2 + 1.1
    assert company["basis"]["provider"] == "2026-09-30"


def test_provider_quarter_is_snapped_to_the_statement_quarter_end():
    data = inputs()  # Apple-style fiscal quarter that ends on the last Saturday
    data["info"].update(trailingEps=6.8, mostRecentQuarter=epoch("2026-06-27T00:00:00+00:00"))
    company = tracker().build_company(**data)
    assert company["basis"]["eps"] == "2026-06-30"
    assert company["flags"]["eps_mismatch"] is False  # no quarterly EPS to compare with
    assert company["notes"] == []


def test_forward_pe_is_labelled_with_the_fiscal_year_of_the_estimate():
    data = inputs()
    data["info"]["nextFiscalYearEnd"] = epoch("2026-09-30T00:00:00+00:00")
    estimates = pd.DataFrame({"avg": [2.0, 2.1, 7.5, 8.0]}, index=["0q", "+1q", "0y", "+1y"])
    company = tracker().build_company(**data, estimates=estimates)
    assert company["forward_eps"]["fiscal_year_end"] == "2027-09"
    assert company["forward_eps"]["period"] == "+1y"
    assert company["forward_eps"]["estimates"] == {"0y": 7.5, "+1y": 8.0}
    assert company["forward_eps"]["gap"] == 0
    estimates.loc["+1y", "avg"] = 9.0
    unmatched = tracker().build_company(**data, estimates=estimates)
    assert unmatched["forward_eps"]["fiscal_year_end"] is None


def test_forward_pe_year_is_inferred_when_one_estimate_is_clearly_nearest():
    # GOOGL on 2026-10-31: forwardEps 15.14 vs 0y 19.71 / +1y 14.84 (not yet re-synced).
    data = inputs()
    data["info"].update(forwardEps=15.13866, nextFiscalYearEnd=epoch("2026-12-31T00:00:00+00:00"))
    estimates = pd.DataFrame({"avg": [19.71035, 14.83975]}, index=["0y", "+1y"])
    forward = tracker().build_company(**data, estimates=estimates)["forward_eps"]
    assert forward["fiscal_year_end"] == "2027-12"
    assert forward["period"] == "+1y"
    assert forward["gap"] == pytest.approx(15.13866 / 14.83975 - 1)


def test_net_income_above_operating_income_is_flagged():
    data = inputs()
    assert tracker().build_company(**data)["flags"]["net_income_exceeds_operating"] is False
    data["income"].loc["Net Income"] = [40, 36, 32, 28, 20]
    company = tracker().build_company(**data)
    assert company["flags"]["net_income_exceeds_operating"] is True
    assert any("営業外" in note for note in company["notes"])


def test_unverified_provider_eps_is_noted_and_not_used_for_share_counts():
    # NVDA on 2026-10-31: trailingEps 7.58 while its last four diluted EPS add up to 7.91.
    data = inputs()
    data["income"].loc["Diluted EPS"] = [1.4, 1.3, 1.2, 1.1, 1.0]
    data["info"].update(trailingEps=4.0, mostRecentQuarter=epoch("2026-06-30T00:00:00+00:00"))
    company = tracker().build_company(**data)
    assert company["flags"]["eps_verified"] is False
    assert company["flags"]["eps_mismatch"] is True
    assert company["flags"]["share_count_gap"] is None
    assert any("一致しません" in note and "5.00" in note for note in company["notes"])


def test_share_count_gap_between_market_cap_and_eps_is_noted():
    data = inputs()
    # Same basis quarter: net income TTM 68 / EPS 6.8 = 10 shares = market cap 1000 / price 100.
    data["income"].loc["Diluted EPS"] = [1.9, 1.8, 1.6, 1.5, 1.0]
    data["info"].update(trailingEps=6.8, mostRecentQuarter=epoch("2026-06-30T00:00:00+00:00"))
    assert tracker().build_company(**data)["flags"]["eps_verified"] is True
    assert tracker().build_company(**data)["flags"]["share_count_gap"] == pytest.approx(0)
    data["info"]["marketCap"] = 1120
    company = tracker().build_company(**data)
    assert company["flags"]["share_count_gap"] == pytest.approx(0.12)
    assert any("株数" in note for note in company["notes"])


class _Ticker:
    """Offline stand-in for yfinance.Ticker built from the hand-calculated inputs."""

    def __init__(self, data, fail_info=False):
        self.data, self.fail_info = data, fail_info
        self.quarterly_income_stmt = data["income"]
        self.quarterly_balance_sheet = data["balance"]
        self.quarterly_cashflow = data["cashflow"]
        self.calendar = data["calendar"]
        self.earnings_estimate = pd.DataFrame()

    def get_info(self):
        if self.fail_info:
            raise RuntimeError("rate limited")
        return self.data["info"]

    def history(self, **_kwargs):
        return self.data["history"]


def test_failed_quote_section_reuses_previous_values_with_their_time(monkeypatch):
    import yfinance

    module = tracker()
    old = module.build_company(**inputs())
    monkeypatch.setattr(yfinance, "Ticker", lambda _symbol: _Ticker(inputs(), fail_info=True))
    snapshot = module.collect_snapshot(previous={"schema_version": 1, "companies": [old]})
    saved = next(c for c in snapshot["companies"] if c["symbol"] == "MSFT")
    assert saved["quote"]["price"] == 100
    assert saved["metrics"]["pe_ttm"] == 20
    assert saved["metrics"]["market_cap"] == 1000
    assert saved["section_fetched_at"] == {"基本情報": old["fetched_at"]}
    assert saved["fetched_at"] != old["fetched_at"]
    assert saved["fetch_status"] == "partial"
    assert any("基本情報" in message and "前回" in message for message in saved["errors"])


def test_stale_fallback_keeps_previous_quality_messages(monkeypatch):
    module = tracker()
    data = inputs()
    data["income"].loc["Total Revenue", pd.Timestamp("2026-06-30")] = NAN
    old = module.build_company(**data)

    def unavailable(_symbol, _previous=None):
        raise RuntimeError("down")

    monkeypatch.setattr(module, "_fetch_company", unavailable)
    snapshot = module.collect_snapshot(previous={"schema_version": 1, "companies": [old]})
    saved = next(c for c in snapshot["companies"] if c["symbol"] == "MSFT")
    assert saved["errors"][0].startswith("更新に失敗しました")
    assert all(message in saved["errors"] for message in old["errors"])
    again = module.collect_snapshot(previous=snapshot)
    repeated = next(c for c in again["companies"] if c["symbol"] == "MSFT")
    assert sum(message.startswith("更新に失敗しました") for message in repeated["errors"]) == 1
