"""What the market could have known before each release.

Every method here obeys one rule: an expectation for a release at ``T`` may only
read vintages whose ``release_date`` is strictly before ``T``. The measured cost
of breaking it: 2026 Q1 stood at +1.8 before the 2026-08-17 release and at +1.9
after it, because that release revised the quarter it was not reporting on.

Business days come from ``market_rates`` rather than the holiday calendar, which
is missing the year-end government and bank holidays.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import duckdb

from . import pit
from .store import Expectation, ReleaseEvent

SOURCE_URL = "computed://macrokit/expectations"


def previous_business_day(con: duckdb.DuckDBPyConnection, when: date) -> date | None:
    row = con.execute(
        "SELECT max(obs_date) FROM market_rates WHERE obs_date < ?", [when]
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _knowable_before(con: duckdb.DuckDBPyConnection, event: ReleaseEvent):
    """The series and the as-of date visible on the last business day before the release."""
    as_of_date = previous_business_day(con, event.release_date.date())
    if as_of_date is None:
        return None, None
    cutoff = datetime.combine(
        as_of_date + timedelta(days=1), datetime.min.time(), tzinfo=event.release_date.tzinfo
    )
    return pit.as_of(con, event.indicator, cutoff), as_of_date


def _previous_quarter(period_start: date) -> date:
    month = period_start.month - 3
    return date(period_start.year - 1, month + 12, 1) if month < 1 else date(period_start.year, month, 1)


def _expectation(event: ReleaseEvent, method: str, value: float, as_of: date) -> Expectation:
    return Expectation(
        indicator=event.indicator,
        period_start=event.period_start,
        release_kind=event.release_kind,
        method=method,
        expected=value,
        as_of=as_of,
        source="macrokit",
        source_url=SOURCE_URL,
        ingested_at=event.ingested_at,
    )


def random_walk(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """Expect this quarter to repeat the previous quarter's last-knowable value."""
    series, as_of_date = _knowable_before(con, event)
    if series is None or series.empty:
        return None
    previous = _previous_quarter(event.period_start)
    if previous not in series.index:
        return None
    return _expectation(event, "random_walk", float(series[previous]), as_of_date)


def prior_vintage(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """A second preliminary's anchor is the first preliminary's published value."""
    if event.release_kind != "2nd_prelim":
        return None
    series, as_of_date = _knowable_before(con, event)
    if series is None or event.period_start not in series.index:
        return None
    return _expectation(event, "prior_vintage", float(series[event.period_start]), as_of_date)


METHODS = {"random_walk": random_walk, "prior_vintage": prior_vintage}


def compute(
    con: duckdb.DuckDBPyConnection,
    events: list[ReleaseEvent],
    *,
    methods: tuple[str, ...] = ("random_walk", "prior_vintage"),
) -> list[Expectation]:
    rows: list[Expectation] = []
    for event in events:
        for method in methods:
            result = METHODS[method](con, event)
            if result is not None:
                rows.append(result)
    return rows
