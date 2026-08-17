"""Resolve a catalog ReleaseRule into a concrete publication datetime.

Japanese agencies publish on regular rules ("5th business day", "the 19th",
"3rd Friday"), so declaring the rule in YAML avoids scraping the schedule pages.
US indicators do not use this at all -- FRED's releases/dates endpoint gives
their calendar directly, including future dates.

Every rule is relative to the month AFTER the period ends, which is how monthly
Japanese statistics are published.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .catalog import ReleaseRule


def nth_business_day(year: int, month: int, n: int, holidays: set[date]) -> date:
    """The nth business day of a month (1-indexed), skipping weekends and holidays."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    days_in_month = calendar.monthrange(year, month)[1]
    seen = 0
    for day in range(1, days_in_month + 1):
        candidate = date(year, month, day)
        if candidate.weekday() >= 5 or candidate in holidays:
            continue
        seen += 1
        if seen == n:
            return candidate
    raise ValueError(f"month {year}-{month:02d} has no {n}th business day")


def nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
    """The nth occurrence of a weekday in a month. ``weekday`` is Mon=0 .. Sun=6."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    days_in_month = calendar.monthrange(year, month)[1]
    seen = 0
    for day in range(1, days_in_month + 1):
        candidate = date(year, month, day)
        if candidate.weekday() != weekday:
            continue
        seen += 1
        if seen == n:
            return candidate
    raise ValueError(f"month {year}-{month:02d} has no {n}th weekday {weekday}")


def _month_after(period_end: date) -> tuple[int, int]:
    first_of_next = (period_end.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_of_next.year, first_of_next.month


def resolve_release(rule: ReleaseRule, period_end: date, holidays: set[date]) -> datetime | None:
    """Publication datetime for the period ending ``period_end``.

    Returns ``None`` for ``kind="manual"``: the schedule is not expressible as a
    rule and must be supplied by hand.
    """
    if rule.kind == "manual":
        return None

    year, month = _month_after(period_end)
    if rule.kind == "nth_business_day":
        if rule.n is None:
            raise ValueError("nth_business_day requires n")
        day = nth_business_day(year, month, rule.n, holidays)
    elif rule.kind == "fixed_day":
        if rule.day is None:
            raise ValueError("fixed_day requires day")
        day = date(year, month, rule.day)
    elif rule.kind == "nth_weekday":
        if rule.n is None or rule.weekday is None:
            raise ValueError("nth_weekday requires n and weekday")
        day = nth_weekday(year, month, rule.n, rule.weekday)
    else:  # pragma: no cover - Literal keeps this unreachable
        raise ValueError(f"unknown release rule kind: {rule.kind}")

    hour, minute = (int(part) for part in rule.time.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(rule.tz))
