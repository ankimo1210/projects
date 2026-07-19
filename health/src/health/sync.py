"""Resumable backfill/incremental sync over the metric catalog."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import RateLimited
from health.endpoints import CATALOG, Metric, chunk_ranges
from health.store import Store

TRAILING_REFETCH_DAYS = 2   # re-fetch last_synced - 2d .. today (3-day window)
TRAILING_BACKFILL_DAYS = 29  # non-full-history metrics: today - 29d start


@dataclass
class MetricProgress:
    metric: str
    fetched_ranges: int = 0
    done: bool = False


@dataclass
class SyncReport:
    progress: list[MetricProgress] = field(default_factory=list)
    paused: bool = False
    resume_in_s: int | None = None


class SyncEngine:
    def __init__(self, client, store: Store, catalog: list[Metric] = CATALOG,
                 today: date | None = None, member_since: date | None = None):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.member_since = member_since

    def _fetch_member_since(self) -> date:
        payload = self.client.get("/1/user/-/profile.json")
        return date.fromisoformat(payload["user"]["memberSince"])

    def _start_date(self, m: Metric, member_since: date) -> date:
        default = member_since if m.full_history else (
            self.today - timedelta(days=TRAILING_BACKFILL_DAYS))
        last = self.store.get_sync_state(m.name)
        if last is None:
            return default
        return max(default, min(last - timedelta(days=TRAILING_REFETCH_DAYS), self.today))

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None,
                 min_budget: int = 5) -> SyncReport:
        report = SyncReport()
        member_since = self.member_since
        if member_since is None:
            member_since = self.member_since = self._fetch_member_since()
        for m in self.catalog:
            prog = MetricProgress(metric=m.name)
            report.progress.append(prog)
            start = self._start_date(m, member_since)
            for s, e in chunk_ranges(start, self.today, m.max_range_days):
                if self.client.remaining is not None and self.client.remaining < min_budget:
                    report.paused = True
                    report.resume_in_s = self.client.reset_s
                    return report
                path = m.path.format(start=s.isoformat(), end=e.isoformat(),
                                     date=s.isoformat())
                try:
                    payload = self.client.get(path)
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    return report
                self.store.upsert_raw(m.name, f"{s}_{e}", payload)
                rows = m.parse(payload)
                self.store.upsert_daily(rows.daily)
                self.store.upsert_sleep(rows.sleep)
                self.store.upsert_intraday(rows.intraday)
                self.store.set_sync_state(m.name, e)
                prog.fetched_ranges += 1
                if progress_cb:
                    progress_cb(m.name, f"{s} → {e}")
            prog.done = True
        return report
