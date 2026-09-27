"""Screener rules distinguish failed conditions from unavailable evidence."""

import math
from datetime import UTC, date, datetime

import pandas as pd
import pytest
from market_research.contracts import FundamentalObservation
from market_research.research.fundamentals import FundamentalField
from market_research.storage import CacheKey, ResearchStore


def _indicators():
    return pd.DataFrame(
        {
            "latest_close": [100.0, 50.0],
            "momentum": [0.1, -0.1],
            "currency": ["USD", "USD"],
            "missing_reason": ["", ""],
            "quality_reasons": [(), ("large_close_jump",)],
        },
        index=pd.Index(["XNYS:IBM", "XNAS:MSFT"], name="instrument_id"),
    )


def _fundamentals(values=(100.0, 50.0), units=("USD", "USD"), reasons=("", "")):
    return pd.DataFrame(
        {
            "value": values,
            "unit": units,
            "taxonomy": ["us-gaap", "us-gaap"],
            "concept": ["Assets", "Assets"],
            "form": ["10-K", "10-K"],
            "missing_reason": reasons,
        },
        index=pd.MultiIndex.from_tuples(
            [("XNYS:IBM", "assets"), ("XNAS:MSFT", "assets")],
            names=["instrument_id", "field"],
        ),
    )


def test_combined_rules_pass_or_fail_with_explicit_evidence():
    from market_research.research.screener import ThresholdRule, screen_research

    rules = (
        ThresholdRule(
            "large_assets",
            "fundamental",
            "assets",
            "ge",
            75,
            "USD",
            field_definition=FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K"),
        ),
        ThresholdRule("positive_momentum", "technical", "momentum", "gt", 0, "fraction"),
    )
    result = screen_research(_indicators(), _fundamentals(), rules)
    assert result.loc["XNYS:IBM", "status"] == "pass"
    assert result.loc["XNYS:IBM", "failed_rules"] == ()
    assert result.loc["XNAS:MSFT", "status"] == "fail"
    assert result.loc["XNAS:MSFT", "failed_rules"] == (
        "large_assets",
        "positive_momentum",
    )
    assert result.loc["XNAS:MSFT", "quality_reasons"] == ("large_close_jump",)


def test_missing_filing_or_indicator_is_unknown_not_false():
    from market_research.research.screener import ThresholdRule, screen_research

    indicators = _indicators()
    indicators.loc["XNAS:MSFT", "momentum"] = math.nan
    indicators.loc["XNAS:MSFT", "missing_reason"] = "insufficient_history"
    fundamentals = _fundamentals(values=(100.0, math.nan), reasons=("", "not_collected"))
    rules = (
        ThresholdRule(
            "assets",
            "fundamental",
            "assets",
            "gt",
            40,
            "USD",
            field_definition=FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K"),
        ),
        ThresholdRule("trend", "technical", "momentum", "gt", 0, "fraction"),
    )
    result = screen_research(indicators, fundamentals, rules)
    assert result.loc["XNAS:MSFT", "status"] == "unknown"
    assert result.loc["XNAS:MSFT", "failed_rules"] == ()
    assert result.loc["XNAS:MSFT", "unknown_rules"] == (
        "assets:not_collected",
        "trend:insufficient_history",
    )


def test_unit_mismatch_and_missing_asset_do_not_compare_numbers():
    from market_research.research.screener import ThresholdRule, screen_research

    fundamentals = _fundamentals(units=("USD", "shares"))
    rules = (
        ThresholdRule(
            "assets",
            "fundamental",
            "assets",
            "ge",
            75,
            "USD",
            field_definition=FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K"),
        ),
    )
    result = screen_research(_indicators(), fundamentals, rules)
    assert result.loc["XNAS:MSFT", "status"] == "unknown"
    assert result.loc["XNAS:MSFT", "unknown_rules"] == ("assets:unit_mismatch",)

    without_msft = fundamentals.drop(("XNAS:MSFT", "assets"))
    result = screen_research(_indicators(), without_msft, rules)
    assert result.loc["XNAS:MSFT", "unknown_rules"] == ("assets:not_collected",)


def test_bad_rule_or_foreign_fundamental_asset_fails_closed():
    from market_research.research.screener import ThresholdRule, screen_research

    with pytest.raises(ValueError, match="operator"):
        ThresholdRule("bad", "technical", "momentum", "eval", 0, "fraction")
    with pytest.raises(ValueError, match="rules"):
        screen_research(_indicators(), _fundamentals(), ())
    foreign = _fundamentals().rename(index={"XNAS:MSFT": "XNYS:OTHER"}, level=0)
    with pytest.raises(ValueError, match="asset"):
        screen_research(
            _indicators(),
            foreign,
            (
                ThresholdRule(
                    "assets",
                    "fundamental",
                    "assets",
                    "ge",
                    75,
                    "USD",
                    field_definition=FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K"),
                ),
            ),
        )


def test_screener_accepts_real_indicator_and_filing_tables(tmp_path):
    from market_research.research.fundamentals import (
        FundamentalField,
        FundamentalRequest,
        load_fundamental_table,
    )
    from market_research.research.indicators import IndicatorInput, indicator_table
    from market_research.research.screener import ThresholdRule, screen_research

    when = datetime(2026, 9, 25, 12, tzinfo=UTC)
    prices = pd.DataFrame(
        {"XNAS:AAPL": [100, 105, 110]},
        index=pd.date_range("2026-09-23", periods=3, tz="UTC"),
    )
    indicators = indicator_table(
        IndicatorInput(prices, "point_in_time", "USD", "raw"),
        momentum_window=1,
        volatility_window=2,
        periods_per_year=252,
    )
    field = FundamentalField("assets", "us-gaap", "Assets", "USD", "10-K")
    fact = FundamentalObservation(
        320193,
        "us-gaap",
        "Assets",
        "USD",
        None,
        date(2025, 9, 27),
        date(2026, 9, 24),
        when,
        None,
        100,
        "10-K",
        "accession",
    )
    key = CacheKey("sec", "fundamental", field.identity(320193), "annual", "USD", "none")
    with ResearchStore(tmp_path) as store:
        saved = store.save(key, b"fact", observed_at=when, fundamentals=(fact,))
        fundamentals = load_fundamental_table(
            store, (FundamentalRequest("XNAS:AAPL", 320193, field, saved.snapshot_id),), as_of=when
        )
    result = screen_research(
        indicators,
        fundamentals,
        (
            ThresholdRule(
                "assets", "fundamental", "assets", "ge", 80, "USD", field_definition=field
            ),
            ThresholdRule("trend", "technical", "momentum", "gt", 0, "fraction"),
        ),
    )
    assert result.loc["XNAS:AAPL", "status"] == "pass"


def test_same_alias_and_unit_cannot_compare_different_sec_concepts():
    from market_research.research.screener import ThresholdRule, screen_research

    fundamentals = _fundamentals(values=(100.0, 100.0)).rename(index={"assets": "size"}, level=1)
    fundamentals.loc[("XNAS:MSFT", "size"), "concept"] = "Liabilities"
    rule = ThresholdRule(
        "size",
        "fundamental",
        "size",
        "ge",
        75,
        "USD",
        field_definition=FundamentalField("size", "us-gaap", "Assets", "USD", "10-K"),
    )
    result = screen_research(_indicators(), fundamentals, (rule,))
    assert result.loc["XNYS:IBM", "status"] == "pass"
    assert result.loc["XNAS:MSFT", "status"] == "unknown"
    assert result.loc["XNAS:MSFT", "unknown_rules"] == ("size:definition_mismatch",)
