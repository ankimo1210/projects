"""Virtual risk uses explicit weights and complete retrospective price windows."""

import math
from dataclasses import replace

import pandas as pd
import pytest
from market_research.research.indicators import IndicatorInput


def _source(prices=None):
    if prices is None:
        prices = pd.DataFrame(
            {"XNYS:IBM": [100.0, 110.0, 99.0], "XNAS:MSFT": [100.0, 110.0, 121.0]},
            index=pd.date_range("2026-09-22", periods=3, tz="UTC"),
        )
    return IndicatorInput(
        prices,
        "retrospective",
        "USD",
        "raw",
        {"XNYS:IBM": ("large_close_jump",), "XNAS:MSFT": ()},
    )


def test_two_asset_risk_matches_hand_calculation_and_cash():
    from market_research.research.portfolio import VirtualConstraints, virtual_risk_report

    weights = pd.Series({"XNYS:IBM": 0.5, "XNAS:MSFT": 0.25})
    result = virtual_risk_report(
        _source(),
        weights,
        base_currency="USD",
        lookback=2,
        periods_per_year=4,
        constraints=VirtualConstraints(max_name_weight=0.5, cash_min=0.25),
    )
    expected = math.sqrt(0.5**2 * 0.02) * math.sqrt(4)
    assert result.total_vol_annualized == pytest.approx(expected)
    assert result.component_vol_annualized.sum() == pytest.approx(expected)
    assert result.component_vol_annualized["XNAS:MSFT"] == pytest.approx(0)
    assert result.cash_weight == pytest.approx(0.25)
    assert result.mode == "retrospective"
    assert result.base_currency == "USD"
    assert result.adjustment == "raw"
    assert result.lookback == 2
    assert result.periods_per_year == 4
    assert result.quality_reasons["XNYS:IBM"] == ("large_close_jump",)


def test_virtual_weights_reject_missing_negative_nonfinite_or_excess():
    from market_research.research.portfolio import VirtualConstraints, virtual_risk_report

    source = _source()
    good = pd.Series({"XNYS:IBM": 0.5, "XNAS:MSFT": 0.25})
    for bad in (
        good.drop("XNYS:IBM"),
        pd.Series({"XNYS:IBM": -0.1, "XNAS:MSFT": 0.25}),
        pd.Series({"XNYS:IBM": math.nan, "XNAS:MSFT": 0.25}),
        pd.Series({"XNYS:IBM": 0.5, "XNAS:MSFT": "0.25"}),
        pd.Series({"XNYS:IBM": 0.8, "XNAS:MSFT": 0.8}),
    ):
        with pytest.raises(ValueError):
            virtual_risk_report(
                source,
                bad,
                base_currency="USD",
                lookback=2,
                periods_per_year=252,
                constraints=VirtualConstraints(max_name_weight=0.5),
            )
    with pytest.raises(ValueError, match="currency"):
        virtual_risk_report(source, good, base_currency="JPY", lookback=2, periods_per_year=252)


def test_missing_or_short_price_window_is_not_silently_dropped():
    from market_research.research.portfolio import virtual_risk_report

    source = _source()
    weights = pd.Series({"XNYS:IBM": 0.5, "XNAS:MSFT": 0.5})
    with pytest.raises(ValueError, match="history"):
        virtual_risk_report(source, weights, base_currency="USD", lookback=3, periods_per_year=252)
    missing = source.prices.copy()
    missing.loc[missing.index[1], "XNYS:IBM"] = math.nan
    with pytest.raises(ValueError, match="missing"):
        virtual_risk_report(
            replace(source, prices=missing),
            weights,
            base_currency="USD",
            lookback=2,
            periods_per_year=252,
        )
    nonpositive = source.prices.copy()
    nonpositive.loc[nonpositive.index[0], "XNAS:MSFT"] = 0
    with pytest.raises(ValueError, match="positive"):
        virtual_risk_report(
            replace(source, prices=nonpositive),
            weights,
            base_currency="USD",
            lookback=2,
            periods_per_year=252,
        )


def test_zero_variance_has_zero_contributions():
    from market_research.research.portfolio import virtual_risk_report

    source = _source(
        pd.DataFrame(
            {"XNYS:IBM": [100, 100, 100], "XNAS:MSFT": [50, 50, 50]},
            index=pd.date_range("2026-09-22", periods=3, tz="UTC"),
        )
    )
    result = virtual_risk_report(
        source,
        pd.Series({"XNYS:IBM": 0.5, "XNAS:MSFT": 0.5}),
        base_currency="USD",
        lookback=2,
        periods_per_year=252,
    )
    assert result.total_vol_annualized == 0
    assert result.component_vol_annualized.eq(0).all()
