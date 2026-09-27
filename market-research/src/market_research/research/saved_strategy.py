"""Offline OOS strategy comparison from explicitly observed price snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from market_research.storage import ResearchStore

from .signals import build_pit_signal_table
from .strategy_compare import StrategyComparison, compare_model_strategies


def compare_saved_strategies(
    store: ResearchStore,
    snapshot_ids: Sequence[str],
    *,
    instrument_id: str,
    as_of: datetime,
    train_size: int,
    test_size: int,
    momentum_window: int = 2,
    volatility_window: int = 2,
    embargo: int = 0,
    commission_bps: float = 0.0,
    slippage_bps: float = 0.0,
    lockbox_start: datetime | None = None,
) -> StrategyComparison:
    """Use one explicit snapshot per decision, never a later display history.

    Selected snapshots must be unique, complete daily captures of one instrument.
    Their observed times become decision times; the newest final bar in each capture
    supplies the expected close boundary. Any stale or repeated close is rejected.
    """
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    when = as_of.astimezone(UTC)
    ids = tuple(snapshot_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("snapshot IDs must be nonempty and unique")
    if not isinstance(instrument_id, str) or not instrument_id.strip():
        raise ValueError("instrument_id is required")
    snapshots = tuple(store.get_snapshot(snapshot_id) for snapshot_id in ids)
    snapshots = tuple(sorted(snapshots, key=lambda snapshot: snapshot.observed_at))
    if any(not snapshot.complete or snapshot.key.dataset != "prices" for snapshot in snapshots):
        raise ValueError("complete price snapshots are required")
    if any(snapshot.observed_at > when for snapshot in snapshots):
        raise ValueError("future snapshot cannot supply a strategy decision")
    first = snapshots[0]
    if first.key.identity != instrument_id or first.key.interval != "1d":
        raise ValueError("one daily instrument is required")
    if first.key.adjustment != "raw":
        raise ValueError("known raw prices are required")
    if any(snapshot.key != first.key for snapshot in snapshots):
        raise ValueError("provider, currency, adjustment and instrument must stay fixed")

    decision_times = []
    expected_ends = []
    previous_end = None
    previous_decision = None
    for snapshot in snapshots:
        decision = snapshot.observed_at
        if previous_decision is not None and decision <= previous_decision:
            raise ValueError("snapshot decision times must be unique and increasing")
        view = store.snapshot_price_view(snapshot, decision)
        bars = [bar for bar in view.bars if bar.instrument.instrument_id == instrument_id]
        if not bars:
            raise ValueError("snapshot has no final close")
        latest = max(bars, key=lambda bar: bar.bar_end)
        if latest.quality != "ok" or not latest.is_final:
            raise ValueError("snapshot latest close is not final quality-ok")
        if any(
            item.bar.instrument.instrument_id == instrument_id
            and item.bar.bar_end >= latest.bar_end
            for item in view.exclusions
        ):
            raise ValueError("snapshot contains a newer excluded bar")
        if any(
            gap.instrument.instrument_id == instrument_id
            and gap.session_date >= latest.session_date
            for gap in view.gaps
        ):
            raise ValueError("snapshot contains a newer price gap")
        if previous_end is not None and latest.bar_end <= previous_end:
            raise ValueError("a new final close is required at each decision")
        decision_times.append(decision)
        expected_ends.append(latest.bar_end)
        previous_decision = decision
        previous_end = latest.bar_end
    signals = build_pit_signal_table(
        store,
        instrument_id=instrument_id,
        snapshot_ids=tuple(snapshot.snapshot_id for snapshot in snapshots),
        decision_times=tuple(decision_times),
        expected_bar_ends=tuple(expected_ends),
        currency=first.key.currency,
        adjustment=first.key.adjustment,
        momentum_window=momentum_window,
        volatility_window=volatility_window,
        horizon=1,
    )
    return compare_model_strategies(
        signals,
        train_size=train_size,
        test_size=test_size,
        embargo=embargo,
        lockbox_start=lockbox_start,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )
