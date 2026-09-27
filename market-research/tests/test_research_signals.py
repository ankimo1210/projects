"""Causal signal features and labels from observed price snapshots."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from market_research.contracts import Instrument, PriceBar
from market_research.storage import CacheKey, ResearchStore

IBM = Instrument("XNYS", "IBM", "USD", "America/New_York")
KEY = CacheKey("yfinance", "prices", IBM.instrument_id, "1d", "USD", "raw")
START = datetime(2026, 9, 1, 21, tzinfo=UTC)


def _fixture(store, closes):
    decisions = tuple(START + timedelta(days=i) for i in range(len(closes)))
    ends = tuple(when - timedelta(hours=1) for when in decisions)
    ids = []
    for i, (when, end, close) in enumerate(zip(decisions, ends, closes, strict=True)):
        bar = PriceBar(
            IBM,
            "yfinance",
            "1d",
            end - timedelta(hours=6),
            end,
            when,
            when,
            close,
            "raw",
            f"v{i}",
        )
        saved = store.save(KEY, f"raw-{i}-{close}".encode(), observed_at=when, prices=(bar,))
        ids.append(saved.snapshot_id)
    return tuple(ids), decisions, ends


def _signals(store, closes, **kwargs):
    from market_research.research.signals import build_pit_signal_table

    ids, decisions, ends = _fixture(store, closes)
    return build_pit_signal_table(
        store,
        instrument_id=IBM.instrument_id,
        snapshot_ids=ids,
        decision_times=decisions,
        expected_bar_ends=ends,
        currency="USD",
        adjustment="raw",
        momentum_window=2,
        volatility_window=2,
        horizon=2,
        **kwargs,
    )


def test_labels_are_future_returns_with_explicit_availability(tmp_path):
    with ResearchStore(tmp_path) as store:
        result = _signals(store, (100, 105, 110, 100, 120, 130))
    table = result.table
    assert result.mode == "point_in_time"
    assert result.instrument_id == IBM.instrument_id
    assert table.loc[START + timedelta(days=2), "momentum"] == pytest.approx(0.1)
    assert table.loc[START, "label"] == pytest.approx(0.1)
    assert table.loc[START, "label_available_at"] == START + timedelta(days=2)
    assert pd.isna(table.iloc[-1]["label"])
    assert pd.isna(table.iloc[-1]["label_available_at"])


def test_changing_future_close_cannot_change_past_features(tmp_path):
    with ResearchStore(tmp_path / "original") as store:
        original = _signals(store, (100, 105, 110, 100, 120, 130))
    with ResearchStore(tmp_path / "changed") as store:
        changed = _signals(store, (100, 105, 110, 100, 500, 130))
    pd.testing.assert_frame_equal(
        original.table.iloc[:4][["momentum", "volatility"]],
        changed.table.iloc[:4][["momentum", "volatility"]],
    )
    assert original.table.iloc[2]["label"] != changed.table.iloc[2]["label"]


def test_signal_builder_rejects_unverified_prices_or_invalid_windows(tmp_path):
    from market_research.research.signals import build_pit_signal_table

    with ResearchStore(tmp_path) as store:
        ids, decisions, ends = _fixture(store, (100, 102, 103))
        arguments = dict(
            instrument_id=IBM.instrument_id,
            snapshot_ids=ids,
            decision_times=decisions,
            expected_bar_ends=ends,
            currency="USD",
            adjustment="raw",
            momentum_window=2,
            volatility_window=2,
            horizon=1,
        )
        with pytest.raises(ValueError, match="horizon"):
            build_pit_signal_table(store, **(arguments | {"horizon": 0}))
        with pytest.raises(ValueError, match="volatility"):
            build_pit_signal_table(store, **(arguments | {"volatility_window": 1}))
        with pytest.raises(ValueError, match="currency"):
            build_pit_signal_table(store, **(arguments | {"currency": "JPY"}))
        with pytest.raises(ValueError, match="expected close"):
            build_pit_signal_table(
                store, **(arguments | {"expected_bar_ends": (ends[0], ends[0], ends[2])})
            )


def test_signal_builder_rejects_missing_decision_close_instead_of_filling(tmp_path):
    from market_research.research.signals import build_pit_signal_table

    with ResearchStore(tmp_path) as store:
        ids, decisions, ends = _fixture(store, (100, 102, 104, 106))
        with pytest.raises(ValueError, match="new final close"):
            build_pit_signal_table(
                store,
                instrument_id=IBM.instrument_id,
                snapshot_ids=ids[:-1],
                decision_times=decisions,
                expected_bar_ends=ends,
                currency="USD",
                adjustment="raw",
                momentum_window=1,
                volatility_window=2,
                horizon=1,
            )


def test_signal_builder_rejects_naive_or_duplicate_decisions(tmp_path):
    from market_research.research.signals import build_pit_signal_table

    with ResearchStore(tmp_path) as store:
        ids, decisions, ends = _fixture(store, (100, 102, 104))
        arguments = dict(
            instrument_id=IBM.instrument_id,
            snapshot_ids=ids,
            expected_bar_ends=ends,
            currency="USD",
            adjustment="raw",
            momentum_window=1,
            volatility_window=2,
            horizon=1,
        )
        with pytest.raises(ValueError, match="timezone-aware"):
            build_pit_signal_table(
                store,
                decision_times=(decisions[0].replace(tzinfo=None), *decisions[1:]),
                **arguments,
            )
        with pytest.raises(ValueError, match="unique and ordered"):
            build_pit_signal_table(
                store,
                decision_times=(decisions[0], decisions[0], decisions[2]),
                **arguments,
            )
