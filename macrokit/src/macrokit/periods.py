"""Map a period start plus a frequency onto the period end.

Sources report the period by its first day (FRED returns `2024-01-01` for
January 2024). Storing the end as well makes "what period does this cover"
answerable without knowing the frequency at query time.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def period_end_for(period_start: date, freq: str) -> date:
    if freq == "D":
        return period_start
    if freq == "W":
        return period_start + timedelta(days=6)
    if freq == "M":
        return period_start.replace(
            day=calendar.monthrange(period_start.year, period_start.month)[1]
        )
    if freq == "Q":
        if period_start.month not in (1, 4, 7, 10):
            raise ValueError(
                f"period_end_for: {period_start} is not a quarter start (month must be "
                "1, 4, 7 or 10). Months 2/3/5/6/8/9 would silently return a plausible "
                "but wrong period end; 11/12 overflow past December."
            )
        end_month = period_start.month + 2
        return date(
            period_start.year, end_month, calendar.monthrange(period_start.year, end_month)[1]
        )
    if freq == "A":
        return date(period_start.year, 12, 31)
    raise ValueError(f"unknown frequency: {freq}")
