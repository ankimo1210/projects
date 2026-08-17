"""Resolve a catalog ReleaseRule into a concrete publication datetime.

Japanese agencies publish on regular rules ("5th business day", "the 19th",
"3rd Friday"), so declaring the rule in YAML avoids scraping the schedule pages.
US indicators do not use this at all -- FRED's releases/dates endpoint gives
their calendar directly, including future dates.

Every rule is relative to the month AFTER the period ends, which is how monthly
Japanese statistics are published.

KNOWN LIMITATION -- business-day count in January and December is unreliable.
``nth_business_day``'s only holiday source is the Cabinet Office's 国民の祝日
CSV (see ``holidays.py``), which does not include the 年末年始 administrative
closure (12/29-1/3, per the law on government office holidays) or bank
holidays (12/31-1/3). Neither of those counts as a public holiday, so this
module cannot subtract them, and ``nth_business_day`` overcounts business days
in January and December by up to two. This matters here because the Bank of
Japan's 消費活動指数 publishes on the 5th business day -- exactly the rule this
module's tests exercise. Do not read a passing test for a January/December
date as validated Bank of Japan behaviour; a proper business-day calendar is
future work.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .catalog import ReleaseRule


def nth_business_day(year: int, month: int, n: int, holidays: set[date]) -> date:
    """The nth business day of a month (1-indexed), skipping weekends and holidays.

    ``holidays`` is expected to be the Cabinet Office's 国民の祝日 set (see
    ``holidays.py``), which excludes the 年末年始 administrative closure
    (12/29-1/3) and bank holidays (12/31-1/3). Neither is a public holiday, so
    this function cannot know to skip them: results for January and December
    overcount business days by up to two and should not be treated as
    reliable until a proper business-day calendar exists.
    """
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
    if rule.calendar != "jp":
        raise ValueError(
            f"resolve_release only knows the 'jp' calendar (nth_business_day skips "
            f"Japanese holidays); got calendar={rule.calendar!r}. US release dates "
            "come from FRED's releases/dates endpoint instead, not this function."
        )

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
