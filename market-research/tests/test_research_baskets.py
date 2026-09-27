"""Basket levels label present-day composition and do not fill missing closes."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.research.dataset import PriceDataset

T1 = datetime(2026, 9, 24, 21, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
T3 = T2 + timedelta(days=1)
IBM = Instrument("XNYS", "IBM", "USD", "America/New_York")
MSFT = Instrument("XNAS", "MSFT", "USD", "America/New_York")


def _bar(instrument: Instrument, decision: datetime, close: float) -> PriceBar:
    end = decision - timedelta(hours=1)
    return PriceBar(
        instrument,
        "yfinance",
        "1d",
        end - timedelta(hours=6),
        end,
        decision,
        decision,
        close,
        "raw",
        decision.isoformat(),
    )


def _dataset(*, missing_middle: bool = False, mode: str = "retrospective") -> PriceDataset:
    ibm = tuple(
        _bar(IBM, time, value) for time, value in zip((T1, T2, T3), (100, 110, 120), strict=True)
    )
    msft_times = (T1, T3) if missing_middle else (T1, T2, T3)
    msft_values = (200, 190) if missing_middle else (200, 210, 190)
    msft = tuple(
        _bar(MSFT, time, value) for time, value in zip(msft_times, msft_values, strict=True)
    )
    gaps = (
        (PriceGap(MSFT, "yfinance", "MSFT", "1d", T2.date(), T2, T2, "raw"),)
        if missing_middle
        else ()
    )
    return PriceDataset(
        T3, ("ibm-snapshot", "msft-snapshot"), "USD", "raw", ibm + msft, gaps, (), mode
    )


def _definition(**changes):
    from market_research.research.baskets import BasketDefinition

    definition = BasketDefinition(
        "two-stock example",
        (IBM.instrument_id, MSFT.instrument_id),
        date(2026, 9, 26),
        "manual synthetic composition",
        "price",
    )
    return replace(definition, **changes)


def test_price_weighted_level_and_weights_match_hand_calculation():
    from market_research.research.baskets import basket_series

    result = basket_series(_dataset(), _definition())
    assert result.mode == "retrospective"
    assert result.definition.composition_as_of == date(2026, 9, 26)
    assert result.snapshot_ids == ("ibm-snapshot", "msft-snapshot")
    assert result.assumptions == ("current_composition_applied_historically", "PAF_assumed_1")
    assert result.values["level"].tolist() == pytest.approx((1, 320 / 300, 310 / 300))
    assert result.values["total_return"].tolist() == pytest.approx((0, 20 / 300, 10 / 300))
    assert result.weights.iloc[0].to_dict() == pytest.approx(
        {"XNYS:IBM": 1 / 3, "XNAS:MSFT": 2 / 3}
    )


def test_missing_constituent_session_stays_missing_without_forward_fill():
    from market_research.research.baskets import basket_series

    result = basket_series(_dataset(missing_middle=True), _definition())
    assert pd.isna(result.values.iloc[1]["level"])
    assert result.weights.iloc[1].isna().all()
    assert result.values.iloc[2]["level"] == pytest.approx(310 / 300)


def test_fixed_shares_market_cap_approximation_is_labeled():
    from market_research.research.baskets import basket_series

    definition = _definition(
        weighting="market_cap",
        factors={"XNYS:IBM": 2, "XNAS:MSFT": 1},
        factors_as_of=date(2026, 9, 26),
    )
    result = basket_series(_dataset(), definition)
    assert result.values["level"].tolist() == pytest.approx((1, 430 / 400, 430 / 400))
    assert result.weights.iloc[0].to_dict() == pytest.approx({"XNYS:IBM": 0.5, "XNAS:MSFT": 0.5})
    assert "fixed_shares" in result.assumptions


def test_pit_or_incomplete_composition_is_rejected():
    from market_research.research.baskets import basket_series

    with pytest.raises(ValueError, match="retrospective"):
        basket_series(_dataset(mode="point_in_time"), _definition())
    with pytest.raises(ValueError, match="composition"):
        basket_series(_dataset(), _definition(composition_as_of=date(2026, 9, 27)))
    with pytest.raises(ValueError, match="factors"):
        basket_series(
            _dataset(),
            _definition(
                weighting="market_cap",
                factors={"XNYS:IBM": 2},
                factors_as_of=date(2026, 9, 26),
            ),
        )


def test_mixed_interval_or_currency_is_not_a_basket():
    from market_research.research.baskets import basket_series

    source = _dataset()
    with pytest.raises(ValueError, match="daily"):
        basket_series(
            replace(source, bars=(*source.bars[:-1], replace(source.bars[-1], interval="1h"))),
            _definition(),
        )
    with pytest.raises(ValueError, match="currency"):
        basket_series(
            replace(
                source,
                bars=(
                    *source.bars[:-1],
                    replace(source.bars[-1], instrument=replace(MSFT, currency="JPY")),
                ),
            ),
            _definition(),
        )
