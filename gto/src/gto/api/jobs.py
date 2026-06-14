"""Minimal in-process job subsystem for the async solve tier (M1b).

Flop custom solves are heavy (a bucketed K_r=128 full SRP 100bb solve is
~10 GB / tens of minutes), so they cannot run on the request path. This is a
deliberately small job manager — no external broker, no persistence beyond
process lifetime — with the one property that actually matters on a single
box: **memory-accounted admission control**. A job only starts when its
declared memory reservation fits the budget; otherwise it queues. On this
box (~22 GB free, flop reservation ~12 GB) that means one flop solve runs at
a time and a second one waits rather than OOM-killing the server.

Honest limitations (documented, not hidden):
- The Rust solve has no cancellation hook, so cancelling a *running* job is
  best-effort: the worker thread runs to completion and its result is
  discarded; the memory reservation frees only when the thread returns.
  Cancelling a *queued* job is immediate.
- Results live in process memory with a TTL; a restart loses them.
- Admission is skip-the-queue (a small job may start ahead of a queued large
  one that does not fit). FIFO within the set of jobs that fit.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


_FINISHED = (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED)


@dataclass
class Job:
    id: str
    kind: str
    est_gb: float
    status: JobStatus = JobStatus.QUEUED
    submitted_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    result: Any | None = None
    error: str | None = None
    _fn: Callable[[], Any] | None = None
    _cancel: bool = False

    def snapshot(self) -> dict:
        """Public status view (no internal fn / cancel flag, no heavy result)."""
        now = time.monotonic()
        started = self.started_at
        finished = self.finished_at
        elapsed = (
            (finished or now) - started if started is not None else None
        )
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status.value,
            "est_gb": self.est_gb,
            "queued_s": (started or now) - self.submitted_at,
            "elapsed_s": elapsed,
            "error": self.error,
        }


def _mem_available_gb() -> float:
    """Available RAM in GB from /proc/meminfo; conservative fallback on miss."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1e6  # kB -> GB
    except (OSError, ValueError):
        pass
    return 8.0


class JobManager:
    """Thread-backed job runner with memory-accounted admission control."""

    def __init__(
        self,
        budget_gb: float | None = None,
        ttl_s: float = 3600.0,
        mem_available_fn: Callable[[], float] = _mem_available_gb,
    ) -> None:
        # Reserve a fraction of currently-available RAM as the budget, so one
        # flop job (~12 GB) fits and a second queues. Env override for ops.
        env = os.environ.get("GTO_JOB_MEM_BUDGET_GB")
        if budget_gb is not None:
            self._budget_gb = budget_gb
        elif env:
            self._budget_gb = float(env)
        else:
            self._budget_gb = max(1.0, mem_available_fn() * 0.8)
        self._ttl_s = ttl_s
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._queue: list[str] = []
        self._running_gb = 0.0

    @property
    def budget_gb(self) -> float:
        return self._budget_gb

    def submit(self, kind: str, est_gb: float, fn: Callable[[], Any]) -> str:
        jid = uuid.uuid4().hex[:12]
        with self._lock:
            self._evict_expired_locked()
            job = Job(id=jid, kind=kind, est_gb=est_gb, _fn=fn)
            self._jobs[jid] = job
            self._queue.append(jid)
            self._try_schedule_locked()
        return jid

    def get(self, jid: str) -> Job | None:
        with self._lock:
            self._evict_expired_locked()
            return self._jobs.get(jid)

    def status(self, jid: str) -> dict | None:
        job = self.get(jid)
        return job.snapshot() if job else None

    def result(self, jid: str) -> tuple[JobStatus, Any | None, str | None] | None:
        with self._lock:
            job = self._jobs.get(jid)
            if job is None:
                return None
            return job.status, job.result, job.error

    def cancel(self, jid: str) -> bool:
        """True if the job was queued (cancelled now) or running (best-effort).
        False if unknown or already finished."""
        with self._lock:
            job = self._jobs.get(jid)
            if job is None:
                return False
            if job.status == JobStatus.QUEUED:
                if jid in self._queue:
                    self._queue.remove(jid)
                job.status = JobStatus.CANCELLED
                job.finished_at = time.monotonic()
                job._fn = None
                return True
            if job.status == JobStatus.RUNNING:
                job._cancel = True  # best-effort; no Rust cancel hook
                return True
            return False

    def stats(self) -> dict:
        with self._lock:
            counts: dict[str, int] = {}
            for j in self._jobs.values():
                counts[j.status.value] = counts.get(j.status.value, 0) + 1
            return {
                "budget_gb": round(self._budget_gb, 2),
                "running_gb": round(self._running_gb, 2),
                "queued": len(self._queue),
                "counts": counts,
            }

    # ----- internals (call under self._lock) ---------------------------------

    def _try_schedule_locked(self) -> None:
        i = 0
        while i < len(self._queue):
            jid = self._queue[i]
            job = self._jobs[jid]
            # Always let at least one job run (running_gb == 0), else admit only
            # if it fits the remaining budget. Skip-and-continue so a small job
            # can start ahead of a queued large one that does not fit.
            fits = self._running_gb == 0.0 or self._running_gb + job.est_gb <= self._budget_gb
            if fits:
                self._queue.pop(i)
                self._running_gb += job.est_gb
                job.status = JobStatus.RUNNING
                job.started_at = time.monotonic()
                t = threading.Thread(target=self._run, args=(jid,), daemon=True)
                t.start()
            else:
                i += 1

    def _run(self, jid: str) -> None:
        with self._lock:
            job = self._jobs[jid]
            fn = job._fn
        res: Any | None = None
        err: str | None = None
        try:
            res = fn() if fn else None
        except BaseException as e:
            # Catch BaseException, not just Exception: a Rust panic surfaces as
            # pyo3_runtime.PanicException, which subclasses BaseException. If it
            # escaped this handler the reservation-release below would be skipped
            # and est_gb would leak permanently, wedging the async flop tier.
            err = repr(e)
        with self._lock:
            job.finished_at = time.monotonic()
            if err is not None:
                job.error, job.status = err, JobStatus.ERROR
            elif job._cancel:
                job.status = JobStatus.CANCELLED  # result discarded
            else:
                job.result, job.status = res, JobStatus.DONE
            self._running_gb -= job.est_gb
            job._fn = None
            self._try_schedule_locked()

    def _evict_expired_locked(self) -> None:
        now = time.monotonic()
        stale = [
            jid
            for jid, j in self._jobs.items()
            if j.status in _FINISHED
            and j.finished_at is not None
            and now - j.finished_at > self._ttl_s
        ]
        for jid in stale:
            del self._jobs[jid]


# Process-wide singleton used by the solve router.
job_manager = JobManager()
