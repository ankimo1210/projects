"""The Mag7 example uses observed prefixes, never the full price history."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.storage import CacheKey, ResearchStore

SYMBOLS = ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA")
START = datetime(2026, 9, 1, 21, tzinfo=UTC)


def _saved_prices(store, *, change_last=False):
    decisions = tuple(START + timedelta(days=i) for i in range(5))
    ends = tuple(when - timedelta(hours=1) for when in decisions)
    snapshots = {}
    expected = {}
    for rank, symbol in enumerate(SYMBOLS, 1):
        instrument = Instrument("XNAS", symbol, "USD", "America/New_York")
        key = CacheKey("yfinance", "prices", instrument.instrument_id, "1d", "USD", "raw")
        ids = []
        for day, (decision, end) in enumerate(zip(decisions, ends, strict=True)):
            close = 100.0 * (1.0 + rank * 0.01) ** day
            if change_last and day == 4 and symbol == "AAPL":
                close *= 1.02
            bar = PriceBar(
                instrument,
                "yfinance",
                "1d",
                end - timedelta(hours=6),
                end,
                decision,
                decision,
                close,
                "raw",
                f"v{day}",
            )
            saved = store.save(
                key,
                f"{symbol}-{day}-{close}".encode(),
                observed_at=decision,
                prices=(bar,),
            )
            ids.append(saved.snapshot_id)
        snapshots[instrument.instrument_id] = tuple(ids)
        expected[instrument.instrument_id] = ends
    return snapshots, decisions, expected


def test_fixed_mag7_example_matches_hand_rank_cost_and_lag(tmp_path):
    from market_research.examples.autostock import run_mag7_example

    with ResearchStore(tmp_path) as store:
        snapshots, decisions, expected = _saved_prices(store)
        result = run_mag7_example(
            store,
            snapshots,
            decisions,
            expected,
            lookback=2,
            cost_bps=5.0,
            currency="USD",
            adjustment="raw",
        )
    weights = result.target_weights
    assert (weights.iloc[:2] == 0.0).all().all()
    assert weights.loc[decisions[2], "XNAS:TSLA"] == pytest.approx(7 / 28)
    assert weights.loc[decisions[2], "XNAS:AAPL"] == pytest.approx(1 / 28)
    assert weights.loc[decisions[2]].sum() == pytest.approx(1.0)
    assert result.backtest.held_weights.loc[decisions[2]].sum() == 0.0
    assert result.backtest.held_weights.loc[decisions[3]].sum() == pytest.approx(1.0)
    assert result.backtest.costs.loc[decisions[3]] == pytest.approx(0.0005)
    assert result.backtest.net_returns.loc[decisions[3]] == pytest.approx(0.0495)
    assert result.mode == "point_in_time"


def test_future_price_change_does_not_change_earlier_mag7_weights(tmp_path):
    from market_research.examples.autostock import run_mag7_example

    with ResearchStore(tmp_path / "first") as store:
        first = run_mag7_example(
            store,
            *_saved_prices(store),
            lookback=2,
            currency="USD",
            adjustment="raw",
        )
    with ResearchStore(tmp_path / "changed") as store:
        changed = run_mag7_example(
            store,
            *_saved_prices(store, change_last=True),
            lookback=2,
            currency="USD",
            adjustment="raw",
        )
    pd.testing.assert_frame_equal(first.target_weights.iloc[:4], changed.target_weights.iloc[:4])


def test_lockbox_decisions_and_returns_are_excluded(tmp_path):
    from market_research.examples.autostock import run_mag7_example

    with ResearchStore(tmp_path) as store:
        snapshots, decisions, expected = _saved_prices(store)
        result = run_mag7_example(
            store,
            snapshots,
            decisions,
            expected,
            lookback=2,
            currency="USD",
            adjustment="raw",
            lockbox_start=decisions[4],
        )
    assert result.target_weights.index.max() < decisions[4]
    assert result.backtest.net_returns.index.max() < decisions[4]


def test_future_interval_snapshot_cannot_change_pre_lockbox_example(tmp_path):
    from market_research.examples.autostock import run_mag7_example

    with ResearchStore(tmp_path) as store:
        snapshots, decisions, expected = _saved_prices(store)
        settings = dict(
            lookback=2,
            currency="USD",
            adjustment="raw",
            lockbox_start=decisions[4],
        )
        baseline = run_mag7_example(store, snapshots, decisions, expected, **settings)
        instrument = Instrument("XNAS", "AAPL", "USD", "America/New_York")
        end = expected[instrument.instrument_id][4]
        future = PriceBar(
            instrument,
            "yfinance",
            "1h",
            end - timedelta(hours=1),
            end,
            decisions[4],
            decisions[4],
            999.0,
            "raw",
            "future-hour",
        )
        saved = store.save(
            CacheKey("yfinance", "prices", instrument.instrument_id, "1h", "USD", "raw"),
            b"future-hour",
            observed_at=decisions[4],
            prices=(future,),
        )
        changed = dict(snapshots)
        changed[instrument.instrument_id] = (
            *snapshots[instrument.instrument_id],
            saved.snapshot_id,
        )
        result = run_mag7_example(store, changed, decisions, expected, **settings)

    pd.testing.assert_frame_equal(result.target_weights, baseline.target_weights)
    pd.testing.assert_series_equal(result.backtest.net_returns, baseline.backtest.net_returns)
    assert saved.snapshot_id not in result.eligible_snapshot_ids
