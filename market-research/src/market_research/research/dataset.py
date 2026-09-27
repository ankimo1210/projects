"""Display inputs from immutable price snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from market_research.contracts import ADJUSTMENTS, PriceBar, PriceGap
from market_research.prices import PriceExclusion
from market_research.storage import ResearchStore


@dataclass(frozen=True, slots=True)
class PriceDataset:
    as_of: datetime
    snapshot_ids: tuple[str, ...]
    currency: str
    adjustment: str
    bars: tuple[PriceBar, ...]
    gaps: tuple[PriceGap, ...]
    exclusions: tuple[PriceExclusion, ...]
    mode: str = "retrospective"


def load_price_dataset(
    store: ResearchStore,
    snapshot_ids: tuple[str, ...],
    *,
    as_of: datetime,
    currency: str,
    adjustment: str,
) -> PriceDataset:
    """Read selected saved rows without fetching or claiming historical PIT."""
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    when = as_of.astimezone(UTC)
    ids = tuple(snapshot_ids)
    if not ids:
        raise ValueError("at least one snapshot is required")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate snapshot IDs")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency is required")
    selected_currency = currency.strip().upper()
    if adjustment not in ADJUSTMENTS:
        raise ValueError("invalid adjustment")

    providers: dict[str, str] = {}
    views = []
    for snapshot_id in ids:
        snapshot = store.get_snapshot(snapshot_id)
        if snapshot.observed_at > when:
            raise ValueError("future snapshot cannot supply research prices")
        if not snapshot.complete or snapshot.key.dataset != "prices":
            raise ValueError("complete price snapshot required")
        if snapshot.key.currency != selected_currency:
            raise ValueError("snapshot currency differs from requested currency")
        if snapshot.key.adjustment != adjustment:
            raise ValueError("snapshot adjustment differs from requested adjustment")
        previous_provider = providers.get(snapshot.key.identity)
        if previous_provider is not None:
            if previous_provider != snapshot.key.provider:
                raise ValueError("provider mixing for one instrument is not allowed")
            raise ValueError("duplicate instrument snapshot")
        providers[snapshot.key.identity] = snapshot.key.provider
        views.append(store.snapshot_price_view(snapshot, when))
    return PriceDataset(
        as_of=when,
        snapshot_ids=ids,
        currency=selected_currency,
        adjustment=adjustment,
        bars=tuple(bar for view in views for bar in view.bars),
        gaps=tuple(gap for view in views for gap in view.gaps),
        exclusions=tuple(exclusion for view in views for exclusion in view.exclusions),
    )
