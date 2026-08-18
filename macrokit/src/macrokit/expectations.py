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
import numpy as np

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

AR_ORDER = 4
AR_MIN_OBSERVATIONS = AR_ORDER + 8


def ar_model(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """One-step-ahead AR(4) forecast fitted by OLS on everything knowable at as_of.

    The order is fixed rather than selected: choosing p from the data would let
    the selection see information the forecast is not allowed to use, and the
    resulting surprise would be smaller than any trader could have achieved.
    """
    series, as_of_date = _knowable_before(con, event)
    if series is None:
        return None
    history = series.sort_index()
    history = history[history.index < event.period_start]
    if len(history) < AR_MIN_OBSERVATIONS:
        return None

    values = history.to_numpy(dtype=float)
    rows = len(values) - AR_ORDER
    design = np.column_stack(
        [np.ones(rows)] + [values[AR_ORDER - lag : len(values) - lag] for lag in range(1, AR_ORDER + 1)]
    )
    target = values[AR_ORDER:]
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)

    latest = np.concatenate([[1.0], values[-1 : -AR_ORDER - 1 : -1]])
    return _expectation(event, "ar_model", float(latest @ coefficients), as_of_date)


METHODS["ar_model"] = ar_model


def compute(
    con: duckdb.DuckDBPyConnection,
    events: list[ReleaseEvent],
    *,
    methods: tuple[str, ...] = ("random_walk", "prior_vintage", "ar_model"),
) -> list[Expectation]:
    rows: list[Expectation] = []
    for event in events:
        for method in methods:
            result = METHODS[method](con, event)
            if result is not None:
                rows.append(result)
    return rows
