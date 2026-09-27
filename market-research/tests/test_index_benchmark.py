"""Saved official-index comparisons remain retrospective and reject mixed closes."""

from __future__ import annotations

import importlib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.contracts import Instrument, PriceBar, PriceGap
from market_research.prices import PriceExclusion
from market_research.research.baskets import BasketDefinition
from market_research.research.dataset import PriceDataset

TIMES = tuple(datetime(2026, 9, 22, 21, tzinfo=UTC) + timedelta(days=n) for n in range(3))
AS_OF = TIMES[-1] + timedelta(hours=2)
IBM = Instrument("XNYS", "IBM", "USD", "America/New_York")
MSFT = Instrument("XNAS", "MSFT", "USD", "America/New_York")
INDEX = Instrument("XNYS", "OFFICIAL-INDEX", "USD", "America/New_York")


def _bar(instrument: Instrument, at: datetime, close: float) -> PriceBar:
    end = at - timedelta(hours=1)
    return PriceBar(
        instrument,
        "saved-provider",
        "1d",
        end - timedelta(hours=6),
        end,
        at,
        at,
        close,
        "raw",
        at.isoformat(),
    )


def _inputs():
    basket_prices = PriceDataset(
        AS_OF,
        ("ibm-snapshot", "msft-snapshot"),
        "USD",
        "raw",
        tuple(_bar(IBM, at, close) for at, close in zip(TIMES, (100, 110, 120), strict=True))
        + tuple(_bar(MSFT, at, close) for at, close in zip(TIMES, (200, 210, 190), strict=True)),
        (),
        (),
    )
    official_prices = PriceDataset(
        AS_OF,
        ("official-snapshot",),
        "USD",
        "raw",
        tuple(_bar(INDEX, at, close) for at, close in zip(TIMES, (1000, 1050, 1010), strict=True)),
        (),
        (),
    )
    definition = BasketDefinition(
        "two-stock basket",
        (IBM.instrument_id, MSFT.instrument_id),
        date(2026, 9, 24),
        "dated manual composition",
        "price",
    )
    observed_at = {
        "ibm-snapshot": AS_OF,
        "msft-snapshot": AS_OF,
        "official-snapshot": AS_OF,
    }
    return basket_prices, definition, official_prices, observed_at


def _compare(basket_prices, definition, official_prices, observed_at, **changes):
    function = importlib.import_module(
        "market_research.research.index_benchmark"
    ).compare_official_index
    options = {
        "index_name": "Published index",
        "index_instrument_id": INDEX.instrument_id,
        "index_source_ref": "published index series, synthetic fixture",
        "snapshot_observed_at": observed_at,
    }
    options.update(changes)
    return function(basket_prices, definition, official_prices, **options)


def test_dated_basket_is_compared_with_saved_index_on_same_closes():
    basket_prices, definition, official_prices, observed_at = _inputs()

    result = _compare(basket_prices, definition, official_prices, observed_at)

    assert result.mode == "retrospective"
    assert result.basket_definition.composition_as_of == date(2026, 9, 24)
    assert result.basket_definition.factors_as_of == date(2026, 9, 24)
    assert result.index_instrument_id == INDEX.instrument_id
    assert result.index_source_ref == "published index series, synthetic fixture"
    assert result.basket_snapshot_ids == ("ibm-snapshot", "msft-snapshot")
    assert result.index_snapshot_ids == ("official-snapshot",)
    assert result.snapshot_observed_at == tuple(observed_at.items())
    assert result.session_dates == tuple(at.date() for at in TIMES)
    assert result.bar_ends == tuple(at - timedelta(hours=1) for at in TIMES)
    assert "current_composition_applied_historically" in result.assumptions
    assert "not_point_in_time" in result.assumptions
    assert result.values["basket_level"].tolist() == pytest.approx((1, 320 / 300, 310 / 300))
    assert result.values["official_index_level"].tolist() == pytest.approx(
        (1, 1050 / 1000, 1010 / 1000)
    )
    assert result.values.iloc[1]["relative_return"] == pytest.approx(320 / 315 - 1)


def test_missing_composition_date_or_future_snapshot_is_rejected():
    basket_prices, definition, official_prices, observed_at = _inputs()
    with pytest.raises(ValueError, match="composition"):
        _compare(basket_prices, None, official_prices, observed_at)
    with pytest.raises(ValueError, match="composition"):
        _compare(
            basket_prices,
            replace(definition, composition_as_of=date(2026, 9, 25)),
            official_prices,
            observed_at,
        )
    with pytest.raises(ValueError, match="future snapshot"):
        _compare(
            basket_prices,
            definition,
            official_prices,
            {**observed_at, "official-snapshot": AS_OF + timedelta(seconds=1)},
        )
    with pytest.raises(ValueError, match="snapshot"):
        _compare(basket_prices, definition, official_prices, {"ibm-snapshot": AS_OF})


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ("currency", "currency"),
        ("adjustment", "adjustment"),
        ("mode", "retrospective"),
    ),
)
def test_mixed_dataset_contract_is_rejected(change, message):
    basket_prices, definition, official_prices, observed_at = _inputs()
    replacement = {"currency": "JPY", "adjustment": "split", "mode": "point_in_time"}[change]
    with pytest.raises(ValueError, match=message):
        _compare(
            basket_prices,
            definition,
            replace(official_prices, **{change: replacement}),
            observed_at,
        )


def test_matching_unknown_adjustment_is_not_evidence_of_comparability():
    basket_prices, definition, official_prices, observed_at = _inputs()
    basket_unknown = replace(
        basket_prices,
        adjustment="unknown",
        bars=tuple(replace(bar, adjustment="unknown") for bar in basket_prices.bars),
    )
    index_unknown = replace(
        official_prices,
        adjustment="unknown",
        bars=tuple(replace(bar, adjustment="unknown") for bar in official_prices.bars),
    )
    with pytest.raises(ValueError, match="known adjustment"):
        _compare(basket_unknown, definition, index_unknown, observed_at)


def test_missing_constituent_or_index_session_is_rejected():
    basket_prices, definition, official_prices, observed_at = _inputs()
    with pytest.raises(ValueError, match="missing"):
        _compare(
            replace(basket_prices, bars=basket_prices.bars[:4] + basket_prices.bars[5:]),
            definition,
            official_prices,
            observed_at,
        )
    with pytest.raises(ValueError, match="session"):
        _compare(
            basket_prices,
            definition,
            replace(official_prices, bars=official_prices.bars[:2]),
            observed_at,
        )


def test_gap_or_exclusion_is_rejected_instead_of_filled():
    basket_prices, definition, official_prices, observed_at = _inputs()
    gap = PriceGap(
        INDEX, "saved-provider", INDEX.symbol, "1d", TIMES[1].date(), TIMES[1], TIMES[1], "raw"
    )
    with pytest.raises(ValueError, match="gap"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices,
                bars=official_prices.bars[:1] + official_prices.bars[2:],
                gaps=(gap,),
            ),
            observed_at,
        )
    with pytest.raises(ValueError, match="exclusion"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices, exclusions=(PriceExclusion(official_prices.bars[1], "non_final"),)
            ),
            observed_at,
        )


def test_session_close_time_or_daily_interval_must_match():
    basket_prices, definition, official_prices, observed_at = _inputs()
    changed = replace(
        official_prices.bars[1], bar_end=official_prices.bars[1].bar_end - timedelta(hours=1)
    )
    with pytest.raises(ValueError, match="bar end"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices, bars=(official_prices.bars[0], changed, official_prices.bars[2])
            ),
            observed_at,
        )
    changed = replace(
        basket_prices.bars[4], bar_end=basket_prices.bars[4].bar_end - timedelta(hours=1)
    )
    with pytest.raises(ValueError, match="bar end"):
        _compare(
            replace(
                basket_prices, bars=(*basket_prices.bars[:4], changed, *basket_prices.bars[5:])
            ),
            definition,
            official_prices,
            observed_at,
        )
    with pytest.raises(ValueError, match="daily"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices,
                bars=(
                    official_prices.bars[0],
                    replace(official_prices.bars[1], interval="1h"),
                    official_prices.bars[2],
                ),
            ),
            observed_at,
        )


def test_future_bar_provider_mixing_or_unverified_index_identity_is_rejected():
    basket_prices, definition, official_prices, observed_at = _inputs()
    with pytest.raises(ValueError, match="future"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices,
                bars=(
                    official_prices.bars[0],
                    official_prices.bars[1],
                    replace(official_prices.bars[2], observed_at=AS_OF + timedelta(seconds=1)),
                ),
            ),
            observed_at,
        )
    with pytest.raises(ValueError, match="provider"):
        _compare(
            basket_prices,
            definition,
            replace(
                official_prices,
                bars=(
                    official_prices.bars[0],
                    replace(official_prices.bars[1], provider="other"),
                    official_prices.bars[2],
                ),
            ),
            observed_at,
        )
    with pytest.raises(ValueError, match="instrument"):
        _compare(
            basket_prices,
            definition,
            official_prices,
            observed_at,
            index_instrument_id="XNYS:OTHER",
        )
