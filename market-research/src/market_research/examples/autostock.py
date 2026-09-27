"""Causal Mag7 momentum-rank example adapted from autostock."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise

import numpy as np
import pandas as pd

from market_research.backtest import BacktestResult, run_backtest, run_prefix_strategy
from market_research.research.history import build_pit_close_frame
from market_research.storage import ResearchStore

MAG7 = (
    "XNAS:AAPL",
    "XNAS:MSFT",
    "XNAS:GOOGL",
    "XNAS:AMZN",
    "XNAS:NVDA",
    "XNAS:META",
    "XNAS:TSLA",
)
MAX_NAME = 0.5
MAX_GROSS = 1.0


@dataclass(frozen=True, slots=True)
class Mag7ExampleRun:
    target_weights: pd.DataFrame
    backtest: BacktestResult
    eligible_snapshot_ids: tuple[str, ...]
    lookback: int
    cost_bps: float
    adjustment: str
    as_of: datetime
    mode: str = "point_in_time"


def _momentum_rank(prefix: pd.DataFrame, lookback: int) -> pd.Series:
    if len(prefix) <= lookback:
        return pd.Series(0.0, index=prefix.columns)
    latest = prefix.iloc[-1].astype(float)
    start = prefix.iloc[-lookback - 1].astype(float)
    if not np.isfinite(latest.to_numpy()).all() or not np.isfinite(start.to_numpy()).all():
        raise ValueError("Mag7 price prefix is incomplete")
    momentum = latest.div(start).sub(1.0)
    ranks = momentum.rank(method="average")
    weights = ranks.div(ranks.sum()).clip(upper=MAX_NAME)
    gross = weights.abs().sum()
    if gross > MAX_GROSS:
        weights = weights * (MAX_GROSS / gross)
    return weights


def run_mag7_example(
    store: ResearchStore,
    snapshot_ids_by_instrument: Mapping[str, Sequence[str]],
    decision_times: Sequence[datetime],
    expected_bar_ends: Mapping[str, Sequence[datetime]],
    *,
    lookback: int = 126,
    cost_bps: float = 5.0,
    currency: str = "USD",
    adjustment: str,
    lockbox_start: datetime | None = None,
) -> Mag7ExampleRun:
    """Reproduce the rank rule using only saved prices observed by each decision."""
    if set(snapshot_ids_by_instrument) != set(MAG7):
        raise ValueError("exactly the seven Mag7 instrument IDs are required")
    if set(expected_bar_ends) != set(MAG7):
        raise ValueError("expected close times must cover the Mag7 instruments")
    if not isinstance(currency, str) or currency.strip().upper() != "USD":
        raise ValueError("Mag7 example requires USD prices")
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 1:
        raise ValueError("lookback must be a positive integer")
    times = tuple(decision_times)
    if not times or any(
        not isinstance(value, datetime) or value.utcoffset() is None for value in times
    ):
        raise ValueError("decision times must be timezone-aware")
    times = tuple(value.astimezone(UTC) for value in times)
    if any(left >= right for left, right in pairwise(times)):
        raise ValueError("decision times must be unique and ordered")
    if any(len(ends) != len(times) for ends in expected_bar_ends.values()):
        raise ValueError("expected close times must align with decisions")
    if lockbox_start is not None:
        if not isinstance(lockbox_start, datetime) or lockbox_start.utcoffset() is None:
            raise ValueError("lockbox_start must be timezone-aware")
        sealed_at = lockbox_start.astimezone(UTC)
        retained = tuple(i for i, value in enumerate(times) if value < sealed_at)
    else:
        retained = tuple(range(len(times)))
    if len(retained) < lookback + 2:
        raise ValueError("not enough pre-lockbox decisions for lookback and next return")
    selected_times = tuple(times[i] for i in retained)
    selected_ends = {
        instrument: tuple(ends[i] for i in retained)
        for instrument, ends in expected_bar_ends.items()
    }
    eligible: list[str] = []
    eligible_by_instrument: dict[str, tuple[str, ...]] = {}
    for instrument in MAG7:
        selected_ids = []
        for snapshot_id in snapshot_ids_by_instrument[instrument]:
            snapshot = store.get_snapshot(snapshot_id)
            if snapshot.observed_at > selected_times[-1]:
                continue
            if snapshot.key.interval != "1d":
                raise ValueError("Mag7 example requires daily price snapshots")
            selected_ids.append(snapshot_id)
            eligible.append(snapshot_id)
        eligible_by_instrument[instrument] = tuple(selected_ids)
    prices = build_pit_close_frame(
        store,
        eligible_by_instrument,
        selected_times,
        currency="USD",
        adjustment=adjustment,
        expected_bar_ends=selected_ends,
    )
    targets = run_prefix_strategy(prices, lambda prefix: _momentum_rank(prefix, lookback))
    returns = prices.pct_change(fill_method=None)
    result = run_backtest(
        targets,
        returns,
        base_currency="USD",
        return_currencies=dict.fromkeys(MAG7, "USD"),
        commission_bps=cost_bps,
    )
    return Mag7ExampleRun(
        targets,
        result,
        tuple(eligible),
        lookback,
        cost_bps,
        adjustment,
        selected_times[-1],
    )
