"""Causal price signals and explicitly timed future labels."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from market_research.storage import ResearchStore

from .history import build_pit_close_frame


@dataclass(frozen=True, slots=True)
class SignalDataset:
    table: pd.DataFrame
    instrument_id: str
    snapshot_ids: tuple[str, ...]
    currency: str
    adjustment: str
    horizon: int
    mode: str = "point_in_time"


def _positive_int(value: int, name: str, minimum: int = 1) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")


def build_pit_signal_table(
    store: ResearchStore,
    *,
    instrument_id: str,
    snapshot_ids: Sequence[str],
    decision_times: Sequence[datetime],
    expected_bar_ends: Sequence[datetime],
    currency: str,
    adjustment: str,
    momentum_window: int,
    volatility_window: int,
    horizon: int,
) -> SignalDataset:
    """Build features only from observed closes; never accept display history."""
    _positive_int(momentum_window, "momentum_window")
    _positive_int(volatility_window, "volatility_window", 2)
    _positive_int(horizon, "horizon")
    ids = tuple(snapshot_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("snapshot_ids must be nonempty and unique")
    if not instrument_id:
        raise ValueError("instrument_id is required")
    frame = build_pit_close_frame(
        store,
        {instrument_id: ids},
        decision_times,
        currency=currency,
        adjustment=adjustment,
        expected_bar_ends={instrument_id: expected_bar_ends},
    )
    if len(frame) <= horizon:
        raise ValueError("more decisions than the label horizon are required")
    closes = frame[instrument_id].astype(float)
    returns = closes.pct_change(fill_method=None)
    table = pd.DataFrame(index=frame.index)
    table["close"] = closes
    table["momentum"] = closes.pct_change(periods=momentum_window, fill_method=None)
    table["volatility"] = returns.rolling(volatility_window, min_periods=volatility_window).std(
        ddof=1
    )
    table["label"] = closes.shift(-horizon).div(closes).sub(1.0)
    availability = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")
    availability.iloc[:-horizon] = frame.index[horizon:]
    table["label_available_at"] = availability
    return SignalDataset(table, instrument_id, ids, currency.strip().upper(), adjustment, horizon)
