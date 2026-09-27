"""Saved-price overview never hides missing correlation observations."""

import math
from dataclasses import replace

import pandas as pd
import pytest
from market_research.research.indicators import IndicatorInput

A, B = "XNYS:IBM", "XNAS:MSFT"


def _inputs(prices=None):
    if prices is None:
        prices = pd.DataFrame(
            {A: [100.0, 110.0, 121.0, 121.0, 133.1], B: [100.0, 100.0, 110.0, 121.0, 121.0]},
            index=pd.date_range("2026-09-21", periods=5, tz="UTC"),
        )
    history = IndicatorInput(prices, "retrospective", "USD", "raw", {A: ("price_jump",)})
    indicators = pd.DataFrame(
        {
            "latest_close": [133.1, 121.0],
            "momentum": [0.1, 0.0],
            "volatility_annualized": [0.5, 0.4],
            "drawdown": [-0.25, -0.05],
            "zscore": [2.5, 0.3],
            "mode": ["retrospective", "retrospective"],
            "currency": ["USD", "USD"],
            "adjustment": ["raw", "raw"],
            "quality_reasons": [("price_jump",), ()],
            "missing_reason": ["", ""],
        },
        index=pd.Index([A, B], name="instrument_id"),
    )
    return history, indicators


def test_overview_ranks_momentum_and_counts_correlation_pairs():
    from market_research.research.overview import market_overview

    source, indicators = _inputs()
    result = market_overview(
        source,
        indicators,
        correlation_window=4,
        drawdown_alert=-0.2,
        zscore_alert=2.0,
    )
    assert result.summary.loc[A, "momentum_rank"] == 1
    assert result.summary.loc[B, "momentum_rank"] == 2
    assert result.pair_counts.loc[A, B] == 4
    assert result.correlations.loc[A, B] == pytest.approx(-1 / math.sqrt(3))
    assert set(result.alerts.loc[result.alerts.instrument_id == A, "kind"]) == {
        "quality",
        "drawdown",
        "zscore",
    }
    assert result.mode == "retrospective"
    assert result.correlation_window == 4


def test_gap_or_constant_returns_cannot_claim_correlation():
    from market_research.research.overview import market_overview

    source, indicators = _inputs()
    gap = source.prices.copy()
    gap.loc[gap.index[2], B] = math.nan
    result = market_overview(
        replace(source, prices=gap),
        indicators,
        correlation_window=4,
        drawdown_alert=-0.2,
        zscore_alert=2.0,
    )
    assert result.pair_counts.loc[A, B] == 2
    assert pd.isna(result.correlations.loc[A, B])
    constant = source.prices.copy()
    constant[B] = 100
    result = market_overview(
        replace(source, prices=constant),
        indicators,
        correlation_window=4,
        drawdown_alert=-0.2,
        zscore_alert=2.0,
    )
    assert result.pair_counts.loc[A, B] == 4
    assert pd.isna(result.correlations.loc[A, B])


def test_incompatible_or_invalid_overview_inputs_fail_closed():
    from market_research.research.overview import market_overview

    source, indicators = _inputs()
    for bad_source, bad_indicators in (
        (replace(source, mode="point_in_time"), indicators),
        (source, indicators.assign(currency="JPY")),
        (source, indicators.drop(B)),
    ):
        with pytest.raises(ValueError):
            market_overview(
                bad_source,
                bad_indicators,
                correlation_window=4,
                drawdown_alert=-0.2,
                zscore_alert=2.0,
            )
    with pytest.raises(ValueError, match="drawdown"):
        market_overview(
            source, indicators, correlation_window=4, drawdown_alert=0.2, zscore_alert=2.0
        )
