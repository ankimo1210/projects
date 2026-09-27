"""Point-in-time views of immutable macro observation vintages."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime

from .contracts import MacroObservation


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def as_of(
    observations: Iterable[MacroObservation],
    indicator: str,
    when: datetime,
    *,
    source: str | None = None,
) -> tuple[MacroObservation, ...]:
    """Return the last released vintage per period at an aware decision time."""
    cutoff = _aware_utc(when, "when")
    selected: dict[tuple[date, str], MacroObservation] = {}
    releases: set[tuple[date, str, datetime]] = set()
    sources_by_period: dict[date, set[str]] = {}
    for row in observations:
        if row.indicator != indicator or row.release_at > cutoff:
            continue
        if source is not None and row.source != source:
            continue
        release_key = (row.period_start, row.source, row.release_at)
        if release_key in releases:
            raise ValueError(f"conflicting releases for {indicator}: {release_key}")
        releases.add(release_key)
        sources_by_period.setdefault(row.period_start, set()).add(row.source)
        group = (row.period_start, row.source)
        previous = selected.get(group)
        if previous is None or row.release_at > previous.release_at:
            selected[group] = row
    if source is None and any(len(sources) > 1 for sources in sources_by_period.values()):
        raise ValueError(f"source is required when {indicator} has multiple providers")
    return tuple(selected[key] for key in sorted(selected, key=lambda item: (item[0], item[1])))


def latest(
    observations: Iterable[MacroObservation],
    indicator: str,
    *,
    now: datetime | None = None,
    source: str | None = None,
) -> tuple[MacroObservation, ...]:
    """Latest released vintages from a separately declared current viewpoint."""
    return as_of(observations, indicator, now or datetime.now(UTC), source=source)
