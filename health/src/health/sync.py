"""Resumable Google Health synchronization with an atomic chunk boundary."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from health.client import ApiError, RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import (
    CATALOG,
    DAILY_ROLLUP,
    Metric,
    PayloadError,
    aligned_chunk,
    chunk_ranges,
)
from health.store import SYNC_IN_PROGRESS, SYNC_OK, Store

MAX_REQUESTS_PER_RUN = 200
TRAILING_REFETCH_DAYS = 2
INTRADAY_LOOKBACK_DAYS = 30
RECENT_WINDOW_DAYS = 7


@dataclass(frozen=True)
class MetricFailure:
    """One metric gave up for this run; the run continued with the others."""

    metric: str
    kind: str  # "api" or "payload"
    status_code: int | None
    message: str


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
    failures: list[MetricFailure] = field(default_factory=list)
    history_remaining: dict[str, int] = field(default_factory=dict)
    paused: bool = False
    resume_in_s: int | None = None
    stopped_early: bool = False
    requests_made: int = 0


class _RunFinished(Exception):  # noqa: N818 -- fixed name from the task interface
    """Internal: the budget ran out or Google asked us to pause."""


@dataclass
class _RunState:
    """Everything one `sync_all()` call threads through both passes.

    `abandoned` is the set of metric names that already recorded a
    `MetricFailure` earlier in this same run (recency pass or history pass).
    `_history_pass` excludes them so a metric that failed on, say, its
    second recency chunk -- which already left it a usable `backfilled_from`
    -- is not attempted again in the history pass of the same run.
    """

    report: SyncReport
    budget: RequestBudget
    progress: dict[str, MetricProgress]
    progress_cb: Callable[[str, str], None] | None
    abandoned: set[str] = field(default_factory=set)


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

    # -- date bounds ---------------------------------------------------------

    def _floor(self, metric: Metric) -> date:
        """The oldest day this metric may ever request."""
        if metric.full_history:
            return backfill_start(self.today, self.environ)
        return self.today - timedelta(days=INTRADAY_LOOKBACK_DAYS - 1)

    def _recent_start(self, metric: Metric) -> date:
        """Where the forward pass starts. A metric with no checkpoint begins one
        short window back, not five years back: the point of the first run is
        that every page has something to show, not that one metric is complete."""
        floor = self._floor(metric)
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None:
            return max(floor, self.today - timedelta(days=RECENT_WINDOW_DAYS - 1))
        if checkpoint.status == SYNC_IN_PROGRESS:
            return max(floor, checkpoint.last_synced + timedelta(days=1))
        return max(floor, checkpoint.last_synced - timedelta(days=TRAILING_REFETCH_DAYS))

    def _next_history_chunk(self, metric: Metric) -> tuple[date, date] | None:
        """The aligned chunk immediately older than everything covered so far,
        or None once history reaches the floor."""
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None or checkpoint.backfilled_from is None:
            return None
        floor = self._floor(metric)
        if checkpoint.backfilled_from <= floor:
            return None
        return aligned_chunk(checkpoint.backfilled_from - timedelta(days=1), metric.max_range_days)

    def history_remaining(self, metric: Metric) -> int:
        checkpoint = self.store.get_sync_checkpoint(metric.name)
        if checkpoint is None or checkpoint.backfilled_from is None:
            return 0
        floor = self._floor(metric)
        if checkpoint.backfilled_from <= floor:
            return 0
        return len(
            chunk_ranges(
                floor, checkpoint.backfilled_from - timedelta(days=1), metric.max_range_days
            )
        )

    # -- one chunk -----------------------------------------------------------

    def _fetch_chunk(self, metric, chunk_start, chunk_end, budget, *, status, watermark):
        request_start = max(chunk_start, self._floor(metric))
        request_end = min(chunk_end, self.today)
        if metric.method == DAILY_ROLLUP:
            payloads = [self.client.daily_rollup(metric, request_start, request_end, budget)]
        else:
            # Buffer every reconcile page. Parsing and replacement only begin
            # once the entire chunk is present.
            payloads = list(self.client.iter_reconciled(metric, request_start, request_end, budget))
        rows = metric.parse_pages(payloads)
        self.store.replace_chunk(
            metric,
            chunk_start,
            chunk_end,
            payloads,
            rows,
            status=status,
            watermark=watermark,
            covered_start=request_start,
            covered_end=request_end,
            backfill_from=chunk_start,
        )
        return request_start, request_end

    # -- the run -------------------------------------------------------------

    def sync_all(self, progress_cb: Callable[[str, str], None] | None = None) -> SyncReport:
        report = SyncReport()
        progress = {m.name: MetricProgress(metric=m.name) for m in self.catalog}
        report.progress = list(progress.values())
        state = _RunState(
            report=report,
            budget=RequestBudget(self.max_requests),
            progress=progress,
            progress_cb=progress_cb,
        )
        try:
            self._recent_pass(state)
            self._history_pass(state)
        except _RunFinished:
            pass
        report.requests_made = state.budget.used
        report.history_remaining = {m.name: self.history_remaining(m) for m in self.catalog}
        return report

    def _recent_pass(self, state: _RunState) -> None:
        for metric in self.catalog:
            start = self._recent_start(metric)
            for chunk_start, chunk_end in chunk_ranges(start, self.today, metric.max_range_days):
                status = SYNC_OK if chunk_end >= self.today else SYNC_IN_PROGRESS
                if not self._guarded(
                    state,
                    metric,
                    chunk_start,
                    chunk_end,
                    status=status,
                    watermark=min(chunk_end, self.today),
                ):
                    break
            else:
                state.progress[metric.name].done = True

    def _history_pass(self, state: _RunState) -> None:
        # A metric already abandoned in the recency pass of this run (e.g. it
        # failed on its second recency chunk, after the first already left it
        # a usable backfilled_from) must not be retried here -- one failure
        # abandons the metric for the whole run, not just the pass it failed in.
        pending = [
            m
            for m in self.catalog
            if m.name not in state.abandoned and self._next_history_chunk(m) is not None
        ]
        while pending:
            next_round = []
            for metric in pending:
                chunk = self._next_history_chunk(metric)
                if chunk is None:
                    continue
                # status/watermark stay None: a history chunk says nothing about
                # how current the metric is.
                if not self._guarded(state, metric, *chunk, status=None, watermark=None):
                    continue
                if self._next_history_chunk(metric) is not None:
                    next_round.append(metric)
            pending = next_round

    def _guarded(
        self, state: _RunState, metric, chunk_start, chunk_end, *, status, watermark
    ) -> bool:
        """Fetch one chunk, translating each error into this run's policy.
        Returns False when this metric should stop; raises _RunFinished when
        the whole run should stop."""
        try:
            request_start, request_end = self._fetch_chunk(
                metric, chunk_start, chunk_end, state.budget, status=status, watermark=watermark
            )
        except RateLimited as exc:
            state.report.paused = True
            state.report.resume_in_s = exc.retry_after_s
            raise _RunFinished from exc
        except RequestCapExceeded as exc:
            state.report.stopped_early = True
            raise _RunFinished from exc
        except ApiError as exc:
            # One data type can be unavailable (403 for a scope never
            # granted, 404 for a device that produces nothing) without
            # saying anything about the next metric -- same isolation
            # rule probe.py already uses.
            state.report.failures.append(
                MetricFailure(metric.name, "api", exc.status_code, exc.message)
            )
            state.abandoned.add(metric.name)
            return False
        except PayloadError as exc:
            state.report.failures.append(MetricFailure(metric.name, "payload", None, exc.detail))
            state.abandoned.add(metric.name)
            return False
        state.progress[metric.name].fetched_ranges += 1
        if state.progress_cb:
            state.progress_cb(
                metric.name, f"{request_start} → {request_end} ({state.budget.used} requests)"
            )
        return True
