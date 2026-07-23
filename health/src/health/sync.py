"""Resumable Google Health synchronization with an atomic chunk boundary."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP, Metric, chunk_ranges
from health.store import SYNC_IN_PROGRESS, SYNC_OK, Store

MAX_REQUESTS_PER_RUN = 200
TRAILING_REFETCH_DAYS = 2
INTRADAY_LOOKBACK_DAYS = 30


def backfill_start(today: date, environ: Mapping[str, str] | None = None) -> date:
    """Return the configured start date, or the same calendar day five years ago.

    February 29 is rounded down to February 28. Invalid and future overrides
    fail before a request is made, instead of silently selecting a surprising
    amount of private health history.
    """

    environ = os.environ if environ is None else environ
    configured = environ.get("HEALTH_BACKFILL_START", "").strip()
    if configured:
        try:
            start = date.fromisoformat(configured)
        except ValueError as exc:
            raise ValueError("HEALTH_BACKFILL_START must be an ISO date (YYYY-MM-DD)") from exc
        if start > today:
            raise ValueError("HEALTH_BACKFILL_START cannot be in the future")
        return start

    try:
        return today.replace(year=today.year - 5)
    except ValueError:  # February 29 -> February 28 in a non-leap year
        return today.replace(year=today.year - 5, day=28)


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
    stopped_early: bool = False
    requests_made: int = 0


class SyncEngine:
    def __init__(
        self,
        client,
        store: Store,
        catalog: Sequence[Metric] = CATALOG,
        today: date | None = None,
        environ: Mapping[str, str] | None = None,
        max_requests: int = MAX_REQUESTS_PER_RUN,
    ):
        self.client = client
        self.store = store
        self.catalog = catalog
        self.today = today or date.today()
        self.environ = environ
        self.max_requests = max_requests

    def _initial_start(self, metric: Metric) -> date:
        if metric.full_history:
            return backfill_start(self.today, self.environ)
        return self.today - timedelta(days=INTRADAY_LOOKBACK_DAYS - 1)

    def _start_date(self, metric: Metric) -> date:
        initial = self._initial_start(metric)
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None:
            return initial
        last, status = checkpoint
        if status == SYNC_IN_PROGRESS:
            # A request cap or error stopped between chunks. Continue at the
            # first unfinished day so even a very small cap makes progress.
            return max(initial, last + timedelta(days=1))
        # A completed metric deliberately overlaps the previous watermark so
        # late-arriving values and upstream deletions are reconciled, including
        # on the first sync of a later calendar day.
        return max(initial, last - timedelta(days=TRAILING_REFETCH_DAYS))

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None) -> SyncReport:
        report = SyncReport()
        budget = RequestBudget(self.max_requests)

        for metric in self.catalog:
            progress = MetricProgress(metric=metric.name)
            report.progress.append(progress)
            start = self._start_date(metric)

            for chunk_start, chunk_end in chunk_ranges(start, self.today, metric.max_range_days):
                try:
                    if metric.method == DAILY_ROLLUP:
                        payloads = [
                            self.client.daily_rollup(metric, chunk_start, chunk_end, budget)
                        ]
                    else:
                        # Buffer every reconcile page. Parsing and replacement
                        # only begin once the entire chunk is present.
                        payloads = list(
                            self.client.iter_reconciled(metric, chunk_start, chunk_end, budget)
                        )
                    rows = metric.parse_pages(payloads)
                    status = SYNC_OK if chunk_end == self.today else SYNC_IN_PROGRESS
                    self.store.replace_chunk(
                        metric,
                        chunk_start,
                        chunk_end,
                        payloads,
                        rows,
                        status=status,
                    )
                except RateLimited as exc:
                    report.paused = True
                    report.resume_in_s = exc.retry_after_s
                    report.requests_made = budget.used
                    return report
                except RequestCapExceeded:
                    report.stopped_early = True
                    report.requests_made = budget.used
                    return report

                progress.fetched_ranges += 1
                if progress_cb:
                    progress_cb(
                        metric.name,
                        f"{chunk_start} → {chunk_end} ({budget.used} requests)",
                    )
            progress.done = True

        report.requests_made = budget.used
        return report
