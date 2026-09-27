"""Explicit exchange schedules; never infer sessions from weekday numbers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from types import MappingProxyType

import pandas as pd

from .contracts import Instrument, _utc
from .prices import BarTiming


@dataclass(frozen=True)
class SessionCalendar:
    market: str
    version: str
    sessions: dict[date, tuple[datetime, datetime]]

    def __post_init__(self):
        if not self.market or not self.version or not self.sessions:
            raise ValueError("calendar market, version and sessions are required")
        clean = {}
        for label, (start, end) in self.sessions.items():
            if not isinstance(label, date) or isinstance(label, datetime):
                raise ValueError("session labels must be dates")
            timing = BarTiming(start, end, True)
            clean[label] = (timing.bar_start, timing.bar_end)
        object.__setattr__(self, "sessions", MappingProxyType(clean))

    @property
    def digest(self):
        value = [
            self.market,
            self.version,
            [
                [label.isoformat(), start.isoformat(), end.isoformat()]
                for label, (start, end) in sorted(self.sessions.items())
            ],
        ]
        return hashlib.sha256(json.dumps(value).encode()).hexdigest()

    @classmethod
    def from_json(cls, content: str):
        data = json.loads(content)
        sessions = {}
        for row in data["sessions"]:
            label = date.fromisoformat(row["date"])
            if label in sessions:
                raise ValueError("duplicate calendar session")
            sessions[label] = (
                datetime.fromisoformat(row["open"]),
                datetime.fromisoformat(row["close"]),
            )
        return cls(data["market"], data["version"], sessions)


def daily_timings(
    labels: pd.DatetimeIndex,
    instrument: Instrument,
    observed_at: datetime,
    *,
    calendar: SessionCalendar | None = None,
):
    observed = _utc(observed_at, "observed_at")
    if labels.tz is None:
        raise ValueError("session labels must be timezone-aware")
    if instrument.market == "CRYPTO":
        if instrument.timezone != "UTC":
            raise ValueError("crypto daily sessions require UTC")
    elif calendar is None or calendar.market != instrument.market:
        raise ValueError("verified calendar for the instrument market is required")
    result = {}
    for label in labels:
        session_date = label.tz_convert(instrument.timezone).date()
        if instrument.market == "CRYPTO":
            start = datetime.combine(session_date, time(), UTC)
            end = start + timedelta(days=1)
        else:
            if session_date not in calendar.sessions:
                raise ValueError(f"calendar has no verified session for {session_date}")
            start, end = calendar.sessions[session_date]
        result[label] = BarTiming(start, end, observed >= end and instrument.market != "FX")
    return result
